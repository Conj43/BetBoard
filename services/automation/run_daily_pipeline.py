#!/usr/bin/env python3
"""
Helper to run the BetBoard daily pipeline end-to-end without CLI arguments.

1. (Optional) ingest fresh raw data snapshots
2. (Optional) build model-ready features
3. Score games with the latest models
4. Publish predictions to Firebase Firestore and save local artifacts
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Sequence

try:
    import joblib  # type: ignore
except ImportError:
    joblib = None  # noqa: N816

import build_features
import ingest_raw
import make_preds
from config import (
    FIREBASE_CREDENTIALS_PATH,
    MAX_PICKS_TO_PUBLISH,
    MODEL_DIR,
    MODEL_FALLBACK_LOCAL_DIR,
    BET_MODEL_DIR,
    BET_MODEL_FALLBACK_LOCAL_DIR,
    PREDICTIONS_DIR,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    FEATURE_COLS_ORDER,
)
from firestore_publisher import publish_predictions_to_firestore


FeatureColumnsSource = Sequence[str] | str | None


def _ensure_model_dir_available(model_dir: str | os.PathLike[str]) -> str:
    try:
        return make_preds._ensure_local_model_dir(str(model_dir))
    except FileNotFoundError:
        model_str = str(model_dir)
        if "with_bet" in model_str:
            return str(BET_MODEL_FALLBACK_LOCAL_DIR)
        return str(MODEL_FALLBACK_LOCAL_DIR)


@dataclass
class PipelineConfig:
    """Configure how the daily pipeline should run."""

    start_date: str | None = None  # None => today
    end_date: str | None = None    # None => same as start_date
    model_dir: str = MODEL_DIR
    feature_columns_source: FeatureColumnsSource = None  # list, file path, or comma string
    firebase_creds: str | None = FIREBASE_CREDENTIALS_PATH
    max_picks: int = MAX_PICKS_TO_PUBLISH
    skip_ingest: bool = False
    skip_features: bool = False
    skip_publish: bool = False
    dry_run: bool = False


PIPELINE_CONFIG = PipelineConfig()


def _date_range(start: datetime, end: datetime) -> List[str]:
    cur = start
    out: List[str] = []
    while cur <= end:
        out.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return out


def _parse_date(label: str) -> datetime:
    return datetime.strptime(label, "%Y-%m-%d")


def _clean_for_json(obj):
    if isinstance(obj, dict):
        return {k: _clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_for_json(v) for v in obj]
    if isinstance(obj, tuple):
        return [_clean_for_json(v) for v in obj]
    if hasattr(obj, "item") and callable(getattr(obj, "item")):
        try:
            return obj.item()
        except Exception:
            pass
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def _write_local_outputs(date_str: str, game_preds, top_picks, output_dir: str | os.PathLike[str]) -> None:
    # Local persistence disabled for cloud deployment.
    return


def _load_feature_columns(model_dir: str | os.PathLike[str], explicit: Sequence[str] | None = None) -> List[str]:
    if explicit:
        return list(explicit)

    model_path = Path(_ensure_model_dir_available(model_dir))
    candidates = [
        model_path / "feature_names.pkl",
        model_path / "feature_names.json",
        model_path / "features.txt",
    ]

    for candidate in candidates:
        if not candidate.exists():
            continue

        if candidate.suffix == ".pkl":
            if joblib is None:
                raise RuntimeError(
                    f"joblib is required to read {candidate}, but it is not installed."
                )
            return list(joblib.load(candidate))

        if candidate.suffix == ".json":
            with open(candidate) as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return list(data.get("feature_names", data.get("features", [])))
                return list(data)

        # treat as newline separated list
        with open(candidate) as fh:
            cols = [line.strip() for line in fh if line.strip()]
            if cols:
                return cols

    if FEATURE_COLS_ORDER:
        return list(FEATURE_COLS_ORDER)

    raise RuntimeError(
        "Unable to determine feature column order. "
        "Provide a feature list via PipelineConfig or ensure feature_names.(pkl|json|txt) "
        "is present in the model directory."
    )


def _resolve_explicit_feature_columns(source: FeatureColumnsSource) -> Sequence[str] | None:
    if source is None:
        return None

    if isinstance(source, (list, tuple)):
        return [str(col) for col in source]

    path = Path(str(source))
    if path.exists():
        with open(path) as fh:
            raw = fh.read()
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(col) for col in data]
        except json.JSONDecodeError:
            pass
        return [line.strip() for line in raw.splitlines() if line.strip()]

    raw = str(source)
    return [item.strip() for item in raw.split(",") if item.strip()]


def main(config: PipelineConfig | None = None) -> None:
    cfg = config or PIPELINE_CONFIG

    start_label = cfg.start_date or datetime.now().strftime("%Y-%m-%d")
    end_label = cfg.end_date or start_label

    start_dt = _parse_date(start_label)
    end_dt = _parse_date(end_label)
    if end_dt < start_dt:
        raise ValueError("end_date must be >= start_date")

    date_strings = _date_range(start_dt, end_dt)

    print("=== BetBoard Daily Pipeline ===")
    print(f"Dates: {date_strings[0]} → {date_strings[-1]}")
    print(f"Raw data dir: {RAW_DATA_DIR}")
    print(f"Processed features dir: {PROCESSED_DATA_DIR}")
    print(f"Predictions output dir: {PREDICTIONS_DIR}")
    print(f"Model dir: {cfg.model_dir}")

    explicit_cols = _resolve_explicit_feature_columns(cfg.feature_columns_source)
    feature_cols = _load_feature_columns(cfg.model_dir, explicit_cols)
    print(f"Using {len(feature_cols)} feature columns (no-bet model).")

    bet_feature_cols = _load_feature_columns(BET_MODEL_DIR, explicit_cols)
    print(f"Using {len(bet_feature_cols)} feature columns (bet model).")

    if not cfg.skip_ingest:
        print("\n[Step 1] Ingesting raw data...")
        ingest_raw.ingest_raw_for_range(date_strings[0], date_strings[-1])
    else:
        print("\n[Step 1] Skipped raw ingest.")

    if not cfg.skip_features:
        print("\n[Step 2] Building features...")
        build_features.build_features_for_range(date_strings[0], date_strings[-1])
    else:
        print("\n[Step 2] Skipped feature build.")

    print("\n[Step 3] Scoring games...")
    all_results = []
    all_picks = []

    for date_str in date_strings:
        print(f"  - {date_str}")
        feature_path = Path(PROCESSED_DATA_DIR) / f"{date_str}_features.csv"
        if not feature_path.exists():
            print(f"    No feature file found at {feature_path}. Skipping.")
            continue

        game_preds, top_picks = make_preds.run_predictions_for_date(
            date_str,
            feature_cols,
            model_dir=cfg.model_dir,
        )
        if not game_preds:
            print(f"    (no games/features found for {date_str})")
            continue

        bet_model_preds, _ = make_preds.run_predictions_for_date(
            date_str,
            bet_feature_cols,
            model_dir=BET_MODEL_DIR,
        )

        _write_local_outputs(date_str, game_preds, top_picks, PREDICTIONS_DIR)

        all_results.extend(game_preds)
        all_picks.extend(top_picks)

        if not cfg.skip_publish and not cfg.dry_run:
            publish_predictions_to_firestore(
                date_str=date_str,
                game_level_preds=game_preds,
                top_picks=top_picks,
                credentials_path=cfg.firebase_creds,
                max_picks=cfg.max_picks,
                bet_model_preds=bet_model_preds,
            )
            print(f"    Published {len(game_preds)} games / {len(top_picks)} picks to Firestore.")
        else:
            print("    Publishing skipped.")

    if not all_results:
        print("\nNo predictions generated. Ensure raw data and features exist for the requested dates.")
        return

    print("\nPipeline complete!")
    if cfg.dry_run:
        print("Dry-run mode: Firestore writes were skipped.")
    elif cfg.skip_publish:
        print("Reminder: Firestore publishing was disabled (skip_publish=True).")


if __name__ == "__main__":
    main()
