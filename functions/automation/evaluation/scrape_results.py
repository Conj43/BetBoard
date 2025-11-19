#!/usr/bin/env python3
"""
Fetch completed men's games from The Odds API scores endpoint and write
final scores directly onto the Firestore game document (home_score/away_score).
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from firebase_admin import firestore

# Add functions directory to path for local testing
_current_file = Path(__file__).resolve()
_functions_dir = _current_file.parent.parent.parent
if str(_functions_dir) not in sys.path:
    sys.path.insert(0, str(_functions_dir))

from automation.config.config import FIRESTORE_PREDICTIONS_COLLECTION, TEAM_MAPPING
from automation.clients.firestore import _ensure_firestore
from automation.config.team_keys import canonicalize_team_key

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore

# The Odds API configuration
ODDS_API_KEY = '1c6427df57a26416824684d74510ebe7'
ODDS_API_SCORES_URL = 'https://api.the-odds-api.com/v4/sports/basketball_ncaab/scores/'
DEFAULT_TIMEZONE = "America/Chicago"
RESULT_DOC_ID = "odds_api"


def _normalize_team_from_odds_api(team_name: str) -> str:
    """
    Normalize team name from Odds API to match your TEAM_MAPPING.
    First tries direct TEAM_MAPPING lookup, then falls back to canonicalize.
    """
    if not team_name:
        return ""
    
    # Try direct mapping first (e.g., "Georgia Bulldogs" -> "georgia")
    if team_name in TEAM_MAPPING:
        return TEAM_MAPPING[team_name]
    
    # Fall back to canonicalize
    return canonicalize_team_key(team_name)


class OddsAPIScoresFetcher:
    """Fetch completed game scores from The Odds API."""
    
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def fetch_completed_scores_for_date(
        self, 
        target_date: date, 
        tz_name: str = DEFAULT_TIMEZONE
    ) -> List[Dict[str, Any]]:
        """
        Fetch completed games from The Odds API for a specific date in the given timezone.
        
        Args:
            target_date: The date to fetch games for (in the given timezone)
            tz_name: Timezone name (default: America/Chicago)
        """
        # Fetch games from the last 2 days to ensure we catch all games
        # that might span timezone boundaries
        params = {
            'apiKey': self.api_key,
            'daysFrom': 2
        }
        
        try:
            response = self.session.get(
                ODDS_API_SCORES_URL,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # Set up timezone
            if ZoneInfo:
                try:
                    tz = ZoneInfo(tz_name)
                except Exception:
                    logging.warning(f"Could not load timezone {tz_name}, using UTC")
                    tz = None
            else:
                tz = None
            
            # Filter for completed games on the target date (in Central timezone)
            completed_games = []
            for game in data:
                if not game.get('completed'):
                    continue
                
                # Parse the commence time (UTC)
                commence_time_str = game.get('commence_time')
                if not commence_time_str:
                    continue
                
                try:
                    # Parse UTC time: "2025-11-17T23:30:00Z"
                    commence_time_utc = datetime.strptime(
                        commence_time_str.rstrip('Z'), 
                        "%Y-%m-%dT%H:%M:%S"
                    ).replace(tzinfo=ZoneInfo("UTC") if ZoneInfo else None)
                    
                    # Convert to target timezone
                    if tz and ZoneInfo:
                        commence_time_local = commence_time_utc.astimezone(tz)
                        game_date = commence_time_local.date()
                    else:
                        # Fallback: use UTC date
                        game_date = commence_time_utc.date()
                    
                    # Only include games from the target date
                    if game_date != target_date:
                        continue
                    
                except (ValueError, AttributeError) as e:
                    logging.warning(f"Could not parse commence_time '{commence_time_str}': {e}")
                    continue
                
                # Parse scores - they come as strings
                try:
                    # scores[0] is home, scores[1] is away based on the API docs
                    home_score = int(game['scores'][0]['score'])
                    away_score = int(game['scores'][1]['score'])
                except (KeyError, ValueError, IndexError):
                    logging.warning(f"Could not parse scores for game: {game.get('id')}")
                    continue
                
                # Normalize team names using TEAM_MAPPING
                home_team_raw = game.get('home_team', '')
                away_team_raw = game.get('away_team', '')
                home_team_normalized = _normalize_team_from_odds_api(home_team_raw)
                away_team_normalized = _normalize_team_from_odds_api(away_team_raw)
                
                if not home_team_normalized or not away_team_normalized:
                    logging.warning(
                        f"Could not normalize teams: {home_team_raw} / {away_team_raw}"
                    )
                    continue
                
                completed_games.append({
                    'game_id': game.get('id'),
                    'home_team': home_team_normalized,  # Now normalized
                    'away_team': away_team_normalized,  # Now normalized
                    'home_team_raw': home_team_raw,     # Keep original for logging
                    'away_team_raw': away_team_raw,     # Keep original for logging
                    'home_score': home_score,
                    'away_score': away_score,
                    'commence_time': commence_time_str,
                    'completed': game.get('completed'),
                })
            
            logging.info(
                f"Fetched {len(completed_games)} completed games for {target_date} "
                f"({tz_name}) from Odds API"
            )
            return completed_games
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch scores from Odds API: {e}")
            raise


def determine_target_date(date_override: Optional[str], tz_name: str = DEFAULT_TIMEZONE) -> date:
    """Determine which date to fetch results for (in Central timezone)."""
    if date_override:
        return datetime.strptime(date_override, "%Y-%m-%d").date()

    if ZoneInfo:
        try:
            tz = ZoneInfo(tz_name)
            # Get yesterday in Central timezone
            return (datetime.now(tz).date() - timedelta(days=1))
        except Exception:
            logging.warning(f"Could not load timezone {tz_name}, using UTC")

    # Fallback to UTC
    return datetime.utcnow().date() - timedelta(days=1)


class GameDocLookup:
    """Helper for matching API results to Firestore game documents."""
    
    def __init__(self, doc_id: str, reference: Any, team_set: frozenset[str], 
                 home_team: str, away_team: str):
        self.doc_id = doc_id
        self.reference = reference
        self.team_set = team_set
        self.home_team = home_team
        self.away_team = away_team


def _build_game_doc_lookup(games_collection) -> tuple[
    Dict[str, GameDocLookup], 
    Dict[frozenset[str], List[GameDocLookup]]
]:
    """Build lookup tables for matching API results to Firestore docs."""
    by_id: Dict[str, GameDocLookup] = {}
    by_team_set: Dict[frozenset[str], List[GameDocLookup]] = {}

    for snapshot in games_collection.stream():
        data = snapshot.to_dict() or {}
        # Normalize these too!
        home_raw = data.get("home_team", "")
        away_raw = data.get("away_team", "")
        
        # Use the same normalization as the API results
        home = _normalize_team_from_odds_api(home_raw) if home_raw else ""
        away = _normalize_team_from_odds_api(away_raw) if away_raw else ""
        
        team_set = frozenset(filter(None, (home, away)))

        entry = GameDocLookup(
            doc_id=snapshot.id,
            reference=snapshot.reference,
            team_set=team_set,
            home_team=home,
            away_team=away,
        )
        by_id[entry.doc_id] = entry
        if team_set:
            by_team_set.setdefault(team_set, []).append(entry)

    return by_id, by_team_set



def _match_game_doc(
    game: Dict[str, Any],
    lookup_by_id: Dict[str, GameDocLookup],
    lookup_by_team_set: Dict[frozenset[str], List[GameDocLookup]],
) -> Optional[GameDocLookup]:
    """Match an API game result to a Firestore game document."""
    # Try matching by game_id first
    game_id = str(game.get("game_id", "")).strip()
    if game_id:
        direct = lookup_by_id.get(game_id)
        if direct:
            return direct

    # Fall back to matching by normalized team names
    home_key = game.get("home_team", "")  # Already normalized
    away_key = game.get("away_team", "")  # Already normalized
    team_set = frozenset(filter(None, (home_key, away_key)))
    
    if not team_set:
        return None

    candidates = lookup_by_team_set.get(team_set, [])
    if not candidates:
        return None
        
    if len(candidates) > 1:
        logging.warning(
            f"Multiple Firestore game docs match teams {sorted(team_set)}; selecting {candidates[0].doc_id}"
        )
    return candidates[0]


def publish_results(
    date_str: str, 
    games: Iterable[Dict[str, Any]], 
    dry_run: bool = False
) -> None:
    """Publish game results to Firestore."""
    games = list(games)
    if not games:
        logging.info(f"No games to publish for {date_str}")
        return

    logging.info(f"Found {len(games)} completed games for {date_str}")
    
    if dry_run:
        for game in games:
            logging.info(
                f"DRY RUN: {game['away_team_raw']} @ {game['home_team_raw']} -> "
                f"{game['away_score']}-{game['home_score']} "
                f"(normalized: {game['away_team']} @ {game['home_team']})"
            )
        return

    db = _ensure_firestore()
    parent_doc = db.collection(FIRESTORE_PREDICTIONS_COLLECTION).document(date_str)
    games_collection = parent_doc.collection("games")
    lookup_by_id, lookup_by_team_set = _build_game_doc_lookup(games_collection)
    
    if not lookup_by_id:
        logging.warning(
            f"No game documents found under {FIRESTORE_PREDICTIONS_COLLECTION}/{date_str}. "
            "Ensure predictions are published before results."
        )
        return

    matched_count = 0
    for game in games:
        match = _match_game_doc(game, lookup_by_id, lookup_by_team_set)
        if not match:
            logging.warning(
                f"Unable to match result {game['away_team_raw']} @ {game['home_team_raw']} "
                f"(normalized: {game['away_team']} @ {game['home_team']}) "
                f"to Firestore games/{date_str}"
            )
            continue

        # Scores are already correct from API
        home_score = game['home_score']
        away_score = game['away_score']

        result_doc = {
            "home_score": home_score,
            "away_score": away_score,
            "source": "odds_api",
            "game_id": game.get('game_id'),
            "commence_time": game.get('commence_time'),
            "completed": game.get('completed'),
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        result_doc = {k: v for k, v in result_doc.items() if v is not None}

        results_collection = match.reference.collection("game_results")
        results_collection.document(RESULT_DOC_ID).set(result_doc)
        matched_count += 1

        logging.info(
            f"Published final score home={home_score} away={away_score} to "
            f"{results_collection.document(RESULT_DOC_ID).path}"
        )
    
    logging.info(f"Successfully published {matched_count}/{len(games)} game results")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch game scores from Odds API and publish to Firestore."
    )
    parser.add_argument(
        "--date", 
        help="YYYY-MM-DD date to fetch (in specified timezone). Defaults to yesterday.", 
        default=None
    )
    parser.add_argument(
        "--timezone", 
        default=DEFAULT_TIMEZONE, 
        help="Timezone for date calculations (default: America/Chicago)."
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Fetch and parse results without writing to Firestore."
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable debug logging."
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    target_date = determine_target_date(args.date, args.timezone)
    logging.info(
        f"Fetching Odds API scores for {target_date.isoformat()} ({args.timezone})"
    )

    fetcher = OddsAPIScoresFetcher(ODDS_API_KEY)
    games = fetcher.fetch_completed_scores_for_date(target_date, args.timezone)

    publish_results(target_date.isoformat(), games, dry_run=args.dry_run)


if __name__ == "__main__":
    main(sys.argv[1:])