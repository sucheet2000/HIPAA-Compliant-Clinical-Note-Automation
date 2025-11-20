#!/usr/bin/env python3
"""
Script to create test users in the database
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User

def create_test_users():
    """Create test users for development"""

    test_users = [
        {
            'username': 'admin_user',
            'email': 'admin@example.com',
            'password': 'admin_pass',
            'role': 'admin',
            'first_name': 'Admin',
            'last_name': 'User'
        },
        {
            'username': 'clinician_1',
            'email': 'clinician1@example.com',
            'password': 'clinician_pass',
            'role': 'clinician',
            'first_name': 'Dr.',
            'last_name': 'Smith'
        },
        {
            'username': 'clinician_2',
            'email': 'clinician2@example.com',
            'password': 'clinician_pass',
            'role': 'clinician',
            'first_name': 'Dr.',
            'last_name': 'Johnson'
        }
    ]

    print("Creating test users...")
    print("-" * 60)

    for user_data in test_users:
        try:
            user = User.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password'],
                role=user_data['role'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name']
            )

            if user:
                print(f"✅ Created user: {user.username} ({user.role})")
            else:
                print(f"❌ Failed to create user: {user_data['username']}")
        except Exception as e:
            print(f"❌ Error creating user {user_data['username']}: {e}")

    print("-" * 60)
    print("✅ Test users creation completed!")
    print("\nTest credentials:")
    print("  Admin: admin_user / admin_pass")
    print("  Clinician 1: clinician_1 / clinician_pass")
    print("  Clinician 2: clinician_2 / clinician_pass")


if __name__ == '__main__':
    create_test_users()
