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
# Prefer standard Stripe key names and nested secrets fallback
STRIPE_KEY     = (_cfg("STRIPE_SECRET_KEY") or _cfg("STRIPE_API_KEY") or
                  (st.secrets.get("stripe", {}).get("secret_key", "").strip() if hasattr(st, 'secrets') else ""))
# Prefer MONTHLY_PRICE_ID, but accept common aliases
MONTHLY_PRICE  = (_cfg("MONTHLY_PRICE_ID") or _cfg("STRIPE_PRICE_ID") or
                  (st.secrets.get("stripe", {}).get("price_id", "").strip() if hasattr(st, 'secrets') else ""))  # e.g., price_...

# Initialize Stripe only if key present; we’ll guard later too
if STRIPE_KEY:
    stripe.api_key = STRIPE_KEY

# ---------- Internal helpers ----------
def _require_payment_config():
    """Validate payment config with sensible alternatives and helpful messaging."""
    missing: list[str] = []

    # Base URL can come from APP_BASE_URL, BASE_URL, or [app].base_url
    base = (APP_BASE_URL or _cfg("BASE_URL") or
            (st.secrets.get('app', {}).get('base_url', '').strip() if hasattr(st, 'secrets') else ""))
    if not base:
        missing.append("APP_BASE_URL or BASE_URL")

    # Stripe key should be present under standard keys
    if not STRIPE_KEY:
        missing.append("STRIPE_SECRET_KEY")

    # Price ID must be a Stripe Price (price_...)
    if not MONTHLY_PRICE:
        missing.append("MONTHLY_PRICE_ID")

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
    if STRIPE_KEY and not getattr(stripe, 'api_key', None):
        stripe.api_key = STRIPE_KEY
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
            _require_payment_config()
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
        _require_payment_config()
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
    """Render payment success screen without auto-starting grading.

    Allows the user to return to the dashboard or explicitly start grading.
    """
    if payment_type == "monthly_subscription":
        st.success("🎉 Monthly subscription activated!")
        st.info("💡 Unlimited grading for this class for the next 30 days.")
    else:
        st.success("✅ Payment successful!")

    # Log payment completion (Firestore)
    try:
        log_payment(user_id, assignment_id, amount, "stripe_session", "completed", payment_type)
    except Exception:
        pass

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        start_now = st.button("🚀 Start grading now", type="primary", use_container_width=True)
    with col_b:
        back = st.button("🏠 Back to dashboard", use_container_width=True)

    if back and not start_now:
        # Return to main app (assignment selection page)
        st.rerun()

    if not start_now:
        # Do not auto-start grading
        return

    # Proceed with grading only when explicitly requested
    from canvas.client import CanvasClient
    from grader.workflows import grade_submissions
    from utils.file_ops import get_submission_status

    try:
        canvas = CanvasClient()
        rubric_items = canvas.get_rubric(assignment_id)
        if not rubric_items:
            st.error("❌ No rubric found for this assignment. Please add a rubric in Canvas, then start grading.")
            return

        submissions = canvas.get_submissions(assignment_id)
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

        # Progress-driven streaming UI (single line + progress bar)
        class ProgressStreamer:
            def __init__(self):
                self._status = st.empty()
                try:
                    self._bar = st.progress(0)
                except Exception:
                    self._bar = None
                self._last_msg = ""

            def __call__(self, msg: str):
                self._last_msg = str(msg)
                self._status.markdown(f"⬇️ {self._last_msg}")

            def update_progress(self, current: int, total: int):
                pct = 100 if total == 0 else int((current / max(total, 1)) * 100)
                if self._bar:
                    try:
                        self._bar.progress(min(max(pct, 0), 100))
                    except Exception:
                        pass
                self._status.markdown(f"🔄 {self._last_msg} — {current}/{total} done")

            def finish(self):
                if self._bar:
                    try:
                        self._bar.progress(100)
                    except Exception:
                        pass
                self._status.markdown("✅ Grading complete.")

        with st.spinner("🔄 AI grading in progress..."):
            streamer = ProgressStreamer()
            results_payload = grade_submissions(
                assignment_id=assignment_id,
                filter_by="submitted",
                stream_callback=streamer,
                external_submissions=selected,
            )
            streamer.finish()

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
