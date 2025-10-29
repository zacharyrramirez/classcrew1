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
                            // Check if this is a new user
                            const isNewUser = authResult.additionalUserInfo.isNewUser;
                            // Pass the token and new user status back to Streamlit
                            window.parent.postMessage({{
                                type: 'streamlit:auth',
                                token: idToken,
                                isNewUser: isNewUser
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
    st.title("Classcrew AI Grader")
    
    if 'show_canvas_setup' not in st.session_state:
        st.session_state['show_canvas_setup'] = False
    
    if st.session_state.get('show_canvas_setup'):
        # Show Canvas setup form for new users
        st.subheader("📚 Set Up Canvas Integration")
        st.markdown("Configure your Canvas connection to start grading assignments.")
        
        with st.form("canvas_setup"):
            canvas_url = st.text_input("Canvas URL", placeholder="https://your-school.instructure.com")
            canvas_token = st.text_input("Canvas API Token", type="password", 
                                       placeholder="Your Canvas API token")
            course_id = st.text_input("Course ID", placeholder="123456")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                **Need help?**
                - Canvas URL: Your school's Canvas domain
                - API Token: Account → Settings → Approved Integrations
                - Course ID: Found in the course URL
                """)
            
            if st.form_submit_button("Complete Setup"):
                if all([canvas_url, canvas_token, course_id]):
                    from utils.auth_manager import update_user_canvas
                    success, message = update_user_canvas(
                        st.session_state['temp_username'], 
                        canvas_url, 
                        canvas_token, 
                        course_id
                    )
                    if success:
                        st.session_state['authenticated'] = True
                        st.session_state['show_canvas_setup'] = False
                        st.success("🎉 Setup complete! Redirecting to dashboard...")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error("❌ Please fill in all fields")
        return
    
    # Main authentication page
    tab1, tab2 = st.tabs(["Email/Password", "Google Sign-In"])
    
    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("Sign In")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Sign In", use_container_width=True):
                success, user_data = authenticate_user(username, password)
                if success:
                    st.session_state['user'] = user_data
                    st.session_state['authenticated'] = True
                    st.success("✅ Successfully signed in!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
        
        with col2:
            st.subheader("Create Account")
            st.markdown("""
            Get started with AI-powered grading:
            - Connect to Canvas
            - Grade automatically
            - Review and post grades
            """)
            if st.button("Sign Up", use_container_width=True):
                st.session_state['show_register'] = True
                st.rerun()
    
    with tab2:
        # Google Sign-In
        render_firebase_ui()
        
        # Handle the token and new user status
        if 'token' in st.session_state:
            success, user_data = authenticate_user(id_token=st.session_state['token'])
            if success:
                if 'isNewUser' in st.session_state and st.session_state['isNewUser']:
                    # Store temporary data and show Canvas setup
                    st.session_state['temp_username'] = user_data['email'].split('@')[0]
                    st.session_state['user'] = user_data
                    st.session_state['show_canvas_setup'] = True
                    st.success("🎉 Account created! Let's set up your Canvas integration.")
                    # Clear the new user flag
                    del st.session_state['isNewUser']
                    st.rerun()
                else:
                    st.session_state['user'] = user_data
                    st.session_state['authenticated'] = True
                    st.success("✅ Successfully signed in!")
                    st.rerun()
            else:
                st.error("❌ Failed to authenticate")