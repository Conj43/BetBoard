
from datetime import timedelta
from datetime import datetime, timezone
################################################################################
# Firebase / GCP
################################################################################

# GCP project / Firebase project info
GCP_PROJECT_ID = "betboardtest"  # TODO: set to your actual Firebase project id
FIREBASE_STORAGE_BUCKET = "betboardtest.firebasestorage.app"  # from screenshot
FIRESTORE_PREDICTIONS_COLLECTION = "predictions"

# Service account / creds:
# In Cloud Run or Cloud Functions you’ll probably rely on workload identity.
# Locally you may point GOOGLE_APPLICATION_CREDENTIALS at your JSON key.
# We don't hardcode here, but scripts should rely on env/auth being already set.


################################################################################
# Storage layout (Firebase Storage = GCS bucket)
################################################################################
# This is the canonical folder structure in your bucket. All jobs should use
# these helpers instead of making up paths.

# Raw ingest outputs (snapshotted daily):
#   gs://<bucket>/raw_data/games/2025-10-28/games.csv
#   gs://<bucket>/raw_data/team_snapshots/2025-10-28/teams.csv
#   gs://<bucket>/raw_data/odds/2025-10-28/odds.csv
RAW_DATA_PREFIX = "raw_data"
RAW_GAMES_PREFIX = f"{RAW_DATA_PREFIX}/games"
RAW_TEAMS_PREFIX = f"{RAW_DATA_PREFIX}/team_snapshots"
RAW_ODDS_PREFIX = f"{RAW_DATA_PREFIX}/odds"
RAW_TORVIK_PREFIX = f"{RAW_DATA_PREFIX}/torvik_rankings"  # you already have this
RAW_RESULTS_PREFIX = f"{RAW_DATA_PREFIX}/results"



# Processed, model-ready features:
#   gs://<bucket>/processed_features/2025-10-28/features.csv
PROCESSED_FEATURES_PREFIX = "processed_features"

# Model artifacts:
#   gs://<bucket>/model_runs/run_2025_10_28/spread_model.pkl
#   gs://<bucket>/model_runs/run_2025_10_28/total_model.pkl
#   gs://<bucket>/model_runs/run_2025_10_28/moneyline_model.pkl
MODEL_RUNS_PREFIX = "model_runs"

# Output predictions we also want to keep historically (for auditing, backtests)
#   gs://<bucket>/predictions_export/2025-10-28/top_picks.json
#   gs://<bucket>/predictions_export/2025-10-28/game_preds.json
PREDICTIONS_EXPORT_PREFIX = "predictions_export"

def raw_results_path(date_str: str) -> str:
    return f"{RAW_RESULTS_PREFIX}/{date_str}/results.csv"

def raw_games_path(date_str: str) -> str:
    return f"{RAW_GAMES_PREFIX}/{date_str}/games.csv"


def raw_teams_path(date_str: str) -> str:
    return f"{RAW_TEAMS_PREFIX}/{date_str}/teams.csv"


def raw_odds_path(date_str: str) -> str:
    return f"{RAW_ODDS_PREFIX}/{date_str}/odds.csv"


def processed_features_path(date_str: str) -> str:
    return f"{PROCESSED_FEATURES_PREFIX}/{date_str}/features.csv"


def predictions_export_game_preds_path(date_str: str) -> str:
    return f"{PREDICTIONS_EXPORT_PREFIX}/{date_str}/game_preds.json"


def predictions_export_top_picks_path(date_str: str) -> str:
    return f"{PREDICTIONS_EXPORT_PREFIX}/{date_str}/top_picks.json"

def predictions_export_graded_picks_path(date_str: str) -> str:
    return f"{PREDICTIONS_EXPORT_PREFIX}/{date_str}/graded_picks.json"

def predictions_export_summary_path(date_str: str) -> str:
    return f"{PREDICTIONS_EXPORT_PREFIX}/{date_str}/summary.json"


def model_run_dir(run_id: str) -> str:
    # run_id example: "run_2025_10_28"
    return f"{MODEL_RUNS_PREFIX}/{run_id}"


def model_path_spread(run_id: str) -> str:
    return f"{model_run_dir(run_id)}/spread_model.pkl"


def model_path_total(run_id: str) -> str:
    return f"{model_run_dir(run_id)}/total_model.pkl"


def model_path_moneyline(run_id: str) -> str:
    return f"{model_run_dir(run_id)}/moneyline_model.pkl"


# Which run is "active" for live predictions?
ACTIVE_MODEL_RUN_ID = "run_2025_10_28"  # TODO update as you retrain


################################################################################
# Business logic thresholds / knobs
################################################################################

# How far ahead you ingest schedules/lines/etc.
# For MVP: 0 days (today only). Then expand to 7.
INGEST_LOOKAHEAD_DAYS = 0  # later you can bump this to 7

# Edge thresholds for betting recs:
MIN_EDGE_SPREAD_PTS = 1.5   # e.g. we only show a spread bet if model vs book differs by >=1.5 pts
MIN_EDGE_TOTAL_PTS = 3.0    # totals are noisy, usually need bigger edge
MIN_PROB_EDGE = 0.05        # 5+ percentage point value on a moneyline

# Max cards to surface in the app:
MAX_PICKS_TO_PUBLISH = 10

# How far in the future we show upcoming games in Firestore even if
# we don't have a pick yet.
FRONTEND_LOOKAHEAD_DAYS = 7


################################################################################
# Feature / model contract
################################################################################

# This list is CRITICAL.
# It must match the columns your models expect at inference.
# build_features.py will output extra columns, but before prediction
# you MUST select these in this exact order.
#
# TODO: Fill this from your actual training code.
FEATURE_COLS_ORDER = [
    # "Conference",
    # "OppConference",
    # "Location",
    # "off_efficiency",
    # "def_efficiency",
    # "tempo",
    # "off_reb_rate",
    # "def_reb_rate",
    # "tov_rate",
    # "opp_off_efficiency",
    # ...
    # "bet_spread_home",
    # "bet_total",
    # "moneyline_home",
    # "moneyline_away",
]


################################################################################
# Firestore schema helpers
################################################################################

def firestore_doc_for_game_pred(game_pred: dict, picks_for_game: list) -> dict:
    """
    Given game-level prediction data and any picks we like for that game,
    build the Firestore document body we store at
    predictions/<DATE>/games/<game_id>.

    This is what the iOS app will read.
    """
    return {
        "game_id": game_pred["game_id"],
        "tipoff_datetime": game_pred.get("tipoff_datetime"),
        "home_team": game_pred.get("home_team"),
        "away_team": game_pred.get("away_team"),

        # sportsbook lines
        "book_spread_home": game_pred.get("book_spread_home"),
        "book_total": game_pred.get("book_total"),
        "moneyline_home": game_pred.get("moneyline_home"),
        "moneyline_away": game_pred.get("moneyline_away"),

        # model view of the matchup
        "model_spread_home": game_pred.get("model_spread_home"),
        "model_total": game_pred.get("model_total"),
        "home_win_prob": game_pred.get("home_win_prob"),

        # edges
        "spread_edge_points": game_pred.get("spread_edge_points"),
        "total_edge_points": game_pred.get("total_edge_points"),
        "moneyline_edge_home": game_pred.get("moneyline_edge_home"),
        "moneyline_edge_away": game_pred.get("moneyline_edge_away"),

        # recommended picks for this game, could be [], 1, or 2+
        "recommended": picks_for_game,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_run_id": ACTIVE_MODEL_RUN_ID,
    }