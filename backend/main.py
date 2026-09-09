"""FastAPI application entry point for the TallyPrime integration backend."""

from fastapi import FastAPI

from backend.api.connection_routes import router as connection_router
from backend.api.data_routes import router as data_router
from backend.api.schemas import HealthResponse
from backend.api.sync_routes import router as sync_router


app = FastAPI(
    title="TallyPrime MySQL Integration API",
    version="0.1.0",
    description="Backend integration layer between TallyPrime and MySQL.",
)
app.include_router(connection_router)
app.include_router(data_router)
app.include_router(sync_router)


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Report API process health without disclosing configuration or credentials."""
    return HealthResponse(status="ok", service="tally-mysql-integration-api")
