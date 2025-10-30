"""
payment_ui.py
Payment interface for assignment grading.
"""

import streamlit as st
import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.payment_manager import create_checkout_session, confirm_payment, log_payment


def _get_base_url() -> str:
    """Resolve the app's base URL for redirects.

    Priority:
    - st.secrets['app']['base_url'] or st.secrets['BASE_URL']
    - env var APP_BASE_URL or BASE_URL
    - fallback to current Streamlit app URL (not reliably available), so default to streamlit.app placeholder
    """
    # Prefer Streamlit secrets
    try:
        if 'app' in st.secrets and 'base_url' in st.secrets['app']:
            return st.secrets['app']['base_url'].rstrip('/')
        if 'BASE_URL' in st.secrets:
            return str(st.secrets['BASE_URL']).rstrip('/')
    except Exception:
        pass

    # Env fallback
    base = os.getenv('APP_BASE_URL') or os.getenv('BASE_URL')
    if base:
        return base.rstrip('/')

    # Final fallback: ask user to configure, but return a sensible placeholder
    st.warning("BASE_URL not configured. Set [app].base_url in Streamlit secrets to build Stripe return URLs.")
    return "https://your-app-name.streamlit.app"

def render_payment_required(assignment_id, user_id):
    """Render payment required screen"""
    st.title("💳 Choose Your Grading Plan")
    
    st.markdown(f"**Assignment ID:** {assignment_id}")
    st.markdown("**Service:** AI-Powered Assignment Grading")
    
    st.divider()
    
    # Create two columns for pricing options
    col1, col2 = st.columns(2)
    
    
    with col1:
        st.markdown("### 🚀 Monthly Unlimited")
        st.markdown("**$9.99 per month per class**")
        st.markdown("""
        **Perfect for:**
        - Regular grading
        - Multiple assignments
        - Best value for active teachers
        
        **What you get:**
        - **Unlimited assignments** for this class
        - All premium features included
        - Save 50%+ vs per-assignment pricing
        - Cancel anytime
        - Priority support
        """)
        
        # Monthly subscription button
        if st.button("🚀 Start $9.99/Month Plan", type="secondary", use_container_width=True):
            _process_payment(assignment_id, user_id, 999, "monthly_subscription")
    
    st.divider()
    
    # Value proposition
    st.markdown("""
    ### 💡 Why Choose Our AI Grading?
    - **Save 3+ hours** of manual grading per assignment
    - **Consistent quality** - no grading fatigue
    - **Detailed feedback** for every student
    - **Canvas integration** - grades posted automatically
    - **Fairness review** by second AI model
    """)

def _process_payment(assignment_id, user_id, amount_cents, payment_type):
    """Process payment for either per-assignment or monthly subscription"""
    # Create Stripe checkout session
    base = _get_base_url()
    success_url = f"{base}/?payment=success&assignment={assignment_id}&user={user_id}&type={payment_type}"
    cancel_url = f"{base}/?payment=cancelled&assignment={assignment_id}&user={user_id}"
    
    session = create_checkout_session(assignment_id, user_id, success_url, cancel_url, amount_cents, payment_type)
    
    if session:
        # Store session info for later verification
        st.session_state['pending_payment'] = {
            'session_id': session.id,
            'assignment_id': assignment_id,
            'user_id': user_id,
            'payment_type': payment_type,
            'amount': amount_cents
        }
        
        # Use Streamlit components to create popup functionality
        import streamlit.components.v1 as components
        
        # Create HTML component with JavaScript for popup
        popup_html = f"""
        <script>
        function openPaymentPopup() {{
            const popup = window.open(
                '{session.url}',
                'stripe-checkout',
                'width=600,height=700,scrollbars=yes,resizable=yes,top=100,left=100'
            );
            
            // Check if popup was blocked
            if (!popup || popup.closed || typeof popup.closed == 'undefined') {{
                alert('Popup was blocked. Please allow popups for this site and try again.');
                return;
            }}
            
            // Monitor the popup
            const checkClosed = setInterval(() => {{
                if (popup.closed) {{
                    clearInterval(checkClosed);
                    // Popup was closed, reload the page to check payment status
                    window.parent.location.reload();
                }}
            }}, 1000);
            
            // Focus the popup
            popup.focus();
        }}
        
        // Open the popup immediately when this component loads
        window.addEventListener('load', openPaymentPopup);
        </script>
        <div style="text-align: center; padding: 20px;">
            <p>Opening secure payment window...</p>
            <button onclick="openPaymentPopup()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">
                Open Payment Window
            </button>
        </div>
        """
        
        st.success("✅ Payment session created!")
        st.info("""
        **Payment window will open automatically...** 
        
        Complete your payment in the popup window. Once payment is successful, the window will close automatically and this page will refresh to start grading your assignment.
        """)
        
        # Render the HTML component
        components.html(popup_html, height=100)
        
    else:
        st.error("Payment system error. Please try again.")

def render_payment_success(assignment_id, user_id, payment_type="monthly_subscription", amount=999):
    """Render payment success screen"""
    if payment_type == "monthly_subscription":
        st.success("🎉 Monthly subscription activated! Starting AI grading...")
        st.info("💡 You now have unlimited grading for this class for the next 30 days!")
    else:
        st.success("✅ Payment successful! Starting AI grading...")
    
    # Log the payment with debugging
    print(f"DEBUG: Logging payment for user={user_id}, assignment={assignment_id}, type={payment_type}, amount={amount}")
    log_payment(user_id, assignment_id, amount, "stripe_session", "completed", payment_type)
    
    # Start automatic grading
    st.info("🤖 Initiating automatic AI grading process...")
    
    # Import grading components
    from canvas.client import CanvasClient
    from grader.workflows import grade_submissions
    from utils.file_ops import get_submission_status
    
    try:
        # Get Canvas client and load assignment data
        canvas = CanvasClient()
        
        # Get all submissions for this assignment
        submissions = canvas.get_submissions(assignment_id)
        rubric_items = canvas.get_rubric(assignment_id)
        
        if not rubric_items:
            st.error("❌ No rubric found for this assignment. Cannot proceed with grading.")
            return
        
        # Filter submissions to grade (only submitted ones)
        selected_subs = []
        for sub in submissions:
            status = get_submission_status(sub)
            if status in ["On Time", "Late", "Resubmitted"]:
                sub["grading_status"] = status
                selected_subs.append(sub)
        
        if not selected_subs:
            st.warning("⚠️ No submissions found to grade.")
            return
        
        st.info(f"📝 Found {len(selected_subs)} submissions to grade...")
        
        # Define stream callback for UI updates
        def stream_to_ui(msg):
            st.write(msg)
        
        # Start grading process
        with st.spinner("🔄 AI grading in progress... Please wait..."):
            results_payload = grade_submissions(
                assignment_id=assignment_id,
                filter_by="submitted",
                stream_callback=stream_to_ui,
                external_submissions=selected_subs
            )
        
        # Store results in session state
        st.session_state["grading_results"] = results_payload
        st.session_state["grading_logs"] = results_payload.get("logs", [])
        st.session_state["overrides"] = {}
        
        st.success("🎉 Grading complete! Review your results below.")
        
        # Show a button to continue to review
        if st.button("📋 Review Grading Results", type="primary"):
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Error during grading: {str(e)}")
        st.info("Please try again or contact support if the issue persists.")

def render_payment_cancelled():
    """Render payment cancelled screen"""
    st.warning("❌ Payment cancelled. You can try again anytime.")
    
    if st.button("🔄 Try Again"):
        st.rerun()

def check_payment_status(assignment_id, user_id):
    """Check if user has paid for this assignment (either per-assignment or subscription)"""
    from utils.payment_manager import check_subscription_status

    print(f"DEBUG: Checking subscription status for user={user_id}, assignment={assignment_id}")

    # Only monthly subscriptions are supported now. Check subscription status in payment manager.
    try:
        if check_subscription_status(user_id, assignment_id):
            print(f"DEBUG: Active monthly subscription found for user {user_id}")
            return True
        else:
            print(f"DEBUG: No active subscription found for user {user_id}")
            return False
    except Exception as e:
        print(f"Warning: subscription check failed: {e}")
        return False

def render_pricing_info():
    """Render pricing information"""
    st.sidebar.markdown("### 💰 Pricing")
    st.sidebar.markdown("""
    
    
    🚀 **$9.99/month per class**
    - Unlimited assignments
    - Best value for active teachers
    - Save 50%+ vs per-assignment
    - AI grading
    - Detailed feedback
    - Rubric scoring
    - Fairness review
    - CSV export
    """)
