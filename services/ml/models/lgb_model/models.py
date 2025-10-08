# models.py
"""Model training functions."""
import numpy as np
import lightgbm as lgb
import pandas as pd
from config import LGBM_PARAMS
import joblib, os, json
from config import TRAIN_CONFIG

def train_lgbm_model(X_train, y_pts_train, X_test, X_val=None, y_pts_val=None, run_dir=None):
    """
    Train LightGBM multi-output regressor for both team scores.
    
    Args:
        X_train: Training features
        y_pts_train: Training targets (pts_A, pts_B)
        X_test: Test features
        X_val: Optional validation features
        y_pts_val: Optional validation targets
        
    Returns:
        dict with predictions and uncertainty estimates
    """
    
    # Train separate model for each team
    models = []
    preds_test = np.zeros((len(X_test), 2))
    preds_train = np.zeros((len(X_train), 2))
    
    for i, team in enumerate(['A', 'B']):
        print(f"\nTraining model for team {team}...")
        
        model = lgb.LGBMRegressor(**LGBM_PARAMS)
        
        fit_kwargs = {}
        if X_val is not None and len(X_val) > 0:
            fit_kwargs = {
                "eval_set": [(X_val, y_pts_val.iloc[:, i])],
                "callbacks": [
                    lgb.early_stopping(100, verbose=False),
                    lgb.log_evaluation(50)
                ],
            }
        
        model.fit(X_train, y_pts_train.iloc[:, i], **fit_kwargs)

        

      

        
        
        preds_test[:, i] = model.predict(X_test)
        preds_train[:, i] = model.predict(X_train)
        models.append(model)

    models_dir = os.path.join(run_dir, "models")
    os.makedirs(models_dir, exist_ok=True)

    joblib.dump(models[0], os.path.join(models_dir,"model_A.pkl"))
    joblib.dump(models[1], os.path.join(models_dir,"model_B.pkl"))


    models[0].booster_.save_model(os.path.join(models_dir, "model_A.txt"))
    models[1].booster_.save_model(os.path.join(models_dir,"model_B.txt"))


    
    with open(os.path.join(models_dir,"feature_names.json"), "w") as f:
        json.dump(list(X_train.columns), f)
    
    # Estimate uncertainty from training residuals
    resid_A = y_pts_train.iloc[:, 0].values - preds_train[:, 0]
    resid_B = y_pts_train.iloc[:, 1].values - preds_train[:, 1]
    
    sigma_A = np.std(resid_A)
    sigma_B = np.std(resid_B)
    
    # Estimate correlation between residuals
    rho = np.corrcoef(resid_A, resid_B)[0, 1]
    rho = np.clip(rho, -0.9, 0.9)  # Bound it
    
    print(f"\nResidual statistics:")
    print(f"  σ_A = {sigma_A:.2f}, σ_B = {sigma_B:.2f}")
    print(f"  ρ = {rho:.3f}")
    
    # Compute variance for margin and total
    var_margin = sigma_A**2 + sigma_B**2 - 2*rho*sigma_A*sigma_B
    var_total = sigma_A**2 + sigma_B**2 + 2*rho*sigma_A*sigma_B
    
    # Extract feature importance
    importance_A = pd.DataFrame({
        'feature': X_train.columns,
        'importance_A': models[0].feature_importances_,
        'gain_A': models[0].booster_.feature_importance(importance_type='gain')
    })

    importance_B = pd.DataFrame({
        'feature': X_train.columns,
        'importance_B': models[1].feature_importances_,
        'gain_B': models[1].booster_.feature_importance(importance_type='gain')
    })

    # Combine and average
    importance = importance_A.merge(importance_B, on='feature')
    importance['avg_importance'] = (importance['importance_A'] + importance['importance_B']) / 2
    importance['avg_gain'] = (importance['gain_A'] + importance['gain_B']) / 2
    importance = importance.sort_values('avg_importance', ascending=False)

    return {
        "pts_A": preds_test[:, 0],
        "pts_B": preds_test[:, 1],
        "mu_margin": preds_test[:, 0] - preds_test[:, 1],
        "mu_total": preds_test[:, 0] + preds_test[:, 1],
        "sigma_margin": np.full(len(X_test), np.sqrt(max(var_margin, 1e-6))),
        "sigma_total": np.full(len(X_test), np.sqrt(max(var_total, 1e-6))),
        "models": models,
        "feature_importance": importance,  # <-- This line is critical
    }


def temporal_split(meta, X, y_pts, y_win, market, val_ratio=0.2):
    """
    Split data chronologically: earlier games for training, later for validation.
    
    Args:
        meta: Metadata with dates
        val_ratio: Fraction of training data to use for validation
        
    Returns:
        Training and validation splits
    """
    sorted_idx = meta.sort_values("date").index.values
    split_point = int(len(sorted_idx) * (1 - val_ratio))
    
    train_idx = sorted_idx[:split_point]
    val_idx = sorted_idx[split_point:]
    
    return {
        "train": {
            "X": X.loc[train_idx],
            "y_pts": y_pts.loc[train_idx],
            "y_win": y_win.loc[train_idx],
            "meta": meta.loc[train_idx],
            "market": market.loc[train_idx] if len(market) > 0 else None,
        },
        "val": {
            "X": X.loc[val_idx],
            "y_pts": y_pts.loc[val_idx],
            "y_win": y_win.loc[val_idx],
            "meta": meta.loc[val_idx],
            "market": market.loc[val_idx] if len(market) > 0 else None,
        }
    }