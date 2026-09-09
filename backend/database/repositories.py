"""Database operations extracted from the working synchronization prototypes."""

from collections.abc import Iterable
import logging
from typing import Any

from backend.utils.date_utils import parse_tally_date


logger = logging.getLogger(__name__)


class LedgerRepository:
    """Persist ledger records using the existing name-based idempotent upsert."""

    def list_all(self, connection: Any) -> list[dict[str, Any]]:
        """Return the actual persisted ledgers in a stable display order."""
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, name, parent, created_at, updated_at FROM ledgers ORDER BY name"
            )
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def get_details(self, connection: Any, ledger_id: int) -> dict[str, Any] | None:
        """Return one ledger and its related vouchers from synchronized MySQL data."""
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT l.id, l.name, l.parent, l.created_at, l.updated_at,
                       v.id AS voucher_id, v.voucher_date, v.voucher_type,
                       v.voucher_number, v.narration, ve.amount,
                       ve.id AS voucher_entry_id
                FROM ledgers AS l
                LEFT JOIN voucher_entries AS ve ON ve.ledger_id = l.id
                LEFT JOIN vouchers AS v ON v.id = ve.voucher_id
                WHERE l.id = %s
                ORDER BY v.voucher_date, v.id, ve.id
                """,
                (ledger_id,),
            )
            rows = list(cursor.fetchall())
        finally:
            cursor.close()

        if not rows:
            return None

        first = rows[0]
        return {
            "id": first["id"],
            "name": first["name"],
            "parent": first["parent"],
            "created_at": first["created_at"],
            "updated_at": first["updated_at"],
            "transactions": [
                {
                    "voucher_id": row["voucher_id"],
                    "voucher_date": row["voucher_date"],
                    "voucher_type": row["voucher_type"],
                    "voucher_number": row["voucher_number"],
                    "narration": row["narration"],
                    "amount": row["amount"],
                }
                for row in rows
                if row["voucher_entry_id"] is not None
            ],
        }

    def save_all(
        self, connection: Any, ledgers: Iterable[dict[str, str | None]]
    ) -> tuple[int, int]:
        inserted = updated = 0
        cursor = connection.cursor()
        try:
            for ledger in ledgers:
                cursor.execute("SELECT id FROM ledgers WHERE name = %s", (ledger["name"],))
                exists = cursor.fetchone() is not None
                cursor.execute(
                    """
                    INSERT INTO ledgers (name, parent) VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE parent = %s, updated_at = CURRENT_TIMESTAMP
                    """,
                    (ledger["name"], ledger["parent"], ledger["parent"]),
                )
                if exists:
                    updated += 1
                else:
                    inserted += 1
        finally:
            cursor.close()
        return inserted, updated


class VoucherRepository:
    """Persist a voucher and replace its entries within the caller's transaction."""

    def list_all(self, connection: Any) -> list[dict[str, Any]]:
        """Return actual vouchers stored in MySQL, ordered by date and ID."""
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, tally_master_id, tally_alter_id, tally_voucher_key,
                       voucher_date, voucher_type, voucher_number, narration,
                       created_at, updated_at
                FROM vouchers
                ORDER BY voucher_date, id
                """
            )
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def list_entries(self, connection: Any) -> list[dict[str, Any]]:
        """Return persisted entry relationships, including their ledger names."""
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT voucher_entries.id, voucher_entries.voucher_id,
                       voucher_entries.ledger_id, ledgers.name AS ledger_name,
                       voucher_entries.amount
                FROM voucher_entries
                INNER JOIN ledgers ON ledgers.id = voucher_entries.ledger_id
                ORDER BY voucher_entries.voucher_id, voucher_entries.id
                """
            )
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def save(self, connection: Any, voucher: dict[str, Any]) -> str:
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT id FROM vouchers WHERE tally_voucher_key = %s",
                (voucher["voucher_key"],),
            )
            existing = cursor.fetchone()
            voucher_date = parse_tally_date(voucher["date"])
            if existing is None:
                cursor.execute(
                    """INSERT INTO vouchers (tally_master_id, tally_alter_id, tally_voucher_key,
                       voucher_date, voucher_type, voucher_number, narration)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (voucher["master_id"], voucher["alter_id"], voucher["voucher_key"], voucher_date,
                     voucher["voucher_type"], voucher["voucher_number"], voucher["narration"]),
                )
                voucher_id, action = cursor.lastrowid, "INSERTED"
            else:
                voucher_id, action = existing[0], "UPDATED"
                cursor.execute(
                    """UPDATE vouchers SET tally_master_id=%s, tally_alter_id=%s, voucher_date=%s,
                       voucher_type=%s, voucher_number=%s, narration=%s WHERE id=%s""",
                    (voucher["master_id"], voucher["alter_id"], voucher_date, voucher["voucher_type"],
                     voucher["voucher_number"], voucher["narration"], voucher_id),
                )
            cursor.execute("DELETE FROM voucher_entries WHERE voucher_id = %s", (voucher_id,))
            for entry in voucher["ledger_entries"]:
                cursor.execute(
                    "SELECT id FROM ledgers WHERE name = %s LIMIT 1", (entry["ledger_name"],)
                )
                ledger = cursor.fetchone()
                if ledger is None:
                    logger.error(
                        "Ledger not found while saving voucher key=%s: %s",
                        voucher["voucher_key"], entry["ledger_name"],
                    )
                    raise LookupError(f"Ledger not found: {entry['ledger_name']}")
                cursor.execute(
                    "INSERT INTO voucher_entries (voucher_id, ledger_id, amount) VALUES (%s, %s, %s)",
                    (voucher_id, ledger[0], entry["amount"]),
                )
            return action
        finally:
            cursor.close()
