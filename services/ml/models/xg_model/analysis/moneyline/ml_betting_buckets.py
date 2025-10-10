import pandas as pd
import sys
from datetime import datetime
year = 2025
directory = "data/xgb_model/xgb_all_models_20251010_132522"
FILE_PATH = f"{directory}/moneyline_predictions_{year}.csv"

# Create output file with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"services/ml/models/xg_model/analysis/moneyline/data/betting_analysis_{timestamp}.txt"

# Custom print function that writes to both console and file
class DualOutput:
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

# Redirect stdout to dual output
dual_output = DualOutput(output_file)
sys.stdout = dual_output

print(f"Output will be saved to: {output_file}")
print("=" * 70)

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

def simulate_flat_betting_with_buckets(df, flat_bet_size=100, min_edge=0, max_edge=25.0, min_odds=None, max_odds=None):
    """Simulate betting with fixed bet size, edge band filter, and odds bucket tracking."""
    total_bets = 0
    won_bets = 0
    total_staked = 0
    total_profit = 0
    
    favorite_bets = []
    underdog_bets = []
    odds_buckets = {}
    
    results = []
    
    for _, game in df.iterrows():
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
            # Skip heavy favorites (odds -1000 or worse)
            if chosen_odds <= -1000:
                continue
            
            # Apply odds range filter if specified
            if min_odds is not None and chosen_odds < min_odds:
                continue
            if max_odds is not None and chosen_odds > max_odds:
                continue
            
            bet_side = chosen_side
            bet_prob = chosen_prob
            decimal_odds = odds_to_decimal(chosen_odds)
            american_odds = chosen_odds
            edge = chosen_edge

        if bet_side:
            bet_amount = flat_bet_size
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

            total_profit += profit
            
            # Track by odds bucket
            bucket = get_odds_bucket(american_odds)
            if bucket not in odds_buckets:
                odds_buckets[bucket] = {
                    'bets': [],
                    'count': 0,
                    'wins': 0,
                    'profit': 0,
                    'staked': 0
                }
            
            odds_buckets[bucket]['bets'].append({
                'odds': american_odds,
                'won': bet_won,
                'profit': profit,
                'edge': edge
            })
            odds_buckets[bucket]['count'] += 1
            odds_buckets[bucket]['wins'] += (1 if bet_won else 0)
            odds_buckets[bucket]['profit'] += profit
            odds_buckets[bucket]['staked'] += bet_amount
            
            # Track favorite vs underdog
            bet_info = {
                'odds': american_odds,
                'won': bet_won,
                'profit': profit
            }
            
            if american_odds < 0:
                favorite_bets.append(bet_info)
            else:
                underdog_bets.append(bet_info)

            results.append({
                'game_id': game.get('game_id'),
                'date': game.get('date'),
                'bet_side': bet_side,
                'bet_amount': bet_amount,
                'odds': american_odds,
                'edge': edge,
                'won': bet_won,
                'profit': profit,
            })

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
        'favorite_bets': favorite_bets,
        'underdog_bets': underdog_bets,
        'odds_buckets': odds_buckets,
        'results': results
    }

def simulate_flat_betting(df, flat_bet_size=100, min_edge=0, max_edge=25.0):
    """Simulate betting with fixed bet size and edge band filter."""
    total_bets = 0
    won_bets = 0
    total_staked = 0
    total_profit = 0
    
    favorite_bets = []
    underdog_bets = []
    
    results = []
    
    for _, game in df.iterrows():
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
            # Skip heavy favorites (odds -1000 or worse)
            if chosen_odds <= -1000:
                continue
            
            bet_side = chosen_side
            bet_prob = chosen_prob
            decimal_odds = odds_to_decimal(chosen_odds)
            american_odds = chosen_odds
            edge = chosen_edge

        if bet_side:
            bet_amount = flat_bet_size
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

            total_profit += profit
            
            # Track favorite vs underdog
            bet_info = {
                'odds': american_odds,
                'won': bet_won,
                'profit': profit
            }
            
            if american_odds < 0:
                favorite_bets.append(bet_info)
            else:
                underdog_bets.append(bet_info)

            results.append({
                'game_id': game.get('game_id'),
                'date': game.get('date'),
                'bet_side': bet_side,
                'bet_amount': bet_amount,
                'odds': american_odds,
                'edge': edge,
                'won': bet_won,
                'profit': profit,
            })

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
        'favorite_bets': favorite_bets,
        'underdog_bets': underdog_bets,
        'results': results
    }

    
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
            # Skip heavy favorites (odds -1000 or worse)
            if chosen_odds <= -1000:
                continue
                
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
    df = pd.read_csv(FILE_PATH)

    # Drop rows with missing market odds
    original_len = len(df)
    df = df.dropna(subset=['moneyline_a', 'moneyline_b'])
    dropped = original_len - len(df)
    


    
    if dropped > 0:
        print(f"\nDropped {dropped} rows with missing market odds ({dropped/original_len:.1%})")
        print(f"Analyzing {len(df)} games with valid market data\n")
    
   

    # print("\n" + "=" * 70)
    # print("EDGE-BAND STRATEGY: Testing various edge bands")
    # print("=" * 70)

    # Define your edge bands to test
    # edge_bands = [
    #     (0.000, 0.0471)
    # ]

    # Run each band and print summary
    # for lo, hi in edge_bands:
    #     max_kelly = 0.25
    #     results = simulate_betting(df, max_kelly=max_kelly, min_edge=lo, max_edge=hi)
        
    #     print(f"\nEdge Band: {lo*100:.4f}%–{hi*100:.4f}% | Kelly: {max_kelly*100:.0f}%")
    #     print("-" * 70)
    #     print(f"Starting Bankroll: ${results['starting_bankroll']:,.2f}")
    #     print(f"Final Bankroll: ${results['final_bankroll']:,.2f}")
    #     print(f"Total Profit/Loss: ${results['total_profit']:,.2f}")
    #     print(f"Total Return: {results['total_return']:.2f}%")
    #     print(f"Total Bets: {results['total_bets']}")
    #     print(f"Bets Won: {results['won_bets']}")
    #     print(f"Win Rate: {results['win_rate']:.2f}%")
    #     print(f"Total Staked: ${results['total_staked']:,.2f}")
    #     print(f"ROI: {results['roi']:.2f}%")
    #     print(f"Average Edge: {results['avg_edge']*100:.2f}%")
    
    
    # FLAT BETTING ANALYSIS
    # print("\n\n" + "=" * 70)
    # print("PART 3: FLAT BETTING ANALYSIS (Best Edge Band)")
    # print("=" * 70)
    
    # # Test the best edge band with flat betting
    # best_edge_band = (0.000, 0.0471)  # Your best performing band
    # flat_bet_sizes = [10, 50, 100]
    
    # for flat_size in flat_bet_sizes:
    #     flat_results = simulate_flat_betting(df, flat_bet_size=flat_size, 
    #                                          min_edge=best_edge_band[0], 
    #                                          max_edge=best_edge_band[1])
        
    #     print(f"\nFlat Bet: ${flat_size} per game")
    #     print("-" * 70)
    #     print(f"Total Bets: {flat_results['total_bets']}")
    #     print(f"Bets Won: {flat_results['won_bets']}")
    #     print(f"Win Rate: {flat_results['win_rate']:.2f}%")
    #     print(f"Total Staked: ${flat_results['total_staked']:,.2f}")
    #     print(f"Total Profit/Loss: ${flat_results['total_profit']:,.2f}")
    #     print(f"ROI: {flat_results['roi']:.2f}%")
    #     print(f"Average Edge: {flat_results['avg_edge']*100:.2f}%")
        
    #     # Favorite vs Underdog breakdown
    #     fav_bets = flat_results['favorite_bets']
    #     dog_bets = flat_results['underdog_bets']
        
    #     print(f"\n  Favorite Bets: {len(fav_bets)} ({len(fav_bets)/flat_results['total_bets']:.1%})")
    #     if len(fav_bets) > 0:
    #         fav_wins = sum(1 for b in fav_bets if b['won'])
    #         fav_profit = sum(b['profit'] for b in fav_bets)
    #         fav_avg_odds = sum(b['odds'] for b in fav_bets) / len(fav_bets)
    #         print(f"    Win Rate: {fav_wins/len(fav_bets):.2%}")
    #         print(f"    Profit: ${fav_profit:,.2f}")
    #         print(f"    Avg Odds: {fav_avg_odds:.0f}")
    #         print(f"    ROI: {(fav_profit/(flat_size*len(fav_bets)))*100:.2f}%")
        
    #     print(f"\n  Underdog Bets: {len(dog_bets)} ({len(dog_bets)/flat_results['total_bets']:.1%})")
    #     if len(dog_bets) > 0:
    #         dog_wins = sum(1 for b in dog_bets if b['won'])
    #         dog_profit = sum(b['profit'] for b in dog_bets)
    #         dog_avg_odds = sum(b['odds'] for b in dog_bets) / len(dog_bets)
    #         print(f"    Win Rate: {dog_wins/len(dog_bets):.2%}")
    #         print(f"    Profit: ${dog_profit:,.2f}")
    #         print(f"    Avg Odds: {dog_avg_odds:.0f}")
    #         print(f"    ROI: {(dog_profit/(flat_size*len(dog_bets)))*100:.2f}%")
    
    # NEW SECTION: ODDS BUCKET ANALYSIS
    print("\n\n" + "=" * 70)
    print("PART 4: ODDS BUCKET ANALYSIS (0-4.71% Edge Band)")
    print("=" * 70)
    
    flat_results = simulate_flat_betting_with_buckets(df, flat_bet_size=100, 
                                                      min_edge=0.000, 
                                                      max_edge=0.0471)
    
    print(f"\nOverall Stats:")
    print("-" * 70)
    print(f"Total Bets: {flat_results['total_bets']}")
    print(f"Win Rate: {flat_results['win_rate']:.2f}%")
    print(f"Total Profit: ${flat_results['total_profit']:,.2f}")
    print(f"ROI: {flat_results['roi']:.2f}%")
    
    print(f"\n\nBreakdown by Odds Bucket:")
    print("=" * 70)
    
    # Sort buckets by typical odds order
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
    
    for bucket_name in bucket_order:
        if bucket_name in flat_results['odds_buckets']:
            bucket = flat_results['odds_buckets'][bucket_name]
            win_rate = (bucket['wins'] / bucket['count'] * 100) if bucket['count'] > 0 else 0
            roi = (bucket['profit'] / bucket['staked'] * 100) if bucket['staked'] > 0 else 0
            avg_odds = sum(b['odds'] for b in bucket['bets']) / len(bucket['bets'])
            avg_edge = sum(b['edge'] for b in bucket['bets']) / len(bucket['bets']) * 100
            
            print(f"\n{bucket_name}")
            print("-" * 70)
            print(f"  Count: {bucket['count']} ({bucket['count']/flat_results['total_bets']:.1%} of total)")
            print(f"  Wins: {bucket['wins']}")
            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  Total Staked: ${bucket['staked']:,.2f}")
            print(f"  Total Profit: ${bucket['profit']:,.2f}")
            print(f"  ROI: {roi:.2f}%")
            print(f"  Avg Odds: {avg_odds:.0f}")
            print(f"  Avg Edge: {avg_edge:.2f}%")
    
    # NEW SECTION: ODDS RANGE FILTER
    print("\n\n" + "=" * 70)
    print("PART 5: ODDS RANGE FILTER (0-4.71% Edge + Odds -10000 to +150)")
    print("=" * 70)
    
    flat_results_filtered = simulate_flat_betting_with_buckets(df, flat_bet_size=100, 
                                                                min_edge=0.000, 
                                                                max_edge=0.0471,
                                                                min_odds=-10000,
                                                                max_odds=150)
    
    print(f"\nFiltered Stats (Odds between -10000 and +150):")
    print("-" * 70)
    print(f"Total Bets: {flat_results_filtered['total_bets']}")
    print(f"Win Rate: {flat_results_filtered['win_rate']:.2f}% ")
    print(f"Total Profit: ${flat_results_filtered['total_profit']:,.2f} ")
    print(f"ROI: {flat_results_filtered['roi']:.2f}% ")
    print(f"Total Staked: ${flat_results_filtered['total_staked']:,.2f}")

    
    print(f"\n\nBreakdown by Odds Bucket (Filtered):")
    print("=" * 70)
    
    for bucket_name in bucket_order:
        if bucket_name in flat_results_filtered['odds_buckets']:
            bucket = flat_results_filtered['odds_buckets'][bucket_name]
            win_rate = (bucket['wins'] / bucket['count'] * 100) if bucket['count'] > 0 else 0
            roi = (bucket['profit'] / bucket['staked'] * 100) if bucket['staked'] > 0 else 0
            avg_odds = sum(b['odds'] for b in bucket['bets']) / len(bucket['bets'])
            avg_edge = sum(b['edge'] for b in bucket['bets']) / len(bucket['bets']) * 100
            
            print(f"\n{bucket_name}")
            print("-" * 70)
            print(f"  Count: {bucket['count']} ({bucket['count']/flat_results_filtered['total_bets']:.1%} of total)")
            print(f"  Wins: {bucket['wins']}")
            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  Total Staked: ${bucket['staked']:,.2f}")
            print(f"  Total Profit: ${bucket['profit']:,.2f}")
            print(f"  ROI: {roi:.2f}%")
            print(f"  Avg Odds: {avg_odds:.0f}")
            print(f"  Avg Edge: {avg_edge:.2f}%")
            
    sys.stdout.close()
    sys.stdout = dual_output.terminal
    print(f"\nResults saved to: {output_file}")