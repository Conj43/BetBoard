import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd

try:
    from config import (
        PROCESSED_DATA_DIR,
        MODEL_DIR,           # e.g. "models/run_2025_10_28"
        MODEL_FALLBACK_LOCAL_DIR,
        BET_MODEL_DIR,
        BET_MODEL_FALLBACK_LOCAL_DIR,
        PREDICTIONS_DIR,     # e.g. "data/output"
        MIN_EDGE_SPREAD_PTS, # e.g. 1.5
        MIN_EDGE_TOTAL_PTS,  # e.g. 3.0
        MIN_PROB_EDGE,       # e.g. 0.05
        FIREBASE_CREDENTIALS_PATH,
        FIREBASE_STORAGE_BUCKET,
    )
except ImportError:
    PROCESSED_DATA_DIR = "data/processed"
    MODEL_DIR = "models/run_ACTIVE"  # TODO: point at your best run
    PREDICTIONS_DIR = "data/output"
    MIN_EDGE_SPREAD_PTS = 1.5
    MIN_EDGE_TOTAL_PTS = 3.0
    MIN_PROB_EDGE = 0.05
    FIREBASE_CREDENTIALS_PATH = ""
    FIREBASE_STORAGE_BUCKET = ""
    MODEL_FALLBACK_LOCAL_DIR = "data/xgb_model/No_Bet_xgb_all_models_20251104_160154/models_production"
    BET_MODEL_DIR = "models/current_production/with_bet"
    BET_MODEL_FALLBACK_LOCAL_DIR = "data/xgb_model/Bet_xgb_all_models_20251104_160047/models_production"

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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_CACHE_DIR = PROJECT_ROOT / "data" / "model_cache"
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_FIREBASE_BUCKET = None
_FIRESTORE_CLIENT = None


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

def _load_xgb_model(model_dir: str, basename: str, model_type: str):
    """
    Load an XGBoost model saved either as a sklearn-style pickle or native JSON.
    """
    pkl_path = os.path.join(model_dir, f"{basename}_model.pkl")
    json_path = os.path.join(model_dir, f"{basename}_model.json")

    if os.path.exists(pkl_path):
        if joblib is None:
            raise RuntimeError(
                f"joblib is required to load {basename}_model.pkl but is not installed."
            )
        return joblib.load(pkl_path)

    if os.path.exists(json_path):
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
        model.load_model(json_path)
        return model

    raise FileNotFoundError(
        f"Could not find {basename}_model.(pkl|json) in {model_dir}"
    )


def load_models(model_dir: str, fallback_dir: Optional[str] = None):
    """
    Load trained models for:
    - spread (predicts margin: home - away)
    - total (predicts combined score)
    - win prob model (predicts P(home wins))
    """
    try:
        resolved_dir = _ensure_local_model_dir(model_dir)
    except FileNotFoundError:
        if fallback_dir:
            resolved_dir = _ensure_local_model_dir(fallback_dir)
        else:
            raise

    spread_model = _load_xgb_model(resolved_dir, "spread", "regressor")
    total_model = _load_xgb_model(resolved_dir, "total", "regressor")
    winprob_model = _load_xgb_model(resolved_dir, "moneyline", "classifier")

    return spread_model, total_model, winprob_model


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
        "tipoff_datetime": home_row.get("tipoff_datetime"),
        "home_team": home_row.get("Team"),
        "away_team": away_row.get("Team") if away_row else home_row.get("Opp"),
        "home_conf": home_row.get("Conference"),
        "away_conf": away_row.get("OppConference"),

        "model_spread_home": home_margin_pred,
        "model_total": total_pred,
        "home_win_prob": home_win_prob,
    }
    bookmakers_raw = home_row.get("bookmakers_json")
    if isinstance(bookmakers_raw, str) and bookmakers_raw:
        try:
            result["bookmakers"] = json.loads(bookmakers_raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    return result


def choose_bets_for_game(game_pred: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Given one game's prediction dict (model lines, book lines, edges),
    decide if there's anything we actually want to RECOMMEND.

    Returns a list of bet objects we like for this game.
    """

    picks = []

    # Spread bet
    sp_edge = game_pred.get("spread_edge_points")
    book_spread_home = game_pred.get("book_spread_home")
    model_spread_home = game_pred.get("model_spread_home") if "model_spread_home" in game_pred else game_pred.get("model_spread_home", game_pred.get("model_spread_home", None))

    # Home spread logic:
    # If model says home should win by 5.0 but book says -2.5, edge = 2.5 in our favor.
    if sp_edge is not None and abs(sp_edge) >= MIN_EDGE_SPREAD_PTS and book_spread_home is not None:
        if sp_edge < 0:
            # model thinks home is more dominant than the book does
            # example: model -7.0, book -4.5 => sp_edge = -2.5
            rec_side = f"{game_pred['home_team']} {book_spread_home}"
        else:
            # model thinks away is stronger than book thinks
            # translate home line to away line = opposite sign
            away_line = None
            try:
                away_line = -float(book_spread_home)
            except (TypeError, ValueError):
                pass
            opp_name = game_pred["away_team"]
            if away_line is not None:
                rec_side = f"{opp_name} {away_line:+.1f}"
            else:
                rec_side = f"{opp_name} spread (calc)"

        picks.append({
            "bet_type": "spread",
            "recommended_side": rec_side,
            "edge_strength": abs(sp_edge),
            "model_spread_home": model_spread_home,
            "book_spread_home": book_spread_home
        })

    # Total
    tot_edge = game_pred.get("total_edge_points")
    book_total = game_pred.get("book_total")
    model_total = game_pred.get("model_total")

    if tot_edge is not None and abs(tot_edge) >= MIN_EDGE_TOTAL_PTS and book_total is not None:
        direction = "OVER" if tot_edge > 0 else "UNDER"
        picks.append({
            "bet_type": "total",
            "recommended_side": f"{direction} {book_total}",
            "edge_strength": abs(tot_edge),
            "model_total": model_total,
            "book_total": book_total
        })

    # Moneyline (home)
    ml_edge_home = game_pred.get("moneyline_edge_home")
    if ml_edge_home is not None and ml_edge_home >= MIN_PROB_EDGE:
        picks.append({
            "bet_type": "moneyline",
            "recommended_side": f"{game_pred['home_team']} ML ({game_pred.get('moneyline_home')})",
            "edge_strength": ml_edge_home,
            "model_home_win_prob": game_pred.get("home_win_prob"),
            "implied_home_win_prob": game_pred.get("implied_home_win_prob"),
        })

    # Moneyline (away)
    ml_edge_away = game_pred.get("moneyline_edge_away")
    if ml_edge_away is not None and ml_edge_away >= MIN_PROB_EDGE:
        picks.append({
            "bet_type": "moneyline",
            "recommended_side": f"{game_pred['away_team']} ML ({game_pred.get('moneyline_away')})",
            "edge_strength": ml_edge_away,
            "model_away_win_prob": (1.0 - game_pred.get("home_win_prob", 0.0)),
            "implied_away_win_prob": game_pred.get("implied_away_win_prob"),
        })

    # add base game context to every pick
    for p in picks:
        p.update({
            "game_id": game_pred["game_id"],
            "home_team": game_pred["home_team"],
            "away_team": game_pred["away_team"],
            "tipoff_datetime": game_pred["tipoff_datetime"],
        })

    return picks


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
                             model_dir: str = MODEL_DIR,
                             fallback_dir: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    For a single date:
    - load features
    - load models
    - create game-level predictions
    - choose bets
    - return (game_level_preds, top_picks)
    """

    # 1. load model-ready features created by build_features.py
    feat_path = os.path.join(PROCESSED_DATA_DIR, f"{date_str}_features.csv")
    features_df = pd.read_csv(feat_path)

    # 2. load trained models
    spread_model, total_model, winprob_model = load_models(model_dir, fallback_dir or MODEL_FALLBACK_LOCAL_DIR)

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

    today = datetime.now().strftime("%Y-%m-%d")

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
        if FIREBASE_CREDENTIALS_PATH and os.path.exists(FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred, {"storageBucket": target_bucket})
        else:
            firebase_admin.initialize_app(options={"storageBucket": target_bucket})
    bucket = storage.bucket(target_bucket)
    if bucket:
        _FIREBASE_BUCKET = bucket
    return bucket


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


def _ensure_local_model_dir(model_dir: str) -> str:
    model_dir = _resolve_model_path(model_dir)
    path = Path(model_dir)
    if path.exists():
        return str(path)

    remote = model_dir.strip()
    bucket_name = FIREBASE_STORAGE_BUCKET

    if remote.startswith("gs://"):
        _, rest = remote.split("://", 1)
        parts = rest.split("/", 1)
        bucket_name = parts[0]
        remote = parts[1] if len(parts) > 1 else ""

    remote = remote.lstrip("/")
    if not remote:
        raise FileNotFoundError("MODEL_DIR does not point to a valid path.")

    bucket = _get_firebase_bucket(bucket_name)
    if bucket is None:
        raise FileNotFoundError("Firebase bucket not configured; cannot download models.")

    relative_parts = [part for part in remote.split("/") if part]
    cache_dir = MODEL_CACHE_DIR / bucket.name
    for part in relative_parts:
        cache_dir /= part
    cache_dir.mkdir(parents=True, exist_ok=True)

    required_files = [
        "spread_model.json",
        "total_model.json",
        "moneyline_model.json",
        "feature_names.pkl",
        "model_metadata.json",
    ]

    for filename in required_files:
        local_path = cache_dir / filename
        if local_path.exists():
            continue
        blob_path = "/".join(relative_parts + [filename])
        blob = bucket.blob(blob_path)
        if not blob.exists():
            raise FileNotFoundError(f"Model artifact missing in bucket: {blob_path}")
        blob.download_to_filename(str(local_path))

    return str(cache_dir)
