# Save this file as:
# functions/automation/pipeline/evaluation_pipeline.py
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

# The sys.path manipulation from the original file has been REMOVED
# as it's not needed when imported by functions/main.py
_current_file = Path(__file__).resolve()
_functions_dir = _current_file.parent.parent.parent
if str(_functions_dir) not in sys.path:
    sys.path.insert(0, str(_functions_dir))

from automation.evaluation import evaluate_predictions as evaluator
from automation.evaluation import scrape_results
from automation.evaluation.settle_user_bets import settle_pending_bets


@dataclass
class EvaluationPipelineConfig:
    """Runtime knobs for the evaluation pipeline."""

    # Provide either (start_date + end_date) OR single_date. Leave blank to
    # evaluate yesterday (UTC) automatically.
    start_date: str | None = None
    end_date: str | None = None
    single_date: str | None = None
    days_back_default: int = 1  # Used when no explicit date(s) set

    scrape_results_first: bool = True
    timezone: str = scrape_results.DEFAULT_TIMEZONE

    result_source: str = evaluator.DEFAULT_RESULT_DOC
    eval_collection: str = evaluator.DEFAULT_EVAL_COLLECTION
    settle_user_bets: bool = True

    dry_run: bool = False
    verbose: bool = False


# --- Edit these defaults as needed ----------------------------------------- #
DEFAULT_EVAL_CONFIG = EvaluationPipelineConfig(
    # Example overrides:
    # start_date="2025-11-01",
    # end_date="2025-11-05",
    # single_date="2025-11-04",
    # dry_run=True,
)
# --------------------------------------------------------------------------- #

def _resolve_dates(cfg: EvaluationPipelineConfig) -> Tuple[List[str], bool]:
    """
    Return (list_of_dates, is_range). Dates are YYYY-MM-DD strings.
    """
    if cfg.start_date and cfg.end_date:
        start_dt = datetime.strptime(cfg.start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(cfg.end_date, "%Y-%m-%d").date()
        if end_dt < start_dt:
            raise ValueError("end_date must be on or after start_date")
        dates: List[str] = []
        cur = start_dt
        while cur <= end_dt:
            dates.append(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)
        return dates, True

    if cfg.start_date or cfg.end_date:
        raise ValueError("Provide both start_date and end_date, or neither.")

    if cfg.single_date:
        datetime.strptime(cfg.single_date, "%Y-%m-%d")  # validate format
        return [cfg.single_date], False

    # Use Chicago timezone to match scraper and odds API
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
        default_date = (datetime.now(tz).date() - timedelta(days=cfg.days_back_default)).strftime("%Y-%m-%d")
    except:
        # Fallback to UTC if zoneinfo unavailable
        default_date = (datetime.utcnow().date() - timedelta(days=cfg.days_back_default)).strftime("%Y-%m-%d")
    
    return [default_date], False


def _run_scraper_for_date(date_str: str, cfg: EvaluationPipelineConfig) -> None:
    args: List[str] = ["--date", date_str, "--timezone", cfg.timezone]
    if cfg.dry_run:
        args.append("--dry-run")
    if cfg.verbose:
        args.append("--verbose")

    print(f"[evaluation][step] Scraping results for {date_str}...")
    scrape_results.main(args)


def _run_evaluator(dates: Sequence[str], is_range: bool, cfg: EvaluationPipelineConfig) -> None:
    args: List[str] = []
    if is_range:
        args.extend(["--start-date", dates[0], "--end-date", dates[-1]])
    else:
        args.extend(["--date", dates[0]])

    args.extend(["--result-source", cfg.result_source])
    args.extend(["--collection", cfg.eval_collection])
    if cfg.dry_run:
        args.append("--dry-run")
    if cfg.verbose:
        args.append("--verbose")

    print(f"[evaluation][step] Evaluating predictions for {dates[0]}{' → ' + dates[-1] if is_range else ''}...")
    evaluator.main(args)


def run_evaluation_pipeline(config: EvaluationPipelineConfig | None = None) -> None:
    import firebase_admin
    from google.cloud import firestore
    
    print(f"[DEBUG] Firebase apps initialized: {len(firebase_admin._apps)}")
    if firebase_admin._apps:
        print(f"[DEBUG] Default app exists: {firebase_admin._apps.get('[DEFAULT]')}")
    
    db = firestore.Client()
    print(f"[DEBUG] Firestore connected to project: {db.project}")
    
    # Check if predictions exist
    test_ref = db.collection('games').document('2025-11-15').collection('games')
    count = len(list(test_ref.limit(1).stream()))
    print(f"[DEBUG] Predictions in this project: {count} games")
    print(f"[DEBUG] Expected project: betboardtest")
    print()
    cfg = config or DEFAULT_EVAL_CONFIG
    dates, is_range = _resolve_dates(cfg)

    if cfg.scrape_results_first:
        for date_str in dates:
            _run_scraper_for_date(date_str, cfg)
    else:
        print("[evaluation][step] Skipping result scraping (scrape_results_first=False).")

    _run_evaluator(dates, is_range, cfg)
    if cfg.settle_user_bets:
        settle_pending_bets(
            db,
            result_source=cfg.result_source,
            dry_run=cfg.dry_run,
            verbose=cfg.verbose,
        )
    else:
        print("[evaluation][bets] Skipping bet settlement (settle_user_bets=False).")
    print("[evaluation] Pipeline complete.")


if __name__ == "__main__":
    # For local testing
    test_config = EvaluationPipelineConfig(
        start_date="2025-11-06",
        end_date="2025-11-17",
        dry_run=False,
        verbose=True
    )
    run_evaluation_pipeline(test_config)
