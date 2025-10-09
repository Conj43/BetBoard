# train_all_xgb_models.py
"""Unified XGBoost training for moneyline, spread, and totals models."""
import os
from datetime import datetime
import pandas as pd
import numpy as np
import json
import xgboost as xgb
from scipy import stats
from sklearn.metrics import (
    accuracy_score, log_loss, roc_auc_score, brier_score_loss,
    mean_absolute_error, mean_squared_error
)
from config import TRAIN_CONFIG
from data_loader import load_game_data, prepare_game_rows
from features import build_features


# Model parameters
XGB_MONEYLINE_PARAMS = {
    "n_estimators": 2000,
    "learning_rate": 0.02,
    "max_depth": 4,
    "min_child_weight": 6,
    "subsample": 0.8,
    "colsample_bytree": 0.7,
    "gamma": 0.4,
    "reg_alpha": 0.4,
    "reg_lambda": 8.0,
    "random_state": 42,
    "n_jobs": -1,
    "eval_metric": "logloss",
}

XGB_SPREAD_PARAMS = {
    "n_estimators": 1000,
    "learning_rate": 0.03,
    "max_depth": 6,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "gamma": 0.1,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "n_jobs": -1,
    "objective": "reg:squarederror",
    "eval_metric": "mae",
}

XGB_TOTAL_PARAMS = {
    "n_estimators": 1000,
    "learning_rate": 0.03,
    "max_depth": 5,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "gamma": 0.1,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "n_jobs": -1,
    "objective": "reg:squarederror",
    "eval_metric": "mae",
}


def create_validation_split(X, y_win, y_margin, y_total, meta, market, val_ratio=0.2):
    """Split data chronologically for validation."""
    sorted_idx = meta.sort_values("date").index.values
    split_point = int(len(sorted_idx) * (1 - val_ratio))
    
    train_idx = sorted_idx[:split_point]
    val_idx = sorted_idx[split_point:]
    
    train_data = {
        "X": X.loc[train_idx],
        "y_win": y_win.loc[train_idx],
        "y_margin": y_margin.loc[train_idx],
        "y_total": y_total.loc[train_idx],
        "meta": meta.loc[train_idx],
        "market": market.loc[train_idx] if len(market.columns) > 0 else pd.DataFrame(),
    }
    
    val_data = {
        "X": X.loc[val_idx],
        "y_win": y_win.loc[val_idx],
        "y_margin": y_margin.loc[val_idx],
        "y_total": y_total.loc[val_idx],
        "meta": meta.loc[val_idx],
        "market": market.loc[val_idx] if len(market.columns) > 0 else pd.DataFrame(),
    }
    
    return train_data, val_data


# ==================== MONEYLINE MODEL ====================

def train_moneyline_model(X_train, y_train, X_test, X_val=None, y_val=None):
    """Train XGBoost classifier for predicting winners."""
    print(f"\n{'='*70}")
    print("TRAINING MONEYLINE MODEL")
    print(f"{'='*70}")
    print(f"Training samples: {len(X_train)}")
    print(f"Class balance: {y_train.mean():.1%} Team A wins")
    
    params = XGB_MONEYLINE_PARAMS.copy()
    if X_val is not None and len(X_val) > 0:
        params["early_stopping_rounds"] = 50
    
    model = xgb.XGBClassifier(**params)
    
    fit_kwargs = {"verbose": False}
    if X_val is not None and len(X_val) > 0:
        fit_kwargs["eval_set"] = [(X_val, y_val)]
    
    model.fit(X_train, y_train, **fit_kwargs)
    
    # Predictions
    pred_proba = model.predict_proba(X_test)[:, 1]
    pred_class = (pred_proba >= 0.5).astype(int)
    
    # Feature importance
    gain_scores = model.get_booster().get_score(importance_type='gain')
    gain_values = [gain_scores.get(f'f{i}', 0) for i in range(len(X_train.columns))]
    
    importance_df = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importances_,
        'gain': gain_values
    }).sort_values('importance', ascending=False)
    
    return {
        "pred_proba": pred_proba,
        "pred_class": pred_class,
        "model": model,
        "feature_importance": importance_df,
    }


def evaluate_moneyline(y_true, pred_proba, pred_class, market=None):
    """Calculate moneyline metrics."""
    metrics = {
        "accuracy": accuracy_score(y_true, pred_class),
        "log_loss": log_loss(y_true, pred_proba),
        "brier_score": brier_score_loss(y_true, pred_proba),
        "auc_roc": roc_auc_score(y_true, pred_proba),
    }
    
    # Moneyline profit
    if market is not None and "moneyline_a" in market.columns and "moneyline_b" in market.columns:
        valid = (market["moneyline_a"].notna()) & (market["moneyline_b"].notna())
        
        if valid.sum() > 0:
            y_true_valid = y_true[valid].values
            pred_class_valid = pred_class[valid]
            ml_a = market.loc[valid, "moneyline_a"].values
            ml_b = market.loc[valid, "moneyline_b"].values
            
            profits = []
            for actual, pred, odds_a, odds_b in zip(y_true_valid, pred_class_valid, ml_a, ml_b):
                bet_on_a = (pred == 1)
                a_won = (actual == 1)
                
                if bet_on_a:
                    profit = 100 * (odds_a / 100 if odds_a > 0 else -100 / odds_a) if a_won else -100
                else:
                    profit = 100 * (odds_b / 100 if odds_b > 0 else -100 / odds_b) if not a_won else -100
                
                profits.append(profit)
            
            metrics["ml_roi"] = (sum(profits) / (len(profits) * 100)) * 100
            metrics["ml_profit"] = sum(profits)
            metrics["ml_bets"] = len(profits)
    
    return metrics


def calculate_moneyline_confidence(pred_proba, market):
    """
    Calculate confidence metrics for moneyline predictions.
    
    Returns:
        - confidence: Distance from 0.5 (0 = coin flip, 1 = certain)
        - edge: Advantage over market-implied probability
        - kelly_size: Suggested bet size (% of bankroll) using Kelly criterion
        - confidence_tier: Low/Medium/High classification
    """
    results = pd.DataFrame(index=market.index)
    
    # Base confidence (distance from 50/50)
    results['confidence'] = np.abs(pred_proba - 0.5) * 2  # Scale to 0-1
    
    # Calculate edge vs market if moneylines available
    if "moneyline_a" in market.columns and "moneyline_b" in market.columns:
        valid = (market["moneyline_a"].notna()) & (market["moneyline_b"].notna())
        
        # Convert American odds to implied probability
        def american_to_prob(odds):
            return np.where(odds > 0, 100 / (odds + 100), -odds / (-odds + 100))
        
        market_prob_a = american_to_prob(market["moneyline_a"].values)
        market_prob_b = american_to_prob(market["moneyline_b"].values)
        
        # Normalize (remove vig)
        total_prob = market_prob_a + market_prob_b
        market_prob_a_fair = market_prob_a / total_prob
        
        # Calculate edge (our probability - market probability)
        results['market_prob_a'] = market_prob_a_fair
        results['edge'] = pred_proba - market_prob_a_fair
        
        # Kelly criterion: f = (bp - q) / b
        # where f = fraction to bet, b = odds, p = win prob, q = 1-p
        # Simplified: f = edge / odds
        results['kelly_size'] = np.where(
            valid,
            np.clip(results['edge'] / 0.05, 0, 0.25),  # Cap at 25% bankroll, 5% typical odds
            0
        )
    else:
        results['edge'] = np.nan
        results['kelly_size'] = np.nan
    
    # Confidence tiers
    results['confidence_tier'] = pd.cut(
        results['confidence'],
        bins=[0, 0.15, 0.35, 1.0],
        labels=['Low', 'Medium', 'High']
    )
    
    return results


# ==================== SPREAD MODEL ====================

def train_spread_model(X_train, y_train, X_test, X_val=None, y_val=None):
    """Train XGBoost regressor for predicting margin."""
    print(f"\n{'='*70}")
    print("TRAINING SPREAD MODEL")
    print(f"{'='*70}")
    print(f"Training samples: {len(X_train)}")
    print(f"Mean margin: {y_train.mean():.2f}")
    print(f"Std margin: {y_train.std():.2f}")
    
    params = XGB_SPREAD_PARAMS.copy()
    if X_val is not None and len(X_val) > 0:
        params["early_stopping_rounds"] = 50
    
    model = xgb.XGBRegressor(**params)
    
    fit_kwargs = {"verbose": False}
    if X_val is not None and len(X_val) > 0:
        fit_kwargs["eval_set"] = [(X_val, y_val)]
    
    model.fit(X_train, y_train, **fit_kwargs)
    
    # Predictions
    pred_margin = model.predict(X_test)
    
    # Feature importance
    gain_scores = model.get_booster().get_score(importance_type='gain')
    gain_values = [gain_scores.get(f'f{i}', 0) for i in range(len(X_train.columns))]
    
    importance_df = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importances_,
        'gain': gain_values
    }).sort_values('importance', ascending=False)
    
    return {
        "pred_margin": pred_margin,
        "model": model,
        "feature_importance": importance_df,
    }


def evaluate_spread(y_true_margin, pred_margin, market=None):
    """Calculate spread metrics."""
    metrics = {
        "mae_margin": mean_absolute_error(y_true_margin, pred_margin),
        "rmse_margin": np.sqrt(mean_squared_error(y_true_margin, pred_margin)),
    }
    
    # ATS performance
    if market is not None and "bet_spread" in market.columns:
        spread_df = market[market["bet_spread"].notna()].copy()
        
        if len(spread_df) > 0:
            pred_series = pd.Series(pred_margin, index=y_true_margin.index)
            spread_df['pred_margin'] = pred_series
            spread_df['true_margin'] = y_true_margin
            spread_df = spread_df.dropna(subset=['pred_margin', 'true_margin'])
            
            spread_df['spread_edge'] = spread_df['pred_margin'] + spread_df['bet_spread']
            spread_df['bet_on_team_a'] = (spread_df['spread_edge'] > 0).astype(int)
            spread_df['team_a_covered'] = (spread_df['true_margin'] + spread_df['bet_spread'] > 0).astype(int)
            spread_df['bet_won'] = (spread_df['bet_on_team_a'] == spread_df['team_a_covered']).astype(int)
            
            metrics['ats_accuracy'] = spread_df['bet_won'].mean()
            metrics['ats_games'] = len(spread_df)
    
    return metrics


def calculate_spread_confidence(pred_margin, market, historical_mae=7.5):
    """
    Calculate confidence metrics for spread predictions.
    
    Args:
        pred_margin: Predicted margins
        market: Market data with bet_spread
        historical_mae: Historical MAE for calibration (default: 7.5 points)
    
    Returns:
        DataFrame with confidence metrics
    """
    results = pd.DataFrame(index=market.index)
    
    if "bet_spread" in market.columns:
        # Edge vs betting line (how far from market)
        results['spread_edge'] = pred_margin + market['bet_spread'].values
        results['edge_abs'] = np.abs(results['spread_edge'])
        
        # Confidence based on edge magnitude
        # Larger edge = more confident pick (but cap it)
        results['confidence'] = np.clip(results['edge_abs'] / 10, 0, 1)
        
        # Uncertainty estimate (assume normal distribution around prediction)
        # Standard error ≈ historical MAE
        results['std_error'] = historical_mae
        results['pred_lower'] = pred_margin - 1.96 * historical_mae  # 95% CI
        results['pred_upper'] = pred_margin + 1.96 * historical_mae
        
        # Win probability (probability of covering spread)
        # Using normal CDF with our edge and standard error
        results['prob_cover'] = stats.norm.cdf(results['spread_edge'] / historical_mae)
        
        # Confidence tiers based on edge
        results['confidence_tier'] = pd.cut(
            results['edge_abs'],
            bins=[0, 3, 7, 100],
            labels=['Low', 'Medium', 'High']
        )
    else:
        results['confidence'] = np.nan
        results['confidence_tier'] = 'Unknown'
    
    return results


# ==================== TOTAL MODEL ====================

def train_total_model(X_train, y_train, X_test, X_val=None, y_val=None):
    """Train XGBoost regressor for predicting total points."""
    print(f"\n{'='*70}")
    print("TRAINING TOTAL MODEL")
    print(f"{'='*70}")
    print(f"Training samples: {len(X_train)}")
    print(f"Mean total: {y_train.mean():.2f}")
    print(f"Std total: {y_train.std():.2f}")
    
    params = XGB_TOTAL_PARAMS.copy()
    if X_val is not None and len(X_val) > 0:
        params["early_stopping_rounds"] = 50
    
    model = xgb.XGBRegressor(**params)
    
    fit_kwargs = {"verbose": False}
    if X_val is not None and len(X_val) > 0:
        fit_kwargs["eval_set"] = [(X_val, y_val)]
    
    model.fit(X_train, y_train, **fit_kwargs)
    
    # Predictions
    pred_total = model.predict(X_test)
    
    # Feature importance
    gain_scores = model.get_booster().get_score(importance_type='gain')
    gain_values = [gain_scores.get(f'f{i}', 0) for i in range(len(X_train.columns))]
    
    importance_df = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importances_,
        'gain': gain_values
    }).sort_values('importance', ascending=False)
    
    return {
        "pred_total": pred_total,
        "model": model,
        "feature_importance": importance_df,
    }


def evaluate_total(y_true_total, pred_total, market=None):
    """Calculate total metrics."""
    metrics = {
        "mae_total": mean_absolute_error(y_true_total, pred_total),
        "rmse_total": np.sqrt(mean_squared_error(y_true_total, pred_total)),
    }
    
    # O/U performance
    if market is not None and "bet_total" in market.columns:
        total_df = market[market["bet_total"].notna()].copy()
        
        if len(total_df) > 0:
            pred_series = pd.Series(pred_total, index=y_true_total.index)
            total_df['pred_total'] = pred_series
            total_df['true_total'] = y_true_total
            total_df = total_df.dropna(subset=['pred_total', 'true_total'])
            
            total_df['total_edge'] = total_df['pred_total'] - total_df['bet_total']
            total_df['bet_over'] = (total_df['total_edge'] > 0).astype(int)
            total_df['actual_over'] = (total_df['true_total'] > total_df['bet_total']).astype(int)
            total_df['bet_won'] = (total_df['bet_over'] == total_df['actual_over']).astype(int)
            
            metrics['ou_accuracy'] = total_df['bet_won'].mean()
            metrics['ou_games'] = len(total_df)
    
    return metrics


def calculate_total_confidence(pred_total, market, historical_mae=8.0):
    """
    Calculate confidence metrics for total predictions.
    
    Args:
        pred_total: Predicted totals
        market: Market data with bet_total
        historical_mae: Historical MAE for calibration (default: 8.0 points)
    
    Returns:
        DataFrame with confidence metrics
    """
    results = pd.DataFrame(index=market.index)
    
    if "bet_total" in market.columns:
        # Edge vs betting line
        results['total_edge'] = pred_total - market['bet_total'].values
        results['edge_abs'] = np.abs(results['total_edge'])
        
        # Confidence based on edge magnitude
        results['confidence'] = np.clip(results['edge_abs'] / 12, 0, 1)
        
        # Uncertainty estimate
        results['std_error'] = historical_mae
        results['pred_lower'] = pred_total - 1.96 * historical_mae  # 95% CI
        results['pred_upper'] = pred_total + 1.96 * historical_mae
        
        # Win probability (probability of going over)
        results['prob_over'] = stats.norm.cdf(results['total_edge'] / historical_mae)
        
        # Confidence tiers
        results['confidence_tier'] = pd.cut(
            results['edge_abs'],
            bins=[0, 4, 8, 200],
            labels=['Low', 'Medium', 'High']
        )
    else:
        results['confidence'] = np.nan
        results['confidence_tier'] = 'Unknown'
    
    return results


# ==================== UNIFIED TRAINING ====================

def train_on_2025_holdout(X, y_pts, y_win, meta, market, run_dir, feature_names, run_id):
    """Train on all pre-2025 seasons, evaluate on 2025."""
    if market is None or len(market) == 0:
        market = pd.DataFrame(index=X.index)
    
    # Calculate targets
    y_margin = y_pts.iloc[:, 0] - y_pts.iloc[:, 1]  # Team A - Team B
    y_total = y_pts.iloc[:, 0] + y_pts.iloc[:, 1]   # Team A + Team B
    
    # Split into train (pre-2025) and test (2025)
    train_mask = meta["season"] < 2025
    test_mask = meta["season"] == 2025
    
    n_train = train_mask.sum()
    n_test = test_mask.sum()
    
    print(f"\n{'='*70}")
    print("TRAIN/TEST SPLIT")
    print(f"{'='*70}")
    print(f"Training seasons: {sorted(meta.loc[train_mask, 'season'].unique())}")
    print(f"Test season: 2025")
    print(f"Training games: {n_train}")
    print(f"Test games: {n_test}")
    
    if n_train == 0 or n_test == 0:
        raise ValueError("Not enough data for train/test split")
    
    # Extract data
    X_train_full = X.loc[train_mask]
    y_win_train_full = y_win.loc[train_mask]
    y_margin_train_full = y_margin.loc[train_mask]
    y_total_train_full = y_total.loc[train_mask]
    meta_train_full = meta.loc[train_mask]
    market_train_full = market.loc[train_mask] if len(market.columns) > 0 else pd.DataFrame()
    
    X_test = X.loc[test_mask]
    y_win_test = y_win.loc[test_mask]
    y_margin_test = y_margin.loc[test_mask]
    y_total_test = y_total.loc[test_mask]
    meta_test = meta.loc[test_mask]
    market_test = market.loc[test_mask] if len(market.columns) > 0 else pd.DataFrame()
    
    # Create validation split from training data
    train_data, val_data = create_validation_split(
        X_train_full,
        y_win_train_full,
        y_margin_train_full,
        y_total_train_full,
        meta_train_full,
        market_train_full,
        val_ratio=TRAIN_CONFIG["validation_split"]
    )
    
    print(f"\n  Train set: {len(train_data['X'])} games")
    print(f"  Val set: {len(val_data['X'])} games")
    
    # ===== TRAIN ALL THREE MODELS =====
    
    # 1. Moneyline
    ml_results = train_moneyline_model(
        train_data['X'],
        train_data['y_win'],
        X_test,
        X_val=val_data['X'] if len(val_data['X']) >= 10 else None,
        y_val=val_data['y_win'] if len(val_data['X']) >= 10 else None
    )
    
    ml_metrics = evaluate_moneyline(
        y_win_test,
        ml_results["pred_proba"],
        ml_results["pred_class"],
        market_test if len(market_test.columns) > 0 else None
    )
    
    print(f"\nMoneyline Performance:")
    print(f"  Accuracy: {ml_metrics['accuracy']:.1%}")
    print(f"  Log Loss: {ml_metrics['log_loss']:.4f}")
    print(f"  AUC-ROC: {ml_metrics['auc_roc']:.4f}")
    if 'ml_roi' in ml_metrics:
        print(f"  ML ROI: {ml_metrics['ml_roi']:+.2f}%")
        print(f"  ML Profit: ${ml_metrics['ml_profit']:,.0f}")
    
    # 2. Spread
    spread_results = train_spread_model(
        train_data['X'],
        train_data['y_margin'],
        X_test,
        X_val=val_data['X'] if len(val_data['X']) >= 10 else None,
        y_val=val_data['y_margin'] if len(val_data['X']) >= 10 else None
    )
    
    spread_metrics = evaluate_spread(
        y_margin_test,
        spread_results["pred_margin"],
        market_test if len(market_test.columns) > 0 else None
    )
    
    print(f"\nSpread Performance:")
    print(f"  MAE: {spread_metrics['mae_margin']:.2f}")
    print(f"  RMSE: {spread_metrics['rmse_margin']:.2f}")
    if 'ats_accuracy' in spread_metrics:
        print(f"  ATS Accuracy: {spread_metrics['ats_accuracy']:.1%} ({spread_metrics['ats_games']} games)")
    
    # 3. Total
    total_results = train_total_model(
        train_data['X'],
        train_data['y_total'],
        X_test,
        X_val=val_data['X'] if len(val_data['X']) >= 10 else None,
        y_val=val_data['y_total'] if len(val_data['X']) >= 10 else None
    )
    
    total_metrics = evaluate_total(
        y_total_test,
        total_results["pred_total"],
        market_test if len(market_test.columns) > 0 else None
    )
    
    print(f"\nTotal Performance:")
    print(f"  MAE: {total_metrics['mae_total']:.2f}")
    print(f"  RMSE: {total_metrics['rmse_total']:.2f}")
    if 'ou_accuracy' in total_metrics:
        print(f"  O/U Accuracy: {total_metrics['ou_accuracy']:.1%} ({total_metrics['ou_games']} games)")
    
    # ===== SAVE PREDICTIONS =====
    
    # Moneyline predictions
    ml_pred_df = meta_test.copy()
    ml_pred_df["true_winner"] = y_win_test.values
    ml_pred_df["pred_winner"] = ml_results["pred_class"]
    ml_pred_df["p_win_A"] = ml_results["pred_proba"]
    ml_pred_df["correct"] = (y_win_test.values == ml_results["pred_class"]).astype(int)
    
    if "moneyline_a" in market_test.columns:
        ml_pred_df["moneyline_a"] = market_test["moneyline_a"].values
        ml_pred_df["moneyline_b"] = market_test["moneyline_b"].values
    
    ml_path = os.path.join(run_dir, "moneyline_predictions_2025.csv")
    ml_pred_df.to_csv(ml_path, index=False)
    print(f"\nSaved: {ml_path}")
    
    # Spread predictions
    spread_pred_df = meta_test.copy()
    spread_pred_df["true_margin"] = y_margin_test.values
    spread_pred_df["pred_margin"] = spread_results["pred_margin"]
    spread_pred_df["err_margin"] = np.abs(y_margin_test.values - spread_results["pred_margin"])
    
    if "bet_spread" in market_test.columns:
        spread_pred_df["bet_spread"] = market_test["bet_spread"].values
        spread_pred_df['adjusted_margin'] = spread_pred_df['true_margin'] + spread_pred_df['bet_spread']
        spread_pred_df['pred_adjusted_margin'] = spread_pred_df['pred_margin'] + spread_pred_df['bet_spread']
        spread_pred_df['model_pick_a'] = (spread_pred_df['pred_adjusted_margin'] > 0).astype(int)
        spread_pred_df['team_a_covered'] = (spread_pred_df['adjusted_margin'] > 0).astype(int)
        spread_pred_df['ats_correct'] = (spread_pred_df['model_pick_a'] == spread_pred_df['team_a_covered']).astype(int)
    
    spread_path = os.path.join(run_dir, "spread_predictions_2025.csv")
    spread_pred_df.to_csv(spread_path, index=False)
    print(f"Saved: {spread_path}")
    
    # Total predictions
    total_pred_df = meta_test.copy()
    total_pred_df["true_total"] = y_total_test.values
    total_pred_df["pred_total"] = total_results["pred_total"]
    total_pred_df["err_total"] = np.abs(y_total_test.values - total_results["pred_total"])
    
    if "bet_total" in market_test.columns:
        total_pred_df["bet_total"] = market_test["bet_total"].values
        total_pred_df['total_edge'] = total_pred_df['pred_total'] - total_pred_df['bet_total']
        total_pred_df['model_pick_over'] = (total_pred_df['total_edge'] > 0).astype(int)
        total_pred_df['actual_over'] = (total_pred_df['true_total'] > total_pred_df['bet_total']).astype(int)
        total_pred_df['ou_correct'] = (total_pred_df['model_pick_over'] == total_pred_df['actual_over']).astype(int)
    
    total_path = os.path.join(run_dir, "total_predictions_2025.csv")
    total_pred_df.to_csv(total_path, index=False)
    print(f"Saved: {total_path}")
    
    # Save metrics
    metrics_summary = {
        "moneyline": ml_metrics,
        "spread": spread_metrics,
        "total": total_metrics,
    }
    
    metrics_path = os.path.join(run_dir, "metrics_summary.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics_summary, f, indent=2, default=str)
    print(f"Saved: {metrics_path}")
    
    # ===== SAVE MODELS =====
    import joblib
    
    models_dir = os.path.join(run_dir, "models")
    os.makedirs(models_dir, exist_ok=True)
    
    # Save XGBoost models
    ml_results["model"].save_model(os.path.join(models_dir, "moneyline_model.json"))
    spread_results["model"].save_model(os.path.join(models_dir, "spread_model.json"))
    total_results["model"].save_model(os.path.join(models_dir, "total_model.json"))
    
    # Save feature names (critical for inference)
    joblib.dump(feature_names, os.path.join(models_dir, "feature_names.pkl"))
    
    # Save model metadata
    model_metadata = {
        "training_date": run_id,
        "training_seasons": sorted(meta.loc[train_mask, 'season'].unique()),
        "test_season": 2025,
        "n_features": len(feature_names),
        "metrics": metrics_summary,
    }
    
    with open(os.path.join(models_dir, "model_metadata.json"), "w") as f:
        json.dump(model_metadata, f, indent=2, default=str)
    
    print(f"\nSaved models to: {models_dir}")
    print(f"  - moneyline_model.json")
    print(f"  - spread_model.json")
    print(f"  - total_model.json")
    print(f"  - feature_names.pkl")
    print(f"  - model_metadata.json")
    
    # Save feature importance
    for model_name, results in [
        ("moneyline", ml_results),
        ("spread", spread_results),
        ("total", total_results)
    ]:
        imp_df = results["feature_importance"].head(20)
        print(f"\n{'='*70}")
        print(f"TOP 20 {model_name.upper()} FEATURES")
        print(f"{'='*70}")
        for idx, row in imp_df.iterrows():
            print(f"{row.name+1:2d}. {row['feature']:<45} {row['importance']:>10.3f}")


def main():
    """Main training pipeline."""
    
    # Create run directory
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(TRAIN_CONFIG["xgb_output"], f"xgb_all_models_{run_id}")
    os.makedirs(run_dir, exist_ok=True)
    
    print(f"{'='*70}")
    print(f"XGBoost All Models Training")
    print(f"Run ID: {run_id}")
    print(f"Output: {run_dir}")
    print(f"{'='*70}")
    
    # Save configuration
    config_path = os.path.join(run_dir, "config.json")
    with open(config_path, "w") as f:
        config_dict = {
            "train_config": TRAIN_CONFIG,
            "xgb_moneyline_params": XGB_MONEYLINE_PARAMS,
            "xgb_spread_params": XGB_SPREAD_PARAMS,
            "xgb_total_params": XGB_TOTAL_PARAMS,
            "run_id": run_id,
        }
        json.dump(config_dict, f, indent=2, default=str)
    print(f"Saved config: {config_path}\n")
    
    # Load data
    print("Loading data...")
    raw_data = load_game_data(years=TRAIN_CONFIG["years"])
    
    # Prepare game rows
    print("\nPreparing game data...")
    game_data = prepare_game_rows(raw_data)
    
    # Build features
    print("\nBuilding features...")
    X, y_pts, y_win, meta, market, feature_names = build_features(
        game_data,
        include_betting_lines=True
    )
    
    # Save feature list
    features_path = os.path.join(run_dir, "features.txt")
    with open(features_path, "w") as f:
        f.write("\n".join(feature_names))
    print(f"\nSaved {len(feature_names)} features to {features_path}")
    
    # Train all models
    train_on_2025_holdout(X, y_pts, y_win, meta, market, run_dir, feature_names, run_id)
    
    print(f"\n{'='*70}")
    print("Training Complete!")
    print(f"All outputs saved to: {run_dir}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()