import uuid

from database.db import (
    execute_query,
    execute_insert
)


class SessionService:

    @staticmethod
    def generate_session_id():
        return f"sess_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def create_session():
        session_id = SessionService.generate_session_id()

        execute_insert(
            """
            INSERT INTO sessions(session_id)
            VALUES (?)
            """,
            (session_id,)
        )

        return session_id

    @staticmethod
    def get_session(session_id):
        result = execute_query(
            """
            SELECT *
            FROM sessions
            WHERE session_id = ?
            """,
            (session_id,)
        )

        if not result:
            return None

        return dict(result[0])

    @staticmethod
    def session_exists(session_id):
        result = execute_query(
            """
            SELECT session_id
            FROM sessions
            WHERE session_id = ?
            """,
            (session_id,)
        )

        return len(result) > 0

    @staticmethod
    def delete_session(session_id):
        execute_insert(
            """
            DELETE FROM sessions
            WHERE session_id = ?
            """,
            (session_id,)
        )