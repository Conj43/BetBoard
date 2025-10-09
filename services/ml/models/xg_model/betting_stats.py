import pandas as pd

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

def kelly_fraction(our_prob, decimal_odds, max_kelly=1.0):
    """Calculate Kelly Criterion bet fraction."""
    b = decimal_odds - 1  # net odds
    p = our_prob
    q = 1 - p
    
    kelly = (b * p - q) / b
    
    # Only bet if kelly is positive (we have an edge)
    if kelly <= 0:
        return 0
    
    # Apply max kelly cap
    return min(kelly, max_kelly)


    
def simulate_betting(df, max_kelly=1.0, starting_bankroll=1000, min_edge=0, max_edge=25.0):
    """Simulate betting with Kelly Criterion and edge band filter [min_edge, max_edge]."""
    current_bankroll = starting_bankroll
    total_bets = 0
    won_bets = 0
    total_staked = 0
    total_profit = 0
    
    results = []
    
    for _, game in df.iterrows():
        if current_bankroll <= 0:
            break

        # require needed columns
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

        # Choose side with higher edge, but only if inside the band
        bet_side = None
        bet_prob = None
        decimal_odds = None
        american_odds = None
        edge = 0

        # pick the higher edge side first
        if edge_a >= edge_b:
            chosen_side = 'A'; chosen_prob = p_win_a; chosen_odds = ml_a; chosen_edge = edge_a
        else:
            chosen_side = 'B'; chosen_prob = p_win_b; chosen_odds = ml_b; chosen_edge = edge_b

        # edge band filter
        if chosen_edge >= min_edge and chosen_edge <= max_edge:
            bet_side = chosen_side
            bet_prob = chosen_prob
            decimal_odds = odds_to_decimal(chosen_odds)
            american_odds = chosen_odds
            edge = chosen_edge

        if bet_side:
            # Kelly fraction (capped)
            kelly_frac = kelly_fraction(bet_prob, decimal_odds, max_kelly)
            if kelly_frac > 0:
                bet_amount = current_bankroll * kelly_frac
                total_staked += bet_amount
                total_bets += 1

                actual_winner = game['true_winner']  # 1 for team A, 0 for team B
                bet_won = (bet_side == 'A' and actual_winner == 1) or \
                          (bet_side == 'B' and actual_winner == 0)

                if bet_won:
                    profit = bet_amount * (decimal_odds - 1)
                    won_bets += 1
                else:
                    profit = -bet_amount

                current_bankroll += profit
                total_profit += profit

                results.append({
                    'game_id': game.get('game_id'),
                    'date': game.get('date'),
                    'bet_side': bet_side,
                    'bet_amount': bet_amount,
                    'odds': american_odds,
                    'edge': edge,
                    'won': bet_won,
                    'profit': profit,
                    'bankroll': current_bankroll
                })

    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
    win_rate = (won_bets / total_bets * 100) if total_bets > 0 else 0
    total_return = ((current_bankroll - starting_bankroll) / starting_bankroll * 100)
    avg_edge = (sum([r['edge'] for r in results]) / len(results)) if results else 0

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
        'avg_edge': avg_edge,
        'results': results
    }

# Main execution
if __name__ == "__main__":
    # Read the CSV file
    df = pd.read_csv('data/xgb_model/xgb_all_models_20251009_161142/moneyline_predictions_2025.csv')

    # Drop rows with missing market odds
    original_len = len(df)
    df = df.dropna(subset=['moneyline_a', 'moneyline_b'])
    dropped = original_len - len(df)
    
    print("=" * 70)
    print("KELLY CRITERION BETTING ANALYSIS")
    print("=" * 70)
    
    if dropped > 0:
        print(f"\nDropped {dropped} rows with missing market odds ({dropped/original_len:.1%})")
        print(f"Analyzing {len(df)} games with valid market data\n")
    
    # Test different Kelly fractions with no edge filter
    print("\n" + "=" * 70)
    print("PART 1: DIFFERENT KELLY FRACTIONS (No edge filter)")
    print("=" * 70)
    
    kelly_fractions = [0.25, 0.5, 1.0]
    kelly_names = ['QUARTER KELLY', 'HALF KELLY', 'FULL KELLY']
    
    for kelly_frac, kelly_name in zip(kelly_fractions, kelly_names):
        results = simulate_betting(df, max_kelly=kelly_frac, min_edge=0)
        
        print(f"\n{kelly_name} ({kelly_frac * 100:.0f}% max)")
        print("-" * 70)
        print(f"Starting Bankroll: ${results['starting_bankroll']:,.2f}")
        print(f"Final Bankroll: ${results['final_bankroll']:,.2f}")
        print(f"Total Profit/Loss: ${results['total_profit']:,.2f}")
        print(f"Total Return: {results['total_return']:.2f}%")
        print(f"\nTotal Bets: {results['total_bets']}")
        print(f"Bets Won: {results['won_bets']}")
        print(f"Win Rate: {results['win_rate']:.2f}%")
        print(f"Total Staked: ${results['total_staked']:,.2f}")
        print(f"ROI: {results['roi']:.2f}%")
        print(f"Average Edge: {results['avg_edge']*100:.2f}%")
    
    # Test different minimum edge thresholds (using Quarter Kelly)
    print("\n\n" + "=" * 70)
    print("PART 2: MINIMUM EDGE THRESHOLDS (Quarter Kelly)")
    print("=" * 70)
    
    edge_thresholds = [0, 0.02, 0.03, 0.05, 0.10]
    
    for min_edge in edge_thresholds:
        results = simulate_betting(df, max_kelly=0.25, min_edge=min_edge)
        
        print(f"\nMinimum Edge: {min_edge*100:.0f}%")
        print("-" * 70)
        print(f"Starting Bankroll: ${results['starting_bankroll']:,.2f}")
        print(f"Final Bankroll: ${results['final_bankroll']:,.2f}")
        print(f"Total Profit/Loss: ${results['total_profit']:,.2f}")
        print(f"Total Return: {results['total_return']:.2f}%")
        print(f"\nTotal Bets: {results['total_bets']}")
        print(f"Bets Won: {results['won_bets']}")
        print(f"Win Rate: {results['win_rate']:.2f}%")
        print(f"Total Staked: ${results['total_staked']:,.2f}")
        print(f"ROI: {results['roi']:.2f}%")
        print(f"Average Edge: {results['avg_edge']*100:.2f}%")


        print("\n" + "=" * 70)
    print("EDGE-BAND STRATEGY: Bet only when edge is between 2% and 5% (Quarter Kelly)")
    print("=" * 70)



    # Define your edge bands to test
    edge_bands = [
        (0.001, 0.01),   # 0.1%–1%
        (0.01, 0.05),    # 1%–5%
        (0.05, 0.10),    # 5%–10%
        (0.10, 0.50),    # 10%–50%
        (0.001, 0.05),
        (0.0001, 0.05),
        (0.0001, 0.0525),
        (0.0001, 0.0475),
        (0.000, 0.0471)
    ]

    # Run each band and print summary
    for lo, hi in edge_bands:
        max_kelly = 1
        results = simulate_betting(df, max_kelly=max_kelly, min_edge=lo, max_edge=hi)
        
        print(f"\nEdge Band: {lo*100:.4f}%–{hi*100:.4f}% | Kelly: {max_kelly*100:.3f}%")
        print("-" * 70)
        print(f"Starting Bankroll: ${results['starting_bankroll']:,.2f}")
        print(f"Final Bankroll: ${results['final_bankroll']:,.2f}")
        print(f"Total Profit/Loss: ${results['total_profit']:,.2f}")
        print(f"Total Return: {results['total_return']:.2f}%")
        print(f"Total Bets: {results['total_bets']}")
        print(f"Bets Won: {results['won_bets']}")
        print(f"Win Rate: {results['win_rate']:.2f}%")
        print(f"Total Staked: ${results['total_staked']:,.2f}")
        print(f"ROI: {results['roi']:.2f}%")
        print(f"Average Edge: {results['avg_edge']*100:.2f}%")