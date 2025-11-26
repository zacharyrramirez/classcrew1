# app/streamlit_app.py

import streamlit as st
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# initialize firebase clients (side-effect)
import utils.firebase as firebase

from ui_assignment import render_assignment_selection
from ui_grading import render_grading_section
from auth_ui import auth_page
from auth_pages import render_account_settings
from payment_ui import render_payment_required, render_payment_success, render_payment_cancelled, check_payment_status, render_pricing_info
from utils.auth_manager import get_user_courses, set_active_course

def main():
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'show_register' not in st.session_state:
        st.session_state['show_register'] = False
    if 'show_settings' not in st.session_state:
        st.session_state['show_settings'] = False
    if 'last_activity' not in st.session_state:
        st.session_state['last_activity'] = time.time()
    
    # Check for session timeout (2 hours)
    if time.time() - st.session_state['last_activity'] > 7200:
        st.session_state['authenticated'] = False
        st.warning("Session expired. Please log in again.")
        st.rerun()
    
    st.session_state['last_activity'] = time.time()
    
    # Show appropriate page based on authentication status
    if not st.session_state['authenticated']:
        auth_page()  # This handles both login and registration
        return
    
    # User is authenticated - show main app
    user = st.session_state.get('user', {})
    # Ensure we have a username, falling back through several options
    username = (st.session_state.get('username') or 
               user.get('email') or 
               user.get('username') or 
               user.get('uid') or 
               'unknown_user')
               
    # Ensure user dictionary has all required fields with defaults
    user = {
        'canvas_url': user.get('canvas_url', ''),
        'canvas_token': user.get('canvas_token', ''),
        'course_id': user.get('course_id', ''),
        **user  # Preserve any other existing fields
    }
    
    # Check if there's a pending payment success after login
    if 'payment_success' in st.session_state:
        payment_info = st.session_state['payment_success']
        assignment_id = payment_info['assignment_id']
        paid_user_id = payment_info.get('user_id')
        
        # Clear the payment success flag
        del st.session_state['payment_success']
        
        # Only show success for the user who paid
        if paid_user_id and str(paid_user_id) != str(username):
            st.info("Payment success detected for a different account. Please sign in as the paying user or start grading from that account.")
            # Best-effort clear of URL params to prevent loops
            try:
                st.query_params.clear()
            except Exception:
                pass  # If clearing fails, continue anyway
            return
        
        # Import the payment success function (handles its own messaging)
        from app.payment_ui import render_payment_success
        print(f"DEBUG: Payment success for user={username}, assignment={assignment_id}")
        render_payment_success(assignment_id, username, payment_info.get('payment_type', 'monthly_subscription'), payment_info.get('amount', 999))
        return
    
    # Set environment variables for this user's Canvas (from active course)
    courses = get_user_courses(username)
    active_course_id = user.get('course_id', '')
    active_course = next((c for c in courses if c.get('id') == active_course_id), None)
    
    if active_course:
        os.environ['CANVAS_API_URL'] = active_course.get('canvas_url', '')
        os.environ['CANVAS_API_KEY'] = active_course.get('canvas_token', '')
        os.environ['CANVAS_COURSE_ID'] = active_course.get('id', '')
    else:
        # Fallback to old fields if courses not migrated yet
        os.environ['CANVAS_API_URL'] = user.get('canvas_url', '')
        os.environ['CANVAS_API_KEY'] = user.get('canvas_token', '')
        os.environ['CANVAS_COURSE_ID'] = user.get('course_id', '')
    
    # Set AI service keys (you provide these)
    # These would be your API keys that you manage
    # Validate that required API keys are configured
    if not os.getenv('OPENAI_API_KEY'):
        st.error("❌ OPENAI_API_KEY not configured. Please add to Streamlit Secrets.")
        st.info("Add to .streamlit/secrets.toml: OPENAI_API_KEY = \"your-key\"")
        st.stop()
    if not os.getenv('GEMINI_API_KEY'):
        st.error("❌ GEMINI_API_KEY not configured. Please add to Streamlit Secrets.")
        st.info("Add to .streamlit/secrets.toml: GEMINI_API_KEY = \"your-key\"")
        st.stop()
    
    # Show main app with user context
    if st.session_state['show_settings']:
        render_account_settings()
        return
    
    # Sidebar with user info and navigation
    with st.sidebar:
        st.markdown(f"### Welcome, {username}!")
        # Allow switching among multiple courses if configured
        courses = get_user_courses(username)
        active_course_id = user.get('course_id', '')
        
        if courses:
            course_options = {f"{c.get('name', 'Unnamed')} (ID: {c.get('id', '')})": c.get('id') for c in courses}
            current_label = next((label for label, cid in course_options.items() if cid == active_course_id), list(course_options.keys())[0] if course_options else None)
            
            selected_label = st.selectbox(
                "🎯 Active Course",
                options=list(course_options.keys()),
                index=list(course_options.keys()).index(current_label) if current_label in course_options.keys() else 0
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
                        # Update env for Canvas client
                        os.environ['CANVAS_API_URL'] = selected_course.get('canvas_url', '')
                        os.environ['CANVAS_API_KEY'] = selected_course.get('canvas_token', '')
                        os.environ['CANVAS_COURSE_ID'] = selected_course_id
                    st.rerun()
        else:
            st.warning("No courses configured")
        
        # Safely parse and display Canvas URL
        canvas_url = user.get('canvas_url', '')
        try:
            # Only try to parse if we have a URL
            if '//' in canvas_url:
                canvas_display = canvas_url.split('//')[1].split('.')[0]
            else:
                canvas_display = 'Not set'
        except (IndexError, AttributeError):
            canvas_display = 'Invalid URL'
            
        st.markdown(f"**Canvas:** {canvas_display}")
        
        # Show subscription status
        from utils.payment_manager import get_user_subscription_info
        subscriptions = get_user_subscription_info(username)
        if subscriptions:
            st.markdown("### 🚀 Active Subscriptions")
            for sub in subscriptions:
                st.markdown(f"**Class {sub['assignment_id']}**")
                st.markdown(f"⏰ {sub['days_remaining']} days remaining")
                st.markdown("---")
        
        # Show pricing info
        render_pricing_info()
        
        if st.button("⚙️ Account Settings"):
            st.session_state['show_settings'] = True
            st.rerun()
        
        if st.button("🚪 Logout"):
            st.session_state['authenticated'] = False
            st.session_state['user'] = None
            st.session_state['username'] = None
            st.session_state['show_settings'] = False
            # Clear cached data to avoid cross-account leakage of Canvas data
            try:
                st.cache_data.clear()
            except Exception:
                pass
            st.rerun()
    
    # Check for payment status in URL parameters
    payment_status = st.query_params.get('payment')
    # Prefer new 'course' param; fall back to legacy 'assignment'
    course_id_param = st.query_params.get('course')
    assignment_id_param = st.query_params.get('assignment')
    id_param = course_id_param or assignment_id_param
    user_id_param = st.query_params.get('user')
    # Only monthly subscription is supported now
    payment_type_param = st.query_params.get('type', 'monthly_subscription')

    if payment_status == 'success' and id_param and user_id_param:
        # Amount is fixed to monthly subscription pricing
        amount = 999
        
        # Store payment success info (rendered once in the top handler)
        st.session_state['payment_success'] = {
            'assignment_id': id_param,
            'status': 'success',
            'payment_type': payment_type_param,
            'amount': amount,
            'user_id': user_id_param
        }
        # Clear payment query params to avoid repeating across users/sessions
        try:
            st.query_params.clear()
        except Exception:
            pass  # If clearing fails, continue anyway
        st.rerun()
        return
        
    elif payment_status == 'cancelled':
        st.session_state['payment_cancelled'] = True
        st.warning("❌ Payment cancelled. You can try again anytime.")
        # Clear payment query params to avoid repeating across users/sessions
        try:
            st.query_params.clear()
        except Exception:
            pass  # If clearing fails, continue anyway
        return
    
    # Main app content
    st.title("Classcrew AI Grader")
    st.markdown("Select an assignment to grade using AI-powered assessment.")
    
    # Assignment selection UI and rubric preview
    assignment_id, rubric_items, assignment_options, submission_filter, filtered_submissions = render_assignment_selection()
    
    # If an assignment is selected, check payment status for the CURRENT COURSE
    if assignment_id and rubric_items is not None:
        current_course_id = user.get('course_id')
        # Fallback: if course_id missing, use assignment_id to avoid blocking
        class_scope_id = current_course_id or assignment_id
        # Check if user has paid for this course/class
        if not check_payment_status(class_scope_id, username):
            render_payment_required(class_scope_id, username)
        else:
            render_grading_section(assignment_id, rubric_items, assignment_options, submission_filter=submission_filter, filtered_submissions=filtered_submissions)

if __name__ == "__main__":
    main()