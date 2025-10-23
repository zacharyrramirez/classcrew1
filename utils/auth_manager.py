"""
auth_manager.py
Simple file-based authentication system for teacher accounts.
Stores user credentials and Canvas configuration in JSON format.
"""

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path

USERS_FILE = "/app/data/users.json"

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Load all users from the users file"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_users(users):
    """Save users to the users file"""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

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
    """Create a new user account"""
    users = load_users()
    
    # Check if username already exists
    if username in users:
        return False, "Username already exists"
    
    # Validate password
    is_valid, message = validate_password(password)
    if not is_valid:
        return False, message
    
    # Create user record
    users[username] = {
        'password_hash': hash_password(password),
        'email': email,
        'canvas_url': canvas_url,
        'canvas_token': canvas_token,
        'course_id': course_id,
        'created_at': datetime.now().isoformat(),
        'last_login': None
    }
    
    save_users(users)
    return True, "Account created successfully"

def authenticate_user(username, password):
    """Authenticate a user login"""
    users = load_users()
    
    if username not in users:
        return False, None
    
    user = users[username]
    if user['password_hash'] == hash_password(password):
        # Update last login
        user['last_login'] = datetime.now().isoformat()
        save_users(users)
        return True, user
    
    return False, None

def update_user_canvas(username, canvas_url, canvas_token, course_id):
    """Update user's Canvas configuration"""
    users = load_users()
    
    if username not in users:
        return False, "User not found"
    
    users[username]['canvas_url'] = canvas_url
    users[username]['canvas_token'] = canvas_token
    users[username]['course_id'] = course_id
    
    save_users(users)
    return True, "Canvas settings updated successfully"

def get_user_by_username(username):
    """Get user data by username"""
    users = load_users()
    return users.get(username)

def user_exists(username):
    """Check if username exists"""
    users = load_users()
    return username in users
