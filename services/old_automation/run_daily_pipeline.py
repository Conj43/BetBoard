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
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Sequence, Dict, Any

import json
import math
import os
import pandas as pd

import build_features
import ingest_raw
import make_preds
from config import (
    FIREBASE_CREDENTIALS_PATH,
    MAX_PICKS_TO_PUBLISH,
    MODEL_DIR,
    BET_MODEL_DIR,
    PROCESSED_FEATURES_PREFIX,
    FEATURE_COLS_ORDER,
)
from firestore_publisher import publish_predictions_to_firestore


FeatureColumnsSource = Sequence[str] | str | None


def _require_firebase_storage() -> None:
    """
    Ensure Firebase Admin SDK with storage support is available before attempting
    remote downloads.
    """
    if getattr(make_preds, "firebase_admin", None) is None:
        raise RuntimeError(
            "firebase_admin is not installed. Install the Firebase Admin SDK to access models in Firebase Storage."
        )
    if getattr(make_preds, "storage", None) is None:
        raise RuntimeError(
            "firebase_admin.storage is unavailable. Install firebase-admin with storage extras (google-cloud-storage)."
        )


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


def _load_feature_columns(model_dir, explicit: Sequence[str] | None = None) -> List[str]:
    if explicit:
        return list(explicit)

    _require_firebase_storage()

    feature_names = make_preds.get_feature_names(str(model_dir))
    if feature_names:
        return feature_names

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


def _download_features_df(date_str: str) -> pd.DataFrame:
    _require_firebase_storage()
    remote_path = f"{PROCESSED_FEATURES_PREFIX}/{date_str}/features.csv"
    try:
        return build_features._download_csv(remote_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Processed features not found in Firebase at {remote_path}. "
            "Run build_features or verify uploads."
        ) from exc


def _score_with_models(features_df, feature_cols, model_dir):
    """Score games, skipping any with insufficient data."""
    
    # Check which games have all required features
    valid_mask = features_df[feature_cols].notna().all(axis=1)
    invalid_games = features_df[~valid_mask]
    
    if not invalid_games.empty:
        print(f"[WARN] Skipping {len(invalid_games)} games with insufficient data:")
        for _, game in invalid_games.iterrows():
            print(f"  - {game.get('game_id', 'unknown')}")
    
    # Only score games with complete data
    features_df = features_df[valid_mask]
    
    if features_df.empty:
        print("[WARN] No games have sufficient data for predictions")
        return pd.DataFrame()

    for col in feature_cols:
        if col not in features_df.columns:
            raise ValueError(f"Missing expected feature column '{col}' in features dataframe.")

    spread_model, total_model, winprob_model = make_preds.load_models(model_dir)
    grouped = make_preds.split_home_away(features_df)

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
    """
    Return only the rows that contain spread, total, and moneyline data.
    """
    required_cols = ["bet_spread", "bet_total", "moneyline_a", "moneyline_b"]
    if not all(col in features_df.columns for col in required_cols):
        return pd.DataFrame(columns=features_df.columns)
    mask = features_df[required_cols].notna().all(axis=1)
    return features_df[mask]


def _label_missing_odds(game_preds: List[Dict[str, Any]]) -> None:
    """Replace missing odds fields with display-friendly placeholder."""
    for pred in game_preds:
        for key in ("bet_spread_home", "bet_total", "moneyline_home", "moneyline_away"):
            value = pred.get(key)
            if value is None or value == "" or (isinstance(value, float) and math.isnan(value)):
                pred[key] = "No Odds"


def _choose_bets_for_game(game_pred: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Simple heuristic to generate potential bets for a single game.
    Looks at spread, total, and moneyline edges relative to model output.
    """
    picks: List[Dict[str, Any]] = []
    game_id = game_pred.get("game_id")
    home_team = game_pred.get("home_team")
    away_team = game_pred.get("away_team")

    def _as_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    bookmakers = game_pred.get("bookmakers") or {}
    preferred_books = ("betmgm", "fanduel", "draftkings")

    def _best_spread():
        best = None  # (edge, line, book, selection, price)
        for book_key, payload in bookmakers.items():
            key_lower = str(book_key).lower()
            if not any(pref in key_lower for pref in preferred_books):
                continue
            spread = payload.get("spread")
            if not isinstance(spread, dict):
                continue
            home_market = spread.get("home") or {}
            away_market = spread.get("away") or {}
            home_line = home_market.get("line")
            away_line = away_market.get("line")
            home_price = home_market.get("price")
            away_price = away_market.get("price")
            model_spread = _as_float(game_pred.get("model_spread_home"))
            if model_spread is None:
                continue
            if home_line is not None:
                edge = model_spread - (-home_line)
                if best is None or abs(edge) > abs(best[0]):
                    best = (edge, -home_line, book_key, home_team if edge >= 0 else away_team, home_price)
            if away_line is not None:
                edge = model_spread - away_line
                if best is None or abs(edge) > abs(best[0]):
                    best = (edge, away_line, book_key, home_team if edge >= 0 else away_team, away_price)
        return best

    best_spread = _best_spread()
    if best_spread:
        edge, line_spread, book_key, selection, price = best_spread
        picks.append({
            "game_id": game_id,
            "bet_type": "spread",
            "selection": selection,
            "model_projection": _as_float(game_pred.get("model_spread_home")),
            "book_line": line_spread,
            "bookmaker": book_key,
            "edge_strength": abs(edge),
            "odds": price,
            "odds_to_prob": make_preds.implied_prob_from_moneyline(price),
        })
    else:
        model_spread = _as_float(game_pred.get("model_spread_home"))
        raw_line_spread = _as_float(game_pred.get("bet_spread_home"))
        line_spread = -raw_line_spread if raw_line_spread is not None else None
        if model_spread is not None and line_spread is not None:
            edge = model_spread - line_spread
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
        best = None  # (edge, line, book, selection, price)
        for book_key, payload in bookmakers.items():
            key_lower = str(book_key).lower()
            if not any(pref in key_lower for pref in preferred_books):
                continue
            total = payload.get("total")
            if not isinstance(total, dict):
                continue
            over_market = total.get("over") or {}
            under_market = total.get("under") or {}
            over_line = over_market.get("line")
            under_line = under_market.get("line")
            over_price = over_market.get("price")
            under_price = under_market.get("price")
            model_total = _as_float(game_pred.get("model_total"))
            if model_total is None:
                continue
            if over_line is not None:
                edge = model_total - over_line
                if best is None or abs(edge) > abs(best[0]):
                    best = (edge, over_line, book_key, "Over" if edge >= 0 else "Under", over_price)
            if under_line is not None:
                edge = model_total - under_line
                if best is None or abs(edge) > abs(best[0]):
                    best = (edge, under_line, book_key, "Over" if edge >= 0 else "Under", under_price)
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
    bookmakers = game_pred.get("bookmakers") or {}
    preferred_books = ("betmgm", "fanduel", "draftkings")
    if home_prob is not None and bookmakers:
        away_prob = 1.0 - home_prob
        best_home = None  # (edge, line, book)
        best_away = None

        for book_key, payload in bookmakers.items():
            key_lower = str(book_key).lower()
            if not any(pref in key_lower for pref in preferred_books):
                continue

            moneyline = payload.get("moneyline", {})
            if not isinstance(moneyline, dict):
                print(f"[DEBUG][moneyline] malformed moneyline for {book_key} on {game_id}: {moneyline}")
                continue

            home_line = moneyline.get("home")
            if home_line is not None:
                home_implied = make_preds.implied_prob_from_moneyline(home_line)
                if home_implied is not None:
                    edge = home_prob - home_implied
                    if best_home is None or edge > best_home[0]:
                        best_home = (edge, home_line, book_key)
                        # print(f"[DEBUG][moneyline] {game_id} home line {home_line} from {book_key} edge {edge:.4f}")
                # else:
                #     print(f"[DEBUG][moneyline] could not compute implied prob for home line {home_line} ({book_key}) on {game_id}")
            # else:
            #     print(f"[DEBUG][moneyline] book {book_key} missing home line for {game_id}")

            away_line = moneyline.get("away")
            if away_line is not None:
                away_implied = make_preds.implied_prob_from_moneyline(away_line)
                if away_implied is not None:
                    edge = away_prob - away_implied
                    if best_away is None or edge > best_away[0]:
                        best_away = (edge, away_line, book_key)
                        # print(f"[DEBUG][moneyline] {game_id} away line {away_line} from {book_key} edge {edge:.4f}")
                # else:
                #     print(f"[DEBUG][moneyline] could not compute implied prob for away line {away_line} ({book_key}) on {game_id}")
            # else:
            #     print(f"[DEBUG][moneyline] book {book_key} missing away line for {game_id}")

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
    print(f"Model dir: {cfg.model_dir}")

    explicit_cols = _resolve_explicit_feature_columns(cfg.feature_columns_source)
    feature_cols = _load_feature_columns(cfg.model_dir, explicit_cols)
    print(f"Using {len(feature_cols)} feature columns (no-bet model).")

    bet_feature_cols = _load_feature_columns(BET_MODEL_DIR, explicit_cols)
    print(f"Using {len(bet_feature_cols)} feature columns (bet model).")

    built_features: Dict[str, pd.DataFrame] = {}

    if not cfg.skip_ingest:
        print("\n[Step 1] Ingesting raw data...")
        ingest_raw.ingest_raw_for_range(date_strings[0], date_strings[-1])
    else:
        print("\n[Step 1] Skipped raw ingest.")

    if not cfg.skip_features:
        print("\n[Step 2] Building features and uploading to Firebase...")
        for date_str in date_strings:
            print(f"  - {date_str}")
            built_features[date_str] = build_features.build_features_for_date(date_str)
    else:
        print("\n[Step 2] Skipped feature build.")

    print("\n[Step 3] Scoring games...")
    all_results = []
    all_picks = []

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
        if game_preds is None:
            print(f"    No games/features found for {date_str}.")
            continue

        day_picks = []
        for game_pred in game_preds:
            day_picks.extend(_choose_bets_for_game(game_pred))
        _label_missing_odds(game_preds)
        ranked_day_picks = sorted(day_picks, key=lambda p: p.get("edge_strength", 0), reverse=True)
        top_recommendations: List[Dict[str, Any]] = []
        bet_types = ("spread", "moneyline", "total")
        for bet_type in bet_types:
            type_specific = [p for p in ranked_day_picks if p.get("bet_type") == bet_type]
            top_recommendations.extend(type_specific[:3])
        top_recommendations = top_recommendations[:9]

        all_results.extend(game_preds)
        all_picks.extend(top_recommendations)

        bet_model_preds: List[Dict[str, Any]] = []
        bet_features_subset = _filter_rows_with_full_odds(features_df)
        if bet_features_subset.empty:
            print("    Skipping bet model scoring due to incomplete odds data.")
        else:
            bet_model_preds = _score_with_models(bet_features_subset, bet_feature_cols, BET_MODEL_DIR)

        if not cfg.skip_publish and not cfg.dry_run:
            publish_predictions_to_firestore(
                date_str=date_str,
                game_level_preds=game_preds,
                top_picks=top_recommendations,
                credentials_path=cfg.firebase_creds,
                max_picks=cfg.max_picks,
                bet_model_preds=bet_model_preds,
            )
            # print(f"    Published {len(game_preds)} games / {len(ranked_day_picks)} picks to Firestore.")
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
