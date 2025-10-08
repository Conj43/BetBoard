#!/usr/bin/env python3
"""
Publish CBB predictions to Firebase Firestore.

Requirements:
    pip install firebase-admin

Setup:
    1. Go to Firebase Console: https://console.firebase.google.com/
    2. Project Settings > Service Accounts
    3. Generate New Private Key
    4. Save as 'firebase-credentials.json' in this directory
"""

import os, re
import json
import pandas as pd
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase configuration
FIREBASE_CREDENTIALS_PATH = "services/firebase/betboardtest-firebase-adminsdk-fbsvc-196904ba56.json"
CSV_PATH = "data/predictions/predictions_2022-12-05.csv"

class FirebasePublisher:
    """Publish predictions to Firebase Firestore."""
    
    def __init__(self, credentials_path=FIREBASE_CREDENTIALS_PATH):
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"Firebase credentials not found at {credentials_path}\n"
                "Please download from Firebase Console > Project Settings > Service Accounts"
            )
        
        if not firebase_admin._apps:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        print(f"✓ Connected to Firebase")
    
    # ---------- Normalization & helpers ----------
    def normalize_team(self, team):
        """Lowercase and remove spaces & non-alphanumeric chars."""
        if pd.isna(team):
            return ""
        return re.sub(r'[^a-z0-9]', '', str(team).lower())
    
    def _choose_team(self, value, team_a_norm: str, team_b_norm: str) -> str:
        """
        Resolve a generic 'choice' value to a normalized team name.
        Handles 1/0, True/False, 'A'/'B', 'team_a'/'team_b', or direct names.
        Returns '' if it can't resolve.
        """
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        
        s = str(value).strip().lower()
        # direct name match (already normalized or raw but matches once normalized)
        if self.normalize_team(s) == team_a_norm:
            return team_a_norm
        if self.normalize_team(s) == team_b_norm:
            return team_b_norm

        # common encodings
        if s in {"a", "team_a", "home", "favorite", "a_team", "team a"}:
            return team_a_norm
        if s in {"b", "team_b", "away", "underdog", "b_team", "team b"}:
            return team_b_norm

        # numeric/bool style
        if s in {"1", "true", "t", "yes"}:
            return team_a_norm
        if s in {"0", "false", "f", "no", "-1"}:
            return team_b_norm
        
        return ""  # unknown encoding
    
    # ---------- Formatting ----------
    def format_game_data(self, row):
        """Convert DataFrame row to Firebase-ready dictionary."""
        # Normalize team names for consistent publishing
        team_a_norm = self.normalize_team(row.get('team_A', ''))
        team_b_norm = self.normalize_team(row.get('team_B', ''))
        
        game_data = {
            'game_id': str(row.get('game_id', '')),
            'date': row['date'].isoformat() if isinstance(row['date'], pd.Timestamp) else str(row['date']),
            'season': int(row.get('season', 0)),
            'team_A': team_a_norm,
            'team_B': team_b_norm,
            'updated_at': firestore.SERVER_TIMESTAMP,
        }
        
        # ----- Moneyline (winner as TEAM NAME) -----
        if 'pred_winner' in row:
            pred_winner_team = self._choose_team(row['pred_winner'], team_a_norm, team_b_norm)
            # If still empty, fallback: treat truthy as A, falsy as B
            if not pred_winner_team:
                try:
                    pred_winner_team = team_a_norm if bool(int(row['pred_winner'])) else team_b_norm
                except Exception:
                    pred_winner_team = ""  # give up if weird type

            moneyline = {
                'pred_winner': pred_winner_team,  # <-- team name (normalized)
            }
            if 'p_win_A' in row and pd.notna(row['p_win_A']):
                # keep p_win_A as-is for reference
                moneyline['p_win_A'] = float(row['p_win_A'])
            if 'moneyline_a' in row and pd.notna(row['moneyline_a']):
                moneyline['odds_a'] = float(row['moneyline_a'])
            if 'moneyline_b' in row and pd.notna(row['moneyline_b']):
                moneyline['odds_b'] = float(row['moneyline_b'])
            game_data['moneyline'] = moneyline
        
        # ----- Spread (pick as TEAM NAME that covers) -----
        if 'pred_margin' in row:
            spread = {
                'pred_margin': float(row['pred_margin']),
            }
            if 'bet_spread' in row and pd.notna(row['bet_spread']):
                spread['line'] = float(row['bet_spread'])
            if 'prob_cover' in row and pd.notna(row['prob_cover']):
                spread['prob_cover'] = float(row['prob_cover'])
            
            # Convert spread_pick to a team name if present
            if 'spread_pick' in row:
                pick_team = self._choose_team(row['spread_pick'], team_a_norm, team_b_norm)
                # If not resolvable, try a margin/line heuristic:
                # positive pred_margin => A projected to win; compare to line if present
                if not pick_team:
                    try:
                        line = float(row['bet_spread']) if pd.notna(row.get('bet_spread', pd.NA)) else None
                    except Exception:
                        line = None
                    try:
                        margin = float(row['pred_margin'])
                    except Exception:
                        margin = None
                    if margin is not None:
                        # If line indicates A is -X (favorite) usually bet_spread is from A's POV.
                        # Without strict convention available, default: margin > 0 => team A, else team B.
                        pick_team = team_a_norm if margin > 0 else team_b_norm
                spread['pick'] = pick_team  # <-- team name (normalized)

            game_data['spread'] = spread
        
        # ----- Total (unchanged, just pass through numbers & pick string if present) -----
        if 'pred_total' in row:
            total = {
                'pred_total': float(row['pred_total']),
            }
            if 'bet_total' in row and pd.notna(row['bet_total']):
                total['line'] = float(row['bet_total'])
            if 'prob_over' in row and pd.notna(row['prob_over']):
                total['prob_over'] = float(row['prob_over'])
            if 'total_pick' in row and pd.notna(row['total_pick']):
                total['pick'] = str(row['total_pick'])
            game_data['total'] = total
        
        return game_data
    
    # ---------- Firestore I/O ----------
    def publish_game(self, game_data, date_str):
        doc_ref = (
            self.db.collection('example_predictions')
                   .document(date_str)
                   .collection('games')
                   .document(game_data['game_id'])
        )
        doc_ref.set(game_data)
        return doc_ref
    
    def publish_day(self, predictions_df, date_str=None):
        if date_str is None:
            first_date = predictions_df['date'].iloc[0]
            if isinstance(first_date, pd.Timestamp):
                date_str = first_date.strftime('%Y-%m-%d')
            else:
                date_str = str(first_date).split('T')[0] if 'T' in str(first_date) else str(first_date)
        
        print(f"\nPublishing {len(predictions_df)} games for {date_str}...")
        published_refs = []
        for idx, row in predictions_df.iterrows():
            try:
                game_data = self.format_game_data(row)
                doc_ref = self.publish_game(game_data, date_str)
                published_refs.append(doc_ref)
                print(f"  ✓ {row.get('team_A', '')} vs {row.get('team_B', '')}")
            except Exception as e:
                print(f"  ✗ Error publishing {row.get('team_A', 'Unknown')} vs {row.get('team_B', 'Unknown')}: {e}")
        
        print(f"\n✓ Published {len(published_refs)} games to Firebase")
        return published_refs
    
    def publish_from_csv(self, csv_path):
        print(f"Loading predictions from {csv_path}...")
        predictions_df = pd.read_csv(csv_path)
        if 'date' in predictions_df.columns:
            predictions_df['date'] = pd.to_datetime(predictions_df['date'])
        return self.publish_day(predictions_df)
    
    def get_predictions(self, date_str):
        games_ref = self.db.collection('example_predictions').document(date_str).collection('games')
        docs = games_ref.stream()
        return [doc.to_dict() for doc in docs]
    
    def delete_date(self, date_str):
        print(f"Deleting predictions for {date_str}...")
        games_ref = self.db.collection('example_predictions').document(date_str).collection('games')
        docs = games_ref.stream()
        deleted_count = 0
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1
        self.db.collection('example_predictions').document(date_str).delete()
        print(f"✓ Deleted {deleted_count} games")


def main():
    publisher = FirebasePublisher()

    if os.path.exists(CSV_PATH):
        publisher.publish_from_csv(CSV_PATH)
    else:
        print(f"CSV not found: {CSV_PATH}")


if __name__ == "__main__":
    main()