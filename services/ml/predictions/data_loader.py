# data_loader.py
"""Load and preprocess game data."""
import os
import re
import pandas as pd
from config import TRAIN_CONFIG

def normalize_name(name: str) -> str:
    """
    Lowercase and remove all non-alphanumeric characters.
    Examples:
      "North Carolina A&T" -> "northcarolinaat"
      "Saint Mary's"       -> "saintmarys"
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    return re.sub(r'[^a-z0-9]', '', str(name).lower())

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
    out["date"] = pd.to_datetime(out.get("Date"), errors="coerce")

    # Normalized IDs for building a safe game_id (lowercase, no spaces/punct)
    team_id = out.get("Team", "").astype(str).apply(normalize_name)
    opp_id  = out.get("Opp",  "").astype(str).apply(normalize_name)

    # Create stable, normalized game identifier (safe for Firestore/doc IDs)
    out["game_id"] = team_id + "_vs_" + opp_id + "_" + out["date"].dt.strftime("%Y%m%d")

    # Team A/B (A = row team, B = opponent) — keep original display names
    out["team_A"] = out.get("Team")
    out["team_B"] = out.get("Opp")
    
    # Parse scores (allow either column names you might have)
    # Prefer explicit 'team_score'/'opp_score' if already present; otherwise try common sources
    if "team_score" not in out.columns:
        out["team_score"] = pd.to_numeric(out.get("Tm"), errors="coerce")
    if "opp_score" not in out.columns:
        # Some datasets use 'Opp.1' or 'opp_score'
        cand = "Opp.1" if "Opp.1" in out.columns else "opp_score"
        out["opp_score"] = pd.to_numeric(out.get(cand), errors="coerce")

    out["pts_A"] = pd.to_numeric(out["team_score"], errors="coerce")
    out["pts_B"] = pd.to_numeric(out["opp_score"], errors="coerce")
    
    # Remove rows with missing scores
    valid = out["pts_A"].notna() & out["pts_B"].notna()
    removed = len(out) - valid.sum()
    out = out.loc[valid].copy()
    
    print(f"Removed {removed} rows with missing scores")
    print(f"Rows after filtering: {len(out)}")
    
    return out