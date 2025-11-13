"""Upload trained XGBoost models to Firebase Storage."""
import os
import json
import firebase_admin
from firebase_admin import credentials, storage, firestore
from datetime import datetime



# ============ CONFIGURATION ============
FIREBASE_STORAGE_BUCKET = "betboardtest.firebasestorage.app"
FIREBASE_CREDS_PATH = "services/firebase/betboardtest-firebase-adminsdk-fbsvc-196904ba56.json"
STORAGE_BASE_PATH = "models"

# Set paths to BOTH model directories
NO_BET_MODELS_DIR = "data/xgb_model/No_Bet_xgb_all_models_20251113_103750/models_production"
WITH_BET_MODELS_DIR = "data/xgb_model/Bet_xgb_all_models_20251113_104003/models_production"
# =======================================


def upload_models(models_dir, model_type, model_version):
    """Upload all model files to Firebase."""
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CREDS_PATH)
        firebase_admin.initialize_app(cred, {
            'storageBucket': FIREBASE_STORAGE_BUCKET
        })
    
    bucket = storage.bucket()
    
    print(f"\nUploading {model_type} models...")
    print(f"Source: {models_dir}\n")
    
    files_to_upload = [
        "moneyline_model.json",
        "spread_model.json",
        "total_model.json",
        "feature_names.pkl",
        "model_metadata.json"
    ]
    
    uploaded_files = {}
    
    for filename in files_to_upload:
        local_path = os.path.join(models_dir, filename)
        
        if not os.path.exists(local_path):
            print(f"⚠ Skipping {filename} (not found)")
            continue
        
        remote_path = f"{STORAGE_BASE_PATH}/{model_version}/{model_type}/{filename}"
        blob = bucket.blob(remote_path)
        blob.upload_from_filename(local_path)
        
        uploaded_files[filename] = {
            "path": remote_path,
            "url": f"gs://{bucket.name}/{remote_path}"
        }
        
        print(f"✓ {filename}")
    
    # Load metadata
    metadata_path = os.path.join(models_dir, "model_metadata.json")
    model_metadata = {}
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            model_metadata = json.load(f)
    
    model_metadata["model_type"] = model_type
    
    print(f"✓ {model_type} models uploaded\n")
    
    return uploaded_files, model_metadata


def upload_both_models(no_bet_dir=NO_BET_MODELS_DIR, with_bet_dir=WITH_BET_MODELS_DIR, model_version=None):
    """Upload both no-bet and with-bet models."""
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CREDS_PATH)
        firebase_admin.initialize_app(cred, {
            'storageBucket': FIREBASE_STORAGE_BUCKET
        })
    
    db = firestore.client()
    
    if model_version is None:
        model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"Model version: {model_version}")
    print("="*70)
    
    # Upload both models
    no_bet_files, no_bet_metadata = upload_models(no_bet_dir, "no_bet", model_version)
    with_bet_files, with_bet_metadata = upload_models(with_bet_dir, "with_bet", model_version)
    
    # Save to Firestore
    model_doc = {
        "version": model_version,
        "uploaded_at": datetime.now(),
        "no_bet": {
            "files": no_bet_files,
            "metadata": no_bet_metadata
        },
        "with_bet": {
            "files": with_bet_files,
            "metadata": with_bet_metadata
        },
        "status": "active"
    }
    
    db.collection("models").document(model_version).set(model_doc)
    
    # Always update 'latest' to point to newest upload
    db.collection("models").document("latest").set({
        "version": model_version,
        "updated_at": datetime.now()
    })
    
    # Also update 'current_production'
    db.collection("models").document("current_production").set({
        "version": model_version,
        "updated_at": datetime.now()
    })
    
    print("="*70)
    print(f"✓ Both models uploaded!")
    print(f"Version: {model_version}")
    print(f"Set as: latest & current_production")
    print(f"Storage: gs://{FIREBASE_STORAGE_BUCKET}/{STORAGE_BASE_PATH}/{model_version}/")
    print(f"  - {STORAGE_BASE_PATH}/{model_version}/no_bet/")
    print(f"  - {STORAGE_BASE_PATH}/{model_version}/with_bet/\n")
    
    return model_version


if __name__ == "__main__":
    upload_both_models()