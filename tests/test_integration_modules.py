"""
Integration-style tests that exercise broader workflows with light stubbing.

These tests avoid network/Firebase by providing in-memory stubs but still
drive more of each module's logic to improve coverage.
"""
from __future__ import annotations

import importlib
import sys
import types
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS_DIR = PROJECT_ROOT / "functions"


def _stub_base_modules():
    """Seed minimal automation/config/firebase stubs before importing modules."""
    for name in list(sys.modules):
        if name.startswith(("automation.config", "automation.clients", "automation.processing", "automation.prediction", "automation.evaluation")):
            sys.modules.pop(name, None)

    # Base package skeleton
    automation_pkg = types.ModuleType("automation")
    automation_pkg.__path__ = [str(FUNCTIONS_DIR / "automation")]
    sys.modules["automation"] = automation_pkg

    config_pkg = types.ModuleType("automation.config")
    config_pkg.__path__ = [str(FUNCTIONS_DIR / "automation" / "config")]
    sys.modules["automation.config"] = config_pkg

    # Config module stub with required constants/helpers
    config_mod = types.ModuleType("automation.config.config")
    config_mod.FIRESTORE_PREDICTIONS_COLLECTION = "games"
    config_mod.FIREBASE_CREDENTIALS_PATH = ""
    config_mod.FIREBASE_STORAGE_BUCKET = "bucket"
    config_mod.RAW_GAMES_PREFIX = "raw/games"
    config_mod.RAW_TEAMS_PREFIX = "raw/teams"
    config_mod.RAW_ODDS_PREFIX = "raw/odds"
    config_mod.PROCESSED_FEATURES_PREFIX = "processed"
    config_mod.GAMELOG_STORAGE_PREFIX = "gamelogs"
    config_mod.SPORTS_REFERENCE_SEASON = "2024"
    config_mod.TEAM_MAPPING = {}
    config_mod.CONFERENCE_MAP = {}
    config_mod.TORVIK_MAP = {}
    config_mod.CANONICAL_BET_COLS = []

    def _canon(name):
        cleaned = "".join(ch if ch.isalnum() else " " for ch in str(name).lower())
        return "-".join(cleaned.split())

    config_mod.canonicalize_team_key = lambda name: _canon(name) if name else ""
    sys.modules["automation.config.config"] = config_mod

    team_keys_mod = types.ModuleType("automation.config.team_keys")
    team_keys_mod.TEAM_MAPPING = {}
    team_keys_mod.CONFERENCE_MAP = {}
    team_keys_mod.canonicalize_team_key = config_mod.canonicalize_team_key
    sys.modules["automation.config.team_keys"] = team_keys_mod

    # Firebase stubs
    fb = types.ModuleType("firebase_admin")
    fb.initialize_app = lambda *_, **__: None
    fb._apps = {"default": object()}
    fb.credentials = types.ModuleType("firebase_admin.credentials")
    fb.storage = types.ModuleType("firebase_admin.storage")
    fb.firestore = types.ModuleType("firebase_admin.firestore")
    fb.firestore.SERVER_TIMESTAMP = object()
    sys.modules["firebase_admin"] = fb
    sys.modules["firebase_admin.credentials"] = fb.credentials
    sys.modules["firebase_admin.storage"] = fb.storage
    sys.modules["firebase_admin.firestore"] = fb.firestore

    # Clients package stub
    clients_pkg = types.ModuleType("automation.clients")
    clients_pkg.__path__ = []
    sys.modules["automation.clients"] = clients_pkg

    firestore_mod = types.ModuleType("automation.clients.firestore")
    firestore_mod._ensure_firestore = lambda *_, **__: None
    sys.modules["automation.clients.firestore"] = firestore_mod


def _ensure_functions_on_path():
    path_str = str(FUNCTIONS_DIR)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def test_scrape_results_publish_flow():
    """Fetch + publish path with fake Odds API and Firestore."""
    _stub_base_modules()
    _ensure_functions_on_path()
    sr = importlib.import_module("automation.evaluation.scrape_results")

    # Fake HTTP response
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return [
                {
                    "id": "game1",
                    "completed": True,
                    "commence_time": "2025-01-01T18:00:00Z",
                    "home_team": "Home Team",
                    "away_team": "Away Team",
                    "scores": [
                        {"name": "Home Team", "score": 80},
                        {"name": "Away Team", "score": 70},
                    ],
                },
                {
                    "id": "ignored",
                    "completed": False,
                },
            ]

    class FakeSession:
        def get(self, *_, **__):
            return FakeResponse()

    fetcher = sr.OddsAPIScoresFetcher("key")
    fetcher.session = FakeSession()

    games = fetcher.fetch_completed_scores_for_date(date(2025, 1, 1))
    assert len(games) == 1
    assert games[0]["home_team"] == "home-team"

    # Fake Firestore structures
    results_written: List[Dict[str, Any]] = []

    class FakeResultDoc:
        def __init__(self, doc_id: str):
            self.path = f"/results/{doc_id}"

        def set(self, data):
            results_written.append(data)

    class FakeSubcollection:
        def document(self, doc_id: str):
            return FakeResultDoc(doc_id)

    class FakeDocRef:
        def __init__(self, doc_id: str, data: Dict[str, Any]):
            self.id = doc_id
            self._data = data

        def collection(self, _name: str):
            return FakeSubcollection()

    class FakeSnapshot:
        def __init__(self, ref: FakeDocRef):
            self.id = ref.id
            self.reference = ref

        def to_dict(self):
            return dict(self.reference._data)

    class FakeGamesCollection:
        def __init__(self, snaps):
            self._snaps = snaps

        def stream(self):
            return self._snaps

    class FakeParentDoc:
        def __init__(self, snaps):
            self._snaps = snaps
            self.id = "parent"

        def document(self, _date: str):
            return self

        def collection(self, name: str):
            assert name == "games"
            return FakeGamesCollection(self._snaps)

    class FakeDB:
        def __init__(self, snaps):
            self._snaps = snaps

        def collection(self, _name: str):
            return FakeParentDoc(self._snaps)

    # Prepare one existing Firestore game doc
    snapshots = [
        FakeSnapshot(FakeDocRef("game1", {"home_team": "home-team", "away_team": "away-team"}))
    ]
    sr._ensure_firestore = lambda *_, **__: FakeDB(snapshots)  # type: ignore[attr-defined]

    sr.publish_results("2025-01-01", games, dry_run=False)
    assert len(results_written) == 1
    assert results_written[0]["home_score"] == 80
    assert results_written[0]["away_score"] == 70


def test_make_preds_download_artifacts(monkeypatch):
    """Exercise model artifact download path with a fake bucket."""
    _stub_base_modules()
    _ensure_functions_on_path()
    mp = importlib.import_module("automation.prediction.make_preds")

    # Disable storage requirement and clear cache
    monkeypatch.setattr(mp, "_require_firebase_storage", lambda: None)
    mp._MODEL_ARTIFACT_CACHE = {}
    monkeypatch.setattr(mp, "FIREBASE_STORAGE_BUCKET", "bucket")

    class FakeBlob:
        def __init__(self, exists: bool, payload: bytes):
            self._exists = exists
            self._payload = payload

        def exists(self):
            return self._exists

        def download_as_bytes(self):
            return self._payload

    class FakeBucket:
        def __init__(self, mapping: Dict[str, bytes]):
            self._mapping = mapping
            self.name = "bucket"

        def blob(self, path: str):
            payload = self._mapping.get(path)
            return FakeBlob(payload is not None, payload or b"")

    payloads = {
        "models/main/spread_model.pkl": b"spread",
        "models/main/total_model.pkl": b"total",
        "models/main/moneyline_model.pkl": b"moneyline",
        "models/main/feature_names.json": b'{"feature_names": ["a", "b"]}',
    }
    fake_bucket = FakeBucket(payloads)
    monkeypatch.setattr(mp, "_get_firebase_bucket", lambda *_, **__: fake_bucket)

    artifacts = mp._download_model_artifacts("models/main")
    assert set(["spread_model.pkl", "total_model.pkl", "moneyline_model.pkl"]).issubset(artifacts)
    assert artifacts["feature_names.json"]


def test_build_features_end_to_end(monkeypatch):
    """Run build_features_for_date with stubbed raw data."""
    _stub_base_modules()
    _ensure_functions_on_path()
    bf = importlib.import_module("automation.processing.build_features")

    games_df = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "date": "2025-01-01",
                "home_team_key": "home",
                "away_team_key": "away",
                "home_team_name": "Home",
                "away_team_name": "Away",
                "location_type": "Home",
                "home_conf": "C1",
                "away_conf": "C2",
            }
        ]
    )
    teams_df = pd.DataFrame(
        [
            {
                "team_key": "home",
                "team_points_roll": 80.0,
                "team_pace_roll": 70.0,
                "team_off_eff_roll": 110.0,
                "team_def_eff_roll": 95.0,
            },
            {
                "team_key": "away",
                "team_points_roll": 75.0,
                "team_pace_roll": 68.0,
                "team_off_eff_roll": 105.0,
                "team_def_eff_roll": 98.0,
            },
        ]
    )
    odds_df = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "date": "2025-01-01",
                "spread_home": -5.5,
                "total": 140.5,
                "moneyline_home": -200,
                "moneyline_away": 180,
            }
        ]
    )

    monkeypatch.setattr(bf, "load_raw_day", lambda ds: (games_df, teams_df, odds_df))
    monkeypatch.setattr(bf, "_upload_features", lambda *_, **__: None)

    df = bf.build_features_for_date("2025-01-01")
    assert not df.empty
    assert "delta_pace_roll" in df.columns
    assert df.iloc[0]["bet_spread"] == -5.5


def test_prepare_rolling_minimal():
    """Hit rolling/pace logic with a tiny DataFrame."""
    _stub_base_modules()
    _ensure_functions_on_path()
    fe = importlib.import_module("automation.processing.feature_engineering")

    df = pd.DataFrame(
        {
            "Date": ["2025-01-01", "2025-01-02"],
            "Team": ["A", "A"],
            "Opp": ["B", "B"],
            "Tm": [70, 75],
            "Opp.1": [65, 70],
            "FGA": [60, 62],
            "FTA": [15, 14],
            "ORB": [10, 9],
            "TOV": [12, 11],
        }
    )

    rolled = fe.prepare_rolling(df)
    assert "team_pace_roll" in rolled.columns
    assert "team_winpct_roll" in rolled.columns


def test_ingest_raw_download_snapshot(monkeypatch):
    """Exercise gamelog download helper with stubbed schedule and storage."""
    _stub_base_modules()
    _ensure_functions_on_path()
    ingest = importlib.import_module("automation.processing.ingest_raw")

    schedule = pd.DataFrame(
        [
            {"home_team_name": "Team A", "away_team_name": "Team B"},
        ]
    )
    monkeypatch.setattr(ingest, "fetch_schedule_for_date", lambda *_: schedule, raising=False)

    class FakeBlob:
        def __init__(self, payload: str):
            self.payload = payload

        def exists(self):
            return True

        def download_as_text(self):
            return self.payload

    class FakeBucket:
        def __init__(self, payload: str):
            self.payload = payload

        def blob(self, path: str):
            assert "gamelogs" in path
            return FakeBlob(self.payload)

    monkeypatch.setattr(ingest, "_get_firebase_bucket", lambda *_, **__: FakeBucket("FG,FG.1\n10,8"), raising=False)

    df = ingest.download_gamelogs_snapshot("2025-01-01")
    assert df is not None
    assert "Team" in df.columns
    assert df.shape[0] >= 1
