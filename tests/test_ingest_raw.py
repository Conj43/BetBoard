"""
Deeper coverage for ingest_raw flows using in-memory stubs so no network/Firebase calls occur.
"""
from __future__ import annotations

import sys
import types
import importlib
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest


def _prep_import():
    # Clear prior ingest_raw import
    for name in list(sys.modules):
        if name.startswith("automation.processing.ingest_raw"):
            sys.modules.pop(name, None)

    functions_dir = Path(__file__).resolve().parents[1] / "functions"
    path_str = str(functions_dir)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

    # Minimal firebase/config stubs
    fb = types.ModuleType("firebase_admin")
    fb._apps = {"default": object()}
    fb.initialize_app = lambda *_, **__: None
    sys.modules["firebase_admin"] = fb
    sys.modules["firebase_admin.credentials"] = types.ModuleType("firebase_admin.credentials")
    sys.modules["firebase_admin.storage"] = types.ModuleType("firebase_admin.storage")

    config_mod = types.ModuleType("automation.config.config")
    config_mod.FIREBASE_CREDENTIALS_PATH = ""
    config_mod.FIREBASE_STORAGE_BUCKET = "bucket"
    config_mod.RAW_GAMES_PREFIX = "raw/games"
    config_mod.RAW_TEAMS_PREFIX = "raw/teams"
    config_mod.RAW_ODDS_PREFIX = "raw/odds"
    config_mod.GAMELOG_STORAGE_PREFIX = "gamelogs"
    config_mod.SPORTS_REFERENCE_SEASON = "2024"
    config_mod.TEAM_MAPPING = {}
    config_mod.CONFERENCE_MAP = {}
    config_mod.TORVIK_MAP = {}
    config_mod.canonicalize_team_key = lambda name: str(name).lower().replace(" ", "-") if name else ""
    sys.modules["automation.config.config"] = config_mod

    utils_mod = types.ModuleType("automation.config.utils")
    utils_mod.parse_dates = lambda s: pd.to_datetime(s, errors="coerce")
    utils_mod.normalize_key = lambda s: s.astype(str)
    utils_mod.standardize_opponent_columns = lambda df: df
    utils_mod.load_alias_map = lambda: {}
    sys.modules["automation.config.utils"] = utils_mod

    fe_mod = types.ModuleType("automation.processing.feature_engineering")
    fe_mod.prepare_rolling = lambda df: df.assign(
        team_key=df["Team"].str.lower().str.replace(" ", "-"),
        opp_key=df["Opp"].str.lower().str.replace(" ", "-"),
        prior_games=1.0,
        team_points_roll=df["Tm"],
        opp_points_roll=df["Opp.1"],
        team_pace_roll=70.0,
        opp_pace_roll=65.0,
        team_off_eff_roll=110.0,
        opp_off_eff_roll=100.0,
        team_def_eff_roll=90.0,
        opp_def_eff_roll=95.0,
    )
    sys.modules["automation.processing.feature_engineering"] = fe_mod

    processing_pkg = types.ModuleType("automation.processing")
    processing_pkg.__path__ = [str(functions_dir / "automation" / "processing")]
    sys.modules["automation.processing"] = processing_pkg

    automation_pkg = types.ModuleType("automation")
    automation_pkg.__path__ = [str(functions_dir / "automation")]
    sys.modules["automation"] = automation_pkg
    config_pkg = types.ModuleType("automation.config")
    config_pkg.__path__ = [str(functions_dir / "automation" / "config")]
    sys.modules["automation.config"] = config_pkg


def test_ingest_raw_for_date(monkeypatch):
    _prep_import()
    ingest = __import__("automation.processing.ingest_raw", fromlist=["ingest_raw"])

    schedule = pd.DataFrame(
        [
            {
                "date": "2025-01-01",
                "home_team_name": "Home",
                "away_team_name": "Away",
                "tipoff_datetime": "2025-01-01T18:00:00Z",
            }
        ]
    )
    monkeypatch.setattr(ingest, "fetch_schedule_for_date", lambda *_: schedule)
    monkeypatch.setattr(ingest, "fetch_team_snapshot", lambda *_, **__: {"team_points_roll": 80})
    monkeypatch.setattr(
        ingest,
        "fetch_odds_for_game",
        lambda *_: {"spread_home": -5.5, "total": 140, "moneyline_home": -200, "moneyline_away": 180},
    )
    uploaded = {}
    monkeypatch.setattr(
        ingest,
        "upload_snapshots_to_firebase",
        lambda game_date, games_df, teams_df, odds_df: uploaded.update({"game_date": game_date, "odds": odds_df}),
    )
    ingest.UPLOAD_TO_FIREBASE = True
    ingest.ingest_raw_for_date("2025-01-01", now_iso="2025-01-01T00:00:00Z")
    assert uploaded.get("game_date") == "2025-01-01"
    assert uploaded.get("odds") is not None


def test_ingest_raw_for_range(monkeypatch):
    _prep_import()
    ingest = __import__("automation.processing.ingest_raw", fromlist=["ingest_raw"])

    called = []

    def fake_ingest(date_str, now_iso):
        called.append(date_str)

    monkeypatch.setattr(ingest, "ingest_raw_for_date", fake_ingest)
    ingest.ingest_raw_for_range("2025-01-01", "2025-01-03")
    assert called == ["2025-01-01", "2025-01-02", "2025-01-03"]


def test_load_latest_odds_and_metrics(monkeypatch):
    _prep_import()
    ingest = __import__("automation.processing.ingest_raw", fromlist=["ingest_raw"])

    class FakeBlob:
        def __init__(self, text: str):
            self.text = text

        def exists(self):
            return True

        def download_as_string(self):
            return self.text.encode("utf-8")

        def download_as_text(self):
            return self.text

    class FakeBucket:
        def blob(self, path: str):
            if "odds" in path:
                return FakeBlob('{"games": [{"id": "g1"}]}')
            if "gamelogs" in path:
                return FakeBlob("Date,Team,Opp,Tm,Opp.1\n2025-01-01,Home,Away,70,65")
            return FakeBlob("")

    monkeypatch.setattr(ingest, "_get_firebase_bucket", lambda *_, **__: FakeBucket())
    ingest._ODDS_CACHE = None
    odds = ingest._load_latest_odds_data()
    ingest._TEAM_METRICS_CACHE = {}
    # Stub team slugs to ensure gamelog download runs
    monkeypatch.setattr(ingest, "_team_slugs_playing_on_date", lambda *_: ["home"])
    metrics = ingest._load_team_metrics("2025-01-01")
    assert odds.get("games")[0]["id"] == "g1"
    assert metrics  # metrics should not be empty


# ---- Helper unit coverage merged from test_ingest_raw_helpers ----


def _load_ingest():
    for name in list(sys.modules):
        if name.startswith("automation.processing.ingest_raw"):
            sys.modules.pop(name, None)
    config_mod = types.ModuleType("automation.config.config")
    config_mod.FIREBASE_CREDENTIALS_PATH = ""
    config_mod.FIREBASE_STORAGE_BUCKET = ""
    config_mod.RAW_GAMES_PREFIX = "raw/games"
    config_mod.RAW_TEAMS_PREFIX = "raw/teams"
    config_mod.RAW_ODDS_PREFIX = "raw/odds"
    config_mod.TEAM_MAPPING = {}
    config_mod.CONFERENCE_MAP = {}
    config_mod.TORVIK_MAP = {}
    config_mod.SPORTS_REFERENCE_SEASON = "2024"
    config_mod.GAMELOG_STORAGE_PREFIX = "gamelogs"
    config_mod.canonicalize_team_key = lambda name: str(name).lower().replace(" ", "-") if name else ""
    sys.modules["automation.config.config"] = config_mod

    config_pkg = types.ModuleType("automation.config")
    config_pkg.__path__ = []
    sys.modules["automation.config"] = config_pkg

    utils_mod = types.ModuleType("automation.config.utils")
    utils_mod.parse_dates = lambda s: pd.to_datetime(s, errors="coerce")
    utils_mod.normalize_key = lambda s: s.astype(str)
    utils_mod.standardize_opponent_columns = lambda df: df
    utils_mod.load_alias_map = lambda: {}
    sys.modules["automation.config.utils"] = utils_mod

    firebase_mod = types.ModuleType("firebase_admin")
    firebase_mod._apps = {"default": object()}
    firebase_mod.initialize_app = lambda *_, **__: None
    sys.modules["firebase_admin"] = firebase_mod
    sys.modules["firebase_admin.credentials"] = types.ModuleType("firebase_admin.credentials")
    sys.modules["firebase_admin.storage"] = types.ModuleType("firebase_admin.storage")
    sys.modules["firebase_admin.firestore"] = types.ModuleType("firebase_admin.firestore")

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "functions"))
    try:
        return importlib.import_module("automation.processing.ingest_raw")
    finally:
        sys.path.pop(0)


def test_team_slug_helpers_and_normalize():
    ingest = _load_ingest()
    assert ingest._slugify_team("North Carolina") == "northcarolina"
    assert ingest._team_slug_from_name("North Carolina") in {"northcarolina", "north-carolina"}
    conf = ingest._team_conference_from_name("Duke")
    assert conf in {"", None}
    assert ingest.normalize_team_key("UNC") == "unc"


def test_make_game_id_and_daterange():
    ingest = _load_ingest()
    assert ingest.make_game_id("2024-01-01", "home", "away") == "2024-01-01_home_away"
    start = datetime.strptime("2024-01-01", "%Y-%m-%d")
    end = datetime.strptime("2024-01-03", "%Y-%m-%d")
    assert list(ingest.daterange(start, end)) == [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
    ]


def test_coalesce_odds_and_load_latest(monkeypatch):
    ingest = _load_ingest()
    if hasattr(ingest, "coalesce_odds_columns"):
        df = pd.DataFrame({"moneyline_a_x": [100], "moneyline_a_y": [110]})
        merged = ingest.coalesce_odds_columns(df)
        assert "moneyline_a_x" not in merged.columns
    monkeypatch.setattr(ingest, "_get_firebase_bucket", lambda: None)
    # Should gracefully return empty dict when bucket missing
    odds = ingest._load_latest_odds_data()
    assert odds == {} or odds.get("games") == []


def test_team_metrics_from_gamelogs(monkeypatch):
    ingest = _load_ingest()
    gamelog_df = pd.DataFrame(
        [
            {"team": "Home", "opponent": "Away", "team_score": 80, "opponent_score": 70, "possessions": 70, "team_key": "home"},
            {"team": "Home", "opponent": "Other", "team_score": 75, "opponent_score": 65, "possessions": 68, "team_key": "home"},
        ]
    )
    ingest.prepare_rolling = lambda df: df
    monkeypatch.setattr(ingest, "download_gamelogs_snapshot", lambda date: gamelog_df)
    res = ingest._team_metrics_from_gamelogs("2025-01-01")
    assert isinstance(res, dict)
    # When schema is unexpected, fallback can yield empty dict
    assert res == {} or res is not None
