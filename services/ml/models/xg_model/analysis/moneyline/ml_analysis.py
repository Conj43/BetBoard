import pandas as pd
import sys
from datetime import datetime
import os

# ===== CONFIGURATION SECTION =====
# Toggle features on/off
SAVE_TO_FILE = False  # Set to True to save results to file
SAVE_BETS_CSV = False  # Set to True to save individual bet records to CSV

# File paths
YEAR = 2025
DIRECTORY = "data/xgb_model/2025_No_Bet_xgb_all_models_20251014_153554"
FILE_PATH = f"{DIRECTORY}/moneyline_predictions_{YEAR}.csv"
OUTPUT_DIR = "services/ml/models/xg_model/analysis/moneyline/results"

# Multi-year analysis configuration
MULTI_YEAR_ANALYSIS = True  # Set to True to run analysis across multiple years
YEAR_FILES = {
    2021: 'data/xgb_model/2021_No_Bet_xgb_all_models_20251014_153704/moneyline_predictions_2021.csv',
    2022: 'data/xgb_model/2022_No_Bet_xgb_all_models_20251014_153652/moneyline_predictions_2022.csv',
    2023: 'data/xgb_model/2023_No_Bet_xgb_all_models_20251014_153638/moneyline_predictions_2023.csv',
    2024: 'data/xgb_model/2024_No_Bet_xgb_all_models_20251014_153613/moneyline_predictions_2024.csv',
    2025: 'data/xgb_model/2025_No_Bet_xgb_all_models_20251014_153554/moneyline_predictions_2025.csv',
}

# Betting parameters
FLAT_BET_SIZE = 100  # Dollar amount per bet
MIN_EDGE = 0.005  # Minimum edge threshold (0 = 0%)
MAX_EDGE = 0.2  # Maximum edge threshold (0.0471 = 4.71%)
EDGE_BUCKET_SIZE = 0.005  # Size of edge buckets for analysis (0.005 = 0.5%)

# Kelly Criterion parameters
KELLY_STARTING_BANKROLL = 10000  # Starting bankroll for Kelly simulations
KELLY_CAP = 0.25  # Kelly fraction cap (0.25 = quarter Kelly)

# Zone configuration - which odds ranges to bet on (set to True/False to enable/disable)
ENABLED_ZONES = {
    'heavy_favorite': False,          # best 0.01 - 0.1 edge (1% - 10%)
    'strong_favorite': False,        # profitable in 0.05 - 0.25
    'moderate_favorite': False,      # not really profitable
    'slight_favorite': True,        # best in 0.005 - 0.2
    'pickem_favorite': False,        # not enough bets here
    'pickem_underdog': False,         # not enough bets here
    'slight_underdog': False,         # not great. 0.22 ROI at 0.02 - 0.16
    'moderate_underdog': False,      # not a lot of data, 0.15 - 0.5 got 7% ROI
    'strong_underdog': False,        # unprofitable
    'heavy_underdog': False,         # unprofitable
}

# Odds range filter (set to None to disable)
MIN_ODDS = -10000  # Minimum odds to bet (e.g., -10000 to include heavy favorites)
MAX_ODDS = 10000     # Maximum odds to bet (e.g., 150 to exclude big underdogs)

# Analysis toggles
RUN_ODDS_BUCKET_ANALYSIS = True  # Detailed breakdown by odds ranges
RUN_EDGE_BUCKET_ANALYSIS = True  # Detailed breakdown by edge ranges
RUN_ZONE_ANALYSIS = True         # Analysis of specific odds zones
RUN_KELLY_ANALYSIS = True        # Kelly Criterion simulations

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


def odds_to_implied_prob(american_odds):
    """Convert American odds to implied probability."""
    if american_odds < 0:
        return abs(american_odds) / (abs(american_odds) + 100)
    else:
        return 100 / (american_odds + 100)


def odds_to_decimal(american_odds):
    """Convert American odds to decimal odds."""
    if american_odds < 0:
        return 1 + (100 / abs(american_odds))
    else:
        return 1 + (american_odds / 100)


def kelly_fraction(our_prob, decimal_odds, max_kelly=0.25):
    """Calculate Kelly Criterion bet fraction."""
    b = decimal_odds - 1
    p = our_prob
    q = 1 - p
    
    if b <= 0:
        return 0
    
    kelly = (b * p - q) / b
    
    if kelly <= 0:
        return 0
    
    return min(kelly, max_kelly)


def get_odds_bucket(american_odds):
    """Categorize American odds into buckets."""
    if american_odds < -300:
        return "Heavy Favorite (<-300)"
    elif american_odds < -200:
        return "Strong Favorite (-300 to -200)"
    elif american_odds < -150:
        return "Moderate Favorite (-200 to -150)"
    elif american_odds < -110:
        return "Slight Favorite (-150 to -110)"
    elif american_odds < 0:
        return "Pick'em Favorite (-110 to -100)"
    elif american_odds <= 110:
        return "Pick'em Underdog (+100 to +110)"
    elif american_odds <= 150:
        return "Slight Underdog (+110 to +150)"
    elif american_odds <= 200:
        return "Moderate Underdog (+150 to +200)"
    elif american_odds <= 300:
        return "Strong Underdog (+200 to +300)"
    else:
        return "Heavy Underdog (>+300)"


def get_edge_bucket(edge, bucket_size=0.005):
    """Assign edge to a bucket based on bucket_size."""
    bucket_num = int(edge / bucket_size)
    bucket_start = bucket_num * bucket_size
    bucket_end = bucket_start + bucket_size
    return f"{bucket_start:.3f}-{bucket_end:.3f}"


def get_zone(odds):
    """Determine which zone an odds value belongs to."""
    if odds < -300:
        return 'heavy_favorite'
    elif -300 <= odds < -200:
        return 'strong_favorite'
    elif -200 <= odds < -150:
        return 'moderate_favorite'
    elif -150 <= odds < -110:
        return 'slight_favorite'
    elif -110 <= odds < 0:
        return 'pickem_favorite'
    elif 0 <= odds <= 110:
        return 'pickem_underdog'
    elif 110 < odds <= 150:
        return 'slight_underdog'
    elif 150 < odds <= 200:
        return 'moderate_underdog'
    elif 200 < odds <= 300:
        return 'strong_underdog'
    else:  # odds > 300
        return 'heavy_underdog'


def simulate_flat_betting_comprehensive(df, flat_bet_size=100, min_edge=0, max_edge=25.0, 
                                       min_odds=None, max_odds=None, enabled_zones=None,
                                       edge_bucket_size=0.005, save_csv=False, output_dir=None):
    """
    Comprehensive flat betting simulation with all tracking features.
    """
    total_bets = 0
    won_bets = 0
    total_staked = 0
    total_profit = 0
    
    favorite_bets = []
    underdog_bets = []
    odds_buckets = {}
    edge_buckets = {}
    zones = {
        'heavy_favorite': {'name': 'Heavy Favorite (<-300)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'strong_favorite': {'name': 'Strong Favorite (-300 to -200)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'moderate_favorite': {'name': 'Moderate Favorite (-200 to -150)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'slight_favorite': {'name': 'Slight Favorite (-150 to -110)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'pickem_favorite': {'name': "Pick'em Favorite (-110 to -100)", 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'pickem_underdog': {'name': "Pick'em Underdog (+100 to +110)", 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'slight_underdog': {'name': 'Slight Underdog (+110 to +150)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'moderate_underdog': {'name': 'Moderate Underdog (+150 to +200)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'strong_underdog': {'name': 'Strong Underdog (+200 to +300)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'heavy_underdog': {'name': 'Heavy Underdog (>+300)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
    }
    
    all_bets = []
    
    for idx, game in df.iterrows():
        if pd.isna(game.get('moneyline_a')) or pd.isna(game.get('moneyline_b')):
            continue

        p_win_a = game['p_win_A']
        p_win_b = 1 - p_win_a

        ml_a = game['moneyline_a']
        ml_b = game['moneyline_b']

        implied_prob_a = odds_to_implied_prob(ml_a)
        implied_prob_b = odds_to_implied_prob(ml_b)

        edge_a = p_win_a - implied_prob_a
        edge_b = p_win_b - implied_prob_b

        # Choose side with higher edge
        if edge_a >= edge_b:
            chosen_side = 'A'
            chosen_prob = p_win_a
            chosen_odds = ml_a
            chosen_edge = edge_a
        else:
            chosen_side = 'B'
            chosen_prob = p_win_b
            chosen_odds = ml_b
            chosen_edge = edge_b

        # Edge band filter
        if chosen_edge < min_edge or chosen_edge > max_edge:
            continue

        # Skip heavy favorites (odds -1000 or worse)
        if chosen_odds <= -1000:
            continue
        
        # Apply odds range filter if specified
        if min_odds is not None and chosen_odds < min_odds:
            continue
        if max_odds is not None and chosen_odds > max_odds:
            continue
        
        # Zone filter if zones are specified
        zone = get_zone(chosen_odds)
        if enabled_zones is not None:
            if zone not in enabled_zones or not enabled_zones[zone]:
                continue

        # Place bet
        bet_amount = flat_bet_size
        total_staked += bet_amount
        total_bets += 1

        actual_winner = game['true_winner']
        bet_won = (chosen_side == 'A' and actual_winner == 1) or \
                  (chosen_side == 'B' and actual_winner == 0)

        decimal_odds = odds_to_decimal(chosen_odds)
        if bet_won:
            profit = bet_amount * (decimal_odds - 1)
            won_bets += 1
        else:
            profit = -bet_amount

        total_profit += profit
        
        # Track by odds bucket
        bucket = get_odds_bucket(chosen_odds)
        if bucket not in odds_buckets:
            odds_buckets[bucket] = {
                'count': 0,
                'wins': 0,
                'profit': 0,
                'staked': 0
            }
        
        odds_buckets[bucket]['count'] += 1
        odds_buckets[bucket]['wins'] += (1 if bet_won else 0)
        odds_buckets[bucket]['profit'] += profit
        odds_buckets[bucket]['staked'] += bet_amount
        
        # Track by edge bucket
        edge_bucket = get_edge_bucket(chosen_edge, edge_bucket_size)
        if edge_bucket not in edge_buckets:
            edge_buckets[edge_bucket] = {'count': 0, 'wins': 0, 'profit': 0, 'staked': 0}
        edge_buckets[edge_bucket]['count'] += 1
        edge_buckets[edge_bucket]['wins'] += (1 if bet_won else 0)
        edge_buckets[edge_bucket]['profit'] += profit
        edge_buckets[edge_bucket]['staked'] += bet_amount
        
        # Track by zone
        if zone in zones:
            zones[zone]['count'] += 1
            zones[zone]['wins'] += (1 if bet_won else 0)
            zones[zone]['profit'] += profit
            zones[zone]['staked'] += bet_amount
        
        # Track favorite vs underdog
        bet_info = {
            'odds': chosen_odds,
            'won': bet_won,
            'profit': profit
        }
        
        if chosen_odds < 0:
            favorite_bets.append(bet_info)
        else:
            underdog_bets.append(bet_info)

        # Record bet details
        bet_record = {
            'date': game.get('date', ''),
            'game_id': game.get('game_id', idx),
            'team_a': game.get('team_a', 'Team A'),
            'team_b': game.get('team_b', 'Team B'),
            'chosen_side': chosen_side,
            'chosen_team': game.get('team_a', 'Team A') if chosen_side == 'A' else game.get('team_b', 'Team B'),
            'chosen_odds': chosen_odds,
            'our_prob': chosen_prob,
            'implied_prob': implied_prob_a if chosen_side == 'A' else implied_prob_b,
            'edge': chosen_edge,
            'edge_bucket': edge_bucket,
            'odds_bucket': bucket,
            'zone': zones[zone]['name'] if zone in zones else 'Other',
            'bet_amount': bet_amount,
            'bet_won': bet_won,
            'profit': profit,
            'actual_winner': 'A' if actual_winner == 1 else 'B'
        }
        all_bets.append(bet_record)

    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
    win_rate = (won_bets / total_bets * 100) if total_bets > 0 else 0
    avg_edge = (sum([r['edge'] for r in all_bets]) / len(all_bets)) if all_bets else 0

    # Save bets to CSV if requested
    if save_csv and output_dir and all_bets:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(output_dir, f"flat_bets_{timestamp}.csv")
        bets_df = pd.DataFrame(all_bets)
        bets_df.to_csv(csv_path, index=False)
        print(f"\n💾 Saved {len(all_bets)} bets to: {csv_path}")

    return {
        'total_profit': total_profit,
        'total_bets': total_bets,
        'won_bets': won_bets,
        'win_rate': win_rate,
        'total_staked': total_staked,
        'roi': roi,
        'avg_edge': avg_edge,
        'favorite_bets': favorite_bets,
        'underdog_bets': underdog_bets,
        'odds_buckets': odds_buckets,
        'edge_buckets': edge_buckets,
        'zones': zones,
        'all_bets': all_bets
    }


def simulate_kelly_comprehensive(df, starting_bankroll=10000, min_edge=0, max_edge=25.0,
                                kelly_cap=0.25, min_odds=None, max_odds=None, 
                                enabled_zones=None, edge_bucket_size=0.005,
                                save_csv=False, output_dir=None):
    """
    Comprehensive Kelly Criterion simulation with all tracking features.
    """
    work = df.copy()
    if "date" in work.columns:
        try:
            work["__date__"] = pd.to_datetime(work["date"])
            work = work.sort_values("__date__")
        except Exception:
            pass

    current_bankroll = float(starting_bankroll)
    total_bets = 0
    won_bets = 0
    total_staked = 0.0
    total_profit = 0.0
    
    edge_buckets = {}
    zones = {
        'heavy_favorite': {'name': 'Heavy Favorite (<-300)', 'count': 0, 'wins': 0, 'profit': 0},
        'strong_favorite': {'name': 'Strong Favorite (-300 to -200)', 'count': 0, 'wins': 0, 'profit': 0},
        'moderate_favorite': {'name': 'Moderate Favorite (-200 to -150)', 'count': 0, 'wins': 0, 'profit': 0},
        'slight_favorite': {'name': 'Slight Favorite (-150 to -110)', 'count': 0, 'wins': 0, 'profit': 0},
        'pickem_favorite': {'name': "Pick'em Favorite (-110 to -100)", 'count': 0, 'wins': 0, 'profit': 0},
        'pickem_underdog': {'name': "Pick'em Underdog (+100 to +110)", 'count': 0, 'wins': 0, 'profit': 0},
        'slight_underdog': {'name': 'Slight Underdog (+110 to +150)', 'count': 0, 'wins': 0, 'profit': 0},
        'moderate_underdog': {'name': 'Moderate Underdog (+150 to +200)', 'count': 0, 'wins': 0, 'profit': 0},
        'strong_underdog': {'name': 'Strong Underdog (+200 to +300)', 'count': 0, 'wins': 0, 'profit': 0},
        'heavy_underdog': {'name': 'Heavy Underdog (>+300)', 'count': 0, 'wins': 0, 'profit': 0},
    }
    
    all_bets = []

    for idx, game in work.iterrows():
        if pd.isna(game.get('moneyline_a')) or pd.isna(game.get('moneyline_b')):
            continue

        p_win_a = float(game['p_win_A'])
        p_win_b = 1.0 - p_win_a

        ml_a = float(game['moneyline_a'])
        ml_b = float(game['moneyline_b'])

        implied_prob_a = odds_to_implied_prob(ml_a)
        implied_prob_b = odds_to_implied_prob(ml_b)

        edge_a = p_win_a - implied_prob_a
        edge_b = p_win_b - implied_prob_b

        if edge_a >= edge_b:
            chosen_side = 'A'
            chosen_prob = p_win_a
            chosen_odds = ml_a
            chosen_edge = edge_a
        else:
            chosen_side = 'B'
            chosen_prob = p_win_b
            chosen_odds = ml_b
            chosen_edge = edge_b

        if chosen_edge < min_edge or chosen_edge > max_edge:
            continue

        if chosen_odds <= -1000:
            continue
            
        if min_odds is not None and chosen_odds < min_odds:
            continue
        if max_odds is not None and chosen_odds > max_odds:
            continue

        zone = get_zone(chosen_odds)
        if enabled_zones is not None:
            if zone not in enabled_zones or not enabled_zones[zone]:
                continue

        dec_odds = odds_to_decimal(chosen_odds)
        frac = kelly_fraction(chosen_prob, dec_odds, max_kelly=kelly_cap)
        if frac <= 0.0 or current_bankroll <= 0:
            continue

        bet_amount = current_bankroll * frac
        if bet_amount < 1e-6:
            continue

        total_staked += bet_amount
        total_bets += 1

        actual_winner = int(game['true_winner'])
        bet_won = (chosen_side == 'A' and actual_winner == 1) or \
                  (chosen_side == 'B' and actual_winner == 0)

        if bet_won:
            profit = bet_amount * (dec_odds - 1.0)
            won_bets += 1
        else:
            profit = -bet_amount

        current_bankroll += profit
        total_profit += profit
        
        # Track by edge bucket
        edge_bucket = get_edge_bucket(chosen_edge, edge_bucket_size)
        if edge_bucket not in edge_buckets:
            edge_buckets[edge_bucket] = {'count': 0, 'wins': 0, 'profit': 0}
        edge_buckets[edge_bucket]['count'] += 1
        edge_buckets[edge_bucket]['wins'] += (1 if bet_won else 0)
        edge_buckets[edge_bucket]['profit'] += profit
        
        # Track by zone
        if zone in zones:
            zones[zone]['count'] += 1
            zones[zone]['wins'] += (1 if bet_won else 0)
            zones[zone]['profit'] += profit
        
        # Record bet details
        bet_record = {
            'date': game.get('date', ''),
            'game_id': game.get('game_id', idx),
            'team_a': game.get('team_a', 'Team A'),
            'team_b': game.get('team_b', 'Team B'),
            'chosen_side': chosen_side,
            'chosen_team': game.get('team_a', 'Team A') if chosen_side == 'A' else game.get('team_b', 'Team B'),
            'chosen_odds': chosen_odds,
            'our_prob': chosen_prob,
            'implied_prob': odds_to_implied_prob(chosen_odds),
            'edge': chosen_edge,
            'edge_bucket': edge_bucket,
            'zone': zones[zone]['name'] if zone in zones else 'Other',
            'bankroll_before': current_bankroll - profit,
            'kelly_fraction': frac,
            'bet_amount': bet_amount,
            'bet_won': bet_won,
            'profit': profit,
            'bankroll_after': current_bankroll,
            'actual_winner': 'A' if actual_winner == 1 else 'B'
        }
        all_bets.append(bet_record)

        if current_bankroll <= 0:
            break

    roi = (total_profit / total_staked * 100.0) if total_staked > 0 else 0.0
    win_rate = (won_bets / total_bets * 100.0) if total_bets > 0 else 0.0
    total_return = ((current_bankroll - starting_bankroll) / starting_bankroll * 100.0)

    # Save bets to CSV if requested
    if save_csv and output_dir and all_bets:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(output_dir, f"kelly_bets_{timestamp}.csv")
        bets_df = pd.DataFrame(all_bets)
        bets_df.to_csv(csv_path, index=False)
        print(f"\n💾 Saved {len(all_bets)} bets to: {csv_path}")

    return {
        'starting_bankroll': starting_bankroll,
        'final_bankroll': current_bankroll,
        'total_profit': total_profit,
        'total_return': total_return,
        'total_bets': total_bets,
        'won_bets': won_bets,
        'win_rate': win_rate,
        'total_staked': total_staked,
        'roi': roi,
        'zones': zones,
        'edge_buckets': edge_buckets,
        'all_bets': all_bets
    }


def print_section_header(title):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(title)
    print(f"{'='*80}")


def print_flat_results(results, bet_size):
    """Print comprehensive flat betting results."""
    print(f"\nOverall Performance:")
    print(f"  Total Bets: {results['total_bets']}")
    print(f"  Wins: {results['won_bets']}")
    print(f"  Win Rate: {results['win_rate']:.2f}%")
    print(f"  Total Staked: ${results['total_staked']:,.2f}")
    print(f"  Total Profit: ${results['total_profit']:,.2f}")
    print(f"  ROI: {results['roi']:.2f}%")
    print(f"  Average Edge: {results['avg_edge']*100:.2f}%")
    
    # Favorite vs Underdog
    fav_bets = results['favorite_bets']
    dog_bets = results['underdog_bets']
    
    if fav_bets or dog_bets:
        print(f"\nFavorite vs Underdog Breakdown:")
        
        if fav_bets:
            fav_wins = sum(1 for b in fav_bets if b['won'])
            fav_profit = sum(b['profit'] for b in fav_bets)
            fav_avg_odds = sum(b['odds'] for b in fav_bets) / len(fav_bets)
            print(f"  Favorites: {len(fav_bets)} bets ({len(fav_bets)/results['total_bets']:.1%})")
            print(f"    Win Rate: {fav_wins/len(fav_bets):.2%}")
            print(f"    Profit: ${fav_profit:,.2f}")
            print(f"    Avg Odds: {fav_avg_odds:.0f}")
            print(f"    ROI: {(fav_profit/(bet_size*len(fav_bets)))*100:.2f}%")
        
        if dog_bets:
            dog_wins = sum(1 for b in dog_bets if b['won'])
            dog_profit = sum(b['profit'] for b in dog_bets)
            dog_avg_odds = sum(b['odds'] for b in dog_bets) / len(dog_bets)
            print(f"  Underdogs: {len(dog_bets)} bets ({len(dog_bets)/results['total_bets']:.1%})")
            print(f"    Win Rate: {dog_wins/len(dog_bets):.2%}")
            print(f"    Profit: ${dog_profit:,.2f}")
            print(f"    Avg Odds: {dog_avg_odds:.0f}")
            print(f"    ROI: {(dog_profit/(bet_size*len(dog_bets)))*100:.2f}%")


def print_odds_buckets(odds_buckets, total_bets):
    """Print odds bucket analysis."""
    bucket_order = [
        "Heavy Favorite (<-300)",
        "Strong Favorite (-300 to -200)",
        "Moderate Favorite (-200 to -150)",
        "Slight Favorite (-150 to -110)",
        "Pick'em Favorite (-110 to -100)",
        "Pick'em Underdog (+100 to +110)",
        "Slight Underdog (+110 to +150)",
        "Moderate Underdog (+150 to +200)",
        "Strong Underdog (+200 to +300)",
        "Heavy Underdog (>+300)"
    ]
    
    print(f"\nBreakdown by Odds Bucket:")
    print("-" * 80)
    
    for bucket_name in bucket_order:
        if bucket_name in odds_buckets and odds_buckets[bucket_name]['count'] > 0:
            bucket = odds_buckets[bucket_name]
            win_rate = (bucket['wins'] / bucket['count'] * 100) if bucket['count'] > 0 else 0
            roi = (bucket['profit'] / bucket['staked'] * 100) if bucket['staked'] > 0 else 0
            
            print(f"\n{bucket_name}")
            print(f"  Count: {bucket['count']} ({bucket['count']/total_bets:.1%} of total)")
            print(f"  Wins: {bucket['wins']}")
            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  Profit: ${bucket['profit']:,.2f}")
            print(f"  ROI: {roi:.2f}%")


def print_edge_buckets(edge_buckets, total_bets, bet_size):
    """Print edge bucket analysis."""
    print(f"\nBreakdown by Edge Bucket:")
    print("-" * 80)
    print(f"{'Edge Range':<15} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
    print("-" * 80)
    
    for bucket in sorted(edge_buckets.keys()):
        data = edge_buckets[bucket]
        win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
        bet_pct = (data['count'] / total_bets * 100) if total_bets > 0 else 0
        bucket_roi = (data['profit'] / (data['count'] * bet_size) * 100) if data['count'] > 0 else 0
        
        print(f"{bucket:<15} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  "
              f"{bet_pct:>8.2f}%  ${data['profit']:>9,.2f}  {bucket_roi:>6.2f}%")


def print_zone_analysis(zones, total_bets):
    """Print zone analysis."""
    print(f"\nBreakdown by Zone:")
    print("-" * 80)
    
    zone_display_order = [
        'heavy_favorite',
        'strong_favorite',
        'moderate_favorite',
        'slight_favorite',
        'pickem_favorite',
        'pickem_underdog',
        'slight_underdog',
        'moderate_underdog',
        'strong_underdog',
        'heavy_underdog'
    ]
    
    for zone_key in zone_display_order:
        if zones[zone_key]['count'] > 0:
            zone = zones[zone_key]
            win_rate = (zone['wins'] / zone['count'] * 100) if zone['count'] > 0 else 0
            roi = (zone['profit'] / zone['staked'] * 100) if zone.get('staked', 0) > 0 else 0
            
            print(f"\n{zone['name']}")
            print(f"  Count: {zone['count']} ({zone['count']/total_bets:.1%} of total)")
            print(f"  Wins: {zone['wins']}")
            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  Profit: ${zone['profit']:,.2f}")
            if zone.get('staked'):
                print(f"  ROI: {roi:.2f}%")


def main():
    # Setup output file if saving
    if SAVE_TO_FILE:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"betting_analysis_{timestamp}.txt")
        dual_output = DualOutput(output_file)
        sys.stdout = dual_output
        print(f"Output will be saved to: {output_file}")
    
    print_section_header("COMPREHENSIVE BETTING ANALYSIS")
    
    # Print configuration
    print(f"\nConfiguration:")
    print(f"  Flat Bet Size: ${FLAT_BET_SIZE}")
    print(f"  Edge Range: {MIN_EDGE*100:.2f}% - {MAX_EDGE*100:.2f}%")
    print(f"  Edge Bucket Size: {EDGE_BUCKET_SIZE*100:.2f}%")
    if MIN_ODDS is not None or MAX_ODDS is not None:
        print(f"  Odds Range: {MIN_ODDS if MIN_ODDS else '-∞'} to {MAX_ODDS if MAX_ODDS else '+∞'}")
    print(f"  Kelly Starting Bankroll: ${KELLY_STARTING_BANKROLL:,.0f}")
    print(f"  Kelly Cap: {KELLY_CAP*100:.0f}%")
    
    if ENABLED_ZONES:
        print(f"\n  Active Zones:")
        zone_display_names = {
            'heavy_favorite': 'Heavy Favorites (odds < -300)',
            'strong_favorite': 'Strong Favorites (odds -300 to -200)',
            'moderate_favorite': 'Moderate Favorites (odds -200 to -150)',
            'slight_favorite': 'Slight Favorites (odds -150 to -110)',
            'pickem_favorite': "Pick'em Favorites (odds -110 to -100)",
            'pickem_underdog': "Pick'em Underdogs (odds +100 to +110)",
            'slight_underdog': 'Slight Underdogs (odds +110 to +150)',
            'moderate_underdog': 'Moderate Underdogs (odds +150 to +200)',
            'strong_underdog': 'Strong Underdogs (odds +200 to +300)',
            'heavy_underdog': 'Heavy Underdogs (odds > +300)'
        }
        for zone_key, enabled in ENABLED_ZONES.items():
            status = "✅ ENABLED" if enabled else "❌ SKIPPED"
            print(f"    {status}: {zone_display_names[zone_key]}")
    
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
    
    # Drop rows with missing market odds
    original_len = len(df)
    df = df.dropna(subset=['moneyline_a', 'moneyline_b'])
    dropped = original_len - len(df)
    
    if dropped > 0:
        print(f"\nDropped {dropped} rows with missing market odds ({dropped/original_len:.1%})")
        print(f"Analyzing {len(df)} games with valid market data")
    
    # Run flat betting analysis
    print_section_header(f"FLAT BETTING ANALYSIS - ${FLAT_BET_SIZE} per bet")
    
    flat_results = simulate_flat_betting_comprehensive(
        df,
        flat_bet_size=FLAT_BET_SIZE,
        min_edge=MIN_EDGE,
        max_edge=MAX_EDGE,
        min_odds=MIN_ODDS,
        max_odds=MAX_ODDS,
        enabled_zones=ENABLED_ZONES if RUN_ZONE_ANALYSIS else None,
        edge_bucket_size=EDGE_BUCKET_SIZE,
        save_csv=SAVE_BETS_CSV,
        output_dir=OUTPUT_DIR
    )
    
    print_flat_results(flat_results, FLAT_BET_SIZE)
    
    # Print detailed breakdowns
    if RUN_ODDS_BUCKET_ANALYSIS and flat_results['odds_buckets']:
        print_section_header("ODDS BUCKET ANALYSIS")
        print_odds_buckets(flat_results['odds_buckets'], flat_results['total_bets'])
    
    if RUN_EDGE_BUCKET_ANALYSIS and flat_results['edge_buckets']:
        print_section_header("EDGE BUCKET ANALYSIS")
        print_edge_buckets(flat_results['edge_buckets'], flat_results['total_bets'], FLAT_BET_SIZE)
    
    if RUN_ZONE_ANALYSIS and any(z['count'] > 0 for z in flat_results['zones'].values()):
        print_section_header("ZONE ANALYSIS")
        print_zone_analysis(flat_results['zones'], flat_results['total_bets'])
    
    # Run Kelly analysis
    if RUN_KELLY_ANALYSIS:
        print_section_header(f"KELLY CRITERION ANALYSIS - {KELLY_CAP*100:.0f}% Kelly Cap")
        
        kelly_results = simulate_kelly_comprehensive(
            df,
            starting_bankroll=KELLY_STARTING_BANKROLL,
            min_edge=MIN_EDGE,
            max_edge=MAX_EDGE,
            kelly_cap=KELLY_CAP,
            min_odds=MIN_ODDS,
            max_odds=MAX_ODDS,
            enabled_zones=ENABLED_ZONES if RUN_ZONE_ANALYSIS else None,
            edge_bucket_size=EDGE_BUCKET_SIZE,
            save_csv=SAVE_BETS_CSV,
            output_dir=OUTPUT_DIR
        )
        
        print(f"\nOverall Performance:")
        print(f"  Total Bets: {kelly_results['total_bets']}")
        print(f"  Wins: {kelly_results['won_bets']}")
        print(f"  Win Rate: {kelly_results['win_rate']:.2f}%")
        print(f"  Starting Bankroll: ${kelly_results['starting_bankroll']:,.2f}")
        print(f"  Ending Bankroll: ${kelly_results['final_bankroll']:,.2f}")
        print(f"  Total Profit: ${kelly_results['total_profit']:,.2f}")
        print(f"  Total Return: {kelly_results['total_return']:+.2f}%")
        print(f"  ROI: {kelly_results['roi']:.2f}%")
        
        if RUN_EDGE_BUCKET_ANALYSIS and kelly_results['edge_buckets']:
            print(f"\nEdge Bucket Breakdown:")
            print("-" * 80)
            for bucket in sorted(kelly_results['edge_buckets'].keys()):
                data = kelly_results['edge_buckets'][bucket]
                win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
                print(f"  {bucket}: {data['count']} bets, {data['wins']} wins ({win_pct:.1f}%), ${data['profit']:,.2f}")
        
        if RUN_ZONE_ANALYSIS and any(z['count'] > 0 for z in kelly_results['zones'].values()):
            print(f"\nZone Breakdown:")
            print("-" * 80)
            for zone_key, zone in kelly_results['zones'].items():
                if zone['count'] > 0:
                    win_rate = (zone['wins'] / zone['count'] * 100) if zone['count'] > 0 else 0
                    print(f"  {zone['name']}: {zone['count']} bets, {zone['wins']} wins ({win_rate:.1f}%), ${zone['profit']:,.2f}")
    
    # Final summary
    print_section_header("SUMMARY")
    print(f"\nFlat Betting (${FLAT_BET_SIZE} per bet):")
    print(f"  Total Profit: ${flat_results['total_profit']:,.2f} ({flat_results['total_profit']/FLAT_BET_SIZE:+.2f} units)")
    print(f"  ROI: {flat_results['roi']:.2f}%")
    print(f"  Win Rate: {flat_results['win_rate']:.2f}%")
    
    if RUN_KELLY_ANALYSIS:
        print(f"\nKelly Criterion ({KELLY_CAP*100:.0f}% cap):")
        print(f"  Total Profit: ${kelly_results['total_profit']:,.2f}")
        print(f"  Total Return: {kelly_results['total_return']:+.2f}%")
        print(f"  Win Rate: {kelly_results['win_rate']:.2f}%")
    
    if flat_results['roi'] > 0:
        print(f"\n✅ Strategy is PROFITABLE with {flat_results['roi']:.2f}% ROI")
    else:
        print(f"\n❌ Strategy is UNPROFITABLE with {flat_results['roi']:.2f}% ROI")


def run_multi_year_analysis():
    """Run analysis across multiple years."""
    flat_results_by_year = {}
    kelly_results_by_year = {}
    
    # Run simulations for each year
    for year in sorted(YEAR_FILES.keys()):
        print(f"\n{'='*80}")
        print(f"YEAR {year}")
        print(f"{'='*80}")
        
        try:
            df = pd.read_csv(YEAR_FILES[year])
            original_len = len(df)
            df = df.dropna(subset=['moneyline_a', 'moneyline_b'])
            
            print(f"Loaded {len(df)} games (dropped {original_len - len(df)} with missing odds)")
            
            # Flat betting
            flat_result = simulate_flat_betting_comprehensive(
                df,
                flat_bet_size=FLAT_BET_SIZE,
                min_edge=MIN_EDGE,
                max_edge=MAX_EDGE,
                min_odds=MIN_ODDS,
                max_odds=MAX_ODDS,
                enabled_zones=ENABLED_ZONES if RUN_ZONE_ANALYSIS else None,
                edge_bucket_size=EDGE_BUCKET_SIZE,
                save_csv=False,  # Don't save individual years in multi-year mode
                output_dir=OUTPUT_DIR
            )
            flat_results_by_year[year] = flat_result
            
            # Kelly betting
            if RUN_KELLY_ANALYSIS:
                kelly_result = simulate_kelly_comprehensive(
                    df,
                    starting_bankroll=KELLY_STARTING_BANKROLL,
                    min_edge=MIN_EDGE,
                    max_edge=MAX_EDGE,
                    kelly_cap=KELLY_CAP,
                    min_odds=MIN_ODDS,
                    max_odds=MAX_ODDS,
                    enabled_zones=ENABLED_ZONES if RUN_ZONE_ANALYSIS else None,
                    edge_bucket_size=EDGE_BUCKET_SIZE,
                    save_csv=False,
                    output_dir=OUTPUT_DIR
                )
                kelly_results_by_year[year] = kelly_result
            
            print(f"\n--- FLAT BETTING (${FLAT_BET_SIZE} per game) ---")
            print(f"Total Bets: {flat_result['total_bets']}")
            print(f"Wins: {flat_result['won_bets']} ({flat_result['win_rate']:.2f}%)")
            print(f"Total Profit: ${flat_result['total_profit']:,.2f}")
            print(f"ROI: {flat_result['roi']:.2f}%")
            
            if RUN_KELLY_ANALYSIS:
                print(f"\n--- QUARTER KELLY (${KELLY_STARTING_BANKROLL:,.0f} starting bankroll) ---")
                print(f"Total Bets: {kelly_result['total_bets']}")
                print(f"Wins: {kelly_result['won_bets']} ({kelly_result['win_rate']:.2f}%)")
                print(f"Starting Bankroll: ${kelly_result['starting_bankroll']:,.2f}")
                print(f"Ending Bankroll: ${kelly_result['final_bankroll']:,.2f}")
                print(f"Total Profit: ${kelly_result['total_profit']:,.2f}")
                print(f"Return: {kelly_result['total_return']:+.2f}%")
            
        except Exception as e:
            print(f"ERROR loading {year}: {e}")
            continue
    
    # Combined summary
    print_section_header("COMBINED RESULTS (2021-2025)")
    
    # Flat betting totals
    print(f"\nFLAT BETTING SUMMARY (${FLAT_BET_SIZE} per bet)")
    print("=" * 80)
    
    total_flat_profit = sum(r['total_profit'] for r in flat_results_by_year.values())
    total_flat_bets = sum(r['total_bets'] for r in flat_results_by_year.values())
    total_flat_wins = sum(r['won_bets'] for r in flat_results_by_year.values())
    total_flat_staked = sum(r['total_staked'] for r in flat_results_by_year.values())
    total_flat_roi = (total_flat_profit / total_flat_staked * 100) if total_flat_staked > 0 else 0
    total_flat_wr = (total_flat_wins / total_flat_bets * 100) if total_flat_bets > 0 else 0
    
    print(f"\nYear-by-Year:")
    print(f"{'Year':<6} {'Bets':<6} {'Wins':<6} {'Win%':<8} {'Profit':<12} {'ROI':<8}")
    print("-" * 80)
    for year in sorted(flat_results_by_year.keys()):
        r = flat_results_by_year[year]
        print(f"{year:<6} {r['total_bets']:<6} {r['won_bets']:<6} "
              f"{r['win_rate']:>6.2f}%  ${r['total_profit']:>9,.2f}  {r['roi']:>6.2f}%")
    
    print("-" * 80)
    print(f"{'TOTAL':<6} {total_flat_bets:<6} {total_flat_wins:<6} "
          f"{total_flat_wr:>6.2f}%  ${total_flat_profit:>9,.2f}  {total_flat_roi:>6.2f}%")
    
    # Edge bucket analysis across all years
    if RUN_EDGE_BUCKET_ANALYSIS:
        print(f"\n\nEDGE BUCKET ANALYSIS ({EDGE_BUCKET_SIZE*100:.1f}% buckets)")
        print("=" * 80)
        
        combined_edge_buckets = {}
        for year_result in flat_results_by_year.values():
            for bucket, data in year_result['edge_buckets'].items():
                if bucket not in combined_edge_buckets:
                    combined_edge_buckets[bucket] = {'count': 0, 'wins': 0, 'profit': 0}
                combined_edge_buckets[bucket]['count'] += data['count']
                combined_edge_buckets[bucket]['wins'] += data['wins']
                combined_edge_buckets[bucket]['profit'] += data['profit']
        
        print(f"\n{'Edge Bucket':<15} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
        print("-" * 90)
        
        for bucket in sorted(combined_edge_buckets.keys()):
            data = combined_edge_buckets[bucket]
            win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
            bet_pct = (data['count'] / total_flat_bets * 100) if total_flat_bets > 0 else 0
            bucket_roi = (data['profit'] / (data['count'] * FLAT_BET_SIZE) * 100) if data['count'] > 0 else 0
            print(f"{bucket:<15} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  {bet_pct:>8.2f}%  "
                  f"${data['profit']:>9,.2f}  {bucket_roi:>6.2f}%")
    
    # Kelly betting totals
    if RUN_KELLY_ANALYSIS and kelly_results_by_year:
        print(f"\n\nKELLY BETTING SUMMARY (${KELLY_STARTING_BANKROLL:,.0f} starting bankroll each year)")
        print("=" * 80)
        
        print(f"\nYear-by-Year:")
        print(f"{'Year':<6} {'Bets':<6} {'Starting':<12} {'Ending':<12} {'Profit':<12} {'Return':<10}")
        print("-" * 80)
        
        total_kelly_profit = 0
        total_kelly_bets = 0
        
        for year in sorted(kelly_results_by_year.keys()):
            r = kelly_results_by_year[year]
            total_kelly_profit += r['total_profit']
            total_kelly_bets += r['total_bets']
            print(f"{year:<6} {r['total_bets']:<6} ${r['starting_bankroll']:>9,.2f}  "
                  f"${r['final_bankroll']:>9,.2f}  ${r['total_profit']:>9,.2f}  {r['total_return']:>7.2f}%")
        
        avg_kelly_return = (total_kelly_profit / (KELLY_STARTING_BANKROLL * len(kelly_results_by_year)) * 100) if len(kelly_results_by_year) > 0 else 0
        
        print("-" * 80)
        print(f"Total Bets: {total_kelly_bets}")
        print(f"Total Profit: ${total_kelly_profit:,.2f}")
        print(f"Average Return per Year: {avg_kelly_return:+.2f}%")
    
    # Final verdict
    print_section_header("FINAL VERDICT")
    
    print(f"\nFlat Betting (${FLAT_BET_SIZE} per bet):")
    print(f"  Total Profit: ${total_flat_profit:,.2f} ({total_flat_profit/FLAT_BET_SIZE:+.2f} units)")
    print(f"  ROI: {total_flat_roi:.2f}%")
    print(f"  Win Rate: {total_flat_wr:.2f}%")
    print(f"  Winning Years: {sum(1 for r in flat_results_by_year.values() if r['total_profit'] > 0)}/{len(flat_results_by_year)}")
    
    if RUN_KELLY_ANALYSIS and kelly_results_by_year:
        print(f"\nKelly Betting ({KELLY_CAP*100:.0f}% cap):")
        print(f"  Total Profit: ${total_kelly_profit:,.2f}")
        print(f"  Avg Return: {avg_kelly_return:+.2f}% per year")
        print(f"  Winning Years: {sum(1 for r in kelly_results_by_year.values() if r['total_profit'] > 0)}/{len(kelly_results_by_year)}")
    
    if total_flat_roi > 0:
        print(f"\n✅ Strategy is PROFITABLE with {total_flat_roi:.2f}% ROI")
    else:
        print(f"\n❌ Strategy is UNPROFITABLE with {total_flat_roi:.2f}% ROI")


if __name__ == "__main__":
    main()