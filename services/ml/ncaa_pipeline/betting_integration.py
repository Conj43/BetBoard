"""
Betting line integration and diagnostic functions.
"""
import pandas as pd
import numpy as np
from config import DIRECTIONAL_BET_COLS, BET_DIR
from utils import parse_dates, slug


def merge_betting(labeled: pd.DataFrame, betting: pd.DataFrame) -> pd.DataFrame:
    """
    Merge betting lines onto per-team rows by (Date-only, team_key, opp_key).
    If direct match fails, try swapped keys and flip directional fields.
    """
    df = labeled.copy()
    b = betting.copy()
    
    # Deduplicate columns before any Date parsing
    if b.columns.duplicated().any():
        b = b.loc[:, ~b.columns.duplicated()].copy()
    
    # Handle multiple 'Date' columns
    if list(b.columns).count("Date") > 1:
        keep_cols = []
        seen_date = False
        for c in b.columns:
            if c == "Date":
                if not seen_date:
                    keep_cols.append(c)
                    seen_date = True
            else:
                keep_cols.append(c)
        b = b.loc[:, keep_cols].copy()
    
    # Parse dates safely
    _df_date = df["Date"] if "Date" in df.columns else pd.Series(pd.NaT, index=df.index)
    if isinstance(_df_date, pd.DataFrame):
        _df_date = _df_date.iloc[:, 0]
    df["Date"] = pd.to_datetime(_df_date, errors="coerce")
    
    _b_date = b["Date"] if "Date" in b.columns else pd.Series(pd.NaT, index=b.index)
    if isinstance(_b_date, pd.DataFrame):
        _b_date = _b_date.iloc[:, 0]
    b["Date"] = pd.to_datetime(_b_date, errors="coerce")
    
    # Create date-only keys for merging
    df["_DateKey"] = df["Date"].dt.date
    b["_DateKey"] = b["Date"].dt.date
    
    base = ["_DateKey", "team_key", "opp_key"]
    bet_cols = [c for c in b.columns if c not in (base + ["Date"])]
    bet_cols = list(dict.fromkeys(bet_cols))
    
    # Tag which side the moneyline applies to
    if "bet_moneyline" in b.columns:
        b["bet_moneyline_for"] = "team"
    if "bet_moneyline_for" in b.columns and "bet_moneyline_for" not in bet_cols:
        bet_cols.append("bet_moneyline_for")
    
    # Direct orientation merge
    m_dir = df.merge(b[base + bet_cols], on=base, how="left")
    
    # Swapped orientation (flip directional fields)
    b2 = b.rename(columns={"team_key": "opp_key", "opp_key": "team_key"}).copy()
    for c in DIRECTIONAL_BET_COLS:
        if c in b2.columns:
            b2[c] = -pd.to_numeric(b2[c], errors="coerce")
    if "bet_moneyline" in b2.columns:
        b2["bet_moneyline_for"] = "opp"
    
    m_sw = df.merge(b2[base + bet_cols], on=base, how="left")
    
    # Fill from swapped where direct is missing
    m_out = m_dir.copy()
    for c in bet_cols:
        if c in m_out.columns and c in m_sw.columns:
            m_out[c] = m_out[c].where(m_out[c].notna(), m_sw[c])
    
    # Moneyline: keep value + 0/1 indicator only
    if "bet_moneyline" in m_out.columns and "bet_moneyline_for" in m_out.columns:
        ind = m_out["bet_moneyline_for"].eq("team").astype(float)
        ind = ind.where(m_out["bet_moneyline"].notna(), np.nan)
        m_out["bet_moneyline_for_team"] = ind
        m_out = m_out.drop(columns=["bet_moneyline_for"], errors="ignore")
    
    return m_out.drop(columns=["_DateKey"], errors="ignore")


def extract_moneylines_per_game(
    betting_full: pd.DataFrame, 
    per_game: pd.DataFrame
) -> pd.DataFrame:
    """
    Extract moneylines from full betting data (both orientations) and attach
    to per-game dataframe as moneyline_a and moneyline_b.
    
    Filters out invalid moneylines:
    - -110.0 (standard juice/placeholder, not actual moneyline)
    - Any other invalid values
    """
    def last_non_null(s: pd.Series):
        s = s.dropna()
        return s.iloc[-1] if not s.empty else np.nan
    
    rb = betting_full.copy()
    
    # Ensure required columns exist
    need = {"Date", "team_key", "opp_key", "bet_moneyline"}
    if not need.issubset(set(rb.columns)):
        per_game["moneyline_a"] = np.nan
        per_game["moneyline_b"] = np.nan
        return per_game
    
    rb["Date"] = pd.to_datetime(rb["Date"], errors="coerce")
    rb["_d"] = rb["Date"].dt.strftime("%Y%m%d")
    
    # Build game_key
    a_key = np.where(rb["team_key"] <= rb["opp_key"], rb["team_key"], rb["opp_key"])
    b_key = np.where(rb["team_key"] <= rb["opp_key"], rb["opp_key"], rb["team_key"])
    rb["game_key"] = a_key + "_" + b_key + "_" + rb["_d"]
    rb["bet_moneyline"] = pd.to_numeric(rb["bet_moneyline"], errors="coerce")
    
    # FILTER OUT INVALID MONEYLINES
    # -110 is standard juice for spreads/totals, not a valid moneyline
    # Also filter out exactly +110 as it's likely the other side of the juice
    print(f"Before filtering: {rb['bet_moneyline'].notna().sum()} moneylines")
    
    invalid_mask = (
        (rb["bet_moneyline"] == -110.0) | 
        (rb["bet_moneyline"] == 110.0) |
        (rb["bet_moneyline"].isna())
    )
    
    rb.loc[invalid_mask, "bet_moneyline"] = np.nan
    
    print(f"After filtering -110/+110: {rb['bet_moneyline'].notna().sum()} moneylines")
    print(f"Filtered out: {invalid_mask.sum()} invalid moneylines")
    
    # Map moneyline to the actual row team
    ml_map = (
        rb.loc[:, ["game_key", "team_key", "bet_moneyline"]]
          .groupby(["game_key", "team_key"], as_index=False)["bet_moneyline"]
          .agg(last_non_null)
          .rename(columns={"bet_moneyline": "moneyline"})
    )
    
    # Merge MLs for Team and Opp
    per_game = per_game.merge(
        ml_map.rename(columns={"moneyline": "moneyline_a"}),
        on=["game_key", "team_key"], 
        how="left"
    )
    per_game = per_game.merge(
        ml_map.rename(columns={"team_key": "opp_key", "moneyline": "moneyline_b"}),
        on=["game_key", "opp_key"], 
        how="left"
    )
    
    # Additional safety: if EITHER moneyline is -110/+110, set BOTH to NaN
    # This ensures we don't have half-valid games
    if "moneyline_a" in per_game.columns and "moneyline_b" in per_game.columns:
        invalid_games = (
            (per_game["moneyline_a"] == -110.0) | 
            (per_game["moneyline_a"] == 110.0) |
            (per_game["moneyline_b"] == -110.0) | 
            (per_game["moneyline_b"] == 110.0)
        )
        
        games_to_invalidate = invalid_games.sum()
        if games_to_invalidate > 0:
            print(f"Setting both moneylines to NaN for {games_to_invalidate} games with -110/+110")
            per_game.loc[invalid_games, ["moneyline_a", "moneyline_b"]] = np.nan
    
    # Report final stats
    if "moneyline_a" in per_game.columns and "moneyline_b" in per_game.columns:
        valid_games = (
            per_game["moneyline_a"].notna() & 
            per_game["moneyline_b"].notna()
        ).sum()
        print(f"Final valid games with both moneylines: {valid_games} / {len(per_game)}")
    
    return per_game