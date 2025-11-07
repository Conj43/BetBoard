"""
Shared team/conference key definitions and normalization helpers.
No Firebase or runtime side effects - safe for import in data/ML pipelines.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path


TEAM_MAPPING = {
    "Rutgers Scarlet Knights":"rutgers",
    "Rider Broncs": "rider",
    "La Salle Explorers": "la-salle",
    "Coppin St Eagles": "coppin-state",
    "Butler Bulldogs": "butler",
    "Southern Indiana Screaming Eagles": "southern-indiana",
    "Temple Owls": "temple",
    "Delaware St Hornets" : "delaware-state",
    "Georgia Bulldogs": "georgia",
    "Maryland-Eastern Shore Hawks": "maryland-eastern-shore",
    "Indiana Hoosiers": "indiana",
    "Alabama A&M Bulldogs": "alabama-am",
    "Creighton Bluejays": "creighton",
    "South Dakota Coyotes": "south-dakota",
    "LSU Tigers": "louisiana-state",
    "Tarleton State Texans": "tarleton-state",
    "Marquette Golden Eagles": "marquette",
    "Southern Jaguars": "southern",
    "New Mexico Lobos": "new-mexico",
    "East Texas A&M Lions": "texas-am-commerce",
    "Fresno St Bulldogs": "fresno-state",
    "South Carolina Upstate Spartans": "south-carolina-upstate",
    "Mississippi St Bulldogs": "mississippi-state",
    "North Alabama Lions": "north-alabama",
    "UC Davis Aggies": "california-davis",
    "North Dakota St Bison": "north-dakota-state",
    "Loyola Marymount Lions": "loyola-marymount",
    "Eastern Washington Eagles": "eastern-washington",
    "Miami Hurricanes": "miami-fl",
    "Bethune-Cookman Wildcats": "bethune-cookman",
    "Boston College Eagles": "boston-college",
    "The Citadel Bulldogs": "citadel",
    "West Virginia Mountaineers": "west-virginia",
    "Campbell Fighting Camels": "campbell",
    "Ohio Bobcats": "ohio",
    "Illinois St Redbirds": "illinois-state",
    "Louisville Cardinals": "louisville",
    "Jackson St Tigers": "jackson-state",
    "Iowa State Cyclones": "iowa-state",
    "Grambling St Tigers": "grambling",
    "Drake Bulldogs": "drake",
    "Robert Morris Colonials": "robert-morris",
    "Abilene Christian Wildcats": "abilene-christian",
    "Omaha Mavericks": "nebraska-omaha",
    "Auburn Tigers": "auburn",
    "Merrimack Warriors": "merrimack",
    "Northern Iowa Panthers": "northern-iowa",
    "CSU Northridge Matadors": "cal-state-northridge",
    "Florida Gators": "florida",
    "North Florida Ospreys": "north-florida",
    "North Dakota Fighting Hawks": "north-dakota",
    "UC Riverside Highlanders": "california-riverside",
    "TCU Horned Frogs": "texas-christian",
    "St. Francis (PA) Red Flash": "saint-francis-pa",
    "Texas A&M Aggies": "texas-am",
    "Texas Southern Tigers": "texas-southern",
    "California Golden Bears": "california",
    "Wright St Raiders": "wright-state",
    "Washington Huskies": "washington",
    "Denver Pioneers": "denver",
    "North Carolina Tar Heels": "north-carolina",
    "Kansas Jayhawks": "kansas",
    "St. John's Red Storm": "st-johns-ny",
    "Alabama Crimson Tide": "alabama",
    "Michigan St Spartans": "michigan-state",
    "Arkansas Razorbacks": "arkansas",
    "Gonzaga Bulldogs": "gonzaga",
    "Oklahoma Sooners": "oklahoma",
    "Alcorn St Braves": "alcorn-state",
    "Arkansas-Pine Bluff Golden Lions": "arkansas-pine-bluff",
    "Central Connecticut St Blue Devils": "central-connecticut-state",
    "Chicago St Cougars": "chicago-state",
    "Le Moyne Dolphins": "le-moyne",
    "Loyola (Chi) Ramblers": "loyola-il",
    "Mercyhurst Lakers": "mercyhurst",
    "North Texas Mean Green": "north-texas",
    "Northwestern St Demons": "northwestern-state",
    "SMU Mustangs": "southern-methodist",
    "Texas A&M-CC Islanders": "texas-am-corpus-christi",
    "Portland Pilots": "portland",
    "Quinnipiac Bobcats": "quinnipiac",
    "Xavier Musketeers": "xavier",
    "Saint Louis Billikens": "saint-louis",
    "South Alabama Jaguars": "south-alabama",
}


def _load_conference_map() -> dict[str, list[str]]:
    data_file = Path(__file__).with_name("cbb_conferences_teams.json")
    if not data_file.exists():
        return {}

    try:
        payload = json.loads(data_file.read_text(encoding="utf-8"))
    except Exception:
        return {}

    conferences = payload.get("conferences", {})
    result: dict[str, list[str]] = {}
    for conf_name, teams in conferences.items():
        slugs: list[str] = []
        if isinstance(teams, list):
            for team in teams:
                slug_value = None
                if isinstance(team, dict):
                    slug_value = team.get("slug") or team.get("name")
                elif isinstance(team, str):
                    slug_value = team
                if not isinstance(slug_value, str):
                    continue
                cleaned = slug_value.strip().lower().replace(" ", "-")
                if cleaned:
                    slugs.append(cleaned)
        result[conf_name] = slugs
    return result


CONFERENCE_MAP = _load_conference_map()


def _slug_team_key(value: str) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


@lru_cache(maxsize=1)
def _canonical_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}

    def _record(name: str) -> None:
        if not isinstance(name, str):
            return
        slug = _slug_team_key(name)
        if not slug or slug in lookup:
            return
        lookup[slug] = name

    for teams in CONFERENCE_MAP.values():
        for team in teams:
            _record(team)

    for canonical in TEAM_MAPPING.values():
        _record(canonical)

    return lookup


def canonicalize_team_key(value: str) -> str:
    slug = _slug_team_key(value)
    if not slug:
        return ""
    return _canonical_lookup().get(slug, slug)
