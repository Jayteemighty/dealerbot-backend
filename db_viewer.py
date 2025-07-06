from database import connect_db, clear_db
from session_manager import clear_session

def view_sessions():
    """View all sessions in the database."""
    conn = connect_db()
    cursor = conn.cursor()
    
    # View sessions table
    print("\n=== Sessions Table ===")
    cursor.execute("SELECT * FROM sessions")
    sessions = cursor.fetchall()
    for session in sessions:
        print(f"\nSession ID: {session[0]}")
        print(f"Created At: {session[3]}")
        print(f"Last Activity: {session[2]}")
        print("Context:", session[1])
    
    cursor.close()
    conn.close()

def view_messages():
    """View all messages in the database."""
    conn = connect_db()
    cursor = conn.cursor()
    
    # View messages table
    print("\n=== Messages Table ===")
    cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC")
    messages = cursor.fetchall()
    for msg in messages:
        print(f"\nID: {msg[0]}")
        print(f"Role: {msg[1]}")
        print(f"Message: {msg[2]}")
        print(f"Session ID: {msg[3]}")
        print(f"Timestamp: {msg[4]}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    # clear_session()
    # clear_db()
    print("Viewing database contents...")
    view_sessions()
    view_messages()