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
    "New Haven Chargers": "new-haven",
    "Columbia Lions": "columbia",
    "UTSA Roadrunners": "texas-san-antonio",
    "SIU-Edwardsville Cougars": "southern-illinois-edwardsville",
    "Colgate Raiders": "colgate",
    "Northeastern Huskies": "northeastern",
    "Northwestern Wildcats": "northwestern",
    "Boston Univ. Terriers": "boston-university",
    "Liberty Flames": "liberty",
    "Charleston Cougars": "college-of-charleston",
    "Maryland Terrapins": "maryland",
    "Georgetown Hoyas": "georgetown",
    "Rhode Island Rams": "rhode-island",
    "Tulsa Golden Hurricane": "tulsa",
    "Buffalo Bulls": "buffalo",
    "Green Bay Phoenix": "green-bay",
    "Ohio State Buckeyes": "ohio-state",
    "Fort Wayne Mastodons": "ipfw",
    "Florida St Seminoles": "florida-state",
    "Alabama St Hornets": "alabama-state",
    "Stephen F. Austin Lumberjacks": "stephen-f-austin",
    "Arkansas St Red Wolves": "arkansas-state",
    "Brown Bears": "brown",
    "Siena Saints": "siena",
    "Charlotte 49ers": "charlotte",
    "Tennessee Tech Golden Eagles": "tennessee-tech",
    "Clemson Tigers": "clemson",
    "Gardner-Webb Bulldogs": "gardner-webb",
    "Kent State Golden Flashes": "kent-state",
    "Cornell Big Red": "cornell",
    "Davidson Wildcats": "davidson",
    "Washington St Cougars": "washington-state",
    "Notre Dame Fighting Irish": "notre-dame",
    "Detroit Mercy Titans": "detroit-mercy",
    "Duquesne Dukes": "duquesne",
    "Sacred Heart Pioneers": "sacred-heart",
    "Arizona Wildcats": "arizona",
    "Bryant Bulldogs": "bryant",
    "Buffalo Bulls": "buffalo",
    "Cal Baptist Lancers": "california-baptist",
    "Chattanooga Mocs": "chattanooga",
    "Cincinnati Bearcats": "cincinnati",
    "DePaul Blue Demons": "depaul",
    "Florida Gulf Coast Eagles": "florida-gulf-coast",
    "Furman Paladins": "furman",
    "George Mason Patriots": "george-mason",
    "Georgia St Panthers": "georgia-state",
    "Georgia Tech Yellow Jackets": "georgia-tech",
    "Grand Canyon Antelopes": "grand-canyon",
    "Hofstra Pride": "hofstra",
    "Idaho State Bengals": "idaho-state",
    "Illinois Fighting Illini": "illinois",
    "Iona Gaels": "iona",
    "Iowa Hawkeyes": "iowa",
    "Kentucky Wildcats": "kentucky",
    "Longwood Lancers": "longwood",
    "Louisiana Ragin' Cajuns": "louisiana-lafayette",
    "McNeese Cowboys": "mcneese-state",
    "Miss Valley St Delta Devils": "mississippi-valley-state",
    "Missouri Tigers": "missouri",
    "Morehead St Eagles": "morehead-state",
    "Murray St Racers": "murray-state",
    "NC State Wolfpack": "north-carolina-state",
    "Navy Midshipmen": "navy",
    "North Carolina Central Eagles": "north-carolina-central",
    "Northern Illinois Huskies": "northern-illinois",
    "Oakland Golden Grizzlies": "oakland",
    "Ole Miss Rebels": "mississippi",
    "Oregon Ducks": "oregon",
    "Oregon St Beavers": "oregon-state",
    "Pepperdine Waves": "pepperdine",
    "Pittsburgh Panthers": "pittsburgh",
    "Purdue Boilermakers": "purdue",
    "Rice Owls": "rice",
    "SE Louisiana Lions": "southeastern-louisiana",
    "SE Missouri St Redhawks": "southeast-missouri-state",
    "Saint Mary's Gaels": "saint-marys-ca",
    "Sam Houston St Bearkats": "sam-houston-state",
    "Samford Bulldogs": "samford",
    "San Diego Toreros": "san-diego",
    "Santa Clara Broncos": "santa-clara",
    "Seton Hall Pirates": "seton-hall",
    "South Carolina St Bulldogs": "south-carolina-state",
    "Southern Illinois Salukis": "southern-illinois",
    "Stonehill Skyhawks": "stonehill",
    "Texas Tech Red Raiders": "texas-tech",
    "Troy Trojans": "troy",
    "UAB Blazers": "alabama-birmingham",
    "UC Irvine Anteaters": "california-irvine",
    "UCLA Bruins": "ucla",
    "UConn Huskies": "connecticut",
    "UIC Flames": "illinois-chicago",
    "UL Monroe Warhawks": "louisiana-monroe",
    "UMKC Kangaroos": "missouri-kansas-city",
    "UMass Lowell River Hawks": "massachusetts-lowell",
    "Utah State Aggies": "utah-state",
    "Utah Tech Trailblazers": "dixie-state",
    "VCU Rams": "virginia-commonwealth",
    "VMI Keydets": "virginia-military-institute",
    "Valparaiso Beacons": "valparaiso",
    "Virginia Cavaliers": "virginia",
    "Wagner Seahawks": "wagner",
    "Wake Forest Demon Deacons": "wake-forest",
    "Washington St Cougars": "washington-state",
    "Western Illinois Leathernecks": "western-illinois",
    "Winthrop Eagles": "winthrop",
    "Wisconsin Badgers": "wisconsin",
    "Yale Bulldogs": "yale",
    "Youngstown St Penguins": "youngstown-state",
    "Air Force Falcons": "air-force",
    "Akron Zips": "akron",
    "Austin Peay Governors": "austin-peay",
    "BYU Cougars": "brigham-young",
    "Bellarmine Knights": "bellarmine",
    "Belmont Bruins": "belmont",
    "Binghamton Bearcats": "binghamton",
    "Boise State Broncos": "boise-state",
    "Bradley Braves": "bradley",
    "CSU Fullerton Titans": "cal-state-fullerton",
    "Cal Poly Mustangs": "cal-poly",
    "Canisius Golden Griffins": "canisius",
    "Central Michigan Chippewas": "central-michigan",
    "Colorado Buffaloes": "colorado",
    "Dayton Flyers": "dayton",
    "Drexel Dragons": "drexel",
    "Duke Blue Devils": "duke",
    "East Carolina Pirates": "east-carolina",
    "East Tennessee St Buccaneers": "east-tennessee-state",
    "Elon Phoenix": "elon",
    "Fairfield Stags": "fairfield",
    "Florida A&M Rattlers": "florida-am",
    "Florida Atlantic Owls": "florida-atlantic",
    "Florida Int'l Golden Panthers": "florida-international",
    "GW Revolutionaries": "george-washington",
    "Holy Cross Crusaders": "holy-cross",
    "Houston Christian Huskies": "houston-baptist",
    "Houston Cougars": "houston",
    "Kansas St Wildcats": "kansas-state",
    "Kennesaw St Owls": "kennesaw-state",
    "Lafayette Leopards": "lafayette",
    "Long Beach St 49ers": "long-beach-state",
    "Maine Black Bears": "maine",
    "Marshall Thundering Herd": "marshall",
    "Memphis Tigers": "memphis",
    "Milwaukee Panthers": "milwaukee",
    "Minnesota Golden Gophers": "minnesota",
    "Monmouth Hawks": "monmouth",
    "Montana Grizzlies": "montana",
    "NJIT Highlanders": "njit",
    "Nebraska Cornhuskers": "nebraska",
    "Nevada Wolf Pack": "nevada",
    "Niagara Purple Eagles": "niagara",
    "Norfolk St Spartans": "norfolk-state",
    "Northern Kentucky Norse": "northern-kentucky",
    "Pacific Tigers": "pacific",
    "Penn State Nittany Lions": "penn-state",
    "Prairie View Panthers": "prairie-view",
    "Presbyterian Blue Hose": "presbyterian",
    "Princeton Tigers": "princeton",
    "Providence Friars": "providence",
    "Queens University Royals": "queens-nc",
    "Richmond Spiders": "richmond",
    "Saint Joseph's Hawks": "saint-josephs",
    "San Francisco Dons": "san-francisco",
    "San José St Spartans": "san-jose-state",
    "Seattle Redhawks": "seattle",
    "South Florida Bulls": "south-florida",
    "Southern Utah Thunderbirds": "southern-utah",
    "St. Bonaventure Bonnies": "st-bonaventure",
    "Stanford Cardinal": "stanford",
    "Stony Brook Seawolves": "stony-brook",
    "Syracuse Orange": "syracuse",
    "Tennessee St Tigers": "tennessee-state",
    "Tennessee Volunteers": "tennessee",
    "Texas Longhorns": "texas",
    "Texas State Bobcats": "texas-state",
    "Toledo Rockets": "toledo",
    "Towson Tigers": "towson",
    "Tulane Green Wave": "tulane",
    "UC San Diego Tritons": "california-san-diego",
    "UC Santa Barbara Gauchos": "california-santa-barbara",
    "UCF Knights": "central-florida",
    "UMBC Retrievers": "maryland-baltimore-county",
    "UNC Greensboro Spartans": "north-carolina-greensboro",
    "UNLV Rebels": "nevada-las-vegas",
    "UT Rio Grande Valley Vaqueros": "texas-pan-american",
    "UT-Arlington Mavericks": "texas-arlington",
    "Utah Utes": "utah",
    "Utah Valley Wolverines": "utah-valley",
    "Vanderbilt Commodores": "vanderbilt",
    "Villanova Wildcats": "villanova",
    "Virginia Tech Hokies": "virginia-tech",
    "Weber State Wildcats": "weber-state",
    "Western Carolina Catamounts": "western-carolina",
    "Wichita St Shockers": "wichita-state",
    "William & Mary Tribe": "william-mary",
    "Wofford Terriers": "wofford",
    "Wyoming Cowboys": "wyoming",
    "Baylor Bears": "baylor",
    "Colorado St Rams": "colorado-state",
    "Eastern Michigan Eagles": "eastern-michigan",
    "Hawai'i Rainbow Warriors": "hawaii",
    "Howard Bison": "howard",
    "Lamar Cardinals": "lamar",
    "Lindenwood Lions": "lindenwood",
    "Manhattan Jaspers": "manhattan",
    "New Orleans Privateers": "new-orleans",
    "San Diego St Aztecs": "san-diego-state",
    "South Carolina Gamecocks": "south-carolina",
    "Southern Miss Golden Eagles": "southern-mississippi",
    "St. Thomas (MN) Tommies": "saint-thomas-mn",
    "UNC Wilmington Seahawks": "north-carolina-wilmington",
    "USC Trojans": "southern-california",
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
