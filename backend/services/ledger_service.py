"""Ledger extraction and synchronization orchestration."""

from dataclasses import dataclass
from typing import Any

from backend.database.connection import get_mysql_connection
from backend.database.repositories import LedgerRepository
from backend.services.sync_service import SyncService
from backend.services.tally_service import TallyClient, build_ledger_request
from backend.services.xml_parser import extract_ledgers, parse_tally_response


@dataclass(frozen=True)
class LedgerSyncResult:
    extracted: int
    inserted: int
    updated: int
    failed: int


class LedgerService:
    """Coordinates the working Tally ledger export with MySQL persistence."""

    def __init__(
        self,
        repository: LedgerRepository | None = None,
        sync_service: SyncService | None = None,
    ):
        self.repository = repository or LedgerRepository()
        self.sync_service = sync_service or SyncService()

    def synchronize(self) -> LedgerSyncResult:
        connection = get_mysql_connection()
        sync_id = self.sync_service.start_run(connection, "LEDGER")
        extracted = 0
        try:
            xml_text = TallyClient().export(build_ledger_request())
            ledgers = extract_ledgers(parse_tally_response(xml_text))
            extracted = len(ledgers)
            connection.start_transaction()
            inserted, updated = self.repository.save_all(connection, ledgers)
            connection.commit()
        except Exception as error:
            connection.rollback()
            self.sync_service.mark_failed(connection, sync_id, extracted, error)
            raise
        else:
            self.sync_service.mark_success(connection, sync_id, extracted, inserted, updated)
            return LedgerSyncResult(extracted=extracted, inserted=inserted, updated=updated, failed=0)
        finally:
            connection.close()

    def list_ledgers(self) -> list[dict[str, Any]]:
        connection = get_mysql_connection()
        try:
            return self.repository.list_all(connection)
        finally:
            connection.close()

    def get_ledger_details(self, ledger_id: int) -> dict[str, Any] | None:
        connection = get_mysql_connection()
        try:
            return self.repository.get_details(connection, ledger_id)
        finally:
            connection.close()
