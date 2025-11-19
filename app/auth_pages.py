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
    """Render account settings page with course management"""
    st.title("⚙️ Account Settings")
    
    user = st.session_state['user']
    username = st.session_state['username']
    
    st.markdown(f"**Logged in as:** {username}")
    st.markdown(f"**Email:** {user['email']}")
    st.markdown(f"**Account created:** {user['created_at'][:10]}")
    
    if user.get('last_login'):
        st.markdown(f"**Last login:** {user['last_login'][:19]}")
    
    st.divider()
    
    # Course Management Section
    st.subheader("📚 Canvas Course Management")
    
    from utils.auth_manager import get_user_courses, add_user_course, update_user_course, delete_user_course, set_active_course
    
    # Load courses
    courses = get_user_courses(username)
    active_course_id = user.get('course_id', '')
    
    # Initialize session state for editing
    if 'editing_course' not in st.session_state:
        st.session_state['editing_course'] = None
    if 'show_add_course' not in st.session_state:
        st.session_state['show_add_course'] = False
    
    # Course selector
    if courses:
        course_options = {f"{c.get('name', 'Unnamed')} (ID: {c.get('id', '')})": c.get('id') for c in courses}
        current_label = next((label for label, cid in course_options.items() if cid == active_course_id), list(course_options.keys())[0] if course_options else None)
        
        selected_label = st.selectbox(
            "🎯 Active Course",
            options=list(course_options.keys()),
            index=list(course_options.keys()).index(current_label) if current_label in course_options.keys() else 0,
            help="Select which course to use for grading"
        )
        
        selected_course_id = course_options[selected_label]
        
        # Update active course if changed
        if selected_course_id != active_course_id:
            success, msg = set_active_course(username, selected_course_id)
            if success:
                st.session_state['user']['course_id'] = selected_course_id
                # Update session course data
                selected_course = next((c for c in courses if c.get('id') == selected_course_id), None)
                if selected_course:
                    st.session_state['user']['canvas_url'] = selected_course.get('canvas_url', '')
                    st.session_state['user']['canvas_token'] = selected_course.get('canvas_token', '')
                st.success(f"Switched to {selected_label}")
                st.rerun()
            else:
                st.error(msg)
    else:
        st.info("No courses configured. Add your first course below.")
    
    st.markdown("---")
    
    # Add new course button
    col_add, col_space = st.columns([1, 3])
    with col_add:
        if st.button("➕ Add New Course", use_container_width=True):
            st.session_state['show_add_course'] = True
            st.session_state['editing_course'] = None
    
    # Add course form
    if st.session_state.get('show_add_course', False):
        with st.form("add_course_form"):
            st.subheader("Add New Course")
            col1, col2 = st.columns(2)
            with col1:
                new_course_name = st.text_input("Course Name", placeholder="e.g., CS 101 Fall 2025")
                new_course_id = st.text_input("Canvas Course ID", placeholder="123456")
            with col2:
                new_canvas_url = st.text_input("Canvas URL", placeholder="https://school.instructure.com")
                new_canvas_token = st.text_input("Canvas API Token", type="password", placeholder="Your token")
            
            col_submit, col_cancel = st.columns(2)
            with col_submit:
                if st.form_submit_button("✅ Add Course", use_container_width=True):
                    if all([new_course_name, new_course_id, new_canvas_url, new_canvas_token]):
                        success, msg = add_user_course(username, new_course_name, new_course_id, new_canvas_url, new_canvas_token)
                        if success:
                            st.success(msg)
                            st.session_state['show_add_course'] = False
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("Please fill in all fields")
            with col_cancel:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state['show_add_course'] = False
                    st.rerun()
    
    # Display existing courses with edit/delete
    if courses:
        st.markdown("### Your Courses")
        for course in courses:
            course_id = course.get('id', '')
            course_name = course.get('name', 'Unnamed Course')
            is_active = course_id == active_course_id
            
            with st.expander(f"{'🌟 ' if is_active else ''}  {course_name} (ID: {course_id})", expanded=(st.session_state.get('editing_course') == course_id)):
                # Show course details
                st.markdown(f"**Canvas URL:** {course.get('canvas_url', 'Not set')}")
                st.markdown(f"**Course ID:** {course_id}")
                if course.get('created_at'):
                    st.markdown(f"**Added:** {course['created_at'][:10]}")
                
                # Edit mode
                if st.session_state.get('editing_course') == course_id:
                    with st.form(f"edit_course_{course_id}"):
                        st.markdown("#### Edit Course")
                        edit_name = st.text_input("Course Name", value=course_name)
                        edit_url = st.text_input("Canvas URL", value=course.get('canvas_url', ''))
                        edit_token = st.text_input("Canvas API Token (leave blank to keep current)", type="password", placeholder="••••••••")
                        
                        col_save, col_cancel_edit = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                                token_update = edit_token if edit_token and edit_token != "••••••••" else None
                                success, msg = update_user_course(username, course_id, edit_name, edit_url, token_update)
                                if success:
                                    st.success(msg)
                                    st.session_state['editing_course'] = None
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with col_cancel_edit:
                            if st.form_submit_button("❌ Cancel", use_container_width=True):
                                st.session_state['editing_course'] = None
                                st.rerun()
                else:
                    col_edit, col_delete = st.columns(2)
                    with col_edit:
                        if st.button(f"✏️ Edit", key=f"edit_{course_id}", use_container_width=True):
                            st.session_state['editing_course'] = course_id
                            st.session_state['show_add_course'] = False
                            st.rerun()
                    with col_delete:
                        if st.button(f"🗑️ Delete", key=f"delete_{course_id}", use_container_width=True, type="secondary"):
                            if len(courses) == 1:
                                st.error("Cannot delete your only course. Add another course first.")
                            else:
                                success, msg = delete_user_course(username, course_id)
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
    
    st.divider()
    
    # Logout button
    if st.button("🚪 Logout", type="secondary"):
        st.session_state['authenticated'] = False
        st.session_state['user'] = None
        st.session_state['username'] = None
        st.session_state['editing_course'] = None
        st.session_state['show_add_course'] = False
        st.success("Logged out successfully!")
        st.rerun()
