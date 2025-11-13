#!/usr/bin/env python3
"""
Evaluate Firestore predictions against finalized game results.

For each date (and across the aggregate date range) this script:
    * Compares moneyline, spread, and total projections against actual scores.
    * Computes MODEL PERFORMANCE metrics (accuracy, MAE, logloss) for all predictions.
    * Simulates BETTING PERFORMANCE for all predictions based on edge detection:
          MONEYLINE: Bets when model probability exceeds implied odds probability (positive EV)
          SPREAD: Bets the side that model projects will cover the spread
          TOTAL: Bets over/under based on model's projected total vs line
    * Uses two staking strategies:
          - Flat $25 wagers from a $1,000 bankroll
          - Quarter-Kelly staking (moneyline only, requires probabilities)
    * Separately evaluates recommended picks with their specific parameters
    * Stores individual pick outcomes under `recommended_picks` subcollection
    * Writes per-day documents plus an overall summary into a Firestore
      collection (default: prediction_evaluation)

BETTING LOGIC:
    * Moneyline: Convert odds to implied probability, bet if model prob > implied prob
                Example: Model says 60%, odds imply 55% → BET (5% edge)
    * Spread: Bet side that model's predicted margin says will cover
                Example: Model predicts home +8, line is 5.5 → BET HOME
    * Total: Bet over/under based on model's predicted total vs line
                Example: Model predicts 145, line is 140.5 → BET OVER

IMPORTANT CONVENTIONS:
    * Spread lines: Positive line = home team favored (needs to win by more than line)
                   Example: line=5.5 means home needs to win by 6+ to cover
    * Margin: home_score - away_score (positive when home wins)

Usage examples:
    python services/automation/evaluate_predictions.py --start-date 2025-11-01 --end-date 2025-11-11
    python services/automation/evaluate_predictions.py --date 2025-11-11 --dry-run
"""
from __future__ import annotations

import argparse
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from config import FIRESTORE_PREDICTIONS_COLLECTION
from firestore_publisher import _ensure_firestore
from team_keys import canonicalize_team_key
from utils import load_alias_map


DEFAULT_RESULT_DOC = "sports_reference"
DEFAULT_EVAL_COLLECTION = "prediction_evaluation"
RECOMMENDED_SUBCOLLECTION = "recommended_picks"
INITIAL_BANKROLL = 1_000.0
FLAT_STAKE = 25.0
MIN_KELLY_STAKE = 0.01  # Minimum stake for Kelly betting ($0.01)
SPREAD_TOTAL_DEFAULT_ODDS = -110  # Assume -110 vig when explicit odds missing


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare predictions vs results and log evaluation metrics.")
    parser.add_argument("--date", help="Single YYYY-MM-DD date to evaluate.", default=None)
    parser.add_argument("--start-date", help="Start date (inclusive). Overrides --date when provided.", default=None)
    parser.add_argument("--end-date", help="End date (inclusive). Required when --start-date is set.", default=None)
    parser.add_argument(
        "--result-source",
        help="game_results/<doc_id> used as truth set.",
        default=DEFAULT_RESULT_DOC,
    )
    parser.add_argument(
        "--collection",
        help="Firestore collection for evaluation documents.",
        default=DEFAULT_EVAL_COLLECTION,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute metrics but do not write back to Firestore.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args(argv)


def _resolve_dates(args: argparse.Namespace) -> List[str]:
    if args.start_date and args.end_date:
        start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        if end < start:
            raise ValueError("--end-date must be on/after --start-date")
        cur = start
        dates: List[str] = []
        while cur <= end:
            dates.append(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)
        return dates

    if args.start_date or args.end_date:
        raise ValueError("Provide both --start-date and --end-date, or neither.")

    if args.date:
        datetime.strptime(args.date, "%Y-%m-%d")  # validate
        return [args.date]

    # Default: evaluate yesterday (UTC)
    default = (datetime.utcnow().date() - timedelta(days=1)).strftime("%Y-%m-%d")
    return [default]


# --------------------------------------------------------------------------- #
# Helpers for normalization / matching
# --------------------------------------------------------------------------- #

_ALIAS_MAP: Optional[Dict[str, str]] = None


def _normalize_team(value: Optional[str]) -> str:
    if not isinstance(value, str):
        return ""

    global _ALIAS_MAP
    if _ALIAS_MAP is None:
        try:
            _ALIAS_MAP = load_alias_map()
        except Exception:
            _ALIAS_MAP = {}

    slug = "".join(ch for ch in value.lower() if ch.isalnum())
    if not slug:
        return ""

    mapped = _ALIAS_MAP.get(slug)
    if mapped:
        return mapped

    return canonicalize_team_key(value)


# --------------------------------------------------------------------------- #
# Metrics / bankroll simulation helpers
# --------------------------------------------------------------------------- #


def _american_to_decimal(odds: Optional[float]) -> Optional[float]:
    """Convert American odds to decimal odds. Returns None for invalid inputs."""
    if odds is None or odds == 0:
        return None
    if odds > 0:
        return 1.0 + (odds / 100.0)
    return 1.0 + (100.0 / abs(odds))


def _validate_odds(odds: Optional[float]) -> bool:
    """Check if odds are in a reasonable range."""
    if odds is None:
        return False
    # Reasonable range: -10000 to +10000
    if abs(odds) > 10000 or abs(odds) < 100:
        return False
    return True


def _simulate_flat_bets(
    bets: Iterable[Dict[str, Any]],
    initial_bankroll: float = INITIAL_BANKROLL,
    stake_size: float = FLAT_STAKE,
) -> Optional[Dict[str, Any]]:
    """Simulate flat betting with fixed stake size."""
    bankroll = initial_bankroll
    wins = losses = pushes = 0
    total_wagered = 0.0

    for bet in bets:
        result = bet.get("result")
        odds = bet.get("odds")
        
        # Validate odds
        if not _validate_odds(odds):
            logging.debug("Skipping bet with invalid odds: %s", odds)
            continue
            
        decimal = _american_to_decimal(odds)
        if decimal is None or bankroll <= 0 or stake_size <= 0:
            continue
            
        stake = min(stake_size, bankroll)
        bankroll -= stake
        
        if result == "push":
            bankroll += stake
            pushes += 1
            continue

        total_wagered += stake
        if result == "win":
            bankroll += stake * decimal
            wins += 1
        elif result == "loss":
            losses += 1
        else:
            # Invalid result, return stake
            bankroll += stake

    bets_placed = wins + losses + pushes
    if bets_placed == 0 and total_wagered == 0:
        return None

    roi = (bankroll - initial_bankroll) / initial_bankroll
    return {
        "final_bankroll": round(bankroll, 2),
        "roi": round(roi, 4),
        "bets": bets_placed,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "total_wagered": round(total_wagered, 2),
    }


def _simulate_quarter_kelly(
    bets: Iterable[Dict[str, Any]],
    initial_bankroll: float = INITIAL_BANKROLL,
    fraction: float = 0.25,
) -> Optional[Dict[str, Any]]:
    """Simulate quarter-Kelly staking (requires probability estimates)."""
    bankroll = initial_bankroll
    wins = losses = pushes = 0
    total_wagered = 0.0

    for bet in bets:
        prob = bet.get("prob")
        odds = bet.get("odds")
        result = bet.get("result")
        
        # Validate inputs
        if not _validate_odds(odds) or prob is None:
            continue
            
        decimal = _american_to_decimal(odds)
        if decimal is None:
            continue
            
        # Clamp probability to valid range
        prob = max(min(prob, 0.999999), 0.000001)
        
        # Calculate Kelly criterion
        b = decimal - 1.0
        if b <= 0:
            continue
            
        kelly = (b * prob - (1 - prob)) / b
        if kelly <= 0:
            continue
            
        stake = bankroll * kelly * fraction
        
        # Round stake to cents and check minimum threshold
        stake = round(stake, 2)
        if stake < MIN_KELLY_STAKE or stake <= 0 or bankroll <= 0:
            continue
            
        stake = min(stake, bankroll)
        bankroll -= stake

        if result == "push":
            bankroll += stake
            pushes += 1
            continue

        total_wagered += stake
        if result == "win":
            bankroll += stake * decimal
            wins += 1
        elif result == "loss":
            losses += 1
        else:
            # Invalid result, return stake
            bankroll += stake

    bets_placed = wins + losses + pushes
    if bets_placed == 0 and total_wagered == 0:
        return None

    roi = (bankroll - initial_bankroll) / initial_bankroll
    return {
        "final_bankroll": round(bankroll, 2),
        "roi": round(roi, 4),
        "bets": bets_placed,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "total_wagered": round(total_wagered, 2),
    }


# --------------------------------------------------------------------------- #
# Evaluation logic
# --------------------------------------------------------------------------- #


@dataclass
class MarketStats:
    """Track statistics for a betting market."""
    count: int = 0
    correct: int = 0
    pushes: int = 0
    mae_sum: float = 0.0
    logloss_sum: float = 0.0
    bets: List[Dict[str, Any]] = field(default_factory=list)
    # Moneyline-specific: track winner prediction separately from betting
    winner_correct: int = 0


def _init_stats() -> Dict[str, Any]:
    """Initialize statistics structure for all markets."""
    return {
        "games": 0,
        "moneyline": MarketStats(),
        "spread": MarketStats(),
        "total": MarketStats(),
    }


def _init_recommended_stats() -> Dict[str, MarketStats]:
    """Initialize statistics for recommended picks."""
    return {
        "moneyline": MarketStats(),
        "spread": MarketStats(),
        "total": MarketStats(),
    }


def _fetch_result_doc(game_ref, preferred_doc: str) -> Optional[Dict[str, Any]]:
    """Fetch game results document from Firestore."""
    results_col = game_ref.collection("game_results")
    if preferred_doc:
        snap = results_col.document(preferred_doc).get()
        if snap.exists:
            return snap.to_dict()

    first = next(results_col.limit(1).stream(), None)
    if first:
        return first.to_dict()
    return None


def _build_actual(result_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract actual game outcome from results document."""
    try:
        home_score = int(result_doc.get("home_score"))
        away_score = int(result_doc.get("away_score"))
    except (TypeError, ValueError):
        return None
        
    margin = home_score - away_score
    total = home_score + away_score
    
    # home_win: 1 if home won, 0 if away won, None if tie
    if margin > 0:
        home_win = 1
    elif margin < 0:
        home_win = 0
    else:
        home_win = None
        
    return {
        "home_score": home_score,
        "away_score": away_score,
        "margin": margin,
        "total": total,
        "home_win": home_win,
    }


def _logloss(prob: float, outcome: int) -> float:
    """Calculate log loss for a single prediction."""
    prob = max(min(prob, 0.999999), 0.000001)
    return -(outcome * math.log(prob) + (1 - outcome) * math.log(1 - prob))


def _resolve_pick(pick_name: Optional[str], home_team: str, away_team: str) -> Optional[str]:
    """
    Resolve a pick name to either 'home' or 'away'.
    
    Returns:
        'home', 'away', or None if pick cannot be resolved
    """
    if not pick_name:
        return None
        
    pick_norm = _normalize_team(pick_name)
    home_norm = _normalize_team(home_team)
    away_norm = _normalize_team(away_team)
    
    if pick_norm and home_norm and pick_norm == home_norm:
        return "home"
    if pick_norm and away_norm and pick_norm == away_norm:
        return "away"
        
    # Handle generic labels
    pick_lower = pick_name.strip().lower()
    if pick_lower in {"home", "team_a", "a"}:
        return "home"
    if pick_lower in {"away", "team_b", "b"}:
        return "away"
        
    return None


def _append_bet(bucket: MarketStats, odds: Optional[float], result: str, prob: Optional[float] = None):
    """Add a bet to the statistics bucket."""
    bet = {
        "odds": odds,
        "result": result,
    }
    if prob is not None:
        bet["prob"] = prob
    bucket.bets.append(bet)


def _flat_profit(result: str, odds: Optional[float], default_odds: Optional[float] = None) -> Optional[float]:
    """Calculate profit/loss for a flat bet."""
    if result not in {"win", "loss", "push"}:
        return None
        
    price = odds if odds is not None else default_odds
    decimal = _american_to_decimal(price) if price is not None else None
    if decimal is None:
        return None
        
    if result == "win":
        return round(FLAT_STAKE * (decimal - 1.0), 2)
    if result == "loss":
        return round(-FLAT_STAKE, 2)
    return 0.0


# --------------------------------------------------------------------------- #
# Model Performance Evaluation (all predictions)
# --------------------------------------------------------------------------- #


def _odds_to_implied_prob(odds: Optional[float]) -> Optional[float]:
    """Convert American odds to implied probability."""
    if not _validate_odds(odds):
        return None
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def _evaluate_moneyline_model(game_data: Dict[str, Any], actual: Dict[str, Any], stats: MarketStats):
    """
    Evaluate moneyline MODEL PERFORMANCE and simulate betting based on edge.
    Bets when model probability exceeds implied probability from odds (positive EV).
    """
    moneyline = game_data.get("moneyline") or {}
    prob_home = moneyline.get("p_win_home")
    odds_home = moneyline.get("odds_home")
    odds_away = moneyline.get("odds_away")

    # Need both prediction and actual outcome (no ties allowed in moneyline)
    if prob_home is None or actual["home_win"] is None:
        return

    stats.count += 1
    home_win = actual["home_win"]
    prob_away = 1 - prob_home
    
    # Model performance metrics
    stats.mae_sum += abs(prob_home - home_win)
    stats.logloss_sum += _logloss(prob_home, home_win)

    # Winner prediction accuracy: did model predict correct winner?
    predicted_winner = 1 if prob_home >= 0.5 else 0
    if predicted_winner == home_win:
        stats.winner_correct += 1

    # Betting simulation: bet if we have edge over implied odds
    implied_home = _odds_to_implied_prob(odds_home)
    implied_away = _odds_to_implied_prob(odds_away)
    
    # Determine if we should bet and which side
    bet_side = None
    bet_odds = None
    bet_prob = None
    
    if implied_home is not None and prob_home > implied_home:
        # Edge on home side
        bet_side = "home"
        bet_odds = odds_home
        bet_prob = prob_home
    elif implied_away is not None and prob_away > implied_away:
        # Edge on away side
        bet_side = "away"
        bet_odds = odds_away
        bet_prob = prob_away
    
    # If we have a bet, determine result and track betting accuracy
    if bet_side and bet_odds:
        if home_win is None:
            result = "push"
        elif (bet_side == "home" and home_win == 1) or (bet_side == "away" and home_win == 0):
            result = "win"
            stats.correct += 1  # Track betting accuracy
        else:
            result = "loss"
        
        _append_bet(stats, bet_odds, result, bet_prob)


def _evaluate_spread_model(game_data: Dict[str, Any], actual: Dict[str, Any], stats: MarketStats):
    """
    Evaluate spread MODEL PERFORMANCE and simulate betting based on predictions.
    Bets the side that the model projects will cover.
    """
    spread = game_data.get("spread") or {}
    predicted_margin = spread.get("predicted_margin")
    line = spread.get("line")
    pick_name = spread.get("pick")

    if predicted_margin is None or line is None:
        return

    stats.count += 1
    
    # MAE on margin prediction
    stats.mae_sum += abs(predicted_margin - actual["margin"])

    # Determine which side model predicts will cover
    # predicted_margin is home's projected margin
    # line is how much home is favored by (positive = home favored)
    predicted_cover = predicted_margin - line
    
    # Calculate actual cover
    actual_cover = actual["margin"] - line
    
    # Determine betting side and result
    if predicted_cover == 0:
        # Model says it's a push, don't bet
        pass
    else:
        bet_side = "home" if predicted_cover > 0 else "away"
        bet_odds = spread.get("odds_home") if bet_side == "home" else spread.get("odds_away")
        
        # If no specific odds, use default
        if not _validate_odds(bet_odds):
            bet_odds = SPREAD_TOTAL_DEFAULT_ODDS
        
        # Determine result
        if actual_cover == 0:
            result = "push"
            stats.pushes += 1
        else:
            home_covered = actual_cover > 0
            predicted_home_covers = predicted_cover > 0
            
            if home_covered == predicted_home_covers:
                stats.correct += 1
                result = "win"
            else:
                result = "loss"
        
        _append_bet(stats, bet_odds, result)


def _evaluate_total_model(game_data: Dict[str, Any], actual: Dict[str, Any], stats: MarketStats):
    """
    Evaluate total MODEL PERFORMANCE and simulate betting based on predictions.
    Bets over/under based on model's projected total vs line.
    """
    total = game_data.get("total") or {}
    predicted_total = total.get("predicted_total")
    line = total.get("line")
    pick = (total.get("pick") or "").strip().upper()

    if predicted_total is None or line is None:
        return

    stats.count += 1
    
    # MAE on total prediction
    stats.mae_sum += abs(predicted_total - actual["total"])

    # Determine betting side based on model prediction
    predicted_diff = predicted_total - line
    
    if predicted_diff == 0:
        # Model says it's exactly the line, don't bet
        pass
    else:
        bet_pick = "OVER" if predicted_diff > 0 else "UNDER"
        bet_odds = total.get("odds_over") if bet_pick == "OVER" else total.get("odds_under")
        
        # If no specific odds, use default
        if not _validate_odds(bet_odds):
            bet_odds = SPREAD_TOTAL_DEFAULT_ODDS
        
        # Calculate actual vs line
        actual_diff = actual["total"] - line
        
        # Determine result
        if actual_diff == 0:
            result = "push"
            stats.pushes += 1
        else:
            actual_pick = "OVER" if actual_diff > 0 else "UNDER"
            
            if bet_pick == actual_pick:
                stats.correct += 1
                result = "win"
            else:
                result = "loss"
        
        _append_bet(stats, bet_odds, result)


# --------------------------------------------------------------------------- #
# Recommended Picks Evaluation (betting simulation)
# --------------------------------------------------------------------------- #


def _grade_moneyline_pick(
    pick: Dict[str, Any],
    game_data: Dict[str, Any],
    actual: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Grade a moneyline pick and return detailed results."""
    selection = pick.get("selection")
    side = _resolve_pick(selection, game_data.get("home_team"), game_data.get("away_team"))
    
    if side not in {"home", "away"} or actual["home_win"] is None:
        logging.warning("Could not resolve moneyline pick: %s", selection)
        return None

    moneyline = game_data.get("moneyline") or {}
    
    # Get odds from pick, fall back to game data
    odds = pick.get("odds")
    if odds is None:
        odds = moneyline.get("odds_home" if side == "home" else "odds_away")
    
    if not _validate_odds(odds):
        logging.warning("Invalid odds for moneyline pick: %s", odds)
        return None

    # Get probability
    prob = pick.get("odds_to_prob")
    if prob is None:
        base_prob = moneyline.get("p_win_home")
        if base_prob is not None:
            prob = base_prob if side == "home" else 1 - base_prob

    # Determine result
    home_win = actual["home_win"]
    if home_win is None:
        result = "push"
    else:
        picked_winner = 1 if side == "home" else 0
        result = "win" if picked_winner == home_win else "loss"

    return {
        "bet_type": "moneyline",
        "selection": selection,
        "side": side,
        "odds": odds,
        "prob": prob,
        "result": result,
        "game_id": pick.get("game_id"),
        "bookmaker": pick.get("bookmaker"),
        "edge_strength": pick.get("edge_strength"),
        "model_projection": moneyline.get("p_win_home"),
        "home_score": actual["home_score"],
        "away_score": actual["away_score"],
        "actual_winner": None if home_win is None else ("home" if home_win == 1 else "away"),
    }


def _grade_spread_pick(
    pick: Dict[str, Any],
    game_data: Dict[str, Any],
    actual: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Grade a spread pick and return detailed results."""
    selection = pick.get("selection")
    side = _resolve_pick(selection, game_data.get("home_team"), game_data.get("away_team"))
    
    if side not in {"home", "away"}:
        logging.warning("Could not resolve spread pick: %s", selection)
        return None

    spread = game_data.get("spread") or {}
    
    # Get line from pick, fall back to game data
    line = pick.get("book_line")
    if line is None:
        line = spread.get("line")
    
    if line is None:
        logging.warning("No spread line available for pick")
        return None

    # Line convention: positive = home favored
    # Calculate actual cover: margin - line
    # If line = 5.5 (home favored by 5.5), home needs to win by 6+
    actual_cover = actual["margin"] - line
    
    # Determine result
    if actual_cover == 0:
        result = "push"
    else:
        home_covered = actual_cover > 0
        picked_home = (side == "home")
        result = "win" if home_covered == picked_home else "loss"

    odds = pick.get("odds")
    if not _validate_odds(odds):
        odds = SPREAD_TOTAL_DEFAULT_ODDS
        
    return {
        "bet_type": "spread",
        "selection": selection,
        "side": side,
        "line": line,
        "odds": odds,
        "result": result,
        "game_id": pick.get("game_id"),
        "bookmaker": pick.get("bookmaker"),
        "edge_strength": pick.get("edge_strength"),
        "model_projection": spread.get("predicted_margin"),
        "home_score": actual["home_score"],
        "away_score": actual["away_score"],
        "actual_margin": actual["margin"],
        "actual_cover": actual_cover,
    }


def _grade_total_pick(
    pick: Dict[str, Any],
    game_data: Dict[str, Any],
    actual: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Grade a total pick and return detailed results."""
    selection = (pick.get("selection") or "").strip().upper()
    
    if selection not in {"OVER", "UNDER"}:
        logging.warning("Invalid total pick selection: %s", selection)
        return None
        
    total = game_data.get("total") or {}
    
    # Get line from pick, fall back to game data
    line = pick.get("book_line")
    if line is None:
        line = total.get("line")
    
    if line is None:
        logging.warning("No total line available for pick")
        return None

    # Calculate actual vs line
    actual_diff = actual["total"] - line
    
    # Determine result
    if actual_diff == 0:
        result = "push"
    else:
        actual_pick = "OVER" if actual_diff > 0 else "UNDER"
        result = "win" if actual_pick == selection else "loss"

    odds = pick.get("odds")
    if not _validate_odds(odds):
        odds = SPREAD_TOTAL_DEFAULT_ODDS

    return {
        "bet_type": "total",
        "selection": selection,
        "line": line,
        "odds": odds,
        "result": result,
        "game_id": pick.get("game_id"),
        "bookmaker": pick.get("bookmaker"),
        "edge_strength": pick.get("edge_strength"),
        "model_projection": total.get("predicted_total"),
        "home_score": actual["home_score"],
        "away_score": actual["away_score"],
        "actual_total": actual["total"],
        "actual_diff": actual_diff,
    }


def _evaluate_recommended_picks(
    game_data: Dict[str, Any],
    actual: Dict[str, Any],
    stats: Dict[str, MarketStats],
) -> List[Dict[str, Any]]:
    """
    Evaluate recommended picks and compute statistics.
    This is where betting simulation happens.
    """
    picks = game_data.get("recommended") or []
    graded: List[Dict[str, Any]] = []
    
    if not picks:
        return graded

    for pick in picks:
        bet_type = pick.get("bet_type")
        
        # Grade the pick
        if bet_type == "moneyline":
            graded_pick = _grade_moneyline_pick(pick, game_data, actual)
        elif bet_type == "spread":
            graded_pick = _grade_spread_pick(pick, game_data, actual)
        elif bet_type == "total":
            graded_pick = _grade_total_pick(pick, game_data, actual)
        else:
            logging.warning("Unknown bet type: %s", bet_type)
            continue

        if not graded_pick:
            continue

        result = graded_pick["result"]
        market_stats = stats[bet_type]
        market_stats.count += 1
        
        # Track outcomes
        if result == "push":
            market_stats.pushes += 1
        elif result == "win":
            market_stats.correct += 1
        
        # For moneyline, also track winner prediction accuracy
        if bet_type == "moneyline" and actual["home_win"] is not None:
            side = graded_pick.get("side")
            predicted_winner = 1 if side == "home" else 0
            if predicted_winner == actual["home_win"]:
                market_stats.winner_correct += 1

        # Track MAE for spread/total picks
        if bet_type == "spread":
            projection = graded_pick.get("model_projection")
            if projection is not None:
                try:
                    market_stats.mae_sum += abs(float(projection) - actual["margin"])
                except (TypeError, ValueError):
                    pass
                    
        elif bet_type == "total":
            projection = graded_pick.get("model_projection")
            if projection is not None:
                try:
                    market_stats.mae_sum += abs(float(projection) - actual["total"])
                except (TypeError, ValueError):
                    pass

        # Track logloss for moneyline picks
        if bet_type == "moneyline":
            prob = graded_pick.get("prob")
            if prob is not None and actual["home_win"] is not None:
                # Convert to binary outcome based on pick side
                side = graded_pick["side"]
                actual_flag = 1 if (actual["home_win"] == 1 and side == "home") or (actual["home_win"] == 0 and side == "away") else 0
                market_stats.mae_sum += abs(prob - actual_flag)
                market_stats.logloss_sum += _logloss(prob, actual_flag)

        # Add bet to simulation
        odds = graded_pick.get("odds")
        prob = graded_pick.get("prob")
        _append_bet(market_stats, odds, result, prob)
        
        # Calculate flat profit
        graded_pick["flat_profit"] = _flat_profit(result, odds, SPREAD_TOTAL_DEFAULT_ODDS)
        
        graded.append(graded_pick)

    return graded


def _finalize_market_payload(
    stats: MarketStats,
    include_logloss: bool = False,
    include_kelly: bool = False,
    is_moneyline: bool = False,
) -> Dict[str, Any]:
    """Convert market statistics into output payload."""
    payload: Dict[str, Any] = {
        "count": stats.count,
        "pushes": stats.pushes,
    }
    
    # Model performance metrics
    if stats.count > 0:
        # For moneyline, show both winner prediction and betting accuracy
        if is_moneyline:
            payload["winner_accuracy"] = round(stats.winner_correct / stats.count, 4)
        
        # Betting accuracy (for moneyline this is accuracy of bets placed, for others it's coverage accuracy)
        non_push = stats.count - stats.pushes
        if non_push > 0 and not is_moneyline:
            payload["accuracy"] = round(stats.correct / non_push, 4)
        
        payload["mae"] = round(stats.mae_sum / stats.count, 4)
        if include_logloss and stats.logloss_sum > 0:
            payload["logloss"] = round(stats.logloss_sum / stats.count, 4)
    
    # Betting simulation
    if stats.bets:
        # Calculate betting accuracy (wins / total bets excluding pushes)
        bet_count = len(stats.bets)
        bet_wins = sum(1 for b in stats.bets if b.get("result") == "win")
        bet_pushes = sum(1 for b in stats.bets if b.get("result") == "push")
        bet_non_push = bet_count - bet_pushes
        
        if bet_non_push > 0:
            payload["betting_accuracy"] = round(bet_wins / bet_non_push, 4)
        
        flat_result = _simulate_flat_bets(stats.bets)
        if flat_result:
            payload["flat_betting"] = flat_result
            # Add simple profit calculation
            payload["total_profit"] = round(flat_result["final_bankroll"] - INITIAL_BANKROLL, 2)
        
        if include_kelly:
            kelly_result = _simulate_quarter_kelly(stats.bets)
            if kelly_result:
                payload["quarter_kelly"] = kelly_result
                
    return payload


def evaluate_date(
    date_str: str,
    db,
    result_source: str,
) -> Optional[Dict[str, Any]]:
    """Evaluate predictions for a single date."""
    games_ref = db.collection(FIRESTORE_PREDICTIONS_COLLECTION).document(date_str).collection("games")
    snapshots = list(games_ref.stream())
    
    if not snapshots:
        logging.info("No games found for %s", date_str)
        return None

    # Model performance stats (all predictions)
    model_stats = _init_stats()
    
    # Betting performance stats (recommended picks only)
    recommended_stats = _init_recommended_stats()
    graded_picks: List[Dict[str, Any]] = []

    for snap in snapshots:
        data = snap.to_dict() or {}
        result_doc = _fetch_result_doc(snap.reference, result_source)
        
        if not result_doc:
            logging.debug("No result document for game: %s", snap.id)
            continue
            
        actual = _build_actual(result_doc)
        if not actual:
            logging.debug("Could not parse results for game: %s", snap.id)
            continue

        model_stats["games"] += 1
        
        # Normalize team names
        data.setdefault("home_team", data.get("home_team") or data.get("team_A"))
        data.setdefault("away_team", data.get("away_team") or data.get("team_B"))

        # Evaluate model performance (all predictions)
        _evaluate_moneyline_model(data, actual, model_stats["moneyline"])
        _evaluate_spread_model(data, actual, model_stats["spread"])
        _evaluate_total_model(data, actual, model_stats["total"])
        
        # Evaluate recommended picks (betting simulation)
        graded_picks.extend(_evaluate_recommended_picks(data, actual, recommended_stats))

    if model_stats["games"] == 0:
        logging.info("No completed games with results for %s", date_str)
        return None

    generated_at = datetime.now(timezone.utc).isoformat()
    
    payload = {
        "date": date_str,
        "games_evaluated": model_stats["games"],
        
        # All predictions with betting simulation
        "all_predictions": {
            "moneyline": _finalize_market_payload(model_stats["moneyline"], include_logloss=True, include_kelly=True, is_moneyline=True),
            "spread": _finalize_market_payload(model_stats["spread"]),
            "total": _finalize_market_payload(model_stats["total"]),
        },
        
        # Betting performance (recommended picks only)
        "recommended": {
            "count": len(graded_picks),
            "moneyline": _finalize_market_payload(recommended_stats["moneyline"], include_logloss=True, include_kelly=True, is_moneyline=True),
            "spread": _finalize_market_payload(recommended_stats["spread"]),
            "total": _finalize_market_payload(recommended_stats["total"]),
        },
        
        "generated_at": generated_at,
    }
    
    # Store raw stats for aggregation
    payload["_raw_model_stats"] = model_stats
    payload["_recommended_stats"] = recommended_stats
    payload["_graded_picks"] = graded_picks
    
    return payload


def _merge_stats(dest: Dict[str, Any], src: Dict[str, Any]) -> None:
    """Merge source stats into destination stats."""
    dest["games"] += src["games"]
    for market in ("moneyline", "spread", "total"):
        dest_market: MarketStats = dest[market]
        src_market: MarketStats = src[market]
        dest_market.count += src_market.count
        dest_market.correct += src_market.correct
        dest_market.pushes += src_market.pushes
        dest_market.mae_sum += src_market.mae_sum
        dest_market.logloss_sum += src_market.logloss_sum
        dest_market.bets.extend(src_market.bets)
        dest_market.winner_correct += src_market.winner_correct


def _merge_recommended_stats(dest: Dict[str, MarketStats], src: Dict[str, MarketStats]) -> None:
    """Merge source recommended stats into destination."""
    for market in ("moneyline", "spread", "total"):
        dest_market = dest[market]
        src_market = src[market]
        dest_market.count += src_market.count
        dest_market.correct += src_market.correct
        dest_market.pushes += src_market.pushes
        dest_market.mae_sum += src_market.mae_sum
        dest_market.logloss_sum += src_market.logloss_sum
        dest_market.bets.extend(src_market.bets)
        dest_market.winner_correct += src_market.winner_correct


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point."""
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    dates = _resolve_dates(args)
    db = _ensure_firestore()
    
    # Aggregate stats across all dates
    overall_model_stats = _init_stats()
    overall_recommended_stats = _init_recommended_stats()
    day_results: List[tuple[Dict[str, Any], List[Dict[str, Any]]]] = []

    for date_str in dates:
        logging.info("Evaluating %s...", date_str)
        payload = evaluate_date(date_str, db, args.result_source)
        
        if not payload:
            continue
            
        # Extract and merge raw stats
        model_stats = payload.pop("_raw_model_stats")
        recommended_stats = payload.pop("_recommended_stats")
        graded_picks = payload.pop("_graded_picks")
        
        _merge_stats(overall_model_stats, model_stats)
        _merge_recommended_stats(overall_recommended_stats, recommended_stats)
        day_results.append((payload, graded_picks))

    if not day_results:
        logging.warning("No evaluation data generated for requested range.")
        return

    # Create summary payload
    summary_payload = {
        "date_range": {
            "start": dates[0],
            "end": dates[-1],
        },
        "games_evaluated": overall_model_stats["games"],
        
        # All predictions with betting simulation
        "all_predictions": {
            "moneyline": _finalize_market_payload(overall_model_stats["moneyline"], include_logloss=True, include_kelly=True, is_moneyline=True),
            "spread": _finalize_market_payload(overall_model_stats["spread"]),
            "total": _finalize_market_payload(overall_model_stats["total"]),
        },
        
        # Betting performance (recommended picks only)
        "recommended": {
            "count": sum(overall_recommended_stats[m].count for m in overall_recommended_stats),
            "moneyline": _finalize_market_payload(overall_recommended_stats["moneyline"], include_logloss=True, include_kelly=True, is_moneyline=True),
            "spread": _finalize_market_payload(overall_recommended_stats["spread"]),
            "total": _finalize_market_payload(overall_recommended_stats["total"]),
        },
        
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if args.dry_run:
        logging.info("[DRY RUN] Computed %d day payloads + summary:", len(day_results))
        for payload, picks in day_results:
            logging.info("  %s -> All predictions: %s, Recommended: %d picks", 
                        payload["date"], 
                        payload["all_predictions"]["moneyline"],
                        len(picks))
        logging.info("Summary: %s", summary_payload)
        return

    # Write to Firestore
    eval_collection = db.collection(args.collection)
    batch = db.batch()
    
    for payload, _ in day_results:
        doc_ref = eval_collection.document(payload["date"])
        batch.set(doc_ref, payload)
        
    batch.set(eval_collection.document("summary"), summary_payload)
    batch.commit()
    
    logging.info(
        "Wrote %d day documents + summary to collection '%s'.",
        len(day_results),
        args.collection,
    )

    # Write recommended picks to subcollection
    for payload, picks in day_results:
        doc_ref = eval_collection.document(payload["date"])
        subcollection = doc_ref.collection(RECOMMENDED_SUBCOLLECTION)
        
        # Clear previous docs
        existing = list(subcollection.stream())
        for doc in existing:
            doc.reference.delete()
            
        # Write new picks
        for idx, pick in enumerate(picks):
            game_id = pick.get("game_id", "game")
            bet_type = pick.get("bet_type", "bet")
            doc_id = f"{game_id}_{bet_type}_{idx}"
            # Sanitize doc_id
            doc_id = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(doc_id))
            
            sub_doc = dict(pick)
            sub_doc.pop("doc_id", None)
            subcollection.document(doc_id).set(sub_doc)
            
    logging.info("Wrote recommended picks to subcollections.")


if __name__ == "__main__":
    main()