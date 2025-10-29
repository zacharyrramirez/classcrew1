"""
test_firebase_auth.py
Test script for Firebase authentication and user management functionality.
"""

import os
import sys
import time
from datetime import datetime

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.auth_manager import (
    create_user,
    authenticate_user,
    update_user_canvas,
    get_user_by_username,
    user_exists
)

def run_tests():
    """Run all authentication and user management tests"""
    # Test data
    test_user = {
        'username': f'test_user_{int(time.time())}',  # Unique username
        'password': 'TestPassword123!',
        'email': f'test_{int(time.time())}@example.com',  # Unique email
        'canvas_url': 'https://school.instructure.com',
        'canvas_token': 'test_token_123',
        'course_id': '12345'
    }
    
    print("\n🔄 Starting Firebase Auth Tests...")
    print("=" * 50)
    
    # Test 1: User Creation
    print("\n1️⃣ Testing User Creation")
    print("-" * 30)
    success, message = create_user(
        username=test_user['username'],
        password=test_user['password'],
        email=test_user['email'],
        canvas_url=test_user['canvas_url'],
        canvas_token=test_user['canvas_token'],
        course_id=test_user['course_id']
    )
    print(f"Create user result: {message}")
    assert success, "User creation failed"
    print("✅ User created successfully")
    
    # Test 2: User Exists Check
    print("\n2️⃣ Testing User Exists")
    print("-" * 30)
    exists = user_exists(test_user['username'])
    assert exists, "User should exist"
    print("✅ User exists check passed")
    
    # Test 3: Authentication
    print("\n3️⃣ Testing Authentication")
    print("-" * 30)
    success, user_data = authenticate_user(test_user['username'], test_user['password'])
    assert success, "Authentication failed"
    assert user_data is not None, "User data should not be None"
    print("✅ Authentication successful")
    print(f"📝 User data retrieved: {list(user_data.keys())}")
    
    # Test 4: Invalid Password
    print("\n4️⃣ Testing Invalid Password")
    print("-" * 30)
    success, _ = authenticate_user(test_user['username'], 'wrong_password')
    assert not success, "Should fail with wrong password"
    print("✅ Invalid password correctly rejected")
    
    # Test 5: Get User Data
    print("\n5️⃣ Testing Get User Data")
    print("-" * 30)
    user_data = get_user_by_username(test_user['username'])
    assert user_data is not None, "Should get user data"
    assert user_data['email'] == test_user['email'], "Email should match"
    print("✅ User data retrieved successfully")
    
    # Test 6: Update Canvas Settings
    print("\n6️⃣ Testing Update Canvas Settings")
    print("-" * 30)
    new_canvas = {
        'canvas_url': 'https://newschool.instructure.com',
        'canvas_token': 'new_token_456',
        'course_id': '67890'
    }
    success, message = update_user_canvas(
        test_user['username'],
        new_canvas['canvas_url'],
        new_canvas['canvas_token'],
        new_canvas['course_id']
    )
    assert success, "Canvas update failed"
    print("✅ Canvas settings updated successfully")
    
    # Test 7: Verify Updates
    print("\n7️⃣ Testing Verify Updates")
    print("-" * 30)
    updated_data = get_user_by_username(test_user['username'])
    assert updated_data['canvas_url'] == new_canvas['canvas_url'], "Canvas URL should be updated"
    assert updated_data['canvas_token'] == new_canvas['canvas_token'], "Canvas token should be updated"
    assert updated_data['course_id'] == new_canvas['course_id'], "Course ID should be updated"
    print("✅ Updates verified successfully")
    
    # Test 8: Non-existent User
    print("\n8️⃣ Testing Non-existent User")
    print("-" * 30)
    success, _ = authenticate_user('nonexistent_user', 'any_password')
    assert not success, "Should fail for non-existent user"
    print("✅ Non-existent user correctly rejected")
    
    print("\n✨ All tests passed successfully!")
    return test_user

def cleanup_test_user(test_user):
    """Optional: Clean up test user data
    Note: Requires additional Firebase Admin permissions"""
    try:
        from firebase_admin import auth
        auth.delete_user(test_user['username'])
        print(f"\n🧹 Cleaned up test user: {test_user['username']}")
    except Exception as e:
        print(f"\n⚠️ Could not clean up test user: {e}")

if __name__ == "__main__":
    try:
        test_user = run_tests()
        
        # Ask if we should clean up the test user
        if input("\nWould you like to delete the test user? [y/N]: ").lower() == 'y':
            cleanup_test_user(test_user)
            
    except AssertionError as e:
        print(f"\n❌ Test failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)