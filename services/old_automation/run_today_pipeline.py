#!/usr/bin/env python3
"""
Convenience entrypoint to run the BetBoard automation stack for today's slate.

This wraps run_daily_pipeline with start/end dates set to today so you can
schedule or manually execute a single command without tweaking the config.
"""
from __future__ import annotations

from datetime import datetime

from run_daily_pipeline import PipelineConfig, main


def run_today(dry_run: bool = False, skip_ingest: bool = False, skip_features: bool = False,
              skip_publish: bool = False) -> None:
    """
    Execute the daily pipeline for today's games.

    Args:
        dry_run: If True, skip Firestore writes but still generate local outputs.
        skip_ingest: Skip the raw data ingest phase.
        skip_features: Skip feature engineering phase (expects pre-built features).
        skip_publish: Skip Firestore publishing even if dry_run is False.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    config = PipelineConfig(
        start_date=today,
        end_date=today,
        dry_run=dry_run,
        skip_ingest=skip_ingest,
        skip_features=skip_features,
        skip_publish=skip_publish,
    )
    main(config)


if __name__ == "__main__":
    run_today()
