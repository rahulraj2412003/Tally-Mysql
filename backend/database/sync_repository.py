"""Persistence operations for synchronization history and checkpoints."""

from datetime import date, datetime
from typing import Any


class SyncRepository:
    def create_log(self, connection: Any, sync_type: str) -> int:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """INSERT INTO sync_log (sync_type, started_at, status)
                   VALUES (%s, %s, %s)""",
                (sync_type, datetime.now(), "RUNNING"),
            )
            return cursor.lastrowid
        finally:
            cursor.close()

    def complete_log(
        self,
        connection: Any,
        sync_id: int,
        status: str,
        extracted: int,
        inserted: int,
        updated: int,
        failed: int,
        error_message: str | None = None,
    ) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE sync_log
                SET completed_at = %s, records_extracted = %s, records_inserted = %s,
                    records_updated = %s, records_failed = %s, status = %s,
                    error_message = %s
                WHERE id = %s
                """,
                (
                    datetime.now(), extracted, inserted, updated, failed, status,
                    error_message[:1000] if error_message else None, sync_id,
                ),
            )
        finally:
            cursor.close()

    def save_state(self, connection: Any, entity_type: str, checkpoint_date: date) -> None:
        cursor = connection.cursor()
        try:
            now = datetime.now()
            cursor.execute(
                """
                INSERT INTO sync_state (entity_type, last_sync_date, last_sync_time)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE last_sync_date = %s, last_sync_time = %s
                """,
                (entity_type, checkpoint_date, now, checkpoint_date, now),
            )
        finally:
            cursor.close()

    def list_history(self, connection: Any, limit: int = 50) -> list[dict[str, Any]]:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, sync_type, started_at, completed_at,
                       records_extracted AS extracted, records_inserted AS inserted,
                       records_updated AS updated, records_failed AS failed,
                       status, error_message
                FROM sync_log
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def list_state(self, connection: Any) -> list[dict[str, Any]]:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT entity_type, last_sync_date, last_sync_time, updated_at
                FROM sync_state
                ORDER BY entity_type
                """
            )
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def get_last_sync_date(self, connection: Any, entity_type: str) -> date | None:
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT last_sync_date FROM sync_state WHERE entity_type = %s",
                (entity_type,),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            cursor.close()
