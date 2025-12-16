from __future__ import annotations

import importlib
import json
import sys
import types
from datetime import datetime
from pathlib import Path

import pandas as pd

from tests.fake_firebase import FakeBucket


def _reload_gamelog(monkeypatch, bucket=None):
    bucket = bucket or FakeBucket()

    for name in list(sys.modules):
        if name.startswith("automation.clients.gamelog") or name.startswith("automation.config"):
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

    config_mod = types.ModuleType("automation.config.config")
    config_mod.TEAM_MAPPING = {"Alias": "mapped-slug"}
    config_mod.CONFERENCE_MAP = {"ConfA": ["team-a"]}
    config_mod.SPORTS_REFERENCE_SEASON = "2025"
    config_mod.GAMELOG_STORAGE_PREFIX = "raw/gamelogs"
    monkeypatch.setitem(sys.modules, "automation.config.config", config_mod)

    team_keys_mod = types.ModuleType("automation.config.team_keys")
    team_keys_mod.canonicalize_team_key = lambda name: str(name or "").lower().replace(" ", "-")
    monkeypatch.setitem(sys.modules, "automation.config.team_keys", team_keys_mod)

    fb = types.ModuleType("firebase_admin")
    fb._apps = {}
    fb.initialize_app = lambda *_, **__: fb._apps.setdefault("default", {})
    monkeypatch.setitem(sys.modules, "firebase_admin", fb)
    monkeypatch.setitem(sys.modules, "firebase_admin.credentials", types.ModuleType("firebase_admin.credentials"))

    storage_mod = types.ModuleType("firebase_admin.storage")
    storage_mod.bucket = lambda name=None: bucket
    monkeypatch.setitem(sys.modules, "firebase_admin.storage", storage_mod)

    gl = importlib.import_module("automation.clients.gamelog")
    gl.bucket = bucket  # ensure module-global bucket is the fake one
    return gl, bucket


def test_map_odds_api_name_to_sr_slug(monkeypatch):
    gl, _ = _reload_gamelog(monkeypatch)

    assert gl.map_odds_api_name_to_sr_slug("Alias") == "mapped-slug"
    assert gl.map_odds_api_name_to_sr_slug("North State") == "north-state"


def test_clean_and_filter_tables(monkeypatch):
    gl, _ = _reload_gamelog(monkeypatch)
    df = pd.DataFrame(
        [["Rk", "Date", "10", "12"], ["1", "2025-01-01", "11", "9"]],
        columns=["Rk", "Date", "FG", "FG"],
    )

    cleaned = gl.clean_table(df)
    assert "Rk" not in cleaned.columns
    assert "FG_1" in cleaned.columns  # duplicate header was renamed

    filtered = gl.filter_completed_games(cleaned)
    assert len(filtered) == 1  # drops header row


def test_fetch_with_retry_handles_rate_limit(monkeypatch):
    gl, _ = _reload_gamelog(monkeypatch)
    attempts = []

    class Response:
        def __init__(self, status_code, text="ok"):
            self.status_code = status_code
            self.text = text

    def fake_get(url, headers=None, timeout=None):
        attempts.append(url)
        return Response(429) if len(attempts) == 1 else Response(200, text="success")

    monkeypatch.setattr(gl, "requests", types.SimpleNamespace(get=fake_get))
    monkeypatch.setattr(gl.time, "sleep", lambda *_: None)
    monkeypatch.setattr(gl.random, "choice", lambda seq: seq[0])

    result = gl.fetch_with_retry("http://example", max_retries=2)
    assert result == "success"
    assert len(attempts) == 2


def test_get_teams_playing_today_reads_latest_odds(monkeypatch):
    bucket = FakeBucket()
    gl, _ = _reload_gamelog(monkeypatch, bucket=bucket)

    payload = {
        "num_games": 2,
        "games": [
            {"commence_time": "2025-01-02T12:00:00", "home_team": "Alias", "away_team": "Other Team"},
            {"commence_time": "2025-01-03T12:00:00", "home_team": "Skip", "away_team": "Skip2"},
        ],
    }
    bucket.set_blob("raw_data/odds/latest.json", json.dumps(payload))

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2025, 1, 2, tzinfo=tz)

    monkeypatch.setattr(gl, "datetime", FixedDatetime)

    teams = gl.get_teams_playing_today()
    assert teams == {"mapped-slug", "other-team"}


def test_process_team_uploads_clean_csv(monkeypatch):
    bucket = FakeBucket()
    gl, _ = _reload_gamelog(monkeypatch, bucket=bucket)
    monkeypatch.setattr(gl, "d1_teams", {"ConfA": ["team-a"]})

    html = """
    <table id="team_game_log">
        <thead><tr><th>Rk</th><th>Date</th><th>Opp</th><th>FG</th><th>FGA</th></tr></thead>
        <tbody>
            <tr><td>1</td><td>2025-01-01</td><td>Opp</td><td>10</td><td>20</td></tr>
            <tr><td>2</td><td>2025-01-05</td><td>Opp2</td><td>8</td><td>15</td></tr>
        </tbody>
    </table>
    """
    monkeypatch.setattr(gl, "fetch_with_retry", lambda *_args, **_kwargs: html)

    result = gl.process_team("team-a")
    expected_path = "raw/gamelogs/team-a/2025.csv"

    assert result is True
    assert bucket.blob(expected_path).uploads  # csv uploaded
