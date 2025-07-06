import uuid
from datetime import datetime, timedelta
import json
from database import connect_db

class SessionManager:
    def __init__(self):
        self.session_timeout = timedelta(hours=2)  # Sessions expire after 2 hours
        self._create_sessions_table()

    def _create_sessions_table(self):
        """Create the sessions table if it doesn't exist."""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                context JSONB,
                last_activity TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

    def create_session(self):
        """Create a new session."""
        session_id = str(uuid.uuid4())
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (session_id, context, last_activity) VALUES (%s, %s, %s)",
            (session_id, json.dumps({
                'last_query': None,
                'last_response': None,
                'last_vehicles': None,
                'last_comparison': None,
                'conversation_history': []
            }), datetime.now())
        )
        conn.commit()
        cursor.close()
        conn.close()
        return session_id

    def get_session(self, session_id):
        """Get session data, updating last activity time."""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT context, last_activity FROM sessions WHERE session_id = %s",
            (session_id,)
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result:
            return None

        context, last_activity = result
        if datetime.now() - last_activity > self.session_timeout:
            self.clear_session(session_id)
            return None

        # Update last activity
        self._update_last_activity(session_id)
        
        # Check if context is already a dict (from JSONB) or needs parsing
        if isinstance(context, dict):
            return {
                'context': context,
                'last_activity': last_activity
            }
        else:
            return {
                'context': json.loads(context),
                'last_activity': last_activity
            }

    def _update_last_activity(self, session_id):
        """Update the last activity timestamp for a session."""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET last_activity = %s WHERE session_id = %s",
            (datetime.now(), session_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

    def update_session(self, session_id, context_updates):
        """Update session context."""
        conn = connect_db()
        cursor = conn.cursor()
        
        # Get current context
        cursor.execute(
            "SELECT context FROM sessions WHERE session_id = %s",
            (session_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            conn.close()
            return False

        # Handle both dict and string cases for JSONB data
        current_context = result[0] if isinstance(result[0], dict) else json.loads(result[0])
        current_context.update(context_updates)
        
        # Update context and last activity
        cursor.execute(
            "UPDATE sessions SET context = %s, last_activity = %s WHERE session_id = %s",
            (json.dumps(current_context), datetime.now(), session_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True

    def add_to_history(self, session_id, query, response):
        """Add a query-response pair to the conversation history."""
        conn = connect_db()
        cursor = conn.cursor()
        
        # Get current context
        cursor.execute(
            "SELECT context FROM sessions WHERE session_id = %s",
            (session_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            conn.close()
            return False

        current_context = json.loads(result[0])
        if 'conversation_history' not in current_context:
            current_context['conversation_history'] = []
        
        current_context['conversation_history'].append({
            'query': query,
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only the last 10 messages
        current_context['conversation_history'] = current_context['conversation_history'][-10:]
        
        # Update context and last activity
        cursor.execute(
            "UPDATE sessions SET context = %s, last_activity = %s WHERE session_id = %s",
            (json.dumps(current_context), datetime.now(), session_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True

    def clear_session(self, session_id):
        """Clear a session's context."""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM sessions WHERE session_id = %s",
            (session_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True

    def save_sessions(self):
        """Save sessions to the JSON file."""
        with open(self.session_file, 'w') as f:
            json.dump(self.sessions, f)

    def clear_all_sessions(self):
        """Clear all sessions from the database."""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions")
        conn.commit()
        cursor.close()
        conn.close()

def clear_session():
    """Clear all sessions from the database."""
    session_manager.clear_all_sessions()

# Create a global session manager instance
session_manager = SessionManager() 