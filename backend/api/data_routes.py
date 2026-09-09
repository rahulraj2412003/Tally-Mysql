"""Read-only routes for synchronized data."""

from fastapi import APIRouter, HTTPException, status

from backend.api.schemas import (
    LedgerDetailData,
    LedgerDetailResponse,
    LedgerResponse,
    VoucherEntryResponse,
    VoucherResponse,
)
from backend.services.ledger_service import LedgerService
from backend.services.voucher_service import VoucherService


router = APIRouter(prefix="/api", tags=["data"])


@router.get("/ledgers", response_model=list[LedgerResponse])
def list_ledgers() -> list[LedgerResponse]:
    try:
        return [LedgerResponse.model_validate(ledger) for ledger in LedgerService().list_ledgers()]
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ledger records are currently unavailable.",
        ) from error


@router.get("/ledgers/{ledger_id}", response_model=LedgerDetailResponse)
def get_ledger_details(ledger_id: int) -> LedgerDetailResponse:
    try:
        ledger = LedgerService().get_ledger_details(ledger_id)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ledger details are currently unavailable.",
        ) from error

    if ledger is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ledger {ledger_id} was not found.",
        )

    return LedgerDetailResponse(
        status="success",
        data=LedgerDetailData.model_validate(ledger),
    )


@router.get("/vouchers", response_model=list[VoucherResponse])
def list_vouchers() -> list[VoucherResponse]:
    try:
        return [VoucherResponse.model_validate(voucher) for voucher in VoucherService().list_vouchers()]
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voucher records are currently unavailable.",
        ) from error


@router.get("/voucher-entries", response_model=list[VoucherEntryResponse])
def list_voucher_entries() -> list[VoucherEntryResponse]:
    try:
        return [
            VoucherEntryResponse.model_validate(entry)
            for entry in VoucherService().list_entries()
        ]
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voucher entry records are currently unavailable.",
        ) from error
