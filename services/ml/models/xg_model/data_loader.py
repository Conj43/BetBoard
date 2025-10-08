# data_loader.py
"""Load and preprocess game data."""
import os
import pandas as pd
from config import TRAIN_CONFIG

def load_game_data(years=None):
    """Load per-game CSV files and combine them."""
    if years is None:
        years = TRAIN_CONFIG["years"]
    
    data_dir = TRAIN_CONFIG["data_dir"]
    frames = []
    
    for year in years:
        path = os.path.join(data_dir, f"per_game_{year}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["season"] = year
            frames.append(df)
            print(f"Loaded {len(df)} games from {year}")
        else:
            print(f"Warning: {path} not found")
    
    if not frames:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    
    combined = pd.concat(frames, ignore_index=True)
    print(f"Total games loaded: {len(combined)}")
    return combined


def prepare_game_rows(df):
    """
    Prepare data with row-stable perspective (no sorting/swapping).
    Each row represents one team's view of a game.
    """
    out = df.copy()
    
    # Parse date
    out["date"] = pd.to_datetime(out["Date"])
    
    # Create stable game identifiers
    team_id = out["Team"].astype(str).str.strip().str.lower()
    opp_id = out["Opp"].astype(str).str.strip().str.lower()
    out["game_id"] = team_id + "_vs_" + opp_id + "_" + out["date"].dt.strftime("%Y%m%d")
    
    # Team A/B (A = row team, B = opponent)
    out["team_A"] = out["Team"]
    out["team_B"] = out["Opp"]
    
    # Parse scores
    out["pts_A"] = pd.to_numeric(out["team_score"], errors="coerce")
    out["pts_B"] = pd.to_numeric(out["opp_score"], errors="coerce")
    
    # Remove rows with missing scores
    valid = out["pts_A"].notna() & out["pts_B"].notna()
    removed = len(out) - valid.sum()
    out = out.loc[valid].copy()
    
    print(f"Removed {removed} rows with missing scores")
    print(f"Rows after filtering: {len(out)}")
    
    return out