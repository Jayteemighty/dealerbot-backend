import psycopg2 #type: ignore

# PostgreSQL connection details
DB_CONFIG = {
    "dbname": "delaerbot",
    "user": "dealerbot_admin",
    "password": "dlb_admin_25!!",
    "host": "147.93.119.68",
    "port": "5432",  # Default PostgreSQL port
}


def connect_db():
    """Establish a connection to the PostgreSQL database."""
    return psycopg2.connect(**DB_CONFIG)

def create_table():
    """Create the messages table if it doesn't exist."""
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
    cursor.close()
    conn.close()

def store_chat(chat_data):
    """Store a list of chat messages in the database."""
    conn = connect_db()
    cursor = conn.cursor()

    for chat in chat_data:
        cursor.execute("INSERT INTO messages (role, message, session_id) VALUES (%s, %s, %s)", 
                       (chat.get("role"), chat.get("message"), chat.get("session_id")))
    
    conn.commit()
    cursor.close()
    conn.close()

def fetch_all_chats():
    """Retrieve all stored chat messages."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role, message, session_id FROM messages")
    chats = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [{"role": role, "message": message, "session_id": session_id} for role, message, session_id in chats]

def clear_db():
    """Delete all rows from the messages table."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    conn.commit()
    cursor.close()
    conn.close()

# Run this once to create the table
if __name__ == "__main__":
    create_table()
    print("PostgreSQL database initialized.")
