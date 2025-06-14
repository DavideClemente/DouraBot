from database import DatabaseManager


def get_latest_message_id_by_channel_id(channel_id: str) -> str:
    with DatabaseManager().get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MESSAGE_ID FROM MESSAGES WHERE CHANNEL_ID = %s ORDER BY UPDATED_AT DESC LIMIT 1", (channel_id,))
        result = cursor.fetchone()
        return result[0] if result else None


def insert_message(context: str, message_id: str, channel_id: str) -> None:
    with DatabaseManager().get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO MESSAGES (CONTEXT, MESSAGE_ID, CHANNEL_ID) VALUES (%s, %s, %s)",
            (context, message_id, channel_id)
        )
        conn.commit()


def delete_message_by_id(message_id: str) -> None:
    with DatabaseManager().get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM MESSAGES WHERE MESSAGE_ID = %s", (message_id,))
        conn.commit()
