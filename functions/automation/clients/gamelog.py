import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import time
import json
import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

# Configure basic logging output
logging.basicConfig(level=logging.INFO)

import firebase_admin
from firebase_admin import credentials, storage
from automation.config.config import (
    TEAM_MAPPING as direct_mapping,
    CONFERENCE_MAP as d1_teams,
    SPORTS_REFERENCE_SEASON,
    GAMELOG_STORAGE_PREFIX,
)

FIREBASE_STORAGE_BUCKET = "betboardtest.firebasestorage.app"

# Initialize Firebase
if not firebase_admin._apps:
    options = {}
    if FIREBASE_STORAGE_BUCKET:
        options["storageBucket"] = FIREBASE_STORAGE_BUCKET
        
    firebase_admin.initialize_app(options=options or None)

bucket = storage.bucket(name=FIREBASE_STORAGE_BUCKET)

# User agent rotation to avoid detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

# --- HELPER FUNCTIONS ---

def download_latest_odds():
    """Download the latest odds data from Firebase."""
    logging.info("📥 Downloading latest odds from Firebase...")
    blob = bucket.blob("raw_data/odds/latest.json")
    if not blob.exists():
        logging.warning("❌ No odds data found.")
        return None
    json_str = blob.download_as_string()
    data = json.loads(json_str)
    logging.info(f"✅ Downloaded {data['num_games']} games")
    return data

def map_odds_api_name_to_sr_slug(team_name):
    if team_name in direct_mapping: return direct_mapping[team_name]
    slug = team_name.lower().replace("'", "").replace(".", "").replace("&", "").replace("  ", " ").strip().replace(" ", "-")
    return slug

def get_teams_playing_today():
    odds_data = download_latest_odds()
    if not odds_data or not odds_data.get('games'): return set()
    
    teams_playing = set()
    today_cst = datetime.now(ZoneInfo("America/Chicago")).date()
    
    logging.info(f"🔍 EXTRACTING TEAMS PLAYING TODAY...")
    
    for game in odds_data['games']:
        start_str = game.get("commence_time")
        if start_str:
            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
                if start_dt.date() != today_cst: continue
            except ValueError: continue
        
        teams_playing.add(map_odds_api_name_to_sr_slug(game['home_team']))
        teams_playing.add(map_odds_api_name_to_sr_slug(game['away_team']))
    
    logging.info(f"✅ Found {len(teams_playing)} unique teams playing today\n")
    return teams_playing

def clean_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all")
    if "Rk" in df.columns: df = df[df["Rk"] != "Rk"]
    if isinstance(df.columns, pd.MultiIndex): df.columns = [col[1] if col[1] != "" else col[0] for col in df.columns]
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
    if "Rk" in df.columns: df = df.drop(columns=["Rk"])
    return df

def filter_completed_games(df: pd.DataFrame) -> pd.DataFrame:
    stat_cols = [col for col in ["Tm", "Opp", "FG", "FGA"] if col in df.columns]
    if not stat_cols: return df
    stat_values = df[stat_cols].apply(pd.to_numeric, errors="coerce")
    has_stats = stat_values.notna().any(axis=1)
    date_mask = pd.Series(True, index=df.index)
    if "Date" in df.columns: date_mask = pd.to_datetime(df["Date"], errors="coerce").notna()
    return df[has_stats & date_mask]

def get_conference_for_team(team_slug):
    for conf, teams in d1_teams.items():
        if team_slug in teams: return conf
    return "Unknown"

# --- SYNCHRONOUS LOGIC ---

def fetch_with_retry(url, max_retries=3):
    """Fetch with exponential backoff and rotating user agents."""
    for attempt in range(max_retries):
        # Rotate user agent on each attempt
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 429:
                wait = 60
                logging.warning(f"  ⏳ Rate limited (429). Waiting {wait}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            
            if response.status_code == 403:
                wait = 30 * (attempt + 1)
                logging.warning(f"  ⏳ Blocked (403). Waiting {wait}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            
            if response.status_code >= 500:
                wait = 2 * (attempt + 1)
                logging.warning(f"  ⏳ Server error {response.status_code}. Waiting {wait}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            
            if response.status_code == 200:
                return response.text
            
            logging.error(f"  ❌ Failed with status {response.status_code}. URL: {url}")
            return None
            
        except Exception as e:
            logging.error(f"  ❌ Network Error: {e}. Waiting 2s.")
            time.sleep(2)
    
    logging.error(f"  ❌ Giving up after {max_retries} retries for URL: {url}")
    return None

def process_team(team_slug):
    """Process a single team."""
    conference = get_conference_for_team(team_slug)
    url = f"https://www.sports-reference.com/cbb/schools/{team_slug}/men/{SPORTS_REFERENCE_SEASON}-gamelogs.html"
    
    html = fetch_with_retry(url)
    
    if not html:
        logging.error(f"  ❌ {team_slug}: Failed to fetch HTML content.")
        return False 

    try:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"id": "team_game_log"})
        
        if table is not None:
            df = pd.read_html(StringIO(str(table)), flavor="lxml")[0]
            df = clean_table(df)
            df = filter_completed_games(df)
            df.insert(0, "Team", team_slug)
            df.insert(1, "Conference", conference)

            if df.empty:
                logging.warning(f"  ⚠️ {team_slug}: No completed games/stats found; skipping upload.")
                return False

            csv_string = df.to_csv(index=False)
            firebase_path = f"{GAMELOG_STORAGE_PREFIX}/{team_slug}/{SPORTS_REFERENCE_SEASON}.csv"
            
            blob = bucket.blob(firebase_path)
            blob.upload_from_string(csv_string, content_type="text/csv")
            
            logging.info(f"  📤 {team_slug}: Uploaded {len(df)} games successfully.")
            return True
        else:
            logging.warning(f"  ⚠️ {team_slug}: No game log table found on page.")
            return False
    
    except Exception as e:
        logging.error(f"  ❌ {team_slug}: CRITICAL PARSING ERROR.", exc_info=True)
        return False

def main():
    logging.info(f"\n{'='*80}")
    logging.info(f"🏀 SPORTS REFERENCE SCRAPER")
    logging.info(f"{'='*80}\n")
    
    teams_playing_today = list(get_teams_playing_today())
    if not teams_playing_today:
        logging.error("❌ No teams to scrape. Exiting.")
        return

    results = []
    for i, team in enumerate(teams_playing_today):
        # Add delay between requests (except before first one)
        if i > 0:
            delay = random.uniform(3.0, 6.0)
            logging.info(f"  ⏳ Waiting {delay:.1f}s before next request...")
            time.sleep(delay)
        
        result = process_team(team)
        results.append(result)

    success_count = sum(results)
    logging.info(f"\n{'='*80}")
    logging.info(f"✅ Finished. Successfully scraped {success_count}/{len(teams_playing_today)} teams.")
    logging.info(f"{'='*80}")

def main_entry_point():
    """Cloud Function Entry Point"""
    main()
    return "Done"

if __name__ == "__main__":
    main()