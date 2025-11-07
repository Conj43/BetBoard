import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import time
import json
import os
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, storage
from config import TEAM_MAPPING as direct_mapping
from config import CONFERENCE_MAP as d1_teams

FIREBASE_CREDENTIALS_PATH = "services/firebase/betboardtest-firebase-adminsdk-fbsvc-196904ba56.json"
FIREBASE_STORAGE_BUCKET = "betboardtest.firebasestorage.app"

# Initialize Firebase
if not firebase_admin._apps:
    if os.path.exists(FIREBASE_CREDENTIALS_PATH):
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred, {
            "storageBucket": FIREBASE_STORAGE_BUCKET
        })
    else:
        firebase_admin.initialize_app()

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
    
    print(f"\n{'='*80}")
    print(f"🔍 EXTRACTING TEAMS PLAYING TODAY")
    print(f"{'='*80}\n")
    
    for game in odds_data['games']:
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
    
    all_logs = []
    scraped_count = 0
    skipped_count = 0
    
    for team_slug in sorted(teams_playing_today):
        conference = get_conference_for_team(team_slug)
        
        print(f"🏀 {team_slug} ({conference})")
        
        url = f"https://www.sports-reference.com/cbb/schools/{team_slug}/men/2026-gamelogs.html"
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
            df.insert(0, "Team", team_slug)
            df.insert(1, "Conference", conference)
            all_logs.append(df)
            scraped_count += 1
            print(f"  ✅ Scraped successfully")
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
    print(f"  📋 Total teams: {len(teams_playing_today)}")
    
    # Save results
    if all_logs:
        combined_df = pd.concat(all_logs, ignore_index=True)
        csv_string = combined_df.to_csv(index=False)
        target_date = datetime.now().strftime("%Y-%m-%d")
        # os.makedirs(f"raw_data/gamelogs/{target_date}", exist_ok=True)
        # local_path = f"raw_data/gamelogs/{target_date}/{target_date}_gamelog.csv"
        # combined_df.to_csv(local_path, index=False)
        
    
        firebase_path = f"raw_data/gamelogs/{target_date}/gamelogs.csv"
        
        blob = bucket.blob(firebase_path)
        blob.upload_from_string(csv_string, content_type="text/csv")
        print(f"  📤 Firebase: gs://{FIREBASE_STORAGE_BUCKET}/{firebase_path}")
        
        # Update latest
        latest_blob = bucket.blob("raw_data/gamelogs/latest.csv")
        latest_blob.upload_from_string(csv_string, content_type="text/csv")
        print(f"  📤 Latest: gs://{FIREBASE_STORAGE_BUCKET}/raw_data/gamelogs/latest.csv")
        
        print(f"\n✅ All done!")



if __name__ == "__main__":
    main()