"""
Unit tests for automation.processing.build_features.
"""
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import pandas as pd
import numpy as np

# --- 1. PATH SETUP: Add 'functions' folder to Python path ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS_DIR = PROJECT_ROOT / "functions"
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

# --- 2. STUBBING: Mock Firebase/Config before importing modules ---
def _stub_modules():
    # Stub firebase_admin and storage
    fb = types.ModuleType("firebase_admin")
    fb.initialize_app = lambda *args, **kwargs: None
    sys.modules["firebase_admin"] = fb
    sys.modules["firebase_admin.credentials"] = types.ModuleType("firebase_admin.credentials")
    sys.modules["firebase_admin.storage"] = types.ModuleType("firebase_admin.storage")

    # Stub config
    config = types.ModuleType("automation.config.config")
    config.RAW_GAMES_PREFIX = "raw/games"
    config.RAW_TEAMS_PREFIX = "raw/teams"
    config.RAW_ODDS_PREFIX = "raw/odds"
    config.FIREBASE_CREDENTIALS_PATH = "fake.json"
    config.FIREBASE_STORAGE_BUCKET = "fake-bucket"
    config.PROCESSED_FEATURES_PREFIX = "processed"
    # Minimal team/conference mapping required by automation.config.utils
    config.TEAM_MAPPING = {}
    config.CONFERENCE_MAP = {}
    config.CANONICAL_BET_COLS = []
    config.canonicalize_team_key = lambda name: str(name).lower().replace(" ", "-") if name else ""
    sys.modules["automation.config.config"] = config

    # Stub ingest_raw
    ingest = types.ModuleType("automation.processing.ingest_raw")
    ingest.normalize_team_key = lambda x: x.lower().replace(" ", "-")
    ingest.make_game_id = lambda d, h, a: f"{d}_{h}_{a}"
    ingest.fetch_schedule_for_date = lambda *_, **__: pd.DataFrame()
    ingest.fetch_team_snapshot = lambda *_, **__: {}
    ingest.fetch_odds_for_game = lambda *_, **__: {}
    sys.modules["automation.processing.ingest_raw"] = ingest

_stub_modules()

# --- 3. IMPORT UNDER TEST ---
from automation.processing import build_features

@pytest.fixture
def mock_raw_data():
    """Returns sample dataframes for games, teams, and odds."""
    games_data = {
        "game_id": ["2023-11-06_team-a_team-b"],
        "date": ["2023-11-06"],
        "home_team_key": ["team-a"],
        "away_team_key": ["team-b"],
        "home_team_name": ["Team A"],
        "away_team_name": ["Team B"],
        "location_type": ["Home"],
        "home_conf": ["SEC"],
        "away_conf": ["ACC"]
    }
    
    teams_data = [
        {"team_key": "team-a", "team_points_roll": 80.0, "team_pace_roll": 70.0, "team_off_eff_roll": 110.0},
        {"team_key": "team-b", "team_points_roll": 75.0, "team_pace_roll": 72.0, "team_off_eff_roll": 105.0}
    ]
    
    odds_data = {
        "game_id": ["2023-11-06_team-a_team-b"],
        "spread_home": [-5.5],
        "total": [145.0],
        "moneyline_home": [-200],
        "moneyline_away": [170]
    }
    
    return (
        pd.DataFrame(games_data),
        pd.DataFrame(teams_data),
        pd.DataFrame(odds_data)
    )

def test_build_features_happy_path(mock_raw_data):
    """Scenario: Normal case with complete, well-formed rows."""
    games, teams, odds = mock_raw_data
    
    with patch("automation.processing.build_features.load_raw_day", return_value=(games, teams, odds)), \
         patch("automation.processing.build_features._upload_features"):
        
        df = build_features.build_features_for_date("2023-11-06")
        
        assert not df.empty
        assert "game_id" in df.columns
        assert "delta_pace_roll" in df.columns
        assert df.iloc[0]["delta_pace_roll"] != 0 
        assert df.iloc[0]["bet_spread"] == -5.5

def test_build_features_missing_values_handling(mock_raw_data):
    """Scenario: Rows with missing numeric values."""
    games, teams, odds = mock_raw_data
    # Introduce missing value in rolling stats
    teams.loc[0, "team_pace_roll"] = np.nan 
    
    with patch("automation.processing.build_features.load_raw_day", return_value=(games, teams, odds)), \
         patch("automation.processing.build_features._upload_features"):
        
        df = build_features.build_features_for_date("2023-11-06")
        
        # format_for_model fills missing expected cols with 0.0
        assert not df["team_pace_roll"].isna().any()
        assert df.iloc[0]["team_pace_roll"] == 0.0

def test_build_features_insufficient_history(mock_raw_data):
    """Scenario: Insufficient history (Team has no previous games)."""
    games, _, odds = mock_raw_data
    # Empty teams dataframe simulates no historical stats found
    empty_teams = pd.DataFrame(columns=["team_key"]) 
    
    with patch("automation.processing.build_features.load_raw_day", return_value=(games, empty_teams, odds)), \
         patch("automation.processing.build_features._upload_features"):
        
        df = build_features.build_features_for_date("2023-11-06")
        
        assert not df.empty
        # Should default to 0.0 for stats
        assert df.iloc[0]["team_off_eff_roll"] == 0.0


# --- Append to existing test_build_features.py ---

def test_format_for_model_fills_defaults(mock_raw_data):
    """Ensure missing columns are backfilled with 0."""
    df = pd.DataFrame({"game_id": ["g1"]}) # Missing almost everything
    formatted = build_features.format_for_model(df)
    
    assert "team_points_roll" in formatted.columns
    assert formatted.iloc[0]["team_points_roll"] == 0.0
    # Ensure ID preserved
    assert formatted.iloc[0]["game_id"] == "g1"

def test_recompute_deltas(mock_raw_data):
    """Test delta calculation helper."""
    df = pd.DataFrame({
        "team_pace_roll": [75.0],
        "opp_pace_roll": [70.0]
    })
    
    res = build_features._recompute_deltas(df)
    assert "delta_pace_roll" in res.columns
    assert res.iloc[0]["delta_pace_roll"] == 5.0

def test_compute_matchup_features_simple():
    """Test simplified matchup logic without full dataframe."""
    from automation.processing.feature_engineering import _compute_matchup_features
    df = pd.DataFrame({
        "team_adj_o": [110], "opp_adj_d": [100],
        "opp_adj_o": [105], "team_adj_d": [95],
        "team_pace_roll": [70], "opp_pace_roll": [70]
    })
    
    res = _compute_matchup_features(df)
    assert res.iloc[0]["team_offensive_matchup"] == 10.0 # 110 - 100
    assert res.iloc[0]["team_matchup_advantage"] == 0.0 # (10) - (10)
    assert "pregame_total_projection" in res.columns


# ---- Additional build_features helper coverage (merged from extended/fb tests) ----


def test_build_team_view_row_locations():
    game_row = pd.Series(
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
    )
    team_stats = {"team_points_roll": 80}
    opp_stats = {"team_points_roll": 70}
    odds_row = {"spread_home": -3.5, "total": 140.0, "moneyline_home": -150, "moneyline_away": 130}

    row = build_features.build_team_view_row(game_row, "home", "away", team_stats, opp_stats, odds_row)
    assert row["Location"] == "Home"
    assert row["bet_spread_home"] == -3.5
    assert row["team_points_roll"] == 80
    assert row["opp_points_roll"] == 70

    # Away perspective should flip location and keep odds
    row_away = build_features.build_team_view_row(game_row, "away", "home", opp_stats, team_stats, odds_row)
    assert row_away["Location"] == "Away"
    assert row_away["bet_spread_home"] == -3.5


def test_recompute_deltas_and_format_for_model():
    df = pd.DataFrame(
        [
            {
                "team_pace_roll": 70.0,
                "opp_pace_roll": 65.0,
                "team_off_eff_roll": 110.0,
                "opp_off_eff_roll": 100.0,
                "game_id": "g1",
            }
        ]
    )
    df = build_features._recompute_deltas(df)
    assert df["delta_pace_roll"].iloc[0] == 5.0

    formatted = build_features.format_for_model(df)
    # All expected columns should exist after formatting
    assert "game_id" in formatted.columns
    assert not formatted.isna().any().any()


def test_recompute_derived_metrics_and_infer_game_type():
    df = pd.DataFrame(
        [
            {
                "team_pace_roll": 70.0,
                "opp_pace_roll": 65.0,
                "team_points_roll": 80.0,
                "opp_points_roll": 75.0,
                "team_def_eff_roll": None,
                "opp_def_eff_roll": None,
            }
        ]
    )
    updated = build_features._recompute_derived_metrics(df.copy())
    assert "delta_pace_roll" in updated.columns
    assert updated["team_def_eff_roll"].notna().all()
    assert updated["opp_def_eff_roll"].notna().all()

    assert build_features.infer_game_type("C1", "C1", pd.Series()) == "REG (Conf)"
    assert build_features.infer_game_type("C1", "C2", pd.Series()) == "REG (Non-Conf)"


def test_format_for_model_missing_strings_and_upload(monkeypatch):
    df = pd.DataFrame(
        [
            {
                "team_pace_roll": 70.0,
                "opp_pace_roll": 65.0,
                "team_points_roll": 80.0,
                "opp_points_roll": 75.0,
            }
        ]
    )
    formatted = build_features.format_for_model(df)
    assert "Team" in formatted.columns
    assert formatted.iloc[0]["Team"] == ""

    # Ensure upload path no-ops when upload disabled
    monkeypatch.setattr(build_features, "UPLOAD_TO_FIREBASE", False)
    build_features._upload_features("csv", "2025-01-01")


def test_get_firebase_bucket_disabled(monkeypatch):
    monkeypatch.setattr(build_features, "UPLOAD_TO_FIREBASE", False)
    assert build_features._get_firebase_bucket() is None


def test_get_firebase_bucket_missing_storage(monkeypatch):
    monkeypatch.setattr(build_features, "UPLOAD_TO_FIREBASE", True)
    monkeypatch.setattr(build_features, "firebase_admin", None)
    monkeypatch.setattr(build_features, "storage", None)
    assert build_features._get_firebase_bucket() is None


def test_get_firebase_bucket_success_and_cache(monkeypatch):
    monkeypatch.setattr(build_features, "UPLOAD_TO_FIREBASE", True)
    build_features.FIREBASE_STORAGE_BUCKET = "bucket"
    build_features._FIREBASE_BUCKET = None

    fb = types.SimpleNamespace(_apps={"default": object()}, initialize_app=lambda *_, **__: None)
    storage_mod = types.SimpleNamespace(bucket=lambda name=None: f"bucket-{name}")
    monkeypatch.setattr(build_features, "firebase_admin", fb)
    monkeypatch.setattr(build_features, "storage", storage_mod)

    first = build_features._get_firebase_bucket()
    second = build_features._get_firebase_bucket()
    assert first == "bucket-bucket"
    assert second == first  # cached


def test_upload_and_download_csv_with_fake_bucket(monkeypatch):
    monkeypatch.setattr(build_features, "UPLOAD_TO_FIREBASE", True)
    build_features.FIREBASE_STORAGE_BUCKET = "bucket"
    build_features._FIREBASE_BUCKET = None

    class FakeBlob:
        def __init__(self, exists=True, data=""):
            self.uploads = []
            self._exists = exists
            self._data = data

        def upload_from_string(self, content, content_type=None):
            self.uploads.append((content, content_type))

        def exists(self):
            return self._exists

        def download_as_text(self):
            return self._data

    class FakeBucket:
        def __init__(self):
            self.created = {}
            self.name = "bucket"

        def blob(self, name):
            blob = self.created.get(name)
            if blob is None:
                blob = FakeBlob(exists=True, data="a,b\n1,2")
                self.created[name] = blob
            return blob

    fake_bucket = FakeBucket()
    monkeypatch.setattr(build_features, "_get_firebase_bucket", lambda: fake_bucket)

    build_features._upload_features("a,b\n1,2", "2025-01-01")
    dated_blob = fake_bucket.created[f"{build_features.PROCESSED_FEATURES_PREFIX}/2025-01-01/features.csv"]
    latest_blob = fake_bucket.created[f"{build_features.PROCESSED_FEATURES_PREFIX}/latest.csv"]
    assert dated_blob.uploads and latest_blob.uploads

    df = build_features._download_csv(f"{build_features.PROCESSED_FEATURES_PREFIX}/2025-01-01/features.csv")
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["a", "b"]


def test_download_csv_missing_blob(monkeypatch):
    monkeypatch.setattr(build_features, "_get_firebase_bucket", lambda: None)
    with pytest.raises(FileNotFoundError):
        build_features._download_csv("missing.csv")
