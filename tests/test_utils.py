"""
Unit tests for automation.config.utils.
"""
import sys
import types
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

# --- Stubbing ---
def _stub_modules():
    for name in list(sys.modules):
        if name.startswith("automation.config"):
            sys.modules.pop(name, None)

    automation_pkg = types.ModuleType("automation")
    automation_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "functions" / "automation")]
    sys.modules["automation"] = automation_pkg

    config_pkg = types.ModuleType("automation.config")
    config_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "functions" / "automation" / "config")]
    sys.modules["automation.config"] = config_pkg

    config = types.ModuleType("automation.config.config")
    config.TEAM_MAPPING = {"alias": "canonical"}
    config.CONFERENCE_MAP = {"ConfA": ["team-a"]}
    config.canonicalize_team_key = lambda x: x.lower().strip()
    config.CANONICAL_BET_COLS = ["col1", "col2"]
    sys.modules["automation.config.config"] = config

_stub_modules()

from automation.config import utils

def test_parse_dates():
    """Test robust date parsing."""
    series = pd.Series(["2025-01-01", "01/02/2025", "invalid", None])
    parsed = utils.parse_dates(series)
    
    assert str(parsed[0].date()) == "2025-01-01"
    assert str(parsed[1].date()) == "2025-01-02"
    assert pd.isna(parsed[2])

def test_normalize_name_and_key():
    assert utils.normalize_name("Team A!") == "teama"
    assert utils.normalize_name(None) == ""
    
    # Test series normalization via mock config
    s = pd.Series(["Team A", "Alias"])
    # "Alias" is in our mock config -> "canonical"
    utils._ALIAS_MAP_CACHE = None
    norm = utils.normalize_key(s)
    assert norm[1] == "canonical"

def test_standardize_opponent_columns():
    """Ensure .1 columns are renamed to opp_*."""
    df = pd.DataFrame({
        "FG": [10], "FG.1": [8],
        "Team": ["A"], "Opp": ["B"]
    })
    
    clean = utils.standardize_opponent_columns(df)
    assert "opp_fg" in clean.columns
    assert "FG.1" not in clean.columns
    assert clean.iloc[0]["opp_fg"] == 8

def test_ensure_bet_schema():
    """Verify missing columns are added."""
    df = pd.DataFrame({"col1": [1]})
    out = utils.ensure_bet_schema(df, cols=["col1", "col2"])
    
    assert "col2" in out.columns
    assert pd.isna(out.iloc[0]["col2"])

def test_coalesce_merge_artifacts():
    """Test merging of _x and _y suffixes."""
    df = pd.DataFrame({
        "val_x": [1, None],
        "val_y": [2, 3]
    })
    
    out = utils.coalesce_merge_artifacts(df)
    
    assert "val" in out.columns
    assert "val_x" not in out.columns
    # Row 0: val_x (1) takes precedence
    assert out.iloc[0]["val"] == 1.0
    # Row 1: val_x is NaN, so val_y (3) is used
    assert out.iloc[1]["val"] == 3.0
