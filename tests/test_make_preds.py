"""
Unit tests for automation.prediction.make_preds.
"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
import pandas as pd
import numpy as np
from io import BytesIO

# --- Stubbing ---
def _stub_modules():
    fb = types.ModuleType("firebase_admin")
    fb.initialize_app = lambda *a, **k: None
    fb._apps = {"default": object()}
    sys.modules["firebase_admin"] = fb
    sys.modules["firebase_admin.storage"] = MagicMock()
    sys.modules["firebase_admin.firestore"] = MagicMock()
    sys.modules["automation.config.config"] = types.ModuleType("automation.config.config")

_stub_modules()

from automation.prediction import make_preds

def test_implied_prob_from_moneyline():
    assert make_preds.implied_prob_from_moneyline(-200) == pytest.approx(0.666, 0.01)
    assert make_preds.implied_prob_from_moneyline(100) == 0.5
    assert make_preds.implied_prob_from_moneyline(150) == 0.4
    assert make_preds.implied_prob_from_moneyline(None) is None
    assert make_preds.implied_prob_from_moneyline("abc") is None

def test_split_home_away():
    """Verify rows are correctly grouped into Home/Away structure."""
    df = pd.DataFrame([
        {"game_id": "g1", "Team": "A", "Opp": "B", "Location": "Home", "val": 1},
        {"game_id": "g1", "Team": "B", "Opp": "A", "Location": "Away", "val": 2},
        {"game_id": "g2", "Team": "C", "Opp": "D", "Location": "Neutral", "val": 3},
    ])
    
    grouped = make_preds.split_home_away(df)
    
    assert "g1" in grouped
    assert grouped["g1"]["home"]["Team"] == "A"
    assert grouped["g1"]["away"]["Team"] == "B"
    
    # Neutral site handling (first encountered becomes home)
    assert "g2" in grouped
    assert grouped["g2"]["home"]["Team"] == "C" 

class DummyModel:
    def __init__(self, val): self.val = val
    def predict(self, X): return [self.val] * len(X)
    def predict_proba(self, X): return np.array([[0.1, self.val]] * len(X))

def test_score_game_logic():
    """Test that models are called and result dict is constructed."""
    home_row = {
        "game_id": "g1", "Date": "2025-01-01", "Team": "HomeTeam", 
        "Opp": "AwayTeam", "Conference": "C1", "OppConference": "C2",
        "bet_spread": -5.0, "bet_total": 150.0,
        "feat1": 10, "feat2": 20
    }
    
    group_entry = {"home": home_row, "away": None} # Away not strictly needed for basic score
    
    res = make_preds.score_game(
        group_entry,
        spread_model=DummyModel(3.5), # Predicts Home wins by 3.5
        total_model=DummyModel(145.0), # Predicts 145 points
        winprob_model=DummyModel(0.60), # 60% win prob
        feature_cols=["feat1", "feat2"]
    )
    
    assert res["game_id"] == "g1"
    assert res["model_spread_home"] == 3.5
    assert res["model_total"] == 145.0
    assert res["home_win_prob"] == 0.60
    assert res["bet_spread_home"] == -5.0

def test_download_model_artifacts_missing():
    """Ensure FileNotFoundError is raised if bucket path is invalid."""
    make_preds._MODEL_ARTIFACT_CACHE = {}
    make_preds.FIREBASE_STORAGE_BUCKET = "bucket"

    with patch("automation.prediction.make_preds._require_firebase_storage", return_value=None), \
         patch("automation.prediction.make_preds._get_firebase_bucket", return_value=None):
        with pytest.raises(FileNotFoundError):
            make_preds._download_model_artifacts("   ")


# ---- Additional coverage merged from extended/artifacts/models suites ----


def test_resolve_model_path_env_override(monkeypatch):
    monkeypatch.setenv("BETBOARD_MODEL_VERSION", "v123")
    assert make_preds._resolve_model_path("models/current_production/no_bet").endswith("models/v123/no_bet")


def test_extract_feature_names_from_artifacts_text():
    artifacts = {"features.txt": b"f1\nf2\n"}
    names = make_preds._extract_feature_names_from_artifacts(artifacts)
    assert names == ["f1", "f2"]


def test_get_feature_names_with_cache(monkeypatch):
    artifacts = {"feature_names.json": b'{"feature_names": ["a", "b"]}'}
    monkeypatch.setattr(make_preds, "_download_model_artifacts", lambda *_: artifacts)
    assert make_preds.get_feature_names("models/main") == ["a", "b"]


def test_download_features_df_success(monkeypatch):
    csv_text = "f1\n1"

    class FakeBlob:
        def exists(self):
            return True

        def download_as_text(self):
            return csv_text

    class FakeBucket:
        def blob(self, _path: str):
            return FakeBlob()

    monkeypatch.setattr(make_preds, "_require_firebase_storage", lambda: None)
    monkeypatch.setattr(make_preds, "_get_firebase_bucket", lambda *_, **__: FakeBucket())

    df = make_preds._download_features_df("2025-01-01")
    assert df.iloc[0]["f1"] == 1


def test_download_model_artifacts_missing_required(monkeypatch):
    monkeypatch.setattr(make_preds, "_require_firebase_storage", lambda: None)
    make_preds.FIREBASE_STORAGE_BUCKET = "bucket"

    class FakeBlob:
        def __init__(self, exists: bool):
            self._exists = exists

        def exists(self):
            return self._exists

        def download_as_bytes(self):
            return b""

    class FakeBucket:
        name = "bucket"

        def blob(self, path: str):
            return FakeBlob(False)

    monkeypatch.setattr(make_preds, "_get_firebase_bucket", lambda *_, **__: FakeBucket())
    make_preds._MODEL_ARTIFACT_CACHE = {}

    with pytest.raises(FileNotFoundError):
        make_preds._download_model_artifacts("models/main")


def test_model_inputs_from_row_numeric_conversion():
    row = {"f1": "3.5", "f2": "abc"}
    df = make_preds.model_inputs_from_row(row, ["f1", "f2"])
    assert df["f1"].iloc[0] == 3.5
    assert df["f2"].isna().all()


def test_rank_all_picks_sorts_and_limits():
    picks = [
        {"edge_strength": 1, "id": 1},
        {"edge_strength": 3, "id": 3},
        {"edge_strength": 2, "id": 2},
    ]
    ranked = make_preds.rank_all_picks(picks, max_picks=2)
    assert [p["id"] for p in ranked] == [3, 2]


def test_download_features_df_missing_bucket(monkeypatch):
    monkeypatch.setattr(make_preds, "_require_firebase_storage", lambda: None)
    monkeypatch.setattr(make_preds, "_get_firebase_bucket", lambda *_, **__: None)
    with pytest.raises(FileNotFoundError):
        make_preds._download_features_df("2025-01-01")


def test_get_firestore_client_with_admin(monkeypatch):
    fb = types.SimpleNamespace(_apps={"default": object()})
    firestore = types.SimpleNamespace(client=lambda: "client")
    monkeypatch.setattr(make_preds, "firebase_admin", fb)
    monkeypatch.setattr(make_preds, "firestore", firestore)
    make_preds._FIRESTORE_CLIENT = None
    assert make_preds._get_firestore_client() == "client"


def test_get_firestore_client_missing_admin(monkeypatch):
    monkeypatch.setattr(make_preds, "firebase_admin", None)
    monkeypatch.setattr(make_preds, "_FIRESTORE_CLIENT", None)
    assert make_preds._get_firestore_client() is None


def test_extract_feature_names_from_artifacts_pickle(monkeypatch):
    loaded_obj = ["a", "b"]

    class FakeJoblib:
        def load(self, buffer):
            assert isinstance(buffer, BytesIO)
            return loaded_obj

    monkeypatch.setattr(make_preds, "joblib", FakeJoblib())
    names = make_preds._extract_feature_names_from_artifacts({"feature_names.pkl": b"pickle"})
    assert names == loaded_obj


def test_resolve_model_path_no_override(monkeypatch):
    monkeypatch.delenv("BETBOARD_MODEL_VERSION", raising=False)
    assert make_preds._resolve_model_path("models/current_production/no_bet").endswith("models/current_production/no_bet")


def test_get_firebase_bucket_cache(monkeypatch):
    bucket_obj = object()
    make_preds._FIREBASE_BUCKET = None
    monkeypatch.setattr(make_preds, "firebase_admin", types.SimpleNamespace(_apps={"default": object()}, initialize_app=lambda *_, **__: None))
    monkeypatch.setattr(make_preds, "storage", types.SimpleNamespace(bucket=lambda name=None: bucket_obj))
    make_preds.FIREBASE_STORAGE_BUCKET = "bucket"
    assert make_preds._get_firebase_bucket() is bucket_obj
    assert make_preds._get_firebase_bucket() is bucket_obj


def test_load_xgb_model_uses_joblib(monkeypatch):
    loaded = object()

    class FakeJoblib:
        def load(self, buffer):
            assert isinstance(buffer, BytesIO)
            return loaded

    monkeypatch.setattr(make_preds, "joblib", FakeJoblib())
    artifacts = {"spread_model.pkl": b"pickle-bytes"}
    assert make_preds._load_xgb_model(artifacts, "spread", "regressor") is loaded


def test_load_xgb_model_missing_artifact():
    with pytest.raises(FileNotFoundError):
        make_preds._load_xgb_model({}, "spread", "regressor")


def test_load_models_calls_helpers(monkeypatch):
    fake_artifacts = {"spread_model.pkl": b"x", "total_model.pkl": b"x", "moneyline_model.pkl": b"x"}
    monkeypatch.setattr(make_preds, "_download_model_artifacts", lambda path: fake_artifacts)

    sentinel_models = [object(), object(), object()]
    calls = []

    def fake_load(arts, name, model_type):
        calls.append((name, model_type))
        return sentinel_models.pop(0)

    monkeypatch.setattr(make_preds, "_load_xgb_model", fake_load)
    models = make_preds.load_models("dir")
    assert len(models) == 3
    assert calls == [("spread", "regressor"), ("total", "regressor"), ("moneyline", "classifier")]


def test_require_firebase_storage_raises_when_missing(monkeypatch):
    monkeypatch.setattr(make_preds, "firebase_admin", None)
    monkeypatch.setattr(make_preds, "storage", None)
    with pytest.raises(RuntimeError):
        make_preds._require_firebase_storage()
