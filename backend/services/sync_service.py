"""Synchronization history and checkpoint service."""

from datetime import date
from dataclasses import dataclass
from typing import Any

from backend.database.connection import get_mysql_connection
from backend.database.sync_repository import SyncRepository


class SyncService:
    def __init__(self, repository: SyncRepository | None = None):
        self.repository = repository or SyncRepository()

    def start_run(self, connection: Any, sync_type: str) -> int:
        sync_id = self.repository.create_log(connection, sync_type)
        connection.commit()
        return sync_id

    def mark_success(
        self, connection: Any, sync_id: int, extracted: int, inserted: int, updated: int
    ) -> None:
        self.repository.complete_log(
            connection, sync_id, "SUCCESS", extracted, inserted, updated, 0
        )
        connection.commit()

    def mark_failed(
        self, connection: Any, sync_id: int, extracted: int, error: Exception
    ) -> None:
        self.repository.complete_log(
            connection, sync_id, "FAILED", extracted, 0, 0, 1, str(error)
        )
        connection.commit()

    def save_checkpoint(self, connection: Any, entity_type: str, checkpoint_date: date) -> None:
        """Save state inside the caller's successful data transaction."""
        self.repository.save_state(connection, entity_type, checkpoint_date)

    def last_sync_date(self, entity_type: str) -> date | None:
        connection = get_mysql_connection()
        try:
            return self.repository.get_last_sync_date(connection, entity_type)
        finally:
            connection.close()

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        connection = get_mysql_connection()
        try:
            return self.repository.list_history(connection, limit)
        finally:
            connection.close()

    def state(self) -> list[dict[str, Any]]:
        connection = get_mysql_connection()
        try:
            return self.repository.list_state(connection)
        finally:
            connection.close()


@dataclass(frozen=True)
class FullSyncResult:
    extracted: int
    inserted: int
    updated: int
    failed: int


class SynchronizationService:
    """Run master and transaction synchronization in dependency order."""

    def __init__(
        self,
        ledger_service: Any | None = None,
        voucher_service: Any | None = None,
        sync_service: SyncService | None = None,
    ):
        self.ledger_service = ledger_service
        self.voucher_service = voucher_service
        self.sync_service = sync_service or SyncService()

    @staticmethod
    def _combine(ledger_result: Any, voucher_result: Any) -> FullSyncResult:
        return FullSyncResult(
            extracted=ledger_result.extracted + voucher_result.extracted,
            inserted=ledger_result.inserted + voucher_result.inserted,
            updated=ledger_result.updated + voucher_result.updated,
            failed=ledger_result.failed + voucher_result.failed,
        )

    def synchronize_full(self, from_date: date, to_date: date) -> FullSyncResult:
        from backend.services.ledger_service import LedgerService
        from backend.services.voucher_service import VoucherService

        ledger_service = self.ledger_service or LedgerService()
        voucher_service = self.voucher_service or VoucherService()
        ledger_result = ledger_service.synchronize()
        voucher_result = voucher_service.synchronize(from_date, to_date)
        return self._combine(ledger_result, voucher_result)

    def synchronize_incremental(self, from_date: date, to_date: date) -> FullSyncResult:
        last_sync_date = self.sync_service.last_sync_date("VOUCHER")
        window_start = last_sync_date or from_date
        return self.synchronize_full(window_start, to_date)
