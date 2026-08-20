"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from finance_api import __version__
from finance_api.db.session import SessionLocal
from finance_api.routers import (
    cohorts_router,
    ledger_router,
    overview_router,
    refinement_router,
    review_router,
)

app = FastAPI(
    title="Finance Manager API",
    description="Personal finance management API",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(refinement_router, prefix="/api/v1/refinement", tags=["refinement"])
app.include_router(review_router, prefix="/api/v1/reviews", tags=["reviews"])
app.include_router(cohorts_router, prefix="/api/v1/cohorts", tags=["cohorts"])
app.include_router(ledger_router, prefix="/api/v1/ledger", tags=["ledger"])
app.include_router(overview_router, prefix="/api/v1", tags=["overview"])


def check_database_health() -> dict[str, str]:
    """Check database connectivity."""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "connected"}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


@app.get("/health")
async def health_check() -> dict[str, str | dict[str, str]]:
    """Health check endpoint with database status."""
    db_status = check_database_health()
    overall_status = "healthy" if db_status["status"] == "connected" else "degraded"
    return {
        "status": overall_status,
        "version": __version__,
        "database": db_status,
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Finance Manager API", "version": __version__}
