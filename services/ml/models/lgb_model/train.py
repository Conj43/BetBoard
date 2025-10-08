# train.py
"""Main training script."""
import os
from datetime import datetime
import pandas as pd
import json
from config import TRAIN_CONFIG, LGBM_PARAMS
from data_loader import load_game_data, prepare_game_rows
from features import build_features
from models import train_lgbm_model
from evaluation import evaluate_predictions, create_prediction_df


def create_validation_split(X, y_pts, meta, market, val_ratio=0.2):
    """
    Split data chronologically: earlier games for training, later for validation.
    
    Returns: (train_data, val_data) where each is a dict with X, y_pts, meta, market
    """
    sorted_idx = meta.sort_values("date").index.values
    split_point = int(len(sorted_idx) * (1 - val_ratio))
    
    train_idx = sorted_idx[:split_point]
    val_idx = sorted_idx[split_point:]
    
    train_data = {
        "X": X.loc[train_idx],
        "y_pts": y_pts.loc[train_idx],
        "meta": meta.loc[train_idx],
        "market": market.loc[train_idx] if len(market.columns) > 0 else pd.DataFrame(),
    }
    
    val_data = {
        "X": X.loc[val_idx],
        "y_pts": y_pts.loc[val_idx],
        "meta": meta.loc[val_idx],
        "market": market.loc[val_idx] if len(market.columns) > 0 else pd.DataFrame(),
    }
    
    return train_data, val_data


def train_seasonal(X, y_pts, meta, market, run_dir):
    """
    Train separate model for each season using all prior seasons as training data.
    """
    # Ensure market is always a DataFrame (not None)
    if market is None or len(market) == 0:
        market = pd.DataFrame(index=X.index)
    
    seasons = sorted(meta["season"].unique())
    all_results = []
    all_predictions = []
    all_importance = []
    
    print(f"\nFound {len(seasons)} seasons: {seasons}")
    
    for test_season in seasons:
        print(f"\n{'='*70}")
        print(f"Season {test_season}")
        print(f"{'='*70}")
        
        # Split: train on all prior seasons, test on current season
        train_mask = meta["season"] < test_season
        test_mask = meta["season"] == test_season
        
        n_train = train_mask.sum()
        n_test = test_mask.sum()
        
        if n_train == 0:
            print(f"Skipping {test_season}: no prior seasons for training")
            continue
        
        if n_test == 0:
            print(f"Skipping {test_season}: no games in test season")
            continue
        
        print(f"Training games: {n_train}")
        print(f"Test games: {n_test}")
        
        # Extract train and test sets
        X_train_full = X.loc[train_mask]
        y_train_full = y_pts.loc[train_mask]
        meta_train_full = meta.loc[train_mask]
        market_train_full = market.loc[train_mask] if len(market.columns) > 0 else pd.DataFrame()
        
        X_test = X.loc[test_mask]
        y_test = y_pts.loc[test_mask]
        meta_test = meta.loc[test_mask]
        market_test = market.loc[test_mask] if len(market.columns) > 0 else pd.DataFrame()
        
        # Create validation split from training data (chronological)
        train_data, val_data = create_validation_split(
            X_train_full,
            y_train_full,
            meta_train_full,
            market_train_full,
            val_ratio=TRAIN_CONFIG["validation_split"]
        )
        
        print(f"  Train set: {len(train_data['X'])} games")
        print(f"  Val set: {len(val_data['X'])} games")
        
        # Train model with validation
        preds = train_lgbm_model(
            train_data['X'],
            train_data['y_pts'],
            X_test,
            X_val=val_data['X'] if len(val_data['X']) >= 10 else None,
            y_pts_val=val_data['y_pts'] if len(val_data['X']) >= 10 else None,
            run_dir=run_dir
        )
        
        # Save feature importance if available
        if "feature_importance" in preds:
            importance = preds["feature_importance"].copy()
            importance["season"] = test_season
            all_importance.append(importance)
            
            importance_path = os.path.join(run_dir, f"feature_importance_{test_season}.csv")
            preds["feature_importance"].to_csv(importance_path, index=False)
            
            print(f"\nTop 10 Features:")
            top_features = preds["feature_importance"].head(10)
            for idx, row in top_features.iterrows():
                print(f"  {row['feature']}: {row['avg_importance']:.1f}")
        
        # Evaluate on test set
        metrics = evaluate_predictions(y_test, preds, meta_test, market_test)
        metrics["season"] = test_season
        metrics["n_train"] = n_train
        metrics["n_test"] = n_test
        all_results.append(metrics)
        
        # Print key metrics
        print(f"\nTest Set Performance:")
        print(f"  MAE Points A: {metrics['mae_pts_A']:.2f}")
        print(f"  MAE Points B: {metrics['mae_pts_B']:.2f}")
        print(f"  MAE Margin: {metrics['mae_margin']:.2f}")
        print(f"  MAE Total: {metrics['mae_total']:.2f}")
        print(f"  Accuracy: {metrics['accuracy']:.1%}")
        print(f"  Brier Score: {metrics['brier_score']:.4f}")
        
        # Create detailed prediction DataFrame
        pred_df = create_prediction_df(meta_test, y_test, preds, market_test)
        pred_df["season"] = test_season
        
        # Save per-season predictions
        pred_path = os.path.join(run_dir, f"predictions_{test_season}.csv")
        pred_df.to_csv(pred_path, index=False)
        print(f"\nSaved predictions: {pred_path}")
        
        all_predictions.append(pred_df)
    
    # Save aggregated results
    if all_results:
        results_df = pd.DataFrame(all_results)
        results_path = os.path.join(run_dir, "metrics_by_season.csv")
        results_df.to_csv(results_path, index=False)
        print(f"\nSaved metrics: {results_path}")
        
        # Print summary statistics
        print(f"\n{'='*70}")
        print("OVERALL SUMMARY")
        print(f"{'='*70}")
        print(f"Average MAE Margin: {results_df['mae_margin'].mean():.2f}")
        print(f"Average MAE Total: {results_df['mae_total'].mean():.2f}")
        print(f"Average Accuracy: {results_df['accuracy'].mean():.1%}")
        print(f"Average Brier Score: {results_df['brier_score'].mean():.4f}")
    
    if all_predictions:
        combined = pd.concat(all_predictions, ignore_index=True)
        combined_path = os.path.join(run_dir, "predictions_all_seasons.csv")
        combined.to_csv(combined_path, index=False)
        print(f"\nSaved combined predictions: {combined_path}")
    
    if all_importance:
        combined_importance = pd.concat(all_importance, ignore_index=True)
        importance_path = os.path.join(run_dir, "feature_importance_all.csv")
        combined_importance.to_csv(importance_path, index=False)
        print(f"\nSaved combined feature importance: {importance_path}")
        
        # Calculate average importance across all seasons
        avg_importance = combined_importance.groupby('feature')[['avg_importance', 'avg_gain']].mean()
        avg_importance = avg_importance.sort_values('avg_importance', ascending=False)
        
        print(f"\n{'='*70}")
        print("TOP 20 FEATURES (averaged across all seasons)")
        print(f"{'='*70}")
        print(f"{'Feature':<40} {'Importance':>12} {'Gain':>12}")
        print("-" * 70)
        for feature, row in avg_importance.head(20).iterrows():
            print(f"{feature:<40} {row['avg_importance']:>12.1f} {row['avg_gain']:>12.1f}")



def train_cutoff(X, y_pts, meta, market, run_dir, cutoff_season=2025):
    """
    Train on all seasons before cutoff, test on cutoff season and after.
    
    Args:
        cutoff_season: Test on this season and later (train on all prior)
    """
    # Ensure market is always a DataFrame
    if market is None or len(market) == 0:
        market = pd.DataFrame(index=X.index)
    
    print(f"\n{'='*70}")
    print(f"CUTOFF TRAINING MODE")
    print(f"Training: seasons < {cutoff_season}")
    print(f"Testing: seasons >= {cutoff_season}")
    print(f"{'='*70}")
    
    # Split based on cutoff
    train_mask = meta["season"] < cutoff_season
    test_mask = meta["season"] >= cutoff_season
    
    n_train = train_mask.sum()
    n_test = test_mask.sum()
    
    if n_train == 0:
        raise ValueError("No training data before cutoff season")
    if n_test == 0:
        raise ValueError("No test data at/after cutoff season")
    
    print(f"\nTraining games: {n_train}")
    print(f"Test games: {n_test}")
    print(f"Train seasons: {sorted(meta[train_mask]['season'].unique())}")
    print(f"Test seasons: {sorted(meta[test_mask]['season'].unique())}")
    
    # Extract train and test sets
    X_train_full = X.loc[train_mask]
    y_train_full = y_pts.loc[train_mask]
    meta_train_full = meta.loc[train_mask]
    market_train_full = market.loc[train_mask] if len(market.columns) > 0 else pd.DataFrame()
    
    X_test = X.loc[test_mask]
    y_test = y_pts.loc[test_mask]
    meta_test = meta.loc[test_mask]
    market_test = market.loc[test_mask] if len(market.columns) > 0 else pd.DataFrame()
    
    # Create validation split from training data (chronological)
    train_data, val_data = create_validation_split(
        X_train_full,
        y_train_full,
        meta_train_full,
        market_train_full,
        val_ratio=TRAIN_CONFIG["validation_split"]
    )
    
    print(f"\nSplit details:")
    print(f"  Train set: {len(train_data['X'])} games")
    print(f"  Val set: {len(val_data['X'])} games")
    print(f"  Test set: {len(X_test)} games")
    
    # Train model with validation
    print(f"\n{'='*70}")
    print("TRAINING MODEL")
    print(f"{'='*70}")
    
    preds = train_lgbm_model(
        train_data['X'],
        train_data['y_pts'],
        X_test,
        X_val=val_data['X'] if len(val_data['X']) >= 10 else None,
        y_pts_val=val_data['y_pts'] if len(val_data['X']) >= 10 else None,
        run_dir=run_dir
    )
    
    # Save feature importance
    if "feature_importance" in preds:
        importance_path = os.path.join(run_dir, "feature_importance.csv")
        preds["feature_importance"].to_csv(importance_path, index=False)
        
        print(f"\n{'='*70}")
        print("TOP 20 FEATURES")
        print(f"{'='*70}")
        print(f"{'Feature':<40} {'Importance':>12} {'Gain':>12}")
        print("-" * 70)
        top_features = preds["feature_importance"].head(20)
        for idx, row in top_features.iterrows():
            print(f"{row['feature']:<40} {row['avg_importance']:>12.1f} {row['avg_gain']:>12.1f}")
    
    # Evaluate on test set
    print(f"\n{'='*70}")
    print("TEST SET PERFORMANCE")
    print(f"{'='*70}")
    
    metrics = evaluate_predictions(y_test, preds, meta_test, market_test)
    
    print(f"\nPrediction Accuracy:")
    print(f"  MAE Points A: {metrics['mae_pts_A']:.2f}")
    print(f"  MAE Points B: {metrics['mae_pts_B']:.2f}")
    print(f"  MAE Margin: {metrics['mae_margin']:.2f}")
    print(f"  MAE Total: {metrics['mae_total']:.2f}")
    print(f"  Win Accuracy: {metrics['accuracy']:.1%}")
    print(f"  Brier Score: {metrics['brier_score']:.4f}")
    
    if 'avg_cover_prob' in metrics:
        print(f"\nBetting Metrics:")
        print(f"  Avg Cover Probability: {metrics['avg_cover_prob']:.1%}")
    if 'avg_over_prob' in metrics:
        print(f"  Avg Over Probability: {metrics['avg_over_prob']:.1%}")
    
    # Save metrics
    metrics_df = pd.DataFrame([metrics])
    metrics_path = os.path.join(run_dir, "test_metrics.csv")
    metrics_df.to_csv(metrics_path, index=False)
    print(f"\nSaved metrics: {metrics_path}")
    
    # Create and save detailed predictions
    pred_df = create_prediction_df(meta_test, y_test, preds, market_test)
    pred_path = os.path.join(run_dir, "predictions_test.csv")
    pred_df.to_csv(pred_path, index=False)
    print(f"Saved predictions: {pred_path}")
    
    # Break down by season
    print(f"\n{'='*70}")
    print("PERFORMANCE BY TEST SEASON")
    print(f"{'='*70}")
    
    for season in sorted(pred_df['season'].unique()):
        season_df = pred_df[pred_df['season'] == season]
        
        # Recalculate metrics for this season
        mae_margin = (season_df['true_margin'] - season_df['pred_margin']).abs().mean()
        accuracy = (season_df['true_winner'] == season_df['pred_winner']).mean()
        
        print(f"\nSeason {season}:")
        print(f"  Games: {len(season_df)}")
        print(f"  MAE Margin: {mae_margin:.2f}")
        print(f"  Accuracy: {accuracy:.1%}")
        
        # Betting performance if available
        if 'bet_spread' in season_df.columns:
            bet_games = season_df[season_df['bet_spread'].notna()].copy()
            if len(bet_games) > 0:
                bet_games['spread_edge'] = bet_games['pred_margin'] + bet_games['bet_spread']
                bet_games['bet_on_team_A'] = (bet_games['spread_edge'] > 0).astype(int)
                bet_games['team_A_covered'] = (bet_games['true_margin'] + bet_games['bet_spread'] > 0).astype(int)
                bet_games['bet_won'] = (bet_games['bet_on_team_A'] == bet_games['team_A_covered']).astype(int)
                
                win_rate = bet_games['bet_won'].mean()
                roi = ((win_rate * 210 - 110) / 110) * 100
                avg_edge = bet_games['spread_edge'].abs().mean()
                
                print(f"  ATS Win Rate: {win_rate:.1%} ({len(bet_games)} games)")
                print(f"  ROI: {roi:+.2f}%")
                print(f"  Avg Edge: {avg_edge:.1f} points")


def main():
    """Main training pipeline."""
    
    # Create run directory
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(TRAIN_CONFIG["output_dir"], f"run_{run_id}")
    os.makedirs(run_dir, exist_ok=True)
    
    print(f"{'='*70}")
    print(f"CBB Model Training")
    print(f"Run ID: {run_id}")
    print(f"Output: {run_dir}")
    print(f"Data directory: {TRAIN_CONFIG['data_dir']}")
    print(f"{'='*70}")
    
    # Save configuration
    config_path = os.path.join(run_dir, "config.json")
    with open(config_path, "w") as f:
        config_dict = {
            "train_config": TRAIN_CONFIG,
            "lgbm_params": LGBM_PARAMS,
            "run_id": run_id,
        }
        json.dump(config_dict, f, indent=2, default=str)
    print(f"Saved config: {config_path}\n")
    
    # Load data
    print("Loading data...")
    raw_data = load_game_data(years=TRAIN_CONFIG["years"])
    
    # Prepare game rows (parse scores, create identifiers)
    print("\nPreparing game data...")
    game_data = prepare_game_rows(raw_data)
    
    # Build features with leakage checks
    print("\nBuilding features...")
    X, y_pts, y_win, meta, market, feature_names = build_features(
        game_data, 
        include_betting_lines=False
    )
    
    # Save feature list
    features_path = os.path.join(run_dir, "features.txt")
    with open(features_path, "w") as f:
        f.write("\n".join(feature_names))
    print(f"\nSaved {len(feature_names)} features to {features_path}")
    
    # Train model
    if TRAIN_CONFIG["mode"] == "seasonal":
        train_seasonal(X, y_pts, meta, market, run_dir)
    elif TRAIN_CONFIG["mode"] == "cutoff":
        cutoff_season = 2025  # You can make this configurable
        train_cutoff(X, y_pts, meta, market, run_dir, cutoff_season=cutoff_season)
    else:
        raise NotImplementedError("Only 'seasonal' training mode is currently implemented")
    
    print(f"\n{'='*70}")
    print("Training Complete!")
    print(f"All outputs saved to: {run_dir}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()