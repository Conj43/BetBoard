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
FILE_PATH = f"{DIRECTORY}/total_predictions_{YEAR}.csv"
OUTPUT_DIR = "services/ml/models/xg_model/analysis/total/results"

# Multi-year analysis configuration
MULTI_YEAR_ANALYSIS = True  # Set to True to run analysis across multiple years
YEAR_FILES = {
    2021: 'data/xgb_model/2021_No_Bet_xgb_all_models_20251014_153704/total_predictions_2021.csv',
    2022: 'data/xgb_model/2022_No_Bet_xgb_all_models_20251014_153652/total_predictions_2022.csv',
    2023: 'data/xgb_model/2023_No_Bet_xgb_all_models_20251014_153638/total_predictions_2023.csv',
    2024: 'data/xgb_model/2024_No_Bet_xgb_all_models_20251014_153613/total_predictions_2024.csv',
    2025: 'data/xgb_model/2025_No_Bet_xgb_all_models_20251014_153554/total_predictions_2025.csv',
}

# Betting parameters
FLAT_BET_SIZE = 100  # Dollar amount per bet
MIN_EDGE = 0  # Minimum edge threshold (in points)
MAX_EDGE = 100  # Maximum edge threshold (in points)
EDGE_BUCKET_SIZE = 2  # Size of edge buckets for analysis (in points)

# Default odds (typical for totals betting)
DEFAULT_OVER_ODDS = -110  # Standard vig for over
DEFAULT_UNDER_ODDS = -110  # Standard vig for under

# Kelly Criterion parameters
KELLY_STARTING_BANKROLL = 10000  # Starting bankroll for Kelly simulations
KELLY_CAP = 0.25  # Kelly fraction cap (0.25 = quarter Kelly)

# Edge zone configuration - which edge ranges to bet on (set to True/False)
ENABLED_ZONES = {
    'tiny_edge': True,         # 0-2 points
    'small_edge': True,        # 2-4 points
    'medium_edge': True,       # 4-6 points
    'large_edge': True,        # 6-8 points
    'huge_edge': True,         # 8+ points
}

# Point zone configuration - which total points ranges to bet on (set to True/False)
# Based on your data: 140-150 is the sweet spot with 67% win rate!
ENABLED_POINT_ZONES = {
    'very_low': True,         # Under 120 points (29% win rate - AVOID!)
    'low': True,              # 120-130 points (38% win rate - AVOID!)
    'below_avg': True,         # 130-140 points (57% win rate)
    'average': True,           # 140-150 points (66% win rate - BEST!)
    'above_avg': True,         # 150-160 points (55% win rate)
    'high': True,             # 160-170 points (42% win rate - AVOID!)
    'very_high': True,        # 170+ points (32% win rate - AVOID!)
}

# Analysis toggles
RUN_EDGE_BUCKET_ANALYSIS = True  # Detailed breakdown by edge ranges
RUN_ZONE_ANALYSIS = True         # Analysis of specific edge zones
RUN_KELLY_ANALYSIS = False        # Kelly Criterion simulations
RUN_DIRECTIONAL_ANALYSIS = True  # Over vs Under breakdown
RUN_TOTAL_POINTS_ANALYSIS = True  # Analysis by total points scored
RUN_LINE_MARGIN_ANALYSIS = True   # Analysis by how close actual was to line

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


def get_edge_zone(edge_abs):
    """Categorize absolute edge into zones."""
    if edge_abs < 2:
        return 'tiny_edge'
    elif edge_abs < 4:
        return 'small_edge'
    elif edge_abs < 6:
        return 'medium_edge'
    elif edge_abs < 8:
        return 'large_edge'
    else:
        return 'huge_edge'


def get_edge_bucket(edge_abs, bucket_size=2):
    """Assign edge to a bucket based on bucket_size."""
    bucket_num = int(edge_abs / bucket_size)
    bucket_start = bucket_num * bucket_size
    bucket_end = bucket_start + bucket_size
    return f"{bucket_start:.1f}-{bucket_end:.1f}"


def get_total_points_bucket(total_points):
    """Categorize games by total points scored."""
    if total_points < 120:
        return "Under 120"
    elif total_points < 130:
        return "120-130"
    elif total_points < 140:
        return "130-140"
    elif total_points < 150:
        return "140-150"
    elif total_points < 160:
        return "150-160"
    elif total_points < 170:
        return "160-170"
    else:
        return "170+"


def get_line_margin_bucket(line_margin):
    """Categorize by how close actual total was to betting line."""
    abs_margin = abs(line_margin)
    if abs_margin < 5:
        return "0-5 (Very Close)"
    elif abs_margin < 10:
        return "5-10 (Close)"
    elif abs_margin < 15:
        return "10-15 (Moderate)"
    elif abs_margin < 20:
        return "15-20 (Far)"
    else:
        return "20+ (Very Far)"


def get_point_zone(pred_total):
    """Categorize predicted total into zones."""
    if pred_total < 120:
        return 'very_low'
    elif pred_total < 130:
        return 'low'
    elif pred_total < 140:
        return 'below_avg'
    elif pred_total < 150:
        return 'average'
    elif pred_total < 160:
        return 'above_avg'
    elif pred_total < 170:
        return 'high'
    else:
        return 'very_high'


def simulate_flat_betting_comprehensive(df, flat_bet_size=100, min_edge=0, max_edge=100,
                                       over_odds=-110, under_odds=-110,
                                       enabled_zones=None, enabled_point_zones=None,
                                       edge_bucket_size=2, save_csv=False, output_dir=None):
    """
    Comprehensive flat betting simulation for over/under betting.
    """
    total_bets = 0
    won_bets = 0
    total_staked = 0
    total_profit = 0
    
    over_bets = []
    under_bets = []
    edge_buckets = {}
    zones = {
        'tiny_edge': {'name': 'Tiny Edge (0-2 pts)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'small_edge': {'name': 'Small Edge (2-4 pts)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'medium_edge': {'name': 'Medium Edge (4-6 pts)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'large_edge': {'name': 'Large Edge (6-8 pts)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
        'huge_edge': {'name': 'Huge Edge (8+ pts)', 'count': 0, 'wins': 0, 'profit': 0, 'staked': 0},
    }
    
    # NEW: Total points buckets
    total_points_buckets = {}
    
    # NEW: Line margin buckets
    line_margin_buckets = {}
    
    all_bets = []
    
    # DEBUG: Check if filtering is happening
    total_games = len(df)
    skipped_by_point_zone = 0
    
    for idx, game in df.iterrows():
        if pd.isna(game.get('bet_total')) or pd.isna(game.get('pred_total')):
            continue

        pred_total = game['pred_total']
        bet_line = game['bet_total']
        true_total = game.get('true_total', 0)
        edge = pred_total - bet_line
        edge_abs = abs(edge)
        
        # NEW: Calculate line margin (how far actual was from line)
        line_margin = true_total - bet_line
        
        # Get odds (from CSV if available, otherwise use defaults)
        if 'over_odds' in game and not pd.isna(game['over_odds']):
            current_over_odds = game['over_odds']
        else:
            current_over_odds = over_odds
            
        if 'under_odds' in game and not pd.isna(game['under_odds']):
            current_under_odds = game['under_odds']
        else:
            current_under_odds = under_odds

        # Edge filter
        if edge_abs < min_edge or edge_abs > max_edge:
            continue

        # Zone filter
        zone = get_edge_zone(edge_abs)
        if enabled_zones is not None:
            if zone not in enabled_zones or not enabled_zones[zone]:
                continue
        
        # Point zone filter
        point_zone = get_point_zone(pred_total)
        if enabled_point_zones is not None:
            if point_zone not in enabled_point_zones or not enabled_point_zones[point_zone]:
                skipped_by_point_zone += 1
                continue
        
        # Point zone filter
        point_zone = get_point_zone(pred_total)
        if enabled_point_zones is not None:
            if point_zone not in enabled_point_zones or not enabled_point_zones[point_zone]:
                continue

        # Determine bet side
        if edge > 0:
            # Bet OVER
            bet_side = 'Over'
            chosen_odds = current_over_odds
            actual_result = game['actual_over']
            bet_won = (actual_result == 1)
        else:
            # Bet UNDER
            bet_side = 'Under'
            chosen_odds = current_under_odds
            actual_result = game['actual_over']
            bet_won = (actual_result == 0)

        # Place bet
        bet_amount = flat_bet_size
        total_staked += bet_amount
        total_bets += 1

        decimal_odds = odds_to_decimal(chosen_odds)
        if bet_won:
            profit = bet_amount * (decimal_odds - 1)
            won_bets += 1
        else:
            profit = -bet_amount

        total_profit += profit
        
        # Track by edge bucket
        edge_bucket = get_edge_bucket(edge_abs, edge_bucket_size)
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
        
        # NEW: Track by total points bucket
        total_bucket = get_total_points_bucket(true_total)
        if total_bucket not in total_points_buckets:
            total_points_buckets[total_bucket] = {'count': 0, 'wins': 0, 'profit': 0, 'staked': 0}
        total_points_buckets[total_bucket]['count'] += 1
        total_points_buckets[total_bucket]['wins'] += (1 if bet_won else 0)
        total_points_buckets[total_bucket]['profit'] += profit
        total_points_buckets[total_bucket]['staked'] += bet_amount
        
        # NEW: Track by line margin bucket
        margin_bucket = get_line_margin_bucket(line_margin)
        if margin_bucket not in line_margin_buckets:
            line_margin_buckets[margin_bucket] = {'count': 0, 'wins': 0, 'profit': 0, 'staked': 0}
        line_margin_buckets[margin_bucket]['count'] += 1
        line_margin_buckets[margin_bucket]['wins'] += (1 if bet_won else 0)
        line_margin_buckets[margin_bucket]['profit'] += profit
        line_margin_buckets[margin_bucket]['staked'] += bet_amount
        
        # Track over vs under
        bet_info = {
            'edge': edge,
            'edge_abs': edge_abs,
            'won': bet_won,
            'profit': profit
        }
        
        if bet_side == 'Over':
            over_bets.append(bet_info)
        else:
            under_bets.append(bet_info)

        # Record bet details
        bet_record = {
            'date': game.get('date', ''),
            'game_id': game.get('game_id', idx),
            'team_a': game.get('team_A', 'Team A'),
            'team_b': game.get('team_B', 'Team B'),
            'bet_line': bet_line,
            'pred_total': pred_total,
            'true_total': true_total,
            'line_margin': line_margin,
            'total_points_bucket': total_bucket,
            'line_margin_bucket': margin_bucket,
            'bet_side': bet_side,
            'chosen_odds': chosen_odds,
            'edge': edge,
            'edge_abs': edge_abs,
            'edge_bucket': edge_bucket,
            'zone': zones[zone]['name'] if zone in zones else 'Other',
            'bet_amount': bet_amount,
            'bet_won': bet_won,
            'profit': profit,
        }
        all_bets.append(bet_record)

    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
    win_rate = (won_bets / total_bets * 100) if total_bets > 0 else 0
    avg_edge = (sum([r['edge_abs'] for r in all_bets]) / len(all_bets)) if all_bets else 0

    # Save bets to CSV if requested
    if save_csv and output_dir and all_bets:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(output_dir, f"flat_bets_totals_{timestamp}.csv")
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
        'over_bets': over_bets,
        'under_bets': under_bets,
        'edge_buckets': edge_buckets,
        'zones': zones,
        'total_points_buckets': total_points_buckets,
        'line_margin_buckets': line_margin_buckets,
        'all_bets': all_bets
    }


def simulate_kelly_comprehensive(df, starting_bankroll=10000, min_edge=0, max_edge=100,
                                kelly_cap=0.25, over_odds=-110, under_odds=-110,
                                enabled_zones=None, enabled_point_zones=None,
                                edge_bucket_size=2, save_csv=False, output_dir=None):
    """
    Comprehensive Kelly Criterion simulation for over/under betting.
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
        'tiny_edge': {'name': 'Tiny Edge (0-2 pts)', 'count': 0, 'wins': 0, 'profit': 0},
        'small_edge': {'name': 'Small Edge (2-4 pts)', 'count': 0, 'wins': 0, 'profit': 0},
        'medium_edge': {'name': 'Medium Edge (4-6 pts)', 'count': 0, 'wins': 0, 'profit': 0},
        'large_edge': {'name': 'Large Edge (6-8 pts)', 'count': 0, 'wins': 0, 'profit': 0},
        'huge_edge': {'name': 'Huge Edge (8+ pts)', 'count': 0, 'wins': 0, 'profit': 0},
    }
    
    all_bets = []

    for idx, game in work.iterrows():
        if pd.isna(game.get('bet_total')) or pd.isna(game.get('pred_total')):
            continue

        pred_total = float(game['pred_total'])
        bet_line = float(game['bet_total'])
        edge = pred_total - bet_line
        edge_abs = abs(edge)
        
        # Get odds
        if 'over_odds' in game and not pd.isna(game['over_odds']):
            current_over_odds = float(game['over_odds'])
        else:
            current_over_odds = over_odds
            
        if 'under_odds' in game and not pd.isna(game['under_odds']):
            current_under_odds = float(game['under_odds'])
        else:
            current_under_odds = under_odds

        if edge_abs < min_edge or edge_abs > max_edge:
            continue

        zone = get_edge_zone(edge_abs)
        if enabled_zones is not None:
            if zone not in enabled_zones or not enabled_zones[zone]:
                continue

        # Determine bet side and calculate probability
        if edge > 0:
            # Bet OVER
            bet_side = 'Over'
            chosen_odds = current_over_odds
            # Estimate prob based on edge (simplified)
            our_prob = 0.5 + min(edge_abs / 20, 0.35)  # Cap at 85%
            actual_result = game['actual_over']
            bet_won = (actual_result == 1)
        else:
            # Bet UNDER
            bet_side = 'Under'
            chosen_odds = current_under_odds
            our_prob = 0.5 + min(edge_abs / 20, 0.35)
            actual_result = game['actual_over']
            bet_won = (actual_result == 0)

        dec_odds = odds_to_decimal(chosen_odds)
        frac = kelly_fraction(our_prob, dec_odds, max_kelly=kelly_cap)
        
        if frac <= 0.0 or current_bankroll <= 0:
            continue

        bet_amount = current_bankroll * frac
        if bet_amount < 1e-6:
            continue

        total_staked += bet_amount
        total_bets += 1

        if bet_won:
            profit = bet_amount * (dec_odds - 1.0)
            won_bets += 1
        else:
            profit = -bet_amount

        current_bankroll += profit
        total_profit += profit
        
        # Track by edge bucket
        edge_bucket = get_edge_bucket(edge_abs, edge_bucket_size)
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
            'team_a': game.get('team_A', 'Team A'),
            'team_b': game.get('team_B', 'Team B'),
            'bet_line': bet_line,
            'pred_total': pred_total,
            'true_total': game.get('true_total', 0),
            'bet_side': bet_side,
            'chosen_odds': chosen_odds,
            'edge': edge,
            'edge_abs': edge_abs,
            'edge_bucket': edge_bucket,
            'zone': zones[zone]['name'] if zone in zones else 'Other',
            'our_prob': our_prob,
            'bankroll_before': current_bankroll - profit,
            'kelly_fraction': frac,
            'bet_amount': bet_amount,
            'bet_won': bet_won,
            'profit': profit,
            'bankroll_after': current_bankroll,
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
        csv_path = os.path.join(output_dir, f"kelly_bets_totals_{timestamp}.csv")
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
    print(f"  Average Edge: {results['avg_edge']:.2f} points")
    
    # Over vs Under
    over_bets = results['over_bets']
    under_bets = results['under_bets']
    
    if over_bets or under_bets:
        print(f"\nOver vs Under Breakdown:")
        
        if over_bets:
            over_wins = sum(1 for b in over_bets if b['won'])
            over_profit = sum(b['profit'] for b in over_bets)
            over_avg_edge = sum(b['edge_abs'] for b in over_bets) / len(over_bets)
            print(f"  OVER Bets: {len(over_bets)} bets ({len(over_bets)/results['total_bets']:.1%})")
            print(f"    Win Rate: {over_wins/len(over_bets):.2%}")
            print(f"    Profit: ${over_profit:,.2f}")
            print(f"    Avg Edge: {over_avg_edge:.2f} pts")
            print(f"    ROI: {(over_profit/(bet_size*len(over_bets)))*100:.2f}%")
        
        if under_bets:
            under_wins = sum(1 for b in under_bets if b['won'])
            under_profit = sum(b['profit'] for b in under_bets)
            under_avg_edge = sum(b['edge_abs'] for b in under_bets) / len(under_bets)
            print(f"  UNDER Bets: {len(under_bets)} bets ({len(under_bets)/results['total_bets']:.1%})")
            print(f"    Win Rate: {under_wins/len(under_bets):.2%}")
            print(f"    Profit: ${under_profit:,.2f}")
            print(f"    Avg Edge: {under_avg_edge:.2f} pts")
            print(f"    ROI: {(under_profit/(bet_size*len(under_bets)))*100:.2f}%")


def print_edge_buckets(edge_buckets, total_bets, bet_size):
    """Print edge bucket analysis."""
    print(f"\nBreakdown by Edge Bucket:")
    print("-" * 80)
    print(f"{'Edge Range':<15} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
    print("-" * 80)
    
    for bucket in sorted(edge_buckets.keys(), key=lambda x: float(x.split('-')[0])):
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
    
    zone_display_order = ['tiny_edge', 'small_edge', 'medium_edge', 'large_edge', 'huge_edge']
    
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


def print_total_points_analysis(total_points_buckets, total_bets, bet_size):
    """Print analysis by total points scored in game."""
    print(f"\nBreakdown by Total Points Scored:")
    print("-" * 80)
    print(f"{'Points Range':<15} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
    print("-" * 80)
    
    bucket_order = ["Under 120", "120-130", "130-140", "140-150", "150-160", "160-170", "170+"]
    
    for bucket in bucket_order:
        if bucket in total_points_buckets and total_points_buckets[bucket]['count'] > 0:
            data = total_points_buckets[bucket]
            win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
            bet_pct = (data['count'] / total_bets * 100) if total_bets > 0 else 0
            bucket_roi = (data['profit'] / (data['count'] * bet_size) * 100) if data['count'] > 0 else 0
            
            print(f"{bucket:<15} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  "
                  f"{bet_pct:>8.2f}%  ${data['profit']:>9,.2f}  {bucket_roi:>6.2f}%")


def print_line_margin_analysis(line_margin_buckets, total_bets, bet_size):
    """Print analysis by how close actual total was to betting line."""
    print(f"\nBreakdown by Distance from Line (Actual - Line):")
    print("-" * 80)
    print(f"{'Margin Range':<20} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
    print("-" * 80)
    
    bucket_order = ["0-5 (Very Close)", "5-10 (Close)", "10-15 (Moderate)", "15-20 (Far)", "20+ (Very Far)"]
    
    for bucket in bucket_order:
        if bucket in line_margin_buckets and line_margin_buckets[bucket]['count'] > 0:
            data = line_margin_buckets[bucket]
            win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
            bet_pct = (data['count'] / total_bets * 100) if total_bets > 0 else 0
            bucket_roi = (data['profit'] / (data['count'] * bet_size) * 100) if data['count'] > 0 else 0
            
            print(f"{bucket:<20} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  "
                  f"{bet_pct:>8.2f}%  ${data['profit']:>9,.2f}  {bucket_roi:>6.2f}%")


def main():
    # Setup output file if saving
    if SAVE_TO_FILE:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"totals_betting_analysis_{timestamp}.txt")
        dual_output = DualOutput(output_file)
        sys.stdout = dual_output
        print(f"Output will be saved to: {output_file}")
    
    print_section_header("OVER/UNDER BETTING ANALYSIS")
    
    # Print configuration
    print(f"\nConfiguration:")
    print(f"  Flat Bet Size: ${FLAT_BET_SIZE}")
    print(f"  Edge Range: {MIN_EDGE} - {MAX_EDGE} points")
    print(f"  Edge Bucket Size: {EDGE_BUCKET_SIZE} points")
    print(f"  Default Over Odds: {DEFAULT_OVER_ODDS}")
    print(f"  Default Under Odds: {DEFAULT_UNDER_ODDS}")
    print(f"  Kelly Starting Bankroll: ${KELLY_STARTING_BANKROLL:,.0f}")
    print(f"  Kelly Cap: {KELLY_CAP*100:.0f}%")
    
    if any(ENABLED_ZONES.values()):
        print(f"\n  Active Edge Zones:")
        zone_display_names = {
            'tiny_edge': 'Tiny Edge (0-2 points)',
            'small_edge': 'Small Edge (2-4 points)',
            'medium_edge': 'Medium Edge (4-6 points)',
            'large_edge': 'Large Edge (6-8 points)',
            'huge_edge': 'Huge Edge (8+ points)'
        }
        for zone_key, enabled in ENABLED_ZONES.items():
            status = "✅ ENABLED" if enabled else "❌ SKIPPED"
            print(f"    {status}: {zone_display_names[zone_key]}")
    
    if any(ENABLED_POINT_ZONES.values()):
        print(f"\n  Active Point Zones:")
        point_zone_display_names = {
            'very_low': 'Very Low Scoring (Under 120 pts)',
            'low': 'Low Scoring (120-130 pts)',
            'below_avg': 'Below Average (130-140 pts)',
            'average': 'Average Scoring (140-150 pts)',
            'above_avg': 'Above Average (150-160 pts)',
            'high': 'High Scoring (160-170 pts)',
            'very_high': 'Very High Scoring (170+ pts)'
        }
        for zone_key, enabled in ENABLED_POINT_ZONES.items():
            status = "✅ ENABLED" if enabled else "❌ SKIPPED"
            print(f"    {status}: {point_zone_display_names[zone_key]}")
    
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
    df = df.dropna(subset=['bet_total', 'pred_total', 'actual_over'])
    dropped = original_len - len(df)
    
    if dropped > 0:
        print(f"\nDropped {dropped} rows with missing data ({dropped/original_len:.1%})")
        print(f"Analyzing {len(df)} games with valid data")
    
    # Run flat betting analysis
    print_section_header(f"FLAT BETTING ANALYSIS - ${FLAT_BET_SIZE} per bet")
    
    flat_results = simulate_flat_betting_comprehensive(
        df,
        flat_bet_size=FLAT_BET_SIZE,
        min_edge=MIN_EDGE,
        max_edge=MAX_EDGE,
        over_odds=DEFAULT_OVER_ODDS,
        under_odds=DEFAULT_UNDER_ODDS,
        enabled_zones=ENABLED_ZONES if any(ENABLED_ZONES.values()) else None,
        enabled_point_zones=ENABLED_POINT_ZONES if any(ENABLED_POINT_ZONES.values()) else None,
        edge_bucket_size=EDGE_BUCKET_SIZE,
        save_csv=SAVE_BETS_CSV,
        output_dir=OUTPUT_DIR
    )
    
    print_flat_results(flat_results, FLAT_BET_SIZE)
    
    # Print detailed breakdowns
    if RUN_EDGE_BUCKET_ANALYSIS and flat_results['edge_buckets']:
        print_section_header("EDGE BUCKET ANALYSIS")
        print_edge_buckets(flat_results['edge_buckets'], flat_results['total_bets'], FLAT_BET_SIZE)
    
    if RUN_ZONE_ANALYSIS and any(z['count'] > 0 for z in flat_results['zones'].values()):
        print_section_header("ZONE ANALYSIS")
        print_zone_analysis(flat_results['zones'], flat_results['total_bets'])
    
    # NEW: Total points analysis
    if RUN_TOTAL_POINTS_ANALYSIS and flat_results['total_points_buckets']:
        print_section_header("TOTAL POINTS ANALYSIS")
        print_total_points_analysis(flat_results['total_points_buckets'], flat_results['total_bets'], FLAT_BET_SIZE)
    
    # NEW: Line margin analysis
    if RUN_LINE_MARGIN_ANALYSIS and flat_results['line_margin_buckets']:
        print_section_header("LINE MARGIN ANALYSIS")
        print_line_margin_analysis(flat_results['line_margin_buckets'], flat_results['total_bets'], FLAT_BET_SIZE)
    
    # Run Kelly analysis
    if RUN_KELLY_ANALYSIS:
        print_section_header(f"KELLY CRITERION ANALYSIS - {KELLY_CAP*100:.0f}% Kelly Cap")
        
        kelly_results = simulate_kelly_comprehensive(
            df,
            starting_bankroll=KELLY_STARTING_BANKROLL,
            min_edge=MIN_EDGE,
            max_edge=MAX_EDGE,
            kelly_cap=KELLY_CAP,
            over_odds=DEFAULT_OVER_ODDS,
            under_odds=DEFAULT_UNDER_ODDS,
            enabled_zones=ENABLED_ZONES if any(ENABLED_ZONES.values()) else None,
            enabled_point_zones=ENABLED_POINT_ZONES if any(ENABLED_POINT_ZONES.values()) else None,
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
            for bucket in sorted(kelly_results['edge_buckets'].keys(), key=lambda x: float(x.split('-')[0])):
                data = kelly_results['edge_buckets'][bucket]
                win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
                print(f"  {bucket}: {data['count']} bets, {data['wins']} wins ({win_pct:.1f}%), ${data['profit']:,.2f}")
        
        if RUN_ZONE_ANALYSIS and any(z['count'] > 0 for z in kelly_results['zones'].values()):
            print(f"\nZone Breakdown:")
            print("-" * 80)
            for zone_key in ['tiny_edge', 'small_edge', 'medium_edge', 'large_edge', 'huge_edge']:
                zone = kelly_results['zones'][zone_key]
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
            df = df.dropna(subset=['bet_total', 'pred_total', 'actual_over'])
            
            print(f"Loaded {len(df)} games (dropped {original_len - len(df)} with missing data)")
            
            # Flat betting
            flat_result = simulate_flat_betting_comprehensive(
                df,
                flat_bet_size=FLAT_BET_SIZE,
                min_edge=MIN_EDGE,
                max_edge=MAX_EDGE,
                over_odds=DEFAULT_OVER_ODDS,
                under_odds=DEFAULT_UNDER_ODDS,
                enabled_zones=ENABLED_ZONES if any(ENABLED_ZONES.values()) else None,
                enabled_point_zones=ENABLED_POINT_ZONES if any(ENABLED_POINT_ZONES.values()) else None,
                edge_bucket_size=EDGE_BUCKET_SIZE,
                save_csv=False,
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
                    over_odds=DEFAULT_OVER_ODDS,
                    under_odds=DEFAULT_UNDER_ODDS,
                    enabled_zones=ENABLED_ZONES if any(ENABLED_ZONES.values()) else None,
                    enabled_point_zones=ENABLED_POINT_ZONES if any(ENABLED_POINT_ZONES.values()) else None,
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
        print(f"\n\nEDGE BUCKET ANALYSIS ({EDGE_BUCKET_SIZE} point buckets)")
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
        
        for bucket in sorted(combined_edge_buckets.keys(), key=lambda x: float(x.split('-')[0])):
            data = combined_edge_buckets[bucket]
            win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
            bet_pct = (data['count'] / total_flat_bets * 100) if total_flat_bets > 0 else 0
            bucket_roi = (data['profit'] / (data['count'] * FLAT_BET_SIZE) * 100) if data['count'] > 0 else 0
            print(f"{bucket:<15} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  {bet_pct:>8.2f}%  "
                  f"${data['profit']:>9,.2f}  {bucket_roi:>6.2f}%")
    
    # NEW: Combined total points analysis
    if RUN_TOTAL_POINTS_ANALYSIS:
        print(f"\n\nTOTAL POINTS ANALYSIS (Combined 2021-2025)")
        print("=" * 80)
        
        combined_total_points = {}
        for year_result in flat_results_by_year.values():
            for bucket, data in year_result['total_points_buckets'].items():
                if bucket not in combined_total_points:
                    combined_total_points[bucket] = {'count': 0, 'wins': 0, 'profit': 0}
                combined_total_points[bucket]['count'] += data['count']
                combined_total_points[bucket]['wins'] += data['wins']
                combined_total_points[bucket]['profit'] += data['profit']
        
        print(f"\n{'Points Range':<15} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
        print("-" * 90)
        
        bucket_order = ["Under 120", "120-130", "130-140", "140-150", "150-160", "160-170", "170+"]
        for bucket in bucket_order:
            if bucket in combined_total_points and combined_total_points[bucket]['count'] > 0:
                data = combined_total_points[bucket]
                win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
                bet_pct = (data['count'] / total_flat_bets * 100) if total_flat_bets > 0 else 0
                bucket_roi = (data['profit'] / (data['count'] * FLAT_BET_SIZE) * 100) if data['count'] > 0 else 0
                print(f"{bucket:<15} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  {bet_pct:>8.2f}%  "
                      f"${data['profit']:>9,.2f}  {bucket_roi:>6.2f}%")
    
    # NEW: Combined line margin analysis
    if RUN_LINE_MARGIN_ANALYSIS:
        print(f"\n\nLINE MARGIN ANALYSIS (Combined 2021-2025)")
        print("=" * 80)
        
        combined_line_margin = {}
        for year_result in flat_results_by_year.values():
            for bucket, data in year_result['line_margin_buckets'].items():
                if bucket not in combined_line_margin:
                    combined_line_margin[bucket] = {'count': 0, 'wins': 0, 'profit': 0}
                combined_line_margin[bucket]['count'] += data['count']
                combined_line_margin[bucket]['wins'] += data['wins']
                combined_line_margin[bucket]['profit'] += data['profit']
        
        print(f"\n{'Margin Range':<20} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
        print("-" * 90)
        
        bucket_order = ["0-5 (Very Close)", "5-10 (Close)", "10-15 (Moderate)", "15-20 (Far)", "20+ (Very Far)"]
        for bucket in bucket_order:
            if bucket in combined_line_margin and combined_line_margin[bucket]['count'] > 0:
                data = combined_line_margin[bucket]
                win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
                bet_pct = (data['count'] / total_flat_bets * 100) if total_flat_bets > 0 else 0
                bucket_roi = (data['profit'] / (data['count'] * FLAT_BET_SIZE) * 100) if data['count'] > 0 else 0
                print(f"{bucket:<20} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  {bet_pct:>8.2f}%  "
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