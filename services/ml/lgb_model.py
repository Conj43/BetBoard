
import os, math, warnings, re
from datetime import datetime
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, brier_score_loss, log_loss, accuracy_score

warnings.filterwarnings("ignore")

# === Run configuration ===
OUTPUT_DIR = "new_model_runs"   # all outputs will be written here
CUTOFF_DATE = "2024-10-01"      # leakage-safe split: train before this date, test on/after
# Training mode: "seasonal" = rolling seasons (train on past seasons, predict current)
#                "cutoff"   = single temporal cutoff across all years
TRAIN_MODE = "seasonal"







# ----------------------------
# Helpers
# ----------------------------

def read_years(base_dir=".", years=(2019, 2020, 2021, 2022, 2023, 2024, 2025)):
    frames = []
    for y in years:
        p = os.path.join(base_dir, f"data/cleaned_historical/per_game_{y}.csv")
        if os.path.exists(p):
            df = pd.read_csv(p)
            df["season"] = y
            frames.append(df)
    if not frames:
        raise FileNotFoundError("No per_game_YYYY.csv files found in the provided directory.")
    return pd.concat(frames, ignore_index=True)

def parse_scores(df):
    """Populate team_pts and opp_pts from the CLEANED dataset.
    Priority 1: direct numeric columns (e.g., team/opp points).
    Priority 2: best text score column with 'NN-NN' pattern (e.g., 'Score', 'bet_Score', etc.).
    Never swap order: values are taken from the row's team vs opponent perspective.
    """
    # --- Try direct numeric columns first ---
    # Common cleaned variants we might see
    numeric_candidates = [
        ("team_pts", "opp_pts"),                 # already present
        ("TeamPts", "OppPts"),
        ("team_points", "opp_points"),
        ("points_for", "points_against"),
        ("PF", "PA"),                            # points for/against
        ("team_score", "opp_score"),
        ("Score_Team", "Score_Opp"),
    ]

    for a_col, b_col in numeric_candidates:
        if a_col in df.columns and b_col in df.columns:
            a = pd.to_numeric(df[a_col], errors="coerce")
            b = pd.to_numeric(df[b_col], errors="coerce")
            if a.notna().any() and b.notna().any():
                df["team_pts"] = a
                df["opp_pts"]  = b
                print(f"[parse_scores] using numeric columns: {a_col}, {b_col}")
                return df

    # Heuristic search for numeric columns by name
    def find_numeric_col(regexes):
        for c in df.columns:
            lc = str(c).lower()
            if any(re.search(r, lc) for r in regexes):
                if pd.api.types.is_numeric_dtype(df[c]):
                    return c
        return None

    team_num = find_numeric_col([r"^team.*(pts|points)$", r"^(pts|points)_team$", r"^pf$"])
    opp_num  = find_numeric_col([r"^opp.*(pts|points)$",  r"^(pts|points)_opp$",  r"^pa$"])
    if team_num and opp_num:
        df["team_pts"] = pd.to_numeric(df[team_num], errors="coerce")
        df["opp_pts"]  = pd.to_numeric(df[opp_num], errors="coerce")
        print(f"[parse_scores] using detected numeric columns: {team_num}, {opp_num}")
        return df

    # --- Fall back to text score columns with 'NN-NN' ---
    # Prefer cleaned columns first, but auto-detect among any *score* columns
    preferred = ["Score", "Final", "Result", "FinalScore"]
    candidates = []
    for c in preferred + [col for col in df.columns if "score" in str(col).lower() and col not in preferred]:
        if c in df.columns and df[c].notna().any():
            s = df[c].astype(str).str.replace("\u2013", "-", regex=False).str.strip()
            m = s.str.extract(r"(\d+)\s*-\s*(\d+)")
            valid = m[0].notna() & m[1].notna()
            if valid.sum() > 0:
                candidates.append((c, valid.sum(), m))
    if candidates:
        # choose the column with the most parseable rows
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_col, _, best_match = candidates[0]
        df["team_pts"] = pd.to_numeric(best_match[0], errors="coerce")
        df["opp_pts"]  = pd.to_numeric(best_match[1], errors="coerce")
        print(f"[parse_scores] using text score column: {best_col}")
        return df

    # If we get here, we failed to parse
    raise ValueError("Could not locate cleaned score columns. Provide numeric team/opponent point columns or a text 'NN-NN' score column in the cleaned data.")




# --- Row-stable canonicalizer: A = row team, B = row opponent (NO swapping) ---

def prepare_row_as_A(df):
    """Produce an A/B-like schema where A == row team and B == row opponent.
    This avoids lexicographic sorting and any team/opp swapping.
    Requires parse_scores() to have already created team_pts/opp_pts.
    """
    out = df.copy()
    # dates / season
    out["date"] = pd.to_datetime(out["Date"])  # assumes 'Date' exists
    if "season" not in out.columns:
        out["season"] = out["date"].dt.year

    # stable id with row order (not sorted): Team|Opp|date
    team_id = out["Team"].astype(str).str.strip().str.lower()
    opp_id  = out["Opp" ].astype(str).str.strip().str.lower()
    out["game_id"] = team_id + "--vs--" + opp_id + "__" + out["date"].dt.strftime("%Y-%m-%d")

    # row-stable A/B fields
    out["team_A"] = out["Team"]
    out["team_B"] = out["Opp"]
    out["team_A_key"] = team_id
    out["team_B_key"] = opp_id

    # labels straight from row perspective
    out["pts_A"] = out["team_pts"].astype(float)
    out["pts_B"] = out["opp_pts" ].astype(float)
    out["margin_A"] = out["pts_A"] - out["pts_B"]
    out["total_pts"] = out["pts_A"] + out["pts_B"]
    out["home_win_A"] = (out["margin_A"] > 0).astype(int)

    # ensure market columns numeric if present
    for c in ("bet_total","bet_spread","closing_total","closing_spread"):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    return out

def drop_bad_rows(df):
    """Remove games with missing or non-finite labels (pts_A/pts_B). Logs how many were removed."""
    if "pts_A" not in df.columns or "pts_B" not in df.columns:
        raise ValueError("Expected pts_A and pts_B after normalization.")
    mask = df["pts_A"].notna() & df["pts_B"].notna()
    mask &= np.isfinite(df["pts_A"]) & np.isfinite(df["pts_B"])
    before = len(df)
    cleaned = df.loc[mask].copy()
    removed = before - len(cleaned)
    print(f"Filtered rows with missing labels: removed {removed}")
    if len(cleaned) == 0:
        print("[drop_bad_rows] WARNING: no rows remain after filtering. Upstream pivot may have produced zero paired games.")
    return cleaned

def build_features(merged):
    # We include all numeric engineered features from both perspectives except:
    # - any columns starting with "bet_" (leakage)
    # - labels and identifiers
    drop_prefixes = ["A__bet_", "B__bet_", "bet_"]
    drop_exact = set([
        "game_id", "date", "season",
        "team_A", "team_B",
        # labels / label-derived
        "pts_A", "pts_B", "margin_A", "total_pts", "home_win_A", "win", "margin",
        # raw parsed row labels
        "team_pts", "opp_pts",
        # market/outcome fields we NEVER allow
        "bet_ats_margin", "bet_ou_margin", "bet_mov",
        "bet_combined",
        # known leaked engineered totals
        "total"
    ])

    # Defensive filter: skip obvious target-like columns even if they slipped through naming
    forbidden_substrings = ["_score", "_scores", "_margin", "_result", "_winner"]

    allowed_market = {"bet_total", "bet_spread", "bet_moneyline", "bet_moneyline_for_team"} 

    feature_cols = []
    for c in merged.columns:
        if c in drop_exact:
            continue
        if c in allowed_market:
            pass  # explicitly allowed
        else:
            if any(c.startswith(p) for p in drop_prefixes):
                continue
            lc = c.lower()
            if any(fs in lc for fs in forbidden_substrings):
                continue
        # keep numerics only
        if pd.api.types.is_numeric_dtype(merged[c]):
            feature_cols.append(c)

    X = merged[feature_cols].copy()
    # NaN diagnostics
    na_counts = X.isna().sum()
    print(na_counts)
    print(na_counts[na_counts > 0])

    # Drop rows with any NaN in features and align targets/meta/market
    row_ok = ~X.isna().any(axis=1)
    X = X.loc[row_ok].copy()

    y_pts = merged[["pts_A", "pts_B"]].copy().loc[row_ok]
    y_win = merged["home_win_A"].astype(int).loc[row_ok]

    meta_cols = ["game_id","date","team_A","team_B","season"]
    if "team_A_key" in merged.columns and "team_B_key" in merged.columns:
        meta_cols += ["team_A_key","team_B_key"]
    meta = merged[meta_cols].copy().loc[row_ok]
    # Market lines if available
    if {"bet_total","bet_spread"}.issubset(merged.columns):
        market = merged[["bet_total","bet_spread"]].copy().loc[row_ok]
    else:
        market = pd.DataFrame(index=X.index)

    return X, y_pts, y_win, meta, market, feature_cols



def season_split(meta, *arrays, cutoff_date="2024-10-01"):
    # Train before cutoff, test on/after cutoff
    dates = pd.to_datetime(meta["date"])
    train_idx = dates < pd.to_datetime(cutoff_date)
    test_idx  = ~train_idx
    split = []
    for arr in arrays:
        if isinstance(arr, pd.DataFrame) or isinstance(arr, pd.Series):
            split.append((arr.loc[train_idx].copy(), arr.loc[test_idx].copy()))
        else:
            # Fallback for numpy arrays
            split.append((arr[train_idx], arr[test_idx]))
    meta_train = meta.loc[train_idx].copy()
    meta_test  = meta.loc[test_idx].copy()
    return meta_train, meta_test, split

# --- Robust temporal split helper ---
def ensure_temporal_split(meta, X, y_pts, y_win, market, cutoff_date):
    """Ensure non-empty train/test splits. If either side is empty, fall back to an 80/20
    time-based split using the 80th percentile date as cutoff. Returns
    (meta_tr, meta_te, (X_tr, X_te), (y_pts_tr, y_pts_te), (y_win_tr, y_win_te), (market_tr, market_te), cutoff_used)
    """
    meta_tr, meta_te, splits = season_split(meta, X, y_pts, y_win, market, cutoff_date=cutoff_date)
    X_tr, X_te = splits[0]
    y_pts_tr, y_pts_te = splits[1]
    y_win_tr, y_win_te = splits[2]
    market_tr, market_te = splits[3]

    if len(X_tr) == 0 or len(X_te) == 0:
        # Fallback: pick cutoff as 80th percentile of dates
        dates = pd.to_datetime(meta["date"]).sort_values()
        if len(dates) == 0:
            raise ValueError("No dates available after preprocessing; cannot split.")
        cutoff_fallback = dates.quantile(0.8)
        meta_tr, meta_te, splits = season_split(meta, X, y_pts, y_win, market, cutoff_date=cutoff_fallback)
        X_tr, X_te = splits[0]
        y_pts_tr, y_pts_te = splits[1]
        y_win_tr, y_win_te = splits[2]
        market_tr, market_te = splits[3]
        return meta_tr, meta_te, (X_tr, X_te), (y_pts_tr, y_pts_te), (y_win_tr, y_win_te), (market_tr, market_te), pd.to_datetime(cutoff_fallback).strftime("%Y-%m-%d")

    return meta_tr, meta_te, (X_tr, X_te), (y_pts_tr, y_pts_te), (y_win_tr, y_win_te), (market_tr, market_te), cutoff_date

def gaussian_over_prob(mu_total, sigma_total, line_total):
    if sigma_total <= 1e-6:
        return float(mu_total > line_total)
    z = (line_total - mu_total) / sigma_total
    return float(0.5 * (1 - math.erf(z / math.sqrt(2))))

def gaussian_cover_prob(mu_margin, sigma_margin, line_spread):
    if sigma_margin <= 1e-6:
        return float(mu_margin > -line_spread)
    z = (-line_spread - mu_margin) / sigma_margin
    return float(0.5 * (1 - math.erf(z / math.sqrt(2))))

# ----------------------------
# LightGBM baseline
# ----------------------------

def train_lgbm_multioutput(X_train, y_pts_train, X_test, X_val=None, y_pts_val=None):
    if lgb is None:
        raise ImportError("LightGBM not available in this environment.")

    # Sanity: ensure no NaN/inf
    if X_train.isnull().values.any():
        X_train = X_train.fillna(X_train.median(numeric_only=True))
    if X_test.isnull().values.any():
        X_test = X_test.fillna(X_train.median(numeric_only=True))
    if y_pts_train.isnull().values.any():
        raise ValueError("y_pts_train contains NaN after preprocessing.")
    if X_val is not None and X_val.isnull().values.any():
        X_val = X_val.fillna(X_train.median(numeric_only=True))
    if y_pts_val is not None and y_pts_val.isnull().values.any():
        raise ValueError("y_pts_val contains NaN after preprocessing.")

    params = dict(
        n_estimators=2000,
        learning_rate=0.035,
        max_depth=-1,
        num_leaves=63,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_alpha=0.1,
        reg_lambda=0.5,
        random_state=42,
        n_jobs=-1,
        force_col_wise=True,
    )

    preds_test = np.zeros((len(X_test), 2), dtype=float)
    preds_train = np.zeros((len(X_train), 2), dtype=float)

    for t in range(2):
        model = lgb.LGBMRegressor(**params)
        fit_kwargs = {}
        if X_val is not None and y_pts_val is not None and len(X_val) > 0:
            fit_kwargs = {
                "eval_set": [(X_val, y_pts_val.iloc[:, t])],
                "callbacks": [lgb.early_stopping(100, verbose=True), lgb.log_evaluation(50)],
            }
        model.fit(X_train, y_pts_train.iloc[:, t], **fit_kwargs)
        preds_test[:, t]  = model.predict(X_test)
        preds_train[:, t] = model.predict(X_train)

    # Residual stds from train for uncertainty
    resid_A = y_pts_train.iloc[:,0].values - preds_train[:,0]
    resid_B = y_pts_train.iloc[:,1].values - preds_train[:,1]
    sigma_A = np.std(resid_A) + 1e-6
    sigma_B = np.std(resid_B) + 1e-6
    rho = 0.2
    var_margin = sigma_A**2 + sigma_B**2 - 2*rho*sigma_A*sigma_B
    var_total  = sigma_A**2 + sigma_B**2 + 2*rho*sigma_A*sigma_B

    home_pred, away_pred = preds_test[:,0], preds_test[:,1]
    out = {
        "pts_A": home_pred,
        "pts_B": away_pred,
        "mu_margin": home_pred - away_pred,
        "mu_total":  home_pred + away_pred,
        "sigma_margin": np.full_like(home_pred, np.sqrt(max(var_margin, 1e-6))),
        "sigma_total":  np.full_like(home_pred, np.sqrt(max(var_total, 1e-6))),
    }
    return out



# ----------------------------
# Evaluate
# ----------------------------

def evaluate(meta_test, y_pts_test, preds, market=None, label_prefix=""):

    yA = y_pts_test["pts_A"].values
    yB = y_pts_test["pts_B"].values

    mae_A = mean_absolute_error(yA, preds["pts_A"])
    mae_B = mean_absolute_error(yB, preds["pts_B"])
    mae_total = mean_absolute_error(yA + yB, preds["mu_total"])
    mae_margin = mean_absolute_error(yA - yB, preds["mu_margin"])

    # Winner prob
    if "p_A_win" in preds:
        p_A = preds["p_A_win"]
    else:
        # approximate from Normal margin
        mu = preds["mu_margin"]
        sig = preds["sigma_margin"]
        p_A = np.array([gaussian_cover_prob(mu[i], sig[i], 0.0) for i in range(len(mu))])

    y_win = (yA > yB).astype(int)
    p = np.clip(p_A, 1e-6, 1 - 1e-6)
    bs = brier_score_loss(y_win, p)
    ll = log_loss(y_win, p)

    # Winner accuracy using predicted margin sign
    y_pred_win = (preds["mu_margin"] > 0).astype(int)
    acc = accuracy_score(y_win, y_pred_win)

    out = {
        f"{label_prefix}MAE_pts_A": mae_A,
        f"{label_prefix}MAE_pts_B": mae_B,
        f"{label_prefix}MAE_total": mae_total,
        f"{label_prefix}MAE_margin": mae_margin,
        f"{label_prefix}Brier(A_win)": bs,
        f"{label_prefix}LogLoss(A_win)": ll,
        f"{label_prefix}Accuracy(A_win)": acc,
    }

    # Market-based if available
    if market is not None and "bet_total" in market.columns and "bet_spread" in market.columns:
        over_prob = []
        cover_prob = []
        for i in range(len(meta_test)):
            muT = preds["mu_total"][i]
            sigT = preds["sigma_total"][i]
            lineT = market["bet_total"].values[i]
            over_prob.append(gaussian_over_prob(muT, sigT, lineT) if not np.isnan(lineT) else np.nan)

            muM = preds["mu_margin"][i]
            sigM = preds["sigma_margin"][i]
            spread = market["bet_spread"].values[i]
            cover_prob.append(gaussian_cover_prob(muM, sigM, spread) if not np.isnan(spread) else np.nan)
        out[f"{label_prefix}Avg P(over)"] = float(np.nanmean(over_prob))
        out[f"{label_prefix}Avg P(A covers)"] = float(np.nanmean(cover_prob))

    return out



# ----------------------------
# Validation: align predictions with cleaned data
# ----------------------------

def validate_predictions_against_cleaned(raw_df, meta_te, y_pts_te, pred_df, run_dir, cutoff_used):
    """Cross-check that teams and scores in predictions match the cleaned data.
    Creates prediction_alignment_report.csv in run_dir and prints a short summary.
    Matching key is (team_A, team_B, date) from the row perspective.
    """
    # Normalize keys in raw (cleaned data) using row perspective (Team/Opp/Date)
    key_raw = pd.DataFrame({
        "team_A": raw_df.get("Team", pd.Series(index=raw_df.index, dtype=str)).astype(str).str.strip(),
        "team_B": raw_df.get("Opp",  pd.Series(index=raw_df.index, dtype=str)).astype(str).str.strip(),
    })
    key_raw["date"] = pd.to_datetime(raw_df["Date"]).dt.strftime("%Y-%m-%d")
    raw_keys = (key_raw["team_A"].str.lower() + "||" +
                key_raw["team_B"].str.lower() + "||" + key_raw["date"])  

    raw_aln = pd.DataFrame({
        "k": raw_keys,
        "clean_team": key_raw["team_A"],
        "clean_opp": key_raw["team_B"],
        "clean_date": key_raw["date"],
        "clean_team_pts": pd.to_numeric(raw_df.get("team_pts", pd.Series(index=raw_df.index)), errors="coerce"),
        "clean_opp_pts": pd.to_numeric(raw_df.get("opp_pts",  pd.Series(index=raw_df.index)), errors="coerce"),
    })

    # Restrict raw to test period if cutoff is known
    if cutoff_used is not None:
        mask_test = pd.to_datetime(raw_aln["clean_date"]) >= pd.to_datetime(cutoff_used)
        raw_aln = raw_aln.loc[mask_test]

    # Build keys for predictions/meta (already row perspective via prepare_row_as_A)
    meta_keys = (meta_te["team_A"].astype(str).str.strip().str.lower() + "||" +
                 meta_te["team_B"].astype(str).str.strip().str.lower() + "||" +
                 pd.to_datetime(meta_te["date"]).dt.strftime("%Y-%m-%d"))

    pred_aln = pd.DataFrame({
        "k": meta_keys,
        "date": pd.to_datetime(meta_te["date"]).dt.strftime("%Y-%m-%d"),
        "team_A": meta_te["team_A"].astype(str),
        "team_B": meta_te["team_B"].astype(str),
        "true_pts_A": y_pts_te["pts_A"].values,
        "true_pts_B": y_pts_te["pts_B"].values,
    })

    # Bring predictions
    for col in ["pred_pts_A","pred_pts_B","pred_mu_margin","pred_mu_total"]:
        if col in pred_df.columns:
            pred_aln[col] = pred_df[col].values

    # Merge
    merged = pred_aln.merge(raw_aln, on="k", how="left", suffixes=("",""))

    # Flags
    merged["name_mismatch"] = (
        merged["team_A"].str.lower().ne(merged["clean_team"].astype(str).str.lower()) |
        merged["team_B"].str.lower().ne(merged["clean_opp"].astype(str).str.lower())
    )
    merged["score_mismatch"] = (
        (merged["true_pts_A"].astype(float) != merged["clean_team_pts"].astype(float)) |
        (merged["true_pts_B"].astype(float) != merged["clean_opp_pts"].astype(float))
    )

    # Would swapping predicted A/B reduce error (diagnostic only)
    if {"pred_pts_A","pred_pts_B"}.issubset(merged.columns):
        err_as_is = (merged["true_pts_A"] - merged["pred_pts_A"]).abs() + (merged["true_pts_B"] - merged["pred_pts_B"]).abs()
        err_swapped = (merged["true_pts_A"] - merged["pred_pts_B"]).abs() + (merged["true_pts_B"] - merged["pred_pts_A"]).abs()
        merged["err_as_is"] = err_as_is
        merged["err_if_swapped"] = err_swapped
        merged["would_swap_help"] = (err_swapped + 1e-6) < (err_as_is - 0.5)

    # Compose a compact flags column
    def _flags(r):
        f = []
        if r.get("name_mismatch", False): f.append("NAME")
        if r.get("score_mismatch", False): f.append("SCORE")
        if r.get("would_swap_help", False): f.append("SWAP_HELP")
        return ",".join(f)
    merged["flags"] = merged.apply(_flags, axis=1)

    # Save CSV
    out_path = os.path.join(run_dir, "prediction_alignment_report.csv")
    merged_cols = [c for c in [
        "date","team_A","team_B","true_pts_A","true_pts_B",
        "clean_team_pts","clean_opp_pts",
        "pred_pts_A","pred_pts_B","pred_mu_margin","pred_mu_total",
        "err_as_is","err_if_swapped","would_swap_help","name_mismatch","score_mismatch","flags"
    ] if c in merged.columns]
    merged[merged_cols].to_csv(out_path, index=False)
    print("Saved:", out_path)

    # Print brief summary
    total = len(merged)
    n_name = int(merged.get("name_mismatch", pd.Series(False, index=merged.index)).sum())
    n_score = int(merged.get("score_mismatch", pd.Series(False, index=merged.index)).sum())
    n_swap = int(merged.get("would_swap_help", pd.Series(False, index=merged.index)).sum())
    print(f"[validate] rows: {total}, name_mismatch: {n_name}, score_mismatch: {n_score}, swap_help: {n_swap}")

# ----------------------------
# Main
# ----------------------------

def main():
    base_dir = os.environ.get("CBB_DIR", ".")
    cutoff = CUTOFF_DATE
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    RUN_DIR = os.path.join(OUTPUT_DIR, f"run_{run_id}")
    os.makedirs(RUN_DIR, exist_ok=True)
    print("Run directory:", RUN_DIR)

    # 1) Load & pivot to one row per game
    raw = read_years(base_dir=base_dir, years=(2019, 2020, 2021, 2022, 2023, 2024, 2025))
    if "Date" not in raw.columns:
        raise ValueError("Expected a 'Date' column (YYYY-MM-DD).")

    # Parse row scores once
    raw = parse_scores(raw)

    # Row-stable path: no pivot, no sorting; A = row team, B = row opponent
    merged = prepare_row_as_A(raw)
    merged = drop_bad_rows(merged)
    X, y_pts, y_win, meta, market, feature_cols = build_features(merged)

    # 3) Training workflow
    if TRAIN_MODE == "seasonal":
        seasons = sorted(pd.to_numeric(meta["season"]).dropna().unique().tolist())
        all_pred_rows = []
        all_metrics = []
        for s in seasons:
            tr_mask = pd.to_numeric(meta["season"]) < s
            te_mask = pd.to_numeric(meta["season"]) == s
            if tr_mask.sum() == 0 or te_mask.sum() == 0:
                print(f"[seasonal] Skip season {s}: train={int(tr_mask.sum())}, test={int(te_mask.sum())}")
                continue
            meta_tr, meta_te = meta.loc[tr_mask], meta.loc[te_mask]
            X_tr, X_te = X.loc[tr_mask], X.loc[te_mask]
            y_pts_tr, y_pts_te = y_pts.loc[tr_mask], y_pts.loc[te_mask]
            market_tr = market.loc[tr_mask] if len(market) else pd.DataFrame(index=X_tr.index)
            market_te = market.loc[te_mask] if len(market) else pd.DataFrame(index=X_te.index)

            # Chronological validation split inside training (last 10%)
            idx = meta_tr.sort_values("date").index.values
            cut = max(1, int(0.9 * len(idx)))
            tr_idx, val_idx = idx[:cut], idx[cut:]
            X_tr_fit, y_pts_tr_fit = X_tr.loc[tr_idx], y_pts_tr.loc[tr_idx]
            X_val, y_pts_val = (X_tr.loc[val_idx], y_pts_tr.loc[val_idx]) if len(val_idx) >= 10 else (None, None)

            print(f"[seasonal] Train on < {s}: {len(X_tr_fit)} rows | Validate: {0 if X_val is None else len(X_val)} | Test {s}: {len(X_te)} rows")
            lgbm_preds = train_lgbm_multioutput(X_tr_fit, y_pts_tr_fit, X_te, X_val=X_val, y_pts_val=y_pts_val)
            res = evaluate(meta_te, y_pts_te, lgbm_preds, market=market_te, label_prefix=f"LGBM/{s}/")
            for k, v in res.items():
                all_metrics.append({"season": s, "metric": k, "value": v})

            # Build prediction frame for this season
            pred_df = meta_te.copy()
            pred_df["season"] = s
            pred_df["true_pts_A"] = y_pts_te["pts_A"].values
            pred_df["true_pts_B"] = y_pts_te["pts_B"].values
            pred_df["true_margin"] = pred_df["true_pts_A"] - pred_df["true_pts_B"]
            pred_df["true_total"] = pred_df["true_pts_A"] + pred_df["true_pts_B"]
            pred_df["true_A_win"] = (pred_df["true_margin"] > 0).astype(int)
            for k, v in lgbm_preds.items():
                pred_df[f"pred_{k}"] = v
            pred_df["pred_A_win"] = (pred_df["pred_mu_margin"] > 0).astype(int)
            pred_df["err_pts_A"] = np.abs(pred_df["true_pts_A"] - pred_df["pred_pts_A"])
            pred_df["err_pts_B"] = np.abs(pred_df["true_pts_B"] - pred_df["pred_pts_B"])
            pred_df["err_total"] = np.abs(pred_df["true_total"] - pred_df["pred_mu_total"])
            pred_df["err_margin"] = np.abs(pred_df["true_margin"] - pred_df["pred_mu_margin"])
            pred_df["correct_winner"] = (pred_df["true_A_win"] == pred_df["pred_A_win"]).astype(int)
            if "bet_total" in market_te.columns:
                pred_df["bet_total"] = market_te["bet_total"].values
            if "bet_spread" in market_te.columns:
                pred_df["bet_spread"] = market_te["bet_spread"].values
            if "team_A_key" in meta_te.columns:
                pred_df["team_A_key"] = meta_te["team_A_key"].values
            if "team_B_key" in meta_te.columns:
                pred_df["team_B_key"] = meta_te["team_B_key"].values

            per_path = os.path.join(RUN_DIR, f"lgbm_predictions_{s}.csv")
            pred_df.to_csv(per_path, index=False)
            print("Saved:", per_path)
            all_pred_rows.append(pred_df)

            try:
                validate_predictions_against_cleaned(raw, meta_te, y_pts_te, pred_df, RUN_DIR, cutoff_used=None)
            except Exception as ve:
                print("[validate] skipped:", ve)

        if all_pred_rows:
            all_preds = pd.concat(all_pred_rows, ignore_index=True)
            all_path = os.path.join(RUN_DIR, "lgbm_predictions_all_seasons.csv")
            all_preds.to_csv(all_path, index=False)
            print("Saved:", all_path)
        if all_metrics:
            metrics_df = pd.DataFrame(all_metrics)
            met_path = os.path.join(RUN_DIR, "lgbm_metrics_by_season.csv")
            metrics_df.to_csv(met_path, index=False)
            print("Saved:", met_path)
    else:
        # Original single-cutoff workflow
        meta_tr, meta_te, (X_tr, X_te), (y_pts_tr, y_pts_te), (y_win_tr, y_win_te), (market_tr, market_te), cutoff_used = ensure_temporal_split(meta, X, y_pts, y_win, market, cutoff)

        print("Split cutoff:", cutoff_used)
        print("Train size:", len(X_tr), " Test size:", len(X_te))
        if len(X_tr) == 0 or len(X_te) == 0:
            raise ValueError("Temporal split produced empty train or test set even after fallback.")

        results = {}
        out_frames = []

        meta_tr_sorted = meta_tr.sort_values("date")
        idx = meta_tr_sorted.index.values
        cut = max(1, int(0.9 * len(idx)))
        tr_idx, val_idx = idx[:cut], idx[cut:]
        X_tr_fit, y_pts_tr_fit = X_tr.loc[tr_idx], y_pts_tr.loc[tr_idx]
        X_val, y_pts_val = X_tr.loc[val_idx], y_pts_tr.loc[val_idx]
        if len(X_val) < 10:
            X_val, y_pts_val = None, None

        try:
            if len(X_tr) == 0:
                raise ValueError("Empty training set for LightGBM after split.")
            lgbm_preds = train_lgbm_multioutput(X_tr_fit, y_pts_tr_fit, X_te, X_val=X_val, y_pts_val=y_pts_val)
            res_lgbm = evaluate(meta_te, y_pts_te, lgbm_preds, market=market_te, label_prefix="LGBM/")
            results.update(res_lgbm)

            pred_df = meta_te.copy()
            pred_df["true_pts_A"] = y_pts_te["pts_A"].values
            pred_df["true_pts_B"] = y_pts_te["pts_B"].values
            pred_df["true_margin"] = pred_df["true_pts_A"] - pred_df["true_pts_B"]
            pred_df["true_total"] = pred_df["true_pts_A"] + pred_df["true_pts_B"]
            pred_df["true_A_win"] = (pred_df["true_margin"] > 0).astype(int)
            for k, v in lgbm_preds.items():
                pred_df[f"pred_{k}"] = v
            pred_df["pred_A_win"] = (pred_df["pred_mu_margin"] > 0).astype(int)
            pred_df["err_pts_A"] = np.abs(pred_df["true_pts_A"] - pred_df["pred_pts_A"])
            pred_df["err_pts_B"] = np.abs(pred_df["true_pts_B"] - pred_df["pred_pts_B"])
            pred_df["err_total"] = np.abs(pred_df["true_total"] - pred_df["pred_mu_total"])
            pred_df["err_margin"] = np.abs(pred_df["true_margin"] - pred_df["pred_mu_margin"])
            pred_df["correct_winner"] = (pred_df["true_A_win"] == pred_df["pred_A_win"]).astype(int)
            if "bet_total" in market_te.columns:
                pred_df["bet_total"] = market_te["bet_total"].values
            if "bet_spread" in market_te.columns:
                pred_df["bet_spread"] = market_te["bet_spread"].values
            if "team_A_key" in meta_te.columns:
                pred_df["team_A_key"] = meta_te["team_A_key"].values
            if "team_B_key" in meta_te.columns:
                pred_df["team_B_key"] = meta_te["team_B_key"].values

            full_path = os.path.join(RUN_DIR, "lgbm_predictions_with_errors.csv")
            pred_df.to_csv(full_path, index=False)
            print("Saved:", full_path)

            metrics_items = sorted(res_lgbm.items())
            metrics_df = pd.DataFrame(metrics_items, columns=["metric", "value"]) 
            metrics_path = os.path.join(RUN_DIR, "lgbm_metrics.csv")
            metrics_df.to_csv(metrics_path, index=False)
            print("Saved:", metrics_path)

            best25 = pred_df.sort_values("err_margin").head(25)
            worst25 = pred_df.sort_values("err_margin", ascending=False).head(25)
            best_path = os.path.join(RUN_DIR, "best25_margin.csv")
            worst_path = os.path.join(RUN_DIR, "worst25_margin.csv")
            best25.to_csv(best_path, index=False)
            worst25.to_csv(worst_path, index=False)
            print("Saved:", best_path)
            print("Saved:", worst_path)

            try:
                validate_predictions_against_cleaned(raw, meta_te, y_pts_te, pred_df, RUN_DIR, cutoff_used)
            except Exception as ve:
                print("[validate] skipped:", ve)

        except Exception as e:
            print("[WARN] LightGBM run skipped:", str(e))
    with open(os.path.join(RUN_DIR, "features_used.json"), "w") as f:
        import json
        json.dump(feature_cols, f, indent=2)
        print("Saved: features_used.json (", len(feature_cols), "features )")

if __name__ == "__main__":
    main()
