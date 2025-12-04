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
            print("DEBUG: Loading Firebase credentials from Streamlit secrets")
            cred = credentials.Certificate(dict(st.secrets['firebase']))
            return cred
        else:
            print("DEBUG: No firebase in Streamlit secrets")
    except ImportError:
        print("DEBUG: Streamlit not available or not running in Streamlit")
    except Exception as e:
        print(f"DEBUG: Error loading from Streamlit secrets: {e}")
    
    # If not running in Streamlit, try local secrets file
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                               '.streamlit', 'secrets.toml')
    print(f"DEBUG: Checking for secrets.toml at {secrets_path}")
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
    
            print("DEBUG: Loading Firebase credentials from secrets.toml")
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
    print("DEBUG: Credentials loaded successfully")
    
    if not firebase_admin._apps:
        print("DEBUG: Initializing Firebase Admin SDK")
        firebase_admin.initialize_app(cred, {
            # optional: set storageBucket if you use storage
            # 'storageBucket': 'your-bucket-name.appspot.com'
        })
        print("DEBUG: Firebase Admin SDK initialized")
    else:
        print("DEBUG: Firebase Admin SDK already initialized")
    
    # Export shared clients
    db = firestore.client()  # Firestore
    firebase_auth = auth     # Auth client
    print("DEBUG: Firebase clients created successfully")
    try:
        bucket = storage.bucket()  # requires storageBucket in initialize_app
    except Exception:
        bucket = None
except Exception as e:
    print(f"ERROR: Firebase initialization failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    print("Some features may be unavailable.")
    db = None
    firebase_auth = None
    bucket = None