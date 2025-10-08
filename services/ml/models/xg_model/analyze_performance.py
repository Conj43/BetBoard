# debug_team_ratings.py
"""Debug and fix team rating matching issues."""
import os
import pandas as pd
import numpy as np

def inspect_data_structure(run_dir, data_dir):
    """Inspect the structure of prediction and rating data."""
    print("="*70)
    print("DATA STRUCTURE INSPECTION")
    print("="*70)
    
    # Load predictions
    ml_path = os.path.join(run_dir, "moneyline_predictions_2025.csv")
    ml_df = pd.read_csv(ml_path)
    
    print("\n1. PREDICTION DATA SAMPLE:")
    print(ml_df[['team_A', 'team_B']].head(10))
    
    print("\n2. UNIQUE TEAMS IN PREDICTIONS:")
    teams_in_preds = set(ml_df['team_A'].unique()) | set(ml_df['team_B'].unique())
    print(f"Total unique teams: {len(teams_in_preds)}")
    print("Sample teams:", sorted(list(teams_in_preds))[:10])
    
    # Load raw data to check what columns exist
    print("\n3. CHECKING RAW DATA FILES:")
    per_game_path = os.path.join(data_dir, "per_game_2025.csv")
    if os.path.exists(per_game_path):
        raw_df = pd.read_csv(per_game_path)
        print(f"\nColumns in per_game_2025.csv:")
        print([col for col in raw_df.columns if 'barthag' in col.lower() or 
               'team' in col.lower() or 'rank' in col.lower() or 'adj' in col.lower()])
        
        print("\n4. SAMPLE RAW DATA:")
        relevant_cols = [col for col in raw_df.columns if col in 
                        ['Team', 'Opp', 'team_barthag', 'opp_barthag', 'team_adj_o', 
                         'team_adj_d', 'team_rank', 'Date']]
        if relevant_cols:
            print(raw_df[relevant_cols].head(10))
        
        print("\n5. CHECKING FOR BARTHAG DATA:")
        if 'team_barthag' in raw_df.columns:
            print(f"team_barthag range: {raw_df['team_barthag'].min():.3f} - {raw_df['team_barthag'].max():.3f}")
            print(f"Non-null barthag: {raw_df['team_barthag'].notna().sum()} / {len(raw_df)}")
            
            # Show some teams with barthag
            sample_with_barthag = raw_df[raw_df['team_barthag'].notna()][['Team', 'team_barthag']].drop_duplicates().head(10)
            print("\nSample teams with barthag:")
            print(sample_with_barthag)
        else:
            print("WARNING: 'team_barthag' column not found!")
            print("Available rating columns:", [col for col in raw_df.columns if 'barthag' in col.lower()])
        
        # Check team name formatting
        print("\n6. TEAM NAME COMPARISON:")
        raw_teams = set(raw_df['Team'].str.strip().unique())
        print(f"Teams in raw data: {len(raw_teams)}")
        print("Sample raw teams:", sorted(list(raw_teams))[:10])
        
        # Check for mismatches
        pred_teams_sample = list(teams_in_preds)[:5]
        print(f"\n7. CHECKING IF PREDICTION TEAMS EXIST IN RAW DATA:")
        for team in pred_teams_sample:
            team_clean = team.strip()
            exists = team_clean in raw_teams
            print(f"  '{team}' -> exists: {exists}")
            if not exists:
                # Find close matches
                close = [t for t in raw_teams if team_clean.lower() in t.lower() or t.lower() in team_clean.lower()]
                if close:
                    print(f"    Possible matches: {close[:3]}")


def create_improved_ratings_loader(data_dir, years=[2025]):
    """Create an improved version that handles the actual data structure."""
    print("\n" + "="*70)
    print("CREATING IMPROVED RATINGS LOADER")
    print("="*70)
    
    frames = []
    
    for year in years:
        path = os.path.join(data_dir, f"per_game_{year}.csv")
        if not os.path.exists(path):
            continue
            
        df = pd.read_csv(path)
        
        # Check what rating columns exist
        rating_cols = [col for col in df.columns if 'barthag' in col.lower()]
        print(f"\nYear {year}: Found columns: {rating_cols}")
        
        if 'team_barthag' in df.columns:
            # Extract unique team ratings
            team_ratings = df[['Team', 'team_barthag']].copy()
            team_ratings = team_ratings[team_ratings['team_barthag'].notna()]
            team_ratings.columns = ['team', 'barthag']
            
            # Also get other metrics if available
            if 'team_adj_o' in df.columns:
                adj_o = df[['Team', 'team_adj_o']].copy()
                adj_o.columns = ['team', 'adj_o']
                team_ratings = team_ratings.merge(adj_o, on='team', how='left')
            
            if 'team_adj_d' in df.columns:
                adj_d = df[['Team', 'team_adj_d']].copy()
                adj_d.columns = ['team', 'adj_d']
                team_ratings = team_ratings.merge(adj_d, on='team', how='left')
            
            if 'team_rank' in df.columns:
                rank = df[['Team', 'team_rank']].copy()
                rank.columns = ['team', 'rank']
                team_ratings = team_ratings.merge(rank, on='team', how='left')
            
            # Clean team names - normalize to match prediction format
            team_ratings['team'] = team_ratings['team'].apply(
                lambda x: str(x).strip().lower().replace(' ', '-').replace('&', '') if pd.notna(x) else x
            )
            
            # Get most recent rating for each team
            team_ratings = team_ratings.drop_duplicates('team', keep='last')
            
            frames.append(team_ratings)
            print(f"  Loaded {len(team_ratings)} teams with ratings")
    
    if frames:
        ratings = pd.concat(frames, ignore_index=True)
        ratings = ratings.drop_duplicates('team', keep='last')
        print(f"\nTotal unique teams: {len(ratings)}")
        print("\nRating summary:")
        print(ratings.describe())
        return ratings
    
    return None


def enhanced_analysis_with_fixed_ratings(run_dir, data_dir):
    """Re-run analysis with proper rating matching."""
    print("\n" + "="*70)
    print("ENHANCED ANALYSIS WITH FIXED RATINGS")
    print("="*70)
    
    # Load predictions
    ml_df = pd.read_csv(os.path.join(run_dir, "moneyline_predictions_2025.csv"))
    spread_df = pd.read_csv(os.path.join(run_dir, "spread_predictions_2025.csv"))
    total_df = pd.read_csv(os.path.join(run_dir, "total_predictions_2025.csv"))
    
    # Parse dates
    for df in [ml_df, spread_df, total_df]:
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.month
        df['month_name'] = df['date'].dt.strftime('%B')
    
    # Load ratings properly
    ratings = create_improved_ratings_loader(data_dir)
    
    if ratings is None:
        print("ERROR: Could not load ratings")
        return
    
    # Add ratings to predictions
    def normalize_team_name(name):
        """Normalize team names to match raw data format."""
        if pd.isna(name):
            return name
        # Convert to lowercase and replace spaces with hyphens
        return str(name).strip().lower().replace(' ', '-').replace('&', '')
    
    def add_ratings_robust(df, ratings):
        """Add ratings with better error handling."""
        df = df.copy()
        df['team_A_clean'] = df['team_A'].apply(normalize_team_name)
        df['team_B_clean'] = df['team_B'].apply(normalize_team_name)
        
        # Merge ratings
        df = df.merge(
            ratings.rename(columns={'team': 'team_A_clean', 'barthag': 'barthag_A'})[['team_A_clean', 'barthag_A']],
            on='team_A_clean',
            how='left'
        )
        df = df.merge(
            ratings.rename(columns={'team': 'team_B_clean', 'barthag': 'barthag_B'})[['team_B_clean', 'barthag_B']],
            on='team_B_clean',
            how='left'
        )
        
        # Check match rate
        matched_A = df['barthag_A'].notna().sum()
        matched_B = df['barthag_B'].notna().sum()
        print(f"  Matched Team A: {matched_A}/{len(df)} ({100*matched_A/len(df):.1f}%)")
        print(f"  Matched Team B: {matched_B}/{len(df)} ({100*matched_B/len(df):.1f}%)")
        
        # Show some examples of matched teams
        if matched_A > 0 and matched_B > 0:
            sample = df[df['barthag_A'].notna() & df['barthag_B'].notna()].head(3)
            print(f"\n  Sample matched games:")
            for idx, row in sample.iterrows():
                print(f"    {row['team_A']} (barthag={row['barthag_A']:.3f}) vs {row['team_B']} (barthag={row['barthag_B']:.3f})")
        
        # Add derived metrics
        df['avg_barthag'] = (df['barthag_A'] + df['barthag_B']) / 2
        df['barthag_diff'] = abs(df['barthag_A'] - df['barthag_B'])
        
        # Categorize matchup quality
        def categorize_matchup(row):
            if pd.isna(row['barthag_A']) or pd.isna(row['barthag_B']):
                return 'Unknown'
            
            # Thresholds based on actual data distribution
            high_threshold = ratings['barthag'].quantile(0.75)
            low_threshold = ratings['barthag'].quantile(0.25)
            
            a_high = row['barthag_A'] >= high_threshold
            a_low = row['barthag_A'] <= low_threshold
            b_high = row['barthag_B'] >= high_threshold
            b_low = row['barthag_B'] <= low_threshold
            
            if a_high and b_high:
                return 'Elite vs Elite'
            elif a_low and b_low:
                return 'Weak vs Weak'
            elif (a_high and b_low) or (a_low and b_high):
                return 'Mismatch'
            else:
                return 'Mid-tier'
        
        df['matchup_quality'] = df.apply(categorize_matchup, axis=1)
        
        # Categorize by rating gap
        df['competitiveness'] = pd.cut(
            df['barthag_diff'],
            bins=[0, 0.05, 0.15, 0.30, 1.0],
            labels=['Very Close', 'Competitive', 'Moderate Gap', 'Large Gap']
        )
        
        return df
    
    print("\nAdding ratings to moneyline predictions:")
    ml_df = add_ratings_robust(ml_df, ratings)
    print("\nAdding ratings to spread predictions:")
    spread_df = add_ratings_robust(spread_df, ratings)
    print("\nAdding ratings to total predictions:")
    total_df = add_ratings_robust(total_df, ratings)
    
    # Re-run analyses
    analysis_dir = os.path.join(run_dir, "performance_analysis_fixed")
    os.makedirs(analysis_dir, exist_ok=True)
    
    # Save enhanced predictions with ratings
    ml_df.to_csv(os.path.join(analysis_dir, "ml_predictions_with_ratings.csv"), index=False)
    spread_df.to_csv(os.path.join(analysis_dir, "spread_predictions_with_ratings.csv"), index=False)
    total_df.to_csv(os.path.join(analysis_dir, "total_predictions_with_ratings.csv"), index=False)
    
    print("\n" + "="*70)
    print("MATCHUP QUALITY BREAKDOWN")
    print("="*70)
    
    print("\nMatchup Quality Distribution:")
    print(ml_df['matchup_quality'].value_counts())
    
    print("\nCompetitiveness Distribution:")
    print(ml_df['competitiveness'].value_counts())
    
    # Analyze by matchup quality
    print("\n" + "="*70)
    print("MONEYLINE BY MATCHUP QUALITY")
    print("="*70)
    
    ml_by_matchup = ml_df.groupby('matchup_quality').agg({
        'correct': ['count', 'mean'],
        'p_win_A': ['mean', 'std']
    }).round(4)
    ml_by_matchup.columns = ['n_games', 'accuracy', 'avg_prob', 'std_prob']
    print(ml_by_matchup)
    ml_by_matchup.to_csv(os.path.join(analysis_dir, "ml_by_matchup_fixed.csv"))
    
    print("\n" + "="*70)
    print("SPREAD BY MATCHUP QUALITY")
    print("="*70)
    
    spread_by_matchup = spread_df.groupby('matchup_quality').agg({
        'err_margin': ['count', 'mean', 'median'],
        'ats_correct': 'mean'
    }).round(3)
    spread_by_matchup.columns = ['n_games', 'mae', 'median_error', 'ats_accuracy']
    print(spread_by_matchup)
    spread_by_matchup.to_csv(os.path.join(analysis_dir, "spread_by_matchup_fixed.csv"))
    
    print("\n" + "="*70)
    print("MONEYLINE BY COMPETITIVENESS")
    print("="*70)
    
    ml_by_comp = ml_df.groupby('competitiveness').agg({
        'correct': ['count', 'mean'],
        'p_win_A': ['mean']
    }).round(4)
    ml_by_comp.columns = ['n_games', 'accuracy', 'avg_prob']
    print(ml_by_comp)
    ml_by_comp.to_csv(os.path.join(analysis_dir, "ml_by_competitiveness_fixed.csv"))
    
    print("\n" + "="*70)
    print("SPREAD BY COMPETITIVENESS")
    print("="*70)
    
    spread_by_comp = spread_df.groupby('competitiveness').agg({
        'err_margin': ['count', 'mean', 'median'],
        'ats_correct': 'mean'
    }).round(3)
    spread_by_comp.columns = ['n_games', 'mae', 'median_error', 'ats_accuracy']
    print(spread_by_comp)
    spread_by_comp.to_csv(os.path.join(analysis_dir, "spread_by_competitiveness_fixed.csv"))
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print(f"Results saved to: {analysis_dir}")
    print("="*70)


if __name__ == "__main__":
    # Update these paths
    RUN_DIR = "data/xgb_model/xgb_all_models_20251007_201057"
    DATA_DIR = "data/cleaned"
    
    # First, inspect the data structure
    inspect_data_structure(RUN_DIR, DATA_DIR)
    
    # Then run the enhanced analysis
    enhanced_analysis_with_fixed_ratings(RUN_DIR, DATA_DIR)