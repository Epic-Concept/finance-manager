"""Tests for typed CEL activation building."""

from datetime import date
from decimal import Decimal

from finance_api.classification.cel.activation import (
    activation_from_context,
    activation_from_transaction,
)
from finance_api.classification.gatherer import GatherContext
from finance_api.models.transaction import Transaction


class TestActivationFromContext:
    def test_sign_scale_and_date_fields(self) -> None:
        act = activation_from_context(
            GatherContext(
                transaction_id=1,
                description="TESCO",
                amount=Decimal("-19.99"),
                currency="GBP",
                transaction_date=date(2026, 8, 20),
                account_name="Current",
                merchant_name="Tesco",
            )
        )
        assert act.amount_minor == -199900
        assert act.is_debit is True
        assert act.day_of_month == 20
        assert act.weekday == 3  # Thursday
        assert act.account == "Current"
        assert act.merchant == "Tesco"

    def test_missing_merchant_and_account_become_empty(self) -> None:
        act = activation_from_context(
            GatherContext(
                transaction_id=1,
                description="X",
                amount=Decimal("10.00"),
                currency="PLN",
                transaction_date=date(2026, 1, 1),
            )
        )
        assert act.merchant == ""
        assert act.account == ""
        assert act.is_debit is False
        assert act.amount_minor == 100000


class TestActivationFromTransaction:
    def test_reads_transaction_fields(self) -> None:
        txn = Transaction(
            transaction_date=date(2026, 2, 1),
            description="NETFLIX",
            amount=Decimal("-12.99"),
            currency="GBP",
            account_name="Santander Current",
            merchant_name="Netflix",
        )
        act = activation_from_transaction(txn)
        assert act.description == "NETFLIX"
        assert act.merchant == "Netflix"
        assert act.account == "Santander Current"
        assert act.amount_minor == -129900
