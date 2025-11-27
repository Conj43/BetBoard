from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from automation.config.config import FIRESTORE_PREDICTIONS_COLLECTION
from automation.evaluation import evaluate_predictions as evaluator

_LINE_PATTERN = re.compile(r"[+-]?\d+(?:\.\d+)?")
_RESULT_MAP = {"win": "won", "loss": "lost", "push": "push"}


def _derive_game_date(game_id: Optional[str], bet_data: Dict[str, Any]) -> Optional[str]:
    if game_id:
        match = re.match(r"(\d{4}-\d{2}-\d{2})", str(game_id))
        if match:
            return match.group(1)

    game_date = bet_data.get("game_date") or bet_data.get("gameDate")
    if game_date is None:
        return None

    converter = getattr(game_date, "to_datetime", None)
    if callable(converter):
        try:
            return converter().date().isoformat()
        except Exception:
            return None

    if hasattr(game_date, "date"):
        try:
            return game_date.date().isoformat()
        except Exception:
            pass

    if isinstance(game_date, datetime):
        return game_date.date().isoformat()

    if isinstance(game_date, str):
        try:
            return datetime.fromisoformat(game_date).date().isoformat()
        except ValueError:
            return None

    return None


def _clean_selection_for_team(selection: str) -> str:
    without_line = _LINE_PATTERN.sub(" ", str(selection))
    without_tokens = re.sub(r"\b(ml|moneyline|over|under)\b", " ", without_line, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", without_tokens)
    return " ".join(cleaned.split())


def _parse_line_from_selection(selection: str) -> Optional[float]:
    match = _LINE_PATTERN.search(str(selection))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _total_direction(selection: str) -> Optional[str]:
    upper = str(selection).upper()
    if "OVER" in upper:
        return "OVER"
    if "UNDER" in upper:
        return "UNDER"
    return None


def _ensure_team_names(game_data: Dict[str, Any], bet_data: Dict[str, Any]) -> Tuple[str, str]:
    home = (
        game_data.get("home_team")
        or bet_data.get("home_team_name")
        or bet_data.get("homeTeamName")
        or ""
    )
    away = (
        game_data.get("away_team")
        or bet_data.get("away_team_name")
        or bet_data.get("awayTeamName")
        or ""
    )
    return home, away


def _fetch_game_and_actual(db, date_str: str, game_id: str, result_source: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    game_ref = (
        db.collection(FIRESTORE_PREDICTIONS_COLLECTION)
        .document(date_str)
        .collection("games")
        .document(game_id)
    )
    game_snap = game_ref.get()
    if not game_snap.exists:
        return None, None

    result_doc = evaluator._fetch_result_doc(game_ref, result_source)
    if not result_doc:
        return game_snap.to_dict() or {}, None

    actual = evaluator._build_actual(result_doc)
    if not actual:
        return game_snap.to_dict() or {}, None

    return game_snap.to_dict() or {}, actual


def _grade_user_bet(bet_data: Dict[str, Any], game_data: Dict[str, Any], actual: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    bet_type = str(bet_data.get("type") or "").lower()
    selection_raw = bet_data.get("selection") or ""

    try:
        odds = float(bet_data.get("odds")) if bet_data.get("odds") is not None else None
    except (TypeError, ValueError):
        odds = None

    home_team, away_team = _ensure_team_names(game_data, bet_data)
    if not home_team or not away_team:
        return None

    game_id = bet_data.get("gameID") or bet_data.get("game_id") or bet_data.get("gameId")

    game_data_with_teams = dict(game_data)
    game_data_with_teams.setdefault("home_team", home_team)
    game_data_with_teams.setdefault("away_team", away_team)

    if bet_type == "moneyline":
        pick_selection = _clean_selection_for_team(selection_raw) or selection_raw
        pick = {"selection": pick_selection, "odds": odds, "game_id": game_id}
        return evaluator._grade_moneyline_pick(pick, game_data_with_teams, actual)

    if bet_type == "spread":
        line = _parse_line_from_selection(selection_raw)
        pick_selection = _clean_selection_for_team(selection_raw) or selection_raw
        side = evaluator._resolve_pick(pick_selection, home_team, away_team)
        if line is None or side not in {"home", "away"}:
            return None

        # Convert bettor's line into the home-team convention used by the grader.
        adjusted_line = line if side == "home" else -line
        pick = {
            "selection": pick_selection,
            "book_line": adjusted_line,
            "odds": odds,
            "game_id": game_id,
        }
        return evaluator._grade_spread_pick(pick, game_data_with_teams, actual)

    if bet_type == "total":
        line = _parse_line_from_selection(selection_raw)
        direction = _total_direction(selection_raw)
        if line is None or not direction:
            return None

        pick = {
            "selection": direction,
            "book_line": line,
            "odds": odds,
            "game_id": game_id,
        }
        return evaluator._grade_total_pick(pick, game_data_with_teams, actual)

    return None


def settle_pending_bets(
    db,
    result_source: str = evaluator.DEFAULT_RESULT_DOC,
    dry_run: bool = False,
    verbose: bool = False,
) -> Dict[str, int]:
    """
    Find user bets stuck in 'pending' and settle them using game results.
    Returns summary counts for logging.
    """
    summary = {
        "pending": 0,
        "updated": 0,
        "missing_game": 0,
        "no_result": 0,
        "parse_failed": 0,
    }

    users_ref = db.collection("users")
    for user_snap in users_ref.stream():
        bets_ref = user_snap.reference.collection("bets").where("result", "==", "pending")
        for bet_snap in bets_ref.stream():
            summary["pending"] += 1
            bet_data = bet_snap.to_dict() or {}
            game_id = (
                bet_data.get("gameID")
                or bet_data.get("game_id")
                or bet_data.get("gameId")
            )
            date_str = _derive_game_date(game_id, bet_data)

            if not game_id or not date_str:
                summary["missing_game"] += 1
                if verbose:
                    print(f"[bets][skip] Missing game info for {bet_snap.reference.path}")
                continue

            game_data, actual = _fetch_game_and_actual(db, date_str, str(game_id), result_source)
            if not game_data:
                summary["missing_game"] += 1
                if verbose:
                    print(f"[bets][skip] Game {game_id} not found for bet {bet_snap.reference.path}")
                continue

            if not actual:
                summary["no_result"] += 1
                if verbose:
                    print(f"[bets][skip] No final score yet for game {game_id}")
                continue

            graded = _grade_user_bet(bet_data, game_data, actual)
            if not graded:
                summary["parse_failed"] += 1
                if verbose:
                    print(f"[bets][skip] Could not grade bet {bet_snap.reference.path}")
                continue

            mapped_result = _RESULT_MAP.get(graded.get("result"))
            if not mapped_result:
                summary["parse_failed"] += 1
                if verbose:
                    print(f"[bets][skip] Unexpected grade for {bet_snap.reference.path}: {graded.get('result')}")
                continue

            if dry_run:
                if verbose:
                    print(f"[bets][dry-run] Would set {bet_snap.reference.path} result -> {mapped_result}")
            else:
                bet_snap.reference.update({"result": mapped_result})

            summary["updated"] += 1

    if summary["pending"] == 0:
        print("[evaluation][bets] No pending user bets found.")
    else:
        print(
            f"[evaluation][bets] Settled {summary['updated']} of {summary['pending']} pending bets "
            f"(no result: {summary['no_result']}, missing game: {summary['missing_game']}, parse issues: {summary['parse_failed']})"
            f"{' [dry-run]' if dry_run else ''}."
        )

    return summary
