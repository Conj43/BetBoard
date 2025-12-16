from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime
from pathlib import Path

from tests.fake_firebase import FakeBucket


def _reload_torvik(monkeypatch, bucket=None):
    bucket = bucket or FakeBucket()

    for name in list(sys.modules):
        if name.startswith("automation.clients.torvik"):
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

    torvik = importlib.import_module("automation.clients.torvik")
    torvik.FIREBASE_STORAGE_BUCKET = "bucket"
    torvik.bucket = bucket
    return torvik, bucket


def test_scrape_torvik_success(monkeypatch):
    torvik, bucket = _reload_torvik(monkeypatch)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2025, 1, 2, 12, 0, tzinfo=tz)

    class Response:
        status_code = 200
        content = b"team,rank\nA,1\n"

    monkeypatch.setattr(torvik, "datetime", FixedDatetime)
    monkeypatch.setattr(torvik, "requests", types.SimpleNamespace(get=lambda url, timeout=None: Response()))

    result, status = torvik.scrape_torvik()

    dated_path = "raw_data/torvik_rankings/2025-01-02/rankings.csv"
    latest_path = "raw_data/torvik_rankings/latest.csv"
    assert status == 200
    assert bucket.blob(dated_path).text.startswith("team,rank")
    assert bucket.blob(latest_path).text.startswith("team,rank")
    assert result["success"] is True


def test_scrape_torvik_handles_http_error(monkeypatch):
    torvik, _ = _reload_torvik(monkeypatch)

    class Response:
        status_code = 500
        content = b""

    monkeypatch.setattr(torvik, "requests", types.SimpleNamespace(get=lambda url, timeout=None: Response()))

    result, status = torvik.scrape_torvik()
    assert status == 500
    assert result["success"] is False
