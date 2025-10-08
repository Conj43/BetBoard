# predict_with_saved_models.py
"""Load trained models and make predictions on new games."""
import os
import json
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
from scipy import stats
from datetime import datetime, date, timedelta
from data_loader import load_game_data, prepare_game_rows
from features import build_features
from config import TRAIN_CONFIG


def get_latest_model_dir(base_dir=None):
    """
    Find the most recently created xgb_all_models directory.
    
    Args:
        base_dir: Base directory to search (default: TRAIN_CONFIG["xgb_output"])
    
    Returns:
        Path to the models subdirectory of the latest run
    """
    if base_dir is None:
        base_dir = TRAIN_CONFIG["xgb_output"]
    
    # Find all xgb_all_models directories
    all_runs = [
        d for d in os.listdir(base_dir) 
        if d.startswith("xgb_all_models_") and os.path.isdir(os.path.join(base_dir, d))
    ]
    
    if not all_runs:
        raise FileNotFoundError(f"No xgb_all_models_* directories found in {base_dir}")
    
    # Sort by timestamp (embedded in directory name)
    latest_run = sorted(all_runs)[-1]
    model_dir = os.path.join(base_dir, latest_run, "models")
    
    if not os.path.exists(model_dir):
        raise FileNotFoundError(f"Models directory not found in {latest_run}")
    
    print(f"Found latest model: {latest_run}")
    return model_dir


def load_games_for_date(target_date=None, years=None):
    """
    Load games for a specific date from cleaned data.
    
    Args:
        target_date: Date string 'YYYY-MM-DD' or datetime object. 
                    If None, uses today's date.
        years: List of years to load data from. If None, loads from config.
    
    Returns:
        X: Features
        meta: Metadata (team names, dates, etc.)
        market: Betting lines
    """
    # Handle date
    if target_date is None:
        target_date = datetime.now().date()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    elif isinstance(target_date, datetime):
        target_date = target_date.date()
    
    print(f"\nLoading games for {target_date.strftime('%Y-%m-%d')}...")
    
    # Load data from cleaned per_game CSVs
    if years is None:
        years = TRAIN_CONFIG["years"]
    
    raw_data = load_game_data(years=years)
    game_data = prepare_game_rows(raw_data)
    
    # Build features for ALL data (needed for rolling averages, etc.)
    X_all, y_pts_all, y_win_all, meta_all, market_all, _ = build_features(
        game_data,
        include_betting_lines=False
    )
    
    # Filter to target date
    meta_all['date'] = pd.to_datetime(meta_all['date']).dt.date
    date_mask = meta_all['date'] == target_date
    
    if date_mask.sum() == 0:
        print(f"⚠️  No games found for {target_date}")
        return None, None, None
    
    # Extract games for target date
    X = X_all.loc[date_mask]
    meta = meta_all.loc[date_mask]
    market = market_all.loc[date_mask] if len(market_all.columns) > 0 else pd.DataFrame(index=X.index)
    
    print(f"Found {len(X)} games on {target_date}")
    
    return X, meta, market


class GamePredictor:
    """Wrapper class for making predictions with saved models."""
    
    def __init__(self, model_dir=None):
        """
        Load trained models from directory.
        
        Args:
            model_dir: Path to directory containing saved models.
                      If None, automatically uses the most recent model.
                      (e.g., "data/xgb_model/xgb_all_models_20241007_123456/models")
        """
        if model_dir is None:
            model_dir = get_latest_model_dir()
        
        self.model_dir = model_dir
        
        # Load models
        print(f"Loading models from {model_dir}...")
        self.moneyline_model = xgb.XGBClassifier()
        self.moneyline_model.load_model(os.path.join(model_dir, "moneyline_model.json"))
        
        self.spread_model = xgb.XGBRegressor()
        self.spread_model.load_model(os.path.join(model_dir, "spread_model.json"))
        
        self.total_model = xgb.XGBRegressor()
        self.total_model.load_model(os.path.join(model_dir, "total_model.json"))
        
        # Load feature names
        self.feature_names = joblib.load(os.path.join(model_dir, "feature_names.pkl"))
        
        # Load metadata
        with open(os.path.join(model_dir, "model_metadata.json"), "r") as f:
            self.metadata = json.load(f)
        
        print(f"✓ Loaded models trained on {self.metadata['training_date']}")
        print(f"✓ {len(self.feature_names)} features")
        print(f"✓ Training seasons: {self.metadata['training_seasons']}")
        
        # Store historical MAE for confidence calculations
        self.spread_mae = self.metadata['metrics']['spread']['mae_margin']
        self.total_mae = self.metadata['metrics']['total']['mae_total']
    
    def validate_features(self, X):
        """Ensure input data has correct features in correct order."""
        missing = set(self.feature_names) - set(X.columns)
        if missing:
            raise ValueError(f"Missing features: {missing}")
        
        extra = set(X.columns) - set(self.feature_names)
        if extra:
            print(f"Warning: Extra columns will be ignored: {extra}")
        
        # Return features in correct order
        return X[self.feature_names]
    
    def predict_game(self, X_game):
        """
        Predict outcome for a single game or batch of games.
        
        Args:
            X_game: DataFrame with features for one or more games
        
        Returns:
            DataFrame with predictions
        """
        # Validate features
        X = self.validate_features(X_game)
        
        # Make predictions
        pred_proba = self.moneyline_model.predict_proba(X)[:, 1]
        pred_winner = (pred_proba >= 0.5).astype(int)
        pred_margin = self.spread_model.predict(X)
        pred_total = self.total_model.predict(X)
        
        # Build results dataframe
        results = pd.DataFrame(index=X.index)
        
        # Moneyline predictions
        results['pred_winner'] = pred_winner
        results['p_win_A'] = pred_proba
        
        # Spread predictions
        results['pred_margin'] = pred_margin
        
        # Total predictions
        results['pred_total'] = pred_total
        
        return results
    
    def predict_with_market(self, X_game, market_data):
        """
        Make predictions and calculate edges vs market lines.
        
        Args:
            X_game: DataFrame with features
            market_data: DataFrame with columns: bet_spread, bet_total, moneyline_a, moneyline_b
        
        Returns:
            DataFrame with predictions, edges, and picks
        """
        # Get base predictions
        results = self.predict_game(X_game)
        
        # Add market data
        for col in ['bet_spread', 'bet_total', 'moneyline_a', 'moneyline_b']:
            if col in market_data.columns:
                results[col] = market_data[col].values
        
        # Calculate spreads
        if 'bet_spread' in results.columns:
            results['spread_edge'] = results['pred_margin'] + results['bet_spread']
            results['prob_cover'] = stats.norm.cdf(results['spread_edge'] / self.spread_mae)
            results['spread_pick'] = np.where(
                results['spread_edge'] > 0, 
                'Team A', 
                'Team B'
            )
        
        # Calculate totals
        if 'bet_total' in results.columns:
            results['total_edge'] = results['pred_total'] - results['bet_total']
            results['prob_over'] = stats.norm.cdf(results['total_edge'] / self.total_mae)
            results['total_pick'] = np.where(
                results['total_edge'] > 0,
                'OVER',
                'UNDER'
            )
        
        # Calculate moneyline edges
        if 'moneyline_a' in results.columns and 'moneyline_b' in results.columns:
            # Convert American odds to probability
            def american_to_prob(odds):
                return np.where(odds > 0, 100 / (odds + 100), -odds / (-odds + 100))
            
            market_prob_a = american_to_prob(results['moneyline_a'].values)
            market_prob_b = american_to_prob(results['moneyline_b'].values)
            total_prob = market_prob_a + market_prob_b
            results['market_prob_a'] = market_prob_a / total_prob
            results['ml_edge'] = results['p_win_A'] - results['market_prob_a']
        
        return results
    
    def get_best_bets(self, predictions, min_edge=0.03):
        """
        Filter predictions to find best betting opportunities.
        
        Args:
            predictions: Output from predict_with_market()
            min_edge: Minimum edge required (default 3%)
        
        Returns:
            Dictionary with best bets for each market
        """
        best_bets = {}
        
        # Moneyline bets
        if 'ml_edge' in predictions.columns:
            ml_bets = predictions[predictions['ml_edge'] > min_edge].copy()
            ml_bets = ml_bets.sort_values('ml_edge', ascending=False)
            best_bets['moneyline'] = ml_bets
        
        # Spread bets (require meaningful edge > 3 points)
        if 'spread_edge' in predictions.columns:
            spread_bets = predictions[np.abs(predictions['spread_edge']) > 3].copy()
            spread_bets = spread_bets.sort_values('prob_cover', ascending=False)
            best_bets['spread'] = spread_bets
        
        # Total bets (require meaningful edge > 4 points)
        if 'total_edge' in predictions.columns:
            total_bets = predictions[np.abs(predictions['total_edge']) > 4].copy()
            total_bets = total_bets.sort_values('prob_over', ascending=False)
            best_bets['totals'] = total_bets
        
        return best_bets


def predict_today(model_dir=None, min_edge=0.03, save=True):
    """
    Quick function to predict today's games.
    
    Args:
        model_dir: Path to model directory. If None, uses latest.
        min_edge: Minimum edge for filtering best bets
        save: Whether to save predictions to CSV
    
    Returns:
        results: DataFrame with all predictions
        best_bets: Dictionary with filtered best betting opportunities
    """
    print("="*70)
    print(f"PREDICTING FOR TODAY ({datetime.now().strftime('%Y-%m-%d')})")
    print("="*70)
    
    results, best_bets = predict_for_date(
        target_date=None,  # Uses today
        model_dir=model_dir,
        min_edge=min_edge
    )
    
    if results is not None:
        print_best_bets(best_bets, results)
        
        if save:
            today = datetime.now().strftime('%Y-%m-%d')
            output_path = f"predictions_{today}.csv"
            results.to_csv(output_path, index=False)
            print(f"\n💾 Saved predictions to: {output_path}")
    
    return results, best_bets


def predict_this_week(model_dir=None, min_edge=0.03, days_ahead=7, save=True):
    """
    Quick function to predict games for the next week.
    
    Args:
        model_dir: Path to model directory. If None, uses latest.
        min_edge: Minimum edge for filtering best bets
        min_confidence: Minimum confidence tier
        days_ahead: Number of days to predict (default 7)
        save: Whether to save predictions to CSV
    
    Returns:
        all_results: DataFrame with all predictions for the week
        all_best_bets: Dictionary with all best bets organized by market
    """
    print("="*70)
    print(f"PREDICTING FOR NEXT {days_ahead} DAYS")
    print("="*70)
    
    # Load model once
    predictor = GamePredictor(model_dir)
    
    start_date = datetime.now().date()
    all_predictions = []
    all_best_bets = {'moneyline': [], 'spread': [], 'totals': []}
    
    for i in range(days_ahead):
        target_date = start_date + timedelta(days=i)
        date_str = target_date.strftime('%Y-%m-%d')
        
        print(f"\n{target_date.strftime('%A, %B %d, %Y')}:")
        
        # Load games for this date
        X, meta, market = load_games_for_date(date_str)
        
        if X is None:
            print("  (No games scheduled)")
            continue
        
        # Make predictions
        predictions = predictor.predict_with_market(X, market)
        results = pd.concat([meta, predictions], axis=1)
        
        # Find best bets
        best_bets = predictor.get_best_bets(results, min_edge=min_edge)
        
        # Store results
        all_predictions.append(results)
        
        # Print summary for this day
        print(f"  ✓ {len(results)} games")
        for market_type in ['moneyline', 'spread', 'totals']:
            if market_type in best_bets and len(best_bets[market_type]) > 0:
                all_best_bets[market_type].append(best_bets[market_type])
                print(f"  • {len(best_bets[market_type])} {market_type} opportunities")
    
    if not all_predictions:
        print("\n❌ No games found in the next week")
        return None, None
    
    # Combine all results
    all_results = pd.concat(all_predictions, ignore_index=True)
    
    if save:
        # Save weekly predictions
        weekly_file = "predictions_weekly.csv"
        all_results.to_csv(weekly_file, index=False)
        print(f"\n💾 Saved {len(all_results)} predictions to: {weekly_file}")
        
        # Save best bets by market
        for market_type in ['moneyline', 'spread', 'totals']:
            if all_best_bets[market_type]:
                market_bets = pd.concat(all_best_bets[market_type], ignore_index=True)
                market_file = f"best_bets_{market_type}.csv"
                market_bets.to_csv(market_file, index=False)
                print(f"💾 Saved {len(market_bets)} {market_type} opportunities to: {market_file}")
    
    # Print weekly summary
    print("\n" + "="*70)
    print("WEEKLY SUMMARY")
    print("="*70)
    print(f"Date Range: {start_date} to {start_date + timedelta(days=days_ahead-1)}")
    print(f"Total Games: {len(all_results)}")
    
    for market_type in ['moneyline', 'spread', 'totals']:
        if all_best_bets[market_type]:
            total = sum(len(df) for df in all_best_bets[market_type])
            print(f"{market_type.capitalize()} Opportunities: {total}")
    
    # Show top picks
    print("\n🔥 TOP PICKS THIS WEEK")
    print("="*70)
    
    if all_best_bets['moneyline']:
        all_ml = pd.concat(all_best_bets['moneyline'], ignore_index=True)
        all_ml = all_ml.sort_values('ml_edge', ascending=False).head(5)
        
        print("\nMoneyline:")
        for idx, row in all_ml.iterrows():
            winner = row['team_A'] if row['pred_winner'] == 1 else row['team_B']
            date_display = pd.to_datetime(row['date']).strftime('%m/%d')
            print(f"  {date_display}: {row['team_A']} vs {row['team_B']}")
            print(f"    Pick: {winner} ({row['p_win_A']:.1%}), Edge: {row['ml_edge']:+.1%}")
    
    if all_best_bets['spread']:
        all_spread = pd.concat(all_best_bets['spread'], ignore_index=True)
        all_spread = all_spread.sort_values('prob_cover', ascending=False).head(5)
        
        print("\nSpread:")
        for idx, row in all_spread.iterrows():
            date_display = pd.to_datetime(row['date']).strftime('%m/%d')
            print(f"  {date_display}: {row['team_A']} vs {row['team_B']}")
            print(f"    Pick: {row['spread_pick']}, Cover prob: {row['prob_cover']:.1%}")
    
    print("\n" + "="*70)
    
    return all_results, all_best_bets


def predict_for_date(target_date=None, model_dir=None, min_edge=0.03):
    """
    Make predictions for all games on a specific date.
    
    Args:
        target_date: Date string 'YYYY-MM-DD' or datetime object. If None, uses today.
        model_dir: Path to model directory. If None, uses latest model.
        min_edge: Minimum edge for filtering best bets
    
    Returns:
        results: DataFrame with all predictions
        best_bets: Dictionary with filtered best betting opportunities
    """
    # Load games for date
    X, meta, market = load_games_for_date(target_date)
    
    if X is None:
        return None, None
    
    # Load model
    predictor = GamePredictor(model_dir)
    
    # Make predictions
    print("\nMaking predictions...")
    predictions = predictor.predict_with_market(X, market)
    
    # Combine with metadata
    results = pd.concat([meta, predictions], axis=1)
    
    # Find best bets
    best_bets = predictor.get_best_bets(results, min_edge=min_edge)
    
    return results, best_bets


def print_best_bets(best_bets, results):
    """Pretty print best betting opportunities."""
    if not best_bets:
        print("\n❌ No games found or no betting opportunities")
        return
    
    print("\n" + "="*70)
    print("BEST BETTING OPPORTUNITIES")
    print("="*70)
    
    if 'moneyline' in best_bets and len(best_bets['moneyline']) > 0:
        print(f"\n💰 MONEYLINE ({len(best_bets['moneyline'])} games):")
        for idx, row in best_bets['moneyline'].head(10).iterrows():
            winner = row['team_A'] if row['pred_winner'] == 1 else row['team_B']
            print(f"\n  {row['team_A']} vs {row['team_B']}")
            print(f"    ✓ Pick: {winner} ({row['p_win_A']:.1%} win prob)")
            print(f"    ✓ Edge: {row['ml_edge']:+.1%}")
            if 'moneyline_a' in row and pd.notna(row['moneyline_a']):
                ml_pick = row['moneyline_a'] if row['pred_winner'] == 1 else row['moneyline_b']
                print(f"    ✓ Odds: {ml_pick:+.0f}")
    
    if 'spread' in best_bets and len(best_bets['spread']) > 0:
        print(f"\n📊 SPREAD ({len(best_bets['spread'])} games):")
        for idx, row in best_bets['spread'].head(10).iterrows():
            print(f"\n  {row['team_A']} vs {row['team_B']}")
            print(f"    ✓ Pick: {row['spread_pick']} ({row['prob_cover']:.1%} cover prob)")
            print(f"    ✓ Line: {row['bet_spread']:+.1f}, Edge: {row['spread_edge']:+.1f}")
            print(f"    ✓ Prediction: {row['team_A']} by {row['pred_margin']:+.1f}")
    
    if 'totals' in best_bets and len(best_bets['totals']) > 0:
        print(f"\n🎯 TOTALS ({len(best_bets['totals'])} games):")
        for idx, row in best_bets['totals'].head(10).iterrows():
            print(f"\n  {row['team_A']} vs {row['team_B']}")
            print(f"    ✓ Pick: {row['total_pick']} ({row['prob_over']:.1%} prob)")
            print(f"    ✓ Line: {row['bet_total']:.1f}, Projection: {row['pred_total']:.1f}")
            print(f"    ✓ Edge: {row['total_edge']:+.1f} points")
    
    print("\n" + "="*70)


def example_usage():
    """Example: Make predictions for today's games."""
    
    # ============================================
    # OPTION 1: Predict TODAY (simplest)
    # ============================================
    results, best_bets = predict_today()
    
    # ============================================
    # OPTION 2: Predict THIS WEEK
    # ============================================
    # Uncomment to predict for next 7 days:
    # all_results, all_best_bets = predict_this_week()
    
    # ============================================
    # OPTION 3: Predict SPECIFIC DATE
    # ============================================
    # Uncomment to predict for a specific date:
    # results, best_bets = predict_for_date("2025-01-15")
    
    return results, best_bets


if __name__ == "__main__":
    # By default, predict for today
    results, best_bets = predict_today()
    
    # Uncomment to predict for this week instead:
    # all_results, all_best_bets = predict_this_week()