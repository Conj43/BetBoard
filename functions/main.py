# This is functions/main.py

import firebase_admin
from firebase_functions import https_fn
from firebase_functions.options import SupportedRegion, MemoryOption, set_global_options
import sys
import os
from pathlib import Path

# Initialize Firebase
firebase_admin.initialize_app(options={
            "storageBucket": "betboardtest.firebasestorage.app",
            "projectId": "betboardtest"
        })

set_global_options(memory=2048)

# Ensure this functions package is importable.
FUNCTIONS_DIR = Path(__file__).resolve().parent
functions_path = str(FUNCTIONS_DIR)
if functions_path not in sys.path:
    sys.path.insert(0, functions_path)

# --- 1. DEBUG PRINTS: Check Python's environment ---
# print("--- [DEBUG] main.py: Script initializing... ---")
# print(f"--- [DEBUG] Current Working Dir: {os.getcwd()}")
# print(f"--- [DEBUG] Python sys.path: {sys.path}")

# expected_path = os.path.join(os.getcwd(), 'automation')
# print(f"--- [DEBUG] Checking for 'automation' folder at: {expected_path}")
# print(f"--- [DEBUG] Does 'automation' folder exist? {os.path.isdir(expected_path)}")


# --- Lazy-loaded pipeline modules ---
_prediction_pipeline = None
_evaluation_pipeline = None  # NEW


def _get_prediction_pipeline():
    """
    Import prediction_pipeline lazily so deployment-time analysis doesn't time out.
    """
    global _prediction_pipeline
    if _prediction_pipeline is not None:
        return _prediction_pipeline

    try:
        # print("--- [DEBUG] Lazy importing automation.pipeline.prediction_pipeline ---")
        from automation.pipeline import prediction_pipeline
        _prediction_pipeline = prediction_pipeline
        # print("--- [DEBUG] Lazy import successful. ---")
        return _prediction_pipeline
    except ImportError as exc:
        # print("--- [DEBUG] IMPORT FAILED DURING LAZY LOAD! ---", file=sys.stderr)
        # print(f"--- [DEBUG] The specific error is: {exc}", file=sys.stderr)
        raise
    except Exception as exc:
        # print(f"--- [DEBUG] Unexpected error during lazy import: {exc}", file=sys.stderr)
        raise


# --- NEW: Lazy-loader for Evaluation Pipeline ---
def _get_evaluation_pipeline():
    """
    Import evaluation_pipeline lazily.
    Assumes file is saved at: automation/pipeline/evaluation_pipeline.py
    """
    global _evaluation_pipeline
    if _evaluation_pipeline is not None:
        return _evaluation_pipeline

    try:
        # print("--- [DEBUG] Lazy importing automation.pipeline.evaluation_pipeline ---")
        # This import path assumes you saved the file as
        # functions/automation/pipeline/evaluation_pipeline.py
        from automation.pipeline import evaluation_pipeline
        _evaluation_pipeline = evaluation_pipeline
        # print("--- [DEBUG] Lazy import successful. ---")
        return _evaluation_pipeline
    except ImportError as exc:
        # print("--- [DEBUG] IMPORT FAILED DURING LAZY LOAD! ---", file=sys.stderr)
        # print(f"--- [DEBUG] The specific error is: {exc}", file=sys.stderr)
        raise
    except Exception as exc:
        # print(f"--- [DEBUG] Unexpected error during lazy import: {exc}", file=sys.stderr)
        raise


# --- HTTP-Triggered Functions ---

@https_fn.on_request(
    timeout_sec=1200,  
    memory=MemoryOption.GB_2
)
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
        
        return https_fn.Response("Prediction pipeline completed successfully.", status=200)
    
    except Exception as e:
        print("--- [ERROR] run_daily_pipeline: Pipeline FAILED! ---", file=sys.stderr)
        print(f"--- [ERROR] The error was: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        
        return https_fn.Response(f"Prediction pipeline failed: {str(e)}", status=500)


# --- NEW: HTTP-Triggered Function for Evaluation ---
@https_fn.on_request()
def run_daily_evaluation(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint triggered by Cloud Scheduler.
    Runs the evaluation pipeline daily.
    """
    print("--- [LOG] run_daily_evaluation: Function TRIGGERED by HTTP request. ---")

    try:
        print("--- [LOG] run_daily_evaluation: Calling evaluation_pipeline.run_evaluation_pipeline()... ---")
        # This calls the function with no config, so it uses DEFAULT_EVAL_CONFIG
        _get_evaluation_pipeline().run_evaluation_pipeline()
        print("--- [LOG] run_daily_evaluation: Pipeline finished successfully. ---")
        
        return https_fn.Response("Evaluation pipeline completed successfully.", status=200)
    
    except Exception as e:
        print("--- [ERROR] run_daily_evaluation: Pipeline FAILED! ---", file=sys.stderr)
        print(f"--- [ERROR] The error was: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        
        return https_fn.Response(f"Evaluation pipeline failed: {str(e)}", status=500)