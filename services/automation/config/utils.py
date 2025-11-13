"""Utility functions for data normalization and key mapping."""
import re

import pandas as pd
import numpy as np

# Import TEAM_ALIASES - assumes name_map.py is in the same directory (ncaa_pipeline/)
from automation.config.config import (
    TEAM_MAPPING as TEAM_ALIASES,
    CONFERENCE_MAP,
    canonicalize_team_key,
)

# Global cache for alias map
_ALIAS_MAP_CACHE = None


def parse_dates(series: pd.Series) -> pd.Series:
    """
    Try multiple date formats and pick the one with the most valid parses.
    Returns timezone-naive dates normalized to midnight.
    """
    candidates = [
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%m/%d/%y",
        "%Y/%m/%d",
        "%d-%b-%y",
        "%d-%b-%Y",
    ]
    best = None
    best_ok = -1
    
    for fmt in candidates:
        dt = pd.to_datetime(series, format=fmt, errors="coerce")
        ok = dt.notna().sum()
        if ok > best_ok:
            best_ok, best = ok, dt
    
    if best_ok <= 0:
        # Fallback: let pandas infer
        best = pd.to_datetime(series, errors="coerce")
    
    # Ensure tz-naive and strip time-of-day for consistent joins
    try:
        best = best.dt.tz_localize(None)
    except Exception:
        pass
    
    return best.dt.normalize()


def slug(s: pd.Series) -> pd.Series:
    """Convert series to lowercase alphanumeric slugs."""
    return s.astype(str).str.lower().str.replace(r"[^a-z0-9]", "", regex=True)


def load_alias_map() -> dict[str, str]:
    """
    Return alias mappings using ONLY the static TEAM_ALIASES.
    Cached after first call.
    """
    global _ALIAS_MAP_CACHE
    
    if _ALIAS_MAP_CACHE is not None:
        return _ALIAS_MAP_CACHE
    
    def _slug(x: str) -> str:
        return "".join(ch for ch in str(x).lower() if ch.isalnum())
    
    alias: dict[str, str] = {}

    def _register(bet_key: str, canon_key: str, overwrite: bool = True) -> None:
        bk = _slug(bet_key)
        canonical = canonicalize_team_key(canon_key)
        if not bk or not canonical:
            return
        if not overwrite and bk in alias:
            return
        alias[bk] = canonical

    # Seed with canonical conference keys so slugs like "northcarolina"
    # always map back to "north-carolina".
    for teams in CONFERENCE_MAP.values():
        for canonical in teams:
            _register(canonical, canonical, overwrite=False)

    # Primary alias table takes precedence
    for bet_key, canon_key in TEAM_ALIASES.items():
        _register(bet_key, canon_key, overwrite=True)
    
    _ALIAS_MAP_CACHE = alias
    return _ALIAS_MAP_CACHE


def normalize_name(name: str) -> str:
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    return re.sub(r'[^a-z0-9]', '', str(name).lower())


def normalize_key(s: pd.Series) -> pd.Series:
    """Normalize team names to canonical keys using alias map."""
    alias = load_alias_map()
    sl = s.astype(str).str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
    return sl.map(lambda x: alias.get(x, canonicalize_team_key(x)))


def _normalize_stat_token(token: str) -> str:
    """Convert raw box score header tokens into snake_case identifiers."""
    token = token.replace("%", "_pct").replace("/", "_per_")
    token = re.sub(r"[^a-zA-Z0-9]+", "_", token.strip())
    token = re.sub(r"_+", "_", token).strip("_")
    return token.lower()


def standardize_opponent_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename duplicated opponent stat columns from ``*.1`` to ``opp_*`` names.

    Sports-Reference style game logs repeat each box score stat for the
    opponent, which pandas disambiguates as ``FG``, ``FG.1`` and so on.
    This helper renames those suffixed columns to clear ``opp_*`` labels while
    leaving the team columns untouched.
    """
    if not isinstance(df, pd.DataFrame):
        return df

    df = df.copy()
    rename_map: dict[str, str] = {}

    for col in df.columns:
        if not col.endswith(".1"):
            continue

        base = col[:-2]
        normalized = _normalize_stat_token(base)
        if not normalized:
            continue

        # Avoid creating ``opp_opp``; treat that column as the scoreboard.
        if normalized == "opp":
            normalized = "score"

        candidate = f"opp_{normalized}"
        # Skip if renaming would collide with an existing column
        if candidate in df.columns and candidate not in rename_map.values():
            continue

        rename_map[col] = candidate

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def ensure_bet_schema(df: pd.DataFrame, cols: list[str] = None) -> pd.DataFrame:
    """
    Ensure the provided betting columns exist in df.
    Adds missing columns as NaN. Returns a new DataFrame.
    """
    from automation.config.config import CANONICAL_BET_COLS
    if cols is None:
        cols = CANONICAL_BET_COLS
    
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan
    return out


def coalesce_merge_artifacts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Coalesce columns that may appear as *_x / *_y due to merges.
    Always prefer non-null values from _x, then _y, then base column.
    """
    cols = df.columns.tolist()
    suffix_bases = {}
    
    for c in cols:
        if c.endswith("_x") or c.endswith("_y"):
            base = c[:-2]
            suffix_bases.setdefault(base, set()).add(c)
    
    df = df.copy()
    for base, suffixed in suffix_bases.items():
        x = f"{base}_x"
        y = f"{base}_y"
        
        # Coalesce into base column
        if base not in df.columns:
            if x in df.columns and y in df.columns:
                df[base] = df[x].where(df[x].notna(), df[y])
            elif x in df.columns:
                df[base] = df[x]
            elif y in df.columns:
                df[base] = df[y]
        else:
            if x in df.columns:
                df[base] = df[base].where(df[base].notna(), df[x])
            if y in df.columns:
                df[base] = df[base].where(df[base].notna(), df[y])
        
        # Drop suffixed variants
        drop_list = [c for c in (x, y) if c in df.columns]
        if drop_list:
            df = df.drop(columns=drop_list)
    
    return df
