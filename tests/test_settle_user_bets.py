"""
Unit tests for automation.evaluation.settle_user_bets helpers.

These tests live outside the functions/ directory so they don't get bundled
into the Cloud Functions deployment. Firebase is stubbed to avoid network
calls on import.
"""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS_DIR = PROJECT_ROOT / "functions"


def _load_module_with_firebase_stub():
    """Load settle_user_bets with firebase_admin and config/evaluator stubbed out."""
    for name in list(sys.modules):
        if name.startswith("automation.config") or name.startswith("automation.evaluation"):
            sys.modules.pop(name, None)

    # Stub firebase_admin to prevent real initialization attempts.
    fake_fb = types.ModuleType("firebase_admin")
    fake_fb._apps = {"default": object()}
    fake_fb.initialize_app = lambda *_, **__: None
    fake_credentials = types.ModuleType("firebase_admin.credentials")
    fake_firestore = types.ModuleType("firebase_admin.firestore")
    fake_storage = types.ModuleType("firebase_admin.storage")
    fake_fb.credentials = fake_credentials
    fake_fb.firestore = fake_firestore
    fake_fb.storage = fake_storage
    sys.modules["firebase_admin"] = fake_fb
    sys.modules["firebase_admin.credentials"] = fake_credentials
    sys.modules["firebase_admin.firestore"] = fake_firestore
    sys.modules["firebase_admin.storage"] = fake_storage

    # Stub minimal automation package pieces needed for imports.
    automation_pkg = types.ModuleType("automation")
    automation_pkg.__path__ = [str(FUNCTIONS_DIR / "automation")]
    sys.modules["automation"] = automation_pkg

    config_pkg = types.ModuleType("automation.config")
    config_pkg.__path__ = [str(FUNCTIONS_DIR / "automation" / "config")]
    sys.modules["automation.config"] = config_pkg

    config_mod = types.ModuleType("automation.config.config")
    config_mod.FIRESTORE_PREDICTIONS_COLLECTION = "games"
    sys.modules["automation.config.config"] = config_mod

    eval_pkg = types.ModuleType("automation.evaluation")
    eval_pkg.__path__ = [str(FUNCTIONS_DIR / "automation" / "evaluation")]
    sys.modules["automation.evaluation"] = eval_pkg

    eval_mod = types.ModuleType("automation.evaluation.evaluate_predictions")
    eval_mod.DEFAULT_RESULT_DOC = "odds_api"

    def _noop(*_, **__):
        return None

    eval_mod._fetch_result_doc = _noop
    eval_mod._build_actual = _noop
    eval_mod._grade_moneyline_pick = _noop
    eval_mod._grade_spread_pick = _noop
    eval_mod._grade_total_pick = _noop
    eval_mod._resolve_pick = lambda *_: None
    sys.modules["automation.evaluation.evaluate_predictions"] = eval_mod

    sys.path.insert(0, str(FUNCTIONS_DIR))
    try:
        return importlib.import_module("automation.evaluation.settle_user_bets")
    finally:
        sys.path.pop(0)


@pytest.fixture(scope="module")
def settle_user_bets():
    return _load_module_with_firebase_stub()


def test_derive_game_date_prefers_game_id_prefix(settle_user_bets):
    bet_data = {"game_date": None}
    result = settle_user_bets._derive_game_date("2025-12-05-00123", bet_data)
    assert result == "2025-12-05"


def test_derive_game_date_handles_iso_string(settle_user_bets):
    bet_data = {"game_date": "2024-10-03T12:00:00"}
    result = settle_user_bets._derive_game_date(None, bet_data)
    assert result == "2024-10-03"


def test_clean_selection_strips_numbers_and_tokens(settle_user_bets):
    cleaned = settle_user_bets._clean_selection_for_team("Kansas State +7.5 ML")
    assert cleaned == "Kansas State"


def test_parse_line_from_selection(settle_user_bets):
    assert settle_user_bets._parse_line_from_selection("-7.5") == -7.5
    assert settle_user_bets._parse_line_from_selection("no number here") is None


def test_total_direction_detection(settle_user_bets):
    assert settle_user_bets._total_direction("Over 145.5") == "OVER"
    assert settle_user_bets._total_direction("under 132") == "UNDER"
    assert settle_user_bets._total_direction("no total") is None


def test_grade_moneyline_uses_clean_selection(monkeypatch, settle_user_bets):
    captured = {}

    def fake_grade_moneyline_pick(pick, game_data, actual):
        captured.update(pick)
        return {"result": "win"}

    monkeypatch.setattr(settle_user_bets.evaluator, "_grade_moneyline_pick", fake_grade_moneyline_pick)

    bet_data = {
        "type": "moneyline",
        "selection": "Kansas State ML +120",
        "odds": -110,
        "gameID": "2025-01-01-001",
    }
    game_data = {"home_team": "Kansas State", "away_team": "Iowa State"}
    actual = {}

    result = settle_user_bets._grade_user_bet(bet_data, game_data, actual)

    assert result == {"result": "win"}
    assert captured["selection"] == "Kansas State"  # cleaned selection
    assert captured["odds"] == -110
    assert captured["game_id"] == "2025-01-01-001"


def test_grade_spread_adjusts_line_for_home(monkeypatch, settle_user_bets):
    captured = {}

    monkeypatch.setattr(settle_user_bets.evaluator, "_resolve_pick", lambda selection, home, away: "home")

    def fake_grade_spread_pick(pick, game_data, actual):
        captured.update(pick)
        return {"result": "win"}

    monkeypatch.setattr(settle_user_bets.evaluator, "_grade_spread_pick", fake_grade_spread_pick)

    bet_data = {
        "type": "spread",
        "selection": "Villanova -3.5",
        "odds": -105,
        "gameID": "2025-01-02-002",
    }
    game_data = {"home_team": "Villanova", "away_team": "Kansas"}
    actual = {}

    result = settle_user_bets._grade_user_bet(bet_data, game_data, actual)

    assert result == {"result": "win"}
    assert captured["book_line"] == -3.5  # home side keeps bettor-facing sign
    assert captured["selection"] == "Villanova"
    assert captured["odds"] == -105


def test_grade_total_passes_direction(monkeypatch, settle_user_bets):
    captured = {}

    def fake_grade_total_pick(pick, game_data, actual):
        captured.update(pick)
        return {"result": "loss"}

    monkeypatch.setattr(settle_user_bets.evaluator, "_grade_total_pick", fake_grade_total_pick)

    bet_data = {
        "type": "total",
        "selection": "Under 145.5",
        "odds": -115,
        "gameID": "2025-01-03-003",
    }
    game_data = {"home_team": "Duke", "away_team": "UNC"}
    actual = {}

    result = settle_user_bets._grade_user_bet(bet_data, game_data, actual)

    assert result == {"result": "loss"}
    assert captured["selection"] == "UNDER"
    assert captured["book_line"] == 145.5
    assert captured["odds"] == -115
