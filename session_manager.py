import uuid
from datetime import datetime, timedelta
import json
from database import connect_db, release_connection
from typing import Dict, Any, Optional

class SessionManager:
    def __init__(self):
        self.session_timeout = timedelta(hours=2)  # Sessions expire after 2 hours
        self._create_sessions_table()

    def _create_sessions_table(self):
        """Create the sessions table if it doesn't exist."""
        conn = None
        try:
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
        except Exception as e:
            print(f"Error creating sessions table: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cursor.close()
                release_connection(conn)

    def create_session(self) -> str:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        conn = None
        try:
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
            return session_id
        except Exception as e:
            print(f"Error creating session: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cursor.close()
                release_connection(conn)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data, updating last activity time."""
        conn = None
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT context, last_activity FROM sessions WHERE session_id = %s",
                (session_id,)
            )
            result = cursor.fetchone()

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
        except Exception as e:
            print(f"Error getting session: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                release_connection(conn)

    def _update_last_activity(self, session_id: str):
        """Update the last activity timestamp for a session."""
        conn = None
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET last_activity = %s WHERE session_id = %s",
                (datetime.now(), session_id)
            )
            conn.commit()
        except Exception as e:
            print(f"Error updating last activity: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cursor.close()
                release_connection(conn)

    def update_session(self, session_id: str, context_updates: Dict[str, Any]) -> bool:
        """Update session context."""
        conn = None
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Get current context
            cursor.execute(
                "SELECT context FROM sessions WHERE session_id = %s",
                (session_id,)
            )
            result = cursor.fetchone()
            
            if not result:
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
            return True
        except Exception as e:
            print(f"Error updating session: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cursor.close()
                release_connection(conn)

    def clear_session(self, session_id: str) -> bool:
        """Clear a session's context."""
        conn = None
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM sessions WHERE session_id = %s",
                (session_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error clearing session: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cursor.close()
                release_connection(conn)

    def clear_all_sessions(self):
        """Clear all sessions from the database."""
        conn = None
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions")
            conn.commit()
        except Exception as e:
            print(f"Error clearing all sessions: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cursor.close()
                release_connection(conn)

# Create a global session manager instance
session_manager = SessionManager()