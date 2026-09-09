"""Synchronization routes that delegate all integration work to services."""

from fastapi import APIRouter, HTTPException, status
from datetime import date

from backend.api.schemas import (
    LedgerSyncResponse,
    FullSyncResponse,
    SyncSummary,
    SyncHistoryResponse,
    SyncStateResponse,
    VoucherSyncRequest,
    VoucherSyncResponse,
)
from backend.services.ledger_service import LedgerService
from backend.services.voucher_service import VoucherService
from backend.services.sync_service import SyncService, SynchronizationService


router = APIRouter(prefix="/api/sync", tags=["synchronization"])


SYNC_START_DATE = date(2000, 1, 1)


def _full_response(message: str, result: object) -> FullSyncResponse:
    return FullSyncResponse(
        status="success",
        message=message,
        summary=SyncSummary(
            extracted=result.extracted,
            inserted=result.inserted,
            updated=result.updated,
            failed=result.failed,
        ),
    )


@router.post("/full", response_model=FullSyncResponse)
def sync_full() -> FullSyncResponse:
    try:
        result = SynchronizationService().synchronize_full(SYNC_START_DATE, date.today())
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Full synchronization could not be completed.",
        ) from error
    return _full_response("Full synchronization completed.", result)


@router.post("/incremental", response_model=FullSyncResponse)
def sync_incremental() -> FullSyncResponse:
    try:
        result = SynchronizationService().synchronize_incremental(SYNC_START_DATE, date.today())
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Incremental synchronization could not be completed.",
        ) from error
    return _full_response("Incremental synchronization completed.", result)


@router.post("/ledgers", response_model=LedgerSyncResponse)
def sync_ledgers() -> LedgerSyncResponse:
    try:
        result = LedgerService().synchronize()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ledger synchronization could not be completed.",
        ) from error

    return LedgerSyncResponse(
        status="success",
        message="Ledger synchronization completed.",
        summary=SyncSummary(
            extracted=result.extracted,
            inserted=result.inserted,
            updated=result.updated,
            failed=result.failed,
        ),
    )


@router.post("/vouchers", response_model=VoucherSyncResponse)
def sync_vouchers(request: VoucherSyncRequest) -> VoucherSyncResponse:
    try:
        result = VoucherService().synchronize(request.from_date, request.to_date)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voucher synchronization could not be completed.",
        ) from error

    return VoucherSyncResponse(
        status="success",
        message="Voucher synchronization completed.",
        summary=SyncSummary(
            extracted=result.extracted,
            inserted=result.inserted,
            updated=result.updated,
            failed=result.failed,
        ),
    )


@router.get("/history", response_model=list[SyncHistoryResponse])
def sync_history() -> list[SyncHistoryResponse]:
    try:
        return [SyncHistoryResponse.model_validate(record) for record in SyncService().history()]
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Synchronization history is currently unavailable.",
        ) from error


@router.get("/state", response_model=list[SyncStateResponse])
def sync_state() -> list[SyncStateResponse]:
    try:
        return [SyncStateResponse.model_validate(record) for record in SyncService().state()]
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Synchronization state is currently unavailable.",
        ) from error
