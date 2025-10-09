import pandas as pd
import numpy as np

def odds_to_prob(odds):
    """Convert American odds to probability."""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)

def analyze_market_disagreement(df):
    """
    Analyze where the model performs well vs poorly when disagreeing with market.
    """
    
    # Drop rows with missing market odds
    original_len = len(df)
    df = df.dropna(subset=['moneyline_a', 'moneyline_b']).copy()
    dropped = original_len - len(df)
    
    if dropped > 0:
        print(f"\nDropped {dropped} rows with missing market odds ({dropped/original_len:.1%})")
    
    # Calculate market's implied probabilities
    df['market_prob_A'] = df['moneyline_a'].apply(odds_to_prob)
    df['market_prob_B'] = df['moneyline_b'].apply(odds_to_prob)
    
    # Calculate disagreement (how much model differs from market)
    df['disagreement'] = abs(df['p_win_A'] - df['market_prob_A'])
    
    # Determine who model predicted to win
    df['model_pick_A'] = (df['p_win_A'] > 0.5).astype(int)
    df['market_pick_A'] = (df['market_prob_A'] > 0.5).astype(int)
    
    # Model correct on its prediction
    df['model_correct'] = (df['model_pick_A'] == df['true_winner']).astype(int)
    df['market_correct'] = (df['market_pick_A'] == df['true_winner']).astype(int)
    
    # Model agrees or disagrees with market pick
    df['picks_agree'] = (df['model_pick_A'] == df['market_pick_A']).astype(int)
    
    print("=" * 80)
    print("MARKET DISAGREEMENT ANALYSIS")
    print("=" * 80)
    
    # Overall stats
    print(f"\nTotal Games: {len(df)}")
    print(f"Model Overall Accuracy: {df['model_correct'].mean():.2%}")
    print(f"Market Overall Accuracy: {df['market_correct'].mean():.2%}")
    print(f"Games Where Picks Agree: {df['picks_agree'].sum()} ({df['picks_agree'].mean():.1%})")
    print(f"Games Where Picks Disagree: {(~df['picks_agree'].astype(bool)).sum()} ({(1-df['picks_agree'].mean()):.1%})")
    
    # Performance when model agrees vs disagrees with market
    print("\n" + "=" * 80)
    print("PERFORMANCE: AGREEMENT VS DISAGREEMENT")
    print("=" * 80)
    
    agree_games = df[df['picks_agree'] == 1]
    disagree_games = df[df['picks_agree'] == 0]
    
    print(f"\n{'Scenario':<30} | {'Games':>8} | {'Model Acc':>12} | {'Market Acc':>12}")
    print("-" * 80)
    print(f"{'When Model Agrees with Market':<30} | {len(agree_games):>8} | "
          f"{agree_games['model_correct'].mean():>11.2%} | {agree_games['market_correct'].mean():>11.2%}")
    print(f"{'When Model Disagrees':<30} | {len(disagree_games):>8} | "
          f"{disagree_games['model_correct'].mean():>11.2%} | {disagree_games['market_correct'].mean():>11.2%}")
    
    # Performance by disagreement level
    print("\n" + "=" * 80)
    print("PERFORMANCE BY DISAGREEMENT LEVEL")
    print("=" * 80)
    
    disagreement_bins = [0, 0.02, 0.05, 0.10, 0.15, 0.20, 1.0]
    bin_labels = ['0-2%', '2-5%', '5-10%', '10-15%', '15-20%', '20%+']
    
    df['disagreement_bin'] = pd.cut(df['disagreement'], bins=disagreement_bins, labels=bin_labels)
    
    print(f"\n{'Disagreement':>12} | {'Games':>8} | {'Model Acc':>12} | {'Market Acc':>12} | {'Winner':>12}")
    print("-" * 80)
    
    for bin_label in bin_labels:
        bin_data = df[df['disagreement_bin'] == bin_label]
        if len(bin_data) > 0:
            model_acc = bin_data['model_correct'].mean()
            market_acc = bin_data['market_correct'].mean()
            winner = 'Model' if model_acc > market_acc else 'Market' if market_acc > model_acc else 'Tie'
            print(f"{bin_label:>12} | {len(bin_data):>8} | {model_acc:>11.2%} | "
                  f"{market_acc:>11.2%} | {winner:>12}")
    
    # When model has "edge" (thinks probability is higher than market)
    print("\n" + "=" * 80)
    print("PERFORMANCE WHEN MODEL SEES 'EDGE'")
    print("=" * 80)
    
    edge_thresholds = [0.01, 0.03, 0.05, 0.10, 0.15]
    
    print(f"\n{'Min Edge':>10} | {'Games':>8} | {'Win Rate':>10} | {'Expected':>10} | {'Diff':>10}")
    print("-" * 80)
    
    for threshold in edge_thresholds:
        # Model sees edge on team A
        edge_A = df[(df['p_win_A'] - df['market_prob_A']) >= threshold]
        # Model sees edge on team B
        edge_B = df[(df['market_prob_A'] - df['p_win_A']) >= threshold]
        
        if len(edge_A) > 0:
            # When betting on A
            win_rate_A = (edge_A['true_winner'] == 1).mean()
            expected_A = edge_A['p_win_A'].mean()
            
            print(f"{threshold:>9.0%}+ | {len(edge_A):>8} | {win_rate_A:>9.2%} | "
                  f"{expected_A:>9.2%} | {(win_rate_A - expected_A):>+9.2%}")
        
        if len(edge_B) > 0:
            # When betting on B  
            win_rate_B = (edge_B['true_winner'] == 0).mean()
            expected_B = (1 - edge_B['p_win_A']).mean()
            
            print(f"{threshold:>9.0%}+ | {len(edge_B):>8} | {win_rate_B:>9.2%} | "
                  f"{expected_B:>9.2%} | {(win_rate_B - expected_B):>+9.2%}")
    
    # Analyze by confidence level when disagreeing - WITH DETAILED VERIFICATION
    print("\n" + "=" * 80)
    print("PERFORMANCE WHEN CONFIDENT AND DISAGREEING WITH MARKET (DETAILED)")
    print("=" * 80)
    
    confidence_levels = [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]
    
    print(f"\n{'Conf':>6} | {'Games':>6} | {'High A':>7} | {'Low A':>7} | {'Avg MktA':>9} | {'Model Acc':>10} | {'Mkt Acc':>10}")
    print("-" * 80)
    
    for conf in confidence_levels:
        # Model confident in either direction AND disagrees with market
        high_conf = df[(df['p_win_A'] >= conf) & (df['picks_agree'] == 0)]
        low_conf = df[(df['p_win_A'] <= (1 - conf)) & (df['picks_agree'] == 0)]
        
        all_conf = pd.concat([high_conf, low_conf])
        
        if len(all_conf) > 0:
            model_acc = all_conf['model_correct'].mean()
            market_acc = all_conf['market_correct'].mean()
            avg_mkt = all_conf['market_prob_A'].mean()
            
            print(f"{conf:>5.0%}+ | {len(all_conf):>6} | {len(high_conf):>7} | {len(low_conf):>7} | "
                  f"{avg_mkt:>8.1%} | {model_acc:>9.2%} | {market_acc:>9.2%}")
    
    # Show some examples of high confidence disagreements
    print("\n" + "=" * 80)
    print("SAMPLE HIGH CONFIDENCE DISAGREEMENTS (90%+)")
    print("=" * 80)
    
    high_90 = df[((df['p_win_A'] >= 0.9) | (df['p_win_A'] <= 0.1)) & (df['picks_agree'] == 0)]
    
    if len(high_90) > 0:
        sample = high_90.head(10)[['team_A', 'team_B', 'p_win_A', 'market_prob_A', 
                                    'model_pick_A', 'market_pick_A', 'true_winner', 'model_correct']]
        print("\nFirst 10 examples:")
        for idx, row in sample.iterrows():
            model_pick = 'A' if row['model_pick_A'] == 1 else 'B'
            market_pick = 'A' if row['market_pick_A'] == 1 else 'B'
            actual = 'A' if row['true_winner'] == 1 else 'B'
            correct = '✓' if row['model_correct'] else '✗'
            
            print(f"{correct} Model: {row['p_win_A']:.1%} picked {model_pick}, "
                  f"Market: {row['market_prob_A']:.1%} picked {market_pick}, "
                  f"Actual: {actual}")
    
    # Find best opportunities (where model beats market most)
    print("\n" + "=" * 80)
    print("BEST OPPORTUNITIES (Model Beats Market Most)")
    print("=" * 80)
    
    # Look at games where model disagrees and see where it wins
    disagree = df[df['picks_agree'] == 0].copy()
    
    if len(disagree) > 0:
        # When model picks underdog
        disagree['model_picks_underdog'] = (
            ((df['p_win_A'] > 0.5) & (df['market_prob_A'] < 0.5)) |
            ((df['p_win_A'] < 0.5) & (df['market_prob_A'] > 0.5))
        )
        
        underdog_picks = disagree[disagree['model_picks_underdog']]
        favorite_picks = disagree[~disagree['model_picks_underdog']]
        
        print(f"\n{'Scenario':<35} | {'Games':>8} | {'Model Acc':>12} | {'Market Acc':>12}")
        print("-" * 80)
        
        if len(underdog_picks) > 0:
            print(f"{'Model Picks Market Underdog':<35} | {len(underdog_picks):>8} | "
                  f"{underdog_picks['model_correct'].mean():>11.2%} | "
                  f"{underdog_picks['market_correct'].mean():>11.2%}")
        
        if len(favorite_picks) > 0:
            print(f"{'Model Picks Market Favorite':<35} | {len(favorite_picks):>8} | "
                  f"{favorite_picks['model_correct'].mean():>11.2%} | "
                  f"{favorite_picks['market_correct'].mean():>11.2%}")
    
    # Closing line value simulation
    print("\n" + "=" * 80)
    print("CLOSING LINE VALUE (CLV) - Are you getting +EV bets?")
    print("=" * 80)
    
    print(f"\n{'Edge Threshold':>15} | {'Bets':>8} | {'Actual Win':>12} | {'Needed Win':>12} | {'Profitable?':>12}")
    print("-" * 80)
    
    for threshold in [0.01, 0.03, 0.05, 0.10]:
        # Calculate needed win rate based on average odds
        bets_A = df[(df['p_win_A'] - df['market_prob_A']) >= threshold]
        bets_B = df[(df['market_prob_A'] - df['p_win_A']) >= threshold]
        
        all_bets = pd.concat([
            bets_A.assign(bet_team='A', bet_odds=bets_A['moneyline_a'], won=(bets_A['true_winner']==1)),
            bets_B.assign(bet_team='B', bet_odds=bets_B['moneyline_b'], won=(bets_B['true_winner']==0))
        ])
        
        if len(all_bets) > 0:
            actual_win_rate = all_bets['won'].mean()
            
            # Calculate breakeven rate from average odds
            avg_decimal = all_bets['bet_odds'].apply(lambda x: 
                1 + (100/abs(x)) if x < 0 else 1 + (x/100)).mean()
            needed_win_rate = 1 / avg_decimal
            
            profitable = 'YES' if actual_win_rate > needed_win_rate else 'NO'
            
            print(f"{threshold:>14.0%}+ | {len(all_bets):>8} | {actual_win_rate:>11.2%} | "
                  f"{needed_win_rate:>11.2%} | {profitable:>12}")

# Main execution
if __name__ == "__main__":
    df = pd.read_csv('data/xgb_model/xgb_all_models_20251007_201057/moneyline_predictions_2025.csv')
    analyze_market_disagreement(df)