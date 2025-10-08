"""
Rolling statistics and feature engineering for team performance metrics.
"""
import pandas as pd
import numpy as np
from utils import parse_dates, normalize_key, standardize_opponent_columns


def prepare_rolling(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute rolling averages and advanced metrics for teams.
    Returns DataFrame with team_*_roll and opp_*_roll columns.
    """
    df = df.copy()
    df = standardize_opponent_columns(df)

    df["Date"] = parse_dates(df["Date"])
    try:
        df["Date"] = df["Date"].dt.tz_localize(None)
    except Exception:
        pass
    df["Date"] = df["Date"].dt.normalize()
    
    df = df.dropna(subset=["Date", "Team", "Opp"])
    
    # Numeric conversion (remove % signs)
    for c in df.columns:
        if df[c].dtype == "object":
            try:
                df[c] = pd.to_numeric(df[c].str.replace("%", "", regex=False))
            except Exception:
                pass
    
    # Normalize keys
    df["team_key"] = normalize_key(df["Team"])
    df["opp_key"] = normalize_key(df["Opp"])
    
    # Sort games chronologically by team
    df["RowID"] = np.arange(len(df))
    df = df.sort_values(["team_key", "Date", "RowID"]).reset_index(drop=True)
    df["prior_games"] = df.groupby("team_key").cumcount()
    
    # Compute basic rolling stats
    df = _compute_basic_rolling_stats(df)
    
    # Compute rolling win% and SOS
    df = _compute_win_pct_and_sos(df)
    
    # Compute rolling pace and efficiency metrics
    df = _compute_pace_and_efficiency(df)


    
    # Filter out games with insufficient data
    df = df[df["prior_games"] > 0].copy()

    # Only require core opponent/team roll stats to be present; keep other
    # advanced metrics even if they still have gaps early in the season.
    required_cols = [
        "team_points_roll",
        "opp_points_roll",
        "team_winpct_roll",
        "opp_winpct_roll",
        "team_SOS_roll",
        "opp_SOS_roll",
    ]
    required_cols = [c for c in required_cols if c in df.columns]
    if required_cols:
        df = df.dropna(subset=required_cols)

    df = df.reset_index(drop=True)

    return df


def _compute_basic_rolling_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute rolling averages for basic box score stats."""
    # Choose numeric stats for rolling
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    stat_cols = [
        c for c in num_cols
        if not c.endswith(".1")
        and not c.startswith("opp_")
        and c not in ["RowID", "prior_games", "Gtm", "win_flag"]
    ]
    
    # Compute rolling averages (shifted by 1 to avoid leakage)
    roll = (
        df.groupby("team_key")[stat_cols]
          .expanding()
          .mean()
          .reset_index(level=0, drop=True)
          .shift(1)
    )
    roll.columns = [f"team_{c}_roll" for c in roll.columns]
    roll = roll.rename(columns={"team_Tm_roll": "team_points_roll"})
    
    # ADD rolling stats directly to df
    for col in roll.columns:
        df[col] = roll[col]
    
    # Now add opponent rolling stats via vectorized merge
    temp = df[["team_key", "Date"] + list(roll.columns)].copy()
    temp = temp.rename(columns={"team_key": "opp_key"})
    for col in roll.columns:
        temp = temp.rename(columns={col: col.replace("team_", "opp_")})
    
    df = df.merge(temp, on=["opp_key", "Date"], how="left")
    
    return df


def _compute_win_pct_and_sos(df: pd.DataFrame) -> pd.DataFrame:
    """Compute rolling win percentage and strength of schedule."""
    # Compute win flag
    opp_score_col = None
    if "opp_score" in df.columns:
        opp_score_col = "opp_score"
    elif "Opp.1" in df.columns:
        opp_score_col = "Opp.1"

    if "Tm" in df.columns and opp_score_col:
        df["Tm"] = pd.to_numeric(df["Tm"], errors="coerce")
        df[opp_score_col] = pd.to_numeric(df[opp_score_col], errors="coerce")
        if opp_score_col != "opp_score":
            df["opp_score"] = df[opp_score_col]
            opp_score_col = "opp_score"
        win_flag = (df["Tm"] > df[opp_score_col]).astype(float)
    else:
        win_flag = pd.Series(np.nan, index=df.index)
    win_flag.name = "win_flag"
    df["win_flag"] = win_flag
    
    # Team rolling win% (shifted to avoid leakage)
    team_winpct_roll = (
        df.groupby("team_key")["win_flag"]
          .expanding()
          .mean()
          .reset_index(level=0, drop=True)
          .shift(1)
    )
    df["team_winpct_roll"] = team_winpct_roll
    
    # Opponent rolling win% - use a dict lookup instead of map
    # Build dict: (team_key, Date) -> team_winpct_roll
    winpct_dict = df.set_index(["team_key", "Date"])["team_winpct_roll"].to_dict()
    
    # Look up opponent's win% using their key and date
    df["opp_winpct_roll"] = df.apply(
        lambda row: winpct_dict.get((row["opp_key"], row["Date"]), np.nan),
        axis=1
    )
    
    # Team SOS: rolling average of opponent win%
    df["team_SOS_roll"] = (
        df.groupby("team_key")["opp_winpct_roll"]
          .expanding()
          .mean()
          .reset_index(level=0, drop=True)
          .shift(1)
    )
    
    # Opponent SOS - dict lookup
    sos_dict = df.set_index(["team_key", "Date"])["team_SOS_roll"].to_dict()
    df["opp_SOS_roll"] = df.apply(
        lambda row: sos_dict.get((row["opp_key"], row["Date"]), np.nan),
        axis=1
    )
    df["delta_SOS_roll"] = df["team_SOS_roll"] - df["opp_SOS_roll"]
    
    return df


def _compute_pace_and_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    """Compute rolling pace and offensive/defensive efficiency metrics."""
    # Rolling Pace (possessions per game, Oliver formula)
    team_req = ["team_FGA_roll", "team_FTA_roll", "team_ORB_roll", "team_TOV_roll"]
    opp_req = ["opp_FGA_roll", "opp_FTA_roll", "opp_ORB_roll", "opp_TOV_roll"]
    
    if all(c in df.columns for c in team_req):
        df["team_pace_roll"] = (
            df["team_FGA_roll"] + 0.44 * df["team_FTA_roll"] - 
            df["team_ORB_roll"] + df["team_TOV_roll"]
        )
    else:
        df["team_pace_roll"] = np.nan
    
    if all(c in df.columns for c in opp_req):
        df["opp_pace_roll"] = (
            df["opp_FGA_roll"] + 0.44 * df["opp_FTA_roll"] - 
            df["opp_ORB_roll"] + df["opp_TOV_roll"]
        )
    else:
        df["opp_pace_roll"] = np.nan
    
    if "team_pace_roll" in df.columns and "opp_pace_roll" in df.columns:
        df["delta_pace_roll"] = df["team_pace_roll"] - df["opp_pace_roll"]
    
    # Rolling Offensive/Defensive Efficiency (per 100 possessions)
    have_team_poss = all(c in df.columns for c in team_req) and ("team_points_roll" in df.columns)
    have_opp_poss = all(c in df.columns for c in opp_req) and ("opp_points_roll" in df.columns)
    
    if have_team_poss:
        team_poss = (
            df["team_FGA_roll"] + 0.44 * df["team_FTA_roll"] - 
            df["team_ORB_roll"] + df["team_TOV_roll"]
        )
        team_poss = team_poss.where(team_poss > 0)
    else:
        team_poss = pd.Series(np.nan, index=df.index)
    
    if have_opp_poss:
        opp_poss = (
            df["opp_FGA_roll"] + 0.44 * df["opp_FTA_roll"] - 
            df["opp_ORB_roll"] + df["opp_TOV_roll"]
        )
        opp_poss = opp_poss.where(opp_poss > 0)
    else:
        opp_poss = pd.Series(np.nan, index=df.index)
    
    # Efficiency metrics
    df["team_off_eff_roll"] = (df.get("team_points_roll") / team_poss) * 100
    df["team_def_eff_roll"] = (df.get("opp_points_roll") / team_poss) * 100
    df["opp_off_eff_roll"] = (df.get("opp_points_roll") / opp_poss) * 100
    df["opp_def_eff_roll"] = (df.get("team_points_roll") / opp_poss) * 100
    
    return df


def _compute_matchup_features(df: pd.DataFrame) -> pd.DataFrame:
    """Expected performance based on offensive/defensive matchups"""
    
    # ===== Core matchup quality =====
    if "team_adj_o" in df.columns and "opp_adj_d" in df.columns:
        # Your offense vs their defense (points per 100 poss advantage)
        df["team_offensive_matchup"] = df["team_adj_o"] - df["opp_adj_d"]
    
    if "opp_adj_o" in df.columns and "team_adj_d" in df.columns:
        # Their offense vs your defense (points per 100 poss disadvantage)
        df["team_defensive_matchup"] = df["opp_adj_o"] - df["team_adj_d"]
    
    # Net advantage
    if "team_offensive_matchup" in df.columns and "team_defensive_matchup" in df.columns:
        df["team_matchup_advantage"] = (
            df["team_offensive_matchup"] - df["team_defensive_matchup"]
        )
    
    # ===== Expected points (if you have pace) =====
    if all(c in df.columns for c in ["team_pace_roll", "opp_pace_roll"]):
        df["expected_possessions"] = (df["team_pace_roll"] + df["opp_pace_roll"]) / 2
        
        if "team_adj_o" in df.columns:
            df["team_expected_points"] = (
                df["team_adj_o"] * (df["expected_possessions"] / 100)
            )
        
        if "opp_adj_o" in df.columns:
            df["opp_expected_points"] = (
                df["opp_adj_o"] * (df["expected_possessions"] / 100)
            )
        
        if "team_expected_points" in df.columns and "opp_expected_points" in df.columns:
            df["pregame_margin_projection"] = df["team_expected_points"] - df["opp_expected_points"]
            df["pregame_total_projection"] = df["team_expected_points"] + df["opp_expected_points"]
    
    return df




