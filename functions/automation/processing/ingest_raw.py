import json
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

try:
    import firebase_admin
    from firebase_admin import credentials, storage
except ImportError:  # pragma: no cover - optional dependency
    firebase_admin = None  # type: ignore
    credentials = None  # type: ignore
    storage = None  # type: ignore

# --- CONFIG IMPORTS ---------------------------------------------------------

from automation.config.config import (
    FIREBASE_CREDENTIALS_PATH,
    FIREBASE_STORAGE_BUCKET,
    RAW_GAMES_PREFIX,
    RAW_TEAMS_PREFIX,
    RAW_ODDS_PREFIX,
    TEAM_MAPPING,
    CONFERENCE_MAP,
    TORVIK_MAP,
    canonicalize_team_key,
    SPORTS_REFERENCE_SEASON,
    GAMELOG_STORAGE_PREFIX,
)


from os import getenv

from automation.processing.feature_engineering import prepare_rolling
from automation.config.utils import load_alias_map, standardize_opponent_columns


UPLOAD_TO_FIREBASE = getenv("BETBOARD_SKIP_FIREBASE_UPLOAD", "0") != "1"
CENTRAL_TZ = ZoneInfo("America/Chicago")


# --- DATA SOURCE HELPERS ----------------------------------------------------
_ODDS_CACHE: Optional[Dict[str, Any]] = None
_TORVIK_LOOKUP: Optional[Dict[str, Dict[str, float]]] = None
_TEAM_METRICS_CACHE: Dict[str, Dict[str, float]] = {}
_TEAM_METRICS_DATE: Optional[str] = None
_ALIAS_MAP: Optional[Dict[str, str]] = None
_FIREBASE_BUCKET: Optional["storage.bucket"] = None  # Add this cache variable

print(f"[DEBUG] FIREBASE_STORAGE_BUCKET = '{FIREBASE_STORAGE_BUCKET}'")
print(f"[DEBUG] FIREBASE_CREDENTIALS_PATH = '{FIREBASE_CREDENTIALS_PATH}'")

def _get_firebase_bucket(allow_when_upload_disabled: bool = False) -> Optional["storage.bucket"]:
    """
    Lazily initialize and cache the Firebase Storage bucket.
    Returns None if firebase_admin is unavailable or initialization fails.
    """
    global _FIREBASE_BUCKET

    # Return cached bucket if available
    if _FIREBASE_BUCKET is not None:
        return _FIREBASE_BUCKET

    if not UPLOAD_TO_FIREBASE and not allow_when_upload_disabled:
        return None

    if firebase_admin is None or storage is None:
        print("[ingest_raw] firebase_admin not available; skipping upload.")
        return None

    if not FIREBASE_STORAGE_BUCKET:
        print("[ingest_raw] FIREBASE_STORAGE_BUCKET not configured; skipping upload.")
        return None

    try:
        if not firebase_admin._apps:
            options = {}
            if FIREBASE_STORAGE_BUCKET:
                options["storageBucket"] = FIREBASE_STORAGE_BUCKET
            
            firebase_admin.initialize_app(options=options or None)

        _FIREBASE_BUCKET = storage.bucket(name=FIREBASE_STORAGE_BUCKET)
        return _FIREBASE_BUCKET
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"[ingest_raw][WARN] Failed to initialize Firebase Storage: {exc}")
        return None


def _upload_csv_string(csv_content: str, remote_path: str) -> None:
    bucket = _get_firebase_bucket()
    if bucket is None:
        return
    try:
        blob = bucket.blob(remote_path)
        blob.upload_from_string(csv_content, content_type="text/csv")
        print(f"[ingest_raw] Uploaded to gs://{bucket.name}/{remote_path}")
    except Exception as exc:  # pragma: no cover - env dependent
        print(f"[ingest_raw][WARN] Failed to upload CSV to {remote_path}: {exc}")


def upload_snapshots_to_firebase(game_date: str,
                                 games_df: pd.DataFrame,
                                 teams_df: pd.DataFrame,
                                 odds_df: pd.DataFrame) -> None:
    uploads = [
        (odds_df, f"{RAW_ODDS_PREFIX}/latest.csv", f"{RAW_ODDS_PREFIX}/latest.csv"),
    ]

    for df, dated_path, latest_path in uploads:
        csv_content = df.to_csv(index=False)
        _upload_csv_string(csv_content, latest_path)


# --- OPTIONAL GAMELOG RETRIEVAL ---------------------------------------------
def download_gamelogs_snapshot(game_date: str) -> Optional[pd.DataFrame]:
    """
    Load Sports Reference gamelog data for the teams playing on `game_date`.
    Each team stores its season-long log at gamelogs/<team>/<season>.csv.
    """
    bucket = _get_firebase_bucket(allow_when_upload_disabled=True)
    if not bucket:
        return None

    team_slugs = _team_slugs_playing_on_date(game_date)
    if not team_slugs:
        print(f"[ingest_raw][WARN] No teams scheduled for {game_date}; skipping gamelog download.")
        return None

    frames: list[pd.DataFrame] = []
    missing: list[str] = []

    for slug in sorted(team_slugs):
        remote_path = f"{GAMELOG_STORAGE_PREFIX}/{slug}/{SPORTS_REFERENCE_SEASON}.csv"
        blob = bucket.blob(remote_path)
        if not blob.exists():
            missing.append(slug)
            continue
        try:
            csv_text = blob.download_as_text()
            df = pd.read_csv(StringIO(csv_text))
            df["Team"] = df.get("Team", slug)
            frames.append(df)
        except Exception as exc:  # pragma: no cover
            print(f"[ingest_raw][WARN] Failed to download {remote_path}: {exc}")

    if missing:
        print(f"[ingest_raw][WARN] Missing gamelog files for {len(missing)} team(s): {', '.join(missing[:10])}")

    if not frames:
        print(f"[ingest_raw][WARN] No gamelog data available for {game_date}.")
        return None

    combined = pd.concat(frames, ignore_index=True)
    print(f"[ingest_raw] Loaded {combined.shape[0]} gamelog rows across {len(frames)} teams for {game_date}")
    return combined


# --- TEAM METRICS COMPUTATION -----------------------------------------------
def _team_metrics_from_gamelogs(game_date: str) -> Dict[str, Dict[str, float]]:
    raw_logs = download_gamelogs_snapshot(game_date)
    if raw_logs is None:
        return {}

    if raw_logs.empty:
        return {}

    try:
        logs = standardize_opponent_columns(raw_logs)
        
        # Filter out future games with no stats
        logs = logs[logs["Tm"].notna()]
        
        print(f"[DEBUG] After filtering: {len(logs)} games with stats")  # ADD THIS
        
        logs["Date"] = pd.to_datetime(logs["Date"], errors="coerce")
        logs = logs.dropna(subset=["Date", "Team", "Opp"])
        logs = logs.sort_values("Date")
        
        print(f"[DEBUG] After date filtering: {len(logs)} games")  # ADD THIS
        print(f"[DEBUG] Unique teams: {logs['Team'].nunique()}")  # ADD THIS
        print(f"[DEBUG] Date range: {logs['Date'].min()} to {logs['Date'].max()}")  # ADD THIS

        rolling = prepare_rolling(logs)
        
        print(f"[DEBUG] prepare_rolling returned {len(rolling)} rows")  # ADD THIS
        if not rolling.empty:
            print(f"[DEBUG] Rolling columns: {list(rolling.columns)}")  # ADD THIS
        
        if rolling.empty:
            return {}

        rolling = rolling.sort_values(["team_key", "Date"])
        latest = rolling.groupby("team_key").tail(1)

        cache: Dict[str, Dict[str, float]] = {}
        for _, row in latest.iterrows():
            team_key = row["team_key"]
            metrics: Dict[str, float] = {}
            if not pd.isna(row.get("prior_games")):
                metrics["prior_games"] = float(row["prior_games"])

            for col, val in row.items():
                if not isinstance(col, str):
                    continue
                if not (col.startswith("team_") or col.startswith("opp_") or col.startswith("delta")):
                    continue
                if col in {"team_key", "opp_key"}:
                    continue

                value = row[col]
                if pd.isna(value):
                    continue
                if isinstance(value, (int, float, np.integer, np.floating)):
                    metrics[col] = float(value)
                else:
                    try:
                        num_value = float(value)
                        metrics[col] = num_value
                    except (TypeError, ValueError):
                        continue

            if metrics:
                cache[team_key] = metrics

        return cache
    except Exception as exc:  # pragma: no cover
        print(f"[ingest_raw][WARN] Exception computing team metrics from gamelogs: {exc}")
        return {}

def _load_team_metrics(game_date: str) -> Dict[str, Dict[str, float]]:
    global _TEAM_METRICS_CACHE, _TEAM_METRICS_DATE

    if _TEAM_METRICS_DATE == game_date and _TEAM_METRICS_CACHE:
        return _TEAM_METRICS_CACHE

    metrics = _team_metrics_from_gamelogs(game_date)

    if not metrics:
        print(f"[ingest_raw][WARN] Rolling metrics unavailable for {game_date} (likely early season data).")

    _TEAM_METRICS_CACHE = metrics
    _TEAM_METRICS_DATE = game_date
    return _TEAM_METRICS_CACHE


def _slugify_team(name: str) -> str:
    if not isinstance(name, str):
        return ""
    cleaned = "".join(ch for ch in name.lower() if ch.isalnum())
    return cleaned


def _team_slug_from_name(name: str) -> str:
    if not name:
        return ""
    mapped = TEAM_MAPPING.get(name, name)
    return canonicalize_team_key(mapped)


def _team_conference_from_name(name: str) -> Optional[str]:
    team_key = _team_slug_from_name(name)
    for conference, teams in CONFERENCE_MAP.items():
        if team_key in teams:
            return conference
    return None


def _load_latest_odds_data() -> Dict[str, Any]:
    global _ODDS_CACHE
    if _ODDS_CACHE is not None:
        return _ODDS_CACHE

    try:
        bucket = _get_firebase_bucket(allow_when_upload_disabled=True)
        if bucket:
            blob = bucket.blob("raw_data/odds/latest.json")
            if blob.exists():
                raw = blob.download_as_string()
                _ODDS_CACHE = json.loads(raw.decode("utf-8"))
                return _ODDS_CACHE
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"[ingest_raw][WARN] Unable to download odds from Firebase: {exc}")

    print("[ingest_raw][WARN] No odds data available; returning empty schedule.")
    _ODDS_CACHE = {"games": []}
    return _ODDS_CACHE


def _load_torvik_lookup() -> Dict[str, Dict[str, float]]:
    global _TORVIK_LOOKUP
    if _TORVIK_LOOKUP is not None:
        return _TORVIK_LOOKUP

    df = None

    try:
        bucket = _get_firebase_bucket(allow_when_upload_disabled=True)
        if bucket:
            blob = bucket.blob("raw_data/torvik_rankings/latest.csv")
            if blob.exists():
                csv_bytes = blob.download_as_string()
                df = pd.read_csv(StringIO(csv_bytes.decode("utf-8")))
    except Exception as exc:  # pragma: no cover
        print(f"[ingest_raw][WARN] Unable to download Torvik rankings: {exc}")

    lookup: Dict[str, Dict[str, float]] = {}
    if df is not None and not df.empty:
        possible_team_cols = [c for c in df.columns if c.lower() in {"team", "school", "team_name"}]
        team_col = possible_team_cols[0] if possible_team_cols else None
        if team_col:
            for _, row in df.iterrows():
                torvik_team_name = str(row[team_col])
                torvik_team_name = torvik_team_name.replace(" St.", "-state")
                torvik_team_name_clean = torvik_team_name.lower().replace(" ", "")
                # print(f"[DEBUG] Processing Torvik team name: '{torvik_team_name}' -> '{torvik_team_name_clean}'")  # ADD THIS
                # Apply both mappings: torvik_name -> normalized_key
                # First check torvik_map, then torvik_map_two (which overrides)
                team_key = TORVIK_MAP.get(torvik_team_name_clean, torvik_team_name_clean)
                team_key = canonicalize_team_key(team_key)
                if not team_key:
                    team_key = _slugify_team(torvik_team_name)
                # print(f"[DEBUG] Mapped to team key: '{team_key}'")  # ADD THIS
                numeric_values: Dict[str, float] = {}
                for col, val in row.items():
                    if col == team_col:
                        continue
                    num_val = pd.to_numeric(pd.Series([val]), errors="coerce").iloc[0]
                    if pd.notna(num_val):
                        numeric_values[col] = float(num_val)
                if numeric_values:
                    lookup[team_key] = numeric_values

    _TORVIK_LOOKUP = lookup
    return _TORVIK_LOOKUP


# --- UTILS / NORMALIZATION --------------------------------------------------
def normalize_team_key(name: str) -> str:
    """
    Convert 'Missouri', 'Mizzou', 'MISSOURI' etc. into a single canonical key.
    """
    global _ALIAS_MAP
    if not isinstance(name, str):
        return ""

    if _ALIAS_MAP is None:
        try:
            _ALIAS_MAP = load_alias_map()
        except Exception:
            _ALIAS_MAP = {}

    slug = _slugify_team(name)
    canonical = _ALIAS_MAP.get(slug)
    if canonical:
        return canonical
    return canonicalize_team_key(slug)


def make_game_id(game_date: str, home_key: str, away_key: str) -> str:
    """
    Stable identifier for a matchup.
    You MUST always generate this the same way everywhere.
    """
    return f"{game_date}_{home_key}_{away_key}"


# --- DATA SOURCE PLACEHOLDERS ----------------------------------------------

def fetch_schedule_for_date(game_date: str) -> pd.DataFrame:
    """
    Return one row per game on `game_date`.

    Data is derived from the latest Odds API snapshot stored in Firebase.
    """
    odds_payload = _load_latest_odds_data()
    games = odds_payload.get("games", [])
    if not games:
        return pd.DataFrame(columns=[
            "date",
            "tipoff_datetime",
            "home_team_name",
            "away_team_name",
            "location_type",
            "home_conf",
            "away_conf",
            "odds_event_id",
            "odds_sport_key",
        ])

    target_date = datetime.strptime(game_date, "%Y-%m-%d").date()

    rows = []
    for game in games:
        commence = game.get("commence_time")
        if not commence:
            continue
        try:
            tipoff_dt = datetime.fromisoformat(commence)
        except ValueError:
            try:
                tipoff_dt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
            except ValueError:
                tipoff_dt = None
        if tipoff_dt is None or tipoff_dt.date() != target_date:
            continue

        home = game.get("home_team")
        away = game.get("away_team")
        if not home or not away:
            continue

        rows.append({
            "date": game_date,
            "tipoff_datetime": tipoff_dt.isoformat(),
            "home_team_name": home,
            "away_team_name": away,
            "location_type": "Home",
            "home_conf": _team_conference_from_name(home),
            "away_conf": _team_conference_from_name(away),
            "odds_event_id": game.get("id"),
            "odds_sport_key": odds_payload.get("sport_key"),
        })

    if not rows:
        print(f"[ingest_raw][WARN] No games found in odds feed for {game_date}.")
        return pd.DataFrame(columns=[
            "date",
            "tipoff_datetime",
            "home_team_name",
            "away_team_name",
            "location_type",
            "home_conf",
            "away_conf",
            "odds_event_id",
            "odds_sport_key",
        ])

    return pd.DataFrame(rows)


def _team_slugs_playing_on_date(game_date: str) -> List[str]:
    """
    Determine which Sports Reference slugs correspond to teams on the card for `game_date`.
    """
    schedule_df = fetch_schedule_for_date(game_date)
    if schedule_df.empty:
        return []

    slugs: set[str] = set()
    for column in ("home_team_name", "away_team_name"):
        for name in schedule_df[column].dropna().unique():
            slug = _team_slug_from_name(name)
            if slug:
                slugs.add(slug)

    return sorted(slugs)


def fetch_team_snapshot(team_key: str, as_of_date: str, team_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get raw team-level state for this team as of RIGHT NOW.

    Pulls the latest Torvik rankings snapshot from Firebase (or local cache)
    and returns numeric metrics for the requested team.
    """
    # slug = _team_slug_from_name(team_name or team_key)
    torvik_lookup = _load_torvik_lookup()
    metrics = torvik_lookup.get(team_key, {})

    team_metrics = _load_team_metrics(as_of_date)
    rolling_stats = team_metrics.get(team_key, {})

    snapshot: Dict[str, Any] = {
        "team_key": team_key,
        "as_of_date": as_of_date,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }

    # Rolling stats (already prefixed with team_)
    for key, value in rolling_stats.items():
        snapshot[key] = value

    # Torvik metrics
    for key, value in metrics.items():
        prefixed = f"team_{key}"
        snapshot[prefixed] = value

    if 'team_adjoe' in snapshot:
        snapshot['team_adj_o'] = snapshot.pop('team_adjoe')
    if 'team_adjde' in snapshot:
        snapshot['team_adj_d'] = snapshot.pop('team_adjde')

    # Convenience flags
    if "team_rank" not in snapshot and "team_rank" in metrics:
        snapshot["team_rank"] = metrics["team_rank"]
    if "prior_games" not in snapshot:
        snapshot["prior_games"] = 0.0

    return snapshot


def fetch_odds_for_game(game_row: pd.Series) -> Dict[str, Any]:
    """
    Get current sportsbook line(s) for this specific game.

    Input: one row from games_df containing at least:
      - odds_event_id (from Odds API)

    Returns betting lines from the first bookmaker that has data.
    """
    odds_payload = _load_latest_odds_data()
    games = odds_payload.get("games", [])
    if not games:
        return {}

    event_id = game_row.get("odds_event_id")
    home_name = game_row.get("home_team_name")
    away_name = game_row.get("away_team_name")

    def canonical(name: str) -> str:
        return name.strip().lower() if isinstance(name, str) else ""

    target_game = None
    for entry in games:
        entry_id = entry.get("id")
        if event_id and entry_id == event_id:
            target_game = entry
            break
        if (not event_id and
                canonical(entry.get("home_team")) == canonical(home_name) and
                canonical(entry.get("away_team")) == canonical(away_name)):
            target_game = entry
            break

    if target_game is None:
        return {}

    spread_home = None
    total = None
    ml_home = None
    ml_away = None
    sportsbook_name = None
    all_bookmakers: Dict[str, Dict[str, Any]] = {}

    primary_captured = False

    for bookmaker in target_game.get("bookmakers", []):
        markets = bookmaker.get("markets", [])
        if not markets:
            continue

        book_key = bookmaker.get("key") or canonical(bookmaker.get("title", ""))
        if not book_key:
            continue

        book_entry: Dict[str, Any] = {
            "bookmaker_key": book_key,
            "bookmaker_title": bookmaker.get("title"),
            "moneyline": {},
            "spread": {},
            "total": {},
        }

        spread_found = False
        total_found = False
        moneyline_found = False

        for market in markets:
            key = market.get("key")
            outcomes = market.get("outcomes", [])
            if key == "spreads" and outcomes:
                for outcome in outcomes:
                    name = canonical(outcome.get("name"))
                    point = outcome.get("point")
                    if point is None:
                        continue
                    price = outcome.get("price")
                    if name == canonical(home_name):
                        spread_home = float(point)
                        spread_found = True
                        book_entry["spread"]["home"] = {
                            "line": float(point),
                            "price": int(price) if price is not None else None,
                        }
                    elif name == canonical(away_name):
                        spread_home = -float(point)
                        spread_found = True
                        book_entry["spread"]["away"] = {
                            "line": float(point),
                            "price": int(price) if price is not None else None,
                        }
            elif key == "totals" and outcomes:
                for outcome in outcomes:
                    point = outcome.get("point")
                    if point is not None:
                        total = float(point)
                        total_found = True
                        label = outcome.get("name", "").strip().lower()
                        price = outcome.get("price")
                        target = {
                            "line": float(point),
                            "price": int(price) if price is not None else None,
                        }
                        if "over" in label:
                            book_entry["total"]["over"] = target
                        elif "under" in label:
                            book_entry["total"]["under"] = target
            elif key in {"h2h", "moneyline"} and outcomes:
                for outcome in outcomes:
                    name = canonical(outcome.get("name"))
                    price = outcome.get("price")
                    if price is None:
                        continue
                    if name == canonical(home_name):
                        ml_home = int(price)
                        moneyline_found = True
                        book_entry["moneyline"]["home"] = int(price)
                    elif name == canonical(away_name):
                        ml_away = int(price)
                        moneyline_found = True
                        book_entry["moneyline"]["away"] = int(price)

        if spread_found or total_found or moneyline_found:
            if not primary_captured:
                sportsbook_name = bookmaker.get("title") or bookmaker.get("key")
                primary_captured = True

        if book_entry["moneyline"] or book_entry["spread"] or book_entry["total"]:
            all_bookmakers[book_key] = book_entry

    return {
        "spread_home": spread_home,
        "total": total,
        "moneyline_home": ml_home,
        "moneyline_away": ml_away,
        "bookmakers": all_bookmakers,
        "sportsbook": sportsbook_name,
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
    if games_df.empty:
        print(f"[ingest_raw] {game_date}: no scheduled games found; skipping.")
        return

    # 2. normalize + assign keys
    games_df["home_team_key"] = games_df["home_team_name"].apply(normalize_team_key)
    games_df["away_team_key"] = games_df["away_team_name"].apply(normalize_team_key)

    games_df["game_id"] = games_df.apply(
        lambda r: make_game_id(r["date"], r["home_team_key"], r["away_team_key"]),
        axis=1
    )

    team_name_lookup: Dict[str, str] = {}
    for _, row in games_df.iterrows():
        team_name_lookup[row["home_team_key"]] = row["home_team_name"]
        team_name_lookup[row["away_team_key"]] = row["away_team_name"]

    # 3. team snapshots
    unique_teams = sorted(
        set(games_df["home_team_key"].tolist() + games_df["away_team_key"].tolist())
    )

    team_records = []
    for team_key in unique_teams:
        team_raw = fetch_team_snapshot(
            team_key=team_key,
            as_of_date=game_date,
            team_name=team_name_lookup.get(team_key),
        )
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
            "retrieved_at": now_iso,
        }

        bookmakers = odds_raw.get("bookmakers")
        if bookmakers:
            try:
                odds_record["bookmakers_json"] = json.dumps(bookmakers)
            except (TypeError, ValueError):
                pass

        odds_records.append(odds_record)

    odds_df = pd.DataFrame(odds_records)

    if UPLOAD_TO_FIREBASE:
        upload_snapshots_to_firebase(
            game_date=game_date,
            games_df=games_df,
            teams_df=team_df,
            odds_df=odds_df,
        )
    else:
        print("[ingest_raw] Firebase upload disabled (BETBOARD_SKIP_FIREBASE_UPLOAD=1)")


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

    today = datetime.now(CENTRAL_TZ).strftime("%Y-%m-%d")
    # For one day:
    ingest_raw_for_range(start_date=today, end_date=today)

    # For 7-day window (uncomment when you're ready for lookahead):
    # seven_days_out = (datetime.now(CENTRAL_TZ) + timedelta(days=7)).strftime("%Y-%m-%d")
    # ingest_raw_for_range(start_date=today, end_date=seven_days_out)
