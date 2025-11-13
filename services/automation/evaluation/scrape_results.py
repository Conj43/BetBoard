#!/usr/bin/env python3
"""
Scrape completed men's games from Sports Reference for the previous day and write
final scores directly onto the Firestore game document (home_score/away_score).
"""
from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from firebase_admin import firestore

from automation.config.config import FIRESTORE_PREDICTIONS_COLLECTION
from automation.clients.firestore import _ensure_firestore
from automation.config.team_keys import canonicalize_team_key
from automation.config.utils import load_alias_map

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback for older Python
    ZoneInfo = None  # type: ignore


BASE_HOST = "https://www.sports-reference.com"
BOX_SCORES_ENDPOINT = f"{BASE_HOST}/cbb/boxscores/index.cgi"
DEFAULT_TIMEZONE = "America/Chicago"
RESULT_DOC_ID = "sports_reference"
_ALIAS_MAP: Optional[Dict[str, str]] = None


def _normalize_team_key(value: Any) -> str:
    if isinstance(value, dict):
        # Allow passing TeamResult dicts directly
        value = value.get("canonical_key") or value.get("name")

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


@dataclasses.dataclass
class TeamResult:
    name: str
    score: int
    slug: Optional[str]
    canonical_key: str
    poll_rank: Optional[int]
    season: Optional[int]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "slug": self.slug,
            "canonical_key": self.canonical_key,
            "poll_rank": self.poll_rank,
            "season": self.season,
        }


@dataclasses.dataclass
class GameDocLookup:
    doc_id: str
    reference: Any
    team_set: frozenset[str]
    home_team: str
    away_team: str


class SportsReferenceResultsScraper:
    def __init__(self, max_retries: int = 3, timeout: int = 30) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        self.max_retries = max_retries
        self.timeout = timeout

    def scrape_date(self, target_date: date) -> List[Dict[str, Any]]:
        page_html = self._fetch_day_html(target_date)
        soup = BeautifulSoup(page_html, "html.parser")
        summaries = soup.select("div.game_summary")
        results: List[Dict[str, Any]] = []

        for summary in summaries:
            parsed = self._parse_summary(summary, target_date)
            if parsed:
                results.append(parsed)

        return results

    def _fetch_day_html(self, target_date: date) -> str:
        params = {"month": target_date.month, "day": target_date.day, "year": target_date.year}
        backoff = 5
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(BOX_SCORES_ENDPOINT, params=params, timeout=self.timeout)
            except Exception as exc:
                last_error = exc
                logging.warning("Request error (attempt %s/%s): %s", attempt, self.max_retries, exc)
                time.sleep(backoff)
                backoff *= 2
                continue

            if resp.status_code == 429 and attempt < self.max_retries:
                logging.warning(
                    "Rate limited fetching %s (attempt %s/%s). Retrying after %ss.",
                    BOX_SCORES_ENDPOINT,
                    attempt,
                    self.max_retries,
                    backoff,
                )
                time.sleep(backoff)
                backoff *= 2
                continue

            resp.raise_for_status()
            return resp.text

        raise RuntimeError(f"Failed to fetch scoreboard after {self.max_retries} attempts") from last_error

    def _parse_summary(self, summary, target_date: date) -> Optional[Dict[str, Any]]:
        teams_table = summary.find("table", class_="teams")
        if not teams_table:
            return None

        winner_row = teams_table.find("tr", class_="winner")
        loser_row = teams_table.find("tr", class_="loser")

        if not winner_row or not loser_row:
            return None

        winner = self._parse_team_row(winner_row)
        loser = self._parse_team_row(loser_row)

        if not winner or not loser:
            return None

        gamelink = summary.select_one("td.gamelink a")
        boxscore_url = urljoin(BASE_HOST, gamelink["href"]) if gamelink and gamelink.has_attr("href") else None
        boxscore_id = None
        if boxscore_url:
            parsed = urlparse(boxscore_url)
            boxscore_id = parsed.path.rstrip("/").split("/")[-1].replace(".html", "")

        gender = "unknown"
        classes = summary.get("class") or []
        for cls in classes:
            if cls.startswith("gender-"):
                gender = {"gender-m": "men", "gender-w": "women"}.get(cls, cls.split("-", 1)[-1])
                break

        desc_cell = teams_table.find("td", class_="desc")
        gender_label = desc_cell.get_text(strip=True) if desc_cell else None

        # Sports Reference mixes men's/women's results on the same page.
        # Only keep men's games.
        gender_label_lower = (gender_label or "").lower()
        if gender != "men" or "women" in gender_label_lower:
            return None

        status_text = None
        if gamelink:
            status_parts = list(gamelink.stripped_strings)
            status_text = "".join(status_parts) if status_parts else None

        status = status_text or "Final"

        margin = winner.score - loser.score

        return {
            "game_id": boxscore_id or f"{target_date.isoformat()}-{winner.canonical_key}-{loser.canonical_key}",
            "source": "sports_reference",
            "result_date": target_date.isoformat(),
            "boxscore_url": boxscore_url,
            "status": status,
            "gender": gender,
            "gender_label": gender_label,
            "winner": winner.as_dict(),
            "loser": loser.as_dict(),
            "margin": margin,
            "scraped_at": datetime.utcnow().isoformat() + "Z",
        }

    def _parse_team_row(self, row) -> Optional[TeamResult]:
        name_link = row.find("a")
        name = name_link.get_text(strip=True) if name_link else row.get_text(strip=True)

        slug = None
        season = None
        if name_link and name_link.has_attr("href"):
            slug, season = self._extract_slug_and_season(name_link["href"])

        canonical = _normalize_team_key(slug or name)

        score_cell = None
        for cell in row.find_all("td"):
            classes = cell.get("class") or []
            if "right" in classes and "gamelink" not in classes:
                score_cell = cell
                break
        if not score_cell:
            return None

        try:
            score = int(score_cell.get_text(strip=True))
        except ValueError:
            return None

        rank = None
        poll = row.find("span", class_="pollrank")
        if poll:
            digits = "".join(ch for ch in poll.get_text() if ch.isdigit())
            rank = int(digits) if digits else None

        return TeamResult(
            name=name,
            score=score,
            slug=slug,
            canonical_key=canonical,
            poll_rank=rank,
            season=season,
        )

    @staticmethod
    def _extract_slug_and_season(href: str) -> tuple[Optional[str], Optional[int]]:
        parts = [part for part in href.split("/") if part]
        slug = None
        if "schools" in parts:
            idx = parts.index("schools")
            if idx + 1 < len(parts):
                slug = parts[idx + 1]
        season = None
        if parts:
            tail = parts[-1]
            if tail.endswith(".html"):
                tail = tail[:-5]
            if tail.isdigit():
                season = int(tail)
        return slug, season


def determine_target_date(date_override: Optional[str], tz_name: str = DEFAULT_TIMEZONE) -> date:
    if date_override:
        return datetime.strptime(date_override, "%Y-%m-%d").date()

    if ZoneInfo:
        try:
            tz = ZoneInfo(tz_name)
            return (datetime.now(tz).date() - timedelta(days=1))
        except Exception:
            pass

    return datetime.utcnow().date() - timedelta(days=1)


def _build_game_doc_lookup(games_collection) -> tuple[Dict[str, GameDocLookup], Dict[frozenset[str], List[GameDocLookup]]]:
    by_id: Dict[str, GameDocLookup] = {}
    by_team_set: Dict[frozenset[str], List[GameDocLookup]] = {}

    for snapshot in games_collection.stream():
        data = snapshot.to_dict() or {}
        home = _normalize_team_key(data.get("home_team"))
        away = _normalize_team_key(data.get("away_team"))
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
    game_id = str(game.get("game_id", "")).strip()
    if game_id:
        direct = lookup_by_id.get(game_id)
        if direct:
            return direct

    winner_key = _normalize_team_key(game.get("winner", {}).get("canonical_key"))
    loser_key = _normalize_team_key(game.get("loser", {}).get("canonical_key"))
    team_set = frozenset(filter(None, (winner_key, loser_key)))
    if not team_set:
        return None

    candidates = lookup_by_team_set.get(team_set, [])
    if not candidates:
        return None
    if len(candidates) > 1:
        logging.warning(
            "Multiple Firestore game docs match teams %s; selecting %s",
            sorted(team_set),
            candidates[0].doc_id,
        )
    return candidates[0]


def _extract_home_away_scores(game: Dict[str, Any], match: GameDocLookup) -> tuple[Optional[int], Optional[int]]:
    scores: Dict[str, int] = {}
    for label in ("winner", "loser"):
        team = game.get(label) or {}
        canonical = _normalize_team_key(team.get("canonical_key") or team.get("slug") or team.get("name"))
        try:
            score = int(team.get("score"))
        except (TypeError, ValueError):
            score = None
        if canonical and score is not None:
            scores[canonical] = score

    home_score = scores.get(match.home_team)
    away_score = scores.get(match.away_team)
    return home_score, away_score


def publish_results(date_str: str, games: Iterable[Dict[str, Any]], dry_run: bool = False) -> None:
    games = list(games)
    if not games:
        logging.info("No games to publish for %s", date_str)
        return

    logging.info("Found %s completed games for %s", len(games), date_str)
    if dry_run:
        for game in games:
            logging.info("DRY RUN: %s vs %s -> %s", game["winner"]["name"], game["loser"]["name"], game["status"])
        return

    db = _ensure_firestore()
    parent_doc = db.collection(FIRESTORE_PREDICTIONS_COLLECTION).document(date_str)
    games_collection = parent_doc.collection("games")
    lookup_by_id, lookup_by_team_set = _build_game_doc_lookup(games_collection)
    if not lookup_by_id:
        logging.warning(
            "No game documents found under %s/%s. Ensure predictions are published before results.",
            FIRESTORE_PREDICTIONS_COLLECTION,
            date_str,
        )

    for game in games:
        match = _match_game_doc(game, lookup_by_id, lookup_by_team_set)
        if not match:
            logging.warning(
                "Unable to match result %s vs %s to Firestore games/%s",
                game["winner"]["name"],
                game["loser"]["name"],
                date_str,
            )
            continue

        payload = dict(game)
        home_score, away_score = _extract_home_away_scores(payload, match)
        if home_score is None or away_score is None:
            logging.warning(
                "Could not determine home/away score for %s vs %s (matched doc %s)",
                match.home_team,
                match.away_team,
                match.doc_id,
            )
            continue

        result_doc = {
            "home_score": home_score,
            "away_score": away_score,
            "status": payload.get("status"),
            "source": "sports_reference",
            "boxscore_url": payload.get("boxscore_url"),
            "boxscore_id": payload.get("game_id"),
            "scraped_at": payload.get("scraped_at"),
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        result_doc = {k: v for k, v in result_doc.items() if v is not None}

        results_collection = match.reference.collection("game_results")
        results_collection.document(RESULT_DOC_ID).set(result_doc)

        logging.info(
            "Published final score home=%s away=%s to %s",
            home_score,
            away_score,
            results_collection.document(RESULT_DOC_ID).path,
        )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Sports Reference results and publish to Firestore.")
    parser.add_argument("--date", help="YYYY-MM-DD date to scrape. Defaults to yesterday in America/Chicago.", default=None)
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help="Timezone used to compute 'yesterday'.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and parse results without writing to Firestore.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    target_date = determine_target_date(args.date, args.timezone)
    logging.info("Scraping Sports Reference results for %s", target_date.isoformat())

    scraper = SportsReferenceResultsScraper()
    games = scraper.scrape_date(target_date)

    publish_results(target_date.isoformat(), games, dry_run=args.dry_run)


if __name__ == "__main__":
    main(sys.argv[1:])
