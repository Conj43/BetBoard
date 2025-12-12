"""
Unit tests for automation.pipeline.prediction_pipeline helpers.

Tests live outside functions/ so they aren't deployed. Imports are isolated by
stubbing firebase_admin and other heavy modules before loading the pipeline.
"""
from __future__ import annotations

import importlib
import math
import sys
import types
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS_DIR = PROJECT_ROOT / "functions"


def _slug(value: str) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _stub_firebase():
    fb = types.ModuleType("firebase_admin")
    fb._apps = {}

    def init_app(*_, **__):
        fb._apps["default"] = object()
        return fb._apps["default"]

    fb.initialize_app = init_app

    credentials = types.ModuleType("firebase_admin.credentials")
    credentials.Certificate = lambda *_, **__: None
    firestore = types.ModuleType("firebase_admin.firestore")
    firestore.client = lambda *_, **__: object()

    class DummyBlob:
        def __init__(self, *_, **__):
            pass

        def exists(self):
            return False

    class DummyBucket:
        def blob(self, *_, **__):
            return DummyBlob()

    storage = types.ModuleType("firebase_admin.storage")
    storage.bucket = lambda *_, **__: DummyBucket()

    fb.credentials = credentials
    fb.firestore = firestore
    fb.storage = storage

    sys.modules["firebase_admin"] = fb
    sys.modules["firebase_admin.credentials"] = credentials
    sys.modules["firebase_admin.firestore"] = firestore
    sys.modules["firebase_admin.storage"] = storage


def _load_pipeline_module():
    """Load prediction_pipeline with dependencies stubbed."""
    for name in list(sys.modules):
        if name.startswith("automation.pipeline.prediction_pipeline"):
            sys.modules.pop(name, None)

    for name in [
        "automation",
        "automation.config",
        "automation.config.config",
        "automation.config.team_keys",
        "automation.pipeline",
        "automation.clients",
        "automation.clients.firestore",
        "automation.clients.gamelog",
        "automation.clients.odds",
        "automation.clients.torvik",
        "automation.prediction",
        "automation.prediction.make_preds",
        "automation.processing",
        "automation.processing.build_features",
        "automation.processing.ingest_raw",
    ]:
        sys.modules.pop(name, None)

    _stub_firebase()

    # Build minimal package skeleton
    automation = types.ModuleType("automation")
    automation.__path__ = [str(FUNCTIONS_DIR / "automation")]
    sys.modules["automation"] = automation

    automation_config = types.ModuleType("automation.config")
    automation_config.__path__ = []
    sys.modules["automation.config"] = automation_config

    team_keys = types.ModuleType("automation.config.team_keys")
    team_keys.canonicalize_team_key = lambda value: _slug(value).replace(" ", "-")
    sys.modules["automation.config.team_keys"] = team_keys

    config_mod = types.ModuleType("automation.config.config")
    config_mod.FIREBASE_CREDENTIALS_PATH = ""
    config_mod.FEATURE_COLS_ORDER = []
    config_mod.MAX_PICKS_TO_PUBLISH = 10
    config_mod.MODEL_DIR = "models/main"
    config_mod.BET_MODEL_DIR = "models/bet"
    sys.modules["automation.config.config"] = config_mod

    clients_pkg = types.ModuleType("automation.clients")
    clients_pkg.__path__ = []
    sys.modules["automation.clients"] = clients_pkg

    firestore_client = types.ModuleType("automation.clients.firestore")
    firestore_client.publish_predictions_to_firestore = lambda *_, **__: None
    sys.modules["automation.clients.firestore"] = firestore_client

    sys.modules["automation.clients.gamelog"] = types.ModuleType("automation.clients.gamelog")
    sys.modules["automation.clients.odds"] = types.ModuleType("automation.clients.odds")
    sys.modules["automation.clients.torvik"] = types.ModuleType("automation.clients.torvik")

    prediction_pkg = types.ModuleType("automation.prediction")
    prediction_pkg.__path__ = []
    sys.modules["automation.prediction"] = prediction_pkg

    make_preds = types.ModuleType("automation.prediction.make_preds")

    def implied_prob_from_moneyline(odds):
        try:
            odds_val = float(odds)
        except (TypeError, ValueError):
            return None
        if odds_val > 0:
            return 100.0 / (odds_val + 100.0)
        return abs(odds_val) / (abs(odds_val) + 100.0)

    make_preds.implied_prob_from_moneyline = implied_prob_from_moneyline
    make_preds.get_feature_names = lambda *_: None
    make_preds.firebase_admin = object()
    make_preds.storage = object()
    sys.modules["automation.prediction.make_preds"] = make_preds

    processing_pkg = types.ModuleType("automation.processing")
    processing_pkg.__path__ = []
    sys.modules["automation.processing"] = processing_pkg
    build_features_mod = types.ModuleType("automation.processing.build_features")
    build_features_mod.PROCESSED_FEATURES_PREFIX = "processed"
    build_features_mod._download_csv = lambda *_, **__: pd.DataFrame()
    build_features_mod.build_features_for_date = lambda *_, **__: pd.DataFrame()
    sys.modules["automation.processing.build_features"] = build_features_mod
    sys.modules["automation.processing.ingest_raw"] = types.ModuleType("automation.processing.ingest_raw")

    sys.path.insert(0, str(FUNCTIONS_DIR))
    try:
        return importlib.import_module("automation.pipeline.prediction_pipeline")
    finally:
        sys.path.pop(0)


@pytest.fixture(scope="module")
def pipeline_mod():
    return _load_pipeline_module()


def test_label_missing_odds_sets_placeholder(pipeline_mod):
    preds = [
        {"bet_spread_home": None, "bet_total": "", "moneyline_home": math.nan, "moneyline_away": 120},
        {"bet_spread_home": -3.5, "bet_total": 142.5, "moneyline_home": -130, "moneyline_away": None},
    ]
    pipeline_mod._label_missing_odds(preds)
    assert preds[0]["bet_spread_home"] == "No Odds"
    assert preds[0]["bet_total"] == "No Odds"
    assert preds[0]["moneyline_home"] == "No Odds"
    assert preds[0]["moneyline_away"] == 120
    assert preds[1]["moneyline_away"] == "No Odds"


def test_build_top_recommendations_respects_caps_and_uniqueness(pipeline_mod):
    picks = [
        {"game_id": "G1", "bet_type": "moneyline", "edge_strength": 0.04},
        {"game_id": "G3", "bet_type": "total", "edge_strength": 6.0},
        {"game_id": "G1", "bet_type": "spread", "edge_strength": 5.0},
        {"game_id": "G2", "bet_type": "moneyline", "edge_strength": 0.03},
        {"game_id": "G4", "bet_type": "spread", "edge_strength": 6.0},
        {"game_id": "G5", "bet_type": "moneyline", "edge_strength": 0.02},
        {"game_id": "G6", "bet_type": "moneyline", "edge_strength": 0.015},
    ]
    top = pipeline_mod._build_top_recommendations(picks, max_picks=4)
    assert len(top) == 4
    assert len({p["game_id"] for p in top}) == 4  # one per game
    assert all(p["bet_type"] in ("spread", "moneyline", "total") for p in top)
    assert sum(1 for p in top if p["bet_type"] == "spread") <= 3
    assert sum(1 for p in top if p["bet_type"] == "moneyline") <= 3
    assert sum(1 for p in top if p["bet_type"] == "total") <= 3
    assert any(p["bet_type"] == "moneyline" for p in top)
    assert any(p["bet_type"] == "spread" for p in top)


def test_choose_bets_for_game_builds_spread_total_and_moneyline(pipeline_mod):
    bookmakers = {
        "betmgm": {
            "spread": {
                "home": {"line": -1.5, "price": -110},
                "away": {"line": 1.5, "price": -110},
            },
            "total": {
                "over": {"line": 142.0, "price": -105},
                "under": {"line": 142.0, "price": -115},
            },
            "moneyline": {"home": -120, "away": 200},
        }
    }
    game_pred = {
        "game_id": "GAME123",
        "home_team": "Home",
        "away_team": "Away",
        "model_spread_home": 4.0,
        "bet_spread_home": -1.5,
        "model_total": 150.0,
        "bet_total": 142.0,
        "home_win_prob": 0.65,
        "bookmakers": bookmakers,
    }

    picks = pipeline_mod._choose_bets_for_game(game_pred)

    # Should include spread, total, and both moneyline edges
    assert any(p["bet_type"] == "spread" and p["selection"] == "Home" for p in picks)
    assert any(p["bet_type"] == "total" and p["selection"].lower() == "over" for p in picks)
    assert any(p["bet_type"] == "moneyline" and p["selection"] == "Home" for p in picks)
    assert any(p["bet_type"] == "moneyline" and p["selection"] == "Away" for p in picks)


# --- ADD THESE TO tests/test_prediction_pipeline.py ---

def test_pipeline_no_games_meeting_criteria(pipeline_mod):
    """
    Scenario: Edge case where no games meet the betting threshold.
    Verifies that an empty recommendation list is handled without error.
    """
    # Create picks with very low edge strength
    picks = [
        {"game_id": "G1", "bet_type": "spread", "edge_strength": 0.1}, # Threshold is 5.0
        {"game_id": "G2", "bet_type": "moneyline", "edge_strength": 0.001} # Threshold is 0.01
    ]
    
    top = pipeline_mod._build_top_recommendations(picks, max_picks=5)
    
    # Should return empty list, not crash
    assert isinstance(top, list)
    assert len(top) == 0

def test_pipeline_handles_missing_model_gracefully(pipeline_mod):
    """
    Scenario: Negative test for corrupted or missing model files.
    Ensures the pipeline surfaces the error (or crashes safely) rather than producing partial junk data.
    """
    # We mock _load_feature_columns to raise an error simulating missing model metadata
    with pytest.raises(RuntimeError, match="Unable to determine feature columns"):
        # We pass an invalid directory and no explicit columns
        pipeline_mod._load_feature_columns(model_dir="non_existent_dir", explicit=None)

def test_pipeline_missing_data_sources(pipeline_mod):
    """
    Scenario: Missing data sources (e.g. features df cannot be downloaded).
    """
    with patch("automation.pipeline.prediction_pipeline._download_features_df", side_effect=FileNotFoundError("No features")):
        with patch("automation.pipeline.prediction_pipeline.build_features.build_features_for_date", side_effect=FileNotFoundError("No source")):
            
            # If we run the pipeline and data is missing, it should catch the error and log it (or continue)
            # The current implementation catches FileNotFoundError inside the loop and prints it
            
            config = pipeline_mod.PredictionPipelineConfig(
                start_date="2023-01-01", 
                skip_refresh=True, 
                skip_ingest=True,
                # skip_features=True to force it to try downloading
                skip_features=True 
            )
            
            # This shouldn't raise, it should just print "Missing features..." and finish
            try:
                pipeline_mod.run_prediction_pipeline(config)
            except Exception as e:
                pytest.fail(f"Pipeline crashed on missing data instead of handling gracefully: {e}")


# ---- Additional coverage merged from extended suite ----


def test_label_missing_odds():
    from automation.pipeline import prediction_pipeline as pp
    preds = [{"bet_spread_home": None, "bet_total": None, "moneyline_home": None, "moneyline_away": None}]
    pp._label_missing_odds(preds)
    assert preds[0]["bet_spread_home"] == "No Odds"
    assert preds[0]["bet_total"] == "No Odds"
    assert preds[0]["moneyline_home"] == "No Odds"
    assert preds[0]["moneyline_away"] == "No Odds"


def test_meets_bet_criteria_edges():
    from automation.pipeline import prediction_pipeline as pp
    pick = {"bet_type": "spread", "edge_strength": 6.0, "bet_total": 150}
    assert pp._meets_bet_criteria(pick)
    pick_bad = {"bet_type": "total", "edge_strength": 4.0}
    assert not pp._meets_bet_criteria(pick_bad)

    ml_good = {"bet_type": "moneyline", "edge_strength": 0.02, "odds": 250}
    ml_bad_low = {"bet_type": "moneyline", "edge_strength": 0.005, "odds": 200}
    ml_bad_high = {"bet_type": "moneyline", "edge_strength": 0.06, "odds": 200}
    ml_longshot = {"bet_type": "moneyline", "edge_strength": 0.02, "odds": 350}
    assert pp._meets_bet_criteria(ml_good)
    assert not pp._meets_bet_criteria(ml_bad_low)
    assert not pp._meets_bet_criteria(ml_bad_high)
    assert not pp._meets_bet_criteria(ml_longshot)


def test_build_top_recommendations_caps():
    from automation.pipeline import prediction_pipeline as pp
    picks = [
        {"game_id": "G1", "bet_type": "spread", "edge_strength": 3},
        {"game_id": "G2", "bet_type": "spread", "edge_strength": 4},
        {"game_id": "G3", "bet_type": "moneyline", "edge_strength": 0.02},
        {"game_id": "G4", "bet_type": "total", "edge_strength": 5},
        {"game_id": "G1", "bet_type": "moneyline", "edge_strength": 0.03},
    ]
    top = pp._build_top_recommendations(picks, max_picks=3)
    assert len(top) == 3
    assert len({p["game_id"] for p in top}) == 3


def test_score_with_models_missing_cols_raises():
    from automation.pipeline import prediction_pipeline as pp
    df = pd.DataFrame([{"f1": 1}])
    with pytest.raises(ValueError):
        pp._score_with_models(df, ["f1", "f2"], "model_dir")


def test_require_firebase_storage_raises_when_missing(monkeypatch):
    from automation.pipeline import prediction_pipeline as pp
    monkeypatch.setattr(pp.make_preds, "firebase_admin", None)
    monkeypatch.setattr(pp.make_preds, "storage", None)
    with pytest.raises(RuntimeError):
        pp._require_firebase_storage()


# ---- Integration-ish pipeline run coverage merged from pipeline_runs ----


def _ensure_functions_on_path():
    path_str = str(FUNCTIONS_DIR)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    for name in list(sys.modules):
        if name.startswith("automation.pipeline") or name.startswith("automation.prediction"):
            sys.modules.pop(name, None)


def _stub_firebase_and_config():
    fb = types.ModuleType("firebase_admin")
    fb._apps = {"default": object()}
    fb.initialize_app = lambda *_, **__: None
    sys.modules["firebase_admin"] = fb
    sys.modules["firebase_admin.credentials"] = types.ModuleType("firebase_admin.credentials")
    sys.modules["firebase_admin.storage"] = types.ModuleType("firebase_admin.storage")
    sys.modules["firebase_admin.firestore"] = types.ModuleType("firebase_admin.firestore")

    config_mod = types.ModuleType("automation.config.config")
    config_mod.FIRESTORE_PREDICTIONS_COLLECTION = "games"
    config_mod.FIREBASE_STORAGE_BUCKET = "bucket"
    config_mod.FIREBASE_CREDENTIALS_PATH = ""
    config_mod.RAW_GAMES_PREFIX = "raw/games"
    config_mod.RAW_TEAMS_PREFIX = "raw/teams"
    config_mod.RAW_ODDS_PREFIX = "raw/odds"
    config_mod.PROCESSED_FEATURES_PREFIX = "processed"
    config_mod.GAMELOG_STORAGE_PREFIX = "gamelogs"
    config_mod.SPORTS_REFERENCE_SEASON = "2024"
    config_mod.MAX_PICKS_TO_PUBLISH = 3
    config_mod.MODEL_DIR = "models/main"
    config_mod.BET_MODEL_DIR = "models/bet"
    config_mod.FEATURE_COLS_ORDER = []
    config_mod.TEAM_MAPPING = {}
    config_mod.CONFERENCE_MAP = {}
    config_mod.TORVIK_MAP = {}
    config_mod.canonicalize_team_key = lambda name: str(name).lower().replace(" ", "-") if name else ""
    sys.modules["automation.config.config"] = config_mod

    automation_pkg = types.ModuleType("automation")
    automation_pkg.__path__ = [str(FUNCTIONS_DIR / "automation")]
    sys.modules["automation"] = automation_pkg
    config_pkg = types.ModuleType("automation.config")
    config_pkg.__path__ = [str(FUNCTIONS_DIR / "automation" / "config")]
    sys.modules["automation.config"] = config_pkg

    eval_pkg = types.ModuleType("automation.evaluation")
    eval_pkg.__path__ = [str(FUNCTIONS_DIR / "automation" / "evaluation")]
    sys.modules["automation.evaluation"] = eval_pkg

    scrape_results_mod = types.ModuleType("automation.evaluation.scrape_results")
    scrape_results_mod.main = lambda *_, **__: None
    scrape_results_mod.DEFAULT_TIMEZONE = "America/Chicago"
    sys.modules["automation.evaluation.scrape_results"] = scrape_results_mod

    eval_preds_mod = types.ModuleType("automation.evaluation.evaluate_predictions")
    eval_preds_mod.main = lambda *_, **__: None
    eval_preds_mod.DEFAULT_RESULT_DOC = "odds_api"
    eval_preds_mod.DEFAULT_EVAL_COLLECTION = "eval"
    sys.modules["automation.evaluation.evaluate_predictions"] = eval_preds_mod

    settle_mod = types.ModuleType("automation.evaluation.settle_user_bets")
    settle_mod.settle_pending_bets = lambda *_, **__: None
    sys.modules["automation.evaluation.settle_user_bets"] = settle_mod

    clients_pkg = types.ModuleType("automation.clients")
    clients_pkg.__path__ = []
    sys.modules["automation.clients"] = clients_pkg

    gamelog_mod = types.ModuleType("automation.clients.gamelog")
    gamelog_mod.main_entry_point = lambda *_, **__: None
    sys.modules["automation.clients.gamelog"] = gamelog_mod

    odds_mod = types.ModuleType("automation.clients.odds")
    odds_mod.get_college_basketball_games = lambda *_, **__: None
    sys.modules["automation.clients.odds"] = odds_mod

    torvik_mod = types.ModuleType("automation.clients.torvik")
    torvik_mod.scrape_torvik = lambda *_, **__: None
    sys.modules["automation.clients.torvik"] = torvik_mod

    firestore_mod = types.ModuleType("automation.clients.firestore")
    firestore_mod.publish_predictions_to_firestore = lambda *_, **__: None
    sys.modules["automation.clients.firestore"] = firestore_mod


def test_run_evaluation_pipeline(monkeypatch):
    _ensure_functions_on_path()
    _stub_firebase_and_config()

    fake_scrape_main = MagicMock()
    fake_eval_main = MagicMock()
    fake_settle = MagicMock()

    with patch("automation.evaluation.scrape_results.main", fake_scrape_main), \
         patch("automation.evaluation.evaluate_predictions.main", fake_eval_main), \
         patch("automation.evaluation.settle_user_bets.settle_pending_bets", fake_settle):

        class FakeGames:
            def limit(self, _n):
                return self

            def stream(self):
                return []

        class FakeDoc:
            def __init__(self):
                self.id = "doc"

            def collection(self, _name):
                return FakeGames()

            def document(self, _id):
                return self

        class FakeClient:
            project = "test"

            def collection(self, _name):
                return FakeDoc()

        google_pkg = types.ModuleType("google")
        cloud_pkg = types.ModuleType("google.cloud")
        firestore_mod = types.ModuleType("google.cloud.firestore")
        firestore_mod.Client = FakeClient
        google_pkg.cloud = cloud_pkg
        cloud_pkg.firestore = firestore_mod
        sys.modules["google"] = google_pkg
        sys.modules["google.cloud"] = cloud_pkg
        sys.modules["google.cloud.firestore"] = firestore_mod

        import automation.pipeline.evaluation_pipeline as ep

        cfg = ep.EvaluationPipelineConfig(
            start_date="2025-01-01",
            end_date="2025-01-01",
            scrape_results_first=True,
            settle_user_bets=True,
            dry_run=False,
            verbose=False,
        )

        ep.run_evaluation_pipeline(cfg)
        fake_scrape_main.assert_called_once()
        fake_eval_main.assert_called_once()
        fake_settle.assert_called_once()


def test_run_prediction_pipeline(monkeypatch):
    _ensure_functions_on_path()
    _stub_firebase_and_config()

    import automation.pipeline.prediction_pipeline as pp

    monkeypatch.setattr(pp, "_load_feature_columns", lambda *_, **__: ["f1"])
    monkeypatch.setattr(pp, "_require_firebase_storage", lambda: None)

    class DummyModel:
        def __init__(self, val):
            self.val = val

        def predict(self, X):
            return [self.val] * len(X)

        def predict_proba(self, X):
            import numpy as np
            return np.array([[0.1, self.val] for _ in range(len(X))])

    make_preds_mod = pp.make_preds

    def fake_load_models(*_):
        return DummyModel(1.0), DummyModel(2.0), DummyModel(0.9)

    monkeypatch.setattr(make_preds_mod, "load_models", fake_load_models)
    monkeypatch.setattr(make_preds_mod, "_require_firebase_storage", lambda: None)
    monkeypatch.setattr(make_preds_mod, "_download_model_artifacts", lambda *_: {})
    monkeypatch.setattr(make_preds_mod, "_load_xgb_model", lambda artifacts, basename, model_type: DummyModel(0.0))
    make_preds_mod.firebase_admin = object()
    make_preds_mod.storage = object()

    published = {}

    def fake_publish(**kwargs):
        published["called"] = True
        published["args"] = kwargs

    monkeypatch.setattr(pp, "publish_predictions_to_firestore", fake_publish)

    features_df = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "team_key": "home",
                "opp_key": "away",
                "Team": "Home",
                "Opp": "Away",
                "Location": "Home",
                "bet_spread": -5.0,
                "bet_total": 140.0,
                "moneyline_a": -150,
                "moneyline_b": 130,
                "f1": 1.0,
            },
            {
                "game_id": "g1",
                "team_key": "away",
                "opp_key": "home",
                "Team": "Away",
                "Opp": "Home",
                "Location": "Away",
                "bet_spread": 5.0,
                "bet_total": 140.0,
                "moneyline_a": 130,
                "moneyline_b": -150,
                "f1": 1.0,
            },
        ]
    )

    monkeypatch.setattr(pp, "_download_features_df", lambda *_: features_df)
    dummy_ingest = types.SimpleNamespace(ingest_raw_for_range=lambda *_, **__: None)
    try:
        monkeypatch.setattr(pp.ingest_raw, "ingest_raw_for_range", lambda *_, **__: None)
    except AttributeError:
        monkeypatch.setattr(pp, "ingest_raw", dummy_ingest)
    monkeypatch.setattr(pp.build_features, "build_features_for_date", lambda *_: features_df)

    cfg = pp.PredictionPipelineConfig(
        start_date="2025-01-01",
        end_date="2025-01-01",
        skip_refresh=True,
        skip_ingest=True,
        skip_features=True,
        skip_publish=False,
        dry_run=False,
    )

    pp.run_prediction_pipeline(cfg)
    assert published.get("called")
