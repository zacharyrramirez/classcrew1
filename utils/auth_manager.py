"""
auth_manager.py
Firebase-based authentication system for teacher accounts.
Handles Firebase Auth for authentication and Firestore for user data.
Supports both email/password and Google Sign-In.
"""

from datetime import datetime
import json
import os
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
    # Free test account bypass
    if username == "test" and password == "test123":
        # Return mock user data for test account
        return True, {
            'email': 'test@classcrew.ai',
            'canvas_url': 'https://canvas.instructure.com',
            'canvas_token': 'test_token',
            'course_id': '12345',
            'courses': [],
            'created_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat()
        }
    
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
            # Firebase Admin SDK doesn't verify passwords directly - use REST API
            try:
                auth_user = auth.get_user(username)
                user_email = auth_user.email
                
                # Verify password using Firebase Auth REST API
                # Get Firebase Web API key from environment
                firebase_api_key = os.getenv('FIREBASE_WEB_API_KEY')
                if not firebase_api_key:
                    # Try to get from Streamlit secrets
                    try:
                        import streamlit as st
                        if hasattr(st, 'secrets') and 'FIREBASE_WEB_API_KEY' in st.secrets:
                            firebase_api_key = st.secrets['FIREBASE_WEB_API_KEY']
                    except Exception:
                        pass
                
                if not firebase_api_key:
                    print("ERROR: FIREBASE_WEB_API_KEY not configured. Password authentication disabled.")
                    print("Add FIREBASE_WEB_API_KEY to your Streamlit secrets or environment variables.")
                    return False, None
                
                # Proper password verification via Firebase REST API
                url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={firebase_api_key}'
                payload = {
                    'email': user_email,
                    'password': password,
                    'returnSecureToken': True
                }
                
                try:
                    response = requests.post(url, json=payload, timeout=10)
                    
                    if response.status_code != 200:
                        # Password verification failed
                        error_data = response.json()
                        error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                        print(f"Firebase auth error: {error_msg}")
                        return False, None
                    
                    # Password verified successfully
                    auth.update_user(username, email_verified=True)
                    
                except requests.exceptions.RequestException as e:
                    print(f"Network error during authentication: {e}")
                    return False, None
                    
            except auth.UserNotFoundError:
                return False, None
            except Exception as e:
                print(f"Unexpected error during authentication: {e}")
                return False, None
        
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
        
        # Backward compatible: support comma-separated course IDs
        course_ids = []
        if isinstance(course_id, str) and "," in course_id:
            course_ids = [c.strip() for c in course_id.split(",") if c.strip()]
            active = course_ids[0] if course_ids else ""
        else:
            active = str(course_id) if course_id is not None else ""
            course_ids = [active] if active else []

        update_payload = {
            'canvas_url': canvas_url,
            'updated_at': datetime.now().isoformat()
        }
        if canvas_token:
            update_payload['canvas_token'] = canvas_token
        if active:
            update_payload['course_id'] = active
        update_payload['course_ids'] = course_ids

        # Update Firestore data
        db.collection('users').document(username).update(update_payload)
        return True, "Canvas settings updated successfully"
    except auth.UserNotFoundError:
        return False, "User not found"
    except Exception as e:
        print(f"Error updating canvas settings: {e}")
        return False, "Failed to update settings"

def update_user_courses(username, course_ids, active_course_id=None):
    """Update a user's list of Canvas course IDs and active course selection."""
    try:
        auth.get_user(username)
        clean_ids = [str(c).strip() for c in (course_ids or []) if str(c).strip()]
        active = str(active_course_id).strip() if active_course_id else (clean_ids[0] if clean_ids else "")
        payload = {
            'course_ids': clean_ids,
            'updated_at': datetime.now().isoformat()
        }
        if active:
            payload['course_id'] = active
        db.collection('users').document(username).update(payload)
        return True, "Courses updated successfully"
    except auth.UserNotFoundError:
        return False, "User not found"
    except Exception as e:
        print(f"Error updating user courses: {e}")
        return False, "Failed to update courses"

def get_user_courses(username):
    """Get all courses for a user as a list of dicts."""
    try:
        user_doc = db.collection('users').document(username).get()
        if not user_doc.exists:
            return []
        user_data = user_doc.to_dict()
        courses = user_data.get('courses', [])
        # Backward compatibility: if courses is empty but old fields exist, migrate
        if not courses and user_data.get('canvas_url'):
            courses = [{
                'id': user_data.get('course_id', ''),
                'name': f"Course {user_data.get('course_id', 'Unknown')}",
                'canvas_url': user_data.get('canvas_url', ''),
                'canvas_token': user_data.get('canvas_token', '')
            }]
        return courses
    except Exception as e:
        print(f"Error getting user courses: {e}")
        return []

def add_user_course(username, course_name, course_id, canvas_url, canvas_token):
    """Add a new course to a user's account."""
    try:
        auth.get_user(username)
        user_doc = db.collection('users').document(username).get()
        if not user_doc.exists:
            return False, "User not found"
        
        user_data = user_doc.to_dict()
        courses = user_data.get('courses', [])
        
        # Check if course_id already exists
        if any(c.get('id') == str(course_id) for c in courses):
            return False, f"Course ID {course_id} already exists"
        
        new_course = {
            'id': str(course_id),
            'name': course_name,
            'canvas_url': canvas_url,
            'canvas_token': canvas_token,
            'created_at': datetime.now().isoformat()
        }
        courses.append(new_course)
        
        # If this is the first course, set it as active
        payload = {
            'courses': courses,
            'updated_at': datetime.now().isoformat()
        }
        if len(courses) == 1:
            payload['course_id'] = str(course_id)
        
        db.collection('users').document(username).update(payload)
        return True, "Course added successfully"
    except auth.UserNotFoundError:
        return False, "User not found"
    except Exception as e:
        print(f"Error adding course: {e}")
        return False, "Failed to add course"

def update_user_course(username, course_id, course_name=None, canvas_url=None, canvas_token=None):
    """Update an existing course for a user."""
    try:
        auth.get_user(username)
        user_doc = db.collection('users').document(username).get()
        if not user_doc.exists:
            return False, "User not found"
        
        user_data = user_doc.to_dict()
        courses = user_data.get('courses', [])
        
        # Find and update the course
        found = False
        for course in courses:
            if course.get('id') == str(course_id):
                if course_name:
                    course['name'] = course_name
                if canvas_url:
                    course['canvas_url'] = canvas_url
                if canvas_token:
                    course['canvas_token'] = canvas_token
                course['updated_at'] = datetime.now().isoformat()
                found = True
                break
        
        if not found:
            return False, f"Course ID {course_id} not found"
        
        db.collection('users').document(username).update({
            'courses': courses,
            'updated_at': datetime.now().isoformat()
        })
        return True, "Course updated successfully"
    except auth.UserNotFoundError:
        return False, "User not found"
    except Exception as e:
        print(f"Error updating course: {e}")
        return False, "Failed to update course"

def delete_user_course(username, course_id):
    """Delete a course from a user's account."""
    try:
        auth.get_user(username)
        user_doc = db.collection('users').document(username).get()
        if not user_doc.exists:
            return False, "User not found"
        
        user_data = user_doc.to_dict()
        courses = user_data.get('courses', [])
        
        # Remove the course
        original_count = len(courses)
        courses = [c for c in courses if c.get('id') != str(course_id)]
        
        if len(courses) == original_count:
            return False, f"Course ID {course_id} not found"
        
        payload = {
            'courses': courses,
            'updated_at': datetime.now().isoformat()
        }
        
        # If the deleted course was active, switch to first available or clear
        if user_data.get('course_id') == str(course_id):
            payload['course_id'] = courses[0]['id'] if courses else ''
        
        db.collection('users').document(username).update(payload)
        return True, "Course deleted successfully"
    except auth.UserNotFoundError:
        return False, "User not found"
    except Exception as e:
        print(f"Error deleting course: {e}")
        return False, "Failed to delete course"

def set_active_course(username, course_id):
    """Set the active course for a user."""
    try:
        auth.get_user(username)
        user_doc = db.collection('users').document(username).get()
        if not user_doc.exists:
            return False, "User not found"
        
        user_data = user_doc.to_dict()
        courses = user_data.get('courses', [])
        
        # Verify course exists
        if not any(c.get('id') == str(course_id) for c in courses):
            return False, f"Course ID {course_id} not found"
        
        db.collection('users').document(username).update({
            'course_id': str(course_id),
            'updated_at': datetime.now().isoformat()
        })
        return True, "Active course updated"
    except auth.UserNotFoundError:
        return False, "User not found"
    except Exception as e:
        print(f"Error setting active course: {e}")
        return False, "Failed to set active course"

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
