"""Main pipeline orchestration for NCAA basketball data processing."""
import pandas as pd

from config import (
    OUT_DIR,
    YEAR_LIST,
    raw_path_for,
)
from data_loaders import (
    load_betting,
    reduce_betting,
    load_torvik_ratings,
)
from feature_engineering import (
    prepare_rolling, _compute_matchup_features
)
from transformations import add_labels, make_per_game, attach_torvik_ratings
from betting_integration import merge_betting, extract_moneylines_per_game
from utils import ensure_bet_schema, coalesce_merge_artifacts, standardize_opponent_columns


def process_year(year: str):
    """Process a single season of NCAA basketball data."""
    print(f"\n{'='*60}")
    print(f"Processing {year}")
    print(f"{'='*60}")

    # Step 1: Load raw logs and compute rolling features
    raw_path = raw_path_for(year)
    raw = pd.read_csv(raw_path)
    raw = standardize_opponent_columns(raw)
    cleaned = prepare_rolling(raw)
    print(f"[features] Computed rolling stats: {len(cleaned)} rows")

    # Step 2: Add outcome labels / context flags
    labeled = add_labels(cleaned, raw)
    print(f"[labels] Added win/loss/margin labels: {len(labeled)} rows")

    # Step 3: Attach Bart Torvik daily ratings (barthag / adj_o / adj_d / rank)
    try:
        torvik = load_torvik_ratings()
        labeled = attach_torvik_ratings(labeled, torvik)
        coverage = labeled[["team_barthag", "opp_barthag"]].notna().any(axis=1).mean()
        print(f"[torvik] Attached ratings (coverage: {coverage:.1%})")
    except FileNotFoundError:
        print("[torvik] Ratings file missing — skipping")
    except Exception as exc:
        print(f"[torvik] Failed to attach ratings: {exc}")

    labeled = _compute_matchup_features(labeled)
    print("[matchup] Computed expected performance metrics")

    # Step 4: Season-level normalization (z-scores)
    try:
        labeled["season"] = int(year)
    except Exception:
        labeled["season"] = pd.to_numeric(year, errors="coerce")


    try:
        bet = load_betting(year)
        bet = reduce_betting(bet)
        print(f"[betting] Loaded {len(bet)} betting lines")

        labeled = merge_betting(labeled, bet)
        labeled = ensure_bet_schema(labeled)
        print("[betting] Merged betting data")
    except FileNotFoundError:
        print(f"[betting] No betting file for {year} — skipping")

    # Step 6: Create per-game dataset
    per_game = make_per_game(labeled)
    print(f"[per-game] Reduced to {len(per_game)} unique games")

    # Step 7: Extract moneylines for both teams
    try:
        raw_bet_full = load_betting(year)
        per_game = extract_moneylines_per_game(raw_bet_full, per_game)
        print("[moneyline] Extracted moneylines for both teams")
    except FileNotFoundError:
        per_game["moneyline_a"] = pd.NA
        per_game["moneyline_b"] = pd.NA

    # Step 8: Clean up artifacts from merges
    for drop_col in ["bet_moneyline", "bet_moneyline_for_team"]:
        if drop_col in per_game.columns:
            per_game = per_game.drop(columns=[drop_col])

    per_game = coalesce_merge_artifacts(per_game)
    per_game = ensure_bet_schema(per_game)

    # Step 9: Sort and persist outputs
    if "team_key" in per_game.columns:
        per_game = per_game.sort_values(["team_key", "Date"], ascending=[True, True])

    per_game_path = OUT_DIR / f"per_game_{year}.csv"
    per_game.to_csv(per_game_path, index=False)
    print(f"[output] Saved per-game dataset → {per_game_path}")

    # Step 10: Summary diagnostics
    print(f"\nSummary for {year}:")
    print(f"  Cleaned rows: {len(cleaned)}")
    print(f"  Labeled rows: {len(labeled)}")
    print(f"  Per-game rows: {len(per_game)}")

    bet_cols_present = [c for c in ["bet_total", "bet_spread"] if c in per_game.columns]
    if bet_cols_present:
        has_bet = per_game[bet_cols_present].notna().any(axis=1).mean()
        print(f"  Betting coverage: {has_bet:.1%} of games have lines")


def main():
    """Process all configured years."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("NCAA Basketball Data Pipeline")
    print(f"Processing years: {', '.join(YEAR_LIST)}")

    for yr in YEAR_LIST:
        try:
            process_year(yr)
        except FileNotFoundError as exc:
            print(f"\n[WARN] Missing file for {yr}: {exc} — skipping")
        except Exception as exc:
            print(f"\n[ERROR] Failed to process {yr}: {exc}")
            raise

    print(f"\n{'='*60}")
    print("Pipeline complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
