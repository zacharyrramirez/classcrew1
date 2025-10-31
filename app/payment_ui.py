"""
payment_ui.py
Payment interface for assignment grading.
"""

import os
import streamlit as st
import stripe

# Keep your utils import as-is for logging/legacy paths
from utils.payment_manager import create_checkout_session, confirm_payment, log_payment  # noqa: F401

# ---------- Safe config helpers ----------
def _cfg(name: str, default: str = "") -> str:
    # secrets -> env -> default; never KeyError
    return st.secrets.get(name, os.getenv(name, default)).strip()

APP_BASE_URL   = _cfg("APP_BASE_URL")
STRIPE_KEY     = _cfg("SECRET_KEY")
MONTHLY_PRICE  = _cfg("MONTHLY_PRICE_ID")  # e.g., price_1SO5WqCnlydO6yshTdB6uHMU

# Initialize Stripe only if key present; we’ll guard later too
if STRIPE_KEY:
    stripe.api_key = STRIPE_KEY

# ---------- Internal helpers ----------
def _require_config(*names):
    missing = [n for n in names if not _cfg(n)]
    if missing:
        st.error(f"Missing config: {', '.join(missing)}. Add them in Streamlit Secrets.")
        st.stop()

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
        if 'APP_BASE_URL' in st.secrets:
            return str(st.secrets['APP_BASE_URL']).rstrip('/')
    except Exception:
        pass

    # Env fallback
    base = os.getenv('APP_BASE_URL') or os.getenv('BASE_URL')
    if base:
        return base.rstrip("/")
    st.warning("APP_BASE_URL not configured. Using placeholder; update Streamlit Secrets.")
    return "https://your-app-name.streamlit.app"

def _create_monthly_checkout_session(success_url: str, cancel_url: str):
    # Uses Price ID for subscription; this is the correct Stripe pattern
    return stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": MONTHLY_PRICE, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        allow_promotion_codes=True,
        automatic_tax={"enabled": True},
    )

# ---------- Public API expected by streamlit_app.py ----------
def render_payment_required(assignment_id, user_id):
    """Render payment required screen"""
    st.title("💳 Choose Your Grading Plan")

    st.markdown(f"**Assignment ID:** {assignment_id}")
    st.markdown("**Service:** AI-Powered Assignment Grading")
    st.divider()

    col1, _ = st.columns(2)

    with col1:
        st.markdown("### 🚀 Monthly Unlimited")
        st.markdown("**$9.99 per month per class**")
        st.markdown(
            """
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
            """
        )

        # Use a form so the button doesn’t disappear on rerun
        with st.form("monthly_checkout"):
            submit = st.form_submit_button("🚀 Start $9.99/Month Plan", use_container_width=True)

        if submit:
            _require_config("APP_BASE_URL", "STRIPE_SECRET_KEY", "MONTHLY_PRICE_ID")
            base = _get_base_url()
            success_url = f"{base}/?payment=success&assignment={assignment_id}&user={user_id}&type=monthly_subscription"
            cancel_url  = f"{base}/?payment=cancelled&assignment={assignment_id}&user={user_id}"

            try:
                session = _create_monthly_checkout_session(success_url, cancel_url)
                # Give the browser a real link. No JS popups. No drama.
                st.link_button("Proceed to Secure Checkout", session.url, use_container_width=True)
            except Exception as e:
                st.error(f"Stripe error: {e}")

    st.divider()
    st.markdown(
        """
        ### 💡 Why Choose Our AI Grading?
        - **Save 3+ hours** of manual grading per assignment
        - **Consistent quality** without fatigue
        - **Detailed feedback** for every student
        - **Canvas integration** for posting grades
        - **Fairness review** by a second AI model
        """
    )

def _process_payment(assignment_id, user_id, amount_cents, payment_type):
    """Legacy path (kept for compatibility). Prefer monthly subscription above."""
    base = _get_base_url()
    success_url = f"{base}/?payment=success&assignment={assignment_id}&user={user_id}&type={payment_type}"
    cancel_url  = f"{base}/?payment=cancelled&assignment={assignment_id}&user={user_id}"

    # If someone calls this for subscriptions by mistake, steer them right
    if payment_type == "monthly_subscription":
        _require_config("APP_BASE_URL", "STRIPE_SECRET_KEY", "MONTHLY_PRICE_ID")
        try:
            session = _create_monthly_checkout_session(success_url, cancel_url)
            st.link_button("Proceed to Secure Checkout", session.url, use_container_width=True)
            return
        except Exception as e:
            st.error(f"Stripe error: {e}")
            return

    # Otherwise fall back to your utils one-time flow
    try:
        session = create_checkout_session(
            assignment_id, user_id, success_url, cancel_url, amount_cents, payment_type
        )
        if session:
            st.link_button("Proceed to Secure Checkout", session.url, use_container_width=True)
        else:
            st.error("Payment system error. Please try again.")
    except Exception as e:
        st.error(f"Payment error: {e}")

def render_payment_success(assignment_id, user_id, payment_type="monthly_subscription", amount=999):
    """Render payment success screen"""
    if payment_type == "monthly_subscription":
        st.success("🎉 Monthly subscription activated! Starting AI grading...")
        st.info("💡 Unlimited grading for this class for the next 30 days.")
    else:
        st.success("✅ Payment successful! Starting AI grading...")

    # Log and kick off grading
    try:
        log_payment(user_id, assignment_id, amount, "stripe_session", "completed", payment_type)
    except Exception:
        pass

    st.info("🤖 Initiating automatic AI grading process...")

    from canvas.client import CanvasClient
    from grader.workflows import grade_submissions
    from utils.file_ops import get_submission_status

    try:
        canvas = CanvasClient()
        submissions = canvas.get_submissions(assignment_id)
        rubric_items = canvas.get_rubric(assignment_id)
        if not rubric_items:
            st.error("❌ No rubric found for this assignment. Cannot proceed with grading.")
            return

        selected = []
        for sub in submissions:
            status = get_submission_status(sub)
            if status in ["On Time", "Late", "Resubmitted"]:
                sub["grading_status"] = status
                selected.append(sub)

        if not selected:
            st.warning("⚠️ No submissions found to grade.")
            return

        st.info(f"📝 Found {len(selected)} submissions to grade...")

        def stream_to_ui(msg):
            st.write(msg)

        with st.spinner("🔄 AI grading in progress..."):
            results_payload = grade_submissions(
                assignment_id=assignment_id,
                filter_by="submitted",
                stream_callback=stream_to_ui,
                external_submissions=selected,
            )

        st.session_state["grading_results"] = results_payload
        st.session_state["grading_logs"] = results_payload.get("logs", [])
        st.session_state["overrides"] = {}
        st.success("🎉 Grading complete! Review your results below.")
        if st.button("📋 Review Grading Results", type="primary"):
            st.rerun()

    except Exception as e:
        st.error(f"❌ Error during grading: {e}")
        st.info("Please try again or contact support if the issue persists.")

def render_payment_cancelled():
    st.warning("❌ Payment cancelled. You can try again anytime.")
    if st.button("🔄 Try Again"):
        st.rerun()

def check_payment_status(assignment_id, user_id):
    """Monthly-only: check active subscription for this user/class."""
    from utils.payment_manager import check_subscription_status

    try:
        return bool(check_subscription_status(user_id, assignment_id))
    except Exception as e:
        print(f"Subscription check failed: {e}")
        return False

def render_pricing_info():
    st.sidebar.markdown("### 💰 Pricing")
    st.sidebar.markdown(
        """
        🚀 **$9.99/month per class**
        - Unlimited assignments
        - Best value for active teachers
        - Save 50%+ vs per-assignment
        - AI grading
        - Detailed feedback
        - Rubric scoring
        - CSV export
        """
    )
