"""Voucher extraction, transformation, and transactional synchronization."""

from dataclasses import dataclass
from datetime import date
import logging
from typing import Any

from backend.database.connection import get_mysql_connection
from backend.database.repositories import VoucherRepository
from backend.services.sync_service import SyncService
from backend.services.tally_service import TallyClient, build_day_book_request
from backend.services.xml_parser import extract_vouchers, parse_tally_response


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoucherSyncResult:
    extracted: int
    inserted: int
    updated: int
    failed: int


class VoucherService:
    """Coordinates the live Day Book export and MySQL voucher persistence."""

    def __init__(
        self,
        repository: VoucherRepository | None = None,
        sync_service: SyncService | None = None,
    ):
        self.repository = repository or VoucherRepository()
        self.sync_service = sync_service or SyncService()

    def synchronize(self, from_date: date, to_date: date) -> VoucherSyncResult:
        connection = get_mysql_connection()
        sync_id = self.sync_service.start_run(connection, "VOUCHER")
        extracted = 0
        try:
            if from_date > to_date:
                raise ValueError("from_date must be on or before to_date.")

            xml_text = TallyClient().export(build_day_book_request(from_date, to_date))
            vouchers = extract_vouchers(parse_tally_response(xml_text))
            extracted = len(vouchers)
            connection.start_transaction()
            inserted = updated = 0
            for voucher in vouchers:
                entry_count = len(voucher["ledger_entries"])
                logger.info(
                    "Voucher type=%s number=%s extracted_ledger_entries=%s",
                    voucher["voucher_type"], voucher["voucher_number"], entry_count,
                )
                action = self.repository.save(connection, voucher)
                if action == "INSERTED":
                    inserted += 1
                else:
                    updated += 1
                logger.info(
                    "Voucher type=%s number=%s inserted_ledger_entries=%s",
                    voucher["voucher_type"], voucher["voucher_number"], entry_count,
                )
            self.sync_service.save_checkpoint(connection, "VOUCHER", to_date)
            connection.commit()
        except Exception as error:
            connection.rollback()
            self.sync_service.mark_failed(connection, sync_id, extracted, error)
            raise
        else:
            self.sync_service.mark_success(connection, sync_id, extracted, inserted, updated)
            return VoucherSyncResult(extracted=extracted, inserted=inserted, updated=updated, failed=0)
        finally:
            connection.close()

    def list_vouchers(self) -> list[dict[str, Any]]:
        connection = get_mysql_connection()
        try:
            return self.repository.list_all(connection)
        finally:
            connection.close()

    def list_entries(self) -> list[dict[str, Any]]:
        connection = get_mysql_connection()
        try:
            return self.repository.list_entries(connection)
        finally:
            connection.close()
