import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import time
import random
import os

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

def clean_table(df):
    # Drop fully empty rows
    df = df.dropna(how="all")

    # Remove repeated header rows (only keep the first one)
    if "Rk" in df.columns:
        df = df[df["Rk"] != "Rk"]

    # Flatten multi-index headers if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[1] if col[1] != "" else col[0] for col in df.columns]

    # Strip whitespace
    df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)

    # Drop the "Rk" column if you don’t want it in the final CSV
    if "Rk" in df.columns:
        df = df.drop(columns=["Rk"])

    return df

all_logs = []

for conf, teams in d1_teams.items():
    print(f"\nScraping conference: {conf}")
    
    for team in teams:
        print(f"Scraping {team}...")
        url = f"https://www.sports-reference.com/cbb/schools/{team}/men/2021-gamelogs.html"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers)
        
        if resp.status_code != 200:
            print(f"Skipped {team}, status {resp.status_code}")
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
            print(f"Added {team}")
        else:
            print(f"No game log table found for {team}")
        
        time.sleep(random.uniform(1, 2))  # polite delay

# Combine all teams into one DataFrame
if all_logs:
    combined_df = pd.concat(all_logs, ignore_index=True)
    os.makedirs("output", exist_ok=True)
    combined_df.to_csv("output/d1_mens_basketball_2021_gamelogs.csv", index=False)
    print("\nAll game logs saved to output/d1_mens_basketball_2021_gamelogs.csv")
else:
    print("No data scraped.")