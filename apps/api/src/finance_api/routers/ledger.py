"""Ledger HTTP API."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from finance_api.db.session import get_db
from finance_api.ledger.spend import SpendTotal, spend_total

router = APIRouter()


@router.get("/spend", response_model=SpendTotal)
def get_spend(
    db: Annotated[Session, Depends(get_db)],
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> SpendTotal:
    """Household spend from journal postings (transfers excluded)."""
    return spend_total(db, start=start, end=end)
