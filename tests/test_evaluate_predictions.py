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
        "automation.config.utils",
        "automation.clients.firestore",
    ]:
        sys.modules.pop(name, None)

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
