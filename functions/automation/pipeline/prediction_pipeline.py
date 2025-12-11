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

    feature_names: Sequence[str] | None = None
    if hasattr(make_preds, "get_feature_names"):
        try:
            _require_firebase_storage()
            feature_names = make_preds.get_feature_names(str(model_dir))
        except Exception:
            feature_names = None

    if feature_names:
        return list(feature_names)

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
    
def _meets_bet_criteria(pick: Dict[str, Any]) -> bool:
    """Filter picks based on edge and odds requirements."""
    bet_type = pick.get("bet_type")
    edge = pick.get("edge_strength", 0)

    try:
        edge_val = float(edge)
    except (TypeError, ValueError):
        return False

    if bet_type in ("spread", "total"):
        # Require a meaningful edge: absolute edge between 5 and 10 points
        return 5.0 <= abs(edge_val) <= 10.0

    if bet_type == "moneyline":
        # Require between 1% and 5% edge on implied win probability.
        return 0.01 <= edge_val <= 0.05

    return False


def _build_top_recommendations(
    day_picks: List[Dict[str, Any]],
    max_picks: int,
) -> List[Dict[str, Any]]:
    """
    Build top recommendations with:
      - global ranking by edge_strength
      - up to 3 per bet_type ("spread", "moneyline", "total")
      - at most ONE pick per game_id overall
      - filtered by min/max edge and odds criteria
    """
    if not day_picks:
        return []

    # Filter picks that meet criteria
    valid_picks = [p for p in day_picks if _meets_bet_criteria(p)]
    
    if not valid_picks:
        return []

    # Global ranking by edge strength (descending)
    ranked = sorted(valid_picks, key=lambda p: p.get("edge_strength", 0.0), reverse=True)

    top_recommendations: List[Dict[str, Any]] = []
    used_game_ids: set[str] = set()
    type_counts: Dict[str, int] = {"spread": 0, "moneyline": 0, "total": 0}
    MAX_PER_TYPE = 3

    for bet_type in ("spread", "moneyline", "total"):
        for pick in ranked:
            if pick.get("bet_type") != bet_type:
                continue

            game_id = pick.get("game_id")
            if not game_id:
                continue

            # Enforce at most one pick per game
            if game_id in used_game_ids:
                continue

            # Enforce per-type cap
            if type_counts[bet_type] >= MAX_PER_TYPE:
                continue

            top_recommendations.append(pick)
            used_game_ids.add(game_id)
            type_counts[bet_type] += 1

            if len(top_recommendations) >= max_picks:
                break
        if len(top_recommendations) >= max_picks:
            break

    return top_recommendations


def _choose_bets_for_game(game_pred: Mapping[str, Any]) -> List[Dict[str, Any]]:
    game_id = game_pred.get("game_id")
    home_team = game_pred.get("home_team") or game_pred.get("Team")
    away_team = game_pred.get("away_team") or game_pred.get("Opp")

    picks: List[Dict[str, Any]] = []
    bookmakers = game_pred.get("bookmakers") or {}
    preferred_books = ("betmgm", "fanduel", "draftkings")

    model_spread = _as_float(game_pred.get("model_spread_home"))
    line_spread = _as_float(game_pred.get("bet_spread_home"))

    def _best_spread():
        if model_spread is None or not bookmakers:
            return None
        best = None
        for book_key, payload in bookmakers.items():
            if not isinstance(book_key, str):
                continue
            if not any(pref in book_key.lower() for pref in preferred_books):
                continue
            if not isinstance(payload, Mapping):
                continue
            spread_market = payload.get("spread")
            if not isinstance(spread_market, Mapping):
                continue
            home_market = spread_market.get("home") or {}
            away_market = spread_market.get("away") or {}
            home_line_val = _as_float(home_market.get("line"))
            if home_line_val is None:
                away_line_val = _as_float(away_market.get("line"))
                if away_line_val is not None:
                    home_line_val = -away_line_val
            if home_line_val is None:
                continue
            
            # Spread edge calculation
            edge_val = model_spread + home_line_val
            selection = home_team if edge_val >= 0 else away_team
            odds = None
            if selection == home_team:
                odds = home_market.get("price")
            else:
                odds = away_market.get("price")
            
            # Build candidate with EV adjustment
            candidate = {
                "edge": edge_val,
                "line": home_line_val,
                "selection": selection,
                "book": book_key,
                "odds": odds,
                "odds_prob": None,
                "ev_adjusted": 0,
            }
            
            if odds is not None:
                odds_prob = make_preds.implied_prob_from_moneyline(odds)
                candidate["odds_prob"] = odds_prob
                if odds_prob is not None:
                    # EV-adjusted edge
                    ev_adjusted = abs(edge_val) * (1.0 - odds_prob)
                    candidate["ev_adjusted"] = ev_adjusted
            
            # Compare and update best (INSIDE THE LOOP)
            if best is None or candidate["ev_adjusted"] > best["ev_adjusted"]:
                best = candidate
        
        return best

    best_spread = _best_spread()
    if best_spread:
        picks.append({
            "game_id": game_id,
            "bet_type": "spread",
            "selection": best_spread["selection"],
            "model_projection": model_spread,
            "book_line": best_spread["line"],
            "bookmaker": best_spread["book"],
            "edge_strength": abs(best_spread["edge"]),
            "odds": best_spread["odds"],
            "odds_to_prob": best_spread["odds_prob"],
        })
    elif model_spread is not None and line_spread is not None:
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
        """Choose the best total bet (Over/Under) from preferred books.

        We define edge as:
        - Over:  model_total - line
        - Under: line - model_total

        We only consider candidates with positive edge (model likes that side),
        and pick the one with the largest EV-adjusted edge.
        """
        model_total = _as_float(game_pred.get("model_total"))
        if model_total is None or not bookmakers:
            return None

        best: Optional[Dict[str, Any]] = None

        for book_key, payload in bookmakers.items():
            if not any(pref in str(book_key).lower() for pref in preferred_books):
                continue

            total = payload.get("total")
            if not isinstance(total, dict):
                continue

            over = total.get("over") or {}
            under = total.get("under") or {}

            over_line = _as_float(over.get("line"))
            under_line = _as_float(under.get("line"))
            over_price = over.get("price")
            under_price = under.get("price")

            # Over candidate: edge = model_total - line
            if over_line is not None and over_price is not None:
                edge_over = model_total - over_line
                if edge_over > 0:
                    odds_prob = make_preds.implied_prob_from_moneyline(over_price)
                    ev_adjusted = 0
                    if odds_prob is not None:
                        ev_adjusted = edge_over * (1.0 - odds_prob)
                    
                    cand = {
                        "selection": "Over",
                        "edge": edge_over,
                        "line": over_line,
                        "book": book_key,
                        "price": over_price,
                        "ev_adjusted": ev_adjusted,
                    }
                    if best is None or cand["ev_adjusted"] > best.get("ev_adjusted", 0):
                        best = cand

            # Under candidate: edge = line - model_total
            if under_line is not None and under_price is not None:
                edge_under = under_line - model_total
                if edge_under > 0:
                    odds_prob = make_preds.implied_prob_from_moneyline(under_price)
                    ev_adjusted = 0
                    if odds_prob is not None:
                        ev_adjusted = edge_under * (1.0 - odds_prob)
                    
                    cand = {
                        "selection": "Under",
                        "edge": edge_under,
                        "line": under_line,
                        "book": book_key,
                        "price": under_price,
                        "ev_adjusted": ev_adjusted,
                    }
                    if best is None or cand["ev_adjusted"] > best.get("ev_adjusted", 0):
                        best = cand

        return best

    best_total = _best_total()
    model_total = _as_float(game_pred.get("model_total"))
    if best_total and model_total is not None:
        picks.append({
            "game_id": game_id,
            "bet_type": "total",
            "selection": best_total["selection"],          # "Over" / "Under"
            "model_projection": model_total,               # e.g. 157.3
            "book_line": best_total["line"],               # e.g. 180.5
            "bookmaker": best_total["book"],
            "edge_strength": best_total["edge"],
            "odds": best_total["price"],
            "odds_to_prob": make_preds.implied_prob_from_moneyline(
                best_total["price"]
            ),
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
    try:
        feature_cols = _load_feature_columns(cfg.model_dir, explicit_cols)
        bet_feature_cols = _load_feature_columns(cfg.bet_model_dir, explicit_cols)
    except RuntimeError as exc:
        print(f"[ERROR] Unable to resolve feature columns: {exc}")
        return

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
        top_recommendations = _build_top_recommendations(day_picks, cfg.max_picks)

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
