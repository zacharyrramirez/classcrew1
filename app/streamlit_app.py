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
    user = st.session_state.get('user') or {}
    # username may not always be set (defensive). Prefer session username, fallback to user email or uid.
    username = st.session_state.get('username') or user.get('email') or user.get('uid') or 'unknown_user'
    
    # Check if there's a pending payment success after login
    if 'payment_success' in st.session_state:
        payment_info = st.session_state['payment_success']
        assignment_id = payment_info['assignment_id']
        
        # Clear the payment success flag
        del st.session_state['payment_success']
        
        # Show payment success and start grading
        st.success("✅ Payment successful! Starting AI grading...")
        
        # Import the payment success function
        from app.payment_ui import render_payment_success
        print(f"DEBUG: Payment success for user={username}, assignment={assignment_id}")
        render_payment_success(assignment_id, username)
        return
    
    # Set environment variables for this user's Canvas
    os.environ['CANVAS_API_URL'] = user['canvas_url']
    os.environ['CANVAS_API_KEY'] = user['canvas_token']
    os.environ['CANVAS_COURSE_ID'] = user['course_id']
    
    # Set AI service keys (you provide these)
    # These would be your API keys that you manage
    # Don't override if already set
    if not os.getenv('OPENAI_API_KEY'):
        os.environ['OPENAI_API_KEY'] = 'your-openai-key'
    if not os.getenv('GEMINI_API_KEY'):
        os.environ['GEMINI_API_KEY'] = 'your-gemini-key'
    
    # Show main app with user context
    if st.session_state['show_settings']:
        render_account_settings()
        return
    
    # Sidebar with user info and navigation
    with st.sidebar:
        st.markdown(f"### Welcome, {username}!")
        st.markdown(f"**Course:** {user['course_id']}")
        st.markdown(f"**Canvas:** {user['canvas_url'].split('//')[1].split('.')[0]}")
        
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
            st.rerun()
    
    # Check for payment status in URL parameters
    payment_status = st.query_params.get('payment')
    assignment_id_param = st.query_params.get('assignment')
    user_id_param = st.query_params.get('user')
    payment_type_param = st.query_params.get('type', 'per_assignment')
    
    if payment_status == 'success' and assignment_id_param and user_id_param:
        # Determine amount based on payment type
        amount = 199 if payment_type_param == 'per_assignment' else 999
        
        # Log the payment and start grading immediately
        from utils.payment_manager import log_payment
        log_payment(user_id_param, assignment_id_param, amount, "stripe_session", "completed", payment_type_param)
        
        # Store payment success info
        st.session_state['payment_success'] = {
            'assignment_id': assignment_id_param,
            'status': 'success',
            'payment_type': payment_type_param,
            'amount': amount
        }
        
        # Show success message and start grading
        if payment_type_param == 'monthly_subscription':
            st.success("🎉 Monthly subscription activated! Starting AI grading...")
            st.info("💡 You now have unlimited grading for this class for the next 30 days!")
        else:
            st.success("✅ Payment successful! Starting AI grading...")
        
        # Import the payment success function
        from app.payment_ui import render_payment_success
        render_payment_success(assignment_id_param, user_id_param, payment_type_param, amount)
        return
        
    elif payment_status == 'cancelled':
        st.session_state['payment_cancelled'] = True
        st.warning("❌ Payment cancelled. You can try again anytime.")
        return
    
    # Main app content
    st.title("Classcrew AI Grader")
    st.markdown("Select an assignment to grade using AI-powered assessment.")
    
    # Assignment selection UI and rubric preview
    assignment_id, rubric_items, assignment_options, submission_filter, filtered_submissions = render_assignment_selection()
    
    # If an assignment is selected, check payment status
    if assignment_id and rubric_items is not None:
        # Check if user has paid for this assignment
        if not check_payment_status(assignment_id, username):
            render_payment_required(assignment_id, username)
        else:
            render_grading_section(assignment_id, rubric_items, assignment_options, submission_filter=submission_filter, filtered_submissions=filtered_submissions)

if __name__ == "__main__":
    main()