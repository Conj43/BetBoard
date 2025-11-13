"""
Utilities for publishing model predictions to Firebase Firestore.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, Iterable, List, Mapping, Optional

import firebase_admin
import pandas as pd
from firebase_admin import credentials, firestore, storage

from automation.config.config import (
    ACTIVE_MODEL_RUN_ID,
    FIREBASE_CREDENTIALS_PATH,
    FIREBASE_STORAGE_BUCKET,
    FIRESTORE_PREDICTIONS_COLLECTION,
    MAX_PICKS_TO_PUBLISH,
    RAW_TORVIK_PREFIX,
    TORVIK_MAP,
    firestore_doc_for_game_pred,
)
from automation.config.team_keys import canonicalize_team_key


def _ensure_firestore(credentials_path: Optional[str] = None) -> firestore.Client:
    """
    Initialize firebase_admin if needed and return a Firestore client.
    """
    cred_path = credentials_path or FIREBASE_CREDENTIALS_PATH

    if not firebase_admin._apps:
        options = {}
        if FIREBASE_STORAGE_BUCKET:
            options["storageBucket"] = FIREBASE_STORAGE_BUCKET

        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, options or None)
        else:
            firebase_admin.initialize_app(options=options or None)

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


_TORVIK_RANKS_CACHE: Optional[Dict[str, int]] = None


def _get_storage_bucket():
    try:
        _ensure_firestore()
        if FIREBASE_STORAGE_BUCKET:
            return storage.bucket(name=FIREBASE_STORAGE_BUCKET)
        return storage.bucket()
    except Exception:
        return None


def _load_latest_torvik_ranks() -> Dict[str, int]:
    global _TORVIK_RANKS_CACHE

    if _TORVIK_RANKS_CACHE is not None:
        return _TORVIK_RANKS_CACHE

    bucket = _get_storage_bucket()
    if not bucket:
        _TORVIK_RANKS_CACHE = {}
        return _TORVIK_RANKS_CACHE

    blob = bucket.blob(f"{RAW_TORVIK_PREFIX}/latest.csv")
    if not blob.exists():
        _TORVIK_RANKS_CACHE = {}
        return _TORVIK_RANKS_CACHE

    try:
        csv_text = blob.download_as_text()
        df = pd.read_csv(StringIO(csv_text))
    except Exception:
        _TORVIK_RANKS_CACHE = {}
        return _TORVIK_RANKS_CACHE

    team_col = next(
        (c for c in df.columns if c and c.strip().lower() in {"team", "school", "team_name"}),
        None,
    )
    rank_col = next(
        (c for c in df.columns if c and c.strip().lower() in {"rank", "torvik_rank"}),
        None,
    )

    if not team_col or not rank_col:
        _TORVIK_RANKS_CACHE = {}
        return _TORVIK_RANKS_CACHE

    ranks: Dict[str, int] = {}

    for _, row in df.iterrows():
        raw_name = str(row.get(team_col, "")).strip()
        if not raw_name:
            continue

        raw_rank = row.get(rank_col)
        try:
            rank_value = int(float(raw_rank))
        except (TypeError, ValueError):
            rank_value = None

        if rank_value is None:
            continue

        cleaned = raw_name.replace(" St.", "-state")
        slug_candidate = cleaned.lower().replace(" ", "")
        mapped = TORVIK_MAP.get(slug_candidate, slug_candidate)
        canonical = canonicalize_team_key(mapped)

        if canonical:
            ranks[canonical] = rank_value

    _TORVIK_RANKS_CACHE = ranks
    return _TORVIK_RANKS_CACHE


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
    torvik_ranks = _load_latest_torvik_ranks()

    root_doc = db.collection(FIRESTORE_PREDICTIONS_COLLECTION).document(date_str)
    games_collection = root_doc.collection("games")
    meta_collection = root_doc.collection("picks_metadata")

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
        doc_body = firestore_doc_for_game_pred(game_pred, picks_for_game, torvik_ranks)
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
        bet_pred = bet_lookup.get(game_id)
        if bet_pred:
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
