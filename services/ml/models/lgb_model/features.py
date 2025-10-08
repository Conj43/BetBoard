# features.py
"""Feature engineering and validation."""
import pandas as pd
import numpy as np
from config import (
    RAW_GAME_STATS, OUTCOME_COLUMNS, IDENTIFIER_COLUMNS,
    BETTING_OUTCOME_COLUMNS, BETTING_LINE_COLUMNS
)

def build_features(df, include_betting_lines=False):
    """Extract features from processed dataframe."""
    df = df.copy()

    # --- Torvik-derived matchup features ---
    torvik_metrics = [
        ("barthag", True),
        ("adj_o", True),
        ("adj_d", True),
        ("rank", False),
    ]

    for metric, allow_ratio in torvik_metrics:
        team_col = f"team_{metric}"
        opp_col = f"opp_{metric}"

        if team_col not in df.columns or opp_col not in df.columns:
            continue

        diff_name = f"torvik_{metric}_diff"
        df[diff_name] = df[team_col] - df[opp_col]

        if allow_ratio:
            ratio_name = f"torvik_{metric}_ratio"
            denom = df[opp_col].replace({0: np.nan})
            df[ratio_name] = df[team_col] / denom

    
    # Build exclusion set
    exclude = set()
    exclude.update(OUTCOME_COLUMNS)
    exclude.update(IDENTIFIER_COLUMNS)
    exclude.update(BETTING_OUTCOME_COLUMNS)
    exclude.add("season")
    exclude.add("date")
    
    # Add raw game stat columns (both team and opponent)
    for stat in RAW_GAME_STATS:
        exclude.add(stat)  # Team version
        exclude.add(f"opp_{stat.lower()}")  # Opponent version
        exclude.add(f"opp_{stat.lower()}_pct")  # Opponent percentage version
    
    if not include_betting_lines:
        exclude.update(BETTING_LINE_COLUMNS)
    
    # Select numeric columns not in exclusion set
    feature_cols = []
    for col in df.columns:
        # Skip if in exclusion set
        if col in exclude:
            continue
        
        # Skip if not numeric
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        
        # Additional safety: check for raw stats by pattern
        col_upper = col.upper()
        if any(stat in col_upper for stat in RAW_GAME_STATS):
            # But allow if it's a rolling average
            if '_roll' not in col.lower():
                continue
        
        # Skip anything with forbidden keywords
        col_lower = col.lower()
        if any(word in col_lower for word in ['score', 'result', 'winner', 'rslt']):
            if '_roll' not in col_lower:  # Allow *_roll versions
                continue
        
        feature_cols.append(col)
    
    # Rest of the function stays the same...
    
    # Validate features
    _validate_no_leakage(feature_cols)
    
    # Build feature matrix
    X = df[feature_cols].copy()
    
    # Handle missing values
    print(f"Features with missing values:")
    missing = X.isna().sum()
    print(missing[missing > 0])
    
    # Drop rows with any NaN
    valid_rows = ~X.isna().any(axis=1)
    X = X.loc[valid_rows]
    
    # Extract targets and metadata
    y_pts = df[["pts_A", "pts_B"]].loc[valid_rows].copy()
    y_win = (df["pts_A"] > df["pts_B"]).astype(int).loc[valid_rows]
    
    meta_cols = ["game_id", "date", "team_A", "team_B", "season"]
    meta = df[meta_cols].loc[valid_rows].copy()
    
    # Extract betting lines for evaluation
    market_cols = [c for c in BETTING_LINE_COLUMNS if c in df.columns]
    market = df[market_cols].loc[valid_rows].copy() if market_cols else pd.DataFrame(index=X.index)
    
    print(f"\nFeature summary:")
    print(f"  Total features: {len(feature_cols)}")
    print(f"  Rolling features: {sum('_roll' in c for c in feature_cols)}")
    print(f"  Context features: {sum(c in ['is_home', 'is_neutral', 'is_conf_game'] for c in feature_cols)}")
    print(f"  Has prior_games: {'prior_games' in feature_cols}")
    print(f"  Valid rows: {len(X)} / {len(df)}")
    
    return X, y_pts, y_win, meta, market, feature_cols


def _validate_no_leakage(feature_cols):
    """Raise error if features contain leaked information."""
    
    # Check for raw game stats (not rolling averages)
    leaked_stats = []
    for stat in RAW_GAME_STATS:
        matches = [c for c in feature_cols if stat in c and '_roll' not in c.lower()]
        leaked_stats.extend(matches)
    
    if leaked_stats:
        raise ValueError(f"LEAKAGE: Raw game stats in features: {leaked_stats[:10]}")
    
    ALLOWED_EXCEPTIONS = ['pregame_margin_projection', 'pregame_total_projection']
    # Check for outcome columns
    leaked_outcomes = [c for c in feature_cols if any(
        outcome in c.lower() for outcome in 
        ['team_score', 'opp_score', 'team_pts', 'opp_pts', 'margin', 'total']
    ) and '_roll' not in c.lower() 
    and not any(exception in c for exception in ALLOWED_EXCEPTIONS)]
    
    if leaked_outcomes:
        raise ValueError(f"LEAKAGE: Outcome columns in features: {leaked_outcomes}")
    
    print("✓ No leakage detected in features")
