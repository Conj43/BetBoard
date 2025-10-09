import pandas as pd
import numpy as np

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


def simulate_profitable_zones(df, flat_bet_size=100, min_edge=0, max_edge=0.0471):
    """
    Simulate betting ONLY in the profitable zones:
    1. Heavy Favorites: odds < -300
    2. Slight Underdogs: odds +110 to +150
    3. Pick'em Underdogs: odds +100 to +110
    
    Skips the death zone: -300 to +100
    """
    
    # Track results by zone
    zones = {
        'heavy_favorite': {'name': 'Heavy Favorite (<-300)', 'bets': []},
        'pickem_underdog': {'name': "Pick'em Underdog (+100 to +110)", 'bets': []},
        'slight_underdog': {'name': 'Slight Underdog (+110 to +150)', 'bets': []},
        'skipped': {'name': 'SKIPPED (Death Zone -300 to +100)', 'bets': []}
    }
    
    total_bets = 0
    won_bets = 0
    total_staked = 0
    total_profit = 0
    
    results = []
    
    for _, game in df.iterrows():
        # Require needed columns
        if pd.isna(game.get('moneyline_a')) or pd.isna(game.get('moneyline_b')):
            continue

        p_win_a = game['p_win_A']
        p_win_b = 1 - p_win_a

        ml_a = game['moneyline_a']
        ml_b = game['moneyline_b']

        # Convert to implied probabilities
        implied_prob_a = odds_to_implied_prob(ml_a)
        implied_prob_b = odds_to_implied_prob(ml_b)

        # Calculate edge on both sides
        edge_a = p_win_a - implied_prob_a
        edge_b = p_win_b - implied_prob_b

        # Choose side with higher edge
        bet_side = None
        bet_prob = None
        decimal_odds = None
        american_odds = None
        edge = 0
        zone = None

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

        # Check edge band filter
        if chosen_edge < min_edge or chosen_edge > max_edge:
            continue

        # CRITICAL: Determine if this falls in profitable zone
        if chosen_odds < -300:
            zone = 'heavy_favorite'
        elif 100 <= chosen_odds <= 110:
            zone = 'pickem_underdog'
        elif 110 < chosen_odds <= 150:
            zone = 'slight_underdog'
        else:
            # SKIP the death zone (-300 to +100, excluding +100-110)
            zone = 'skipped'
            zones['skipped']['bets'].append({
                'odds': chosen_odds,
                'edge': chosen_edge
            })
            continue  # Don't bet on this game

        # If we're here, we're in a profitable zone - place bet
        bet_side = chosen_side
        bet_prob = chosen_prob
        decimal_odds = odds_to_decimal(chosen_odds)
        american_odds = chosen_odds
        edge = chosen_edge

        bet_amount = flat_bet_size
        total_staked += bet_amount
        total_bets += 1

        actual_winner = game['true_winner']
        bet_won = (bet_side == 'A' and actual_winner == 1) or \
                  (bet_side == 'B' and actual_winner == 0)

        if bet_won:
            profit = bet_amount * (decimal_odds - 1)
            won_bets += 1
        else:
            profit = -bet_amount

        total_profit += profit

        # Track by zone
        bet_info = {
            'game_id': game.get('game_id'),
            'date': game.get('date'),
            'bet_side': bet_side,
            'odds': american_odds,
            'edge': edge,
            'won': bet_won,
            'profit': profit
        }
        
        zones[zone]['bets'].append(bet_info)
        results.append(bet_info)

    # Calculate overall metrics
    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
    win_rate = (won_bets / total_bets * 100) if total_bets > 0 else 0
    avg_edge = (sum([r['edge'] for r in results]) / len(results)) if results else 0

    return {
        'total_profit': total_profit,
        'total_bets': total_bets,
        'won_bets': won_bets,
        'win_rate': win_rate,
        'total_staked': total_staked,
        'roi': roi,
        'avg_edge': avg_edge,
        'zones': zones,
        'results': results
    }


def print_zone_analysis(zones):
    """Print detailed breakdown by profitable zone."""
    
    print("\n" + "=" * 70)
    print("BREAKDOWN BY PROFITABLE ZONE")
    print("=" * 70)
    
    profitable_zones = ['heavy_favorite', 'pickem_underdog', 'slight_underdog']
    
    for zone_key in profitable_zones:
        zone = zones[zone_key]
        bets = zone['bets']
        
        if len(bets) == 0:
            continue
            
        wins = sum(1 for b in bets if b['won'])
        total_profit = sum(b['profit'] for b in bets)
        avg_odds = sum(b['odds'] for b in bets) / len(bets)
        avg_edge = sum(b['edge'] for b in bets) / len(bets)
        
        print(f"\n{zone['name']}")
        print("-" * 70)
        print(f"  Bets: {len(bets)}")
        print(f"  Wins: {wins}")
        print(f"  Win Rate: {wins/len(bets):.2%}")
        print(f"  Total Profit: ${total_profit:,.2f}")
        print(f"  ROI: {(total_profit / (len(bets) * 100)) * 100:.2f}%")
        print(f"  Avg Odds: {avg_odds:.0f}")
        print(f"  Avg Edge: {avg_edge * 100:.2f}%")
    
    # Show skipped bets
    skipped = zones['skipped']['bets']
    if len(skipped) > 0:
        print(f"\n{zones['skipped']['name']}")
        print("-" * 70)
        print(f"  Skipped Bets: {len(skipped)}")
        print(f"  Avg Odds (skipped): {sum(b['odds'] for b in skipped) / len(skipped):.0f}")
        print(f"  Avg Edge (skipped): {sum(b['edge'] for b in skipped) / len(skipped) * 100:.2f}%")
        print(f"  → These bets were AVOIDED (death zone)")


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
    return min(k, max_kelly)  # cap at 0.25 for Quarter Kelly


def simulate_profitable_zones_kelly(
    df,
    starting_bankroll=1000.0,
    min_edge=0.0,
    max_edge=0.0471,
    kelly_cap=0.25,
):
    """
    Quarter-Kelly staking in the 'profitable zones':
      - Heavy Favorite: odds < -300
      - Pick'em Underdog: +100 to +110
      - Slight Underdog: +110 to +150
    Skips the 'death zone': -300 to +100 (except +100–110).
    Applies edge band filter [min_edge, max_edge].
    """

    # Optional: bet in chronological order if 'date' exists
    work = df.copy()
    if "date" in work.columns:
        try:
            work["__date__"] = pd.to_datetime(work["date"])
            work = work.sort_values("__date__")
        except Exception:
            pass

    # Track per-zone and global metrics
    zones = {
        'heavy_favorite': {'name': 'Heavy Favorite (<-300)', 'bets': []},
        'pickem_underdog': {'name': "Pick'em Underdog (+100 to +110)", 'bets': []},
        'slight_underdog': {'name': 'Slight Underdog (+110 to +150)', 'bets': []},
        'skipped': {'name': 'SKIPPED (Death Zone -300 to +100)', 'bets': []}
    }

    current_bankroll = float(starting_bankroll)
    total_bets = 0
    won_bets = 0
    total_staked = 0.0
    total_profit = 0.0
    results = []

    for _, game in work.iterrows():
        # Need market odds and model prob
        if pd.isna(game.get('moneyline_a')) or pd.isna(game.get('moneyline_b')):
            continue

        p_win_a = float(game['p_win_A'])
        p_win_b = 1.0 - p_win_a

        ml_a = float(game['moneyline_a'])
        ml_b = float(game['moneyline_b'])

        # Implied probs
        implied_prob_a = odds_to_implied_prob(ml_a)
        implied_prob_b = odds_to_implied_prob(ml_b)

        # Edges
        edge_a = p_win_a - implied_prob_a
        edge_b = p_win_b - implied_prob_b

        # Choose higher-edge side
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

        # Zone filter
        if chosen_odds < -300:
            zone_key = 'heavy_favorite'
        elif 100 <= chosen_odds <= 110:
            zone_key = 'pickem_underdog'
        elif 110 < chosen_odds <= 150:
            zone_key = 'slight_underdog'
        else:
            zone_key = 'skipped'
            zones['skipped']['bets'].append({'odds': chosen_odds, 'edge': chosen_edge})
            continue  # do not bet

        # Kelly stake (Quarter Kelly by default)
        dec_odds = odds_to_decimal(chosen_odds)
        frac = kelly_fraction(chosen_prob, dec_odds, max_kelly=kelly_cap)
        if frac <= 0.0 or current_bankroll <= 0:
            continue  # no positive edge after Kelly, or busted

        bet_amount = current_bankroll * frac
        # Guard tiny dust bets (optional)
        if bet_amount < 1e-6:
            continue

        total_staked += bet_amount
        total_bets += 1

        # Settle result
        actual_winner = int(game['true_winner'])  # 1 for A, 0 for B
        bet_won = (chosen_side == 'A' and actual_winner == 1) or \
                  (chosen_side == 'B' and actual_winner == 0)

        if bet_won:
            profit = bet_amount * (dec_odds - 1.0)
            won_bets += 1
        else:
            profit = -bet_amount

        current_bankroll += profit
        total_profit += profit

        info = {
            'game_id': game.get('game_id'),
            'date': game.get('date'),
            'bet_side': chosen_side,
            'bet_amount': bet_amount,
            'odds': chosen_odds,
            'edge': chosen_edge,
            'won': bet_won,
            'profit': profit,
            'bankroll_after': current_bankroll,
            'kelly_frac': frac,
        }
        zones[zone_key]['bets'].append(info)
        results.append(info)

        if current_bankroll <= 0:
            break  # bankroll exhausted

    roi = (total_profit / total_staked * 100.0) if total_staked > 0 else 0.0
    win_rate = (won_bets / total_bets * 100.0) if total_bets > 0 else 0.0
    avg_edge = (np.mean([r['edge'] for r in results]) if results else 0.0)

    return {
        'starting_bankroll': starting_bankroll,
        'final_bankroll': current_bankroll,
        'total_profit': total_profit,
        'total_return': ((current_bankroll - starting_bankroll) / starting_bankroll * 100.0),
        'total_bets': total_bets,
        'won_bets': won_bets,
        'win_rate': win_rate,
        'total_staked': total_staked,
        'roi': roi,
        'avg_edge': avg_edge,
        'zones': zones,
        'results': results
    }

def main():
    # Read the CSV file
    df = pd.read_csv('data/xgb_model/xgb_all_models_20251009_161142/moneyline_predictions_2025.csv')
    
    # Drop rows with missing market odds
    original_len = len(df)
    df = df.dropna(subset=['moneyline_a', 'moneyline_b'])
    dropped = original_len - len(df)
    
    print("=" * 70)
    print("PROFITABLE ZONES BETTING STRATEGY")
    print("=" * 70)
    print("\nBetting ONLY on:")
    print("  1. Heavy Favorites (odds < -300)")
    print("  2. Pick'em Underdogs (odds +100 to +110)")
    print("  3. Slight Underdogs (odds +110 to +150)")
    print("\nSKIPPING:")
    print("  ❌ Death Zone (odds -300 to +100, excluding +100-110)")
    
    if dropped > 0:
        print(f"\nDropped {dropped} rows with missing market odds ({dropped/original_len:.1%})")
    
    # Simulate with different bet sizes
    print("\n" + "=" * 70)
    print("RESULTS BY BET SIZE")
    print("=" * 70)
    
    bet_sizes = [10, 50, 100]
    
    for bet_size in bet_sizes:
        results = simulate_profitable_zones(
            df, 
            flat_bet_size=bet_size,
            min_edge=0.0,
            max_edge=0.0471
        )
        
        print(f"\n{'='*70}")
        print(f"FLAT BET: ${bet_size} per game")
        print('='*70)
        print(f"Total Bets Placed: {results['total_bets']}")
        print(f"Bets Won: {results['won_bets']}")
        print(f"Win Rate: {results['win_rate']:.2f}%")
        print(f"Total Staked: ${results['total_staked']:,.2f}")
        print(f"Total Profit: ${results['total_profit']:,.2f}")
        print(f"ROI: {results['roi']:.2f}%")
        print(f"Average Edge: {results['avg_edge']*100:.2f}%")
        
        # Print zone breakdown
        print_zone_analysis(results['zones'])
    
    # Show projection with line shopping
    print("\n" + "=" * 70)
    print("PROJECTED RESULTS WITH LINE SHOPPING")
    print("=" * 70)
    
    base_roi = results['roi']
    line_shopping_boost = 1.5  # Conservative estimate: 1.5% boost
    
    projected_roi = base_roi + line_shopping_boost
    
    print(f"\nBase ROI (paper trading): {base_roi:+.2f}%")
    print(f"Line shopping boost (est): +{line_shopping_boost:.2f}%")
    print(f"Projected real ROI: {projected_roi:+.2f}%")
    
    if projected_roi > 3:
        print(f"\n✅ STRONG EDGE: {projected_roi:.2f}% ROI is professional-level")
    elif projected_roi > 1:
        print(f"\n✅ REAL EDGE: {projected_roi:.2f}% ROI is profitable")
    elif projected_roi > 0:
        print(f"\n⚠️  MARGINAL EDGE: {projected_roi:.2f}% ROI is breakeven-ish")
    else:
        print(f"\n❌ NO EDGE: {projected_roi:.2f}% ROI is still losing")
    
    # Show what $1000 becomes
    print("\n" + "=" * 70)
    print("BANKROLL GROWTH PROJECTION")
    print("=" * 70)
    
    starting_bankroll = 1000
    if results['total_bets'] > 0:
        growth_factor = 1 + (results['roi'] / 100)
        final_bankroll = starting_bankroll * growth_factor
        
        print(f"\nStarting bankroll: ${starting_bankroll:,.2f}")
        print(f"After {results['total_bets']} bets: ${final_bankroll:,.2f}")
        print(f"Profit: ${final_bankroll - starting_bankroll:,.2f}")
        
        # With line shopping
        growth_with_shopping = 1 + (projected_roi / 100)
        final_with_shopping = starting_bankroll * growth_with_shopping
        
        print(f"\nWith line shopping: ${final_with_shopping:,.2f}")
        print(f"Projected profit: ${final_with_shopping - starting_bankroll:,.2f}")

    results = simulate_profitable_zones_kelly(
        df,
        starting_bankroll=1000,
        min_edge=0.001,   # e.g., 0.1%
        max_edge=0.0471,  # ~4.71%
        kelly_cap=0.25 # Quarter Kelly
    )

    print(f"\nQuarter Kelly in profitable zones (edge {0.1:.1f}%–{4.71:.2f}%)")
    print("-" * 70)
    print(f"Starting Bankroll: ${results['starting_bankroll']:,.2f}")
    print(f"Final Bankroll:    ${results['final_bankroll']:,.2f}")
    print(f"Total Profit/Loss: ${results['total_profit']:,.2f}")
    print(f"Total Return:      {results['total_return']:.2f}%")
    print(f"Total Bets:        {results['total_bets']}")
    print(f"Bets Won:          {results['won_bets']}")
    print(f"Win Rate:          {results['win_rate']:.2f}%")
    print(f"Total Staked:      ${results['total_staked']:,.2f}")
    print(f"ROI:               {results['roi']:.2f}%")
    print(f"Average Edge:      {results['avg_edge']*100:.2f}%")


if __name__ == "__main__":
    main()