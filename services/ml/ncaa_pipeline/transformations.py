"""Data transformation functions for labeling and game-level aggregation."""
import difflib

import pandas as pd
import numpy as np
from utils import parse_dates, normalize_key, standardize_opponent_columns, normalize_name


def _ensure_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Guarantee the provided columns exist (filled with NaN if missing)."""
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            out[col] = pd.NA
    return out


def _align_rating_keys(
    ratings: pd.DataFrame,
    known_keys: set[str],
    cutoff: float = 0.9,
) -> pd.DataFrame:
    """Map unrated team keys to closest known keys via string similarity."""
    if ratings.empty or not known_keys:
        return ratings

    known_keys = {k for k in known_keys if isinstance(k, str) and k}
    if not known_keys:
        return ratings

    unique_keys = {k for k in ratings["team_key"].dropna().astype(str)}
    missing = unique_keys - known_keys
    if not missing:
        return ratings

    mapping: dict[str, str] = {}
    for key in sorted(missing):
        match = difflib.get_close_matches(key, known_keys, n=1, cutoff=cutoff)
        if match:
            mapping[key] = match[0]

    if not mapping:
        return ratings

    aligned = ratings.copy()
    aligned["team_key"] = aligned["team_key"].replace(mapping)
    return aligned


def add_labels(cleaned: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """
    Add outcome labels (win, margin, total) and contextual features 
    (home/away, conference game, etc.) by merging with raw game logs.
    """
    raw = raw.copy()
    raw = standardize_opponent_columns(raw)
    raw["Date"] = parse_dates(raw["Date"])
    try:
        raw["Date"] = raw["Date"].dt.tz_localize(None)
    except Exception:
        pass
    raw["Date"] = raw["Date"].dt.normalize()
    raw["team_key"] = normalize_key(raw["Team"])
    raw["opp_key"] = normalize_key(raw["Opp"])
    
    # Build conference map (most frequent non-null value per team)
    if "Conference" in raw.columns:
        conf_df = raw[["Team", "Conference"]].copy()
        conf_df["team_key"] = normalize_key(conf_df["Team"])
        conf_df = conf_df.dropna(subset=["Conference"])
        conf_map = (
            conf_df.groupby("team_key")["Conference"]
                   .agg(lambda s: s.value_counts().idxmax())
        )
    else:
        conf_map = pd.Series(dtype=object)
    
    # Select only needed columns from raw to avoid duplication
    score_col = "opp_score" if "opp_score" in raw.columns else "Opp.1"
    raw_cols = ["team_key", "opp_key", "Date", "Tm", "Location"]
    if score_col in raw.columns:
        raw_cols.append(score_col)
    raw_subset = raw[[c for c in raw_cols if c in raw.columns]].copy()
    
    # Merge with raw scores and location
    merged = pd.merge(
        cleaned,
        raw_subset,
        on=["team_key", "opp_key", "Date"],
        how="inner"
    )
    
    # Resolve team/opponent scores (merges may create _x/_y suffixes).
    team_sources = ["Tm_y", "Tm_x", "Tm", "team_score"]
    opp_sources = ["opp_score_y", "opp_score_x", score_col, "opp_score"]

    def _extract_score(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
        for col in candidates:
            if col and col in df.columns:
                return pd.to_numeric(df[col], errors="coerce")
        return pd.Series(pd.NA, index=df.index, dtype="float64")

    merged["team_score"] = _extract_score(merged, team_sources)
    merged["opp_score"] = _extract_score(merged, opp_sources)

    drop_candidates = {"Tm", "Tm_x", "Tm_y", "team_score_x", "team_score_y",
                       score_col, "opp_score_x", "opp_score_y"}
    keep = {"team_score", "opp_score"}
    drop_cols = [c for c in drop_candidates if c in merged.columns and c not in keep]
    if drop_cols:
        merged = merged.drop(columns=drop_cols)
    
    # Ensure numeric
    if "team_score" in merged.columns:
        merged["team_score"] = pd.to_numeric(merged["team_score"], errors="coerce")
    if "opp_score" in merged.columns:
        merged["opp_score"] = pd.to_numeric(merged["opp_score"], errors="coerce")
    
    # Create outcome labels
    if "team_score" in merged.columns and "opp_score" in merged.columns:
        merged["win"] = (merged["team_score"] > merged["opp_score"]).astype(int)
        merged["margin"] = merged["team_score"] - merged["opp_score"]
        merged["total"] = merged["team_score"] + merged["opp_score"]
    else:
        merged["win"] = 0
        merged["margin"] = 0
        merged["total"] = 0
    
    # Home/away/neutral from Location column
    location_sources = [c for c in ("Location_x", "Location_y", "Location") if c in merged.columns]
    if location_sources:
        loc = merged[location_sources[0]].fillna("")
        merged["is_neutral"] = (loc == "N").astype(int)
        merged["is_home"] = (~loc.isin(["@", "N"])).astype(int)
        drop_loc = [c for c in location_sources if c in merged.columns]
        merged = merged.drop(columns=drop_loc)
    else:
        merged["is_neutral"] = 0
        merged["is_home"] = 1  # Default to home when no indicator present
    
    # Conference game flag: team_conf == opp_conf
    if not conf_map.empty:
        team_conf = merged["team_key"].map(conf_map)
        opp_conf = merged["opp_key"].map(conf_map)
        merged["is_conf_game"] = (
            team_conf.notna() & opp_conf.notna() & (team_conf == opp_conf)
        ).astype(int)
    else:
        merged["is_conf_game"] = 0
    

    
    # Game ID: same id for both team rows
    merged["Date"] = pd.to_datetime(merged["Date"], errors="coerce")
    merged["team_key"] = merged["team_key"].astype(str).apply(normalize_name)
    merged["opp_key"] = merged["opp_key"].astype(str).apply(normalize_name)

    pair_key = np.where(
        merged["team_key"] <= merged["opp_key"],
        merged["team_key"] + "_" + merged["opp_key"],
        merged["opp_key"] + "_" + merged["team_key"],
    )

    # Make sure final key is safe (lowercase, alnum only)
    merged["game_key"] = pair_key + "_" + merged["Date"].dt.strftime("%Y%m%d")
    merged["game_key"] = merged["game_key"].str.lower().str.replace(r"[^a-z0-9_]", "", regex=True)
    
    return merged


def attach_torvik_ratings(
    df: pd.DataFrame,
    ratings: pd.DataFrame,
    feature_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Enrich team rows with daily Bart Torvik metrics for both teams."""
    base_cols = ["rank", "barthag", "adj_o", "adj_d"]
    if feature_cols is None:
        feature_cols = [c for c in base_cols if c in ratings.columns]
    else:
        feature_cols = [c for c in feature_cols if c in ratings.columns]

    merged = df.copy()

    if feature_cols:
        keep = ["team_key", "Date"] + feature_cols
        ratings = ratings[[c for c in keep if c in ratings.columns]].copy()

        known_keys = (
            set(merged.get("team_key", pd.Series(dtype=object)).dropna().astype(str)) |
            set(merged.get("opp_key", pd.Series(dtype=object)).dropna().astype(str))
        )
        ratings = _align_rating_keys(ratings, known_keys)

        if not ratings.empty:
            team_map = {col: f"team_{col}" for col in feature_cols}
            team_ratings = ratings.rename(columns=team_map)
            merged = merged.drop(columns=list(team_map.values()), errors="ignore")
            merged = merged.merge(team_ratings, on=["team_key", "Date"], how="left")

            opp_map = {col: f"opp_{col}" for col in feature_cols}
            opp_ratings = ratings.rename(columns={"team_key": "opp_key", **opp_map})
            merged = merged.drop(columns=list(opp_map.values()), errors="ignore")
            merged = merged.merge(opp_ratings, on=["opp_key", "Date"], how="left")

    all_cols = [f"team_{c}" for c in base_cols] + [f"opp_{c}" for c in base_cols]
    merged = _ensure_columns(merged, all_cols)
    return merged


def make_per_game(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reduce to one row per game by preferring home team row.
    Uses game_key to identify unique games.
    """
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    # Build game_key if not present
    if "game_key" not in df.columns:
        pair_key = np.where(
            df["team_key"] <= df["opp_key"],
            df["team_key"] + "_" + df["opp_key"],
            df["opp_key"] + "_" + df["team_key"],
        )
        df["game_key"] = pair_key + "_" + df["Date"].dt.strftime("%Y%m%d")
    
    # Prefer home row (is_home==1); otherwise keep first
    df = df.sort_values(
        ["Date", "game_key", "is_home"], 
        ascending=[True, True, False]
    ).reset_index(drop=True)
    
    per_game = df.drop_duplicates(subset=["game_key"], keep="first")
    
    return per_game
