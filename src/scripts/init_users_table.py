#!/usr/bin/env python3
"""
Initialize users table in PostgreSQL database
"""

import sys
import os
import psycopg2

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.database import PostgreSQLConnection

def init_users_table():
    """Create users table if it doesn't exist"""

    sql = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) NOT NULL UNIQUE,
        email VARCHAR(100) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL DEFAULT 'clinician',
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    """

    try:
        db = PostgreSQLConnection()
        if not db.connect():
            print("❌ Failed to connect to PostgreSQL")
            return False

        # Execute the SQL
        cursor = db.connection.cursor()
        cursor.execute(sql)
        db.connection.commit()
        cursor.close()

        print("✅ Users table created successfully!")
        db.disconnect()
        return True

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    init_users_table()
