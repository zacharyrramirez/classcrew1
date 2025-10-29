"""
test_auth_manager.py
Temporary test version of auth manager with simplified authentication
"""

from datetime import datetime
from firebase_admin import auth
from firebase_admin.auth import EmailAlreadyExistsError, UidAlreadyExistsError
from utils.firebase import db

# Test constants - in production, use proper Firebase Auth UI
TEST_PASSWORD = "TestPassword123!"

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
            password=TEST_PASSWORD,  # Use test password for all test users
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
        
    except EmailAlreadyExistsError:
        return False, "Email already registered"
    except UidAlreadyExistsError:
        return False, "Username already exists"
    except Exception as e:
        print(f"Error creating user: {e}")
        return False, "Failed to create account"

def authenticate_user(username, password):
    """Test version of authentication"""
    try:
        # Verify username exists
        try:
            auth_user = auth.get_user(username)
        except auth.UserNotFoundError:
            return False, None
            
        # In testing, we only accept the test password
        if password != TEST_PASSWORD:
            return False, None
            
        # Get user data from Firestore
        user_doc = db.collection('users').document(username).get()
        if not user_doc.exists:
            return False, None
            
        user_data = user_doc.to_dict()
        
        # Update last login
        db.collection('users').document(username).update({
            'last_login': datetime.now().isoformat()
        })
        
        return True, user_data
            
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