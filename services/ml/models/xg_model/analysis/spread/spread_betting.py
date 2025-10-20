import pandas as pd
import sys
from datetime import datetime
import os

# ===== CONFIGURATION SECTION =====
# Toggle features on/off
SAVE_TO_FILE = True  # Set to True to save results to file
SAVE_BETS_CSV = True  # Set to True to save individual bet records to CSV

# File paths
YEAR = 2025
DIRECTORY = "data/xgb_model/2025_No_Bet_xgb_all_models_20251014_153554"
FILE_PATH = f"{DIRECTORY}/spread_predictions_{YEAR}.csv"
OUTPUT_DIR = "services/ml/models/xg_model/analysis/spread/results"

# Multi-year analysis configuration
MULTI_YEAR_ANALYSIS = True  # Set to True to run analysis across multiple years
YEAR_FILES = {
    2021: 'data/xgb_model/2021_No_Bet_xgb_all_models_20251014_153704/spread_predictions_2021.csv',
    2022: 'data/xgb_model/2022_No_Bet_xgb_all_models_20251014_153652/spread_predictions_2022.csv',
    2023: 'data/xgb_model/2023_No_Bet_xgb_all_models_20251014_153638/spread_predictions_2023.csv',
    2024: 'data/xgb_model/2024_No_Bet_xgb_all_models_20251014_153613/spread_predictions_2024.csv',
    2025: 'data/xgb_model/2025_No_Bet_xgb_all_models_20251014_153554/spread_predictions_2025.csv',
}

# Betting parameters
FLAT_BET_SIZE = 110  # Dollar amount to risk per bet (typically risk 110 to win 100)
MIN_EDGE = 0.000  # Minimum edge threshold (0 = 0%)
MAX_EDGE = 0.500  # Maximum edge threshold (0.10 = 10%)
EDGE_BUCKET_SIZE = 0.005  # Size of edge buckets for analysis (0.01 = 1%)

# Margin prediction thresholds (absolute value of predicted adjusted margin)
MIN_MARGIN = 0.0  # Minimum predicted margin (absolute value)
MAX_MARGIN = 50.0  # Maximum predicted margin (absolute value)
MARGIN_BUCKET_SIZE = 2.0  # Size of margin buckets (e.g., 2.0 = 0-2, 2-4, 4-6, etc.)

# Spread range filter (set to None to disable)
MIN_SPREAD = None  # Minimum spread (e.g., -30 for large favorites)
MAX_SPREAD = None  # Maximum spread (e.g., 30 for large underdogs)

# Analysis toggles
RUN_EDGE_BUCKET_ANALYSIS = True  # Detailed breakdown by edge ranges
RUN_MARGIN_BUCKET_ANALYSIS = True  # Breakdown by predicted margin buckets
RUN_SPREAD_BUCKET_ANALYSIS = True  # Breakdown by actual spread ranges
RUN_PICK_DIRECTION_ANALYSIS = True  # Analysis by betting favorites vs underdogs

# ===== END CONFIGURATION =====


class DualOutput:
    """Writes output to both console and file."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'w')
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    
    def close(self):
        self.log.close()


def calculate_spread_edge(pred_adjusted_margin, bet_spread):
    """
    Calculate edge for spread betting.
    Edge = probability of covering - implied probability (0.5 at -110 odds)
    
    We estimate probability based on how far our prediction is from the spread.
    This is a simplified model - you may want to use a more sophisticated approach.
    """
    # Calculate the difference between our prediction and the spread
    # Positive means we think team A will beat the spread
    margin_diff = pred_adjusted_margin - bet_spread
    
    # Convert margin difference to win probability using a logistic function
    # This assumes ~7 points = 50% probability shift (adjust based on your data)
    import math
    prob_cover = 1 / (1 + math.exp(-margin_diff / 7.0))
    
    # Edge = our probability - implied probability at -110 (52.38%)
    implied_prob = 0.5238  # -110 odds
    edge = prob_cover - implied_prob
    
    return edge, prob_cover


def get_edge_bucket(edge, bucket_size=0.01):
    """Assign edge to a bucket based on bucket_size."""
    bucket_num = int(edge / bucket_size)
    bucket_start = bucket_num * bucket_size
    bucket_end = bucket_start + bucket_size
    return f"{bucket_start:.3f}-{bucket_end:.3f}"


def get_margin_bucket(margin, bucket_size=2.0):
    """Assign predicted margin to a bucket."""
    abs_margin = abs(margin)
    bucket_num = int(abs_margin / bucket_size)
    bucket_start = bucket_num * bucket_size
    bucket_end = bucket_start + bucket_size
    return f"{bucket_start:.1f}-{bucket_end:.1f}"


def get_spread_bucket(spread):
    """Categorize spreads into buckets."""
    abs_spread = abs(spread)
    if abs_spread < 3:
        return "Pick'em (< 3)"
    elif abs_spread < 7:
        return "Small (3-7)"
    elif abs_spread < 12:
        return "Medium (7-12)"
    elif abs_spread < 20:
        return "Large (12-20)"
    else:
        return "Huge (20+)"


def simulate_spread_betting(df, flat_bet_size=110, min_edge=0, max_edge=0.1,
                            min_margin=0, max_margin=50, min_spread=None, max_spread=None,
                            edge_bucket_size=0.01, margin_bucket_size=2.0,
                            save_csv=False, output_dir=None):
    """
    Comprehensive spread betting simulation.
    """
    total_bets = 0
    won_bets = 0
    total_risked = 0
    total_profit = 0
    
    edge_buckets = {}
    margin_buckets = {}
    spread_buckets = {}
    
    favorite_bets = []
    underdog_bets = []
    
    all_bets = []
    
    for idx, game in df.iterrows():
        # Skip if missing required data
        if pd.isna(game.get('bet_spread')) or pd.isna(game.get('pred_adjusted_margin')):
            continue
        
        pred_margin = game['pred_adjusted_margin']
        bet_spread = game['bet_spread']
        
        # Calculate edge
        edge, prob_cover = calculate_spread_edge(pred_margin, bet_spread)
        
        # Edge filter
        if edge < min_edge or edge > max_edge:
            continue
        
        # Margin filter (absolute value of prediction)
        abs_pred_margin = abs(pred_margin)
        if abs_pred_margin < min_margin or abs_pred_margin > max_margin:
            continue
        
        # Spread filter if specified
        if min_spread is not None and bet_spread < min_spread:
            continue
        if max_spread is not None and bet_spread > max_spread:
            continue
        
        # Determine which side we're betting
        # If pred_margin > bet_spread, bet on team A (favorite to cover)
        # If pred_margin < bet_spread, bet on team B (underdog to cover)
        betting_team_a = pred_margin > bet_spread
        
        # Place bet
        bet_risked = flat_bet_size
        total_risked += bet_risked
        total_bets += 1
        
        # Check if bet won
        ats_correct = bool(game['ats_correct'])
        bet_won = ats_correct  # ats_correct is 1 if model pick was correct
        
        if bet_won:
            profit = bet_risked * (100 / 110)  # Win 100 for every 110 risked
            won_bets += 1
        else:
            profit = -bet_risked
        
        total_profit += profit
        
        # Track by edge bucket
        edge_bucket = get_edge_bucket(edge, edge_bucket_size)
        if edge_bucket not in edge_buckets:
            edge_buckets[edge_bucket] = {'count': 0, 'wins': 0, 'profit': 0, 'risked': 0}
        edge_buckets[edge_bucket]['count'] += 1
        edge_buckets[edge_bucket]['wins'] += (1 if bet_won else 0)
        edge_buckets[edge_bucket]['profit'] += profit
        edge_buckets[edge_bucket]['risked'] += bet_risked
        
        # Track by margin bucket
        margin_bucket = get_margin_bucket(pred_margin, margin_bucket_size)
        if margin_bucket not in margin_buckets:
            margin_buckets[margin_bucket] = {'count': 0, 'wins': 0, 'profit': 0, 'risked': 0}
        margin_buckets[margin_bucket]['count'] += 1
        margin_buckets[margin_bucket]['wins'] += (1 if bet_won else 0)
        margin_buckets[margin_bucket]['profit'] += profit
        margin_buckets[margin_bucket]['risked'] += bet_risked
        
        # Track by spread bucket
        spread_bucket = get_spread_bucket(bet_spread)
        if spread_bucket not in spread_buckets:
            spread_buckets[spread_bucket] = {'count': 0, 'wins': 0, 'profit': 0, 'risked': 0}
        spread_buckets[spread_bucket]['count'] += 1
        spread_buckets[spread_bucket]['wins'] += (1 if bet_won else 0)
        spread_buckets[spread_bucket]['profit'] += profit
        spread_buckets[spread_bucket]['risked'] += bet_risked
        
        # Track favorite vs underdog
        bet_info = {
            'spread': bet_spread,
            'pred_margin': pred_margin,
            'won': bet_won,
            'profit': profit
        }
        
        if betting_team_a and bet_spread < 0:  # Betting on favorite
            favorite_bets.append(bet_info)
        else:  # Betting on underdog
            underdog_bets.append(bet_info)
        
        # Record bet details
        bet_record = {
            'date': game.get('date', ''),
            'game_id': game.get('game_id', idx),
            'team_a': game.get('team_A', 'Team A'),
            'team_b': game.get('team_B', 'Team B'),
            'bet_spread': bet_spread,
            'pred_margin': pred_margin,
            'true_margin': game.get('true_margin', None),
            'betting_team_a': betting_team_a,
            'bet_on': game.get('team_A') if betting_team_a else game.get('team_B'),
            'edge': edge,
            'prob_cover': prob_cover,
            'edge_bucket': edge_bucket,
            'margin_bucket': margin_bucket,
            'spread_bucket': spread_bucket,
            'bet_risked': bet_risked,
            'bet_won': bet_won,
            'profit': profit
        }
        all_bets.append(bet_record)
    
    roi = (total_profit / total_risked * 100) if total_risked > 0 else 0
    win_rate = (won_bets / total_bets * 100) if total_bets > 0 else 0
    avg_edge = (sum([b['edge'] for b in all_bets]) / len(all_bets)) if all_bets else 0
    
    # Save bets to CSV if requested
    if save_csv and output_dir and all_bets:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(output_dir, f"spread_bets_{timestamp}.csv")
        bets_df = pd.DataFrame(all_bets)
        bets_df.to_csv(csv_path, index=False)
        print(f"\n💾 Saved {len(all_bets)} bets to: {csv_path}")
    
    return {
        'total_profit': total_profit,
        'total_bets': total_bets,
        'won_bets': won_bets,
        'win_rate': win_rate,
        'total_risked': total_risked,
        'roi': roi,
        'avg_edge': avg_edge,
        'favorite_bets': favorite_bets,
        'underdog_bets': underdog_bets,
        'edge_buckets': edge_buckets,
        'margin_buckets': margin_buckets,
        'spread_buckets': spread_buckets,
        'all_bets': all_bets
    }


def print_section_header(title):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(title)
    print(f"{'='*80}")


def print_spread_results(results):
    """Print comprehensive spread betting results."""
    print(f"\nOverall Performance:")
    print(f"  Total Bets: {results['total_bets']}")
    print(f"  Wins: {results['won_bets']}")
    print(f"  Win Rate: {results['win_rate']:.2f}%")
    print(f"  Total Risked: ${results['total_risked']:,.2f}")
    print(f"  Total Profit: ${results['total_profit']:,.2f}")
    print(f"  ROI: {results['roi']:.2f}%")
    print(f"  Average Edge: {results['avg_edge']*100:.2f}%")
    print(f"  Units Won: {results['total_profit']/FLAT_BET_SIZE:+.2f}u")
    
    # Favorite vs Underdog
    fav_bets = results['favorite_bets']
    dog_bets = results['underdog_bets']
    
    if fav_bets or dog_bets:
        print(f"\nFavorite vs Underdog Breakdown:")
        
        if fav_bets:
            fav_wins = sum(1 for b in fav_bets if b['won'])
            fav_profit = sum(b['profit'] for b in fav_bets)
            fav_avg_spread = sum(b['spread'] for b in fav_bets) / len(fav_bets)
            print(f"  Favorites: {len(fav_bets)} bets ({len(fav_bets)/results['total_bets']:.1%})")
            print(f"    Win Rate: {fav_wins/len(fav_bets):.2%}")
            print(f"    Profit: ${fav_profit:,.2f}")
            print(f"    Avg Spread: {fav_avg_spread:.1f}")
            print(f"    ROI: {(fav_profit/(FLAT_BET_SIZE*len(fav_bets)))*100:.2f}%")
        
        if dog_bets:
            dog_wins = sum(1 for b in dog_bets if b['won'])
            dog_profit = sum(b['profit'] for b in dog_bets)
            dog_avg_spread = sum(b['spread'] for b in dog_bets) / len(dog_bets)
            print(f"  Underdogs: {len(dog_bets)} bets ({len(dog_bets)/results['total_bets']:.1%})")
            print(f"    Win Rate: {dog_wins/len(dog_bets):.2%}")
            print(f"    Profit: ${dog_profit:,.2f}")
            print(f"    Avg Spread: {dog_avg_spread:.1f}")
            print(f"    ROI: {(dog_profit/(FLAT_BET_SIZE*len(dog_bets)))*100:.2f}%")


def print_edge_buckets(edge_buckets, total_bets):
    """Print edge bucket analysis."""
    print(f"\nBreakdown by Edge Bucket:")
    print("-" * 90)
    print(f"{'Edge Range':<15} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
    print("-" * 90)
    
    for bucket in sorted(edge_buckets.keys()):
        data = edge_buckets[bucket]
        win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
        bet_pct = (data['count'] / total_bets * 100) if total_bets > 0 else 0
        bucket_roi = (data['profit'] / data['risked'] * 100) if data['risked'] > 0 else 0
        
        print(f"{bucket:<15} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  "
              f"{bet_pct:>8.2f}%  ${data['profit']:>9,.2f}  {bucket_roi:>6.2f}%")


def print_margin_buckets(margin_buckets, total_bets):
    """Print margin bucket analysis."""
    print(f"\nBreakdown by Predicted Margin Bucket:")
    print("-" * 90)
    print(f"{'Margin Range':<15} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
    print("-" * 90)
    
    for bucket in sorted(margin_buckets.keys(), key=lambda x: float(x.split('-')[0])):
        data = margin_buckets[bucket]
        win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
        bet_pct = (data['count'] / total_bets * 100) if total_bets > 0 else 0
        bucket_roi = (data['profit'] / data['risked'] * 100) if data['risked'] > 0 else 0
        
        print(f"{bucket:<15} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  "
              f"{bet_pct:>8.2f}%  ${data['profit']:>9,.2f}  {bucket_roi:>6.2f}%")


def print_spread_buckets(spread_buckets, total_bets):
    """Print spread bucket analysis."""
    bucket_order = [
        "Pick'em (< 3)",
        "Small (3-7)",
        "Medium (7-12)",
        "Large (12-20)",
        "Huge (20+)"
    ]
    
    print(f"\nBreakdown by Spread Size:")
    print("-" * 80)
    
    for bucket_name in bucket_order:
        if bucket_name in spread_buckets and spread_buckets[bucket_name]['count'] > 0:
            bucket = spread_buckets[bucket_name]
            win_rate = (bucket['wins'] / bucket['count'] * 100) if bucket['count'] > 0 else 0
            roi = (bucket['profit'] / bucket['risked'] * 100) if bucket['risked'] > 0 else 0
            
            print(f"\n{bucket_name}")
            print(f"  Count: {bucket['count']} ({bucket['count']/total_bets:.1%} of total)")
            print(f"  Wins: {bucket['wins']}")
            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  Profit: ${bucket['profit']:,.2f}")
            print(f"  ROI: {roi:.2f}%")


def main():
    # Setup output file if saving
    if SAVE_TO_FILE:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"spread_analysis_{timestamp}.txt")
        dual_output = DualOutput(output_file)
        sys.stdout = dual_output
        print(f"Output will be saved to: {output_file}")
    
    print_section_header("COMPREHENSIVE SPREAD BETTING ANALYSIS")
    
    # Print configuration
    print(f"\nConfiguration:")
    print(f"  Flat Bet Risk: ${FLAT_BET_SIZE} (to win ${FLAT_BET_SIZE * 100/110:.2f})")
    print(f"  Edge Range: {MIN_EDGE*100:.2f}% - {MAX_EDGE*100:.2f}%")
    print(f"  Edge Bucket Size: {EDGE_BUCKET_SIZE*100:.2f}%")
    print(f"  Margin Range: {MIN_MARGIN:.1f} - {MAX_MARGIN:.1f} points")
    print(f"  Margin Bucket Size: {MARGIN_BUCKET_SIZE:.1f} points")
    if MIN_SPREAD is not None or MAX_SPREAD is not None:
        print(f"  Spread Range: {MIN_SPREAD if MIN_SPREAD else '-∞'} to {MAX_SPREAD if MAX_SPREAD else '+∞'}")
    
    # Single year or multi-year analysis
    if MULTI_YEAR_ANALYSIS:
        print(f"\n  Mode: Multi-Year Analysis (2021-2025)")
        run_multi_year_analysis()
    else:
        print(f"\n  Mode: Single Year Analysis ({YEAR})")
        run_single_year_analysis()
    
    # Close output file if saving
    if SAVE_TO_FILE:
        sys.stdout.close()
        sys.stdout = dual_output.terminal
        print(f"\nResults saved to: {output_file}")


def run_single_year_analysis():
    """Run analysis for a single year."""
    # Read the CSV file
    df = pd.read_csv(FILE_PATH)
    
    # Drop rows with missing data
    original_len = len(df)
    df = df.dropna(subset=['bet_spread', 'pred_adjusted_margin', 'ats_correct'])
    dropped = original_len - len(df)
    
    if dropped > 0:
        print(f"\nDropped {dropped} rows with missing data ({dropped/original_len:.1%})")
        print(f"Analyzing {len(df)} games with valid data")
    
    # Run spread betting analysis
    print_section_header(f"SPREAD BETTING ANALYSIS - Risk ${FLAT_BET_SIZE} per bet")
    
    results = simulate_spread_betting(
        df,
        flat_bet_size=FLAT_BET_SIZE,
        min_edge=MIN_EDGE,
        max_edge=MAX_EDGE,
        min_margin=MIN_MARGIN,
        max_margin=MAX_MARGIN,
        min_spread=MIN_SPREAD,
        max_spread=MAX_SPREAD,
        edge_bucket_size=EDGE_BUCKET_SIZE,
        margin_bucket_size=MARGIN_BUCKET_SIZE,
        save_csv=SAVE_BETS_CSV,
        output_dir=OUTPUT_DIR
    )
    
    print_spread_results(results)
    
    # Print detailed breakdowns
    if RUN_EDGE_BUCKET_ANALYSIS and results['edge_buckets']:
        print_section_header("EDGE BUCKET ANALYSIS")
        print_edge_buckets(results['edge_buckets'], results['total_bets'])
    
    if RUN_MARGIN_BUCKET_ANALYSIS and results['margin_buckets']:
        print_section_header("PREDICTED MARGIN ANALYSIS")
        print_margin_buckets(results['margin_buckets'], results['total_bets'])
    
    if RUN_SPREAD_BUCKET_ANALYSIS and results['spread_buckets']:
        print_section_header("SPREAD SIZE ANALYSIS")
        print_spread_buckets(results['spread_buckets'], results['total_bets'])
    
    # Final summary
    print_section_header("SUMMARY")
    print(f"\nSpread Betting (risk ${FLAT_BET_SIZE} per bet):")
    print(f"  Total Profit: ${results['total_profit']:,.2f} ({results['total_profit']/FLAT_BET_SIZE:+.2f} units)")
    print(f"  ROI: {results['roi']:.2f}%")
    print(f"  Win Rate: {results['win_rate']:.2f}% (need 52.38% to break even)")
    
    if results['roi'] > 0:
        print(f"\n✅ Strategy is PROFITABLE with {results['roi']:.2f}% ROI")
    else:
        print(f"\n❌ Strategy is UNPROFITABLE with {results['roi']:.2f}% ROI")


def run_multi_year_analysis():
    """Run analysis across multiple years."""
    results_by_year = {}
    
    # Run simulations for each year
    for year in sorted(YEAR_FILES.keys()):
        print(f"\n{'='*80}")
        print(f"YEAR {year}")
        print(f"{'='*80}")
        
        try:
            df = pd.read_csv(YEAR_FILES[year])
            original_len = len(df)
            df = df.dropna(subset=['bet_spread', 'pred_adjusted_margin', 'ats_correct'])
            
            print(f"Loaded {len(df)} games (dropped {original_len - len(df)} with missing data)")
            
            result = simulate_spread_betting(
                df,
                flat_bet_size=FLAT_BET_SIZE,
                min_edge=MIN_EDGE,
                max_edge=MAX_EDGE,
                min_margin=MIN_MARGIN,
                max_margin=MAX_MARGIN,
                min_spread=MIN_SPREAD,
                max_spread=MAX_SPREAD,
                edge_bucket_size=EDGE_BUCKET_SIZE,
                margin_bucket_size=MARGIN_BUCKET_SIZE,
                save_csv=False,
                output_dir=OUTPUT_DIR
            )
            results_by_year[year] = result
            
            print(f"\n--- RESULTS ---")
            print(f"Total Bets: {result['total_bets']}")
            print(f"Wins: {result['won_bets']} ({result['win_rate']:.2f}%)")
            print(f"Total Profit: ${result['total_profit']:,.2f}")
            print(f"ROI: {result['roi']:.2f}%")
            
        except Exception as e:
            print(f"ERROR loading {year}: {e}")
            continue
    
    # Combined summary
    print_section_header("COMBINED RESULTS (2021-2025)")
    
    print(f"\nSPREAD BETTING SUMMARY (risk ${FLAT_BET_SIZE} per bet)")
    print("=" * 80)
    
    total_profit = sum(r['total_profit'] for r in results_by_year.values())
    total_bets = sum(r['total_bets'] for r in results_by_year.values())
    total_wins = sum(r['won_bets'] for r in results_by_year.values())
    total_risked = sum(r['total_risked'] for r in results_by_year.values())
    total_roi = (total_profit / total_risked * 100) if total_risked > 0 else 0
    total_wr = (total_wins / total_bets * 100) if total_bets > 0 else 0
    
    print(f"\nYear-by-Year:")
    print(f"{'Year':<6} {'Bets':<6} {'Wins':<6} {'Win%':<8} {'Profit':<12} {'ROI':<8}")
    print("-" * 80)
    for year in sorted(results_by_year.keys()):
        r = results_by_year[year]
        print(f"{year:<6} {r['total_bets']:<6} {r['won_bets']:<6} "
              f"{r['win_rate']:>6.2f}%  ${r['total_profit']:>9,.2f}  {r['roi']:>6.2f}%")
    
    print("-" * 80)
    print(f"{'TOTAL':<6} {total_bets:<6} {total_wins:<6} "
          f"{total_wr:>6.2f}%  ${total_profit:>9,.2f}  {total_roi:>6.2f}%")
    
    # Edge bucket analysis across all years
    if RUN_EDGE_BUCKET_ANALYSIS:
        print(f"\n\nEDGE BUCKET ANALYSIS ({EDGE_BUCKET_SIZE*100:.1f}% buckets)")
        print("=" * 80)
        
        combined_edge_buckets = {}
        for year_result in results_by_year.values():
            for bucket, data in year_result['edge_buckets'].items():
                if bucket not in combined_edge_buckets:
                    combined_edge_buckets[bucket] = {'count': 0, 'wins': 0, 'profit': 0, 'risked': 0}
                combined_edge_buckets[bucket]['count'] += data['count']
                combined_edge_buckets[bucket]['wins'] += data['wins']
                combined_edge_buckets[bucket]['profit'] += data['profit']
                combined_edge_buckets[bucket]['risked'] += data['risked']
        
        print(f"\n{'Edge Bucket':<15} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
        print("-" * 90)
        
        for bucket in sorted(combined_edge_buckets.keys()):
            data = combined_edge_buckets[bucket]
            win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
            bet_pct = (data['count'] / total_bets * 100) if total_bets > 0 else 0
            bucket_roi = (data['profit'] / data['risked'] * 100) if data['risked'] > 0 else 0
            print(f"{bucket:<15} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  {bet_pct:>8.2f}%  "
                  f"${data['profit']:>9,.2f}  {bucket_roi:>6.2f}%")
    
    # Margin bucket analysis across all years
    if RUN_MARGIN_BUCKET_ANALYSIS:
        print(f"\n\nPREDICTED MARGIN BUCKET ANALYSIS ({MARGIN_BUCKET_SIZE:.1f} point buckets)")
        print("=" * 80)
        
        combined_margin_buckets = {}
        for year_result in results_by_year.values():
            for bucket, data in year_result['margin_buckets'].items():
                if bucket not in combined_margin_buckets:
                    combined_margin_buckets[bucket] = {'count': 0, 'wins': 0, 'profit': 0, 'risked': 0}
                combined_margin_buckets[bucket]['count'] += data['count']
                combined_margin_buckets[bucket]['wins'] += data['wins']
                combined_margin_buckets[bucket]['profit'] += data['profit']
                combined_margin_buckets[bucket]['risked'] += data['risked']
        
        print(f"\n{'Margin Bucket':<15} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
        print("-" * 90)
        
        for bucket in sorted(combined_margin_buckets.keys(), key=lambda x: float(x.split('-')[0])):
            data = combined_margin_buckets[bucket]
            win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
            bet_pct = (data['count'] / total_bets * 100) if total_bets > 0 else 0
            bucket_roi = (data['profit'] / data['risked'] * 100) if data['risked'] > 0 else 0
            print(f"{bucket:<15} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  {bet_pct:>8.2f}%  "
                  f"${data['profit']:>9,.2f}  {bucket_roi:>6.2f}%")
    
    # Final verdict
    print_section_header("FINAL VERDICT")
    
    print(f"\nSpread Betting (risk ${FLAT_BET_SIZE} per bet):")
    print(f"  Total Profit: ${total_profit:,.2f} ({total_profit/FLAT_BET_SIZE:+.2f} units)")
    print(f"  ROI: {total_roi:.2f}%")
    print(f"  Win Rate: {total_wr:.2f}% (need 52.38% to break even)")
    print(f"  Winning Years: {sum(1 for r in results_by_year.values() if r['total_profit'] > 0)}/{len(results_by_year)}")
    
    if total_roi > 0:
        print(f"\n✅ Strategy is PROFITABLE with {total_roi:.2f}% ROI")
    else:
        print(f"\n❌ Strategy is UNPROFITABLE with {total_roi:.2f}% ROI")


if __name__ == "__main__":
    main()