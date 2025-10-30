"""
webhook_handler.py
Handles Stripe webhook events for payment confirmation.
"""

import streamlit as st
import stripe
import os
import json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# initialize firebase clients (side-effect)
import utils.firebase as firebase

from utils.payment_manager import log_payment

# Initialize Stripe (prefer Streamlit secrets if available)
_stripe_key = None
_webhook_secret = None
try:
    if hasattr(st, 'secrets'):
        if 'stripe' in st.secrets:
            _stripe_key = st.secrets['stripe'].get('secret_key', _stripe_key)
            _webhook_secret = st.secrets['stripe'].get('webhook_secret', _webhook_secret)
        # Flat keys fallback
        _stripe_key = st.secrets.get('STRIPE_SECRET_KEY', _stripe_key)
        if not _stripe_key:
            _stripe_key = st.secrets.get('STRIPE_API_KEY', _stripe_key)
        _webhook_secret = st.secrets.get('STRIPE_WEBHOOK_SECRET', _webhook_secret)
except Exception:
    pass

stripe.api_key = _stripe_key or os.getenv('STRIPE_SECRET_KEY') or os.getenv('STRIPE_API_KEY')
webhook_secret = _webhook_secret or os.getenv('STRIPE_WEBHOOK_SECRET')

if not stripe.api_key:
    print("Warning: STRIPE_SECRET_KEY not configured. Stripe webhook verification will fail.")
if not webhook_secret:
    print("Warning: STRIPE_WEBHOOK_SECRET not configured. Stripe webhook verification will fail.")

def handle_stripe_webhook(request_body, signature):
    """Handle Stripe webhook events"""
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            request_body, signature, webhook_secret
        )
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            handle_payment_success(session)
        elif event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            handle_payment_intent_success(payment_intent)
        else:
            print(f"Unhandled event type: {event['type']}")
            
        return True
    except ValueError as e:
        print(f"Invalid payload: {e}")
        return False
    except stripe.error.SignatureVerificationError as e:
        print(f"Invalid signature: {e}")
        return False

def handle_payment_success(session):
    """Handle successful checkout session"""
    try:
        assignment_id = session['metadata']['assignment_id']
        user_id = session['metadata']['user_id']
        amount = session['amount_total']
        payment_intent_id = session['payment_intent']
        
        # Log the payment
        log_payment(user_id, assignment_id, amount, payment_intent_id, 'completed')
        
        print(f"Payment successful for user {user_id}, assignment {assignment_id}")
        
    except Exception as e:
        print(f"Error handling payment success: {e}")

def handle_payment_intent_success(payment_intent):
    """Handle successful payment intent"""
    try:
        assignment_id = payment_intent['metadata']['assignment_id']
        user_id = payment_intent['metadata']['user_id']
        amount = payment_intent['amount']
        payment_intent_id = payment_intent['id']
        
        # Log the payment
        log_payment(user_id, assignment_id, amount, payment_intent_id, 'completed')
        
        print(f"Payment intent successful for user {user_id}, assignment {assignment_id}")
        
    except Exception as e:
        print(f"Error handling payment intent success: {e}")

def create_webhook_endpoint():
    """Create webhook endpoint in Stripe dashboard"""
    # Note: Streamlit Cloud cannot host arbitrary webhook endpoints.
    # If deploying on Streamlit, host your webhook on a separate service
    # (e.g., Fly.io, Cloud Run, Firebase Functions) and set that URL below.
    webhook_url = os.getenv('WEBHOOK_URL', "https://classcrew.fly.dev/webhook/stripe")
    
    print(f"""
    To set up your Stripe webhook:
    
    1. Go to your Stripe Dashboard
    2. Navigate to Developers → Webhooks
    3. Click "Add endpoint"
    4. Set endpoint URL to: {webhook_url}
    5. Select these events:
       - checkout.session.completed
       - payment_intent.succeeded
    6. Copy the webhook signing secret
    7. Store the signing secret securely (Streamlit: in secrets; Fly.io: as a secret env var)
    """)
