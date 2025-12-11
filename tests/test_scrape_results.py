"""
Unit tests for automation.evaluation.scrape_results.
"""
import sys
import types
from datetime import date, datetime
from unittest.mock import MagicMock, patch
import pytest

# --- Module Stubbing ---
def _stub_scrape_module():
    # Stub dependencies
    fb = types.ModuleType("firebase_admin")
    fb.initialize_app = lambda *a, **k: None
    sys.modules["firebase_admin"] = fb
    
    firestore = types.ModuleType("firebase_admin.firestore")
    firestore.SERVER_TIMESTAMP = "SERVER_TIMESTAMP"
    sys.modules["firebase_admin.firestore"] = firestore

    # Stub config
    config = types.ModuleType("automation.config.config")
    config.FIRESTORE_PREDICTIONS_COLLECTION = "predictions"
    config.TEAM_MAPPING = {"Georgia Bulldogs": "georgia"} # Sample mapping
    sys.modules["automation.config.config"] = config

    # Stub firestore client
    fs_client = types.ModuleType("automation.clients.firestore")
    fs_client._ensure_firestore = MagicMock()
    sys.modules["automation.clients.firestore"] = fs_client

    # Stub team keys
    keys = types.ModuleType("automation.config.team_keys")
    keys.canonicalize_team_key = lambda x: x.lower().replace(" ", "-")
    sys.modules["automation.config.team_keys"] = keys

_stub_scrape_module()

# Import after stubbing
from automation.evaluation import scrape_results

@pytest.fixture
def mock_odds_response():
    """Returns a sample Odds API JSON response."""
    return [
        {
            "id": "game_1",
            "home_team": "Georgia Bulldogs",
            "away_team": "Alabama",
            "commence_time": "2025-11-17T23:30:00Z",
            "completed": True,
            "scores": [
                {"name": "Georgia Bulldogs", "score": "75"},
                {"name": "Alabama", "score": "80"}
            ]
        },
        {
            "id": "game_incomplete",
            "home_team": "Duke",
            "away_team": "UNC",
            "commence_time": "2025-11-17T23:30:00Z",
            "completed": False, # Should be filtered
            "scores": None
        }
    ]

def test_normalize_team_from_odds_api():
    # Test direct mapping match
    assert scrape_results._normalize_team_from_odds_api("Georgia Bulldogs") == "georgia"
    # Test fallback to canonicalize
    assert scrape_results._normalize_team_from_odds_api("Alabama") == "alabama"
    # Test empty
    assert scrape_results._normalize_team_from_odds_api(None) == ""

def test_fetch_completed_scores_filtering(mock_odds_response):
    """Verify filtering of incomplete games and score parsing."""
    with patch("requests.Session.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_odds_response
        
        fetcher = scrape_results.OddsAPIScoresFetcher("fake_key")
        # Target date matching the mocked commence_time
        target_date = date(2025, 11, 17) 
        
        # We assume UTC for simplicity in test environment if ZoneInfo fails or is mocked
        results = fetcher.fetch_completed_scores_for_date(target_date, tz_name="UTC")
        
        assert len(results) == 1
        game = results[0]
        assert game["game_id"] == "game_1"
        assert game["home_score"] == 75
        assert game["away_score"] == 80
        assert game["home_team"] == "georgia" # Normalized

def test_match_game_doc_by_id():
    """Test matching API result to Firestore doc via Game ID."""
    mock_doc = MagicMock()
    mock_doc.doc_id = "doc_1"
    
    lookup_id = {"game_1": mock_doc}
    lookup_team = {}
    
    api_game = {"game_id": "game_1", "home_team": "a", "away_team": "b"}
    
    match = scrape_results._match_game_doc(api_game, lookup_id, lookup_team)
    assert match == mock_doc

def test_match_game_doc_by_teams():
    """Test matching API result to Firestore doc via Team Names."""
    # Create a lookup entry
    entry = scrape_results.GameDocLookup(
        doc_id="doc_teams", 
        reference=None, 
        team_set=frozenset(["team-a", "team-b"]),
        home_team="team-a", 
        away_team="team-b"
    )
    
    lookup_id = {}
    lookup_team = {frozenset(["team-a", "team-b"]): [entry]}
    
    # API game has no ID but matching teams
    api_game = {"game_id": None, "home_team": "team-a", "away_team": "team-b"}
    
    match = scrape_results._match_game_doc(api_game, lookup_id, lookup_team)
    assert match == entry

def test_publish_results_flow():
    """Test the full publish flow with mocked Firestore."""
    mock_db = MagicMock()
    scrape_results._ensure_firestore = MagicMock(return_value=mock_db)
    
    # Setup Firestore stream to return one matching game doc
    mock_snapshot = MagicMock()
    mock_snapshot.id = "firestore_doc_1"
    mock_snapshot.to_dict.return_value = {"home_team": "Georgia Bulldogs", "away_team": "Alabama"}
    
    # The collection stream returns our snapshot
    mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = [mock_snapshot]
    
    games_input = [{
        "game_id": "api_id_1",
        "home_team": "georgia", # Normalized
        "away_team": "alabama", # Normalized
        "home_score": 70,
        "away_score": 65,
        "home_team_raw": "Georgia Bulldogs",
        "away_team_raw": "Alabama"
    }]
    
    scrape_results.publish_results("2025-11-17", games_input)
    
    # Verify set() was called on the results subcollection
    results_col = mock_snapshot.reference.collection.return_value
    results_col.document.assert_called_with("odds_api")
    results_col.document.return_value.set.assert_called_once()
    
    # Check that scores were written
    args, _ = results_col.document.return_value.set.call_args
    payload = args[0]
    assert payload["home_score"] == 70
    assert payload["away_score"] == 65