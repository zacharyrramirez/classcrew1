"""
Client-side Firebase configuration for Google Sign-In
Loads configuration from Streamlit secrets
"""

import streamlit as st

# Firebase configuration for client-side (web) authentication
FIREBASE_CONFIG = {
    "apiKey": st.secrets["firebase"]["web_api_key"],
    "authDomain": f"{st.secrets['firebase']['project_id']}.firebaseapp.com",
    "projectId": st.secrets["firebase"]["project_id"],
    "storageBucket": f"{st.secrets['firebase']['project_id']}.appspot.com",
    "messagingSenderId": st.secrets["firebase"]["client_id"],
    "appId": st.secrets["firebase"]["web_app_id"],
    "measurementId": st.secrets["firebase"]["measurement_id"]
}