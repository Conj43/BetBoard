import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple
import pandas as pd

try:
    from config import (
        PROCESSED_DATA_DIR,
        MODEL_DIR,           # e.g. "models/run_2025_10_28"
        PREDICTIONS_DIR,     # e.g. "data/output"
        MIN_EDGE_SPREAD_PTS, # e.g. 1.5
        MIN_EDGE_TOTAL_PTS,  # e.g. 3.0
        MIN_PROB_EDGE,       # e.g. 0.05
    )
except ImportError:
    PROCESSED_DATA_DIR = "data/processed"
    MODEL_DIR = "models/run_ACTIVE"  # TODO: point at your best run
    PREDICTIONS_DIR = "data/output"
    MIN_EDGE_SPREAD_PTS = 1.5
    MIN_EDGE_TOTAL_PTS = 3.0
    MIN_PROB_EDGE = 0.05

# We'll assume LightGBM/XGBoost-ish models were joblib'd.
# If you're using pickle or something else, tweak here.
try:
    import joblib
except ImportError:
    joblib = None  # TODO: make sure joblib is installed in prod env


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

def load_models(model_dir: str):
    """
    Load trained models for:
    - spread (predicts margin: home - away)
    - total (predicts combined score)
    - win prob model (predicts P(home wins))

    TODO: update filenames to match what you actually saved.
    """
    if joblib is None:
        raise RuntimeError("joblib not available. Install joblib or adjust loader.")

    spread_model_path = os.path.join(model_dir, "spread_model.pkl")
    total_model_path = os.path.join(model_dir, "total_model.pkl")
    winprob_model_path = os.path.join(model_dir, "moneyline_model.pkl")

    spread_model = joblib.load(spread_model_path)
    total_model = joblib.load(total_model_path)
    winprob_model = joblib.load(winprob_model_path)

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
    return pd.DataFrame([data])


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

    # Pull sportsbook numbers from home_row.
    # We assume build_features stored the live lines like:
    # - bet_spread_home (spread where negative means home is favored)
    # - bet_total
    # - moneyline_home
    # - moneyline_away
    book_spread_home = home_row.get("bet_spread_home")
    book_total = home_row.get("bet_total")
    ml_home = home_row.get("moneyline_home")
    ml_away = home_row.get("moneyline_away")

    # Compute edges
    # Spread edge: how far off we think the line is from reality
    # (positive absolute difference == stronger edge)
    if book_spread_home is not None:
        spread_edge_points = home_margin_pred - float(book_spread_home)
    else:
        spread_edge_points = None

    # Total edge
    if book_total is not None:
        total_edge_points = total_pred - float(book_total)
    else:
        total_edge_points = None

    # Moneyline edge
    implied_home = implied_prob_from_moneyline(ml_home)
    implied_away = implied_prob_from_moneyline(ml_away)

    if implied_home is not None:
        moneyline_edge_home = home_win_prob - implied_home
    else:
        moneyline_edge_home = None

    if implied_away is not None:
        moneyline_edge_away = (1.0 - home_win_prob) - implied_away
    else:
        moneyline_edge_away = None

    # Build summary record for this game
    result = {
        "game_id": home_row.get("game_id"),
        "tipoff_datetime": home_row.get("tipoff_datetime"),
        "home_team": home_row.get("Team"),
        "away_team": away_row.get("Team") if away_row else home_row.get("Opp"),
        "home_conf": home_row.get("Conference"),
        "away_conf": away_row.get("OppConference"),

        "model_spread_home": home_margin_pred,   # model's home minus away
        "book_spread_home": book_spread_home,
        "spread_edge_points": spread_edge_points,

        "model_total": total_pred,
        "book_total": book_total,
        "total_edge_points": total_edge_points,

        "home_win_prob": home_win_prob,
        "moneyline_home": ml_home,
        "moneyline_away": ml_away,
        "implied_home_win_prob": implied_home,
        "implied_away_win_prob": implied_away,
        "moneyline_edge_home": moneyline_edge_home,
        "moneyline_edge_away": moneyline_edge_away,
    }

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

    os.makedirs(PREDICTIONS_DIR, exist_ok=True)

    # 1. save game-level preds (all games, not just picks)
    game_preds_path = os.path.join(PREDICTIONS_DIR, f"{date_str}_game_preds.json")
    with open(game_preds_path, "w") as f:
        json.dump(game_level_preds, f, indent=2)
    print(f"[make_predictions] wrote {game_preds_path}")

    # 2. save final picks (ranked bets we actually like)
    picks_path = os.path.join(PREDICTIONS_DIR, f"{date_str}_top_picks.json")
    with open(picks_path, "w") as f:
        json.dump(top_picks, f, indent=2)
    print(f"[make_predictions] wrote {picks_path}")

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
                             feature_cols: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
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
    spread_model, total_model, winprob_model = load_models(MODEL_DIR)

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

        picks_for_game = choose_bets_for_game(game_pred)
        all_picks.extend(picks_for_game)

    # 5. rank picks across all games
    top_picks = rank_all_picks(all_picks, max_picks=10)

    return game_level_preds, top_picks


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