import psycopg2
from psycopg2 import pool
from typing import List, Dict, Any
import os

# PostgreSQL connection details
DB_CONFIG = {
    "dbname": "delaerbot",
    "user": "dealerbot_admin",
    "password": "dlb_admin_25!!",
    "host": "147.93.119.68",
    "port": "5432",
}

# Create a connection pool
connection_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    **DB_CONFIG
)

def connect_db():
    """Get a connection from the pool."""
    return connection_pool.getconn()

def release_connection(conn):
    """Release a connection back to the pool."""
    connection_pool.putconn(conn)

def create_table():
    """Create the messages table if it doesn't exist."""
    conn = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                session_id TEXT,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"Error creating table: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cursor.close()
            release_connection(conn)

def store_chat(chat_data: List[Dict[str, Any]]):
    """Store a list of chat messages in the database."""
    conn = None
    try:
        conn = connect_db()
        cursor = conn.cursor()

        for chat in chat_data:
            cursor.execute(
                "INSERT INTO messages (role, message, session_id) VALUES (%s, %s, %s)",
                (chat.get("role"), chat.get("message"), chat.get("session_id")))
        
        conn.commit()
    except Exception as e:
        print(f"Error storing chat: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            cursor.close()
            release_connection(conn)

def fetch_all_chats() -> List[Dict[str, Any]]:
    """Retrieve all stored chat messages."""
    conn = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT role, message, session_id FROM messages")
        chats = cursor.fetchall()
        return [{"role": role, "message": message, "session_id": session_id} 
                for role, message, session_id in chats]
    except Exception as e:
        print(f"Error fetching chats: {e}")
        raise
    finally:
        if conn:
            cursor.close()
            release_connection(conn)

def clear_db():
    """Delete all rows from the messages table."""
    conn = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        conn.commit()
    except Exception as e:
        print(f"Error clearing database: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            cursor.close()
            release_connection(conn)

# Run this once to create the table
if __name__ == "__main__":
    create_table()
    print("PostgreSQL database initialized.")