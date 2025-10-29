"""
payment_manager.py
Handles Stripe payments for assignment grading.
"""

import stripe
import os
import json
from datetime import datetime
from datetime import timedelta

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Optional Firestore integration (if Firebase Admin is initialized)
try:
    from . import firebase as firebase_utils
except Exception:
    # Fallback if package import fails
    firebase_utils = None

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
            # For subscription, we'll create a recurring price
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
    
    # Save to payment log file (local backup)
    log_file = f"/app/data/payments_{user_id}.json"
    payments = []
    
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            payments = json.load(f)
    
    payments.append(payment_log)
    
    with open(log_file, 'w') as f:
        json.dump(payments, f, indent=2)
    
    # Also write to Firestore if configured
    try:
        if firebase_utils and getattr(firebase_utils, 'db', None):
            # Use a collection named 'payments' and let Firestore assign a doc id
            firebase_utils.db.collection('payments').add(payment_log)
    except Exception as e:
        # Don't fail the payment flow if Firestore write fails
        print(f"Warning: failed to write payment to Firestore: {e}")

    return payment_log

def check_subscription_status(user_id, assignment_id):
    """Check if user has an active monthly subscription for this assignment/class"""
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
        print(f"Warning: Firestore subscription check failed, falling back to local file: {e}")

    # Fallback to local file-based check
    payment_file = f"/app/data/payments_{user_id}.json"
    
    if not os.path.exists(payment_file):
        return False
    
    with open(payment_file, 'r') as f:
        payments = json.load(f)
    
    # Check for active monthly subscriptions
    for payment in payments:
        if (payment.get('payment_type') == 'monthly_subscription' and 
            payment.get('status') == 'completed'):
            try:
                payment_date = datetime.fromisoformat(payment['timestamp'])
            except Exception:
                continue
            if (datetime.now() - payment_date) < timedelta(days=30):
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
        print(f"Warning: Firestore query failed, falling back to local file: {e}")

    # Fallback to local file
    payment_file = f"/app/data/payments_{user_id}.json"
    
    if not os.path.exists(payment_file):
        return None
    
    with open(payment_file, 'r') as f:
        payments = json.load(f)
    
    # Find active subscriptions
    active_subscriptions = []
    for payment in payments:
        if (payment.get('payment_type') == 'monthly_subscription' and 
            payment.get('status') == 'completed'):
            try:
                payment_date = datetime.fromisoformat(payment['timestamp'])
            except Exception:
                continue
            days_since_payment = (datetime.now() - payment_date).days
            
            if days_since_payment < 30:
                days_remaining = 30 - days_since_payment
                active_subscriptions.append({
                    'assignment_id': payment['assignment_id'],
                    'start_date': payment_date,
                    'days_remaining': days_remaining,
                    'amount': payment['amount']
                })
    
    return active_subscriptions
