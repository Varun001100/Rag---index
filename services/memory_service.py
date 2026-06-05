from database.db import execute_query, execute_insert


class MemoryService:

    @staticmethod
    def get_history(session_id, limit=5):
        """
        Retrieves the last N conversation turns for a session from SQLite,
        ordered by timestamp ascending.
        
        Returns:
            list: A list of dicts, e.g., [{"question": "...", "answer": "...", "timestamp": "..."}]
        """
        query = """
            SELECT question, answer, timestamp
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        rows = execute_query(query, (session_id, limit))
        
        # We fetch DESC to get the latest ones, but return in chronological (ASC) order
        history = []
        for row in reversed(rows):
            history.append({
                "question": row["question"],
                "answer": row["answer"],
                "timestamp": row["timestamp"]
            })
        return history

    @staticmethod
    def add_message(session_id, question, answer):
        """
        Saves a new conversation turn into the SQLite conversations table.
        """
        query = """
            INSERT INTO conversations (session_id, question, answer)
            VALUES (?, ?, ?)
        """
        return execute_insert(query, (session_id, question, answer))

    @staticmethod
    def clear_history(session_id):
        """
        Deletes all conversation history for a given session.
        """
        query = """
            DELETE FROM conversations
            WHERE session_id = ?
        """
        execute_insert(query, (session_id,))
