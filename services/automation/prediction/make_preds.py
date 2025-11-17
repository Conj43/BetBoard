import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional
from zoneinfo import ZoneInfo
import pandas as pd
from io import BytesIO, StringIO

try:
    import automation.config.config as _config
except ImportError:  # pragma: no cover
    _config = None


MODEL_DIR = getattr(_config, "MODEL_DIR", "models/current_production/no_bet")
BET_MODEL_DIR = getattr(_config, "BET_MODEL_DIR", "models/current_production/with_bet")
FIREBASE_CREDENTIALS_PATH = getattr(_config, "FIREBASE_CREDENTIALS_PATH", "")
FIREBASE_STORAGE_BUCKET = getattr(_config, "FIREBASE_STORAGE_BUCKET", "")
PROCESSED_FEATURES_PREFIX = getattr(_config, "PROCESSED_FEATURES_PREFIX", "processed_features")
CENTRAL_TZ = ZoneInfo("America/Chicago")




# We'll assume LightGBM/XGBoost-ish models were joblib'd.
# If you're using pickle or something else, tweak here.
try:
    import joblib
except ImportError:
    joblib = None  # TODO: make sure joblib is installed in prod env

try:
    import firebase_admin
    from firebase_admin import credentials, storage, firestore
except ImportError:  # pragma: no cover
    firebase_admin = None  # type: ignore
    credentials = None  # type: ignore
    storage = None  # type: ignore
    firestore = None  # type: ignore

_FIREBASE_BUCKET = None
_FIRESTORE_CLIENT = None
_MODEL_ARTIFACT_CACHE: Dict[str, Dict[str, bytes]] = {}


def _require_firebase_storage() -> None:
    """
    Ensure Firebase Admin SDK (with storage support) is available.
    """
    if firebase_admin is None or storage is None:
        raise RuntimeError(
            "firebase_admin with storage support is required to load models from Firebase Storage. "
            "Install firebase-admin and google-cloud-storage."
        )


# --- Helpers for implied probability from moneyline -------------------------

def implied_prob_from_moneyline(odds: float) -> float:
    """
    Convert American odds to implied win probability.
    Returns float in [0,1].
    """
    if odds is None:
        return None
    try:
        odds = float(odds)
    except (TypeError, ValueError):
        return None

    if odds < 0:
        # -135 -> 135 / (135+100)
        return (-odds) / ((-odds) + 100.0)
    else:
        # +115 -> 100 / (115+100)
        return 100.0 / (odds + 100.0)


# --- Load models ------------------------------------------------------------

def _load_xgb_model(artifacts: Dict[str, bytes], basename: str, model_type: str):
    """
    Load an XGBoost model saved either as a sklearn-style pickle or native JSON.
    """
    pkl_key = f"{basename}_model.pkl"
    json_key = f"{basename}_model.json"

    if pkl_key in artifacts:
        if joblib is None:
            raise RuntimeError(
                f"joblib is required to load {pkl_key} but is not installed."
            )
        return joblib.load(BytesIO(artifacts[pkl_key]))

    if json_key in artifacts:
        try:
            import xgboost as xgb  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "xgboost is required to load JSON model artifacts. "
                "Install xgboost or provide pickle models."
            ) from exc

        if model_type == "classifier":
            model = xgb.XGBClassifier()
        else:
            model = xgb.XGBRegressor()
        model.load_model(bytearray(artifacts[json_key]))
        return model

    raise FileNotFoundError(
        f"Missing {basename}_model.(pkl|json) in Firebase artifacts."
    )


def load_models(model_dir: str):
    """
    Load trained models from Firebase Storage for:
    - spread (predicts margin: home - away)
    - total (predicts combined score)
    - win prob model (predicts P(home wins))
    """
    artifacts = _download_model_artifacts(model_dir)

    spread_model = _load_xgb_model(artifacts, "spread", "regressor")
    total_model = _load_xgb_model(artifacts, "total", "regressor")
    winprob_model = _load_xgb_model(artifacts, "moneyline", "classifier")

    return spread_model, total_model, winprob_model


def _extract_feature_names_from_artifacts(artifacts: Dict[str, bytes]) -> Optional[List[str]]:
    if "feature_names.pkl" in artifacts:
        if joblib is None:
            raise RuntimeError("joblib is required to load feature_names.pkl but is not installed.")
        return list(joblib.load(BytesIO(artifacts["feature_names.pkl"])))

    if "feature_names.json" in artifacts:
        data = json.loads(artifacts["feature_names.json"].decode("utf-8"))
        if isinstance(data, dict):
            names = data.get("feature_names") or data.get("features")
            if isinstance(names, list):
                return [str(col) for col in names]
        elif isinstance(data, list):
            return [str(col) for col in data]

    if "features.txt" in artifacts:
        text = artifacts["features.txt"].decode("utf-8")
        names = [line.strip() for line in text.splitlines() if line.strip()]
        if names:
            return names

    return None


def get_feature_names(model_dir: str) -> Optional[List[str]]:
    artifacts = _download_model_artifacts(model_dir)
    return _extract_feature_names_from_artifacts(artifacts)


def _download_features_df(date_str: str) -> pd.DataFrame:
    _require_firebase_storage()
    bucket = _get_firebase_bucket()
    if bucket is None:
        raise FileNotFoundError("Firebase bucket not configured; cannot download features.")

    remote_path = f"{PROCESSED_FEATURES_PREFIX}/{date_str}/features.csv"
    blob = bucket.blob(remote_path)
    if not blob.exists():
        raise FileNotFoundError(f"Processed features missing in Firebase: {remote_path}")

    csv_text = blob.download_as_text()
    return pd.read_csv(StringIO(csv_text))


# --- Core prediction logic --------------------------------------------------

def split_home_away(features_df: pd.DataFrame) -> Dict[str, Dict[str, dict]]:
    """
    Group feature rows by game_id and identify which row is 'home team POV'
    and which is 'away team POV'.

    Assumptions:
    - features_df has one row per team per game.
    - Row contains:
        - game_id
        - team_key
        - opp_key
        - Team (name)
        - Opp (name)
        - Location ("Home"/"Away"/"Neutral")
        - bet_spread_home OR equivalent betting columns from build_features step
        - bet_total
        - moneyline_home / moneyline_away
        - tipoff_datetime

    Returns dict:
    {
      game_id: {
        "home": {...row as dict...},
        "away": {...row as dict...}
      },
      ...
    }

    We will infer home vs away by Location value.
    """
    grouped: Dict[str, Dict[str, dict]] = {}

    for _, row in features_df.iterrows():
        game_id = row["game_id"]
        rowd = row.to_dict()

        # Decide if this row is the "home" POV or the "away" POV.
        # We trust Location from build_features.py.
        loc = str(rowd.get("Location", "")).lower()

        if game_id not in grouped:
            grouped[game_id] = {"home": None, "away": None}

        if loc == "home":
            grouped[game_id]["home"] = rowd
        elif loc == "away":
            grouped[game_id]["away"] = rowd
        else:
            # Neutral site game. We'll assign one side arbitrarily as "home"
            # for book purposes, but both sides will get predictions anyway.
            # For now, first neutral row becomes "home" if empty.
            if grouped[game_id]["home"] is None:
                grouped[game_id]["home"] = rowd
            else:
                grouped[game_id]["away"] = rowd

    return grouped


def model_inputs_from_row(rowd: dict, feature_cols: List[str]) -> pd.DataFrame:
    """
    Take a single feature row dict and select just the model input columns.
    This MUST match what you trained on.

    TODO: You should import FEATURE_COLS_ORDER from build_features.py or
    pull from a shared feature_config module so we don't duplicate.
    Right now we'll just assume it's passed in.
    """
    data = {col: rowd.get(col) for col in feature_cols}
    df = pd.DataFrame([data])

    # ensure numeric types for XGBoost (strings -> NaN)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def score_game(group_entry: Dict[str, dict],
               spread_model,
               total_model,
               winprob_model,
               feature_cols: List[str]) -> Dict[str, Any]:
    """
    Given one game's 'home' and 'away' row dictionaries,
    run the models and compute:
      - model_spread (home - away)
      - model_total
      - home_win_prob
      - edges vs sportsbook lines
    """

    home_row = group_entry["home"]
    away_row = group_entry["away"]

    # We'll build model inputs for both sides just in case you need them.
    X_home = model_inputs_from_row(home_row, feature_cols)
    X_away = model_inputs_from_row(away_row, feature_cols) if away_row else None

    # Spread model: predicts margin from *whose* POV?
    # Assumption: spread_model.predict(X_home) ≈ "home minus away final margin".
    # You MUST align this with how you actually trained.
    home_margin_pred = float(spread_model.predict(X_home)[0])

    # Total model: predicts total points scored in the game.
    total_pred = float(total_model.predict(X_home)[0])

    # Win prob: probability home team wins.
    # If this model is classifier-ish with predict_proba:
    try:
        home_win_prob = float(winprob_model.predict_proba(X_home)[0, 1])
    except AttributeError:
        # If you trained regression giving win prob directly:
        home_win_prob = float(winprob_model.predict(X_home)[0])

    # Build summary record for this game
    result = {
        "game_id": home_row.get("game_id"),
        "game_date": home_row.get("Date"),
        "tipoff_datetime": home_row.get("tipoff_datetime"),
        "home_team": home_row.get("Team"),
        "away_team": away_row.get("Team") if away_row else home_row.get("Opp"),
        "home_conf": home_row.get("Conference"),
        "away_conf": away_row.get("OppConference") if away_row else home_row.get("OppConference"),
        "model_spread_home": home_margin_pred,
        "model_total": total_pred,
        "home_win_prob": home_win_prob,
        "bet_spread_home": home_row.get("bet_spread"),
        "bet_total": home_row.get("bet_total"),
        "moneyline_home": home_row.get("moneyline_a"),
        "moneyline_away": home_row.get("moneyline_b"),
        "is_neutral_site": bool(home_row.get("is_neutral")),
        "season": str(home_row.get("Date", "")).split("-")[0] if home_row.get("Date") else None,
    }
    bookmakers_raw = home_row.get("bookmakers_json")
    if isinstance(bookmakers_raw, str) and bookmakers_raw:
        try:
            result["bookmakers"] = json.loads(bookmakers_raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    return result




def rank_all_picks(all_picks: List[Dict[str, Any]], max_picks: int = 10) -> List[Dict[str, Any]]:
    """
    Sort all picks across all games by edge_strength (descending),
    take top N.
    """
    sorted_picks = sorted(
        all_picks,
        key=lambda p: p.get("edge_strength", 0),
        reverse=True
    )
    return sorted_picks[:max_picks]


# --- Publishing layer stub --------------------------------------------------

def publish_to_firestore(date_str: str,
                         game_level_preds: List[Dict[str, Any]],
                         top_picks: List[Dict[str, Any]]) -> None:
    """
    Push data so that the app can read it.

    Recommended Firestore shape:
      predictions/<DATE>/<game_id>

    For each game_id doc, you could store:
      - matchup info
      - tipoff
      - book lines
      - model predictions
      - best pick(s) for that game, if any
      - a status flag like "upcoming" or "actionable"

    TODO: actually implement with google-cloud-firestore.
    For now we just dump JSON locally to PREDICTIONS_DIR.
    """

    # Local JSON persistence disabled for cloud deployment.

    # TODO: Firestore example structure (pseudo-code):
    #
    # from google.cloud import firestore
    # db = firestore.Client()
    #
    # for g in game_level_preds:
    #     game_doc_ref = db.collection("predictions").document(date_str).collection("games").document(g["game_id"])
    #     game_doc_ref.set(g)
    #
    # picks_doc_ref = db.collection("predictions").document(date_str).collection("meta").document("top_picks")
    # picks_doc_ref.set({"picks": top_picks, "generated_at": datetime.now(timezone.utc).isoformat()})


# --- Driver -----------------------------------------------------------------

def run_predictions_for_date(date_str: str,
                             feature_cols: List[str],
                             model_dir: str = MODEL_DIR) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    For a single date:
    - load features
    - load models
    - create game-level predictions
    - choose bets
    - return (game_level_preds, top_picks)
    """

    # 1. load model-ready features created by build_features.py (from Firebase)
    features_df = _download_features_df(date_str)

    # 2. load trained models
    spread_model, total_model, winprob_model = load_models(model_dir)

    # 3. group rows by game (home/away)
    grouped = split_home_away(features_df)

    game_level_preds: List[Dict[str, Any]] = []
    all_picks: List[Dict[str, Any]] = []

    # 4. for each game, score it and create bets
    for game_id, side_info in grouped.items():
        game_pred = score_game(
            group_entry=side_info,
            spread_model=spread_model,
            total_model=total_model,
            winprob_model=winprob_model,
            feature_cols=feature_cols,  # must match training
        )

        game_level_preds.append(game_pred)
    return game_level_preds, []


def run_predictions_for_range(start_date: str, end_date: str, feature_cols: List[str]):
    """
    Convenience to mirror build_features_for_range.
    Usually you'll call this just for today (and maybe tomorrow),
    not 7 days out, because future games won't have stable features/odds.
    """
    cur = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    while cur <= end_dt:
        date_str = cur.strftime("%Y-%m-%d")
        try:
            game_level_preds, top_picks = run_predictions_for_date(date_str, feature_cols)
            publish_to_firestore(date_str, game_level_preds, top_picks)
        except Exception as e:
            print(f"[make_predictions][ERROR] {date_str}: {e}")
        cur += timedelta(days=1)


if __name__ == "__main__":
    # TODO: import FEATURE_COLS_ORDER from build_features or a shared feature_config module
    # For now we stub:
    FEATURE_COLS_FROM_TRAINING = [
        # must match the columns your model expects, same as FEATURE_COLS_ORDER
        # e.g. "off_efficiency", "def_efficiency", "opp_off_efficiency", ...
    ]

    today = datetime.now(CENTRAL_TZ).strftime("%Y-%m-%d")

    # Usually you'll only run for today (and maybe tomorrow)
    run_predictions_for_range(
        start_date=today,
        end_date=today,  # change to tomorrow if you want to surface early lines
        feature_cols=FEATURE_COLS_FROM_TRAINING,
    )
def _get_firebase_bucket(bucket_name: Optional[str] = None):
    global _FIREBASE_BUCKET
    if firebase_admin is None or storage is None:
        return None

    if _FIREBASE_BUCKET is not None and (bucket_name is None or _FIREBASE_BUCKET.name == bucket_name):
        return _FIREBASE_BUCKET

    target_bucket = bucket_name or FIREBASE_STORAGE_BUCKET
    if not target_bucket:
        return None

    if not firebase_admin._apps:
        options = {}
        if FIREBASE_STORAGE_BUCKET:
            options["storageBucket"] = FIREBASE_STORAGE_BUCKET
        
        firebase_admin.initialize_app(options=options or None)
    
    # Fix: Call storage.bucket() with the target bucket name
    _FIREBASE_BUCKET = storage.bucket(target_bucket)
    return _FIREBASE_BUCKET


def _get_firestore_client():
    global _FIRESTORE_CLIENT
    if firebase_admin is None or firestore is None:
        return None
    if _FIRESTORE_CLIENT is not None:
        return _FIRESTORE_CLIENT
    if not firebase_admin._apps:
        _get_firebase_bucket()
    try:
        _FIRESTORE_CLIENT = firestore.client()
    except Exception:
        _FIRESTORE_CLIENT = None
    return _FIRESTORE_CLIENT


def _current_model_version() -> Optional[str]:
    explicit = os.environ.get("BETBOARD_MODEL_VERSION")
    if explicit and explicit != "current_production":
        return explicit
    client = _get_firestore_client()
    if client is None:
        return None
    try:
        doc = client.collection("models").document("current_production").get()
        if doc.exists:
            data = doc.to_dict() or {}
            return data.get("version")
    except Exception:
        return None
    return None


def _resolve_model_path(model_dir: str) -> str:
    path_str = str(model_dir)
    if "current_production" in path_str or "latest" in path_str:
        version = _current_model_version()
        if version:
            path_str = path_str.replace("current_production", version).replace("latest", version)
    return path_str


MODEL_FILE_CANDIDATES = {
    "spread": ["spread_model.json", "spread_model.pkl"],
    "total": ["total_model.json", "total_model.pkl"],
    "moneyline": ["moneyline_model.json", "moneyline_model.pkl"],
}

OPTIONAL_MODEL_FILES = [
    "feature_names.pkl",
    "feature_names.json",
    "features.txt",
    "model_metadata.json",
]

def _download_model_artifacts(model_dir: str) -> Dict[str, bytes]:
    _require_firebase_storage()

    resolved = _resolve_model_path(model_dir)
    remote = resolved.strip()
    bucket_name = FIREBASE_STORAGE_BUCKET

    if remote.startswith("gs://"):
        _, rest = remote.split("://", 1)
        parts = rest.split("/", 1)
        bucket_name = parts[0]
        remote = parts[1] if len(parts) > 1 else ""

    remote = remote.lstrip("/")
    if not remote:
        raise FileNotFoundError("MODEL_DIR does not point to a valid Firebase Storage path.")

    if not bucket_name:
        raise FileNotFoundError(
            "Firebase bucket not configured; set FIREBASE_STORAGE_BUCKET or provide a gs:// path."
        )

    bucket = _get_firebase_bucket(bucket_name)
    if bucket is None:
        raise FileNotFoundError(
            "Firebase bucket not configured; cannot download models. "
            "Ensure firebase_admin is initialized with storage credentials."
        )

    cache_key = f"{bucket.name}/{remote}"
    if cache_key in _MODEL_ARTIFACT_CACHE:
        return _MODEL_ARTIFACT_CACHE[cache_key]

    artifacts: Dict[str, bytes] = {}
    missing_required: List[str] = []

    for label, candidate_files in MODEL_FILE_CANDIDATES.items():
        found = False
        for filename in candidate_files:
            blob_path = "/".join(filter(None, [remote, filename]))
            blob = bucket.blob(blob_path)
            if blob.exists():
                artifacts[filename] = blob.download_as_bytes()
                found = True
        if not found:
            missing_required.append(label)

    if missing_required:
        raise FileNotFoundError(
            f"Model artifact(s) missing for {', '.join(missing_required)} in {remote}."
        )

    for filename in OPTIONAL_MODEL_FILES:
        blob_path = "/".join(filter(None, [remote, filename]))
        blob = bucket.blob(blob_path)
        if blob.exists():
            artifacts[filename] = blob.download_as_bytes()

    _MODEL_ARTIFACT_CACHE[cache_key] = artifacts
    return artifacts
