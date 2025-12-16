from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from tests.fake_firebase import FakeBucket, FakeFirestoreClient


def _reload_firestore(monkeypatch, bucket=None, db=None):
    """Load automation.clients.firestore with firebase/config stubs."""
    bucket = bucket or FakeBucket()
    db = db or FakeFirestoreClient()

    for name in list(sys.modules):
        if name.startswith("automation.clients.firestore") or name.startswith("automation.config"):
            sys.modules.pop(name, None)

    monkeypatch.syspath_prepend("functions")

    automation_pkg = types.ModuleType("automation")
    automation_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "functions" / "automation")]
    monkeypatch.setitem(sys.modules, "automation", automation_pkg)

    clients_pkg = types.ModuleType("automation.clients")
    clients_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "functions" / "automation" / "clients")]
    monkeypatch.setitem(sys.modules, "automation.clients", clients_pkg)

    config_pkg = types.ModuleType("automation.config")
    config_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "functions" / "automation" / "config")]
    monkeypatch.setitem(sys.modules, "automation.config", config_pkg)

    team_keys_mod = types.ModuleType("automation.config.team_keys")
    team_keys_mod.canonicalize_team_key = lambda name: str(name or "").strip().lower().replace(" ", "-")
    monkeypatch.setitem(sys.modules, "automation.config.team_keys", team_keys_mod)

    config_mod = types.ModuleType("automation.config.config")
    config_mod.ACTIVE_MODEL_RUN_ID = "run_test"
    config_mod.FIREBASE_CREDENTIALS_PATH = "/tmp/creds.json"
    config_mod.FIREBASE_STORAGE_BUCKET = "bucket"
    config_mod.FIRESTORE_PREDICTIONS_COLLECTION = "preds"
    config_mod.MAX_PICKS_TO_PUBLISH = 2
    config_mod.RAW_TORVIK_PREFIX = "raw_data/torvik_rankings"
    config_mod.TORVIK_MAP = {"texasa&mcorpuschris": "texas-am-cc", "thecitadel": "citadel"}
    config_mod.firestore_doc_for_game_pred = (
        lambda game_pred, picks, torvik_ranks=None: {**game_pred, "recommended": picks, "torvik": torvik_ranks}
    )
    config_mod.canonicalize_team_key = team_keys_mod.canonicalize_team_key
    monkeypatch.setitem(sys.modules, "automation.config.config", config_mod)

    fb = types.ModuleType("firebase_admin")
    fb._apps = {}
    init_calls: list[dict] = []

    def _init_app(*args, **kwargs):
        options = args[0] if args else kwargs
        init_calls.append(options)
        fb._apps["default"] = options or {"initialized": True}

    fb.initialize_app = _init_app
    monkeypatch.setitem(sys.modules, "firebase_admin", fb)
    monkeypatch.setitem(sys.modules, "firebase_admin.credentials", types.ModuleType("firebase_admin.credentials"))

    storage_mod = types.ModuleType("firebase_admin.storage")
    storage_mod.bucket = lambda name=None: bucket
    monkeypatch.setitem(sys.modules, "firebase_admin.storage", storage_mod)

    firestore_mod = types.ModuleType("firebase_admin.firestore")
    firestore_mod.client = lambda: db
    monkeypatch.setitem(sys.modules, "firebase_admin.firestore", firestore_mod)

    fs = importlib.import_module("automation.clients.firestore")
    fs._TORVIK_RANKS_CACHE = None
    return fs, init_calls, bucket, db


def test_ensure_firestore_initializes_once(monkeypatch):
    fs, init_calls, _, db = _reload_firestore(monkeypatch)

    first = fs._ensure_firestore()
    second = fs._ensure_firestore()

    assert first is db
    assert second is db
    assert len(init_calls) == 1
    assert init_calls[0].get("options", {}).get("storageBucket") == "bucket"


def test_to_serializable_handles_scalars_and_nested(monkeypatch):
    fs, _, _, _ = _reload_firestore(monkeypatch)

    pd_scalar = pd.Series([1]).iloc[0]
    dt_value = datetime(2025, 1, 1)
    nested = {"x": pd_scalar, "y": [dt_value]}

    serialized = fs._to_serializable(nested)

    assert serialized["x"] == 1
    assert serialized["y"][0] == dt_value.isoformat()


def test_load_latest_torvik_ranks_parses_csv(monkeypatch):
    bucket = FakeBucket()
    bucket.set_blob(
        "raw_data/torvik_rankings/latest.csv",
        "Team,Rank\nThe Citadel,12\nTexas A&M Corpus Chris,5\n",
    )
    fs, _, _, _ = _reload_firestore(monkeypatch, bucket=bucket)

    ranks = fs._load_latest_torvik_ranks()

    assert ranks["citadel"] == 12
    assert ranks["texas-am-cc"] == 5
    # Cached on subsequent calls
    assert fs._load_latest_torvik_ranks() is ranks


def test_publish_predictions_to_firestore_writes_collections(monkeypatch):
    bucket = FakeBucket()
    db = FakeFirestoreClient()
    fs, _, _, _ = _reload_firestore(monkeypatch, bucket=bucket, db=db)

    monkeypatch.setattr(fs, "_load_latest_torvik_ranks", lambda: {"home": 7})

    captured = {}

    def _build_doc(game_pred, picks, torvik_ranks=None):
        captured["picks"] = picks
        captured["torvik"] = torvik_ranks
        return {"game_id": game_pred["game_id"], "recommended": picks, "torvik": torvik_ranks}

    monkeypatch.setattr(fs, "firestore_doc_for_game_pred", _build_doc)

    game_pred = {
        "game_id": "g1",
        "home_team": "Home",
        "away_team": "Away",
        "bookmakers": {"bk": {"bookmaker_title": "Book", "bookmaker_key": "bk"}},
    }
    picks = [{"game_id": "g1", "edge": 2}, {"game_id": "g2", "edge": 1}]
    bet_preds = [{"game_id": "g1", "model_spread_home": -3, "model_total": 150, "home_win_prob": 0.6}]

    fs.publish_predictions_to_firestore("2025-01-01", [game_pred], picks, max_picks=1, bet_model_preds=bet_preds)

    root_doc = db.collection("preds").document("2025-01-01")
    game_doc = root_doc.collection("games").document("g1")

    assert captured["picks"] == [picks[0]]
    assert captured["torvik"] == {"home": 7}
    assert game_doc.set_calls[0]["body"]["recommended"] == [picks[0]]

    odds_doc = game_doc.collection("sportsbookOdds").document("bk")
    assert odds_doc.set_calls[0]["body"]["bookmaker_title"] == "Book"

    bet_doc = game_doc.collection("betModel").document("bet_model_document")
    assert bet_doc.set_calls[0]["body"]["model_spread_home"] == -3

    meta_top = root_doc.collection("picks_metadata").document("top_picks")
    assert meta_top.set_calls[0]["body"]["picks"] == [picks[0]]
