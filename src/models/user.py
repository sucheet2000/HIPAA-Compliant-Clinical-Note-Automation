"""
User Model
Handles user authentication and role-based access control
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from modules.database import PostgreSQLConnection
from typing import Optional


class User(UserMixin):
    """User class for Flask-Login integration"""

    def __init__(self, user_id: int, username: str, email: str, role: str,
                 first_name: Optional[str] = None, last_name: Optional[str] = None,
                 user_is_active: bool = True):
        self.id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.first_name = first_name
        self.last_name = last_name
        self._is_active = user_is_active

    @property
    def is_active(self):
        """Check if user is active"""
        return self._is_active

    def get_full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == 'admin'

    def is_clinician(self) -> bool:
        """Check if user is clinician"""
        return self.role == 'clinician'

    @staticmethod
    def create_user(username: str, email: str, password: str, role: str = 'clinician',
                   first_name: Optional[str] = None, last_name: Optional[str] = None) -> Optional['User']:
        """Create a new user in the database"""
        try:
            db = PostgreSQLConnection()
            if not db.connect():
                return None

            password_hash = generate_password_hash(password)

            query = """
                INSERT INTO users (username, email, password_hash, role, first_name, last_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, username, email, role, first_name, last_name, is_active
            """
            params = (username, email, password_hash, role, first_name, last_name)

            result = db.execute_query(query, params)
            db.disconnect()

            if result:
                user_data = result[0]
                return User(
                    user_id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    role=user_data['role'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    user_is_active=user_data['is_active']
                )
            return None
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return None

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional['User']:
        """Get user by ID"""
        try:
            db = PostgreSQLConnection()
            if not db.connect():
                return None

            query = "SELECT id, username, email, role, first_name, last_name, is_active FROM users WHERE id = %s"
            result = db.execute_query(query, (user_id,))
            db.disconnect()

            if result:
                user_data = result[0]
                return User(
                    user_id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    role=user_data['role'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    user_is_active=user_data['is_active']
                )
            return None
        except Exception as e:
            print(f"❌ Error fetching user by ID: {e}")
            return None

    @staticmethod
    def get_user_by_username(username: str) -> Optional['User']:
        """Get user by username"""
        try:
            db = PostgreSQLConnection()
            if not db.connect():
                return None

            query = "SELECT id, username, email, role, first_name, last_name, is_active FROM users WHERE username = %s"
            result = db.execute_query(query, (username,))
            db.disconnect()

            if result:
                user_data = result[0]
                return User(
                    user_id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    role=user_data['role'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    user_is_active=user_data['is_active']
                )
            return None
        except Exception as e:
            print(f"❌ Error fetching user by username: {e}")
            return None

    @staticmethod
    def verify_credentials(username: str, password: str) -> Optional['User']:
        """Verify user credentials and return user if valid"""
        try:
            db = PostgreSQLConnection()
            if not db.connect():
                return None

            query = "SELECT id, username, email, password_hash, role, first_name, last_name, is_active FROM users WHERE username = %s"
            result = db.execute_query(query, (username,))
            db.disconnect()

            if not result:
                return None

            user_data = result[0]

            if not user_data['is_active']:
                return None

            if check_password_hash(user_data['password_hash'], password):
                return User(
                    user_id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    role=user_data['role'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    user_is_active=user_data['is_active']
                )
            return None
        except Exception as e:
            print(f"❌ Error verifying credentials: {e}")
            return None
