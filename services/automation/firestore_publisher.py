"""
Utilities for publishing model predictions to Firebase Firestore.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

import firebase_admin
from firebase_admin import credentials, firestore

from config import (
    ACTIVE_MODEL_RUN_ID,
    FIREBASE_CREDENTIALS_PATH,
    FIRESTORE_PREDICTIONS_COLLECTION,
    MAX_PICKS_TO_PUBLISH,
    firestore_doc_for_game_pred,
)


def _ensure_firestore(credentials_path: Optional[str] = None) -> firestore.Client:
    """
    Initialize firebase_admin if needed and return a Firestore client.
    """
    cred_path = credentials_path or FIREBASE_CREDENTIALS_PATH

    if not firebase_admin._apps:
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()

    return firestore.client()


def _to_serializable(value: Any) -> Any:
    """
    Convert numpy/pandas scalars and datetimes into native Python types that
    Firestore can accept.
    """
    # Handle pandas / numpy scalar values
    if hasattr(value, "item") and callable(getattr(value, "item")):
        try:
            return value.item()
        except Exception:
            pass

    # datetimes -> ISO strings
    if isinstance(value, datetime):
        return value.isoformat()

    # Mapping / iterable conversions
    if isinstance(value, Mapping):
        return {str(k): _to_serializable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_to_serializable(v) for v in value]

    return value


def publish_predictions_to_firestore(
    date_str: str,
    game_level_preds: Iterable[Dict[str, Any]],
    top_picks: Iterable[Dict[str, Any]],
    credentials_path: Optional[str] = None,
    max_picks: Optional[int] = None,
    bet_model_preds: Optional[Iterable[Dict[str, Any]]] = None,
) -> None:
    """
    Upsert game-level predictions and ranked picks into Firestore under
    predictions/<date>/<...>.

    Args:
        date_str: Date identifier (YYYY-MM-DD).
        game_level_preds: Iterable of game prediction dicts.
        top_picks: Iterable of pick dicts, already ranked.
        credentials_path: Optional override for Firebase credentials.
        max_picks: Optional override for number of picks to publish.
    """
    db = _ensure_firestore(credentials_path)

    max_publish = max_picks if max_picks is not None else MAX_PICKS_TO_PUBLISH
    picks_list = list(top_picks)[:max_publish]
    games_list = list(game_level_preds)

    root_doc = db.collection(FIRESTORE_PREDICTIONS_COLLECTION).document(date_str)
    games_collection = root_doc.collection("games")
    meta_collection = root_doc.collection("meta")

    # Create lookup of picks per game for doc assembly
    picks_by_game: Dict[str, List[Dict[str, Any]]] = {}
    for pick in picks_list:
        game_id = str(pick.get("game_id", ""))
        if not game_id:
            continue
        picks_by_game.setdefault(game_id, []).append(_to_serializable(pick))

    generated_at = datetime.now(timezone.utc).isoformat()

    bet_lookup: Dict[str, Dict[str, Any]] = {}
    if bet_model_preds:
        for pred in bet_model_preds:
            game_id = str(pred.get("game_id", ""))
            if game_id:
                bet_lookup[game_id] = pred

    for game_pred in games_list:
        game_id = str(game_pred.get("game_id", ""))
        if not game_id:
            continue

        picks_for_game = picks_by_game.get(game_id, [])
        doc_body = firestore_doc_for_game_pred(game_pred, picks_for_game)
        games_collection.document(game_id).set(_to_serializable(doc_body))

        bookmakers = game_pred.get("bookmakers")
        if isinstance(bookmakers, Mapping):
            odds_collection = games_collection.document(game_id).collection("sportsbookOdds")
            for book_key, payload in bookmakers.items():
                if not isinstance(book_key, str):
                    continue
                payload_dict = dict(payload) if isinstance(payload, Mapping) else {}
                base_doc = {
                    "game_id": game_id,
                    "home_team": game_pred.get("home_team"),
                    "away_team": game_pred.get("away_team"),
                    "bookmaker_key": payload_dict.get("bookmaker_key", book_key),
                    "bookmaker_title": payload_dict.get("bookmaker_title"),
                    "retrieved_at": generated_at,
                }
                if "bookmaker_key" not in payload_dict:
                    payload_dict["bookmaker_key"] = book_key
                merged = {**payload_dict, **base_doc}
                odds_collection.document(book_key).set(_to_serializable(merged))

        # Minimal model predictions document
        bet_pred = bet_lookup.get(game_id, game_pred)
        minimal_doc = {
            "model_spread_home": bet_pred.get("model_spread_home"),
            "model_total": bet_pred.get("model_total"),
            "home_win_prob": bet_pred.get("home_win_prob"),
            "model_run_id": ACTIVE_MODEL_RUN_ID,
            "generated_at": generated_at,
        }
        minimal_doc = {k: v for k, v in minimal_doc.items() if v is not None}
        if minimal_doc:
            model_collection = games_collection.document(game_id).collection("betModel")
            model_collection.document("bet_model_document").set(_to_serializable(minimal_doc))

    summary_payload = {
        "generated_at": generated_at,
        "model_run_id": ACTIVE_MODEL_RUN_ID,
        "game_count": len(games_list),
        "top_picks_count": len(picks_list),
    }

    root_doc.set(_to_serializable(summary_payload), merge=True)

    meta_collection.document("summary").set(_to_serializable(summary_payload))
    meta_collection.document("top_picks").set({
        "generated_at": generated_at,
        "picks": _to_serializable(picks_list),
    })
