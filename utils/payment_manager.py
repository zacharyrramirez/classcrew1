"""
payment_manager.py
Handles Stripe payments for assignment grading.
"""

import stripe
import os
import json
from datetime import datetime
from datetime import timedelta
import time

# Initialize Stripe (prefer Streamlit secrets if available)
_stripe_key = None
_stripe_price_id = None
try:
    # Lazy import streamlit so non-Streamlit contexts still work
    import streamlit as st  # type: ignore
    if hasattr(st, 'secrets'):
        # Support both nested and flat secrets
        if 'stripe' in st.secrets and 'secret_key' in st.secrets['stripe']:
            _stripe_key = st.secrets['stripe']['secret_key']
        elif 'STRIPE_SECRET_KEY' in st.secrets:
            _stripe_key = st.secrets['STRIPE_SECRET_KEY']
        elif 'STRIPE_API_KEY' in st.secrets:
            # Backward/alternate naming compatibility
            _stripe_key = st.secrets['STRIPE_API_KEY']
        # Optional pre-created Price ID for subscriptions
        if 'stripe' in st.secrets and 'price_id' in st.secrets['stripe']:
            _stripe_price_id = st.secrets['stripe']['price_id']
        elif 'STRIPE_PRICE_ID' in st.secrets:
            _stripe_price_id = st.secrets['STRIPE_PRICE_ID']
        elif 'MONTHLY_PRICE_ID' in st.secrets:
            # Alternate naming some setups use
            _stripe_price_id = st.secrets['MONTHLY_PRICE_ID']
except Exception:
    # Ignore if streamlit is not available
    pass

if not _stripe_key:
    _stripe_key = os.getenv('STRIPE_SECRET_KEY') or os.getenv('STRIPE_API_KEY')
if not _stripe_price_id:
    _stripe_price_id = os.getenv('STRIPE_PRICE_ID') or os.getenv('MONTHLY_PRICE_ID')

stripe.api_key = _stripe_key

if not stripe.api_key:
    # Helpful diagnostics in logs without crashing
    print("Warning: STRIPE_SECRET_KEY not configured. Payments will fail until set.")

# Optional Firestore integration (if Firebase Admin is initialized)
try:
    from . import firebase as firebase_utils
except Exception:
    # Fallback if package import fails
    firebase_utils = None

# Users that always have free access (comma-separated env var)
_FREE_ACCESS_USERS = set()
_free_users_env = os.getenv('FREE_ACCESS_USERS')
if _free_users_env:
    _FREE_ACCESS_USERS = set([u.strip() for u in _free_users_env.split(',') if u.strip()])
else:
    # Default test account(s)
    _FREE_ACCESS_USERS = set(['test'])

def create_payment_intent(assignment_id, user_id, amount=500):  # $5.00 in cents
    """Create a Stripe payment intent for assignment grading"""
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            metadata={
                'assignment_id': assignment_id,
                'user_id': user_id,
                'service': 'ai_grading'
            }
        )
        return intent
    except Exception as e:
        print(f"Error creating payment intent: {e}")
        return None

def confirm_payment(payment_intent_id):
    """Confirm a payment intent"""
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return intent.status == 'succeeded'
    except Exception as e:
        print(f"Error confirming payment: {e}")
        return False

def create_checkout_session(assignment_id, user_id, success_url, cancel_url, amount_cents=999, payment_type="monthly_subscription"):
    """Create a Stripe checkout session"""
    try:
        # Determine product name and description based on payment type
        if payment_type == "monthly_subscription":
            product_name = f'Monthly Unlimited Grading - Class {assignment_id}'
            product_description = 'Unlimited AI-powered assignment grading for one class for 30 days'
            mode = 'subscription'
            # Prefer a pre-created Price ID if provided via secrets/env, as it's more reliable
            if _stripe_price_id:
                line_items = [{
                    'price': _stripe_price_id,
                    'quantity': 1,
                }]
            else:
                # Create price on-the-fly as a fallback
                line_items = [{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': product_name,
                            'description': product_description
                        },
                        'unit_amount': amount_cents,
                        'recurring': {
                            'interval': 'month'
                        }
                    },
                    'quantity': 1,
                }]
        else:
            # Fallback: treat unknown types as monthly subscription
            product_name = f'Monthly Unlimited Grading - Class {assignment_id}'
            product_description = 'Unlimited AI-powered assignment grading for one class for 30 days'
            mode = 'subscription'
            line_items = [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product_name,
                        'description': product_description
                    },
                    'unit_amount': amount_cents,
                    'recurring': {
                        'interval': 'month'
                    }
                },
                'quantity': 1,
            }]
        
        # Basic validation
        if not stripe.api_key:
            raise RuntimeError("Stripe API key not configured")

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode=mode,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'assignment_id': assignment_id,
                'user_id': user_id,
                'payment_type': payment_type
            }
        )
        return session
    except Exception as e:
        # Log for server-side visibility
        print(f"Error creating checkout session: {e}")
        return None

def log_payment(user_id, assignment_id, amount, payment_intent_id, status, payment_type="monthly_subscription"):
    """Log payment information"""
    payment_log = {
        'user_id': user_id,
        'assignment_id': assignment_id,
        'amount': amount,
        'payment_intent_id': payment_intent_id,
        'status': status,
        'payment_type': payment_type,
        'timestamp': datetime.now().isoformat()
    }
    
    # No local filesystem logging; rely solely on Firestore if available
    
    # Also write to Firestore if configured (idempotent when payment_intent_id present)
    try:
        if firebase_utils and getattr(firebase_utils, 'db', None):
            try:
                pid = payment_log.get('payment_intent_id')
                if pid:
                    # Use payment_intent_id as document id for idempotency
                    firebase_utils.db.collection('payments').document(pid).set(payment_log)
                else:
                    # No payment intent id - fall back to add()
                    firebase_utils.db.collection('payments').add(payment_log)

                # If this is a monthly subscription and completed, update the user's subscription in Firestore
                if payment_type == 'monthly_subscription' and status == 'completed':
                    expires = (datetime.utcnow() + timedelta(days=30)).isoformat()
                    try:
                        firebase_utils.db.collection('users').document(user_id).update({
                            'subscription_active': True,
                            'subscription_expires': expires,
                            'subscription_updated_at': datetime.utcnow().isoformat()
                        })
                    except Exception as e:
                        # If the user document doesn't exist or update fails, log warning
                        print(f"Warning: Failed to update user subscription in Firestore for {user_id}: {e}")
            except Exception as e:
                # Don't fail the payment flow if Firestore write fails
                print(f"Warning: failed to write payment to Firestore: {e}")
    except Exception as e:
        # Don't fail the payment flow if Firestore write fails
        print(f"Warning: failed to write payment to Firestore: {e}")

    return payment_log

def check_subscription_status(user_id, assignment_id):
    """Check if user has an active monthly subscription for this assignment/class"""
    # Quick bypass for free/test users
    if user_id in _FREE_ACCESS_USERS:
        return True
    # First try Firestore if available
    try:
        if firebase_utils and getattr(firebase_utils, 'db', None):
            payments_ref = firebase_utils.db.collection('payments')
            query = (payments_ref
                        .where('user_id', '==', user_id)
                        .where('payment_type', '==', 'monthly_subscription')
                        .where('status', '==', 'completed'))
            docs = query.stream()
            for doc in docs:
                payment = doc.to_dict()
                try:
                    payment_date = datetime.fromisoformat(payment['timestamp'])
                except Exception:
                    # If timestamp stored differently, skip
                    continue
                if (datetime.now() - payment_date) < timedelta(days=30):
                    return True
            return False
    except Exception as e:
        print(f"Warning: Firestore subscription check failed: {e}")
    # Also allow free users
    if user_id in _FREE_ACCESS_USERS:
        return True
    return False

def get_user_subscription_info(user_id):
    """Get information about user's active subscriptions"""
    # Try Firestore first for centralized data
    try:
        if firebase_utils and getattr(firebase_utils, 'db', None):
            payments_ref = firebase_utils.db.collection('payments')
            query = (payments_ref
                        .where('user_id', '==', user_id)
                        .where('payment_type', '==', 'monthly_subscription')
                        .where('status', '==', 'completed'))
            docs = query.stream()
            active_subscriptions = []
            for doc in docs:
                payment = doc.to_dict()
                try:
                    payment_date = datetime.fromisoformat(payment['timestamp'])
                except Exception:
                    continue
                days_since_payment = (datetime.now() - payment_date).days
                if days_since_payment < 30:
                    days_remaining = 30 - days_since_payment
                    active_subscriptions.append({
                        'assignment_id': payment.get('assignment_id'),
                        'start_date': payment_date,
                        'days_remaining': days_remaining,
                        'amount': payment.get('amount')
                    })
            return active_subscriptions
    except Exception as e:
        print(f"Warning: Firestore query failed: {e}")
    # Do not use local filesystem fallback; return empty list
    return []


def grant_subscription(user_id: str, months: int = 1, amount_per_month: int = 999):
    """Grant a subscription to a user programmatically.

    This creates a payment audit entry (log_payment) and updates the user's
    Firestore document with subscription fields. Returns the payment log dict.
    """
    months = max(1, int(months))
    total_amount = amount_per_month * months
    intent_id = f"manual_grant_{user_id}_{int(time.time())}"
    payment = log_payment(user_id, 'SUBSCRIPTION', total_amount, intent_id, 'completed', 'monthly_subscription')

    # Update user doc expiry
    try:
        if firebase_utils and getattr(firebase_utils, 'db', None):
            expires = (datetime.utcnow() + timedelta(days=30*months)).isoformat()
            firebase_utils.db.collection('users').document(user_id).update({
                'subscription_active': True,
                'subscription_expires': expires,
                'subscription_updated_at': datetime.utcnow().isoformat()
            })
    except Exception as e:
        print(f"Warning: Failed to update user subscription in Firestore for {user_id}: {e}")

    return payment
