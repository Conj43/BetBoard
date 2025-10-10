"""
Unified Betting Analysis Framework
Run all analyses at once with a single configuration file
"""
import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
from pathlib import Path

# ============================================================================
# CONFIGURATION - Edit this section for your experiments
# ============================================================================

CONFIG = {
    # Data files
    'data_files': {
        2021: 'data/xgb_model/2021_xgb_all_models_20251009_202637/moneyline_predictions_2021.csv',
        2022: 'data/xgb_model/2022_xgb_all_models_20251009_202214/moneyline_predictions_2022.csv',
        2023: 'data/xgb_model/2023_xgb_all_models_20251009_200335/moneyline_predictions_2023.csv',
        2024: 'data/xgb_model/2024_xgb_all_models_20251009_200100/moneyline_predictions_2024.csv',
        2025: 'data/xgb_model/2025_xgb_all_models_20251009_194955/moneyline_predictions_2025.csv',
    },
    
    # Output configuration
    'output_dir': 'services/ml/models/xg_model/analysis/moneyline/results',
    'experiment_name': 'full_analysis',  # Change this for each experiment
    
    # Betting parameters
    'flat_bet_size': 100,
    'kelly_starting_bankroll': 10000,
    'kelly_fraction': 0.25,
    
    # Filters
    'min_edge': 0.000,
    'max_edge': 0.0471,
    'min_odds': None,  # Set to filter odds range (e.g., -300)
    'max_odds': None,  # Set to filter odds range (e.g., +150)
    
    # Zone configuration (LEGACY - use odds_buckets_enabled instead)
    'enabled_zones': {
        'heavy_favorite': True,      # odds < -300
        'pickem_underdog': True,     # odds +100 to +110
        'slight_underdog': True,     # odds +110 to +150
    },
    
    # Bucket configurations
    'edge_bucket_size': 0.005,  # 0.5% edge buckets
    'odds_buckets': [
        ('Heavy Favorite', -10000, -300),
        ('Strong Favorite', -300, -200),
        ('Moderate Favorite', -200, -150),
        ('Slight Favorite', -150, -110),
        ('Pickem Favorite', -110, 0),
        ('Pickem Underdog', 0, 110),
        ('Slight Underdog', 110, 150),
        ('Moderate Underdog', 150, 200),
        ('Strong Underdog', 200, 300),
        ('Heavy Underdog', 300, 10000),
    ],
    
    # Enable/disable specific odds buckets for betting
    'odds_buckets_enabled': {
        'Heavy Favorite': True,
        'Strong Favorite': False,
        'Moderate Favorite': False,
        'Slight Favorite': False,
        'Pickem Favorite': False,
        'Pickem Underdog': True,
        'Slight Underdog': True,
        'Moderate Underdog': False,  # Example: disable this bucket
        'Strong Underdog': False,
        'Heavy Underdog': False,
    },
    
    # Analysis flags - Turn on/off different analyses
    'run_calibration': True,      # Check model calibration
    'run_edge_buckets': True,     # Analyze by edge buckets
    'run_odds_buckets': True,     # Analyze by odds buckets
    'run_zone_analysis': True,    # Analyze by betting zones
    'run_baseline_comparison': True,  # Compare to random/market baseline
    'run_yearly_breakdown': True, # Year-by-year results
    'save_all_bets_csv': True,    # Export all bets to CSV
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def odds_to_implied_prob(american_odds):
    if american_odds < 0:
        return abs(american_odds) / (abs(american_odds) + 100)
    return 100 / (american_odds + 100)

def odds_to_decimal(american_odds):
    if american_odds < 0:
        return 1 + (100 / abs(american_odds))
    return 1 + (american_odds / 100)

def kelly_fraction(our_prob, decimal_odds, max_kelly=0.25):
    b = decimal_odds - 1.0
    p = float(our_prob)
    q = 1.0 - p
    if b <= 0:
        return 0.0
    k = (b * p - q) / b
    if k <= 0:
        return 0.0
    return min(k, max_kelly)

def get_edge_bucket(edge, bucket_size):
    bucket_num = int(edge / bucket_size)
    bucket_start = bucket_num * bucket_size
    bucket_end = bucket_start + bucket_size
    return (bucket_start, bucket_end)

def get_odds_bucket(odds, buckets):
    for name, min_odds, max_odds in buckets:
        if min_odds <= odds < max_odds:
            return name
    return 'Other'

def get_zone(odds, enabled_zones):
    """LEGACY function - use odds bucket filtering instead"""
    if odds < -300 and enabled_zones.get('heavy_favorite'):
        return 'heavy_favorite'
    elif 100 <= odds <= 110 and enabled_zones.get('pickem_underdog'):
        return 'pickem_underdog'
    elif 110 < odds <= 150 and enabled_zones.get('slight_underdog'):
        return 'slight_underdog'
    return None

def is_odds_bucket_enabled(odds, odds_buckets, odds_buckets_enabled):
    """Check if a bet with given odds should be placed based on enabled buckets"""
    bucket_name = get_odds_bucket(odds, odds_buckets)
    return odds_buckets_enabled.get(bucket_name, False)

# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def simulate_betting(df, config):
    """Run comprehensive betting simulation with all tracking"""
    
    all_bets = []
    edge_buckets = {}
    odds_buckets = {}
    zone_stats = {}  # Dynamic - will add zones as encountered
    calibration_bins = {}  # {prob_bin: {'count': 0, 'wins': 0}}
    
    # Flat betting stats
    flat_total_bets = 0
    flat_won_bets = 0
    flat_total_profit = 0
    flat_total_staked = 0
    
    # Kelly betting stats
    kelly_bankroll = float(config['kelly_starting_bankroll'])
    kelly_total_bets = 0
    kelly_won_bets = 0
    kelly_total_profit = 0
    kelly_total_staked = 0
    
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
        
        # Choose higher edge side
        if edge_a >= edge_b:
            chosen_side, chosen_prob, chosen_odds, chosen_edge = 'A', p_win_a, ml_a, edge_a
        else:
            chosen_side, chosen_prob, chosen_odds, chosen_edge = 'B', p_win_b, ml_b, edge_b
        
        # Apply filters
        if chosen_edge < config['min_edge'] or chosen_edge > config['max_edge']:
            continue
        if config['min_odds'] is not None and chosen_odds < config['min_odds']:
            continue
        if config['max_odds'] is not None and chosen_odds > config['max_odds']:
            continue
        if chosen_odds <= -1000:
            continue
        
        # Check if this odds bucket is enabled
        if not is_odds_bucket_enabled(chosen_odds, config['odds_buckets'], config['odds_buckets_enabled']):
            continue
            
        # Get zone (for legacy tracking)
        zone = get_zone(chosen_odds, config['enabled_zones'])
        if zone is None:
            zone = 'other'  # Fallback for odds outside legacy zones
        
        # Place bet
        decimal_odds = odds_to_decimal(chosen_odds)
        actual_winner = game['true_winner']
        bet_won = (chosen_side == 'A' and actual_winner == 1) or \
                  (chosen_side == 'B' and actual_winner == 0)
        
        # Flat betting
        flat_bet_amount = config['flat_bet_size']
        flat_profit = flat_bet_amount * (decimal_odds - 1) if bet_won else -flat_bet_amount
        flat_total_bets += 1
        flat_won_bets += (1 if bet_won else 0)
        flat_total_profit += flat_profit
        flat_total_staked += flat_bet_amount
        
        # Kelly betting
        kelly_frac = kelly_fraction(chosen_prob, decimal_odds, config['kelly_fraction'])
        if kelly_frac > 0 and kelly_bankroll > 0:
            kelly_bet_amount = kelly_bankroll * kelly_frac
            kelly_profit = kelly_bet_amount * (decimal_odds - 1) if bet_won else -kelly_bet_amount
            kelly_bankroll += kelly_profit
            kelly_total_bets += 1
            kelly_won_bets += (1 if bet_won else 0)
            kelly_total_profit += kelly_profit
            kelly_total_staked += kelly_bet_amount
        else:
            kelly_bet_amount = 0
            kelly_profit = 0
        
        # Track by edge bucket
        edge_bucket = get_edge_bucket(chosen_edge, config['edge_bucket_size'])
        if edge_bucket not in edge_buckets:
            edge_buckets[edge_bucket] = {'count': 0, 'wins': 0, 'profit': 0}
        edge_buckets[edge_bucket]['count'] += 1
        edge_buckets[edge_bucket]['wins'] += (1 if bet_won else 0)
        edge_buckets[edge_bucket]['profit'] += flat_profit
        
        # Track by odds bucket
        odds_bucket = get_odds_bucket(chosen_odds, config['odds_buckets'])
        if odds_bucket not in odds_buckets:
            odds_buckets[odds_bucket] = {'count': 0, 'wins': 0, 'profit': 0}
        odds_buckets[odds_bucket]['count'] += 1
        odds_buckets[odds_bucket]['wins'] += (1 if bet_won else 0)
        odds_buckets[odds_bucket]['profit'] += flat_profit
        
        # Track by zone
        if zone not in zone_stats:
            zone_stats[zone] = {'count': 0, 'wins': 0, 'profit': 0}
        zone_stats[zone]['count'] += 1
        zone_stats[zone]['wins'] += (1 if bet_won else 0)
        zone_stats[zone]['profit'] += flat_profit
        
        # Track calibration
        prob_bin = round(chosen_prob, 1)  # Round to nearest 10%
        if prob_bin not in calibration_bins:
            calibration_bins[prob_bin] = {'count': 0, 'wins': 0}
        calibration_bins[prob_bin]['count'] += 1
        calibration_bins[prob_bin]['wins'] += (1 if bet_won else 0)
        
        # Record bet
        bet_record = {
            'date': game.get('date', ''),
            'game_id': game.get('game_id', idx),
            'team_a': game.get('team_a', 'Team A'),
            'team_b': game.get('team_b', 'Team B'),
            'chosen_side': chosen_side,
            'chosen_team': game.get('team_a') if chosen_side == 'A' else game.get('team_b'),
            'chosen_odds': chosen_odds,
            'our_prob': chosen_prob,
            'implied_prob': odds_to_implied_prob(chosen_odds),
            'edge': chosen_edge,
            'edge_bucket': f"{edge_bucket[0]:.3f}-{edge_bucket[1]:.3f}",
            'odds_bucket': odds_bucket,
            'zone': zone,
            'flat_bet_amount': flat_bet_amount,
            'flat_profit': flat_profit,
            'kelly_bet_amount': kelly_bet_amount,
            'kelly_profit': kelly_profit,
            'bet_won': bet_won,
            'actual_winner': 'A' if actual_winner == 1 else 'B'
        }
        all_bets.append(bet_record)
    
    # Calculate metrics
    flat_roi = (flat_total_profit / flat_total_staked * 100) if flat_total_staked > 0 else 0
    flat_win_rate = (flat_won_bets / flat_total_bets * 100) if flat_total_bets > 0 else 0
    
    kelly_roi = (kelly_total_profit / kelly_total_staked * 100) if kelly_total_staked > 0 else 0
    kelly_win_rate = (kelly_won_bets / kelly_total_bets * 100) if kelly_total_bets > 0 else 0
    kelly_return = ((kelly_bankroll - config['kelly_starting_bankroll']) / config['kelly_starting_bankroll'] * 100)
    
    return {
        'flat': {
            'total_bets': flat_total_bets,
            'won_bets': flat_won_bets,
            'win_rate': flat_win_rate,
            'total_staked': flat_total_staked,
            'total_profit': flat_total_profit,
            'roi': flat_roi,
        },
        'kelly': {
            'total_bets': kelly_total_bets,
            'won_bets': kelly_won_bets,
            'win_rate': kelly_win_rate,
            'total_staked': kelly_total_staked,
            'total_profit': kelly_total_profit,
            'roi': kelly_roi,
            'starting_bankroll': config['kelly_starting_bankroll'],
            'final_bankroll': kelly_bankroll,
            'total_return': kelly_return,
        },
        'edge_buckets': edge_buckets,
        'odds_buckets': odds_buckets,
        'zone_stats': zone_stats,
        'calibration_bins': calibration_bins,
        'all_bets': all_bets,
    }

def run_baseline_comparison(df, config):
    """Compare to random betting and always-favorite strategies"""
    
    # Random betting on same games
    random_profit = 0
    random_bets = 0
    
    # Always bet favorite
    favorite_profit = 0
    favorite_bets = 0
    
    # Always bet underdog
    underdog_profit = 0
    underdog_bets = 0
    
    np.random.seed(42)
    
    for _, game in df.iterrows():
        if pd.isna(game.get('moneyline_a')) or pd.isna(game.get('moneyline_b')):
            continue
            
        ml_a = game['moneyline_a']
        ml_b = game['moneyline_b']
        actual_winner = game['true_winner']
        
        # Random betting (50/50 choice)
        random_side = np.random.choice(['A', 'B'])
        random_odds = ml_a if random_side == 'A' else ml_b
        random_won = (random_side == 'A' and actual_winner == 1) or \
                     (random_side == 'B' and actual_winner == 0)
        random_decimal = odds_to_decimal(random_odds)
        random_profit += config['flat_bet_size'] * (random_decimal - 1) if random_won else -config['flat_bet_size']
        random_bets += 1
        
        # Always favorite
        if ml_a < ml_b:
            fav_odds, fav_side = ml_a, 'A'
        else:
            fav_odds, fav_side = ml_b, 'B'
        fav_won = (fav_side == 'A' and actual_winner == 1) or \
                  (fav_side == 'B' and actual_winner == 0)
        fav_decimal = odds_to_decimal(fav_odds)
        favorite_profit += config['flat_bet_size'] * (fav_decimal - 1) if fav_won else -config['flat_bet_size']
        favorite_bets += 1
        
        # Always underdog
        if ml_a > ml_b:
            dog_odds, dog_side = ml_a, 'A'
        else:
            dog_odds, dog_side = ml_b, 'B'
        dog_won = (dog_side == 'A' and actual_winner == 1) or \
                  (dog_side == 'B' and actual_winner == 0)
        dog_decimal = odds_to_decimal(dog_odds)
        underdog_profit += config['flat_bet_size'] * (dog_decimal - 1) if dog_won else -config['flat_bet_size']
        underdog_bets += 1
    
    return {
        'random': {
            'total_bets': random_bets,
            'profit': random_profit,
            'roi': (random_profit / (random_bets * config['flat_bet_size']) * 100) if random_bets > 0 else 0
        },
        'always_favorite': {
            'total_bets': favorite_bets,
            'profit': favorite_profit,
            'roi': (favorite_profit / (favorite_bets * config['flat_bet_size']) * 100) if favorite_bets > 0 else 0
        },
        'always_underdog': {
            'total_bets': underdog_bets,
            'profit': underdog_profit,
            'roi': (underdog_profit / (underdog_bets * config['flat_bet_size']) * 100) if underdog_bets > 0 else 0
        }
    }

# ============================================================================
# OUTPUT FUNCTIONS
# ============================================================================

def print_section(title, width=80):
    print(f"\n{'='*width}")
    print(title)
    print(f"{'='*width}")

def save_results(config, all_results, output_dir):
    """Save all results to organized directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_dir = Path(output_dir) / f"{timestamp}_{config['experiment_name']}"
    exp_dir.mkdir(parents=True, exist_ok=True)
    
    # Save config
    with open(exp_dir / 'config.json', 'w') as f:
        json.dump(config, f, indent=2, default=str)
    
    # Save summary
    with open(exp_dir / 'summary.txt', 'w') as f:
        f.write(f"Experiment: {config['experiment_name']}\n")
        f.write(f"Timestamp: {timestamp}\n\n")
        f.write(f"Overall Results:\n")
        f.write(f"  Flat Betting ROI: {all_results['combined']['flat']['roi']:.2f}%\n")
        f.write(f"  Kelly Betting Return: {all_results['combined']['kelly']['total_return']:.2f}%\n")
    
    # Save all bets CSV
    if config['save_all_bets_csv']:
        all_bets_combined = []
        for year, results in all_results['by_year'].items():
            for bet in results['all_bets']:
                bet['year'] = year
                all_bets_combined.append(bet)
        
        if all_bets_combined:
            bets_df = pd.DataFrame(all_bets_combined)
            bets_df.to_csv(exp_dir / 'all_bets.csv', index=False)
            print(f"\n💾 Saved {len(all_bets_combined)} bets to: {exp_dir / 'all_bets.csv'}")
    
    print(f"\n✅ All results saved to: {exp_dir}")
    return exp_dir

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print_section("UNIFIED BETTING ANALYSIS FRAMEWORK")
    print(f"Experiment: {CONFIG['experiment_name']}")
    print(f"Edge Range: {CONFIG['min_edge']*100:.2f}% - {CONFIG['max_edge']*100:.2f}%")
    print(f"Flat Bet Size: ${CONFIG['flat_bet_size']}")
    print(f"Kelly Bankroll: ${CONFIG['kelly_starting_bankroll']}")
    
    print(f"\nEnabled Odds Buckets:")
    for bucket_name, enabled in CONFIG['odds_buckets_enabled'].items():
        status = "✅" if enabled else "❌"
        print(f"  {status} {bucket_name}")
    
    # Load and combine all data
    all_results = {'by_year': {}, 'combined': None}
    combined_bets = []
    
    for year, filepath in CONFIG['data_files'].items():
        print_section(f"YEAR {year}", width=80)
        try:
            df = pd.read_csv(filepath)
            df = df.dropna(subset=['moneyline_a', 'moneyline_b'])
            print(f"Loaded {len(df)} games")
            
            results = simulate_betting(df, CONFIG)
            all_results['by_year'][year] = results
            
            print(f"\nFlat: {results['flat']['total_bets']} bets | "
                  f"${results['flat']['total_profit']:,.2f} profit | "
                  f"{results['flat']['roi']:.2f}% ROI")
            print(f"Kelly: {results['kelly']['total_bets']} bets | "
                  f"${results['kelly']['total_profit']:,.2f} profit | "
                  f"{results['kelly']['total_return']:.2f}% return")
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    # Combine all years
    print_section("COMBINED RESULTS (ALL YEARS)", width=80)
    
    combined_flat = {
        'total_bets': sum(r['flat']['total_bets'] for r in all_results['by_year'].values()),
        'won_bets': sum(r['flat']['won_bets'] for r in all_results['by_year'].values()),
        'total_staked': sum(r['flat']['total_staked'] for r in all_results['by_year'].values()),
        'total_profit': sum(r['flat']['total_profit'] for r in all_results['by_year'].values()),
    }
    combined_flat['roi'] = (combined_flat['total_profit'] / combined_flat['total_staked'] * 100) if combined_flat['total_staked'] > 0 else 0
    combined_flat['win_rate'] = (combined_flat['won_bets'] / combined_flat['total_bets'] * 100) if combined_flat['total_bets'] > 0 else 0
    
    print(f"\nFlat Betting Summary:")
    print(f"  Total Bets: {combined_flat['total_bets']}")
    print(f"  Win Rate: {combined_flat['win_rate']:.2f}%")
    print(f"  Total Profit: ${combined_flat['total_profit']:,.2f}")
    print(f"  ROI: {combined_flat['roi']:.2f}%")
    
    # Edge bucket analysis
    if CONFIG['run_edge_buckets']:
        print_section("EDGE BUCKET ANALYSIS", width=80)
        combined_edge_buckets = {}
        for results in all_results['by_year'].values():
            for bucket, data in results['edge_buckets'].items():
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
            bet_pct = (data['count'] / combined_flat['total_bets'] * 100) if combined_flat['total_bets'] > 0 else 0
            roi = (data['profit'] / (data['count'] * CONFIG['flat_bet_size']) * 100) if data['count'] > 0 else 0
            print(f"{bucket[0]:.3f}-{bucket[1]:.3f}   {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  {bet_pct:>8.2f}%  "
                  f"${data['profit']:>9,.2f}  {roi:>6.2f}%")
    
    # Odds bucket analysis
    if CONFIG['run_odds_buckets']:
        print_section("ODDS BUCKET ANALYSIS", width=80)
        combined_odds_buckets = {}
        for results in all_results['by_year'].values():
            for bucket, data in results['odds_buckets'].items():
                if bucket not in combined_odds_buckets:
                    combined_odds_buckets[bucket] = {'count': 0, 'wins': 0, 'profit': 0}
                combined_odds_buckets[bucket]['count'] += data['count']
                combined_odds_buckets[bucket]['wins'] += data['wins']
                combined_odds_buckets[bucket]['profit'] += data['profit']
        
        print(f"\n{'Odds Bucket':<25} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Bet%':<10} {'Profit':<12} {'ROI':<8}")
        print("-" * 95)
        
        # Print in order defined in config
        for bucket_name, _, _ in CONFIG['odds_buckets']:
            if bucket_name in combined_odds_buckets:
                data = combined_odds_buckets[bucket_name]
                win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
                bet_pct = (data['count'] / combined_flat['total_bets'] * 100) if combined_flat['total_bets'] > 0 else 0
                roi = (data['profit'] / (data['count'] * CONFIG['flat_bet_size']) * 100) if data['count'] > 0 else 0
                print(f"{bucket_name:<25} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  {bet_pct:>8.2f}%  "
                      f"${data['profit']:>9,.2f}  {roi:>6.2f}%")
    
    # Zone analysis
    if CONFIG['run_zone_analysis']:
        print_section("ZONE ANALYSIS", width=80)
        combined_zones = {}
        for results in all_results['by_year'].values():
            for zone, data in results['zone_stats'].items():
                if data['count'] > 0:  # Only include zones with bets
                    if zone not in combined_zones:
                        combined_zones[zone] = {'count': 0, 'wins': 0, 'profit': 0}
                    combined_zones[zone]['count'] += data['count']
                    combined_zones[zone]['wins'] += data['wins']
                    combined_zones[zone]['profit'] += data['profit']
        
        zone_names = {
            'heavy_favorite': 'Heavy Favorite (< -300)',
            'pickem_underdog': "Pick'em Underdog (+100 to +110)",
            'slight_underdog': 'Slight Underdog (+110 to +150)'
        }
        
        print(f"\n{'Zone':<35} {'Bets':<8} {'Wins':<8} {'Win%':<10} {'Profit':<12} {'ROI':<8}")
        print("-" * 90)
        for zone_key, zone_name in zone_names.items():
            if zone_key in combined_zones:
                data = combined_zones[zone_key]
                win_pct = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
                roi = (data['profit'] / (data['count'] * CONFIG['flat_bet_size']) * 100) if data['count'] > 0 else 0
                print(f"{zone_name:<35} {data['count']:<8} {data['wins']:<8} {win_pct:>8.2f}%  "
                      f"${data['profit']:>9,.2f}  {roi:>6.2f}%")
    
    # Calibration analysis
    if CONFIG['run_calibration']:
        print_section("MODEL CALIBRATION", width=80)
        combined_calibration = {}
        for results in all_results['by_year'].values():
            for prob_bin, data in results['calibration_bins'].items():
                if prob_bin not in combined_calibration:
                    combined_calibration[prob_bin] = {'count': 0, 'wins': 0}
                combined_calibration[prob_bin]['count'] += data['count']
                combined_calibration[prob_bin]['wins'] += data['wins']
        
        print(f"\n{'Predicted':<12} {'Actual':<12} {'Bets':<8} {'Difference':<12}")
        print("-" * 50)
        for prob_bin in sorted(combined_calibration.keys()):
            data = combined_calibration[prob_bin]
            actual_rate = (data['wins'] / data['count']) if data['count'] > 0 else 0
            diff = actual_rate - prob_bin
            print(f"{prob_bin*100:>6.1f}%      {actual_rate*100:>6.1f}%      {data['count']:<8} {diff*100:>+7.2f}%")
    
    # Combine Kelly results
    combined_kelly = {
        'total_bets': sum(r['kelly']['total_bets'] for r in all_results['by_year'].values()),
        'won_bets': sum(r['kelly']['won_bets'] for r in all_results['by_year'].values()),
        'total_staked': sum(r['kelly']['total_staked'] for r in all_results['by_year'].values()),
        'total_profit': sum(r['kelly']['total_profit'] for r in all_results['by_year'].values()),
    }
    combined_kelly['roi'] = (combined_kelly['total_profit'] / combined_kelly['total_staked'] * 100) if combined_kelly['total_staked'] > 0 else 0
    combined_kelly['win_rate'] = (combined_kelly['won_bets'] / combined_kelly['total_bets'] * 100) if combined_kelly['total_bets'] > 0 else 0
    combined_kelly['total_return'] = (combined_kelly['total_profit'] / (CONFIG['kelly_starting_bankroll'] * len(all_results['by_year'])) * 100) if len(all_results['by_year']) > 0 else 0
    
    print(f"\nKelly Betting Summary:")
    print(f"  Total Bets: {combined_kelly['total_bets']}")
    print(f"  Total Profit: ${combined_kelly['total_profit']:,.2f}")
    print(f"  Avg Return per Year: {combined_kelly['total_return']:.2f}%")
    
    all_results['combined'] = {'flat': combined_flat, 'kelly': combined_kelly}
    
    # Save everything
    save_results(CONFIG, all_results, CONFIG['output_dir'])

if __name__ == "__main__":
    main()