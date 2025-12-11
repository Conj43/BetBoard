"""
Unit tests for automation.evaluation.settle_user_bets helpers.
Updated with coverage for date derivation, parsing, and settlement logic.
"""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# --- Stubbing (reusing existing pattern) ---
def _load_settle_module():
    for name in list(sys.modules):
        if name.startswith("automation.config") or name.startswith("automation.evaluation"):
            sys.modules.pop(name, None)

    automation_pkg = types.ModuleType("automation")
    automation_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "functions" / "automation")]
    sys.modules["automation"] = automation_pkg

    config_pkg = types.ModuleType("automation.config")
    config_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "functions" / "automation" / "config")]
    sys.modules["automation.config"] = config_pkg

    eval_pkg = types.ModuleType("automation.evaluation")
    eval_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "functions" / "automation" / "evaluation")]
    sys.modules["automation.evaluation"] = eval_pkg

    fake_fb = types.ModuleType("firebase_admin")
    fake_fb.initialize_app = lambda *_, **__: None
    sys.modules["firebase_admin"] = fake_fb
    
    # Stub config
    config = types.ModuleType("automation.config.config")
    config.FIRESTORE_PREDICTIONS_COLLECTION = "predictions"
    config.TEAM_MAPPING = {}
    config.CONFERENCE_MAP = {}
    config.canonicalize_team_key = lambda name: str(name).lower().replace(" ", "-") if name else ""
    sys.modules["automation.config.config"] = config

    # Stub evaluator
    eval_mod = types.ModuleType("automation.evaluation.evaluate_predictions")
    eval_mod.DEFAULT_RESULT_DOC = "odds_api"
    eval_mod._grade_moneyline_pick = MagicMock(return_value={"result": "win"})
    eval_mod._grade_spread_pick = MagicMock(return_value={"result": "loss"})
    eval_mod._grade_total_pick = MagicMock(return_value={"result": "push"})
    eval_mod._resolve_pick = MagicMock(return_value="home")
    # Helper to return fake results
    eval_mod._fetch_result_doc = MagicMock(return_value={"home_score": 10})
    eval_mod._build_actual = MagicMock(return_value={"home_score": 10, "home_win": 1})
    sys.modules["automation.evaluation.evaluate_predictions"] = eval_mod

    import automation.evaluation.settle_user_bets as mod
    return mod

@pytest.fixture
def settle_mod():
    return _load_settle_module()

def test_derive_game_date(settle_mod):
    # Case 1: ID contains date
    assert settle_mod._derive_game_date("2025-01-01_game", {}) == "2025-01-01"
    # Case 2: Dict has string date
    assert settle_mod._derive_game_date(None, {"gameDate": "2025-02-02"}) == "2025-02-02"
    # Case 3: None
    assert settle_mod._derive_game_date("invalid_id", {}) is None

def test_clean_selection(settle_mod):
    assert settle_mod._clean_selection_for_team("Duke -3.5") == "Duke"
    assert settle_mod._clean_selection_for_team("UNC Moneyline") == "UNC"
    assert settle_mod._clean_selection_for_team("Over 145.5") == ""

def test_total_direction(settle_mod):
    assert settle_mod._total_direction("Over 150") == "OVER"
    assert settle_mod._total_direction("Under 140") == "UNDER"
    assert settle_mod._total_direction("Kansas") is None

def test_grade_user_bet_dispatch(settle_mod):
    """Test that correct evaluator functions are called based on bet type."""
    game = {"home_team": "H", "away_team": "A"}
    actual = {"home_win": 1}
    
    # Moneyline
    bet_ml = {"type": "moneyline", "selection": "H", "odds": -110}
    settle_mod._grade_user_bet(bet_ml, game, actual)
    settle_mod.evaluator._grade_moneyline_pick.assert_called()
    
    # Spread
    bet_spread = {"type": "spread", "selection": "H -3.5", "odds": -110}
    settle_mod._grade_user_bet(bet_spread, game, actual)
    settle_mod.evaluator._grade_spread_pick.assert_called()

def test_settle_pending_bets_logic(settle_mod):
    """Test the iteration and update logic of settle_pending_bets."""
    mock_db = MagicMock()
    
    # Setup mock user -> bets -> bet_doc
    mock_bet = MagicMock()
    mock_bet.to_dict.return_value = {
        "gameID": "2025-01-01_g1", 
        "type": "moneyline", 
        "selection": "H", 
        "result": "pending"
    }
    mock_bet.reference.path = "users/u1/bets/b1"
    
    mock_user = MagicMock()
    # Chain: users -> stream -> user -> bets -> where -> stream -> [bet]
    mock_db.collection.return_value.stream.return_value = [mock_user]
    mock_user.reference.collection.return_value.where.return_value.stream.return_value = [mock_bet]
    
    # Mock helpers to ensure flow proceeds to update
    with patch("automation.evaluation.settle_user_bets._fetch_game_and_actual", 
               return_value=({"home_team": "H", "away_team": "A"}, {"final": True})):
        
        summary = settle_mod.settle_pending_bets(mock_db)
        
        assert summary["updated"] == 1
        # Check that update was called with the result from our stubbed evaluator ("win")
        mock_bet.reference.update.assert_called_with({"result": "won"}) # Mapped from "win" -> "won"
