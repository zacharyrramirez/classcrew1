"""
Streamlit authentication page with Google Sign-In support
"""

import streamlit as st
import streamlit.components.v1 as components
from utils.auth_manager import authenticate_user, create_user
from utils.firebase_config import FIREBASE_CONFIG

def render_firebase_ui():
    """Render the Firebase UI for authentication"""
    # Include Firebase scripts
    components.html(
        f"""
        <script type="module">
            // Import the functions you need from the SDKs you need
            import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/12.4.0/firebase-app.js";
            import {{ getAuth, GoogleAuthProvider }} from "https://www.gstatic.com/firebasejs/12.4.0/firebase-auth.js";
            import {{ getAnalytics }} from "https://www.gstatic.com/firebasejs/12.4.0/firebase-analytics.js";

            // Your web app's Firebase configuration
            const firebaseConfig = {str(FIREBASE_CONFIG)};

            // Initialize Firebase
            const app = initializeApp(firebaseConfig);
            const auth = getAuth(app);
            const analytics = getAnalytics(app);

            // Set up Google Auth Provider
            const provider = new GoogleAuthProvider();
        </script>

        <div id="firebaseui-auth-container"></div>
        <div id="loader">Loading...</div>

        <script>
            
            // Set up sign-in methods
            const uiConfig = {{
                signInOptions: [
                    // Enable Google Sign-In
                    GoogleAuthProvider.PROVIDER_ID,
                    // Enable Email/Password sign-in
                    {{
                        provider: EmailAuthProvider.PROVIDER_ID,
                        requireDisplayName: true
                    }}
                ],
                callbacks: {{
                    signInSuccessWithAuthResult: function(authResult, redirectUrl) {{
                        // Get the user's ID token
                        authResult.user.getIdToken().then(function(idToken) {{
                            // Pass the token back to Streamlit
                            window.parent.postMessage({{
                                type: 'streamlit:auth',
                                token: idToken
                            }}, '*');
                        }});
                        return false;
                    }}
                }}
            }};
            
            ui.start('#firebaseui-auth-container', uiConfig);
        </script>
        """.replace("{config}", str(FIREBASE_CONFIG)),
        height=500
    )

def auth_page():
    """Main authentication page"""
    st.title("Sign In")
    
    # Add tabs for different auth methods
    tab1, tab2 = st.tabs(["Email/Password", "Google Sign-In"])
    
    with tab1:
        # Regular email/password authentication
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Sign In"):
            success, user_data = authenticate_user(username, password)
            if success:
                st.session_state['user'] = user_data
                st.success("Successfully signed in!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with tab2:
        # Google Sign-In
        render_firebase_ui()
        
        # Handle the token from Google Sign-In
        if 'token' in st.session_state:
            success, user_data = authenticate_user(id_token=st.session_state['token'])
            if success:
                st.session_state['user'] = user_data
                st.success("Successfully signed in with Google!")
                st.rerun()
            else:
                st.error("Failed to authenticate with Google")