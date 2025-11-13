# This is script for testing outside of google cloud scheduler/functions
# We dont need the credentials once it is added to the cloud function environment

import requests
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, storage
import os

FIREBASE_CREDENTIALS_PATH = "services/firebase/betboardtest-firebase-adminsdk-fbsvc-196904ba56.json"

# Initialize Firebase
if not firebase_admin._apps:
    if os.path.exists(FIREBASE_CREDENTIALS_PATH):
        # Local: Use service account file
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'betboardtest.firebasestorage.app'  # Update with exact bucket name
        })
    else:
        # Cloud Functions: Use default credentials
        firebase_admin.initialize_app()

def scrape_torvik(request=None):
    """
    Cloud Function to scrape Torvik rankings and save to Firebase Storage.
    Can be triggered by Cloud Scheduler.
    """
    try:
        # URL for Torvik's rankings CSV
        url = "https://barttorvik.com/2026_team_results.csv"
        
        # Download the CSV
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            error_msg = f"Error downloading CSV: Status {response.status_code}"
            print(error_msg)
            return {"success": False, "error": error_msg}, 500
        
        # Create filename with date (consistent naming for easy retrieval)
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"raw_data/torvik_rankings/{today}/rankings.csv"
        
        # Upload to Firebase Storage
        bucket = storage.bucket()
        blob = bucket.blob(filename)
        blob.upload_from_string(
            response.content,
            content_type='text/csv'
        )
        
        # Also save as "latest" for easy access
        latest_blob = bucket.blob("raw_data/torvik_rankings/latest.csv")
        latest_blob.upload_from_string(
            response.content,
            content_type='text/csv'
        )
        
        success_msg = f"Successfully uploaded to {filename}"
        print(success_msg)
        
        return {
            "success": True, 
            "message": success_msg,
            "file": filename,
            "date": today
        }, 200
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}, 500

# For local testing
if __name__ == "__main__":
    result, status = scrape_torvik()
    print(f"Status: {status}")
    print(f"Result: {result}")