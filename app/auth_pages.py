"""
auth_pages.py
Authentication pages for login and registration.
"""

import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.auth_manager import create_user, authenticate_user, validate_password

def render_login_page():
    """Render the login page"""
    st.title("Classcrew AI Grader Login")
    st.markdown("Welcome! Please sign in to access your grading dashboard.")
    
    # Login form
    with st.form("login_form"):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Sign In")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            login_button = st.form_submit_button("Login", use_container_width=True)
        
        with col2:
            st.subheader("New Teacher?")
            st.markdown("""
            Create your account to get started with AI-powered grading:
            - Connect to your Canvas course
            - Grade assignments automatically
            - Review and post grades
            """)
            register_button = st.form_submit_button("Create Account", use_container_width=True)
        
        if login_button:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                success, user = authenticate_user(username, password)
                if success:
                    st.session_state['authenticated'] = True
                    st.session_state['user'] = user
                    st.session_state['username'] = username
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        if register_button:
            st.session_state['show_register'] = True
            st.rerun()

def render_register_page():
    """Render the registration page"""
    st.title("📝 Create Account")
    st.markdown("Set up your Classcrew AI Grader account to start grading assignments.")
    
    # Registration form
    with st.form("register_form"):
        st.subheader("Account Information")
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username", placeholder="Choose a username")
            password = st.text_input("Password", type="password", placeholder="Create a password")
            email = st.text_input("Email", placeholder="your.email@school.edu")
        
        with col2:
            st.markdown("**Password Requirements:**")
            st.markdown("""
            - At least 8 characters
            - One uppercase letter
            - One lowercase letter
            - One number
            """)
        
        st.subheader("Canvas Configuration")
        st.markdown("Connect to your Canvas course to grade assignments:")
        
        col3, col4 = st.columns(2)
        with col3:
            canvas_url = st.text_input("Canvas URL", placeholder="https://your-school.instructure.com")
            canvas_token = st.text_input("Canvas API Token", type="password", placeholder="Your Canvas API token")
        
        with col4:
            course_id = st.text_input("Course ID", placeholder="123456")
            st.markdown("""
            **Need help finding these?**
            - Canvas URL: Your school's Canvas domain
            - API Token: Account → Settings → Approved Integrations
            - Course ID: Found in the course URL
            """)
        
        col5, col6 = st.columns([1, 1])
        with col5:
            if st.form_submit_button("Create Account", use_container_width=True):
                # Validate input
                if not all([username, password, email, canvas_url, canvas_token, course_id]):
                    st.error("Please fill in all fields")
                else:
                    success, message = create_user(username, password, email, canvas_url, canvas_token, course_id)
                    if success:
                        st.success(message)
                        st.session_state['show_register'] = False
                        st.rerun()
                    else:
                        st.error(message)
        
        with col6:
            if st.form_submit_button("Back to Login", use_container_width=True):
                st.session_state['show_register'] = False
                st.rerun()

def render_account_settings():
    """Render account settings page"""
    st.title("⚙️ Account Settings")
    
    user = st.session_state['user']
    username = st.session_state['username']
    
    st.markdown(f"**Logged in as:** {username}")
    st.markdown(f"**Email:** {user['email']}")
    st.markdown(f"**Account created:** {user['created_at'][:10]}")
    
    if user.get('last_login'):
        st.markdown(f"**Last login:** {user['last_login'][:19]}")
    
    st.divider()
    
    # Canvas settings update form
    with st.form("update_canvas_form"):
        st.subheader("Canvas Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            canvas_url = st.text_input("Canvas URL", value=user['canvas_url'])
            # Support multiple courses: comma-separated list
            existing_ids = user.get('course_ids') or ([] if not user.get('course_id') else [user.get('course_id')])
            course_ids_input = st.text_input("Course IDs (comma-separated)", value=", ".join(existing_ids))
        
        with col2:
            canvas_token = st.text_input("Canvas API Token", value="••••••••", type="password", 
                                       help="Leave blank to keep current token")
            # Active course selector
            try:
                parsed_ids = [c.strip() for c in (course_ids_input or '').split(',') if c.strip()]
            except Exception:
                parsed_ids = []
            active_default = user.get('course_id') or (parsed_ids[0] if parsed_ids else "")
            active_course = st.selectbox("Active Course", options=[active_default] + [c for c in parsed_ids if c != active_default])
        
        if st.form_submit_button("Update Canvas Settings"):
            from utils.auth_manager import update_user_canvas, update_user_courses

            # If token is masked, don't update it
            if canvas_token == "••••••••":
                canvas_token = user['canvas_token']

            # Update Canvas base settings and courses
            # First update canvas URL/token and store courses (comma-supported in update_user_canvas)
            success, message = update_user_canvas(username, canvas_url, canvas_token, course_ids_input)
            if success:
                # Then ensure active course is saved
                success2, message2 = update_user_courses(username, parsed_ids, active_course)
                if success2:
                    st.success("Canvas settings updated successfully")
                    # Update session state
                    st.session_state['user']['canvas_url'] = canvas_url
                    st.session_state['user']['canvas_token'] = canvas_token
                    st.session_state['user']['course_id'] = active_course
                    st.session_state['user']['course_ids'] = parsed_ids
                    st.rerun()
                else:
                    st.error(message2)
            else:
                st.error(message)
    
    st.divider()
    
    # Logout button
    if st.button("Logout", type="secondary"):
        st.session_state['authenticated'] = False
        st.session_state['user'] = None
        st.session_state['username'] = None
        st.success("Logged out successfully!")
        st.rerun()
