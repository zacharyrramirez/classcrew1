"""
migrate_users_to_firebase.py
Script to check for existing users and optionally migrate them to Firebase.
"""

import os
import json
from datetime import datetime
from firebase import db, firebase_auth

def check_existing_users():
    """Check for existing users in the local JSON file"""
    possible_paths = [
        "/app/data/users.json",  # Production path
        "data/users.json",       # Local relative path
        "../data/users.json",    # Local relative from utils/
        "app/data/users.json"    # Alternative local path
    ]
    
    for path in possible_paths:
        try:
            with open(path, 'r') as f:
                users = json.load(f)
                print(f"Found {len(users)} users in {path}")
                return users
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    
    print("No existing users found in any location")
    return None

def migrate_users_to_firebase(users):
    """Migrate users to Firebase Firestore"""
    if not users:
        print("No users to migrate")
        return
    
    # Create users collection in Firestore
    users_ref = db.collection('users')
    
    for username, user_data in users.items():
        try:
            # Create the user in Firebase Auth first
            try:
                firebase_auth.create_user(
                    uid=username,
                    email=user_data.get('email'),
                    password_hash=bytes.fromhex(user_data['password_hash']),
                    display_name=username
                )
                print(f"✅ Created Auth user: {username}")
            except Exception as e:
                print(f"⚠️ Could not create Auth user {username}: {e}")
            
            # Store user data in Firestore
            users_ref.document(username).set({
                'email': user_data.get('email'),
                'canvas_url': user_data.get('canvas_url'),
                'canvas_token': user_data.get('canvas_token'),
                'course_id': user_data.get('course_id'),
                'created_at': user_data.get('created_at', datetime.now().isoformat()),
                'last_login': user_data.get('last_login'),
                'migrated_at': datetime.now().isoformat()
            })
            print(f"✅ Migrated user data: {username}")
            
        except Exception as e:
            print(f"❌ Error migrating user {username}: {e}")

def main():
    # Check for existing users
    users = check_existing_users()
    
    if users:
        print(f"\nFound {len(users)} users to migrate:")
        for username in users.keys():
            print(f"- {username}")
        
        if input("\nWould you like to migrate these users to Firebase? [y/N]: ").lower() == 'y':
            migrate_users_to_firebase(users)
        else:
            print("Migration cancelled")
    else:
        print("\nNo existing users found - ready to start fresh with Firebase!")

if __name__ == "__main__":
    main()