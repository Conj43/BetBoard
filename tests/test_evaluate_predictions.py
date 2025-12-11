"""
Unit tests for automation.evaluation.evaluate_predictions helpers.

Lives outside the functions/ folder to avoid being deployed with Cloud
Functions. Firebase is stubbed so imports do not attempt real initialization.
"""
from __future__ import annotations

import importlib
import sys
import types
from argparse import Namespace
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS_DIR = PROJECT_ROOT / "functions"


def _load_eval_module():
    """Load evaluate_predictions with firebase_admin stubbed out."""
    for name in [
        "automation.evaluation.evaluate_predictions",
        "automation.config.config",
        "automation.config.team_keys",
        "automation.config.utils",
        "automation.clients.firestore",
    ]:
        sys.modules.pop(name, None)

    # Minimal package skeleton so imports resolve to stubs
    automation_pkg = types.ModuleType("automation")
    automation_pkg.__path__ = [str(FUNCTIONS_DIR / "automation")]
    sys.modules["automation"] = automation_pkg

    automation_config_pkg = types.ModuleType("automation.config")
    automation_config_pkg.__path__ = [str(FUNCTIONS_DIR / "automation" / "config")]
    sys.modules["automation.config"] = automation_config_pkg

    config_mod = types.ModuleType("automation.config.config")
    config_mod.FIRESTORE_PREDICTIONS_COLLECTION = "games"
    config_mod.TEAM_MAPPING = {}
    config_mod.CONFERENCE_MAP = {}
    def _canon(name):
        cleaned = "".join(ch if ch.isalnum() else " " for ch in str(name).lower())
        return "-".join(cleaned.split())

    config_mod.canonicalize_team_key = lambda name: _canon(name) if name else ""
    sys.modules["automation.config.config"] = config_mod

    team_keys_mod = types.ModuleType("automation.config.team_keys")
    team_keys_mod.TEAM_MAPPING = {}
    team_keys_mod.CONFERENCE_MAP = {}
    team_keys_mod.canonicalize_team_key = lambda name: _canon(name) if name else ""
    sys.modules["automation.config.team_keys"] = team_keys_mod

    utils_mod = types.ModuleType("automation.config.utils")
    utils_mod.load_alias_map = lambda: {}
    utils_mod._ALIAS_MAP_CACHE = None
    sys.modules["automation.config.utils"] = utils_mod

    clients_pkg = types.ModuleType("automation.clients")
    clients_pkg.__path__ = []
    sys.modules["automation.clients"] = clients_pkg

    firestore_mod = types.ModuleType("automation.clients.firestore")
    firestore_mod._ensure_firestore = lambda *_, **__: None
    sys.modules["automation.clients.firestore"] = firestore_mod

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

    sys.path.insert(0, str(FUNCTIONS_DIR))
    try:
        return importlib.import_module("automation.evaluation.evaluate_predictions")
    finally:
        sys.path.pop(0)


@pytest.fixture(scope="module")
def eval_mod():
    return _load_eval_module()


def test_resolve_dates_range(eval_mod):
    args = Namespace(
        date=None,
        start_date="2025-01-01",
        end_date="2025-01-03",
        result_source=None,
        collection=None,
        dry_run=False,
        verbose=False,
    )
    dates = eval_mod._resolve_dates(args)
    assert dates == ["2025-01-01", "2025-01-02", "2025-01-03"]


def test_resolve_dates_single(eval_mod):
    args = Namespace(
        date="2025-02-10",
        start_date=None,
        end_date=None,
        result_source=None,
        collection=None,
        dry_run=False,
        verbose=False,
    )
    dates = eval_mod._resolve_dates(args)
    assert dates == ["2025-02-10"]


def test_american_to_decimal(eval_mod):
    assert eval_mod._american_to_decimal(-110) == pytest.approx(1.9091, rel=1e-4)
    assert eval_mod._american_to_decimal(150) == 2.5
    assert eval_mod._american_to_decimal(0) is None
    assert eval_mod._american_to_decimal(None) is None


def test_validate_odds(eval_mod):
    assert eval_mod._validate_odds(-110) is True
    assert eval_mod._validate_odds(10000) is True
    assert eval_mod._validate_odds(10001) is False
    assert eval_mod._validate_odds(50) is False
    assert eval_mod._validate_odds(None) is False
    assert eval_mod._validate_odds(99) is False


def test_resolve_dates_requires_both_bounds(eval_mod):
    args = Namespace(
        date=None,
        start_date="2025-01-01",
        end_date=None,
        result_source=None,
        collection=None,
        dry_run=False,
        verbose=False,
    )
    with pytest.raises(ValueError):
        eval_mod._resolve_dates(args)


def test_simulate_flat_bets(eval_mod):
    bets = [
        {"result": "win", "odds": 100},
        {"result": "loss", "odds": -110},
        {"result": "push", "odds": -105},
    ]
    summary = eval_mod._simulate_flat_bets(bets, initial_bankroll=1000, stake_size=25)
    assert summary == {
        "final_bankroll": 1000.0,
        "roi": 0.0,
        "bets": 3,
        "wins": 1,
        "losses": 1,
        "pushes": 1,
        "total_wagered": 50.0,
    }


def test_simulate_quarter_kelly(eval_mod):
    bets = [
        {"result": "win", "odds": -110, "prob": 0.6},
        {"result": "loss", "odds": 150, "prob": 0.55},
    ]
    summary = eval_mod._simulate_quarter_kelly(bets, initial_bankroll=1000, fraction=0.25)
    assert summary is not None
    assert summary["final_bankroll"] == pytest.approx(971.59, rel=1e-3)
    assert summary["roi"] == pytest.approx(-0.0284, rel=1e-3)
    assert summary["bets"] == 2
    assert summary["wins"] == 1
    assert summary["losses"] == 1
    assert summary["pushes"] == 0
    assert summary["total_wagered"] == pytest.approx(104.77, rel=1e-3)


def test_simulate_flat_bets_returns_none_on_invalid(eval_mod):
    bets = [
        {"result": "win", "odds": None},
        {"result": "loss", "odds": 50},  # invalid range
    ]
    assert eval_mod._simulate_flat_bets(bets, initial_bankroll=1000, stake_size=25) is None


def test_simulate_quarter_kelly_returns_none_on_invalid(eval_mod):
    bets = [
        {"result": "win", "odds": 0, "prob": 0.5},  # zero odds
        {"result": "loss", "odds": 150, "prob": None},  # missing prob
    ]
    assert eval_mod._simulate_quarter_kelly(bets, initial_bankroll=1000, fraction=0.25) is None


def test_normalize_team(eval_mod):
    normalized = eval_mod._normalize_team("North Carolina!!")
    assert normalized == "north-carolina"


def test_normalize_team_handles_non_string(eval_mod):
    assert eval_mod._normalize_team(None) == ""
    assert eval_mod._normalize_team(123) == ""

def test_build_actual_and_resolve_pick(eval_mod):
    doc = {"home_score": 80, "away_score": 70}
    actual = eval_mod._build_actual(doc)
    assert actual["margin"] == 10
    assert actual["home_win"] == 1

    eval_mod._ALIAS_MAP = {}
    assert eval_mod._resolve_pick("Home", "Home", "Away") == "home"
    assert eval_mod._resolve_pick("away", "Home", "Away") == "away"
    assert eval_mod._resolve_pick("team_a", "Home", "Away") == "home"
    assert eval_mod._resolve_pick("unknown", "Home", "Away") is None


def test_odds_and_profit_helpers(eval_mod):
    assert eval_mod._odds_to_implied_prob(-110) == pytest.approx(0.5238, rel=1e-3)
    assert eval_mod._odds_to_implied_prob(50) is None
    assert eval_mod._flat_profit("win", -110, None) == pytest.approx(22.73, rel=1e-2)
    assert eval_mod._flat_profit("loss", -110, None) == -25.0
    assert eval_mod._flat_profit("push", -110, None) == 0.0
    assert eval_mod._flat_profit("weird", -110, None) is None


def test_grade_moneyline_pick_variants(eval_mod, caplog):
    game = {"home_team": "Home", "away_team": "Away", "moneyline": {"p_win_home": 0.6, "odds_home": -120, "odds_away": 150}}
    actual = {"home_win": 1, "home_score": 80, "away_score": 70}

    eval_mod._resolve_pick = lambda *_, **__: "home"
    pick = {"selection": "Home", "odds": None}
    graded = eval_mod._grade_moneyline_pick(pick, game, actual)
    assert graded["result"] == "win"

    bad_pick = {"selection": "Home", "odds": 50}
    assert eval_mod._grade_moneyline_pick(bad_pick, game, actual) is None

    eval_mod._ALIAS_MAP = {"home": "home", "away": "away"}
    eval_mod._resolve_pick = lambda *_, **__: "home"
    push_pick = {"selection": "Home", "odds": -120}
    actual_push = {"home_win": None, "home_score": 75, "away_score": 75}
    assert eval_mod._grade_moneyline_pick(push_pick, game, actual_push) is None


def test_grade_spread_and_total(eval_mod):
    game = {
        "home_team": "Home",
        "away_team": "Away",
        "spread": {"predicted_margin": 5.0, "line": -3.5},
        "total": {"predicted_total": 150.0, "line": 140.0},
    }
    actual = {"home_score": 80, "away_score": 70, "margin": 10, "total": 150}

    eval_mod._resolve_pick = lambda *_, **__: "home"
    spread_pick = {"selection": "Home", "odds": None, "book_line": None}
    graded_spread = eval_mod._grade_spread_pick(spread_pick, game, actual)
    assert graded_spread["result"] == "win"
    assert graded_spread["odds"] == eval_mod.SPREAD_TOTAL_DEFAULT_ODDS

    eval_mod._resolve_pick = lambda *_, **__: "away"
    spread_push = {"selection": "Away", "odds": -105, "book_line": 10}
    graded_push = eval_mod._grade_spread_pick(spread_push, game, {"home_score": 80, "away_score": 70, "margin": 10, "total": 150})
    assert graded_push["result"] == "push"

    total_pick = {"selection": "UNDER", "book_line": 155, "odds": -110}
    graded_total = eval_mod._grade_total_pick(total_pick, game, actual)
    assert graded_total["result"] == "win"

    bad_total = {"selection": "INVALID", "book_line": 150}
    assert eval_mod._grade_total_pick(bad_total, game, actual) is None

# --- ADD THESE TO tests/test_evaluate_predictions.py ---

def test_evaluate_perfect_predictions(eval_mod):
    """
    Scenario: All predictions are correct.
    Verifies maximum performance metrics (100% accuracy).
    """
    # Mock specific game data
    game_data = {
        "moneyline": {"p_win_home": 0.9, "odds_home": -500, "odds_away": 400},
        "spread": {"predicted_margin": 10.0, "line": -5.0}, # Predicted Home by 10, Line Home -5 (Favored)
        "total": {"predicted_total": 150.0, "line": 140.0}  # Predicted 150, Line 140 -> OVER
    }
    
    # Actual result matches predictions perfectly
    actual = {
        "home_score": 80,
        "away_score": 65,
        "margin": 15,   # Covers -5 spread
        "total": 145,   # Over 140
        "home_win": 1
    }
    
    stats = eval_mod._init_stats()
    
    eval_mod._evaluate_moneyline_model(game_data, actual, stats["moneyline"])
    eval_mod._evaluate_spread_model(game_data, actual, stats["spread"])
    eval_mod._evaluate_total_model(game_data, actual, stats["total"])
    
    # Check Moneyline
    assert stats["moneyline"].winner_correct == 1
    
    # Check Spread (Covered)
    assert stats["spread"].correct == 1
    
    # Check Total (Predicted Over, Actual Over)
    assert stats["total"].correct == 1

def test_evaluate_zero_accuracy(eval_mod):
    """
    Scenario: All predictions are wrong.
    Verifies handling of complete failure (0% accuracy).
    """
    game_data = {
        "moneyline": {"p_win_home": 0.9}, # Predicted Home Win
        "spread": {"predicted_margin": 10.0, "line": -5.0}, # Predicted Cover
        "total": {"predicted_total": 150.0, "line": 140.0}  # Predicted Over
    }
    
    actual = {
        "home_score": 50,
        "away_score": 60,
        "margin": -10,  # Home Lost
        "total": 110,   # Under
        "home_win": 0
    }
    
    stats = eval_mod._init_stats()
    
    eval_mod._evaluate_moneyline_model(game_data, actual, stats["moneyline"])
    eval_mod._evaluate_spread_model(game_data, actual, stats["spread"])
    eval_mod._evaluate_total_model(game_data, actual, stats["total"])
    
    assert stats["moneyline"].winner_correct == 0
    assert stats["spread"].correct == 0
    assert stats["total"].correct == 0

def test_evaluate_push_logic(eval_mod):
    """
    Scenario: Mixed case with a Push.
    Verifies that pushes are excluded from win/loss counts but tracked separately.
    """
    game_data = {
        "spread": {"predicted_margin": 5.0, "line": -5.0} # Line is Home -5
    }
    actual = {
        "margin": 5, # Exactly 5 point win
        "home_win": 1
    }
    
    stats = eval_mod.MarketStats()
    eval_mod._evaluate_spread_model(game_data, actual, stats)
    
    assert stats.pushes == 1
    assert stats.correct == 0 # Push is not a win


# --- Append to existing test_evaluate_predictions.py ---

def test_evaluate_moneyline_model_betting_logic(eval_mod):
    """Test that moneyline bets are placed only when EV is positive."""
    stats = eval_mod.MarketStats()
    # Model says 60% win prob. 
    # Case 1: Odds +100 (Implied 50%) -> Edge -> Should Bet
    game_data_good = {
        "moneyline": {"p_win_home": 0.60, "odds_home": 100, "odds_away": -120}
    }
    actual = {"home_win": 1}
    eval_mod._evaluate_moneyline_model(game_data_good, actual, stats)
    assert len(stats.bets) == 1
    assert stats.bets[0]["result"] == "win"

    # Case 2: Odds -200 (Implied 66%) -> No Edge -> No Bet
    stats.bets = []
    game_data_bad = {
        "moneyline": {"p_win_home": 0.60, "odds_home": -200, "odds_away": -500}
    }
    eval_mod._evaluate_moneyline_model(game_data_bad, actual, stats)
    assert len(stats.bets) == 0

def test_validate_odds_boundaries(eval_mod):
    """Expand odds validation."""
    assert eval_mod._validate_odds(100) is True
    assert eval_mod._validate_odds(-10000) is True
    assert eval_mod._validate_odds(-10001) is False # Too small
    assert eval_mod._validate_odds(50) is False # Too close to zero (invalid American)
    assert eval_mod._validate_odds(0) is False

def test_simulate_flat_bets_invalid_inputs(eval_mod):
    """Ensure robustness against bad data."""
    # Odds of None should be skipped
    bets = [{"result": "win", "odds": None}]
    res = eval_mod._simulate_flat_bets(bets)
    assert res is None # No valid bets placed

def test_normalize_team_edge_cases(eval_mod):
    """Test non-string normalization."""
    assert eval_mod._normalize_team(123) == ""
    assert eval_mod._normalize_team(None) == ""
    assert eval_mod._normalize_team("  Duke  ") == "duke"


# ---- Additional coverage merged from extended/more/flow suites ----


def test_resolve_dates_errors():
    eval_mod = _load_eval_module()
    args = Namespace(date=None, start_date="2025-01-02", end_date=None)
    with pytest.raises(ValueError):
        eval_mod._resolve_dates(args)

    args_bad = Namespace(date=None, start_date="2025-02-30", end_date="2025-03-01")
    with pytest.raises(ValueError):
        eval_mod._resolve_dates(args_bad)


def test_simulate_quarter_kelly_edge_cases():
    eval_mod = _load_eval_module()
    bets = [{"result": "win", "odds": -110, "prob": 0.0}]
    # prob <= 0 leads to None
    assert eval_mod._simulate_quarter_kelly(bets, initial_bankroll=0, fraction=0.25) is None

    bad_bets = [{"result": "win", "odds": None, "prob": None}]
    assert eval_mod._simulate_quarter_kelly(bad_bets) is None


def test_evaluate_total_model_push_and_invalid():
    eval_mod = _load_eval_module()
    stats = eval_mod.MarketStats()
    game = {"total": {"predicted_total": 150.0, "line": 145.0, "pick": "over"}}
    actual = {"total": 145, "home_win": 1}
    eval_mod._evaluate_total_model(game, actual, stats)
    assert stats.pushes == 1  # total == line -> push

    stats2 = eval_mod.MarketStats()
    bad_game = {"total": {"predicted_total": "abc", "line": None}}
    eval_mod._evaluate_total_model(bad_game, actual, stats2)  # should no-op safely
    assert stats2.count == 0


def test_evaluate_spread_model_invalid_inputs(caplog):
    eval_mod = _load_eval_module()
    stats = eval_mod.MarketStats()
    game = {"spread": {"predicted_margin": "abc", "line": "bad"}}
    actual = {"margin": 5, "home_win": 1}
    eval_mod._evaluate_spread_model(game, actual, stats)
    assert stats.count == 0


def test_grade_total_pick_invalid_and_default_odds():
    eval_mod = _load_eval_module()
    game = {"total": {"line": 150.0, "predicted_total": 155}}
    actual = {"total": 145}

    bad_pick = {"selection": "SIDEWAYS", "book_line": 150}
    assert eval_mod._grade_total_pick(bad_pick, game, actual) is None

    pick = {"selection": "OVER", "book_line": None, "odds": None}
    graded = eval_mod._grade_total_pick(pick, game, {"total": 145, "home_score": 80, "away_score": 70})
    assert graded["odds"] == eval_mod.SPREAD_TOTAL_DEFAULT_ODDS


def test_build_actual_invalid_scores():
    eval_mod = _load_eval_module()
    bad_doc = {"home_score": "N/A", "away_score": 70}
    assert eval_mod._build_actual(bad_doc) is None


def test_grade_moneyline_pick_push_on_unknown():
    eval_mod = _load_eval_module()
    game_data = {"home_team": "Home", "away_team": "Away", "moneyline": {}}
    pick = {"selection": "Home", "odds": 100}
    actual = {"home_win": None, "home_score": 80, "away_score": 70}
    graded = eval_mod._grade_moneyline_pick(pick, game_data, actual)
    assert graded is None  # cannot resolve without odds/team mapping


def test_grade_spread_pick_invalid_line(monkeypatch):
    eval_mod = _load_eval_module()
    game = {"spread": {"line": None}}
    pick = {"selection": "Home", "book_line": "bad"}
    actual = {"margin": 5, "home_score": 80, "away_score": 70}
    assert eval_mod._grade_spread_pick(pick, game, actual) is None


def test_finalize_market_payload_empty(eval_mod):
    empty_stats = eval_mod.MarketStats()
    payload = eval_mod._finalize_market_payload(empty_stats, include_logloss=True, include_kelly=True, is_moneyline=True)
    assert payload["count"] == 0
    assert "flat_betting" not in payload


def test_evaluate_recommended_picks_invalid_bet_type(eval_mod, caplog):
    game = {"recommended": [{"bet_type": "weird", "selection": "Home"}]}
    actual = {"home_win": 1, "margin": 5, "total": 150, "home_score": 80, "away_score": 70}
    stats = {
        "moneyline": eval_mod.MarketStats(),
        "spread": eval_mod.MarketStats(),
        "total": eval_mod.MarketStats(),
    }
    graded = eval_mod._evaluate_recommended_picks(game, actual, stats)
    assert graded == []


def test_parse_args_defaults():
    eval_mod = _load_eval_module()
    args = eval_mod.parse_args([])
    assert args.collection == eval_mod.DEFAULT_EVAL_COLLECTION
    assert args.result_source == eval_mod.DEFAULT_RESULT_DOC


def test_evaluate_moneyline_model_tracks_metrics_and_bet():
    eval_mod = _load_eval_module()
    stats = eval_mod.MarketStats()
    game = {
        "home_team": "Home",
        "away_team": "Away",
        "moneyline": {"p_win_home": 0.65, "odds_home": -125, "odds_away": 115},
    }
    eval_mod._evaluate_moneyline_model(game, {"home_win": 1}, stats)
    assert stats.count == 1
    assert stats.winner_correct == 1  # predicted winner correct
    assert stats.bets and stats.bets[0]["result"] == "win"
    assert stats.mae_sum > 0 and stats.logloss_sum > 0


def test_evaluate_recommended_picks_accumulates_stats_and_bets():
    eval_mod = _load_eval_module()
    stats = {
        "moneyline": eval_mod.MarketStats(),
        "spread": eval_mod.MarketStats(),
        "total": eval_mod.MarketStats(),
    }
    game = {
        "home_team": "Home",
        "away_team": "Away",
        "moneyline": {"p_win_home": 0.6},
        "spread": {"line": -3.5, "predicted_margin": 4.5},
        "total": {"line": 145.0, "predicted_total": 152.0},
        "recommended": [
            {"bet_type": "moneyline", "selection": "Home", "odds": -110, "odds_to_prob": 0.6},
            {"bet_type": "spread", "selection": "Away", "book_line": 3.5, "odds": -110, "edge_strength": 0.1},
            {"bet_type": "total", "selection": "OVER", "book_line": 145.0, "odds": -105, "edge_strength": 0.1},
        ],
    }
    graded = eval_mod._evaluate_recommended_picks(game, eval_mod._build_actual({"home_score": 78, "away_score": 72}), stats)
    assert len(graded) == 3
    assert stats["moneyline"].count == 1
    assert stats["spread"].count == 1
    assert stats["total"].count == 1
    assert stats["moneyline"].logloss_sum > 0  # logloss applied
    assert stats["spread"].mae_sum > 0 and stats["total"].mae_sum > 0
    # Bets captured for flat/kelly calculations
    assert stats["moneyline"].bets and stats["spread"].bets and stats["total"].bets


def test_finalize_market_payload_includes_betting_blocks():
    eval_mod = _load_eval_module()
    stats = eval_mod.MarketStats(
        count=2,
        correct=1,
        pushes=0,
        mae_sum=1.0,
        logloss_sum=0.5,
        bets=[
            {"odds": -110, "result": "win", "prob": 0.6},
            {"odds": -105, "result": "loss", "prob": 0.4},
        ],
        winner_correct=2,
    )
    payload = eval_mod._finalize_market_payload(
        stats,
        include_logloss=True,
        include_kelly=True,
        is_moneyline=True,
    )
    assert payload["winner_accuracy"] == 1.0
    assert payload["mae"] > 0
    assert "flat_betting" in payload and "total_profit" in payload
    assert "quarter_kelly" in payload  # kelly results added when bets + prob present


def test_evaluate_date_and_merge_helpers(monkeypatch):
    eval_mod = _load_eval_module()

    class _FakeSnap:
        def __init__(self, data):
            self._data = data
            self.reference = object()

        def to_dict(self):
            return dict(self._data)

    class _FakeGamesCollection:
        def __init__(self, snaps):
            self._snaps = snaps

        def stream(self):
            return iter(self._snaps)

    class _FakeEvalCollection:
        def __init__(self):
            self.docs = []
            self.set_calls = []

        def document(self, doc_id):
            return self

        def set(self, payload):
            self.set_calls.append(payload)

        def stream(self):
            payload = {
                "date": "2025-01-01",
                "games_evaluated": 1,
                "all_predictions": {
                    "moneyline": {"count": 1, "pushes": 0, "mae": 0.1, "logloss": 0.2, "winner_accuracy": 1.0, "betting_accuracy": 1.0},
                    "spread": {"count": 1, "pushes": 0, "mae": 2.0, "accuracy": 1.0},
                    "total": {"count": 1, "pushes": 0, "mae": 3.0, "accuracy": 1.0},
                },
                "recommended": {
                    "moneyline": {"count": 1, "pushes": 0, "mae": 0.1, "logloss": 0.2, "winner_accuracy": 1.0, "betting_accuracy": 1.0},
                    "spread": {"count": 1, "pushes": 0, "mae": 2.0, "accuracy": 1.0},
                    "total": {"count": 1, "pushes": 0, "mae": 3.0, "accuracy": 1.0},
                },
            }
            return iter([types.SimpleNamespace(id="2025-01-01", to_dict=lambda: payload)])

        def batch(self):
            return types.SimpleNamespace(set=lambda *_, **__: None, commit=lambda: None)

    class _FakeDB:
        def __init__(self, snaps):
            self._snaps = snaps
            self.eval_collection = _FakeEvalCollection()

        def collection(self, name):
            if name == "games":
                return types.SimpleNamespace(document=lambda _date: types.SimpleNamespace(collection=lambda _name: _FakeGamesCollection(self._snaps)))
            return self.eval_collection

    # Fake snapshots for one game
    game_data = {
        "home_team": "Home",
        "away_team": "Away",
        "moneyline": {"p_win_home": 0.6, "odds_home": -110, "odds_away": 100},
        "spread": {"predicted_margin": 5.0, "line": -4.0},
        "total": {"predicted_total": 150.0, "line": 148.0},
        "recommended": [{"bet_type": "moneyline", "selection": "Home", "odds": -110}],
    }
    snaps = [_FakeSnap(game_data)]
    fake_db = _FakeDB(snaps)

    # Force _fetch_result_doc to return a valid result
    monkeypatch.setattr(eval_mod, "_fetch_result_doc", lambda *_, **__: {"home_score": 80, "away_score": 74})
    payload = eval_mod.evaluate_date("2025-01-01", fake_db, "odds_api")
    assert payload["games_evaluated"] == 1
    assert payload["all_predictions"]["moneyline"]["count"] == 1

    # Merge helpers aggregate counts/sums
    dest = eval_mod._init_stats()
    src = eval_mod._init_stats()
    src["games"] = 2
    src["moneyline"].count = 1
    src["moneyline"].mae_sum = 0.4
    eval_mod._merge_stats(dest, src)
    assert dest["games"] == 2
    assert dest["moneyline"].mae_sum == 0.4

    rec_dest = eval_mod._init_recommended_stats()
    rec_src = eval_mod._init_recommended_stats()
    rec_src["spread"].count = 1
    rec_src["spread"].mae_sum = 1.0
    eval_mod._merge_recommended_stats(rec_dest, rec_src)
    assert rec_dest["spread"].mae_sum == 1.0


def test_parse_args_and_main_dry_run(monkeypatch):
    eval_mod = _load_eval_module()

    args = eval_mod.parse_args(["--date", "2025-01-02", "--collection", "evals", "--result-source", "odds", "--dry-run"])
    assert args.date == "2025-01-02"
    assert args.collection == "evals"
    assert args.result_source == "odds"
    assert args.dry_run is True

    # Stub firestore and evaluation to avoid external calls
    class _FakeEvalCollection:
        def document(self, _id):
            return self

        def stream(self):
            return []

    fake_db = types.SimpleNamespace(
        collection=lambda name: _FakeEvalCollection(),
    )
    monkeypatch.setattr(eval_mod, "_ensure_firestore", lambda: fake_db)
    monkeypatch.setattr(eval_mod, "evaluate_date", lambda date, db, src: {"date": date, "games_evaluated": 0, "all_predictions": {}, "recommended": {}, "_graded_picks": []})
    eval_mod.main(["--date", "2025-01-02", "--collection", "evals", "--result-source", "odds", "--dry-run"])
