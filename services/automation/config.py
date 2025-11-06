
import os
from pathlib import Path
from datetime import timedelta
from datetime import datetime, timezone

################################################################################
# Local paths
################################################################################

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

# Local staging directories for raw ingest, engineered features, and outputs.
RAW_DATA_DIR = os.environ.get("BETBOARD_RAW_DATA_DIR", str(DATA_DIR / "raw"))
PROCESSED_DATA_DIR = os.environ.get("BETBOARD_PROCESSED_DATA_DIR", str(DATA_DIR / "processed"))
PREDICTIONS_DIR = os.environ.get("BETBOARD_PREDICTIONS_DIR", str(DATA_DIR / "predictions"))

# Default model artifacts (can override via env BETBOARD_MODEL_DIR)
_default_model_run = os.environ.get("BETBOARD_LOCAL_MODEL_RUN", "No_Bet_xgb_all_models_20251104_160154")
_default_bet_model_run = os.environ.get("BETBOARD_LOCAL_BET_MODEL_RUN", "Bet_xgb_all_models_20251104_160047")
_storage_model_version = os.environ.get("BETBOARD_MODEL_VERSION", "current_production")
MODEL_DIR = os.environ.get(
    "BETBOARD_MODEL_DIR",
    f"models/{_storage_model_version}/no_bet",
)
MODEL_FALLBACK_LOCAL_DIR = str(DATA_DIR / "xgb_model" / _default_model_run / "models_production")
BET_MODEL_DIR = os.environ.get(
    "BETBOARD_BET_MODEL_DIR",
    f"models/{_storage_model_version}/with_bet",
)
BET_MODEL_FALLBACK_LOCAL_DIR = str(DATA_DIR / "xgb_model" / _default_bet_model_run / "models_production")

# Firebase credentials (service account JSON)
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    "BETBOARD_FIREBASE_CREDENTIALS",
    str(BASE_DIR / "services" / "firebase" / "betboardtest-firebase-adminsdk-fbsvc-196904ba56.json"),
)
################################################################################
# Firebase / GCP
################################################################################

# GCP project / Firebase project info
GCP_PROJECT_ID = "betboardtest"  # TODO: set to your actual Firebase project id
FIREBASE_STORAGE_BUCKET = "betboardtest.firebasestorage.app"  # from screenshot
FIRESTORE_PREDICTIONS_COLLECTION = "games"

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
    doc = {
        "game_id": game_pred["game_id"],
        "tipoff_datetime": game_pred.get("tipoff_datetime"),
        "home_team": game_pred.get("home_team"),
        "away_team": game_pred.get("away_team"),
        "model_spread_home": game_pred.get("model_spread_home"),
        "model_total": game_pred.get("model_total"),
        "home_win_prob": game_pred.get("home_win_prob"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_run_id": ACTIVE_MODEL_RUN_ID,
    }
    if picks_for_game:
        doc["recommended"] = picks_for_game
    return doc




# Direct mapping for teams with unusual names or abbreviations
TEAM_MAPPING = {
    "Rutgers Scarlet Knights":"rutgers",
    "Rider Broncs": "rider",
    "La Salle Explorers": "la-salle",
    "Coppin St Eagles": "coppin-state",
    "Butler Bulldogs": "butler",
    "Southern Indiana Screaming Eagles": "southern-indiana",
    "Temple Owls": "temple",
    "Delaware St Hornets" : "delaware-state",
    "Georgia Bulldogs": "georgia",
    "Maryland-Eastern Shore Hawks": "maryland-eastern-shore",
    "Indiana Hoosiers": "indiana",
    "Alabama A&M Bulldogs": "alabama-am",
    "Creighton Bluejays": "creighton",
    "South Dakota Coyotes": "south-dakota",
    "LSU Tigers": "louisiana-state",
    "Tarleton State Texans": "tarleton-state",
    "Marquette Golden Eagles": "marquette",
    "Southern Jaguars": "southern",
    "New Mexico Lobos": "new-mexico",
    "East Texas A&M Lions": "texas-am-commerce",
    "Fresno St Bulldogs": "fresno-state",
    "South Carolina Upstate Spartans": "south-carolina-upstate",
    "Mississippi St Bulldogs": "mississippi-state",
    "North Alabama Lions": "north-alabama",
    "UC Davis Aggies": "california-davis",
    "North Dakota St Bison": "north-dakota-state",
    "Loyola Marymount Lions": "loyola-marymount",
    "Eastern Washington Eagles": "eastern-washington",
    "Miami Hurricanes": "miami-fl",
    "Bethune-Cookman Wildcats": "bethune-cookman",
    "Boston College Eagles": "boston-college",
    "The Citadel Bulldogs": "the-citadel",
    "West Virginia Mountaineers": "west-virginia",
    "Campbell Fighting Camels": "campbell",
    "Ohio Bobcats": "ohio",
    "Illinois St Redbirds": "illinois-state",
    "Louisville Cardinals": "louisville",
    "Jackson St Tigers": "jackson-state",
    "Iowa State Cyclones": "iowa-state",
    "Grambling St Tigers": "grambling-state",
    "Drake Bulldogs": "drake",
    "Robert Morris Colonials": "robert-morris",
    "Abilene Christian Wildcats": "abilene-christian",
    "Omaha Mavericks": "nebraska-omaha",
    "Auburn Tigers": "auburn",
    "Merrimack Warriors": "merrimack",
    "Northern Iowa Panthers": "northern-iowa",
    "CSU Northridge Matadors": "cal-state-northridge",
    "Florida Gators": "florida",
    "North Florida Ospreys": "north-florida",
    "North Dakota Fighting Hawks": "north-dakota",
    "UC Riverside Highlanders": "uc-riverside",
    "TCU Horned Frogs": "texas-christian",
    "St. Francis (PA) Red Flash": "saint-francis-pa",
    "Texas A&M Aggies": "texas-am",
    "Texas Southern Tigers": "texas-southern",
    "California Golden Bears": "california",
    "Wright St Raiders": "wright-state",
    "Washington Huskies": "washington",
    "Denver Pioneers": "denver",
    "North Carolina Tar Heels": "north-carolina",
    "Kansas Jayhawks": "kansas",
    "St. John's Red Storm": "st-johns-ny",
    "Alabama Crimson Tide": "alabama",
    "Michigan St Spartans": "michigan-state",
    "Arkansas Razorbacks": "arkansas",
    "Gonzaga Bulldogs": "gonzaga",
    "Oklahoma Sooners": "oklahoma",
}



CONFERENCE_MAP = {
    "ACC": ["duke", "louisville", "clemson", "wake-forest", "north-carolina", "southern-methodist", "stanford", "georgia-tech", "virginia-tech", "florida-state", "virginia", "notre-dame", "pittsburgh", "syracuse", "california", "north-carolina-state", "boston-college", "miami-fl"],
    "America East": ["bryant", "vermont", "maine", "albany-ny", "binghamton", "massachusetts-lowell", "new-hampshire", "maryland-baltimore-county", "njit"],
    "American": ["memphis", "north-texas", "alabama-birmingham", "tulane", "east-carolina", "florida-atlantic", "temple", "wichita-state", "south-florida", "tulsa", "texas-san-antonio", "rice", "charlotte"],
    "ASUN": ["lipscomb", "north-alabama", "florida-gulf-coast", "jacksonville", "eastern-kentucky", "queens-nc", "north-florida", "austin-peay", "stetson", "central-arkansas", "west-georgia", "bellarmine"],
    "Atlantic 10": ["virginia-commonwealth", "george-mason", "loyola-il", "dayton", "saint-josephs", "saint-louis", "st-bonaventure", "george-washington", "duquesne", "rhode-island", "massachusetts", "davidson", "la-salle", "richmond", "fordham"],
    "SEC": ["auburn", "florida", "alabama", "tennessee", "texas-am", "mississippi", "kentucky", "missouri", "arkansas", "mississippi-state", "georgia", "vanderbilt", "oklahoma", "texas", "louisiana-state", "south-carolina"],
    "Big Ten": ["michigan-state", "maryland", "michigan", "wisconsin", "purdue", "ucla", "illinois", "oregon", "indiana", "ohio-state", "rutgers", "minnesota", "northwestern", "southern-california", "iowa", "nebraska", "penn-state", "washington"],
    "Big 12": ["houston", "texas-tech", "brigham-young", "arizona", "iowa-state", "kansas", "baylor", "west-virginia", "texas-christian", "kansas-state", "utah", "cincinnati", "central-florida", "oklahoma-state", "arizona-state", "colorado"],
    "Big East": ["st-johns-ny", "creighton", "connecticut", "marquette", "xavier", "villanova", "georgetown", "butler", "providence", "depaul", "seton-hall"],
    "West Coast": ["saint-marys-ca", "gonzaga", "san-francisco", "santa-clara", "oregon-state", "washington-state", "loyola-marymount", "portland", "pepperdine", "pacific", "san-diego"],
    "Big Sky": ["northern-colorado", "montana", "portland-state", "idaho-state", "montana-state", "northern-arizona", "idaho", "eastern-washington", "weber-state", "sacramento-state"],
    "Big South": ["high-point", "winthrop", "north-carolina-asheville", "radford", "longwood", "presbyterian", "charleston-southern", "gardner-webb", "south-carolina-upstate"],
    "Big West": ["california-san-diego", "california-irvine", "cal-state-northridge", "california-riverside", "california-santa-barbara", "california-davis", "cal-poly", "cal-state-bakersfield", "hawaii", "long-beach-state", "cal-state-fullerton"],
    "CAA": ["towson", "north-carolina-wilmington", "college-of-charleston", "william-mary", "campbell", "monmouth", "drexel", "northeastern", "elon", "hampton", "hofstra", "delaware", "stony-brook", "north-carolina-at"],
    "CUSA": ["liberty", "middle-tennessee", "jacksonville-state", "kennesaw-state", "new-mexico-state", "louisiana-tech", "western-kentucky", "texas-el-paso", "sam-houston-state", "florida-international"],
    "Horizon": ["robert-morris", "milwaukee", "cleveland-state", "youngstown-state", "ipfw", "northern-kentucky", "oakland", "wright-state", "iupui", "detroit-mercy", "green-bay"],
    "Ivy League": ["yale", "cornell", "princeton", "dartmouth", "harvard", "brown", "pennsylvania", "columbia"],
    "MAAC": ["quinnipiac", "merrimack", "marist", "mount-st-marys", "manhattan", "iona", "sacred-heart", "siena", "rider", "fairfield", "saint-peters", "niagara", "canisius"],
    "MAC": ["akron", "miami-oh", "kent-state", "toledo", "ohio", "eastern-michigan", "bowling-green-state", "central-michigan", "ball-state", "buffalo", "northern-illinois"],
    "MEAC": ["norfolk-state", "south-carolina-state", "delaware-state", "morgan-state", "howard", "north-carolina-central", "coppin-state", "maryland-eastern-shore"],
    "Mountain West": ["new-mexico", "colorado-state", "utah-state", "boise-state", "san-diego-state", "nevada-las-vegas", "nevada", "san-jose-state", "wyoming", "fresno-state", "air-force"],
    "MVC": ["drake", "bradley", "northern-iowa", "belmont", "illinois-state", "illinois-chicago", "murray-state", "indiana-state", "southern-illinois", "evansville", "valparaiso", "missouri-state"],
    "NEC": ["central-connecticut-state", "long-island-university", "mercyhurst", "saint-francis-pa", "fairleigh-dickinson", "stonehill", "wagner", "le-moyne", "chicago-state"],
    "OVC": ["southeast-missouri-state", "southern-illinois-edwardsville", "arkansas-little-rock", "tennessee-state", "lindenwood", "tennessee-state", "morehead-state", "tennessee-martin", "eastern-illinois", "western-illinois", "southern-indiana"],
    "Patriot": ["american", "bucknell", "army", "boston-university", "navy", "colgate", "lafayette", "loyola-md", "lehigh", "holy-cross"],
    "SoCon": ["chattanooga", "north-carolina-greensboro", "samford", "east-tennessee-state", "furman", "wofford", "virginia-military-institute", "mercer", "western-carolina", "citadel"],
    "Southland": ["mcneese-state", "lamar", "nicholls-state", "texas-am-corpus-christi", "southeastern-louisiana", "northwestern-state", "incarnate-word", "houston-baptist", "texas-pan-american", "stephen-f-austin", "texas-am-commerce", "new-orleans"],
    "Summit League": ["nebraska-omaha", "st-thomas-mn", "south-dakota-state", "north-dakota-state", "south-dakota", "north-dakota", "denver", "missouri-kansas-city", "oral-roberts"],
    "Sun Belt": ["arkansas-state", "troy", "south-alabama", "james-madison", "marshall", "appalachian-state", "texas-state", "georgia-southern", "old-dominion", "georgia-state", "louisiana-lafayette", "southern-mississippi", "coastal-carolina", "louisiana-monroe"],
    "SWAC": ["southern", "jackson-state", "bethune-cookman", "alabama-state", "texas-southern", "alcorn-state", "florida-am", "grambling", "alabama-am", "prairie-view", "arkansas-pine-bluff", "mississippi-valley-state"],
    "WAC": ["utah-valley", "grand-canyon", "california-baptist", "abilene-christian", "seattle", "tarleton-state", "texas-arlington", "southern-utah", "dixie-state"]
}
