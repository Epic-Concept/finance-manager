"""Typed CEL activation for a bank transaction.

Money enters CEL as integer minor units (amount × 10^4), never as a float.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from finance_api.classification.gatherer import GatherContext

AMOUNT_SCALE = Decimal("10000")


def amount_to_minor(amount: Decimal) -> int:
    """Scale a Decimal amount to integer minor units (× 10^4)."""
    return int((amount * AMOUNT_SCALE).quantize(Decimal("1")))


@dataclass(frozen=True)
class TxnActivation:
    """Values exposed to CEL as ``txn.*``."""

    description: str
    merchant: str
    account: str
    currency: str
    amount_minor: int
    day_of_month: int
    weekday: int
    is_debit: bool

    def as_cel_map(self) -> dict[str, str | int | bool]:
        return {
            "description": self.description,
            "merchant": self.merchant,
            "account": self.account,
            "currency": self.currency,
            "amount_minor": self.amount_minor,
            "day_of_month": self.day_of_month,
            "weekday": self.weekday,
            "is_debit": self.is_debit,
        }


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _as_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _as_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    raise TypeError(f"transaction_date must be date, got {type(value)}")


def build_activation(
    *,
    description: str | None,
    merchant: str | None,
    account: str | None,
    currency: str | None,
    amount: Decimal,
    transaction_date: date,
) -> TxnActivation:
    minor = amount_to_minor(amount)
    return TxnActivation(
        description=_as_str(description),
        merchant=_as_str(merchant),
        account=_as_str(account),
        currency=_as_str(currency) or "GBP",
        amount_minor=minor,
        day_of_month=transaction_date.day,
        weekday=transaction_date.weekday(),
        is_debit=minor < 0,
    )


def activation_from_context(context: GatherContext) -> TxnActivation:
    return build_activation(
        description=context.description,
        merchant=context.merchant_name,
        account=context.account_name,
        currency=context.currency,
        amount=context.amount,
        transaction_date=context.transaction_date,
    )


def activation_from_transaction(txn: Any) -> TxnActivation:
    """Build an activation from a Transaction or a duck-typed test double."""
    return build_activation(
        description=_as_str(getattr(txn, "description", None)),
        merchant=_as_str(getattr(txn, "merchant_name", None)),
        account=_as_str(getattr(txn, "account_name", None)),
        currency=_as_str(getattr(txn, "currency", None)) or "GBP",
        amount=_as_decimal(txn.amount),
        transaction_date=_as_date(txn.transaction_date),
    )
