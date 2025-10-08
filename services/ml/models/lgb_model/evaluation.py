# evaluation.py
"""Evaluation metrics and utilities."""
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, brier_score_loss, log_loss, accuracy_score
import math


def evaluate_predictions(y_pts_true, preds, meta=None, market=None):
    """
    Compute evaluation metrics.
    
    Args:
        y_pts_true: True scores (pts_A, pts_B) as DataFrame
        preds: Prediction dict from model with keys: pts_A, pts_B, mu_margin, mu_total, sigma_margin, sigma_total
        meta: Optional metadata
        market: Optional betting lines (DataFrame with bet_spread, bet_total columns)
        
    Returns:
        dict of metrics
    """
    
    true_A = y_pts_true["pts_A"].values
    true_B = y_pts_true["pts_B"].values
    
    metrics = {
        "mae_pts_A": mean_absolute_error(true_A, preds["pts_A"]),
        "mae_pts_B": mean_absolute_error(true_B, preds["pts_B"]),
        "mae_total": mean_absolute_error(true_A + true_B, preds["mu_total"]),
        "mae_margin": mean_absolute_error(true_A - true_B, preds["mu_margin"]),
    }
    
    # Win probability metrics
    p_win_A = compute_win_probs(preds["mu_margin"], preds["sigma_margin"])
    true_win = (true_A > true_B).astype(int)
    
    metrics["brier_score"] = brier_score_loss(true_win, p_win_A)
    metrics["log_loss"] = log_loss(true_win, np.clip(p_win_A, 1e-6, 1-1e-6))
    
    # Accuracy
    pred_win = (preds["mu_margin"] > 0).astype(int)
    metrics["accuracy"] = accuracy_score(true_win, pred_win)
    
    # Betting market metrics if available
    if market is not None and len(market.columns) > 0:
        if "bet_spread" in market.columns:
            spread_coverage = compute_spread_coverage(
                preds["mu_margin"], 
                preds["sigma_margin"],
                market["bet_spread"].values
            )
            metrics["avg_cover_prob"] = float(np.nanmean(spread_coverage))
        
        if "bet_total" in market.columns:
            over_probs = compute_over_probs(
                preds["mu_total"],
                preds["sigma_total"],
                market["bet_total"].values
            )
            metrics["avg_over_prob"] = float(np.nanmean(over_probs))
    
    return metrics


def compute_win_probs(mu_margin, sigma_margin):
    """Compute win probability from Normal distribution of margin."""
    probs = []
    for mu, sigma in zip(mu_margin, sigma_margin):
        if sigma <= 1e-6:
            probs.append(1.0 if mu > 0 else 0.0)
        else:
            z = -mu / sigma  # standardize
            prob = 0.5 * (1 + math.erf(z / math.sqrt(2)))
            probs.append(1 - prob)  # P(margin > 0)
    return np.array(probs)


def compute_spread_coverage(mu_margin, sigma_margin, spreads):
    """Compute probability of covering spread."""
    probs = []
    for mu, sigma, spread in zip(mu_margin, sigma_margin, spreads):
        if np.isnan(spread):
            probs.append(np.nan)
            continue
        
        if sigma <= 1e-6:
            probs.append(1.0 if mu > -spread else 0.0)
        else:
            z = (-spread - mu) / sigma
            prob = 0.5 * (1 - math.erf(z / math.sqrt(2)))
            probs.append(prob)
    return np.array(probs)


def compute_over_probs(mu_total, sigma_total, totals):
    """Compute probability of going over the total."""
    probs = []
    for mu, sigma, total in zip(mu_total, sigma_total, totals):
        if np.isnan(total):
            probs.append(np.nan)
            continue
        
        if sigma <= 1e-6:
            probs.append(1.0 if mu > total else 0.0)
        else:
            z = (total - mu) / sigma
            prob = 0.5 * (1 - math.erf(z / math.sqrt(2)))
            probs.append(prob)
    return np.array(probs)


def create_prediction_df(meta, y_pts_true, preds, market=None):
    """Create detailed prediction dataframe for analysis."""
    
    df = meta.copy()
    
    # True values
    df["true_pts_A"] = y_pts_true["pts_A"].values
    df["true_pts_B"] = y_pts_true["pts_B"].values
    df["true_margin"] = df["true_pts_A"] - df["true_pts_B"]
    df["true_total"] = df["true_pts_A"] + df["true_pts_B"]
    df["true_winner"] = (df["true_margin"] > 0).astype(int)
    
    # Predictions
    df["pred_pts_A"] = preds["pts_A"]
    df["pred_pts_B"] = preds["pts_B"]
    df["pred_margin"] = preds["mu_margin"]
    df["pred_total"] = preds["mu_total"]
    df["pred_winner"] = (preds["mu_margin"] > 0).astype(int)
    df["sigma_margin"] = preds["sigma_margin"]
    df["sigma_total"] = preds["sigma_total"]
    
    # Win probability
    df["p_win_A"] = compute_win_probs(preds["mu_margin"], preds["sigma_margin"])
    
    # Errors
    df["err_pts_A"] = np.abs(df["true_pts_A"] - df["pred_pts_A"])
    df["err_pts_B"] = np.abs(df["true_pts_B"] - df["pred_pts_B"])
    df["err_margin"] = np.abs(df["true_margin"] - df["pred_margin"])
    df["err_total"] = np.abs(df["true_total"] - df["pred_total"])
    df["correct_winner"] = (df["true_winner"] == df["pred_winner"]).astype(int)
    
    # Add betting lines if available
    if market is not None and len(market.columns) > 0:
        for col in market.columns:
            if col in market.columns:
                df[col] = market[col].values
    
    return df