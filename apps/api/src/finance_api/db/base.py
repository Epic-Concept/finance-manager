"""SQLAlchemy declarative base."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Import all models here for Alembic to discover them
# This ensures all models are registered with the Base.metadata
def import_models() -> None:
    """Import all models to register them with SQLAlchemy metadata."""
    from finance_api.models import (  # noqa: F401
        BankSession,
        Category,
        CategoryClosure,
        OnlinePurchase,
        Transaction,
        TransactionCategory,
    )
