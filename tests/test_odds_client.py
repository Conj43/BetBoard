from __future__ import annotations

import importlib
import json
import sys
import types
from datetime import datetime
from pathlib import Path

from tests.fake_firebase import FakeBucket


def _reload_odds(monkeypatch, bucket=None):
    bucket = bucket or FakeBucket()

    for name in list(sys.modules):
        if name.startswith("automation.clients.odds"):
            sys.modules.pop(name, None)

    monkeypatch.syspath_prepend("functions")

    automation_pkg = types.ModuleType("automation")
    automation_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "functions" / "automation")]
    monkeypatch.setitem(sys.modules, "automation", automation_pkg)

    clients_pkg = types.ModuleType("automation.clients")
    clients_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "functions" / "automation" / "clients")]
    monkeypatch.setitem(sys.modules, "automation.clients", clients_pkg)

    fb = types.ModuleType("firebase_admin")
    fb._apps = {}
    fb.initialize_app = lambda *_, **kwargs: fb._apps.setdefault("default", kwargs)
    monkeypatch.setitem(sys.modules, "firebase_admin", fb)
    monkeypatch.setitem(sys.modules, "firebase_admin.credentials", types.ModuleType("firebase_admin.credentials"))

    storage_mod = types.ModuleType("firebase_admin.storage")
    storage_mod.bucket = lambda name=None: bucket
    monkeypatch.setitem(sys.modules, "firebase_admin.storage", storage_mod)

    odds = importlib.import_module("automation.clients.odds")
    odds.FIREBASE_STORAGE_BUCKET = "bucket"
    return odds, bucket, fb


def test_initialize_firebase_runs_once(monkeypatch):
    odds, bucket, fb = _reload_odds(monkeypatch)

    first = odds.initialize_firebase()
    second = odds.initialize_firebase()

    assert first is bucket
    assert second is bucket
    assert "default" in fb._apps  # initialized exactly once


def test_save_to_firebase_uploads_latest_and_dated(monkeypatch):
    odds, bucket, _ = _reload_odds(monkeypatch)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2025, 1, 2, 15, 30, tzinfo=tz)

    monkeypatch.setattr(odds, "datetime", FixedDatetime)
    monkeypatch.setattr(odds, "initialize_firebase", lambda: bucket)

    latest, dated = odds.save_to_firebase([{"id": 1}], "basketball_ncaab")

    latest_blob = bucket.blob(latest)
    dated_blob = bucket.blob(dated)
    latest_payload = json.loads(latest_blob.text)

    assert "scraped_at" in latest_payload
    assert latest_payload["num_games"] == 1
    assert dated_blob.text == latest_blob.text


def test_check_available_sports_filters_cbb(monkeypatch):
    odds, _, _ = _reload_odds(monkeypatch)

    sample = [
        {"key": "basketball_nba", "title": "NBA", "group": "basketball", "active": True},
        {"key": "basketball_ncaab", "title": "NCAA Men's", "group": "basketball", "active": True},
    ]

    class Response:
        status_code = 200

        def json(self):
            return sample

    monkeypatch.setattr(odds, "requests", types.SimpleNamespace(get=lambda url, params=None: Response()))

    result = odds.check_available_sports()
    assert len(result) == 1
    assert result[0]["key"] == "basketball_ncaab"


def test_get_college_basketball_games_filters_today_and_calls_save(monkeypatch):
    odds, bucket, _ = _reload_odds(monkeypatch)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2025, 1, 2, 12, 0, tzinfo=tz)

    monkeypatch.setattr(odds, "datetime", FixedDatetime)

    games_payload = [
        {
            "commence_time": "2025-01-02T18:00:00Z",
            "home_team": "Home",
            "away_team": "Away",
            "bookmakers": [{"title": "Book", "markets": []}],
        },
        {
            "commence_time": "2025-01-03T18:00:00Z",
            "home_team": "Tomorrow",
            "away_team": "Later",
            "bookmakers": [],
        },
    ]

    class Response:
        status_code = 200
        headers = {"x-requests-remaining": "499"}

        def json(self):
            return games_payload

    monkeypatch.setattr(odds, "requests", types.SimpleNamespace(get=lambda url, params=None: Response()))

    saved = {}
    monkeypatch.setattr(odds, "save_to_firebase", lambda data, sport_key: saved.update({"data": data, "sport_key": sport_key}))

    result = odds.get_college_basketball_games("basketball_ncaab")

    assert result == saved["data"]
    assert saved["sport_key"] == "basketball_ncaab"
    assert len(saved["data"]) == 1
    assert saved["data"][0]["commence_time"].endswith("00")
    tz_abbr = result[0]["commence_time_formatted"].split()[-1]
    assert tz_abbr in {"CST", "CDT"}
