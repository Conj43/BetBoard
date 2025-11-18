import requests
import json
from datetime import datetime
import pytz
import firebase_admin
from firebase_admin import credentials, storage

# ============ CONFIGURATION ============
API_KEY = '1c6427df57a26416824684d74510ebe7'
BASE_URL = 'https://api.the-odds-api.com/v4'

FIREBASE_STORAGE_BUCKET = "betboardtest.firebasestorage.app"
# FIREBASE_CREDS_PATH = "services/firebase/betboardtest-firebase-adminsdk-fbsvc-196904ba56.json"
# =======================================


def initialize_firebase():
    """Initialize Firebase if not already initialized."""
    if not firebase_admin._apps:
        options = {}
        if FIREBASE_STORAGE_BUCKET:
            options["storageBucket"] = FIREBASE_STORAGE_BUCKET
        
        firebase_admin.initialize_app(options=options or None)
    return storage.bucket()


def save_to_firebase(data, sport_key):
    """Save odds data to Firebase Storage with timestamped + latest objects."""
    bucket = initialize_firebase()
    
    # Get current time in Central
    central = pytz.timezone('US/Central')
    now = datetime.now(central)
    
    latest_path = "raw_data/odds/latest.json"
    dated_path = f"raw_data/odds/{now.strftime('%Y-%m-%d')}/odds.json"
    
    # Prepare data with metadata
    output_data = {
        "scraped_at": now.isoformat(),
        "scraped_at_formatted": now.strftime('%m/%d/%Y %I:%M:%S %p %Z'),
        "sport_key": sport_key,
        "num_games": len(data),
        "games": data
    }
    
    json_str = json.dumps(output_data, indent=2)
    
    blob_latest = bucket.blob(latest_path)
    blob_latest.upload_from_string(json_str, content_type='application/json')
    print(f"✅ Saved latest JSON: {latest_path}")

    dated_blob = bucket.blob(dated_path)
    dated_blob.upload_from_string(json_str, content_type='application/json')
    print(f"✅ Saved dated JSON: {dated_path}")
    
    return latest_path, dated_path


def check_available_sports():
    """Check what sports are currently available."""
    url = f'{BASE_URL}/sports'
    params = {'apiKey': API_KEY}
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        sports = response.json()
        
        print(f"\n{'='*80}")
        print(f"🔍 SEARCHING FOR COLLEGE BASKETBALL")
        print(f"{'='*80}\n")
        
        # Look for college basketball
        cbb_sports = [s for s in sports if 'basketball' in s['key'].lower() and 
                      ('college' in s['title'].lower() or 'ncaa' in s['title'].lower())]
        
        if cbb_sports:
            print(f"✅ FOUND {len(cbb_sports)} COLLEGE BASKETBALL SPORT(S):")
            for sport in cbb_sports:
                status = "🟢 ACTIVE" if sport['active'] else "🔴 INACTIVE"
                print(f"\n  {status}")
                print(f"  Sport Key: {sport['key']}")
                print(f"  Title: {sport['title']}")
                print(f"  Group: {sport['group']}")
                print(f"  Description: {sport.get('description', 'N/A')}")
                print(f"  Has Outrights: {sport.get('has_outrights', False)}")
            
            return cbb_sports
        else:
            print("❌ NO COLLEGE BASKETBALL FOUND")
            print("\n🏀 Basketball sports available:")
            bball_sports = [s for s in sports if 'basketball' in s['key'].lower()]
            for sport in bball_sports:
                print(f"  - {sport['title']} ({sport['key']}) - {'Active' if sport['active'] else 'Inactive'}")
            
            return []
    else:
        print(f"❌ Error fetching sports: {response.status_code}")
        return []


def get_college_basketball_games(sport_key='basketball_ncaab'):
    """Get college basketball games with odds and save to Firebase."""
    url = f'{BASE_URL}/sports/{sport_key}/odds'
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'h2h,spreads,totals',
        'oddsFormat': 'american',
        'dateFormat': 'iso'
    }
    
    print(f"\n{'='*80}")
    print(f"📊 FETCHING ODDS FOR: {sport_key}")
    print(f"{'='*80}\n")
    
    response = requests.get(url, params=params)
    remaining = response.headers.get('x-requests-remaining')
    
    print(f"📈 API requests remaining: {remaining}/500\n")
    
    if response.status_code == 200:
        games = response.json()
        
        if not games:
            print("❌ No games available for this sport right now")
            print("   (This is normal during off-season or between game days)")
            return None
        
        # Convert all times to Central Time and filter for today only
        central = pytz.timezone('US/Central')
        today = datetime.now(central).date()
        
        todays_games = []
        for game in games:
            # Parse UTC time
            utc_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            # Convert to Central
            central_time = utc_time.astimezone(central)
            
            # Check if game is today
            if central_time.date() == today:
                # Save back as ISO string WITHOUT timezone suffix so downstream
                # systems don't append "-06:00" or similar offsets
                game['commence_time'] = central_time.strftime('%Y-%m-%dT%H:%M:%S')
                # Also add a human-readable version
                game['commence_time_formatted'] = central_time.strftime('%m/%d/%Y %I:%M %p %Z')
                todays_games.append(game)
        
        games = todays_games
        
        if not games:
            print("❌ No games scheduled for today")
            return None
        
        print(f"✅ FOUND {len(games)} GAMES TODAY\n")
        print(f"{'='*80}")
        print(f"📋 GAME SCHEDULE (Central Time)")
        print(f"{'='*80}\n")
        
        for idx, game in enumerate(games, 1):
            num_books = len(game['bookmakers'])
            
            # print(f"[{idx:2d}] {game['away_team']}")
            # print(f"     @ {game['home_team']}")
            # print(f"     🕐 {game['commence_time_formatted']}")
            # print(f"     📖 {num_books} bookmakers")
            # print()
        
        # Save to Firebase
        print(f"\n{'='*80}")
        print(f"💾 SAVING TO FIREBASE")
        print(f"{'='*80}\n")
        
        try:
            latest_path, dated_path = save_to_firebase(games, sport_key)
            print(f"\n✅ Firebase upload complete!")
            print(f"   Latest JSON: gs://{FIREBASE_STORAGE_BUCKET}/{latest_path}")
            print(f"   Daily JSON:  gs://{FIREBASE_STORAGE_BUCKET}/{dated_path}")
        except Exception as e:
            print(f"❌ Firebase upload failed: {e}")

        
        # Show sample bookmakers from first game
        if games and games[0]['bookmakers']:
            print(f"\n{'='*80}")
            print(f"📖 BOOKMAKERS AVAILABLE (Sample from first game)")
            print(f"{'='*80}\n")
            
            for book in games[0]['bookmakers']:
                print(f"  ✓ {book['title']}")
        
        # Show sample odds from first game
        if games and games[0]['bookmakers']:
            print(f"\n{'='*80}")
            print(f"💰 SAMPLE ODDS")
            print(f"{'='*80}")
            print(f"\n🏀 {games[0]['away_team']} @ {games[0]['home_team']}\n")
            
            book = games[0]['bookmakers'][0]
            print(f"📖 {book['title']}:\n")
            
            for market in book['markets']:
                if market['key'] == 'h2h':
                    print(f"  💰 Moneyline:")
                    for outcome in market['outcomes']:
                        print(f"     {outcome['name']:<40s}: {outcome['price']:>6}")
                elif market['key'] == 'spreads':
                    print(f"\n  📊 Spread:")
                    for outcome in market['outcomes']:
                        print(f"     {outcome['name']:<40s}: {outcome['point']:>6.1f} @ {outcome['price']:>6}")
                elif market['key'] == 'totals':
                    print(f"\n  🎯 Total:")
                    for outcome in market['outcomes']:
                        print(f"     {outcome['name']:<40s}: {outcome['point']:>6.1f} @ {outcome['price']:>6}")
        
        # Statistics
        total_bookmakers = sum(len(game['bookmakers']) for game in games)
        
        print(f"\n{'='*80}")
        print(f"📈 STATISTICS")
        print(f"{'='*80}")
        print(f"  Total games: {len(games)}")
        print(f"  Total bookmaker entries: {total_bookmakers}")
        print(f"  Average bookmakers per game: {total_bookmakers/len(games):.1f}")
        print(f"  Cost: 1 API request")
        print(f"  Remaining requests: {remaining}/500")
        
        return games
    
    elif response.status_code == 404:
        print(f"❌ Sport '{sport_key}' not found or no odds available")
        return None
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None


def main():
    print(f"\n{'='*80}")
    print(f"🏀 COLLEGE BASKETBALL ODDS CHECKER → FIREBASE")
    print(f"{'='*80}")
    
    # Step 1: Check what college basketball sports are available
    cbb_sports = check_available_sports()
    
    if not cbb_sports:
        print("\n⚠️ No college basketball sports found!")
        print("   Try these sport keys manually:")
        print("   - basketball_ncaab (NCAA Men's)")
        print("   - basketball_ncaaw (NCAA Women's)")
        
        # Try anyway
        print("\n🔄 Trying basketball_ncaab anyway...")
        games = get_college_basketball_games('basketball_ncaab')
        
        # if not games:
        #     print("\n🔄 Trying basketball_ncaaw...")
        #     games = get_college_basketball_games('basketball_ncaaw')
    else:
        # Try each active college basketball sport
        for sport in cbb_sports:
            if sport['active']:
                games = get_college_basketball_games(sport['key'])
                
                if games:
                    break  # Found games, stop looking
    
    print(f"\n{'='*80}")
    print(f"✅ CHECK COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
