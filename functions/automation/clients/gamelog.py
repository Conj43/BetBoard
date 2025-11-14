import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import time
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import firebase_admin
from firebase_admin import credentials, storage
from automation.config.config import (
    TEAM_MAPPING as direct_mapping,
    CONFERENCE_MAP as d1_teams,
    SPORTS_REFERENCE_SEASON,
    GAMELOG_STORAGE_PREFIX,
)

# FIREBASE_CREDENTIALS_PATH = "services/firebase/betboardtest-firebase-adminsdk-fbsvc-196904ba56.json"
FIREBASE_STORAGE_BUCKET = "betboardtest.firebasestorage.app"

# Initialize Firebase
if not firebase_admin._apps:
    options = {}
    if FIREBASE_STORAGE_BUCKET:
        options["storageBucket"] = FIREBASE_STORAGE_BUCKET
        
    firebase_admin.initialize_app(options=options or None)

bucket = storage.bucket(name=FIREBASE_STORAGE_BUCKET)


def download_latest_odds():
    """Download the latest odds data from Firebase."""
    print("📥 Downloading latest odds from Firebase...")
    
    blob = bucket.blob("raw_data/odds/latest.json")
    
    if not blob.exists():
        print("❌ No odds data found in Firebase at raw_data/odds/latest.json")
        return None
    
    json_str = blob.download_as_string()
    data = json.loads(json_str)
    
    print(f"✅ Downloaded {data['num_games']} games from {data['scraped_at_formatted']}")
    return data


def map_odds_api_name_to_sr_slug(team_name):
    """
    Map Odds API team names to Sports Reference slugs.
    This is a comprehensive mapping for NCAA basketball teams.
    """
    

    
    # Check direct mapping first
    if team_name in direct_mapping:
        return direct_mapping[team_name]
    
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = team_name.lower()
    slug = slug.replace("'", "")
    slug = slug.replace(".", "")
    slug = slug.replace("&", "")
    slug = slug.replace("  ", " ")
    slug = slug.strip()
    slug = slug.replace(" ", "-")
    
    return slug


def get_teams_playing_today():
    """Get set of Sports Reference slugs for teams playing today from Odds API data."""
    
    odds_data = download_latest_odds()
    
    if not odds_data or not odds_data.get('games'):
        print("❌ No games data available")
        return set()
    
    teams_playing = set()
    today_cst = datetime.now(ZoneInfo("America/Chicago")).date()
    
    print(f"\n{'='*80}")
    print(f"🔍 EXTRACTING TEAMS PLAYING TODAY")
    print(f"{'='*80}\n")
    
    for game in odds_data['games']:
        start_str = game.get("commence_time")
        if start_str:
            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                start_dt = None
        else:
            start_dt = None

        if start_dt and start_dt.date() != today_cst:
            continue
        
        home_team = game['home_team']
        away_team = game['away_team']
        
        home_slug = map_odds_api_name_to_sr_slug(home_team)
        away_slug = map_odds_api_name_to_sr_slug(away_team)
        
        print(f"  {away_team:<45} → {away_slug}")
        print(f"  {home_team:<45} → {home_slug}")
        print()
        
        teams_playing.add(home_slug)
        teams_playing.add(away_slug)
    
    print(f"✅ Found {len(teams_playing)} unique teams playing today\n")
    
    return teams_playing


def clean_table(df: pd.DataFrame) -> pd.DataFrame:
    """Clean scraped table data."""
    df = df.dropna(how="all")
    
    if "Rk" in df.columns:
        df = df[df["Rk"] != "Rk"]
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[1] if col[1] != "" else col[0] for col in df.columns]
    
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
    
    obj_cols = df.select_dtypes(include="object").columns
    df[obj_cols] = df[obj_cols].apply(lambda col: col.str.strip())
    
    if "Rk" in df.columns:
        df = df.drop(columns=["Rk"])
    
    return df


def filter_completed_games(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only rows that contain box score data.
    Sports Reference includes upcoming games as empty rows—those should be dropped.
    """
    stat_cols = [col for col in ["Tm", "Opp", "FG", "FGA"] if col in df.columns]
    if not stat_cols:
        return df

    # Coerce numeric columns so empty strings/whitespace become NaN before filtering
    stat_values = df[stat_cols].apply(pd.to_numeric, errors="coerce")
    has_stats = stat_values.notna().any(axis=1)

    date_mask = pd.Series(True, index=df.index)
    if "Date" in df.columns:
        date_mask = pd.to_datetime(df["Date"], errors="coerce").notna()

    return df[has_stats & date_mask]


session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
})


def fetch_with_retry(url, max_retries=5):
    """Fetch a URL with retry logic."""
    for attempt in range(max_retries):
        resp = session.get(url)
        
        if resp.status_code == 429:
            wait = 300
            print(f"  ⏳ Rate limited. Waiting {wait}s... (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
            continue
        
        if resp.status_code >= 500:
            wait = 10 * (attempt + 1)
            print(f"  ⏳ Server error {resp.status_code}. Waiting {wait}s... (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
            continue
        
        return resp
    
    print(f"  ❌ Giving up after {max_retries} retries")
    return resp




def get_conference_for_team(team_slug):
    """Find which conference a team belongs to."""
    for conf, teams in d1_teams.items():
        if team_slug in teams:
            return conf
    return "Unknown"


def main():
    print(f"\n{'='*80}")
    print(f"🏀 SPORTS REFERENCE SCRAPER - TODAY'S GAMES ONLY")
    print(f"{'='*80}\n")
    
    # Get teams playing today from Odds API data
    teams_playing_today = get_teams_playing_today()
    
    if not teams_playing_today:
        print("❌ No teams to scrape. Exiting.")
        return
    
    print(f"\n{'='*80}")
    print(f"🌐 SCRAPING SPORTS REFERENCE")
    print(f"{'='*80}\n")
    
    scraped_count = 0
    skipped_count = 0
    uploaded_count = 0
    
    for team_slug in sorted(teams_playing_today):
        conference = get_conference_for_team(team_slug)
        
        print(f"🏀 {team_slug} ({conference})")
        
        url = (
            "https://www.sports-reference.com/"
            f"cbb/schools/{team_slug}/men/{SPORTS_REFERENCE_SEASON}-gamelogs.html"
        )
        resp = fetch_with_retry(url)
        
        if resp.status_code != 200:
            print(f"  ❌ Failed (HTTP {resp.status_code})")
            skipped_count += 1
            continue
        
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "team_game_log"})
        
        if table:
            df = pd.read_html(StringIO(str(table)), flavor="lxml")[0]
            df = clean_table(df)
            df = filter_completed_games(df)
            df.insert(0, "Team", team_slug)
            df.insert(1, "Conference", conference)

            if df.empty:
                print("  ⚠️ No completed games with stats yet; skipping upload")
                skipped_count += 1
                continue

            csv_string = df.to_csv(index=False)
            firebase_path = f"{GAMELOG_STORAGE_PREFIX}/{team_slug}/{SPORTS_REFERENCE_SEASON}.csv"
            blob = bucket.blob(firebase_path)
            blob.upload_from_string(csv_string, content_type="text/csv")
            uploaded_count += 1
            scraped_count += 1
            print(f"  📤 Uploaded {len(df)} games → {firebase_path}")
        else:
            print(f"  ⚠️  No game log table found")
            skipped_count += 1
        
        # Polite delay
        time.sleep(5)
    
    print(f"\n{'='*80}")
    print(f"📊 SCRAPING COMPLETE")
    print(f"{'='*80}")
    print(f"  ✅ Successfully scraped: {scraped_count}")
    print(f"  ❌ Skipped/Failed: {skipped_count}")
    print(f"  📤 Uploaded team files: {uploaded_count}")
    print(f"  📋 Total teams considered: {len(teams_playing_today)}")
    print(f"\n✅ All done!")



if __name__ == "__main__":
    main()
