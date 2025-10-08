#!/usr/bin/env python3
"""
Weekly Predictions Script - Generate predictions for the next 7 days.

Usage:
    python weekly_predictions.py
"""

import pandas as pd
from datetime import datetime, timedelta
from make_preds import predict_for_date, GamePredictor

# Configuration
DAYS_AHEAD = 7
MIN_EDGE = 0.03
MIN_CONFIDENCE = 'Medium'


def main():
    print("="*70)
    print(f"GENERATING PREDICTIONS FOR NEXT {DAYS_AHEAD} DAYS")
    print("="*70)
    
    start_date = datetime.now().date()
    all_predictions = []
    all_best_bets = {'moneyline': [], 'spread': [], 'totals': []}
    
    # Load model once (reuse for all dates)
    predictor = GamePredictor()
    
    for i in range(DAYS_AHEAD):
        target_date = start_date + timedelta(days=i)
        date_str = target_date.strftime('%Y-%m-%d')
        
        print(f"\n{'='*70}")
        print(f"Date: {date_str} ({target_date.strftime('%A')})")
        print(f"{'='*70}")
        
        # Predict for this date
        results, best_bets = predict_for_date(
            target_date=date_str,
            min_edge=MIN_EDGE,
            min_confidence=MIN_CONFIDENCE
        )
        
        if results is not None:
            print(f"✓ Found {len(results)} games")
            all_predictions.append(results)
            
            # Collect best bets
            for market in ['moneyline', 'spread', 'totals']:
                if market in best_bets and len(best_bets[market]) > 0:
                    all_best_bets[market].append(best_bets[market])
                    print(f"  • {len(best_bets[market])} {market} opportunities")
        else:
            print("  (No games scheduled)")
    
    # Combine all predictions
    if all_predictions:
        print(f"\n{'='*70}")
        print("SAVING RESULTS")
        print(f"{'='*70}")
        
        # Save all predictions
        weekly_predictions = pd.concat(all_predictions, ignore_index=True)
        weekly_file = "predictions_weekly.csv"
        weekly_predictions.to_csv(weekly_file, index=False)
        print(f"✓ Saved {len(weekly_predictions)} total predictions to: {weekly_file}")
        
        # Save best bets by market
        for market in ['moneyline', 'spread', 'totals']:
            if all_best_bets[market]:
                market_bets = pd.concat(all_best_bets[market], ignore_index=True)
                market_file = f"best_bets_{market}.csv"
                market_bets.to_csv(market_file, index=False)
                print(f"✓ Saved {len(market_bets)} {market} opportunities to: {market_file}")
        
        # Print summary
        print(f"\n{'='*70}")
        print("WEEKLY SUMMARY")
        print(f"{'='*70}")
        print(f"Date Range: {start_date} to {start_date + timedelta(days=DAYS_AHEAD-1)}")
        print(f"Total Games: {len(weekly_predictions)}")
        print(f"Days with Games: {len(all_predictions)}")
        
        for market in ['moneyline', 'spread', 'totals']:
            if all_best_bets[market]:
                total = sum(len(df) for df in all_best_bets[market])
                print(f"{market.capitalize()} Opportunities: {total}")
        
        print(f"{'='*70}")
        
        # Show top opportunities
        print("\n🔥 TOP 5 OPPORTUNITIES THIS WEEK")
        print(f"{'='*70}")
        
        if all_best_bets['moneyline']:
            all_ml = pd.concat(all_best_bets['moneyline'], ignore_index=True)
            all_ml = all_ml.sort_values('ml_edge', ascending=False).head(5)
            
            print("\nMoneyline:")
            for idx, row in all_ml.iterrows():
                winner = row['team_A'] if row['pred_winner'] == 1 else row['team_B']
                print(f"  {row['date'].strftime('%m/%d')}: {row['team_A']} vs {row['team_B']}")
                print(f"    Pick: {winner} ({row['p_win_A']:.1%}), Edge: {row['ml_edge']:+.1%}")
        
        if all_best_bets['spread']:
            all_spread = pd.concat(all_best_bets['spread'], ignore_index=True)
            all_spread = all_spread.sort_values('prob_cover', ascending=False).head(5)
            
            print("\nSpread:")
            for idx, row in all_spread.iterrows():
                print(f"  {row['date'].strftime('%m/%d')}: {row['team_A']} vs {row['team_B']}")
                print(f"    Pick: {row['spread_pick']}, Cover prob: {row['prob_cover']:.1%}")
        
        print(f"\n{'='*70}")
    else:
        print("\n❌ No games found in the next week")


if __name__ == "__main__":
    main()