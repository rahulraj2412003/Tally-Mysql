"""Response schemas exposed by the API."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class ConnectionTestResponse(BaseModel):
    status: str
    message: str
    details: dict[str, int] | None = None


class SyncSummary(BaseModel):
    extracted: int
    inserted: int
    updated: int
    failed: int


class LedgerSyncResponse(BaseModel):
    status: str
    message: str
    summary: SyncSummary


class LedgerResponse(BaseModel):
    id: int
    name: str
    parent: str | None
    created_at: datetime | None
    updated_at: datetime | None


class LedgerTransactionResponse(BaseModel):
    voucher_id: int
    voucher_date: date
    voucher_type: str | None
    voucher_number: str | None
    narration: str | None
    amount: Decimal


class LedgerDetailData(BaseModel):
    id: int
    name: str
    parent: str | None
    created_at: datetime | None
    updated_at: datetime | None
    transactions: list[LedgerTransactionResponse]


class LedgerDetailResponse(BaseModel):
    status: str
    data: LedgerDetailData


class VoucherSyncRequest(BaseModel):
    from_date: date
    to_date: date


class VoucherSyncResponse(BaseModel):
    status: str
    message: str
    summary: SyncSummary


class FullSyncResponse(BaseModel):
    status: str
    message: str
    summary: SyncSummary


class VoucherResponse(BaseModel):
    id: int
    tally_master_id: int | None
    tally_alter_id: int | None
    tally_voucher_key: str
    voucher_date: date
    voucher_type: str | None
    voucher_number: str | None
    narration: str | None
    created_at: datetime | None
    updated_at: datetime | None


class VoucherEntryResponse(BaseModel):
    id: int
    voucher_id: int
    ledger_id: int
    ledger_name: str
    amount: Decimal


class SyncHistoryResponse(BaseModel):
    id: int
    sync_type: str
    started_at: datetime
    completed_at: datetime | None
    extracted: int | None
    inserted: int | None
    updated: int | None
    failed: int | None
    status: str
    error_message: str | None


class SyncStateResponse(BaseModel):
    entity_type: str
    last_sync_date: date | None
    last_sync_time: datetime | None
    updated_at: datetime | None
