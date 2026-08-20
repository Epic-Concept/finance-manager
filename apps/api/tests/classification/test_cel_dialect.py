"""Locked CEL dialect for classification rules."""

from datetime import date
from decimal import Decimal

from finance_api.classification.cel import (
    CelEvaluator,
    activation_from_context,
    amount_to_minor,
)
from finance_api.classification.gatherer import GatherContext


def _ctx(
    description: str = "TESCO STORES",
    amount: str = "-12.50",
    account: str | None = "Santander Current",
    merchant: str | None = "Tesco",
    day: int = 3,
) -> GatherContext:
    return GatherContext(
        transaction_id=1,
        description=description,
        amount=Decimal(amount),
        currency="GBP",
        transaction_date=date(2026, 6, day),
        account_name=account,
        merchant_name=merchant,
    )


class TestCelDialect:
    def setup_method(self) -> None:
        self.ev = CelEvaluator()

    def test_description_matches_case_insensitive(self) -> None:
        act = activation_from_context(_ctx("TESCO STORES"))
        assert self.ev.matches('txn.description.matches("(?i)tesco")', act) is True
        assert self.ev.matches('txn.description.matches("(?i)amazon")', act) is False

    def test_is_debit_and_conjunction(self) -> None:
        act = activation_from_context(_ctx(amount="-12.50"))
        assert (
            self.ev.matches('txn.is_debit && txn.description.matches("(?i)tesco")', act)
            is True
        )
        credit = activation_from_context(_ctx(amount="12.50"))
        assert (
            self.ev.matches(
                'txn.is_debit && txn.description.matches("(?i)tesco")', credit
            )
            is False
        )

    def test_amount_minor_equality(self) -> None:
        act = activation_from_context(_ctx(amount="-12.99"))
        assert self.ev.matches("txn.amount_minor == -129900", act) is True
        assert self.ev.matches("txn.amount_minor == 0", act) is False

    def test_account_equality(self) -> None:
        act = activation_from_context(_ctx())
        assert self.ev.matches('txn.account == "Santander Current"', act) is True
        assert self.ev.matches('txn.account == "Savings"', act) is False

    def test_day_of_month_and_rent(self) -> None:
        act = activation_from_context(_ctx("RENT PAYMENT", amount="-1250.00", day=3))
        expr = 'txn.day_of_month <= 5 && txn.description.matches("(?i)rent")'
        assert self.ev.matches(expr, act) is True
        late = activation_from_context(_ctx("RENT PAYMENT", day=20))
        assert self.ev.matches(expr, late) is False

    def test_invalid_expression_returns_none(self) -> None:
        act = activation_from_context(_ctx())
        assert self.ev.matches("txn.description.matches(", act) is None


class TestAmountMinorScale:
    def test_two_decimal_pounds(self) -> None:
        assert amount_to_minor(Decimal("-42.50")) == -425000

    def test_positive_income(self) -> None:
        assert amount_to_minor(Decimal("1250.00")) == 12500000

    def test_four_decimal_places(self) -> None:
        assert amount_to_minor(Decimal("1.2345")) == 12345
