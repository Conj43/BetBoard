# analyze_predictions.py
"""Analyze model predictions to identify strengths, weaknesses, and betting opportunities."""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def load_predictions_with_context():
    """Load predictions and merge with cleaned data for contextual features."""
    # Load predictions
    model_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lgb_model")
    runs = [d for d in os.listdir(model_dir) if d.startswith("run_")]
    latest_run = sorted(runs)[-1]
    pred_path = os.path.join(model_dir, latest_run, "predictions_all_seasons.csv")
    
    print(f"Loading predictions from: {latest_run}")
    predictions = pd.read_csv(pred_path)
    
    # Load cleaned data with context
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cleaned")
    
    # Load all seasons
    all_cleaned = []
    for year in predictions['season'].unique():
        cleaned_path = os.path.join(data_dir, f"per_game_{int(year)}.csv")
        if os.path.exists(cleaned_path):
            df_year = pd.read_csv(cleaned_path)
            df_year['season'] = int(year)
            all_cleaned.append(df_year)
            print(f"Loaded {len(df_year)} games from {year}")
    
    if not all_cleaned:
        print("Warning: No cleaned data found, returning predictions only")
        return predictions
    
    cleaned = pd.concat(all_cleaned, ignore_index=True)
    print(f"Total cleaned games: {len(cleaned)}")
    print(f"Cleaned columns: {list(cleaned.columns[:20])}")  # Show first 20 columns
    
    # Merge on game_key if it exists in both
    if 'game_key' in predictions.columns and 'game_key' in cleaned.columns:
        print("Merging on game_key...")
        
        # Select context columns to merge
        context_cols = ['game_key']
        for col in ['is_home', 'is_neutral', 'is_conf_game', 'team_barthag', 'opp_barthag']:
            if col in cleaned.columns:
                context_cols.append(col)
        
        merged = predictions.merge(
            cleaned[context_cols],
            on='game_key',
            how='left',
            suffixes=('', '_context')
        )
    else:
        print("Warning: game_key not found, skipping context merge")
        return predictions
    
    print(f"Merged {len(merged)} predictions with context data")
    
    # Report merge success
    if 'is_home' in merged.columns:
        coverage = merged['is_home'].notna().mean()
        print(f"Context merge coverage: {coverage:.1%}")
    
    context_cols_available = [c for c in ['is_home', 'is_neutral', 'is_conf_game', 'team_barthag', 'opp_barthag'] if c in merged.columns]
    print(f"Context columns available: {context_cols_available}")
    
    return merged


def analyze_prediction_errors(df):
    """Identify systematic biases in predictions."""
    print("\n" + "="*70)
    print("PREDICTION ERROR ANALYSIS")
    print("="*70)
    
    # Overall error distribution
    print(f"\nMargin Error Distribution:")
    print(f"  Mean: {df['err_margin'].mean():.2f}")
    print(f"  Median: {df['err_margin'].median():.2f}")
    print(f"  Std: {df['err_margin'].std():.2f}")
    print(f"  75th percentile: {df['err_margin'].quantile(0.75):.2f}")
    print(f"  95th percentile: {df['err_margin'].quantile(0.95):.2f}")
    
    # Bias check: are we consistently over/under predicting?
    mean_margin_error = (df['pred_margin'] - df['true_margin']).mean()
    print(f"\nMargin Bias: {mean_margin_error:.2f} points")
    print(f"  (Positive = over-predicting favorite's margin)")
    
    # Errors by game closeness
    df['true_margin_abs'] = df['true_margin'].abs()
    df['game_type'] = pd.cut(df['true_margin_abs'], 
                             bins=[0, 5, 15, 100],
                             labels=['Close (<5)', 'Competitive (5-15)', 'Blowout (>15)'])
    
    print(f"\nErrors by Game Type:")
    for game_type in ['Close (<5)', 'Competitive (5-15)', 'Blowout (>15)']:
        subset = df[df['game_type'] == game_type]
        print(f"  {game_type}: MAE = {subset['err_margin'].mean():.2f}, Acc = {subset['correct_winner'].mean():.1%}, n={len(subset)}")
    
    # Errors by confidence level
    df['confidence'] = df['p_win_A'].apply(lambda x: max(x, 1-x))
    df['confidence_bucket'] = pd.cut(df['confidence'],
                                     bins=[0.5, 0.6, 0.7, 0.8, 1.0],
                                     labels=['50-60%', '60-70%', '70-80%', '80%+'])
    
    print(f"\nErrors by Confidence Level:")
    for bucket in ['50-60%', '60-70%', '70-80%', '80%+']:
        subset = df[df['confidence_bucket'] == bucket]
        if len(subset) > 0:
            print(f"  {bucket}: MAE = {subset['err_margin'].mean():.2f}, Acc = {subset['correct_winner'].mean():.1%}, n={len(subset)}")


def analyze_calibration(df):
    """Check if win probabilities are well-calibrated."""
    print("\n" + "="*70)
    print("PROBABILITY CALIBRATION")
    print("="*70)
    
    # Bin predictions by probability
    df['prob_bucket'] = pd.cut(df['p_win_A'],
                               bins=[0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                               labels=['0-50%', '50-60%', '60-70%', '70-80%', '80-90%', '90%+'])
    
    print(f"\nCalibration Table:")
    print(f"{'Predicted Prob':<15} {'Actual Win %':<15} {'Count':<10} {'Delta'}")
    print("-" * 55)
    
    for bucket in df['prob_bucket'].dropna().unique():
        subset = df[df['prob_bucket'] == bucket]
        actual = subset['true_winner'].mean()
        predicted = subset['p_win_A'].mean()
        delta = actual - predicted
        print(f"{bucket:<15} {actual:>6.1%}        {len(subset):<10} {delta:+.3f}")


def simulate_betting_performance(df):
    """Simulate historical betting performance with different strategies."""
    print("\n" + "="*70)
    print("SIMULATED BETTING PERFORMANCE")
    print("="*70)
    
    # Filter to games with betting lines
    bet_df = df[df['bet_spread'].notna()].copy()
    print(f"\nGames with betting lines: {len(bet_df)}")
    
    if len(bet_df) == 0:
        print("No betting line data available")
        return
    
    # --- SPREAD BETTING LOGIC ---
    # bet_spread is negative when Team A is favored (e.g., -7 means A favored by 7)
    # bet_spread is positive when Team A is underdog (e.g., +3 means A getting 3 points)
    
    # Calculate edge: how much better/worse we think Team A will do vs the spread
    # Positive edge = we think Team A will cover
    # Negative edge = we think Team B will cover
    bet_df['spread_edge'] = bet_df['pred_margin'] + bet_df['bet_spread']
    
    # Determine which team we bet on
    bet_df['bet_on_team_A'] = (bet_df['spread_edge'] > 0).astype(int)
    
    # Determine who actually covered
    bet_df['team_A_covered'] = (bet_df['true_margin'] + bet_df['bet_spread'] > 0).astype(int)
    
    # Did our bet win?
    bet_df['bet_won'] = (bet_df['bet_on_team_A'] == bet_df['team_A_covered']).astype(int)
    
    # Spread betting confidence - distance from 50/50 after accounting for spread
    # Convert edge to probability of covering using margin std dev
    margin_std = bet_df['pred_margin'].std() if len(bet_df) > 0 else 14
    from scipy.stats import norm
    bet_df['spread_confidence'] = bet_df['spread_edge'].apply(
        lambda edge: norm.cdf(abs(edge) / margin_std)
    )
    
    # Strategy 1: Bet Every Game
    all_roi = ((bet_df['bet_won'].mean() * 210 - 110) / 110) * 100
    print(f"\nStrategy 1: Bet Every Game")
    print(f"  Bets: {len(bet_df)}")
    print(f"  Win rate: {bet_df['bet_won'].mean():.1%}")
    print(f"  ROI: {all_roi:.2f}%")
    
    # Strategy 2: Only bet when edge > threshold (in points)
    print(f"\nStrategy 2: Minimum Edge (in points)")
    for threshold in [2, 3, 5, 7, 10]:
        filtered = bet_df[bet_df['spread_edge'].abs() > threshold]
        if len(filtered) > 0:
            win_rate = filtered['bet_won'].mean()
            roi = ((win_rate * 210 - 110) / 110) * 100
            print(f"  Edge > {threshold} pts: {len(filtered):3d} bets, {win_rate:.1%} win rate, {roi:+.2f}% ROI")
    
    # Strategy 3: High spread confidence
    print(f"\nStrategy 3: High Spread Confidence")
    for conf_threshold in [0.60, 0.65, 0.70, 0.75]:
        high_conf = bet_df[bet_df['spread_confidence'] > conf_threshold]
        if len(high_conf) > 0:
            win_rate = high_conf['bet_won'].mean()
            roi = ((win_rate * 210 - 110) / 110) * 100
            print(f"  Confidence > {conf_threshold:.0%}: {len(high_conf):3d} bets, {win_rate:.1%} win rate, {roi:+.2f}% ROI")
    
    # Strategy 4: Combined (edge + confidence)
    print(f"\nStrategy 4: Edge + Confidence Combined")
    for edge_thresh in [3, 5]:
        for conf_thresh in [0.60, 0.65]:
            combined = bet_df[
                (bet_df['spread_edge'].abs() > edge_thresh) & 
                (bet_df['spread_confidence'] > conf_thresh)
            ]
            if len(combined) > 0:
                win_rate = combined['bet_won'].mean()
                roi = ((win_rate * 210 - 110) / 110) * 100
                print(f"  Edge>{edge_thresh}pts + Conf>{conf_thresh:.0%}: {len(combined):3d} bets, {win_rate:.1%} win rate, {roi:+.2f}% ROI")
    
    # Performance by Season
    print("\nPerformance by Season:")
    for season in sorted(bet_df['season'].unique()):
        season_df = bet_df[bet_df['season'] == season]
        if len(season_df) > 0:
            win_rate = season_df['bet_won'].mean()
            avg_edge = season_df['spread_edge'].abs().mean()
            roi = ((win_rate * 210 - 110) / 110) * 100
            print(f"  {season}: {win_rate:.1%} win rate, {roi:+.2f}% ROI, {avg_edge:.1f} avg edge, n={len(season_df)}")


def find_worst_predictions(df, n=20):
    """Identify games where model was most wrong."""
    print("\n" + "="*70)
    print(f"TOP {n} WORST PREDICTIONS")
    print("="*70)
    
    worst = df.nlargest(n, 'err_margin')[
        ['date', 'team_A', 'team_B', 'true_margin', 'pred_margin', 'err_margin', 'p_win_A']
    ]
    
    print("\n" + worst.to_string(index=False))

def debug_betting_logic(df):
    """Debug the betting simulation to find why results are too good."""
    bet_df = df[df['bet_spread'].notna()].copy()
    
    # Calculate betting columns (same as in simulate_betting_performance)
    bet_df['spread_edge'] = bet_df['pred_margin'] + bet_df['bet_spread']
    bet_df['bet_on_team_A'] = (bet_df['spread_edge'] > 0).astype(int)
    bet_df['team_A_covered'] = (bet_df['true_margin'] + bet_df['bet_spread'] > 0).astype(int)
    bet_df['bet_won'] = (bet_df['bet_on_team_A'] == bet_df['team_A_covered']).astype(int)
    
    print("="*70)
    print("DEBUGGING BETTING LOGIC")
    print("="*70)
    
    # 1. Check if pred_margin and true_margin are suspiciously similar
    print("\n1. CHECKING FOR DATA LEAKAGE")
    correlation = bet_df[['pred_margin', 'true_margin']].corr().iloc[0, 1]
    print(f"Correlation between pred_margin and true_margin: {correlation:.4f}")
    print("(Should be ~0.3-0.5 for a good model, >0.9 suggests leakage)")
    
    mae = (bet_df['pred_margin'] - bet_df['true_margin']).abs().mean()
    print(f"Mean Absolute Error: {mae:.2f} points")
    print("(Should be ~10-12 points for NBA, <5 suggests leakage)")
    
    # 2. Look at sample predictions
    print("\n2. SAMPLE PREDICTIONS")
    sample = bet_df.sample(min(10, len(bet_df)), random_state=42)
    cols_to_show = ['pred_margin', 'true_margin', 'bet_spread', 'spread_edge', 'bet_won']
    if 'team_A' in bet_df.columns:
        cols_to_show = ['team_A', 'team_B'] + cols_to_show
    print("\nRandom sample of predictions:")
    print(sample[cols_to_show].to_string())
    
    # 3. Check spread sign convention
    print("\n3. SPREAD SIGN CHECK")
    print("\nWhen Team A is favored (should win):")
    favored = bet_df[bet_df['bet_spread'] < -5].head(5)
    cols = ['bet_spread', 'pred_margin', 'true_margin']
    if 'team_A' in bet_df.columns:
        cols = ['team_A', 'team_B'] + cols
    print(favored[cols].to_string())
    
    print("\nWhen Team A is underdog:")
    underdog = bet_df[bet_df['bet_spread'] > 5].head(5)
    print(underdog[cols].to_string())
    
    # 4. Check if we're training on test data
    print("\n4. TEMPORAL CHECK")
    print("Are predictions made BEFORE games were played?")
    if 'game_date' in bet_df.columns and 'prediction_date' in bet_df.columns:
        future_leak = (bet_df['prediction_date'] > bet_df['game_date']).sum()
        print(f"Predictions made AFTER game: {future_leak} ({future_leak/len(bet_df):.1%})")
    else:
        print("No date columns to check - THIS IS A PROBLEM")
        print("You might be testing on training data!")
    
    # 5. Distribution of edges
    print("\n5. EDGE DISTRIBUTION")
    print(f"Mean absolute edge: {bet_df['spread_edge'].abs().mean():.2f} points")
    print(f"Median absolute edge: {bet_df['spread_edge'].abs().median():.2f} points")
    print(f"% of bets with >5pt edge: {(bet_df['spread_edge'].abs() > 5).mean():.1%}")
    print("(Real models rarely have >3pt edge on average)")
    
    # 6. Check the actual bet logic with a manual example
    print("\n6. MANUAL CALCULATION CHECK")
    example = bet_df.iloc[0]
    team_a_name = example.get('team_A', 'Team A')
    team_b_name = example.get('team_B', 'Team B')
    print(f"\nExample game: {team_a_name} vs {team_b_name}")
    print(f"Predicted margin: {example['pred_margin']:.1f} (+ means A wins)")
    print(f"Betting spread: {example['bet_spread']:.1f} (- means A favored)")
    print(f"Spread edge: {example['spread_edge']:.1f}")
    print(f"We bet on: {'Team A' if example['bet_on_team_A'] else 'Team B'}")
    print(f"Actual margin: {example['true_margin']:.1f}")
    print(f"Team A covered: {bool(example['team_A_covered'])}")
    print(f"Our bet won: {bool(example['bet_won'])}")
    
    # Manual check
    actual_cover = (example['true_margin'] + example['bet_spread']) > 0
    print(f"\nManual cover check: {actual_cover}")
    print(f"Matches team_A_covered: {actual_cover == bool(example['team_A_covered'])}")
    
    # 7. Win rate by predicted edge direction
    print("\n7. WIN RATE BY EDGE DIRECTION")
    bet_A = bet_df[bet_df['spread_edge'] > 0]
    bet_B = bet_df[bet_df['spread_edge'] < 0]
    print(f"When edge favors A (bet A): {bet_A['bet_won'].mean():.1%} win rate, n={len(bet_A)}")
    print(f"When edge favors B (bet B): {bet_B['bet_won'].mean():.1%} win rate, n={len(bet_B)}")
    print("(Both should be similar if model is unbiased)")
    
    # 8. Check columns available
    print("\n8. AVAILABLE COLUMNS")
    print(f"Columns in dataframe: {list(bet_df.columns)}")
    

def simulate_moneyline_betting(df):
    """Analyze betting performance on moneyline (who wins outright)."""
    print("\n" + "="*70)
    print("MONEYLINE BETTING PERFORMANCE")
    print("="*70)
    
    # Filter to games with moneyline odds
    ml_df = df[(df['moneyline_a'].notna()) & (df['moneyline_b'].notna())].copy()
    print(f"\nGames with moneyline odds: {len(ml_df)}")
    
    if len(ml_df) == 0:
        print("No moneyline data available")
        return
    
    # Predict winner based on model
    ml_df['predicted_winner'] = (ml_df['pred_margin'] > 0).astype(int)  # 1 = Team A, 0 = Team B
    ml_df['actual_winner'] = (ml_df['true_margin'] > 0).astype(int)
    ml_df['prediction_correct'] = (ml_df['predicted_winner'] == ml_df['actual_winner']).astype(int)
    
    # Calculate payout for each bet
    # If we bet on Team A and they win, payout based on moneyline_a
    # If we bet on Team B and they win, payout based on moneyline_b
    def calculate_ml_payout(row):
        """Calculate profit/loss on $100 bet."""
        bet_on_a = row['predicted_winner'] == 1
        a_won = row['actual_winner'] == 1
        
        if bet_on_a:
            if a_won:
                # Won betting on A
                ml = row['moneyline_a']
                return 100 * (ml / 100 if ml > 0 else -100 / ml)
            else:
                # Lost betting on A
                return -100
        else:
            if not a_won:
                # Won betting on B
                ml = row['moneyline_b']
                return 100 * (ml / 100 if ml > 0 else -100 / ml)
            else:
                # Lost betting on B
                return -100
    
    ml_df['profit'] = ml_df.apply(calculate_ml_payout, axis=1)
    
    # Overall performance
    win_rate = ml_df['prediction_correct'].mean()
    total_profit = ml_df['profit'].sum()
    total_bet = len(ml_df) * 100
    roi = (total_profit / total_bet) * 100
    
    print(f"\nStrategy 1: Bet Every Game")
    print(f"  Bets: {len(ml_df)}")
    print(f"  Win rate: {win_rate:.1%}")
    print(f"  Total profit: ${total_profit:,.0f}")
    print(f"  ROI: {roi:.2f}%")
    print(f"  Avg profit per bet: ${ml_df['profit'].mean():.2f}")
    
    # By confidence level
    print(f"\nStrategy 2: Bet by Confidence")
    ml_df['confidence'] = ml_df['p_win_A'].apply(lambda x: max(x, 1-x))
    
    for conf_thresh in [0.60, 0.65, 0.70, 0.75]:
        high_conf = ml_df[ml_df['confidence'] > conf_thresh]
        if len(high_conf) > 0:
            win_rate = high_conf['prediction_correct'].mean()
            total_profit = high_conf['profit'].sum()
            total_bet = len(high_conf) * 100
            roi = (total_profit / total_bet) * 100
            
            print(f"  Confidence > {conf_thresh:.0%}: {len(high_conf):3d} bets, "
                  f"{win_rate:.1%} win rate, {roi:+.2f}% ROI, "
                  f"${high_conf['profit'].mean():+.2f} avg profit")
    
    # Performance by season
    print("\nPerformance by Season:")
    for season in sorted(ml_df['season'].unique()):
        season_df = ml_df[ml_df['season'] == season]
        win_rate = season_df['prediction_correct'].mean()
        total_profit = season_df['profit'].sum()
        total_bet = len(season_df) * 100
        roi = (total_profit / total_bet) * 100
        
        print(f"  {season}: {win_rate:.1%} win rate, {roi:+.2f}% ROI, "
              f"${season_df['profit'].mean():+.2f} avg, n={len(season_df)}")


def simulate_totals_betting(df):
    """Analyze betting performance on over/under totals."""
    print("\n" + "="*70)
    print("OVER/UNDER BETTING PERFORMANCE")
    print("="*70)
    
    # Filter to games with totals
    totals_df = df[df['bet_total'].notna()].copy()
    print(f"\nGames with O/U lines: {len(totals_df)}")
    
    if len(totals_df) == 0:
        print("No totals data available")
        return
    
    # Calculate edge on totals
    totals_df['total_edge'] = totals_df['pred_total'] - totals_df['bet_total']
    
    # Determine bet: Over if pred > line, Under if pred < line
    totals_df['bet_over'] = (totals_df['total_edge'] > 0).astype(int)
    
    # Actual result
    totals_df['actual_over'] = (totals_df['true_total'] > totals_df['bet_total']).astype(int)
    
    # Did bet win?
    totals_df['bet_won'] = (totals_df['bet_over'] == totals_df['actual_over']).astype(int)
    
    # Push (total exactly equals line) - these are refunded
    totals_df['push'] = (totals_df['true_total'] == totals_df['bet_total']).astype(int)
    totals_df.loc[totals_df['push'] == 1, 'bet_won'] = np.nan  # Pushes don't count
    
    # Remove pushes for analysis
    totals_no_push = totals_df[totals_df['push'] == 0].copy()
    
    # Strategy 1: Bet every game
    win_rate = totals_no_push['bet_won'].mean()
    roi = ((win_rate * 210 - 110) / 110) * 100
    
    print(f"\nStrategy 1: Bet Every Game")
    print(f"  Bets: {len(totals_no_push)} (excluded {totals_df['push'].sum()} pushes)")
    print(f"  Win rate: {win_rate:.1%}")
    print(f"  ROI: {roi:.2f}%")
    
    # Strategy 2: Bet by edge size
    print(f"\nStrategy 2: Bet by Edge Size")
    for threshold in [2, 3, 5, 7, 10]:
        filtered = totals_no_push[totals_no_push['total_edge'].abs() > threshold]
        if len(filtered) > 0:
            win_rate = filtered['bet_won'].mean()
            roi = ((win_rate * 210 - 110) / 110) * 100
            avg_edge = filtered['total_edge'].abs().mean()
            
            print(f"  Edge > {threshold} pts: {len(filtered):3d} bets, "
                  f"{win_rate:.1%} win rate, {roi:+.2f}% ROI, "
                  f"{avg_edge:.1f} avg edge")
    
    # Strategy 3: Over vs Under performance
    print(f"\nStrategy 3: Over vs Under")
    over_bets = totals_no_push[totals_no_push['bet_over'] == 1]
    under_bets = totals_no_push[totals_no_push['bet_over'] == 0]
    
    if len(over_bets) > 0:
        over_win_rate = over_bets['bet_won'].mean()
        over_roi = ((over_win_rate * 210 - 110) / 110) * 100
        print(f"  Over bets: {len(over_bets):3d} bets, {over_win_rate:.1%} win rate, {over_roi:+.2f}% ROI")
    
    if len(under_bets) > 0:
        under_win_rate = under_bets['bet_won'].mean()
        under_roi = ((under_win_rate * 210 - 110) / 110) * 100
        print(f"  Under bets: {len(under_bets):3d} bets, {under_win_rate:.1%} win rate, {under_roi:+.2f}% ROI")
    
    # Performance by season
    print("\nPerformance by Season:")
    for season in sorted(totals_no_push['season'].unique()):
        season_df = totals_no_push[totals_no_push['season'] == season]
        win_rate = season_df['bet_won'].mean()
        roi = ((win_rate * 210 - 110) / 110) * 100
        avg_edge = season_df['total_edge'].abs().mean()
        
        print(f"  {season}: {win_rate:.1%} win rate, {roi:+.2f}% ROI, "
              f"{avg_edge:.1f} avg edge, n={len(season_df)}")


def analyze_prediction_patterns(df):
    """Identify which types of games the model predicts well vs poorly."""
    print("\n" + "="*70)
    print("PREDICTION PATTERN ANALYSIS")
    print("="*70)
    
    df = df.copy()
    
    # Add some categorical variables for analysis
    df['favorite_size'] = pd.cut(df['bet_spread'].abs(), 
                                  bins=[0, 3, 7, 12, 100],
                                  labels=['Pick\'em (<3)', 'Small fav (3-7)', 
                                         'Medium fav (7-12)', 'Large fav (>12)'])
    
    df['expected_total'] = pd.cut(df['bet_total'],
                                   bins=[0, 130, 145, 160, 300],
                                   labels=['Low (<130)', 'Medium (130-145)',
                                          'High (145-160)', 'Very High (>160)'])
    
    # Conference game flag
    df['conf_game'] = df.get('is_conf_game', 0)
    
    # Home/away
    if 'is_home' in df.columns:
        df['venue'] = df['is_home'].map({1: 'Home', 0: 'Away/Neutral'})
    
    # Team quality (based on Torvik)
    if 'team_barthag' in df.columns:
        df['team_quality'] = pd.cut(df['team_barthag'],
                                     bins=[0, 0.5, 0.7, 0.85, 1.0],
                                     labels=['Weak (<.500)', 'Average (.500-.700)',
                                            'Good (.700-.850)', 'Elite (>.850)'])
    
    # Matchup quality difference
    if 'team_barthag' in df.columns and 'opp_barthag' in df.columns:
        df['matchup_gap'] = (df['team_barthag'] - df['opp_barthag']).abs()
        df['matchup_type'] = pd.cut(df['matchup_gap'],
                                     bins=[0, 0.1, 0.3, 1.0],
                                     labels=['Even matchup', 'Slight mismatch', 'Big mismatch'])
    
    # Month of season
    if 'Date' in df.columns:
        df['month'] = pd.to_datetime(df['Date']).dt.month
        df['season_phase'] = df['month'].map({
            11: 'Early', 12: 'Early', 1: 'Mid', 2: 'Mid', 3: 'Late', 4: 'Tournament'
        })
    
    # Analysis categories
    categories = [
        ('favorite_size', 'Favorite Size'),
        ('expected_total', 'Expected Scoring'),
        ('venue', 'Venue'),
        ('season_phase', 'Season Phase'),
    ]
    
    if 'team_quality' in df.columns:
        categories.append(('team_quality', 'Team Quality'))
    if 'matchup_type' in df.columns:
        categories.append(('matchup_type', 'Matchup Type'))
    if 'conf_game' in df.columns:
        categories.append(('conf_game', 'Conference Game'))
    
    # Analyze each category
    for col, label in categories:
        if col not in df.columns:
            continue
            
        print(f"\n{label}:")
        print(f"{'Category':<20} {'Count':>7} {'MAE':>7} {'Acc':>7} {'ATS%':>7}")
        print("-" * 70)
        
        for category in sorted(df[col].dropna().unique()):
            subset = df[df[col] == category]
            
            if len(subset) < 10:
                continue
            
            mae = subset['err_margin'].mean()
            acc = subset['correct_winner'].mean() if 'correct_winner' in subset.columns else 0
            
            # ATS performance
            if 'bet_spread' in subset.columns:
                bet_subset = subset[subset['bet_spread'].notna()].copy()
                if len(bet_subset) > 0:
                    bet_subset['spread_edge'] = bet_subset['pred_margin'] + bet_subset['bet_spread']
                    bet_subset['bet_on_team_A'] = (bet_subset['spread_edge'] > 0).astype(int)
                    bet_subset['team_A_covered'] = (bet_subset['true_margin'] + bet_subset['bet_spread'] > 0).astype(int)
                    bet_subset['bet_won'] = (bet_subset['bet_on_team_A'] == bet_subset['team_A_covered']).astype(int)
                    ats_pct = bet_subset['bet_won'].mean()
                else:
                    ats_pct = 0
            else:
                ats_pct = 0
            
            print(f"{str(category):<20} {len(subset):>7} {mae:>7.2f} {acc:>6.1%} {ats_pct:>6.1%}")


def find_best_worst_scenarios(df):
    """Find specific scenarios where model excels or struggles."""
    print("\n" + "="*70)
    print("BEST & WORST PREDICTION SCENARIOS")
    print("="*70)
    
    scenarios = []
    
    # Define scenarios to test
    test_scenarios = [
        # Spread-based
        ("bet_spread", lambda x: x < -10, "Heavy favorites"),
        ("bet_spread", lambda x: (x >= -3) & (x <= 3), "Pick'em games"),
        ("bet_spread", lambda x: x > 10, "Heavy underdogs"),
        
        # Totals-based
        ("bet_total", lambda x: x < 135, "Low-scoring games"),
        ("bet_total", lambda x: x > 155, "High-scoring games"),
        
        # Venue
        ("is_home", lambda x: x == 1, "Home games"),
        ("is_home", lambda x: x == 0, "Away/neutral games"),
        
        # Conference
        ("is_conf_game", lambda x: x == 1, "Conference games"),
        ("is_conf_game", lambda x: x == 0, "Non-conference games"),
    ]
    
    # Torvik-based if available
    if 'team_barthag' in df.columns:
        test_scenarios.extend([
            ("team_barthag", lambda x: x > 0.85, "Elite teams"),
            ("team_barthag", lambda x: x < 0.50, "Weak teams"),
        ])
    
    # Month-based
    if 'Date' in df.columns:
        df['month'] = pd.to_datetime(df['Date']).dt.month
        test_scenarios.extend([
            ("month", lambda x: x == 11, "November games"),
            ("month", lambda x: x == 3, "March games"),
        ])
    
    for col, condition, label in test_scenarios:
        if col not in df.columns:
            continue
        
        try:
            subset = df[condition(df[col])].copy()
        except:
            continue
        
        if len(subset) < 50:  # Need enough samples
            continue
        
        # Calculate metrics
        mae = subset['err_margin'].mean()
        acc = subset['correct_winner'].mean() if 'correct_winner' in subset.columns else 0
        
        # ATS
        bet_subset = subset[subset['bet_spread'].notna()].copy()
        if len(bet_subset) > 0:
            bet_subset['spread_edge'] = bet_subset['pred_margin'] + bet_subset['bet_spread']
            bet_subset['bet_on_team_A'] = (bet_subset['spread_edge'] > 0).astype(int)
            bet_subset['team_A_covered'] = (bet_subset['true_margin'] + bet_subset['bet_spread'] > 0).astype(int)
            bet_subset['bet_won'] = (bet_subset['bet_on_team_A'] == bet_subset['team_A_covered']).astype(int)
            ats_pct = bet_subset['bet_won'].mean()
        else:
            ats_pct = 0
        
        scenarios.append({
            'scenario': label,
            'count': len(subset),
            'mae': mae,
            'accuracy': acc,
            'ats_pct': ats_pct
        })
    
    # Sort by ATS performance
    scenarios_df = pd.DataFrame(scenarios)
    
    print("\nBest ATS Performance (Top 10):")
    print(f"{'Scenario':<25} {'Count':>7} {'MAE':>7} {'Acc':>7} {'ATS%':>7}")
    print("-" * 70)
    best = scenarios_df.nlargest(10, 'ats_pct')
    for _, row in best.iterrows():
        print(f"{row['scenario']:<25} {row['count']:>7.0f} {row['mae']:>7.2f} "
              f"{row['accuracy']:>6.1%} {row['ats_pct']:>6.1%}")
    
    print("\nWorst ATS Performance (Bottom 10):")
    print(f"{'Scenario':<25} {'Count':>7} {'MAE':>7} {'Acc':>7} {'ATS%':>7}")
    print("-" * 70)
    worst = scenarios_df.nsmallest(10, 'ats_pct')
    for _, row in worst.iterrows():
        print(f"{row['scenario']:<25} {row['count']:>7.0f} {row['mae']:>7.2f} "
              f"{row['accuracy']:>6.1%} {row['ats_pct']:>6.1%}")



def main():
    df = load_predictions_with_context()
    
    print(f"\nTotal predictions: {len(df)}")
    print(f"Seasons: {sorted(df['season'].unique())}")
    
    analyze_prediction_errors(df)
    analyze_calibration(df)
    simulate_betting_performance(df)
    simulate_moneyline_betting(df)
    simulate_totals_betting(df)
    analyze_prediction_patterns(df)
    find_best_worst_scenarios(df)
    find_worst_predictions(df, n=20)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()