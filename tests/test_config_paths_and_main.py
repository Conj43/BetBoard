"""
Cover config path helpers and lazy loaders in functions/main.py without touching real Firebase.
"""
from __future__ import annotations

import sys
import types
import importlib
from pathlib import Path
import pandas as pd


def _stub_firebase_for_config():
    """Install minimal firebase_admin/credentials/firestore stubs so config import is safe."""
    fb = types.ModuleType("firebase_admin")
    fb._apps = {"default": object()}  # Pretend already initialized so config doesn't call initialize_app
    fb.initialize_app = lambda *_, **__: None
    credentials_mod = types.ModuleType("firebase_admin.credentials")
    credentials_mod.Certificate = lambda *_, **__: None
    firestore_mod = types.ModuleType("firebase_admin.firestore")
    firestore_mod.client = lambda *_, **__: types.SimpleNamespace()
    return fb, credentials_mod, firestore_mod


def test_config_path_helpers_and_resolve_team_key(monkeypatch):
    fb, creds_mod, firestore_mod = _stub_firebase_for_config()
    monkeypatch.setitem(sys.modules, "firebase_admin", fb)
    monkeypatch.setitem(sys.modules, "firebase_admin.credentials", creds_mod)
    monkeypatch.setitem(sys.modules, "firebase_admin.firestore", firestore_mod)

    for name in list(sys.modules):
        if name.startswith("automation.config"):
            sys.modules.pop(name, None)

    sys.path.insert(0, "functions")
    try:
        config = importlib.import_module("automation.config.config")
    finally:
        sys.path.remove("functions")
    assert config.raw_results_path("2025-01-01").endswith("2025-01-01/results.csv")
    assert config.raw_odds_path("2025-01-01").endswith("2025-01-01/odds.csv")
    assert config.processed_features_path("2025-01-01").endswith("2025-01-01/features.csv")
    assert config.predictions_export_game_preds_path("2025-01-01").endswith("game_preds.json")
    assert config.predictions_export_top_picks_path("2025-01-01").endswith("top_picks.json")
    assert config.predictions_export_graded_picks_path("2025-01-01").endswith("graded_picks.json")
    assert config.predictions_export_summary_path("2025-01-01").endswith("summary.json")
    assert config.model_run_dir("run_x") == "model_runs/run_x"
    assert config.model_path_spread("run_x").endswith("spread_model.pkl")

    # _resolve_team_key should respect TEAM_MAPPING and fall back to canonicalization
    monkeypatch.setattr(config, "TEAM_MAPPING", {"UNC": "North Carolina"})
    monkeypatch.setattr(config, "canonicalize_team_key", lambda name: str(name).lower().replace(" ", "-"))
    assert config._resolve_team_key("UNC") == "north-carolina"
    assert config._resolve_team_key("Duke") == "duke"


def test_firestore_doc_for_game_pred_builds_expected_sections(monkeypatch):
    fb, creds_mod, firestore_mod = _stub_firebase_for_config()
    monkeypatch.setitem(sys.modules, "firebase_admin", fb)
    monkeypatch.setitem(sys.modules, "firebase_admin.credentials", creds_mod)
    monkeypatch.setitem(sys.modules, "firebase_admin.firestore", firestore_mod)

    for name in list(sys.modules):
        if name.startswith("automation.config"):
            sys.modules.pop(name, None)

    sys.path.insert(0, "functions")
    try:
        config = importlib.import_module("automation.config.config")
    finally:
        sys.path.remove("functions")

    monkeypatch.setattr(config, "canonicalize_team_key", lambda name: str(name).lower().replace(" ", "-"))
    game_pred = {
        "game_id": "g1",
        "game_date": "2025-01-01",
        "home_team": "Home",
        "away_team": "Away",
        "home_conf": "A",
        "away_conf": "B",
        "bet_spread_home": -4,
        "model_spread_home": -6,
        "bet_total": 150,
        "model_total": 156,
        "moneyline_home": -120,
        "moneyline_away": 110,
        "home_win_prob": 0.6,
    }
    picks = [{"selection": "Home", "bet_type": "moneyline", "odds": -120}]
    doc = config.firestore_doc_for_game_pred(game_pred, picks, torvik_ranks={"home": 5, "away": 20})

    assert doc["game_id"] == "g1"
    assert doc["moneyline"]["p_win_home"] == 0.6
    assert doc["spread"]["pick"] == "Away"  # edge favors away given inputs
    assert doc["total"]["pick"] == "OVER"
    assert doc["recommended"] == picks
    # torvik ranks populated using _resolve_team_key
    assert doc["torvik_home_rank"] == 5
    assert doc["torvik_away_rank"] == 20


def test_main_lazy_loaders(monkeypatch):
    """Ensure _get_prediction_pipeline/_get_evaluation_pipeline cache modules."""
    # Stub firebase_admin and firebase_functions before importing functions.main
    fb = types.ModuleType("firebase_admin")
    fb._apps = {"default": object()}
    fb.initialize_app = lambda *_, **__: None
    monkeypatch.setitem(sys.modules, "firebase_admin", fb)

    https_fn = types.SimpleNamespace(on_request=lambda *args, **kwargs: (lambda f: f), Request=object, Response=lambda body, status=200: (body, status))
    options_mod = types.SimpleNamespace(SupportedRegion=object, MemoryOption=types.SimpleNamespace(GB_2="2GB"), set_global_options=lambda **_: None)
    ff_mod = types.ModuleType("firebase_functions")
    ff_mod.https_fn = https_fn
    monkeypatch.setitem(sys.modules, "firebase_functions", ff_mod)
    monkeypatch.setitem(sys.modules, "firebase_functions.options", options_mod)

    # Provide stub pipeline modules
    pred_mod = types.ModuleType("automation.pipeline.prediction_pipeline")
    pred_mod.run_prediction_pipeline = lambda *_, **__: "pred"
    eval_mod = types.ModuleType("automation.pipeline.evaluation_pipeline")
    eval_mod.run_evaluation_pipeline = lambda *_, **__: "eval"
    monkeypatch.setitem(sys.modules, "automation", types.ModuleType("automation"))
    monkeypatch.setitem(sys.modules, "automation.pipeline", types.ModuleType("automation.pipeline"))
    monkeypatch.setitem(sys.modules, "automation.pipeline.prediction_pipeline", pred_mod)
    monkeypatch.setitem(sys.modules, "automation.pipeline.evaluation_pipeline", eval_mod)

    repo_root = str(Path(__file__).resolve().parents[1])
    sys.path.insert(0, repo_root)
    sys.path.insert(0, "functions")
    try:
        main_mod = importlib.import_module("functions.main")
    finally:
        sys.path.remove("functions")
        sys.path.remove(repo_root)

    assert main_mod._get_prediction_pipeline() is pred_mod
    assert main_mod._get_prediction_pipeline() is pred_mod  # cached
    assert main_mod._get_evaluation_pipeline() is eval_mod
    assert main_mod._get_evaluation_pipeline() is eval_mod


# ---- Config utils coverage (merged) ----


def _load_utils():
    if "automation.config.utils" in sys.modules:
        sys.modules.pop("automation.config.utils")
    sys.path.insert(0, "functions")
    try:
        return importlib.import_module("automation.config.utils")
    finally:
        sys.path.pop(0)


def test_parse_dates_infers_fallback_and_normalizes():
    utils = _load_utils()
    series = pd.Series(["2025-01-01", "01/02/25", "notadate"])
    parsed = utils.parse_dates(series)
    hours = parsed.dt.hour.tolist()
    assert hours[0] == 0 and hours[1] == 0
    assert pd.isna(hours[2])


def test_load_alias_map_registers_conference_and_alias(monkeypatch):
    utils = _load_utils()
    monkeypatch.setattr(utils, "TEAM_ALIASES", {"UNC": "North Carolina"})
    monkeypatch.setattr(utils, "CONFERENCE_MAP", {"ACC": ["duke"]})
    monkeypatch.setattr(utils, "canonicalize_team_key", lambda name: str(name).lower().replace(" ", "-"))
    utils._ALIAS_MAP_CACHE = None
    alias = utils.load_alias_map()
    assert alias["unc"] == "north-carolina"
    assert alias["duke"] == "duke"  # seeded from conference map without overwrite


def test_standardize_opponent_columns_and_coalesce_merge_artifacts():
    utils = _load_utils()
    df = pd.DataFrame({"FG": [1], "FG.1": [2], "score": [50]})
    renamed = utils.standardize_opponent_columns(df)
    assert "opp_fg" in renamed.columns

    merged = utils.coalesce_merge_artifacts(pd.DataFrame({"x": [None, 1], "x_y": [5, 6]}))
    assert "x_y" not in merged.columns
    assert merged["x"].iloc[0] == 5


def test_ensure_bet_schema_adds_missing_columns(monkeypatch):
    utils = _load_utils()
    monkeypatch.setattr(utils, "canonicalize_team_key", lambda name: str(name).lower().replace(" ", "-"))
    df = pd.DataFrame({"existing": [1]})
    out = utils.ensure_bet_schema(df, cols=["existing", "newcol"])
    assert "newcol" in out.columns
