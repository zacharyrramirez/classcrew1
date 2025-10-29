"""
Streamlit authentication page with Google Sign-In support
"""

import streamlit as st
from urllib.parse import urlparse
from utils.auth_manager import authenticate_user, create_user


def validate_canvas_url(url: str):
    """Validate that canvas URL is present and looks like a URL with scheme and hostname."""
    if not url or not url.strip():
        return False, "Canvas URL is required"
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        return False, "Canvas URL must include scheme (https://...)"
    if not parsed.hostname:
        return False, "Canvas URL appears invalid"
    if '.' not in parsed.hostname:
        return False, "Canvas hostname appears invalid"
    return True, ""


def validate_course_id(course_id: str):
    if not course_id or not str(course_id).strip():
        return False, "Course ID is required"
    if not str(course_id).strip().isdigit():
        return False, "Course ID must be numeric"
    return True, ""


def validate_canvas_token(token: str):
    if not token or not str(token).strip():
        return False, "Canvas API token is required"
    if len(str(token).strip()) < 10:
        return False, "Canvas API token looks too short"
    return True, ""



def render_breadcrumb():
    """Render navigation breadcrumb"""
    current = st.session_state.get('current_page', 'login')
    
    breadcrumb_style = """
        <style>
            .breadcrumb { color: #666; font-size: 0.9em; margin-bottom: 1em; }
            .breadcrumb-current { color: #ff4b4b; font-weight: bold; }
        </style>
    """
    
    if current == 'login':
        path = '<p class="breadcrumb">🏠 Home</p>'
    elif current == 'register':
        path = '<p class="breadcrumb">🏠 Home > 📝 Register</p>'
    elif current == 'canvas_setup':
        path = '<p class="breadcrumb">🏠 Home > 📝 Register > 🎓 Canvas Setup</p>'
    
    st.markdown(breadcrumb_style, unsafe_allow_html=True)
    st.markdown(path, unsafe_allow_html=True)

def render_help_sidebar():
    """Render helpful information in the sidebar"""
    with st.sidebar:
        st.subheader("🔍 Quick Help")
        
        current_page = st.session_state.get('current_page', 'login')
        
        if current_page == 'login':
            st.markdown("""
            **Need help signing in?**
            - Make sure your username is correct
            - Passwords are case-sensitive
            - [Forgot password?](#) (Coming soon)
            """)
        
        elif current_page == 'register':
            st.markdown("""
            **Registration Tips:**
            1. Choose a memorable username
            2. Use a strong password
            3. Use your school email
            
            **Canvas Setup:**
            - Have your Canvas URL ready
            - Generate an API token
            - Find your course ID
            """)
            
            with st.expander("🎓 How to find Course ID"):
                st.markdown("""
                1. Go to your Canvas course
                2. Look at the URL
                3. The number after 'courses/' is your Course ID
                """)
                
            with st.expander("🔑 How to get API Token"):
                st.markdown("""
                1. Go to Canvas Account Settings
                2. Click 'New Access Token'
                3. Give it a purpose (e.g., 'AI Grader')
                4. Copy the generated token
                """)

def auth_page():
    """Main authentication page"""
    st.title("Classcrew AI Grader")
    
    # Render breadcrumb navigation
    render_breadcrumb()
    
    # Render help sidebar
    render_help_sidebar()
    
    # Initialize all navigation state variables
    if 'show_canvas_setup' not in st.session_state:
        st.session_state['show_canvas_setup'] = False
    if 'show_register' not in st.session_state:
        st.session_state['show_register'] = False
    if 'nav_stack' not in st.session_state:
        st.session_state['nav_stack'] = []
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'login'
        
    # Handle query parameters for navigation
    params = st.experimental_get_query_params()
    if 'page' in params:
        requested_page = params['page'][0]
        if requested_page != st.session_state['current_page']:
            # Update navigation stack
            st.session_state['nav_stack'].append(st.session_state['current_page'])
            st.session_state['current_page'] = requested_page
            
            # Set appropriate state based on requested page
            if requested_page == 'register':
                st.session_state['show_register'] = True
            elif requested_page == 'canvas_setup':
                st.session_state['show_canvas_setup'] = True
            elif requested_page == 'login':
                st.session_state['show_register'] = False
                st.session_state['show_canvas_setup'] = False
        
    # Show registration form if sign up was clicked
    if st.session_state.get('show_register'):
        st.subheader("📝 Create Your Account")
        
        # Show registration progress
        progress_style = """
        <style>
            .step-container { display: flex; justify-content: space-between; margin: 2em 0; }
            .step { text-align: center; flex: 1; }
            .step-number { 
                width: 30px; 
                height: 30px; 
                border-radius: 50%; 
                background: #f0f2f6;
                color: #666;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 0.5em;
            }
            .step.active .step-number { 
                background: #ff4b4b;
                color: white;
            }
            .step-label { font-size: 0.8em; color: #666; }
            .step.active .step-label { color: #ff4b4b; font-weight: bold; }
        </style>
        <div class="step-container">
            <div class="step active">
                <div class="step-number">1</div>
                <div class="step-label">Account Details</div>
            </div>
            <div class="step">
                <div class="step-number">2</div>
                <div class="step-label">Canvas Setup</div>
            </div>
            <div class="step">
                <div class="step-number">3</div>
                <div class="step-label">Ready!</div>
            </div>
        </div>
        """
        st.markdown(progress_style, unsafe_allow_html=True)
        
        with st.form("registration_form"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                username = st.text_input("Username", placeholder="Choose a username")
                password = st.text_input("Password", type="password", placeholder="Create a password")
                email = st.text_input("Email", placeholder="your.email@school.edu")
                
                # Canvas information
                st.subheader("Canvas Connection")
                canvas_url = st.text_input("Canvas URL", placeholder="https://your-school.instructure.com")
                canvas_token = st.text_input("Canvas API Token", type="password", 
                                         placeholder="Find in Canvas Settings → Approved Integrations")
                course_id = st.text_input("Course ID", placeholder="Found in your course URL")
            
            with col2:
                st.markdown("**Password Requirements:**")
                st.markdown("""
                - At least 8 characters
                - One uppercase letter
                - One lowercase letter
                - One number
                """)
                
                st.markdown("**Canvas Help:**")
                st.markdown("""
                1. Canvas URL: Your school's Canvas domain
                2. API Token: Generate in Canvas Settings
                3. Course ID: Found in course URL
                """)
            
            col3, col4 = st.columns(2)
            with col3:
                if st.form_submit_button("Create Account", use_container_width=True):
                    # Validate required fields including Canvas specifics
                    errors = []
                    if not all([username, password, email, canvas_url, canvas_token, course_id]):
                        errors.append("Please fill in all fields.")

                    ok, msg = validate_canvas_url(canvas_url)
                    if not ok:
                        errors.append(msg)

                    ok, msg = validate_canvas_token(canvas_token)
                    if not ok:
                        errors.append(msg)

                    ok, msg = validate_course_id(course_id)
                    if not ok:
                        errors.append(msg)

                    if errors:
                        for e in errors:
                            st.error(f"❌ {e}")
                    else:
                        success, message = create_user(username, password, email,
                                                      canvas_url, canvas_token, course_id)
                        if success:
                            # Attempt to sign the user in automatically so they see a clear
                            # success message and are redirected to the dashboard.
                            auth_success, user_data = authenticate_user(username, password)
                            if auth_success:
                                st.session_state['user'] = user_data
                                st.session_state['username'] = username
                                st.session_state['authenticated'] = True
                                st.session_state['show_register'] = False
                                st.success("🎉 Account created and signed in! Redirecting to dashboard...")
                                st.rerun()
                            else:
                                # Account created, but couldn't auto-authenticate.
                                st.session_state['show_register'] = False
                                st.success("🎉 Account created! Please sign in.")
                                st.rerun()
                        else:
                            st.error(f"❌ {message}")
            
            with col4:
                if st.form_submit_button("Back to Login", use_container_width=True):
                    # Pop the last page from navigation stack
                    if st.session_state['nav_stack']:
                        last_page = st.session_state['nav_stack'].pop()
                        st.session_state['current_page'] = last_page
                    else:
                        st.session_state['current_page'] = 'login'
                    
                    st.session_state['show_register'] = False
                    # Update URL to reflect the change
                    st.experimental_set_query_params(page='login')
                    st.rerun()
        return
        
    # Show Canvas setup form for new Google Sign-In users
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
                # Validate Canvas fields before updating
                v_errors = []
                ok, msg = validate_canvas_url(canvas_url)
                if not ok:
                    v_errors.append(msg)
                ok, msg = validate_canvas_token(canvas_token)
                if not ok:
                    v_errors.append(msg)
                ok, msg = validate_course_id(course_id)
                if not ok:
                    v_errors.append(msg)

                if v_errors:
                    for e in v_errors:
                        st.error(f"❌ {e}")
                else:
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
        return
    
    # Main authentication page (email/password only)
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Sign In")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Sign In", use_container_width=True):
            success, user_data = authenticate_user(username, password)
            if success:
                st.session_state['user'] = user_data
                # Store username in session so other pages can find it
                st.session_state['username'] = username
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
            # Add current page to navigation stack before changing
            st.session_state['nav_stack'].append(st.session_state['current_page'])
            st.session_state['current_page'] = 'register'
            st.session_state['show_register'] = True
            # Update URL to reflect the change
            st.experimental_set_query_params(page='register')
            st.rerun()