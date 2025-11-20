"""
Database Connection Module
Handles connections to PostgreSQL (audit logs) and MongoDB (FHIR data)
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
from typing import Optional, Dict, Any
from datetime import datetime


class PostgreSQLConnection:
    """PostgreSQL connection handler for audit logs"""

    def __init__(self):
        self.connection = None
        self.db_url = os.getenv(
            'DATABASE_URL',
            'postgresql://clinicaluser:secure_password_change_me@localhost:5432/clinical_notes_audit'
        )

    def connect(self) -> bool:
        """Establish PostgreSQL connection"""
        try:
            self.connection = psycopg2.connect(self.db_url)
            print("✅ Connected to PostgreSQL")
            return True
        except psycopg2.Error as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            return False

    def disconnect(self):
        """Close PostgreSQL connection"""
        if self.connection:
            self.connection.close()
            print("✅ Disconnected from PostgreSQL")

    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute SELECT query"""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except psycopg2.Error as e:
            print(f"❌ Query execution failed: {e}")
            return []

    def execute_insert(self, query: str, params: tuple = ()) -> Optional[int]:
        """Execute INSERT query and return inserted ID"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                # If the query has RETURNING id, fetch it
                result = cursor.fetchone()
                return result[0] if result else None
        except psycopg2.Error as e:
            self.connection.rollback()
            print(f"❌ Insert failed: {e}")
            return None

    def execute_update(self, query: str, params: tuple = ()) -> bool:
        """Execute UPDATE query"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                return True
        except psycopg2.Error as e:
            self.connection.rollback()
            print(f"❌ Update failed: {e}")
            return False

    def log_audit_event(
        self,
        transaction_id: str,
        event_type: str,
        status: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """Log an audit event"""
        import json
        query = """
            INSERT INTO audit_logs
            (transaction_id, event_type, status, user_id, ip_address, details, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            transaction_id,
            event_type,
            status,
            user_id,
            ip_address,
            json.dumps(details),
            datetime.utcnow()
        )
        return self.execute_update(query, params)


class MongoDBConnection:
    """MongoDB connection handler for FHIR bundles"""

    def __init__(self):
        self.client = None
        self.db = None
        self.mongodb_url = os.getenv(
            'MONGODB_URL',
            'mongodb://clinicaluser:secure_password_change_me@localhost:27017/clinical_notes_fhir?authSource=admin'
        )

    def connect(self) -> bool:
        """Establish MongoDB connection"""
        try:
            self.client = MongoClient(self.mongodb_url)
            # Verify connection
            self.client.admin.command('ping')
            self.db = self.client['clinical_notes_fhir']
            print("✅ Connected to MongoDB")
            return True
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            return False

    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("✅ Disconnected from MongoDB")

    def save_fhir_bundle(
        self,
        transaction_id: str,
        bundle: Dict[str, Any],
        confidence_score: float = 0.0,
        validation_status: str = 'pending'
    ) -> bool:
        """Save FHIR bundle to MongoDB"""
        try:
            collection = self.db['fhir_bundles']
            document = {
                'transaction_id': transaction_id,
                'bundle': bundle,
                'confidence_score': confidence_score,
                'validation_status': validation_status,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            result = collection.insert_one(document)
            print(f"✅ Saved FHIR bundle: {transaction_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to save FHIR bundle: {e}")
            return False

    def get_fhir_bundle(self, transaction_id: str) -> Optional[Dict]:
        """Retrieve FHIR bundle from MongoDB"""
        try:
            collection = self.db['fhir_bundles']
            document = collection.find_one({'transaction_id': transaction_id})
            return document
        except Exception as e:
            print(f"❌ Failed to retrieve FHIR bundle: {e}")
            return None

    def save_clinical_note(
        self,
        transaction_id: str,
        masked_text: str,
        structured_output: Dict[str, Any],
        original_text: Optional[str] = None
    ) -> bool:
        """Save clinical note metadata to MongoDB"""
        try:
            collection = self.db['clinical_notes']
            document = {
                'transaction_id': transaction_id,
                'original_text': original_text,
                'masked_text': masked_text,
                'structured_output': structured_output,
                'created_at': datetime.utcnow()
            }
            collection.insert_one(document)
            print(f"✅ Saved clinical note: {transaction_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to save clinical note: {e}")
            return False

    def save_clinician_review(
        self,
        transaction_id: str,
        clinician_id: str,
        action: str,
        notes: Optional[str] = None
    ) -> bool:
        """Save clinician review decision"""
        try:
            collection = self.db['clinician_reviews']
            document = {
                'transaction_id': transaction_id,
                'clinician_id': clinician_id,
                'action': action,
                'notes': notes,
                'reviewed_at': datetime.utcnow()
            }
            collection.insert_one(document)
            print(f"✅ Saved clinician review: {transaction_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to save clinician review: {e}")
            return False

    def get_flagged_notes(self, min_confidence: float = 0.85) -> list:
        """Get notes flagged for review (low confidence)"""
        try:
            collection = self.db['fhir_bundles']
            flagged = collection.find(
                {'confidence_score': {'$lt': min_confidence}},
                sort=[('created_at', -1)]
            ).limit(100)
            return list(flagged)
        except Exception as e:
            print(f"❌ Failed to retrieve flagged notes: {e}")
            return []


# Global connection instances
_postgres_conn: Optional[PostgreSQLConnection] = None
_mongodb_conn: Optional[MongoDBConnection] = None


def get_postgres_connection() -> PostgreSQLConnection:
    """Get or create PostgreSQL connection"""
    global _postgres_conn
    if _postgres_conn is None:
        _postgres_conn = PostgreSQLConnection()
        _postgres_conn.connect()
    return _postgres_conn


def get_mongodb_connection() -> MongoDBConnection:
    """Get or create MongoDB connection"""
    global _mongodb_conn
    if _mongodb_conn is None:
        _mongodb_conn = MongoDBConnection()
        _mongodb_conn.connect()
    return _mongodb_conn


def close_connections():
    """Close all database connections"""
    global _postgres_conn, _mongodb_conn
    if _postgres_conn:
        _postgres_conn.disconnect()
    if _mongodb_conn:
        _mongodb_conn.disconnect()
