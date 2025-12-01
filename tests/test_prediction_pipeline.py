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

import pytest

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
    sys.modules["automation.prediction.make_preds"] = make_preds

    processing_pkg = types.ModuleType("automation.processing")
    processing_pkg.__path__ = []
    sys.modules["automation.processing"] = processing_pkg
    sys.modules["automation.processing.build_features"] = types.ModuleType("automation.processing.build_features")
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
        {"game_id": "G1", "bet_type": "moneyline", "edge_strength": 7.0},
        {"game_id": "G3", "bet_type": "total", "edge_strength": 6.0},
        {"game_id": "G1", "bet_type": "spread", "edge_strength": 5.0},
        {"game_id": "G2", "bet_type": "moneyline", "edge_strength": 4.0},
        {"game_id": "G4", "bet_type": "spread", "edge_strength": 3.0},
        {"game_id": "G5", "bet_type": "moneyline", "edge_strength": 3.0},
        {"game_id": "G6", "bet_type": "moneyline", "edge_strength": 2.0},
    ]
    top = pipeline_mod._build_top_recommendations(picks, max_picks=4)
    assert len(top) == 4
    assert len({p["game_id"] for p in top}) == 4  # one per game
    assert sum(1 for p in top if p["bet_type"] == "spread") <= 3
    assert sum(1 for p in top if p["bet_type"] == "moneyline") <= 3
    assert sum(1 for p in top if p["bet_type"] == "total") <= 3
    # Spread pick from G1 should block moneyline from same game
    assert {"G1", "G4"} <= {p["game_id"] for p in top}


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
