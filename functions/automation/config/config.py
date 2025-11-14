
import os
from pathlib import Path
from datetime import timedelta
from datetime import datetime, timezone
import re
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore

from automation.config.team_keys import (
    TEAM_MAPPING,
    CONFERENCE_MAP,
    canonicalize_team_key,
)

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"

# Firebase credentials (service account JSON)
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    "BETBOARD_FIREBASE_CREDENTIALS",
    str(BASE_DIR / "services" / "firebase" / "betboardtest-firebase-adminsdk-fbsvc-196904ba56.json"),
)
# GCP project / Firebase project info
GCP_PROJECT_ID = "betboardtest" 
FIREBASE_STORAGE_BUCKET = "betboardtest.firebasestorage.app" 
FIRESTORE_PREDICTIONS_COLLECTION = "games"

# cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
if not firebase_admin._apps:
    firebase_admin.initialize_app()
    db = firestore.client()
    doc_ref = db.collection('models').document('current_production')
    doc = doc_ref.get()

# if doc.exists:
#     _storage_model_version =  doc.to_dict().get('version')
# else:
_storage_model_version = "20251113_104120"


MODEL_DIR = f"models/{_storage_model_version}/no_bet"


BET_MODEL_DIR = f"models/{_storage_model_version}/with_bet"

RAW_DATA_PREFIX = "raw_data"
RAW_GAMES_PREFIX = f"{RAW_DATA_PREFIX}/games"
RAW_TEAMS_PREFIX = f"{RAW_DATA_PREFIX}/team_snapshots"
RAW_ODDS_PREFIX = f"{RAW_DATA_PREFIX}/odds"
RAW_TORVIK_PREFIX = f"{RAW_DATA_PREFIX}/torvik_rankings"
RAW_RESULTS_PREFIX = f"{RAW_DATA_PREFIX}/results"
GAMELOG_STORAGE_PREFIX = f"{RAW_DATA_PREFIX}/gamelogs"
SPORTS_REFERENCE_SEASON = "2026"


PROCESSED_FEATURES_PREFIX = "processed_features"

MODEL_RUNS_PREFIX = "model_runs"

PREDICTIONS_EXPORT_PREFIX = "predictions_export"

def raw_results_path(date_str: str) -> str:
    return f"{RAW_RESULTS_PREFIX}/{date_str}/results.csv"




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

def _resolve_team_key(name: Optional[str]) -> str:
    if not isinstance(name, str):
        return ""
    mapped = TEAM_MAPPING.get(name)
    if mapped:
        return canonicalize_team_key(mapped)
    return canonicalize_team_key(name)


def firestore_doc_for_game_pred(
    game_pred: dict,
    picks_for_game: list,
    torvik_ranks: Optional[dict[str, int]] = None,
) -> dict:
    """
    Given game-level prediction data and any picks we like for that game,
    build the Firestore document body we store at
    predictions/<DATE>/games/<game_id>.

    This is what the iOS app will read.
    """
    def _as_float(value):
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    game_date = game_pred.get("game_date")
    tipoff = game_pred.get("tipoff_datetime")
    home_team = game_pred.get("home_team")
    away_team = game_pred.get("away_team")
    home_conf = game_pred.get("home_conf") or game_pred.get("Conference")
    away_conf = game_pred.get("away_conf") or game_pred.get("OppConference")

    season = game_pred.get("season")

    tipoff_time = None
    tipoff_raw = game_pred.get("tipoff_datetime")
    if isinstance(tipoff_raw, str):
        match = re.search(r"T(\d{2}:\d{2})", tipoff_raw)
        if match:
            hh, mm = match.group(1).split(":")
            try:
                hour = int(hh)
                suffix = "AM"
                if hour == 0:
                    hour = 12
                elif hour == 12:
                    suffix = "PM"
                elif hour > 12:
                    hour -= 12
                    suffix = "PM"
                tipoff_time = f"{hour}:{mm} {suffix} CT"
            except ValueError:
                tipoff_time = match.group(1) + " CT"

    doc: dict = {
        "game_id": game_pred["game_id"],
        "date": game_date,
        "season": season or (str(game_date).split("-")[0] if game_date else None),
        "tipoff_time": tipoff_time,
        "home_team": home_team,
        "away_team": away_team,
        "home_conf": home_conf,
        "away_conf": away_conf,
        "neutral_site": bool(game_pred.get("is_neutral_site")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_run_id": ACTIVE_MODEL_RUN_ID,
    }

    # Moneyline block
    ml_home = _as_float(game_pred.get("moneyline_home"))
    ml_away = _as_float(game_pred.get("moneyline_away"))
    prob_home = _as_float(game_pred.get("home_win_prob"))
    moneyline: dict = {}
    if ml_home is not None:
        moneyline["odds_home"] = ml_home
    if ml_away is not None:
        moneyline["odds_away"] = ml_away
    if prob_home is not None:
        moneyline["p_win_home"] = prob_home
        moneyline["p_win_away"] = 1 - prob_home
        moneyline["predicted_winner"] = home_team if prob_home >= 0.5 else away_team
    if moneyline:
        doc["moneyline"] = moneyline

    # Spread block
    raw_spread_line = _as_float(game_pred.get("bet_spread_home"))
    spread_line = -raw_spread_line if raw_spread_line is not None else None
    predicted_margin = _as_float(game_pred.get("model_spread_home"))
    spread: dict = {}
    if spread_line is not None:
        spread["line"] = spread_line
    if predicted_margin is not None:
        spread["predicted_margin"] = predicted_margin
    if spread_line is not None and predicted_margin is not None:
        edge = predicted_margin - spread_line
        spread["edge"] = edge
        spread["pick"] = home_team if edge >= 0 else away_team
    if spread:
        doc["spread"] = spread

    # Total block
    total_line = _as_float(game_pred.get("bet_total"))
    predicted_total = _as_float(game_pred.get("model_total"))
    total: dict = {}
    if total_line is not None:
        total["line"] = total_line
    if predicted_total is not None:
        total["predicted_total"] = predicted_total
    if total_line is not None and predicted_total is not None:
        diff = predicted_total - total_line
        total["edge"] = diff
        total["pick"] = "OVER" if diff > 0 else "UNDER"
    if total:
        doc["total"] = total

    if torvik_ranks:
        home_key = _resolve_team_key(home_team)
        away_key = _resolve_team_key(away_team)

        home_rank = torvik_ranks.get(home_key)
        away_rank = torvik_ranks.get(away_key)

        if home_rank is not None:
            doc["torvik_home_rank"] = home_rank
        if away_rank is not None:
            doc["torvik_away_rank"] = away_rank

    if picks_for_game:
        doc["recommended"] = picks_for_game
    return doc




# Direct mapping for teams with unusual names or abbreviations
TORVIK_MAP = {
    "thecitadel": "citadel",
    "centralconnecticut": "central-connecticut-state",
    "ucriverside": "california-riverside",
    "texasa&mcorpuschris": "texas-am-corpus-christi",
    "grambling-state": "grambling",
    "tcu": "texas-christian",
    "saintfrancis": "saint-francis-pa",
    "loyolachicago": "loyola-il",
    "smu": "southern-methodist",
    "utsa": "texas-san-antonio",
    "charleston": "college-of-charleston",
    "purduefortwayne": "ipfw",
    "umasslowell": "massachusetts-lowell",
    "umkc": "missouri-kansas-city",
    "vcu": "virginia-commonwealth",
    "louisiana": "louisiana-lafayette",
    "vmi": "virginia-military-institute",
    "utahtech": "dixie-state",
    "uab": "alabama-birmingham",
    "n.c.state": "north-carolina-state",
    "ucirvine": "california-irvine",
    "calbaptist": "california-baptist",
    "saintmary's": "saint-marys-ca",
    "siuedwardsville": "southern-illinois-edwardsville",
    "st.john's": "st-johns-ny",
    "fiu": "florida-international",
    "umbc": "maryland-baltimore-county",
    "uncgreensboro": "north-carolina-greensboro",
    "utarlington": "texas-arlington",
    "ucsantabarbara": "california-santa-barbara",
    "ucf": "central-florida",
    "prairieviewa&m": "prairie-view",
    "queens": "queens-nc",
    "utriograndevalley": "texas-pan-american",
    "byu": "brigham-young",
    "unlv": "nevada-las-vegas",
    "ucsandiego": "california-san-diego",
    "houstonchristian": "houston-baptist",
    "ucdavis": "california-davis",
    "usc": "southern-california",
    "southernmiss": "southern-mississippi",
    "uncwilmington": "north-carolina-wilmington",
    "littlerock": "arkansas-little-rock",
    "lsu": "louisiana-state",
    "st.thomas": "st-thomas-mn",
    "liu": "long-island-university",
    "uncasheville": "north-carolina-asheville",
    "mount-statemary's": "mount-st-marys",
    "penn": "pennsylvania",
    "utep": "texas-el-paso",
}
