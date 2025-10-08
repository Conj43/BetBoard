#!/usr/bin/env python3
"""
Daily Predictions Script - Run this every morning for today's betting picks.

Usage:
    python daily_predictions.py              # Predict for today
"""

import sys
from datetime import datetime
from make_preds import predict_for_date, print_best_bets

# Configuration - Adjust these to your preferences
MIN_EDGE = 0.03           # Minimum 3% edge
MIN_CONFIDENCE = 'Medium' # Low, Medium, or High
SAVE_PREDICTIONS = True   # Save to CSV
TODAY = False


def main():
    # Get target date from command line or use today
    if not TODAY:
        target_date = "2022-12-05"
        print(f"🗓️  Predicting for: {target_date}")
    else:
        target_date = None  # Uses today
        print(f"🗓️  Predicting for: TODAY ({datetime.now().strftime('%Y-%m-%d')})")
    
    print("="*70)
    
    # Make predictions
    results, best_bets = predict_for_date(
        target_date=target_date,
        min_edge=MIN_EDGE
    )
    
    if results is None:
        print("\n❌ No games found for this date")
        return
    
    # Display best opportunities
    print_best_bets(best_bets, results)
    
    # Save to file
    if SAVE_PREDICTIONS:
        if target_date is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        else:
            date_str = target_date
        
        output_file = f"data/predictions/predictions_{date_str}.csv"
        results.to_csv(output_file, index=False)
        print(f"\n💾 Saved {len(results)} predictions to: {output_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total Games: {len(results)}")
    
    if 'moneyline' in best_bets:
        print(f"Moneyline Opportunities: {len(best_bets['moneyline'])}")
    if 'spread' in best_bets:
        print(f"Spread Opportunities: {len(best_bets['spread'])}")
    if 'totals' in best_bets:
        print(f"Total Opportunities: {len(best_bets['totals'])}")
    
    print("="*70)


if __name__ == "__main__":
    main()