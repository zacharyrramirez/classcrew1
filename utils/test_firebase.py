"""
test_firebase.py
Test Firebase connection and basic operations.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from utils.firebase import db, firebase_auth
from datetime import datetime

def test_firebase_connection():
    """Test basic Firebase operations"""
    print("🔄 Testing Firebase connection...")
    
    # Test collection reference
    try:
        test_collection = db.collection('test')
        print("✅ Successfully connected to Firestore")
        
        # Try writing a test document
        test_doc = test_collection.document('test_connection')
        test_doc.set({
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        })
        print("✅ Successfully wrote to Firestore")
        
        # Try reading it back
        result = test_doc.get()
        if result.exists:
            print("✅ Successfully read from Firestore")
            print(f"📄 Document data: {result.to_dict()}")
        
        # Clean up - delete test document
        test_doc.delete()
        print("✅ Successfully deleted test document")
        
    except Exception as e:
        print(f"❌ Error testing Firestore: {str(e)}")
        return False
    
    # Test Firebase Auth
    try:
        # List users (limited to 1 just to test API access)
        users = firebase_auth.list_users(max_results=1)
        print("✅ Successfully connected to Firebase Auth")
        print(f"👥 Found {len(list(users.users))} users")
        
    except Exception as e:
        print(f"❌ Error testing Firebase Auth: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_firebase_connection()
    if success:
        print("\n🎉 All Firebase tests passed!")
    else:
        print("\n❌ Some Firebase tests failed")