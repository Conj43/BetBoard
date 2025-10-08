"""
Functions for loading and reducing betting line data.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from config import (
    BET_COLS_MAP,
    betting_path_for,
    TORVIK_DAILY_PATH,
    TORVIK_FEATURE_COLS,
)
from utils import parse_dates, normalize_key


def load_betting(year: str) -> pd.DataFrame:
    """
    Load betting lines CSV for a year and normalize columns/keys.
    Returns DataFrame with standardized bet_* columns.
    """
    path = betting_path_for(year)
    if not path.exists():
        raise FileNotFoundError(str(path))
    
    b = pd.read_csv(path)
    
    # Drop any duplicate-named columns (some CSVs may repeat headers)
    if b.columns.duplicated().any():
        b = b.loc[:, ~b.columns.duplicated()].copy()
    
    # If there are multiple columns that are effectively 'Date' (case-insensitive), keep the first
    date_like = [c for c in b.columns if c.lower() == "date"]
    if len(date_like) > 1:
        keep = date_like[0]
        drop = date_like[1:]
        b = b.drop(columns=drop)
        if keep != "Date":
            b = b.rename(columns={keep: "Date"})
    
    # Rename to normalized bet_* columns where present
    rename = {k: v for k, v in BET_COLS_MAP.items() if k in b.columns}
    b = b.rename(columns=rename)
    
    # After renaming, ensure unique column names again
    if b.columns.duplicated().any():
        seen = set()
        new_cols = []
        for col in b.columns:
            if col not in seen:
                new_cols.append(col)
                seen.add(col)
            else:
                new_cols.append(f"__dup__{col}")
        b.columns = new_cols
        b = b.loc[:, [c for c in b.columns if not c.startswith("__dup__")]].copy()
    
    # Parse date
    b["Date"] = parse_dates(b["Date"]) if "Date" in b.columns else pd.NaT
    if "Date" in b.columns:
        try:
            b["Date"] = b["Date"].dt.tz_localize(None)
        except Exception:
            pass
        b["Date"] = b["Date"].dt.normalize()
    
    # Normalize keys
    if "bet_Team" in b.columns:
        b["team_key"] = normalize_key(b["bet_Team"])
    else:
        b["team_key"] = ""
    if "bet_Opponent" in b.columns:
        b["opp_key"] = normalize_key(b["bet_Opponent"])
    else:
        b["opp_key"] = ""
    
    # Coerce numerics where applicable
    numeric_cols = [
        "bet_spread", "bet_ats_margin", "bet_total", 
        "bet_combined", "bet_ou_margin", "bet_moneyline", "bet_mov"
    ]
    for c in numeric_cols:
        if c in b.columns:
            b[c] = pd.to_numeric(b[c], errors="coerce")
    
    # Build a deterministic, de-duplicated keep list
    mapped_vals = [v for v in BET_COLS_MAP.values() if v in b.columns]
    mapped_vals = [v for v in mapped_vals if v not in {"Date", "team_key", "opp_key"}]
    keep = ["Date", "team_key", "opp_key"] + mapped_vals
    keep = list(dict.fromkeys([c for c in keep if c in b.columns]))
    
    b = b.loc[:, keep].copy()
    return b


def reduce_betting(b: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse to one row per game (Date, team_key, opp_key), taking last non-null 
    for bet_* columns. Drops rows with missing Date/team_key/opp_key.
    """
    if b.empty:
        return b
    
    b = b.copy()
    
    # Parse date and build day-only key
    b["Date"] = pd.to_datetime(b["Date"], errors="coerce")
    b["_DateKey"] = b["Date"].dt.date
    
    # Normalize and trim keys, drop unusable rows
    for k in ("team_key", "opp_key"):
        if k not in b.columns:
            b[k] = ""
        b[k] = b[k].astype(str).str.strip()
    
    # Keep only rows with complete merge keys
    b = b.dropna(subset=["_DateKey"]).loc[
        (b["team_key"] != "") & (b["opp_key"] != "")
    ].copy()
    
    if b.empty:
        return b.assign(Date=pd.to_datetime(pd.Series([], dtype="datetime64[ns]")))
    
    grp = ["_DateKey", "team_key", "opp_key"]
    
    def last_non_null(s: pd.Series):
        s = s.dropna()
        return s.iloc[-1] if not s.empty else pd.NA
    
    agg = {}
    for c in b.columns:
        if c in grp or c == "Date":
            continue
        if c.startswith("bet_"):
            agg[c] = last_non_null
        else:
            agg[c] = lambda s: s.dropna().iloc[0] if s.dropna().size else pd.NA
    
    out = b.groupby(grp, as_index=False).agg(agg)
    
    # Restore Date from key at midnight
    out["Date"] = pd.to_datetime(out["_DateKey"], errors="coerce")
    out = out.drop(columns=["_DateKey"], errors="ignore")
    
    # Final guard: enforce strict uniqueness
    dup_mask = out.duplicated(subset=["Date", "team_key", "opp_key"], keep=False)
    if dup_mask.any():
        out = (
            out.sort_values(["Date", "team_key", "opp_key"])
               .drop_duplicates(subset=["Date", "team_key", "opp_key"], keep="last")
        )
    
    return out.reset_index(drop=True)


def load_torvik_ratings() -> pd.DataFrame:
    """Load daily Bart Torvik ratings and normalize keys/dates."""
    path = TORVIK_DAILY_PATH
    if not path.exists():
        raise FileNotFoundError(str(path))

    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=["team_key", "Date", *TORVIK_FEATURE_COLS])

    date_col = "as_of_date" if "as_of_date" in df.columns else None
    if date_col is None:
        raise ValueError("Torvik ratings file must include an 'as_of_date' column")

    df["Date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["Date"] = df["Date"].dt.normalize()
    df["Date"] = df["Date"] + pd.Timedelta(days=1)
    df["team_key"] = normalize_key(df["team"])

    keep_cols = ["team_key", "Date"]
    for col in TORVIK_FEATURE_COLS:
        if col in df.columns:
            keep_cols.append(col)
            df[col] = pd.to_numeric(df[col], errors="coerce")

    out = df[keep_cols].dropna(subset=["team_key", "Date"]).copy()
    out = out.drop_duplicates(subset=["team_key", "Date"], keep="last")
    return out.reset_index(drop=True)
