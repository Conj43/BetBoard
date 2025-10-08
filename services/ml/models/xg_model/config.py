# config.py
"""Configuration for CBB model training."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent.parent


TRAIN_CONFIG = {
    "mode": "seasonal",  # or "cutoff"
    "cutoff_date": "2024-10-01",
    "years": (2019, 2020, 2021, 2022, 2023, 2024, 2025),
    "data_dir": os.path.join(BASE_DIR, "data", "cleaned"),
    "output_dir": os.path.join(BASE_DIR, "data", "lgb_model"),
    "validation_split": 0.2,  # 20% of training data
    "xgb_output": os.path.join(BASE_DIR, "data", "xgb_model"),
}

LGBM_PARAMS = {
    "n_estimators": 2000,
    "learning_rate": 0.035,
    "max_depth": -1,
    "num_leaves": 63,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "reg_alpha": 0.1,
    "reg_lambda": 0.5,
    "random_state": 42,
    "n_jobs": -1,
}

# Feature exclusion rules
RAW_GAME_STATS = [
    "FG", "FGA", "FG%", "3P", "3PA", "3P%", "2P", "2PA", "2P%",
    "eFG%", "FT", "FTA", "FT%", "ORB", "DRB", "TRB", "AST",
    "STL", "BLK", "TOV", "PF",
]

OUTCOME_COLUMNS = [
    "team_score", "opp_score", "team_pts", "opp_pts",
    "pts_A", "pts_B", "margin_A", "total_pts", "home_win_A",
    "win", "margin", "total", "win_flag", "Rslt",
]

IDENTIFIER_COLUMNS = [
    "Team", "Opp", "Date", "Conference", "Type", "OT", "Gtm",
    "game_id", "game_key", "RowID", "team_key", "opp_key",
    "team_A", "team_B", "team_A_key", "team_B_key",
]

BETTING_OUTCOME_COLUMNS = [
    "bet_ats_margin", "bet_ou_margin", "bet_mov", 
    "bet_combined", "bet_Score",
]

BETTING_LINE_COLUMNS = [
    "bet_spread", "bet_total", "moneyline_a", "moneyline_b",
]