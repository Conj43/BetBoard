"""
Integration tests for functions/main.py.
Mocks the Cloud Function environment to verify pipeline triggers.
"""
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# --- 1. PATH SETUP: Ensure we can import from functions/ ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS_DIR = PROJECT_ROOT / "functions"
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

# --- 2. STUBBING: Mock firebase_functions and admin ---
def _stub_cloud_environment():
    # Stub firebase_admin
    fb = types.ModuleType("firebase_admin")
    fb.initialize_app = lambda *args, **kwargs: None
    sys.modules["firebase_admin"] = fb

    # Stub firebase_functions hierarchy
    ff = types.ModuleType("firebase_functions")
    
    # Stub https_fn
    https_fn = types.ModuleType("firebase_functions.https_fn")
    
    # Decorator stub: @on_request(...) returns the original function
    def on_request_stub(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    https_fn.on_request = on_request_stub
    
    # Stub Response class
    class MockResponse:
        def __init__(self, body, status=200):
            self.body = body
            self.status = status
    https_fn.Response = MockResponse
    # Simple Request placeholder for type hints
    class MockRequest:
        pass
    https_fn.Request = MockRequest
    
    ff.https_fn = https_fn
    
    # Stub options
    options = types.ModuleType("firebase_functions.options")
    options.SupportedRegion = MagicMock()
    options.MemoryOption = MagicMock()
    options.set_global_options = MagicMock()
    ff.options = options
    
    sys.modules["firebase_functions"] = ff
    sys.modules["firebase_functions.https_fn"] = https_fn
    sys.modules["firebase_functions.options"] = options

_stub_cloud_environment()

# --- 3. IMPORT UNDER TEST ---
# With 'functions' in sys.path, we can import 'main' directly
import main as cloud_functions

def test_run_daily_pipeline_success():
    """Scenario: Successful scheduled trigger execution."""
    mock_req = MagicMock()
    
    # Mock the lazy loader to return a mock pipeline
    mock_pipeline_module = MagicMock()
    
    with patch("main._get_prediction_pipeline", return_value=mock_pipeline_module):
        response = cloud_functions.run_daily_pipeline(mock_req)
        
        # Verify the pipeline was run
        mock_pipeline_module.run_prediction_pipeline.assert_called_once()
        assert response.status == 200
        assert "completed successfully" in response.body

def test_run_daily_pipeline_failure():
    """Scenario: Pipeline execution failure (e.g. Exception)."""
    mock_req = MagicMock()
    mock_pipeline_module = MagicMock()
    
    # Simulate a crash in the pipeline
    mock_pipeline_module.run_prediction_pipeline.side_effect = Exception("Critical DB Error")
    
    with patch("main._get_prediction_pipeline", return_value=mock_pipeline_module):
        response = cloud_functions.run_daily_pipeline(mock_req)
        
        assert response.status == 500
        assert "Prediction pipeline failed" in response.body


def test_run_daily_evaluation_success():
    """Scenario: Evaluation pipeline completes."""
    mock_req = MagicMock()
    mock_eval_module = MagicMock()
    with patch("main._get_evaluation_pipeline", return_value=mock_eval_module):
        response = cloud_functions.run_daily_evaluation(mock_req)
        mock_eval_module.run_evaluation_pipeline.assert_called_once()
        assert response.status == 200
        assert "Evaluation pipeline completed successfully" in response.body


def test_run_daily_evaluation_failure():
    """Scenario: Evaluation pipeline throws."""
    mock_req = MagicMock()
    mock_eval_module = MagicMock()
    mock_eval_module.run_evaluation_pipeline.side_effect = RuntimeError("Boom")
    with patch("main._get_evaluation_pipeline", return_value=mock_eval_module):
        response = cloud_functions.run_daily_evaluation(mock_req)
        assert response.status == 500
        assert "Evaluation pipeline failed" in response.body
