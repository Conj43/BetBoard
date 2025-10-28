import os
from datetime import datetime, timedelta
import pandas as pd

try:
    from config import RAW_DATA_DIR, PROCESSED_DATA_DIR
except ImportError:
    RAW_DATA_DIR = "data/raw"
    PROCESSED_DATA_DIR = "data/processed"


# --- You will eventually want this imported from a shared module -------------
# This list should match the columns you actually trained on.
# Right now it's a placeholder. You MUST fill it in to match per_game_2024.csv
# (but only the columns that were used as features, not targets like "final score").
FEATURE_COLS_ORDER = [
    # "Team",
    # "Opp",
    # "Conference",
    # "OppConference",
    # "Location",            # "Home"/"Away"/"Neutral"
    # "Date",
    # "Type",
    # "off_efficiency",
    # "def_efficiency",
    # "tempo",
    # "off_reb_rate",
    # "def_reb_rate",
    # "tov_rate",
    # "opp_off_efficiency",
    # "opp_def_efficiency",
    # "opp_tempo",
    # ...
    # "bet_spread",
    # "bet_total",
    # "moneyline_home",
    # "moneyline_away",
    # etc.
    #
    # TODO: fill this out to EXACT model inputs in training.
    # For now we will build a superset and then select these before saving.
]


def load_raw_day(date_str: str):
    """
    Load the three raw CSVs that ingest_raw.py produced for this date.
    Returns (games_df, teams_df, odds_df)
    """
    day_dir = os.path.join(RAW_DATA_DIR, date_str)

    games_path = os.path.join(day_dir, f"{date_str}_games.csv")
    teams_path = os.path.join(day_dir, f"{date_str}_teams.csv")
    odds_path = os.path.join(day_dir, f"{date_str}_odds.csv")

    games_df = pd.read_csv(games_path)
    teams_df = pd.read_csv(teams_path)
    odds_df = pd.read_csv(odds_path)

    return games_df, teams_df, odds_df


def index_team_stats(teams_df: pd.DataFrame):
    """
    Build a lookup dict keyed by team_key so we can quickly grab that team's snapshot.

    teams_df columns will include at least:
    - team_key
    - off_efficiency
    - def_efficiency
    - tempo
    - etc.
    """
    team_map = {}
    for _, row in teams_df.iterrows():
        key = row["team_key"]
        team_map[key] = row.to_dict()
    return team_map


def build_team_view_row(game_row: pd.Series,
                        team_key: str,
                        opp_key: str,
                        team_stats: dict,
                        opp_stats: dict,
                        odds_row: dict) -> dict:
    """
    Create ONE feature row representing `team_key` playing `opp_key` in this game.

    This is where we mirror the training schema.
    We attach:
        - identifiers (Team, Opp)
        - conference info
        - location from THIS team's perspective
        - team stats snapshot (raw)
        - opponent stats snapshot (prefixed with opp_)
        - sportsbook info for the game
    """

    # Who is this team in human-readable terms?
    # We assume game_row still has `home_team_name`, `away_team_name`.
    if team_key == game_row["home_team_key"]:
        team_name = game_row["home_team_name"]
        opp_name = game_row["away_team_name"]
        location_for_team = "Home" if game_row["location_type"] == "Home" else (
            "Neutral" if game_row["location_type"] == "Neutral" else "Home"
        )
        # ^^^ Explanation: if location_type is "Home", then home team is Home.
        # If it's "Neutral", both teams are Neutral.
        # If it's something else weird like "Away" from home POV, we just treat home as Home,
        # because for CBB it's usually Home/Away/Neutral anyway.
    else:
        team_name = game_row["away_team_name"]
        opp_name = game_row["home_team_name"]
        # If you're the away team:
        if game_row["location_type"] == "Home":
            # Home means from home_team POV, so from away POV it's Away.
            location_for_team = "Away"
        elif game_row["location_type"] == "Neutral":
            location_for_team = "Neutral"
        else:
            # TODO: If you ever store explicit "Away" or "Neutral" differently, handle that here.
            location_for_team = "Away"

    # Conference info for each side, if present
    home_conf = game_row.get("home_conf", None)
    away_conf = game_row.get("away_conf", None)

    if team_key == game_row["home_team_key"]:
        team_conf = home_conf
        opp_conf = away_conf
    else:
        team_conf = away_conf
        opp_conf = home_conf

    # Start assembling the row.
    row = {
        # Identifiers / game context
        "game_id": game_row["game_id"],
        "Date": game_row["date"],
        "tipoff_datetime": game_row.get("tipoff_datetime"),
        "Team": team_name,
        "Opp": opp_name,
        "team_key": team_key,
        "opp_key": opp_key,
        "Conference": team_conf,
        "OppConference": opp_conf,
        "Location": location_for_team,
        # "Type": "REG (Conf)" or similar
        #   TODO: If you classify games (conference game, non-conf, tournament),
        #   you can add it in ingest_raw or infer it here.
        "Type": infer_game_type(team_conf, opp_conf, game_row),
    }

    # Attach team stats snapshot fields directly
    for k, v in team_stats.items():
        if k in ["team_key", "as_of_date", "retrieved_at"]:
            continue
        row[k] = v

    # Attach opponent stats snapshot with prefix
    for k, v in opp_stats.items():
        if k in ["team_key", "as_of_date", "retrieved_at"]:
            continue
        row[f"opp_{k}"] = v

    # Attach odds
    # Note: model training likely assumed bet_spread from the team's POV OR from home POV
    # You HAVE to be consistent with how you trained.
    # For now, we will just attach raw game-level fields and deal with POV later in prediction.
    row["bet_spread_home"] = odds_row.get("spread_home")
    row["bet_total"] = odds_row.get("total")
    row["moneyline_home"] = odds_row.get("moneyline_home")
    row["moneyline_away"] = odds_row.get("moneyline_away")
    row["sportsbook"] = odds_row.get("sportsbook")

    return row


def infer_game_type(team_conf: str, opp_conf: str, game_row: pd.Series) -> str:
    """
    Try to guess the 'Type' column you had in training (ex: "REG (Conf)", "REG (Non-Conf)", "Tourney").

    TODO: make this match your historical data exactly.
    For now:
    - If both conferences match and not None -> 'REG (Conf)'
    - Else -> 'REG (Non-Conf)'
    Later, add logic for neutral-site tournaments, March Madness, etc.
    """
    # You could also look at date / location / known tourneys later.
    if team_conf and opp_conf and team_conf == opp_conf:
        return "REG (Conf)"
    return "REG (Non-Conf)"


def build_features_for_date(date_str: str) -> pd.DataFrame:
    """
    Core driver for a single date:
    - loads raw dfs
    - builds two rows per game
    - returns one big features_df
    - also writes the result to data/processed/<DATE>_features.csv
    """

    games_df, teams_df, odds_df = load_raw_day(date_str)

    # map team_key -> snapshot dict
    team_lookup = index_team_stats(teams_df)

    # map game_id -> odds info dict
    odds_lookup = {
        row["game_id"]: row.to_dict()
        for _, row in odds_df.iterrows()
    }

    feature_rows = []

    for _, game_row in games_df.iterrows():
        game_id = game_row["game_id"]

        # grab odds for this game (may not exist if lines not posted yet)
        odds_row = odds_lookup.get(game_id, {})

        home_key = game_row["home_team_key"]
        away_key = game_row["away_team_key"]

        # lookup raw stats
        home_stats = team_lookup.get(home_key, {})
        away_stats = team_lookup.get(away_key, {})

        # Build "home team vs away team" row
        row_home = build_team_view_row(
            game_row=game_row,
            team_key=home_key,
            opp_key=away_key,
            team_stats=home_stats,
            opp_stats=away_stats,
            odds_row=odds_row
        )
        feature_rows.append(row_home)

        # Build "away team vs home team" row
        row_away = build_team_view_row(
            game_row=game_row,
            team_key=away_key,
            opp_key=home_key,
            team_stats=away_stats,
            opp_stats=home_stats,
            odds_row=odds_row
        )
        feature_rows.append(row_away)

    features_df = pd.DataFrame(feature_rows)

    # IMPORTANT:
    # The model will later expect columns in a specific order and with specific names.
    # So we enforce that here if FEATURE_COLS_ORDER is defined.
    if FEATURE_COLS_ORDER:
        # keep only columns the model knows about, in order
        missing_cols = [c for c in FEATURE_COLS_ORDER if c not in features_df.columns]
        if missing_cols:
            print(f"[build_features][WARN] {date_str}: missing expected cols {missing_cols}")
            # We still continue, but you'll need to fix upstream.

        # add any missing cols as NaN so model .predict won't crash
        for c in missing_cols:
            features_df[c] = None

        features_df = features_df[FEATURE_COLS_ORDER]

    # write to disk
    out_dir = PROCESSED_DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{date_str}_features.csv")
    features_df.to_csv(out_path, index=False)
    print(f"[build_features] wrote {out_path}")

    return features_df


def build_features_for_range(start_date: str, end_date: str):
    """
    Convenience wrapper to match ingest_raw_for_range.
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    cur = start_dt
    while cur <= end_dt:
        ds = cur.strftime("%Y-%m-%d")
        try:
            build_features_for_date(ds)
        except Exception as e:
            print(f"[build_features][ERROR] {ds}: {e}")
        cur += timedelta(days=1)


if __name__ == "__main__":
    # For now, just run today's date.
    today = datetime.now().strftime("%Y-%m-%d")
    build_features_for_range(today, today)

    # Later for 7-day lookahead:
    # seven_days_out = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    # build_features_for_range(today, seven_days_out)