# This is functions/main.py

import firebase_admin
from firebase_functions import https_fn
from firebase_functions.options import set_global_options
import sys
import os
from pathlib import Path

# Initialize Firebase
firebase_admin.initialize_app()

set_global_options(memory=2048)

# Ensure this functions package is importable.
FUNCTIONS_DIR = Path(__file__).resolve().parent
functions_path = str(FUNCTIONS_DIR)
if functions_path not in sys.path:
    sys.path.insert(0, functions_path)

# --- 1. DEBUG PRINTS: Check Python's environment ---
print("--- [DEBUG] main.py: Script initializing... ---")
print(f"--- [DEBUG] Current Working Dir: {os.getcwd()}")
print(f"--- [DEBUG] Python sys.path: {sys.path}")

expected_path = os.path.join(os.getcwd(), 'automation')
print(f"--- [DEBUG] Checking for 'automation' folder at: {expected_path}")
print(f"--- [DEBUG] Does 'automation' folder exist? {os.path.isdir(expected_path)}")


_prediction_pipeline = None


def _get_prediction_pipeline():
    """
    Import prediction_pipeline lazily so deployment-time analysis doesn't time out.
    """
    global _prediction_pipeline
    if _prediction_pipeline is not None:
        return _prediction_pipeline

    try:
        print("--- [DEBUG] Lazy importing automation.pipeline.prediction_pipeline ---")
        from automation.pipeline import prediction_pipeline
        _prediction_pipeline = prediction_pipeline
        print("--- [DEBUG] Lazy import successful. ---")
        return _prediction_pipeline
    except ImportError as exc:
        print("--- [DEBUG] IMPORT FAILED DURING LAZY LOAD! ---", file=sys.stderr)
        print(f"--- [DEBUG] The specific error is: {exc}", file=sys.stderr)
        raise
    except Exception as exc:
        print(f"--- [DEBUG] Unexpected error during lazy import: {exc}", file=sys.stderr)
        raise


@https_fn.on_request()
def run_daily_pipeline(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint triggered by Cloud Scheduler.
    Runs the prediction pipeline daily.
    """
    print("--- [LOG] run_daily_pipeline: Function TRIGGERED by HTTP request. ---")

    try:
        print("--- [LOG] run_daily_pipeline: Calling prediction_pipeline.run_prediction_pipeline()... ---")
        _get_prediction_pipeline().run_prediction_pipeline()
        print("--- [LOG] run_daily_pipeline: Pipeline finished successfully. ---")
        
        return https_fn.Response("Pipeline completed successfully.", status=200)
    
    except Exception as e:
        print("--- [ERROR] run_daily_pipeline: Pipeline FAILED! ---", file=sys.stderr)
        print(f"--- [ERROR] The error was: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        
        return https_fn.Response(f"Pipeline failed: {str(e)}", status=500)