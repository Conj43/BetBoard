import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import pandas as pd

# --- CONFIG IMPORTS ---------------------------------------------------------
try:
    from config import RAW_DATA_DIR
except ImportError:
    RAW_DATA_DIR = "data/raw"


# --- UTILS / NORMALIZATION --------------------------------------------------
def normalize_team_key(name: str) -> str:
    """
    Convert 'Missouri', 'Mizzou', 'MISSOURI' etc. into a single canonical key.
    TODO: replace with your real normalization logic from utils.py
    """
    if not isinstance(name, str):
        return ""
    key = name.upper().strip()
    # TODO: apply any alias maps, e.g. {"MIZZOU": "MISSOURI"}
    return key


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def make_game_id(game_date: str, home_key: str, away_key: str) -> str:
    """
    Stable identifier for a matchup.
    You MUST always generate this the same way everywhere.
    """
    return f"{game_date}_{home_key}_{away_key}"


# --- DATA SOURCE PLACEHOLDERS ----------------------------------------------
# These are the 3 things you'll eventually need to hook up to real scrapers/APIs.


def fetch_schedule_for_date(game_date: str) -> pd.DataFrame:
    """
    Return one row per game on `game_date`.

    Expected columns in the returned DataFrame:
    - date (YYYY-MM-DD string)
    - tipoff_datetime (ISO8601 string w/ offset or UTC 'Z')
    - home_team_name (string human readable)
    - away_team_name (string human readable)
    - location_type ("Home" | "Away" | "Neutral" from home team POV or game POV)
    - home_conf (optional)
    - away_conf (optional)

    TODO: Implement using your schedule source. This is currently a stub.
    """
    # TEMP MOCK EXAMPLE:
    data = [
        {
            "date": game_date,
            "tipoff_datetime": f"{game_date}T19:00:00-05:00",  # TODO real tipoff
            "home_team_name": "Missouri",
            "away_team_name": "Kentucky",
            "location_type": "Home",  # or "Neutral"
            "home_conf": "SEC",
            "away_conf": "SEC",
        }
    ]
    return pd.DataFrame(data)


def fetch_team_snapshot(team_key: str, as_of_date: str) -> Dict[str, Any]:
    """
    Get raw team-level state for this team as of RIGHT NOW.

    This is where you will eventually:
    - read TorvikScript.R output
    - pull rolling season stats from Sports-Reference or similar
    - maybe compute simple season-to-date aggregates

    This should return raw stats, not fully engineered features.
    We'll save these directly (so we can re-engineer features later).

    Required keys:
    - "team_key"
    - any numeric fields you want downstream (off_eff, def_eff, tempo, etc.)

    TODO: Replace body with actual data loader(s) in data_loaders.py,
    or merge multiple sources into one dict.
    """
    # TEMP MOCK EXAMPLE:
    return {
        "team_key": team_key,
        "games_played": 3,
        "off_efficiency": 112.4,
        "def_efficiency": 98.7,
        "tempo": 70.3,
        "off_reb_rate": 31.2,
        "def_reb_rate": 74.5,
        "tov_rate": 17.8,
        "ft_rate": 29.1,
        # add anything else you normally pull
    }


def fetch_odds_for_game(game_row: pd.Series) -> Dict[str, Any]:
    """
    Get current sportsbook line(s) for this specific game.

    Input: one row from games_df containing at least:
      - game_id
      - home_team_key
      - away_team_key
      - tipoff_datetime
      - date

    Return:
      - spread_home (float, e.g. -2.5 meaning home favored by 2.5)
      - total (float, e.g. 148.5)
      - moneyline_home (int, e.g. -135)
      - moneyline_away (int, e.g. +115)
      - sportsbook (str)
      - NOTE: if a line doesn't exist yet (like 5 days out), return None.

    TODO: hook up to TheOddsAPI / your odds scraper.
    """
    # TEMP MOCK EXAMPLE:
    return {
        "spread_home": -2.5,
        "total": 148.5,
        "moneyline_home": -135,
        "moneyline_away": 115,
        "sportsbook": "DraftKings",
    }


# --- CORE LOGIC -------------------------------------------------------------

def ingest_raw_for_date(game_date: str, now_iso: str) -> None:
    """
    For a single date:
    1. Get the slate of games.
    2. Normalize team keys, assign game_id.
    3. Snapshot teams (unique teams in the slate).
    4. Snapshot odds per game.
    5. Write CSVs to data/raw/<DATE>/

    We don't do any feature engineering or predictions here.
    """

    # 1. schedule
    games_df = fetch_schedule_for_date(game_date)

    # 2. normalize + assign keys
    games_df["home_team_key"] = games_df["home_team_name"].apply(normalize_team_key)
    games_df["away_team_key"] = games_df["away_team_name"].apply(normalize_team_key)

    games_df["game_id"] = games_df.apply(
        lambda r: make_game_id(r["date"], r["home_team_key"], r["away_team_key"]),
        axis=1
    )

    # 3. team snapshots
    unique_teams = sorted(
        set(games_df["home_team_key"].tolist() + games_df["away_team_key"].tolist())
    )

    team_records = []
    for team_key in unique_teams:
        team_raw = fetch_team_snapshot(team_key, as_of_date=game_date)
        team_raw["team_key"] = team_key  # ensure present
        team_raw["as_of_date"] = game_date
        team_raw["retrieved_at"] = now_iso
        team_records.append(team_raw)

    team_df = pd.DataFrame(team_records)

    # 4. odds snapshots
    odds_records = []
    for _, g in games_df.iterrows():
        odds_raw = fetch_odds_for_game(g)

        odds_record = {
            "game_id": g["game_id"],
            "date": g["date"],
            "tipoff_datetime": g["tipoff_datetime"],
            "home_team_key": g["home_team_key"],
            "away_team_key": g["away_team_key"],
            "spread_home": odds_raw.get("spread_home"),
            "total": odds_raw.get("total"),
            "moneyline_home": odds_raw.get("moneyline_home"),
            "moneyline_away": odds_raw.get("moneyline_away"),
            "sportsbook": odds_raw.get("sportsbook"),
            "retrieved_at": now_iso,
        }

        odds_records.append(odds_record)

    odds_df = pd.DataFrame(odds_records)

    # 5. write out
    out_dir = os.path.join(RAW_DATA_DIR, game_date)
    ensure_dir(out_dir)

    # You now get repeatable daily snapshots:
    games_path = os.path.join(out_dir, f"{game_date}_games.csv")
    teams_path = os.path.join(out_dir, f"{game_date}_teams.csv")
    odds_path = os.path.join(out_dir, f"{game_date}_odds.csv")

    games_df.to_csv(games_path, index=False)
    team_df.to_csv(teams_path, index=False)
    odds_df.to_csv(odds_path, index=False)

    print(f"[ingest_raw] {game_date}: wrote {games_path}")
    print(f"[ingest_raw] {game_date}: wrote {teams_path}")
    print(f"[ingest_raw] {game_date}: wrote {odds_path}")


def daterange(start_date: datetime, end_date: datetime) -> List[str]:
    """
    Inclusive date range helper.
    Returns list of YYYY-MM-DD strings from start_date through end_date.
    """
    days = []
    cur = start_date
    while cur <= end_date:
        days.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return days


def ingest_raw_for_range(start_date: str, end_date: str) -> None:
    """
    Driver for multi-day ingest.
    Example: today through today+7.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    for d in daterange(start_dt, end_dt):
        try:
            ingest_raw_for_date(d, now_iso=now_iso)
        except Exception as e:
            # TODO: you may want better logging / alerts in production
            print(f"[ingest_raw][ERROR] failed {d}: {e}")


if __name__ == "__main__":
    # Default behavior: run for today only.
    # Later, when you want a 7-day lookahead, you can change this main block
    # OR call ingest_raw_for_range from Cloud Scheduler with args.

    today = datetime.now().strftime("%Y-%m-%d")
    # For one day:
    ingest_raw_for_range(start_date=today, end_date=today)

    # For 7-day window (uncomment when you're ready for lookahead):
    # seven_days_out = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    # ingest_raw_for_range(start_date=today, end_date=seven_days_out)