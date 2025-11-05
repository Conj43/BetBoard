import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import time
import random
import os
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, storage

FIREBASE_CREDENTIALS_PATH = "~/Desktop/betboardtest-firebase-adminsdk-fbsvc-385950fbce.json"

# Initialize Firebase (local vs Cloud Functions)
if not firebase_admin._apps:
    if os.path.exists(FIREBASE_CREDENTIALS_PATH):
        # Local: Use service account file
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred, {
            "storageBucket": "betboardtest.firebasestorage.app"  # <-- use your real bucket
        })
    else:
        # Cloud Functions / Cloud Run: Use default credentials
        firebase_admin.initialize_app()

# Define D1 schools (slugs used on Sports-Reference)
d1_teams = {
    "ACC": ["duke", "louisville", "clemson", "wake-forest", "north-carolina", "southern-methodist", "stanford", "georgia-tech", "virginia-tech", "florida-state", "virginia", "notre-dame", "pittsburgh", "syracuse", "california", "north-carolina-state", "boston-college", "miami-fl"],
    "America East": ["bryant", "vermont", "maine", "albany-ny", "binghamton", "massachusetts-lowell", "new-hampshire", "maryland-baltimore-county", "njit"],
    "American": ["memphis", "north-texas", "alabama-birmingham", "tulane", "east-carolina", "florida-atlantic", "temple", "wichita-state", "south-florida", "tulsa", "texas-san-antonio", "rice", "charlotte"],
    "ASUN": ["lipscomb", "north-alabama", "florida-gulf-coast", "jacksonville", "eastern-kentucky", "queens-nc", "north-florida", "austin-peay", "stetson", "central-arkansas", "west-georgia", "bellarmine"],
    "Atlantic 10": ["virginia-commonwealth", "george-mason", "loyola-il", "dayton", "saint-josephs", "saint-louis", "st-bonaventure", "george-washington", "duquesne", "rhode-island", "massachusetts", "davidson", "la-salle", "richmond", "fordham"],
    "SEC": ["auburn", "florida", "alabama", "tennessee", "texas-am", "mississippi", "kentucky", "missouri", "arkansas", "mississippi-state", "georgia", "vanderbilt", "oklahoma", "texas", "louisiana-state", "south-carolina"],
    "Big Ten": ["michigan-state", "maryland", "michigan", "wisconsin", "purdue", "ucla", "illinois", "oregon", "indiana", "ohio-state", "rutgers", "minnesota", "northwestern", "southern-california", "iowa", "nebraska", "penn-state", "washington"],
    "Big 12": ["houston", "texas-tech", "brigham-young", "arizona", "iowa-state", "kansas", "baylor", "west-virginia", "texas-christian", "kansas-state", "utah", "cincinnati", "central-florida", "oklahoma-state", "arizona-state", "colorado"],
    "Big East": ["st-johns-ny", "creighton", "connecticut", "marquette", "xavier", "villanova", "georgetown", "butler", "providence", "depaul", "seton-hall"],
    "West Coast": ["saint-marys-ca", "gonzaga", "san-francisco", "santa-clara", "oregon-state", "washington-state", "loyola-marymount", "portland", "pepperdine", "pacific", "san-diego"],
    "Big Sky": ["northern-colorado", "montana", "portland-state", "idaho-state", "montana-state", "northern-arizona", "idaho", "eastern-washington", "weber-state", "sacramento-state"],
    "Big South": ["high-point", "winthrop", "north-carolina-asheville", "radford", "longwood", "presbyterian", "charleston-southern", "gardner-webb", "south-carolina-upstate"],
    "Big West": ["california-san-diego", "california-irvine", "cal-state-northridge", "california-riverside", "california-santa-barbara", "california-davis", "cal-poly", "cal-state-bakersfield", "hawaii", "long-beach-state", "cal-state-fullerton"],
    "CAA": ["towson", "north-carolina-wilmington", "college-of-charleston", "william-mary", "campbell", "monmouth", "drexel", "northeastern", "elon", "hampton", "hofstra", "delaware", "stony-brook", "north-carolina-at"],
    "CUSA": ["liberty", "middle-tennessee", "jacksonville-state", "kennesaw-state", "new-mexico-state", "louisiana-tech", "western-kentucky", "texas-el-paso", "sam-houston-state", "florida-international"],
    "Horizon": ["robert-morris", "milwaukee", "cleveland-state", "youngstown-state", "ipfw", "northern-kentucky", "oakland", "wright-state", "iupui", "detroit-mercy", "green-bay"],
    "Ivy League": ["yale", "cornell", "princeton", "dartmouth", "harvard", "brown", "pennsylvania", "columbia"],
    "MAAC": ["quinnipiac", "merrimack", "marist", "mount-st-marys", "manhattan", "iona", "sacred-heart", "siena", "rider", "fairfield", "saint-peters", "niagara", "canisius"],
    "MAC": ["akron", "miami-oh", "kent-state", "toledo", "ohio", "eastern-michigan", "bowling-green-state", "central-michigan", "ball-state", "buffalo", "northern-illinois"],
    "MEAC": ["norfolk-state", "south-carolina-state", "delaware-state", "morgan-state", "howard", "north-carolina-central", "coppin-state", "maryland-eastern-shore"],
    "Mountain West": ["new-mexico", "colorado-state", "utah-state", "boise-state", "san-diego-state", "nevada-las-vegas", "nevada", "san-jose-state", "wyoming", "fresno-state", "air-force"],
    "MVC": ["drake", "bradley", "northern-iowa", "belmont", "illinois-state", "illinois-chicago", "murray-state", "indiana-state", "southern-illinois", "evansville", "valparaiso", "missouri-state"],
    "NEC": ["central-connecticut-state", "long-island-university", "mercyhurst", "saint-francis-pa", "fairleigh-dickinson", "stonehill", "wagner", "le-moyne", "chicago-state"],
    "OVC": ["southeast-missouri-state", "southern-illinois-edwardsville", "arkansas-little-rock", "tennessee-state", "lindenwood", "tennessee-state", "morehead-state", "tennessee-martin", "eastern-illinois", "western-illinois", "southern-indiana"],
    "Patriot": ["american", "bucknell", "army", "boston-university", "navy", "colgate", "lafayette", "loyola-md", "lehigh", "holy-cross"],
    "SoCon": ["chattanooga", "north-carolina-greensboro", "samford", "east-tennessee-state", "furman", "wofford", "virginia-military-institute", "mercer", "western-carolina", "citadel"],
    "Southland": ["mcneese-state", "lamar", "nicholls-state", "texas-am-corpus-christi", "southeastern-louisiana", "northwestern-state", "incarnate-word", "houston-baptist", "texas-pan-american", "stephen-f-austin", "texas-am-commerce", "new-orleans"],
    "Summit League": ["nebraska-omaha", "st-thomas-mn", "south-dakota-state", "north-dakota-state", "south-dakota", "north-dakota", "denver", "missouri-kansas-city", "oral-roberts"],
    "Sun Belt": ["arkansas-state", "troy", "south-alabama", "james-madison", "marshall", "appalachian-state", "texas-state", "georgia-southern", "old-dominion", "georgia-state", "louisiana-lafayette", "southern-mississippi", "coastal-carolina", "louisiana-monroe"],
    "SWAC": ["southern", "jackson-state", "bethune-cookman", "alabama-state", "texas-southern", "alcorn-state", "florida-am", "grambling", "alabama-am", "prairie-view", "arkansas-pine-bluff", "mississippi-valley-state"],
    "WAC": ["utah-valley", "grand-canyon", "california-baptist", "abilene-christian", "seattle", "tarleton-state", "texas-arlington", "southern-utah", "dixie-state"]
}

def clean_table(df: pd.DataFrame) -> pd.DataFrame:
    # Drop fully empty rows
    df = df.dropna(how="all")

    # Remove repeated header rows inside the body (where Rk == "Rk")
    if "Rk" in df.columns:
        df = df[df["Rk"] != "Rk"]

    # Flatten MultiIndex column headers if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[1] if col[1] != "" else col[0] for col in df.columns]

    # Ensure all column names are unique (important for concat)
    new_cols = []
    seen = {}
    for c in df.columns:
        c_str = str(c)
        if c_str in seen:
            seen[c_str] += 1
            new_cols.append(f"{c_str}_{seen[c_str]}")
        else:
            seen[c_str] = 0
            new_cols.append(c_str)
    df.columns = new_cols

    # Strip whitespace from string columns only (no applymap warning)
    obj_cols = df.select_dtypes(include="object").columns
    df[obj_cols] = df[obj_cols].apply(lambda col: col.str.strip())

    # Drop 'Rk' column if you don't want it
    if "Rk" in df.columns:
        df = df.drop(columns=["Rk"])

    return df

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Referer": "https://www.google.com/"})

def fetch_with_retry(url, max_retries=5):
    """Fetch a URL with retry logic; waits 5 minutes if rate limited (429)."""
    for attempt in range(max_retries):
        resp = session.get(url)

        if resp.status_code == 429:
            wait = 300  # 5 minutes
            print(f" Rate limited (429) on {url}. Waiting {wait}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait)
            continue

        if resp.status_code >= 500:
            wait = 10 * (attempt + 1)
            print(f" Server error {resp.status_code} on {url}. Waiting {wait}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait)
            continue

        return resp

    print(f" Giving up on {url} after {max_retries} retries.")
    return resp

all_logs = []

for conf, teams in d1_teams.items():
    print(f"\nScraping conference: {conf}")
    
    for team in teams:
        print(f"Scraping {team}...")
        url = f"https://www.sports-reference.com/cbb/schools/{team}/men/2026-gamelogs.html"

        # use retry-aware fetch instead of raw requests.get
        resp = fetch_with_retry(url)

        if resp.status_code != 200:
            print(f" Skipped {team}, status {resp.status_code}")
            continue
        
        soup = BeautifulSoup(resp.text, "html.parser")
        # Find the game log table
        table = soup.find("table", {"id": "team_game_log"})
        
        if table:
            df = pd.read_html(StringIO(str(table)), flavor="lxml")[0]
            df = clean_table(df)
            # Add identifying columns
            df.insert(0, "Team", team)
            df.insert(1, "Conference", conf)
            all_logs.append(df)
            print(f"    Added {team}")
        else:
            print(f"    No game log table found for {team}")
        
        # still keep a small polite delay between teams
        time.sleep(2)

# Combine all teams into one DataFrame
if all_logs:
    combined_df = pd.concat(all_logs, ignore_index=True)
    os.makedirs("output", exist_ok=True)

    # 2) Filter in memory to keep only games from the PREVIOUS day
    try:
        if "Date" not in combined_df.columns:
            print("'Date' column not found; cannot filter by day.")
        else:
            combined_df["Date"] = pd.to_datetime(combined_df["Date"], errors="coerce").dt.date

            # 🔹 yesterday, not today
            target_date = datetime.today().date() - timedelta(days=1)

            before_rows = len(combined_df)
            filtered_df = combined_df[combined_df["Date"] == target_date]
            after_rows = len(filtered_df)

            if after_rows == 0:
                print(f"No games found for {target_date}. Not uploading to Firebase.")
            else:
                date_str = target_date.strftime("%Y%m%d")
                filtered_csv_path = f"raw_data/sports_reference/{target_date}/{target_date}_gamelog.csv"
                filtered_df.to_csv(filtered_csv_path, index=False)
                print(
                    f"Filtered CSV to only games played on {target_date}. "
                    f"Rows before: {before_rows}, after: {after_rows}"
                )
                print(f"Filtered game logs saved to {filtered_csv_path}")

                # ---------- Upload filtered CSV to Firebase Storage ----------
                # assuming you already initialized firebase_admin and have a bucket
                # e.g. at top: bucket = storage.bucket()
                # if not, you can do: bucket = storage.bucket()

                folder_date = target_date.strftime("%Y-%m-%d")
                filename = f"raw_data/sports_reference_gamelogs/{folder_date}/gamelogs.csv"

                print("Uploading to Firebase path:", filename)

                blob = bucket.blob(filename)
                blob.upload_from_filename(filtered_csv_path, content_type="text/csv")
                print(f"📤 Uploaded daily CSV to Firebase at: {filename}")

                # Also update a 'latest' pointer for convenience
                latest_blob = bucket.blob("raw_data/sports_reference_gamelogs/latest.csv")
                latest_blob.upload_from_filename(filtered_csv_path, content_type="text/csv")
                print("📤 Updated latest CSV at: raw_data/sports_reference_gamelogs/latest.csv")

    except Exception as e:
        print(f" Error while filtering/uploading CSV for previous day: {e}")
else:
    print("No data scraped.")
