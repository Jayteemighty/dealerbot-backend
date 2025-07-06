import sqlite3
from datetime import datetime
from typing import Optional

class FeedbackManager:
    def __init__(self, db_path: str = "dealerbot.db"):
        self.db_path = db_path
        self._create_feedback_table()

    def _create_feedback_table(self):
        """Create the feedback table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    message TEXT
                )
            ''')
            conn.commit()

    def store_feedback(self, session_id: str, feedback_type: str, message: Optional[str] = None) -> bool:
        """
        Store user feedback in the database.
        
        Args:
            session_id: The session ID associated with the feedback
            feedback_type: Either 'positive' or 'negative'
            message: Optional message from the user
            
        Returns:
            bool: True if feedback was stored successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO feedback (session_id, feedback_type, timestamp, message)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, feedback_type, datetime.now(), message))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error storing feedback: {e}")
            return False

    def get_feedback_stats(self, days: int = 30) -> dict:
        """
        Get feedback statistics for the specified number of days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            dict: Statistics including total feedback, positive/negative counts, and ratio
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN feedback_type = 'positive' THEN 1 ELSE 0 END) as positive_count,
                        SUM(CASE WHEN feedback_type = 'negative' THEN 1 ELSE 0 END) as negative_count
                    FROM feedback
                    WHERE timestamp >= datetime('now', ?)
                ''', (f'-{days} days',))
                
                result = cursor.fetchone()
                total, positive, negative = result
                
                return {
                    'total_feedback': total,
                    'positive_count': positive,
                    'negative_count': negative,
                    'positive_ratio': positive / total if total > 0 else 0
                }
        except Exception as e:
            print(f"Error getting feedback stats: {e}")
            return {
                'total_feedback': 0,
                'positive_count': 0,
                'negative_count': 0,
                'positive_ratio': 0
            } 