"""
auth_manager.py
Firebase-based authentication system for teacher accounts.
Handles Firebase Auth for authentication and Firestore for user data.
Supports both email/password and Google Sign-In.
"""

from datetime import datetime
import json
from firebase_admin import auth
from firebase_admin.auth import EmailAlreadyExistsError, UidAlreadyExistsError
from utils.firebase import db
import requests

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

def create_user(username, password, email, canvas_url, canvas_token, course_id):
    """Create a new user account with Firebase Auth and Firestore"""
    # Validate password
    is_valid, message = validate_password(password)
    if not is_valid:
        return False, message
    
    try:
        # Create the user in Firebase Auth
        user = auth.create_user(
            uid=username,  # Use username as uid for simplicity
            email=email,
            password=password,  # Firebase handles password hashing
            display_name=username
        )
        
        # Store additional user data in Firestore
        user_data = {
            'email': email,
            'canvas_url': canvas_url,
            'canvas_token': canvas_token,
            'course_id': course_id,
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }
        
        db.collection('users').document(username).set(user_data)
        return True, "Account created successfully"
        
    except auth.EmailAlreadyExistsError:
        return False, "Email already registered"
    except auth.UidAlreadyExistsError:
        return False, "Username already exists"
    except Exception as e:
        print(f"Error creating user: {e}")
        return False, "Failed to create account"

def authenticate_user(username, password=None, id_token=None):
    """
    Authenticate a user using Firebase Auth and get Firestore data
    Supports both email/password and Google Sign-In (via id_token)
    """
    try:
        if id_token:
            # Verify the Google Sign-In token
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token['uid']
            email = decoded_token['email']
            
            # Check if user exists in our system
            try:
                user = auth.get_user_by_email(email)
                username = user.uid  # Get our internal username
            except auth.UserNotFoundError:
                # First time Google Sign-In - create user
                display_name = decoded_token.get('name', email.split('@')[0])
                user = auth.create_user(
                    uid=email.split('@')[0],  # Use email prefix as username
                    email=email,
                    display_name=display_name,
                    email_verified=True
                )
                username = user.uid
                
                # Create Firestore document
                db.collection('users').document(username).set({
                    'email': email,
                    'created_at': datetime.now().isoformat(),
                    'last_login': None,
                    'auth_type': 'google'
                })
        else:
            # Regular email/password authentication
            auth_user = auth.get_user(username)
            
            # For testing purposes (NOT FOR PRODUCTION)
            # In production, you should use Firebase Authentication UI or REST API
            auth.update_user(
                username,
                email_verified=True
            )
        
        # Get user data from Firestore
        user_doc = db.collection('users').document(username).get()
        if not user_doc.exists:
            return False, None
        
        user_data = user_doc.to_dict()
        
        # Update last login in Firestore
        db.collection('users').document(username).update({
            'last_login': datetime.now().isoformat()
        })
        
        return True, user_data
        
    except auth.UserNotFoundError:
        return False, None
    except Exception as e:
        print(f"Error during authentication: {e}")
        return False, None

def update_user_canvas(username, canvas_url, canvas_token, course_id):
    """Update user's Canvas configuration in Firestore"""
    try:
        # Verify user exists in Firebase Auth
        auth.get_user(username)
        
        # Update Firestore data
        db.collection('users').document(username).update({
            'canvas_url': canvas_url,
            'canvas_token': canvas_token,
            'course_id': course_id,
            'updated_at': datetime.now().isoformat()
        })
        return True, "Canvas settings updated successfully"
    except auth.UserNotFoundError:
        return False, "User not found"
    except Exception as e:
        print(f"Error updating canvas settings: {e}")
        return False, "Failed to update settings"

def get_user_by_username(username):
    """Get user data from Firebase Auth and Firestore"""
    try:
        # Get user from Firebase Auth
        auth_user = auth.get_user(username)
        
        # Get additional data from Firestore
        user_doc = db.collection('users').document(username).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            user_data.update({
                'uid': auth_user.uid,
                'email_verified': auth_user.email_verified
            })
            return user_data
        return None
    except auth.UserNotFoundError:
        return None

def user_exists(username):
    """Check if user exists in Firebase Auth"""
    try:
        auth.get_user(username)
        return True
    except auth.UserNotFoundError:
        return False
