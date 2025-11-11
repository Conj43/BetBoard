#!/usr/bin/env python3
"""
Build a JSON mapping of active Division I men's basketball conferences
to their teams (name + slug) using Sports-Reference.

Output file: cbb_conferences_teams.json
"""

import json
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import requests
from bs4 import BeautifulSoup

# ================= Settings (no CLI) =================
OUTPUT_PATH = "cbb_conferences_teams.json"
REQUEST_DELAY_SEC = 10.0
BASE = "https://www.sports-reference.com"
INDEX_URL = f"{BASE}/cbb/conferences/"
HEADERS = {"User-Agent": "AcademicScraper/1.0"}
CURRENT_SEASON = "2026"
# =====================================================

# /cbb/conferences/acc/men/
CONF_MEN_LINK_RE = re.compile(r"^/cbb/conferences/([a-z0-9-]+)/men/?$", re.I)
# /cbb/schools/north-carolina/  or /cbb/schools/north-carolina/men/
TEAM_LINK_RE = re.compile(r"^/cbb/schools/([a-z0-9-]+)/(?:men/)?$", re.I)


def fetch_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    if REQUEST_DELAY_SEC > 0:
        time.sleep(REQUEST_DELAY_SEC)
    return BeautifulSoup(resp.text, "html.parser")


def clean_conf_title(raw: str) -> str:
    """
    Examples:
      "Men's Atlantic Coast Conference Schools" -> "Atlantic Coast Conference"
      "Men's America East Conference Schools"   -> "America East Conference"
    """
    s = " ".join(raw.split())
    # Strip leading "Men's" or "Women's"
    s = re.sub(r"^(Men's|Women’s|Women's)\s+", "", s, flags=re.I)
    # Drop trailing "Schools" or "Index"
    s = re.sub(r"\s+(Schools|Index)$", "", s, flags=re.I)
    return s


def get_active_conference_slugs() -> List[Tuple[str, str]]:
    """
    Read the Active Conferences table and return list of (slug, display_name_from_index).
    """
    soup = fetch_soup(INDEX_URL)
    out: List[Tuple[str, str]] = []
    for a in soup.select('table#active_NCAAM tbody td[data-stat="conf_name"] a[href]'):
        href = a.get("href", "")
        m = CONF_MEN_LINK_RE.match(href)
        if not m:
            continue
        slug = m.group(1)
        name = " ".join(a.get_text(" ", strip=True).split())
        out.append((slug, name))

    # Deduplicate, preserve order
    seen = set()
    uniq: List[Tuple[str, str]] = []
    for slug, name in out:
        if slug not in seen:
            seen.add(slug)
            uniq.append((slug, name))
    return uniq


def conference_schools_url(slug: str) -> str:
    return f"{BASE}/cbb/conferences/{slug}/men/schools.html"


def extract_conference_title(soup: BeautifulSoup, fallback_slug: str) -> str:
    h1 = soup.find("h1")
    if h1:
        cleaned = clean_conf_title(h1.get_text(" ", strip=True))
        if cleaned:
            return cleaned
    return fallback_slug.upper()


def _get_table_rows(soup: BeautifulSoup) -> List:
    table = soup.find("table", {"id": "schools"}) or soup.find("table")
    if not table or not table.tbody:
        return []
    return table.tbody.find_all("tr")


def extract_team_name_slug(soup: BeautifulSoup, current_season: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Parse the Schools table; return [{name, slug}, ...]
    """
    teams: List[Dict[str, str]] = []

    seen = set()
    for row in _get_table_rows(soup):
        name_cell = row.find("td", {"data-stat": "school_name"})
        if not name_cell:
            continue
        a = name_cell.find("a", href=True)
        if not a:
            continue

        if current_season:
            year_max_cell = row.find("td", {"data-stat": "year_max"})
            year_max = year_max_cell.get_text(strip=True) if year_max_cell else ""
            if year_max and year_max != current_season:
                continue

        href = a.get("href", "")
        m = TEAM_LINK_RE.match(href)
        if not m:
            continue
        slug = m.group(1).lower()
        name = " ".join(a.get_text(" ", strip=True).split())
        key = (name, slug)
        if key in seen:
            continue
        seen.add(key)
        teams.append({"name": name, "slug": slug})

    return teams


def run():
    try:
        confs = get_active_conference_slugs()
        if not confs:
            print("[FATAL] No conferences found on Active Conferences table.", file=sys.stderr)
            sys.exit(2)

        result: Dict[str, List[Dict[str, str]]] = {}

        for slug, _idx_name in confs:
            try:
                url = conference_schools_url(slug)
                page = fetch_soup(url)
                conf_title = extract_conference_title(page, slug)
                teams = extract_team_name_slug(page, CURRENT_SEASON)
                result[conf_title] = teams
                print(f"[OK] {conf_title}: {len(teams)} teams")
            except requests.HTTPError as e:
                code = getattr(e.response, "status_code", None)
                print(f"[WARN] HTTP {code} for {slug}: {e}", file=sys.stderr)
            except Exception as e:
                print(f"[WARN] Failed on {slug}: {e}", file=sys.stderr)

        payload = {
            "source": "sports-reference.com",
            "scraped_at": datetime.utcnow().isoformat() + "Z",
            "conferences": result,
        }
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        print(f"\nWrote {len(result)} conferences to {OUTPUT_PATH}")
    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
