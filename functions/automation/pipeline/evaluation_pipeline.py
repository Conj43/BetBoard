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

from automation.evaluation import evaluate_predictions as evaluator
from automation.evaluation import scrape_results


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
    cfg = config or DEFAULT_EVAL_CONFIG
    dates, is_range = _resolve_dates(cfg)

    if cfg.scrape_results_first:
        for date_str in dates:
            _run_scraper_for_date(date_str, cfg)
    else:
        print("[evaluation][step] Skipping result scraping (scrape_results_first=False).")

    _run_evaluator(dates, is_range, cfg)
    print("[evaluation] Pipeline complete.")
