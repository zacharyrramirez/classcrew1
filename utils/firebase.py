# utils/firebase.py
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth, storage

def initialize_firebase():
    """Initialize Firebase Admin SDK with credentials"""
    # First try loading from Streamlit secrets if available
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'firebase' in st.secrets:
            cred = credentials.Certificate(dict(st.secrets['firebase']))
            return cred
    except ImportError:
        pass
    
    # If not running in Streamlit, try local secrets file
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                               '.streamlit', 'secrets.toml')
    if os.path.exists(secrets_path):
        try:
            import tomli
        except ImportError:
            # Install tomli if not available
            import subprocess
            subprocess.check_call(['pip', 'install', 'tomli'])
            import tomli
            
        with open(secrets_path, 'rb') as f:
            config = tomli.load(f)
            if 'firebase' not in config:
                raise RuntimeError("No [firebase] section found in secrets.toml")
            firebase_section = config['firebase']
    
            cred = credentials.Certificate(firebase_section)
            return cred
    
    raise RuntimeError(
        "Firebase credentials not found. Either:\n"
        "1. Run in Streamlit with secrets configured, or\n"
        "2. Create .streamlit/secrets.toml with [firebase] section"
    )

# Initialize Firebase and create shared clients
try:
    cred = initialize_firebase()
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {
            # optional: set storageBucket if you use storage
            # 'storageBucket': 'your-bucket-name.appspot.com'
        })
    
    # Export shared clients
    db = firestore.client()  # Firestore
    firebase_auth = auth     # Auth client
    try:
        bucket = storage.bucket()  # requires storageBucket in initialize_app
    except Exception:
        bucket = None
except Exception as e:
    print(f"Warning: Firebase initialization failed: {e}")
    print("Some features may be unavailable.")
    db = None
    firebase_auth = None
    bucket = None