#!/usr/bin/env python3
"""
Simple script to inspect files in Firebase Storage.
Change the FILE_PATH variable to look at different files.
"""

import json
from io import StringIO
import pandas as pd
import firebase_admin
from firebase_admin import credentials, storage

# =============================================================================
# CONFIGURATION - Change these to inspect different files
# =============================================================================

FIREBASE_CREDENTIALS_PATH = "services/firebase/betboardtest-firebase-adminsdk-fbsvc-196904ba56.json"
FIREBASE_STORAGE_BUCKET = "betboardtest.firebasestorage.app"

# Change this to inspect different files
# FILE_PATH = "gamelogs/alabama-birmingham/2026.csv"
FILE_PATH = "processed_features/latest.csv"
# Examples:
# FILE_PATH = "raw_data/gamelogs/kansas-state/2026.csv"
# FILE_PATH = "raw_data/odds/latest.json"
# FILE_PATH = "raw_data/torvik_rankings/latest.csv"
# FILE_PATH = "raw_data/games/latest.csv"
# FILE_PATH = "raw_data/team_snapshots/latest.csv"

# =============================================================================

def inspect_file(file_path: str):
    """Download and inspect a file from Firebase Storage."""
    
    print(f"\n{'='*70}")
    print(f"Inspecting: {file_path}")
    print(f"{'='*70}\n")
    
    # Initialize Firebase
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_STORAGE_BUCKET})
    
    bucket = storage.bucket(FIREBASE_STORAGE_BUCKET)
    blob = bucket.blob(file_path)
    
    # Check if file exists
    if not blob.exists():
        print(f"❌ File does NOT exist at: {file_path}")
        print("\nTry one of these paths:")
        print("  - raw_data/gamelogs/<team>/2026.csv")
        print("  - raw_data/odds/latest.json")
        print("  - raw_data/torvik_rankings/latest.csv")
        print("  - raw_data/games/latest.csv")
        print("  - raw_data/team_snapshots/latest.csv")
        return
    
    print(f"✅ File exists!")
    
    # Get metadata
    blob.reload()
    print(f"\nFile size: {blob.size:,} bytes")
    print(f"Updated: {blob.updated}")
    print(f"Content type: {blob.content_type}")
    
    # Download content
    content = blob.download_as_text()
    
    # Handle different file types
    if file_path.endswith('.json'):
        print("\n" + "-"*70)
        print("JSON CONTENT:")
        print("-"*70)
        data = json.loads(content)
        print(json.dumps(data, indent=2))
        
        if isinstance(data, dict):
            print(f"\nTop-level keys: {list(data.keys())}")
            if 'games' in data:
                print(f"Number of games: {len(data.get('games', []))}")
        
    elif file_path.endswith('.csv'):

        df = pd.read_csv(StringIO(content))
        df.to_csv('services/automation/torvik.csv', index=False) 
        


if __name__ == "__main__":
    try:
        inspect_file(FILE_PATH)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
