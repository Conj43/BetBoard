import pandas as pd
import numpy as np
from datetime import datetime

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
    """Quarter Kelly by default. Returns fraction of bankroll to stake."""
    b = decimal_odds - 1.0  # net odds
    p = float(our_prob)
    q = 1.0 - p
    if b <= 0:
        return 0.0
    k = (b * p - q) / b
    if k <= 0:
        return 0.0
    return min(k, max_kelly)

def simulate_zones_flat(df, flat_bet_size=100, min_edge=0.0, max_edge=0.0471, enabled_zones=None):
    """
    Simulate betting on configurable zones.
    
    enabled_zones: dict like {'heavy_favorite': True, 'pickem_underdog': False, 'slight_underdog': True}
    """
    
    if enabled_zones is None:
        enabled_zones = {
            'heavy_favorite': True,
            'pickem_underdog': True,
            'slight_underdog': True
        }
    
    zones = {
        'heavy_favorite': {'name': 'Heavy Favorite (<-300)', 'bets': [], 'profit': 0, 'count': 0, 'wins': 0, 'enabled': enabled_zones.get('heavy_favorite', False)},
        'pickem_underdog': {'name': "Pick'em Underdog (+100 to +110)", 'bets': [], 'profit': 0, 'count': 0, 'wins': 0, 'enabled': enabled_zones.get('pickem_underdog', False)},
        'slight_underdog': {'name': 'Slight Underdog (+110 to +150)', 'bets': [], 'profit': 0, 'count': 0, 'wins': 0, 'enabled': enabled_zones.get('slight_underdog', False)},
    }
    
    total_bets = 0
    won_bets = 0
    total_staked = 0
    total_profit = 0
    
    for _, game in df.iterrows():
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

        # Pick the higher edge side
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

        # Determine zone
        zone = None
        if chosen_odds < -300:
            zone = 'heavy_favorite'
        elif 100 <= chosen_odds <= 110:
            zone = 'pickem_underdog'
        elif 110 < chosen_odds <= 150:
            zone = 'slight_underdog'
        else:
            continue  # Skip everything else

        # Check if this zone is enabled
        if not zones[zone]['enabled']:
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
        
        # Track by zone
        zones[zone]['count'] += 1
        zones[zone]['wins'] += (1 if bet_won else 0)
        zones[zone]['profit'] += profit

    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
    win_rate = (won_bets / total_bets * 100) if total_bets > 0 else 0

    return {
        'total_profit': total_profit,
        'total_bets': total_bets,
        'won_bets': won_bets,
        'win_rate': win_rate,
        'total_staked': total_staked,
        'roi': roi,
        'zones': zones
    }

def simulate_zones_kelly(df, starting_bankroll=10000.0, min_edge=0.0, max_edge=0.0471, kelly_cap=0.25, enabled_zones=None):
    """
    Quarter-Kelly staking in configurable zones.
    """
    
    if enabled_zones is None:
        enabled_zones = {
            'heavy_favorite': True,
            'pickem_underdog': True,
            'slight_underdog': True
        }
    
    work = df.copy()
    if "date" in work.columns:
        try:
            work["__date__"] = pd.to_datetime(work["date"])
            work = work.sort_values("__date__")
        except Exception:
            pass

    zones = {
        'heavy_favorite': {'name': 'Heavy Favorite (<-300)', 'profit': 0, 'count': 0, 'wins': 0, 'enabled': enabled_zones.get('heavy_favorite', False)},
        'pickem_underdog': {'name': "Pick'em Underdog (+100 to +110)", 'profit': 0, 'count': 0, 'wins': 0, 'enabled': enabled_zones.get('pickem_underdog', False)},
        'slight_underdog': {'name': 'Slight Underdog (+110 to +150)', 'profit': 0, 'count': 0, 'wins': 0, 'enabled': enabled_zones.get('slight_underdog', False)},
    }

    current_bankroll = float(starting_bankroll)
    total_bets = 0
    won_bets = 0
    total_staked = 0.0
    total_profit = 0.0

    for _, game in work.iterrows():
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

        # Zone filter
        zone_key = None
        if chosen_odds < -300:
            zone_key = 'heavy_favorite'
        elif 100 <= chosen_odds <= 110:
            zone_key = 'pickem_underdog'
        elif 110 < chosen_odds <= 150:
            zone_key = 'slight_underdog'
        else:
            continue

        # Check if this zone is enabled
        if not zones[zone_key]['enabled']:
            continue

        # Kelly stake
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
        
        zones[zone_key]['count'] += 1
        zones[zone_key]['wins'] += (1 if bet_won else 0)
        zones[zone_key]['profit'] += profit

        if current_bankroll <= 0:
            break

    roi = (total_profit / total_staked * 100.0) if total_staked > 0 else 0.0
    win_rate = (won_bets / total_bets * 100.0) if total_bets > 0 else 0.0
    total_return = ((current_bankroll - starting_bankroll) / starting_bankroll * 100.0)

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
        'zones': zones
    }

def main():
    # ===== CONFIGURE YOUR FILE PATHS HERE =====
    year_files = {
        # 2021: 'data/xgb_model/2021_xgb_all_models_20251009_202637/moneyline_predictions_2021.csv',
        # 2022: 'data/xgb_model/2022_xgb_all_models_20251009_202214/moneyline_predictions_2022.csv',
        # 2023: 'data/xgb_model/2023_xgb_all_models_20251009_200335/moneyline_predictions_2023.csv',
        # 2024: 'data/xgb_model/2024_xgb_all_models_20251009_200100/moneyline_predictions_2024.csv',
        2025: 'data/xgb_model/xgb_all_models_20251010_132522/moneyline_predictions_2025.csv',
    }
    
    # ===== ZONE CONFIGURATION =====
    # Set to True to bet on that zone, False to skip it
    ENABLED_ZONES = {
        'heavy_favorite': True,      # Heavy Favorites (odds < -300)
        'pickem_underdog': True,     # Pick'em Underdogs (+100 to +110)
        'slight_underdog': True,      # Slight Underdogs (+110 to +150)
    }
    
    # Betting parameters
    FLAT_BET_SIZE = 100  # $100 per bet = 1 unit
    KELLY_STARTING_BANKROLL = 10000  # $10,000 starting bankroll
    KELLY_CAP = 0.25  # Quarter Kelly
    
    # Set up output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    enabled_zone_names = [k.replace('_', '') for k, v in ENABLED_ZONES.items() if v]
    zones_suffix = "_".join(enabled_zone_names) if enabled_zone_names else "NO_ZONES"
    output_file = f"data/predictions/MONEYLINE_{zones_suffix}_{timestamp}.txt"
    
    import sys
    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj)
        def flush(self):
            for f in self.files:
                f.flush()
    
    f = open(output_file, 'w')
    original = sys.stdout
    sys.stdout = Tee(sys.stdout, f)
    
    try:
        print("=" * 80)
        print("CONFIGURABLE ZONES ANALYSIS (2021-2025)")
        print("=" * 80)
        print("\nBetting on SELECTED zones only:")
        
        zone_display_names = {
            'heavy_favorite': 'Heavy Favorites (odds < -300)',
            'pickem_underdog': "Pick'em Underdogs (odds +100 to +110)",
            'slight_underdog': 'Slight Underdogs (odds +110 to +150)'
        }
        
        for zone_key, enabled in ENABLED_ZONES.items():
            status = "✅ ENABLED" if enabled else "❌ SKIPPED"
            print(f"  {status}: {zone_display_names[zone_key]}")
        
        print("=" * 80)
        
        # Store results
        flat_results_by_year = {}
        kelly_results_by_year = {}
        
        # Run simulations for each year
        for year in sorted(year_files.keys()):
            print(f"\n{'='*80}")
            print(f"YEAR {year}")
            print(f"{'='*80}")
            
            try:
                df = pd.read_csv(year_files[year])
                original_len = len(df)
                df = df.dropna(subset=['moneyline_a', 'moneyline_b'])
                
                print(f"Loaded {len(df)} games (dropped {original_len - len(df)} with missing odds)")
                
                # Flat betting
                flat_result = simulate_zones_flat(df, flat_bet_size=FLAT_BET_SIZE, enabled_zones=ENABLED_ZONES)
                flat_results_by_year[year] = flat_result
                
                # Kelly betting
                kelly_result = simulate_zones_kelly(
                    df, 
                    starting_bankroll=KELLY_STARTING_BANKROLL,
                    kelly_cap=KELLY_CAP,
                    enabled_zones=ENABLED_ZONES
                )
                kelly_results_by_year[year] = kelly_result
                
                print(f"\n--- FLAT BETTING (${FLAT_BET_SIZE} per game) ---")
                print(f"Total Bets: {flat_result['total_bets']}")
                print(f"Wins: {flat_result['won_bets']} ({flat_result['win_rate']:.2f}%)")
                print(f"Total Profit: ${flat_result['total_profit']:,.2f}")
                print(f"ROI: {flat_result['roi']:.2f}%")
                
                print(f"\n  Zone Breakdown:")
                for zone_key, zone_data in flat_result['zones'].items():
                    if zone_data['enabled'] and zone_data['count'] > 0:
                        zone_roi = (zone_data['profit'] / (zone_data['count'] * FLAT_BET_SIZE) * 100)
                        zone_wr = (zone_data['wins'] / zone_data['count'] * 100)
                        print(f"    {zone_data['name']}: {zone_data['count']} bets, "
                              f"{zone_data['wins']} wins ({zone_wr:.1f}%), "
                              f"${zone_data['profit']:,.2f} profit ({zone_roi:+.2f}% ROI)")
                
                print(f"\n--- QUARTER KELLY (${KELLY_STARTING_BANKROLL:,.0f} starting bankroll) ---")
                print(f"Total Bets: {kelly_result['total_bets']}")
                print(f"Wins: {kelly_result['won_bets']} ({kelly_result['win_rate']:.2f}%)")
                print(f"Starting Bankroll: ${kelly_result['starting_bankroll']:,.2f}")
                print(f"Ending Bankroll: ${kelly_result['final_bankroll']:,.2f}")
                print(f"Total Profit: ${kelly_result['total_profit']:,.2f}")
                print(f"Return: {kelly_result['total_return']:+.2f}%")
                
                print(f"\n  Zone Breakdown:")
                for zone_key, zone_data in kelly_result['zones'].items():
                    if zone_data['enabled'] and zone_data['count'] > 0:
                        zone_wr = (zone_data['wins'] / zone_data['count'] * 100)
                        print(f"    {zone_data['name']}: {zone_data['count']} bets, "
                              f"{zone_data['wins']} wins ({zone_wr:.1f}%), "
                              f"${zone_data['profit']:,.2f} profit")
                
            except Exception as e:
                print(f"ERROR loading {year}: {e}")
                continue
        
        # ===== COMBINED SUMMARY =====
        print(f"\n\n{'='*80}")
        print("COMBINED RESULTS (2021-2025)")
        print(f"{'='*80}")
        
        # Flat betting totals
        print(f"\n{'='*80}")
        print(f"FLAT BETTING SUMMARY (${FLAT_BET_SIZE} per bet = 1 unit)")
        print(f"{'='*80}")
        
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
        
        # Zone breakdown across all years (only enabled zones)
        print(f"\n\nCombined Zone Performance (Flat Betting):")
        print("-" * 80)
        
        combined_zones = {}
        for year_result in flat_results_by_year.values():
            for zone_key, zone_data in year_result['zones'].items():
                if not zone_data['enabled']:
                    continue
                if zone_key not in combined_zones:
                    combined_zones[zone_key] = {'name': zone_data['name'], 'profit': 0, 'count': 0, 'wins': 0}
                combined_zones[zone_key]['profit'] += zone_data['profit']
                combined_zones[zone_key]['count'] += zone_data['count']
                combined_zones[zone_key]['wins'] += zone_data['wins']
        
        for zone_key, zone_data in combined_zones.items():
            if zone_data['count'] > 0:
                zone_roi = (zone_data['profit'] / (zone_data['count'] * FLAT_BET_SIZE) * 100)
                zone_wr = (zone_data['wins'] / zone_data['count'] * 100)
                print(f"{zone_data['name']}")
                print(f"  Bets: {zone_data['count']} | Wins: {zone_data['wins']} ({zone_wr:.2f}%)")
                print(f"  Profit: ${zone_data['profit']:,.2f} | ROI: {zone_roi:+.2f}%")
                print()
        
        # Kelly betting totals
        print(f"\n{'='*80}")
        print(f"KELLY BETTING SUMMARY (${KELLY_STARTING_BANKROLL:,.0f} starting bankroll each year)")
        print(f"{'='*80}")
        
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
        
        # Zone breakdown for Kelly (only enabled zones)
        print(f"\n\nCombined Zone Performance (Kelly Betting):")
        print("-" * 80)
        
        combined_kelly_zones = {}
        for year_result in kelly_results_by_year.values():
            for zone_key, zone_data in year_result['zones'].items():
                if not zone_data['enabled']:
                    continue
                if zone_key not in combined_kelly_zones:
                    combined_kelly_zones[zone_key] = {'name': zone_data['name'], 'profit': 0, 'count': 0, 'wins': 0}
                combined_kelly_zones[zone_key]['profit'] += zone_data['profit']
                combined_kelly_zones[zone_key]['count'] += zone_data['count']
                combined_kelly_zones[zone_key]['wins'] += zone_data['wins']
        
        for zone_key, zone_data in combined_kelly_zones.items():
            if zone_data['count'] > 0:
                zone_wr = (zone_data['wins'] / zone_data['count'] * 100)
                print(f"{zone_data['name']}")
                print(f"  Bets: {zone_data['count']} | Wins: {zone_data['wins']} ({zone_wr:.2f}%)")
                print(f"  Profit: ${zone_data['profit']:,.2f}")
                print()
        
        # Final summary
        print(f"\n{'='*80}")
        print("FINAL VERDICT")
        print(f"{'='*80}")
        
        print(f"\nFlat Betting ({FLAT_BET_SIZE} units):")
        print(f"  Total Profit: ${total_flat_profit:,.2f} ({total_flat_profit/FLAT_BET_SIZE:+.2f} units)")
        print(f"  ROI: {total_flat_roi:.2f}%")
        print(f"  Win Rate: {total_flat_wr:.2f}%")
        print(f"  Winning Years: {sum(1 for r in flat_results_by_year.values() if r['total_profit'] > 0)}/5")
        
        print(f"\nQuarter Kelly Betting:")
        print(f"  Total Profit: ${total_kelly_profit:,.2f}")
        print(f"  Avg Return: {avg_kelly_return:+.2f}% per year")
        print(f"  Winning Years: {sum(1 for r in kelly_results_by_year.values() if r['total_profit'] > 0)}/5")
        
        if total_flat_roi > 0:
            print(f"\n✅ Strategy is PROFITABLE with {total_flat_roi:.2f}% ROI")
        else:
            print(f"\n❌ Strategy is UNPROFITABLE with {total_flat_roi:.2f}% ROI")
            
    finally:
        sys.stdout = original
        f.close()
        print(f"\n✅ Analysis saved to: {output_file}")

if __name__ == "__main__":
    main()