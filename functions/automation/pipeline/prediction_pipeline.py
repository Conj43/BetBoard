#!/usr/bin/env python3
"""
Single entry point to fetch data, build features, score games, and publish
predictions for today's slate. If you need custom behavior (date range,
skip flags, etc.) construct a `PredictionPipelineConfig` and call
`run_prediction_pipeline(config)`.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SERVICES_ROOT = PROJECT_ROOT / "services"
for path in (PROJECT_ROOT, SERVICES_ROOT):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import pandas as pd

from automation.clients import gamelog as gamelog_client
from automation.clients import odds as odds_client
from automation.clients import torvik as torvik_client
from automation.clients.firestore import publish_predictions_to_firestore
from automation.config.config import (
    FIREBASE_CREDENTIALS_PATH,
    FEATURE_COLS_ORDER,
    MAX_PICKS_TO_PUBLISH,
    MODEL_DIR,
    BET_MODEL_DIR,
)
from automation.prediction import make_preds
from automation.processing import build_features, ingest_raw

FeatureColumnsSource = Sequence[str] | str | None


def _require_firebase_storage() -> None:
    """Ensure firebase_admin with storage support is available before scoring."""
    if getattr(make_preds, "firebase_admin", None) is None:
        raise RuntimeError(
            "firebase_admin is not installed; required for model/feature downloads."
        )
    if getattr(make_preds, "storage", None) is None:
        raise RuntimeError(
            "firebase_admin.storage missing; install firebase-admin with storage extras."
        )


@dataclass
class PredictionPipelineConfig:
    start_date: str | None = None  # defaults to today
    end_date: str | None = None    # defaults to start_date
    model_dir: str = MODEL_DIR
    bet_model_dir: str = BET_MODEL_DIR
    feature_columns_source: FeatureColumnsSource = None
    firebase_creds: str | None = FIREBASE_CREDENTIALS_PATH
    max_picks: int = MAX_PICKS_TO_PUBLISH
    skip_ingest: bool = False
    skip_features: bool = False
    skip_publish: bool = False
    dry_run: bool = False
    skip_refresh: bool = False


def _run_client_task(label: str, func: Callable[[], Any]) -> bool:
    try:
        result = func()
        if isinstance(result, tuple) and len(result) == 2:
            payload, status = result
            if status and status >= 400:
                print(f"    [{label}] completed with status {status}: {payload}")
                return False
        print(f"    [{label}] completed successfully.")
        return True
    except Exception as exc:
        print(f"    [{label}] failed: {exc}")
        return False


def _refresh_source_data() -> None:
    tasks: List[Tuple[str, Callable[[], Any]]] = [
        ("odds", lambda: odds_client.get_college_basketball_games("basketball_ncaab")),
        ("gamelog", gamelog_client.main_entry_point),
        ("torvik", torvik_client.scrape_torvik),
    ]

    for label, func in tasks:
        _run_client_task(label, func)


def _date_range(start: datetime, end: datetime) -> List[str]:
    dates: List[str] = []
    cur = start
    while cur <= end:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return dates


def _parse_date(label: str) -> datetime:
    return datetime.strptime(label, "%Y-%m-%d")


def _load_feature_columns(model_dir: str, explicit: Sequence[str] | None = None) -> List[str]:
    if explicit:
        return list(explicit)

    _require_firebase_storage()
    feature_names = make_preds.get_feature_names(str(model_dir))
    if feature_names:
        return feature_names

    if FEATURE_COLS_ORDER:
        return list(FEATURE_COLS_ORDER)

    raise RuntimeError(
        "Unable to determine feature columns. Provide feature_columns_source or "
        "ensure feature_names.(pkl|json|txt) exists in your model directory."
    )


def _resolve_explicit_feature_columns(source: FeatureColumnsSource) -> Sequence[str] | None:
    if source is None:
        return None

    if isinstance(source, (list, tuple)):
        return [str(col) for col in source]

    path = Path(str(source))
    if path.exists():
        raw = path.read_text().strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(col) for col in data]
        except json.JSONDecodeError:
            pass
        return [line.strip() for line in raw.splitlines() if line.strip()]

    raw = str(source)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _download_features_df(date_str: str) -> pd.DataFrame:
    _require_firebase_storage()
    remote_path = f"{build_features.PROCESSED_FEATURES_PREFIX}/{date_str}/features.csv"
    return build_features._download_csv(remote_path)  # type: ignore[attr-defined]


def _score_with_models(
    features_df: pd.DataFrame,
    feature_cols: Sequence[str],
    model_dir: str,
) -> List[Dict[str, Any]]:
    if features_df.empty:
        return []

    missing_cols = [col for col in feature_cols if col not in features_df.columns]
    if missing_cols:
        raise ValueError(f"Missing feature columns: {missing_cols}")

    valid_mask = features_df[feature_cols].notna().all(axis=1)
    invalid = features_df[~valid_mask]
    if not invalid.empty:
        print(f"[WARN] Skipping {len(invalid)} rows with incomplete features.")

    usable = features_df[valid_mask]
    if usable.empty:
        return []

    spread_model, total_model, winprob_model = make_preds.load_models(model_dir)
    grouped = make_preds.split_home_away(usable)

    game_level_preds: List[Dict[str, Any]] = []
    for _, side_info in grouped.items():
        game_pred = make_preds.score_game(
            group_entry=side_info,
            spread_model=spread_model,
            total_model=total_model,
            winprob_model=winprob_model,
            feature_cols=list(feature_cols),
        )
        game_level_preds.append(game_pred)

    return game_level_preds


def _filter_rows_with_full_odds(features_df: pd.DataFrame) -> pd.DataFrame:
    required = ["bet_spread", "bet_total", "moneyline_a", "moneyline_b"]
    if not all(col in features_df.columns for col in required):
        return pd.DataFrame(columns=features_df.columns)
    mask = features_df[required].notna().all(axis=1)
    return features_df[mask]


def _label_missing_odds(game_preds: Iterable[Dict[str, Any]]) -> None:
    for pred in game_preds:
        for key in ("bet_spread_home", "bet_total", "moneyline_home", "moneyline_away"):
            value = pred.get(key)
            if value is None or value == "" or (isinstance(value, float) and math.isnan(value)):
                pred[key] = "No Odds"


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _choose_bets_for_game(game_pred: Mapping[str, Any]) -> List[Dict[str, Any]]:
    game_id = game_pred.get("game_id")
    home_team = game_pred.get("home_team") or game_pred.get("Team")
    away_team = game_pred.get("away_team") or game_pred.get("Opp")

    picks: List[Dict[str, Any]] = []
    bookmakers = game_pred.get("bookmakers") or {}
    preferred_books = ("betmgm", "fanduel", "draftkings")

    model_spread = _as_float(game_pred.get("model_spread_home"))
    line_spread = _as_float(game_pred.get("bet_spread_home"))

    if model_spread is not None and line_spread is not None:
        # Spread edge is the predicted ATS margin: predicted_margin + bookmaker_line
        edge = model_spread + line_spread
        selection = home_team if edge >= 0 else away_team
        picks.append({
            "game_id": game_id,
            "bet_type": "spread",
            "selection": selection,
            "model_projection": model_spread,
            "book_line": line_spread,
            "edge_strength": abs(edge),
        })

    def _best_total():
        best = None
        for book_key, payload in bookmakers.items():
            if not any(pref in str(book_key).lower() for pref in preferred_books):
                continue
            total = payload.get("total")
            if not isinstance(total, dict):
                continue
            over = total.get("over") or {}
            under = total.get("under") or {}
            for label, market in (("Over", over), ("Under", under)):
                line = market.get("line")
                if line is None:
                    continue
                model_total = _as_float(game_pred.get("model_total"))
                if model_total is None:
                    continue
                edge = model_total - line if label == "Over" else line - model_total
                if best is None or abs(edge) > abs(best[0]):
                    best = (edge, line, book_key, label, market.get("price"))
        return best

    best_total = _best_total()
    model_total = _as_float(game_pred.get("model_total"))
    if best_total:
        edge, line_total, book_key, selection, price = best_total
        picks.append({
            "game_id": game_id,
            "bet_type": "total",
            "selection": selection,
            "model_projection": model_total,
            "book_line": line_total,
            "bookmaker": book_key,
            "edge_strength": abs(edge),
            "odds": price,
            "odds_to_prob": make_preds.implied_prob_from_moneyline(price),
        })
    elif model_total is not None:
        line_total = _as_float(game_pred.get("bet_total"))
        if line_total is not None:
            edge = model_total - line_total
            picks.append({
                "game_id": game_id,
                "bet_type": "total",
                "selection": "Over" if edge >= 0 else "Under",
                "model_projection": model_total,
                "book_line": line_total,
                "edge_strength": abs(edge),
            })

    home_prob = _as_float(game_pred.get("home_win_prob"))
    if home_prob is not None and bookmakers:
        away_prob = 1.0 - home_prob
        best_home = None
        best_away = None

        for book_key, payload in bookmakers.items():
            if not any(pref in str(book_key).lower() for pref in preferred_books):
                continue
            moneyline = payload.get("moneyline") or {}
            home_line = moneyline.get("home")
            if home_line is not None:
                home_implied = make_preds.implied_prob_from_moneyline(home_line)
                if home_implied is not None:
                    edge = home_prob - home_implied
                    if best_home is None or edge > best_home[0]:
                        best_home = (edge, home_line, book_key)
            away_line = moneyline.get("away")
            if away_line is not None:
                away_implied = make_preds.implied_prob_from_moneyline(away_line)
                if away_implied is not None:
                    edge = away_prob - away_implied
                    if best_away is None or edge > best_away[0]:
                        best_away = (edge, away_line, book_key)

        if best_home:
            picks.append({
                "game_id": game_id,
                "bet_type": "moneyline",
                "selection": home_team,
                "model_projection": home_prob,
                "book_line": best_home[1],
                "bookmaker": best_home[2],
                "edge_strength": best_home[0],
                "odds": best_home[1],
                "odds_to_prob": make_preds.implied_prob_from_moneyline(best_home[1]),
            })
        if best_away:
            picks.append({
                "game_id": game_id,
                "bet_type": "moneyline",
                "selection": away_team,
                "model_projection": away_prob,
                "book_line": best_away[1],
                "bookmaker": best_away[2],
                "edge_strength": best_away[0],
                "odds": best_away[1],
                "odds_to_prob": make_preds.implied_prob_from_moneyline(best_away[1]),
            })

    return picks


def run_prediction_pipeline(config: PredictionPipelineConfig | None = None) -> None:
    cfg = config or PredictionPipelineConfig()

    start_label = cfg.start_date or datetime.now(CENTRAL_TZ).strftime("%Y-%m-%d")
    end_label = cfg.end_date or start_label

    start_dt = _parse_date(start_label)
    end_dt = _parse_date(end_label)
    if end_dt < start_dt:
        raise ValueError("end_date must be >= start_date")

    date_strings = _date_range(start_dt, end_dt)
    print("=== BetBoard Prediction Pipeline ===")
    print(f"Dates: {date_strings[0]} → {date_strings[-1]}")
    print(f"Model dir: {cfg.model_dir}")

    explicit_cols = _resolve_explicit_feature_columns(cfg.feature_columns_source)
    feature_cols = _load_feature_columns(cfg.model_dir, explicit_cols)
    bet_feature_cols = _load_feature_columns(cfg.bet_model_dir, explicit_cols)
    print(f"Using {len(feature_cols)} feature columns (main model).")
    print(f"Using {len(bet_feature_cols)} feature columns (bet model).")

    built_features: Dict[str, pd.DataFrame] = {}

    if not cfg.skip_refresh:
        print("\n[1/5] Refreshing upstream data via clients...")
        _refresh_source_data()
    else:
        print("\n[1/5] Skipping source refresh (skip_refresh=True).")

    if not cfg.skip_ingest:
        print("\n[2/5] Ingesting raw data (schedule, odds, gamelog, torvik)...")
        ingest_raw.ingest_raw_for_range(date_strings[0], date_strings[-1])
    else:
        print("\n[2/5] Skipping ingest.")

    if not cfg.skip_features:
        print("\n[3/5] Building features...")
        for date_str in date_strings:
            print(f"  - {date_str}")
            built_features[date_str] = build_features.build_features_for_date(date_str)
    else:
        print("\n[3/5] Skipping feature build.")

    print("\n[4/5] Scoring games...")
    for date_str in date_strings:
        print(f"  - {date_str}")
        features_df = built_features.get(date_str)
        if features_df is None:
            try:
                features_df = _download_features_df(date_str)
            except FileNotFoundError as exc:
                print(f"    Missing features for {date_str}: {exc}")
                continue

        game_preds = _score_with_models(features_df, feature_cols, cfg.model_dir)
        if not game_preds:
            print("    No valid games to score.")
            continue

        day_picks: List[Dict[str, Any]] = []
        for game_pred in game_preds:
            day_picks.extend(_choose_bets_for_game(game_pred))

        _label_missing_odds(game_preds)
        ranked = sorted(day_picks, key=lambda p: p.get("edge_strength", 0), reverse=True)
        top_recommendations: List[Dict[str, Any]] = []
        for bet_type in ("spread", "moneyline", "total"):
            filtered = [p for p in ranked if p.get("bet_type") == bet_type]
            top_recommendations.extend(filtered[:3])
        top_recommendations = top_recommendations[: cfg.max_picks]

        bet_model_preds: List[Dict[str, Any]] = []
        bet_ready = _filter_rows_with_full_odds(features_df)
        if bet_ready.empty:
            print("    Bet model skipped (missing odds columns).")
        else:
            bet_model_preds = _score_with_models(bet_ready, bet_feature_cols, cfg.bet_model_dir)

        if cfg.skip_publish or cfg.dry_run:
            print("    Publishing skipped (dry run or skip flag).")
            continue

        publish_predictions_to_firestore(
            date_str=date_str,
            game_level_preds=game_preds,
            top_picks=top_recommendations,
            credentials_path=cfg.firebase_creds,
            max_picks=cfg.max_picks,
            bet_model_preds=bet_model_preds,
        )
        print(f"    Published {len(game_preds)} games / {len(top_recommendations)} picks.")

    print("\n[5/5] Pipeline complete.")
    if cfg.dry_run:
        print("Dry-run mode: Firestore writes were skipped.")


if __name__ == "__main__":
    run_prediction_pipeline()
CENTRAL_TZ = ZoneInfo("America/Chicago")
