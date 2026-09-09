"""Connection routes with no direct database or Tally implementation details."""

from fastapi import APIRouter, HTTPException, status

from backend.api.schemas import ConnectionTestResponse
from backend.services.connection_service import check_mysql_connection, check_tally_connection


router = APIRouter(prefix="/api", tags=["connections"])


@router.post("/tally/test", response_model=ConnectionTestResponse)
def test_tally() -> ConnectionTestResponse:
    try:
        ledger_count = check_tally_connection()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to connect to or validate the TallyPrime response.",
        ) from error
    return ConnectionTestResponse(
        status="success",
        message="TallyPrime connection successful.",
        details={"ledgers_parsed": ledger_count},
    )


@router.post("/mysql/test", response_model=ConnectionTestResponse)
def test_mysql() -> ConnectionTestResponse:
    try:
        check_mysql_connection()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to connect to MySQL.",
        ) from error
    return ConnectionTestResponse(status="success", message="MySQL connection successful.")
