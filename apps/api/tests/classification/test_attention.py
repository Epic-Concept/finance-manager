"""Tests for the money-at-risk interrupt budget."""

from datetime import date
from decimal import Decimal

from finance_api.classification.attention import AttentionKind, classify_attention
from finance_api.classification.evidence import StrengthTier
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.policy import Decision, MerchantClass, Outcome

CAP = 2_000_000  # £200


def _ctx(amount: str, description: str = "X") -> GatherContext:
    return GatherContext(
        transaction_id=1,
        description=description,
        amount=Decimal(amount),
        currency="GBP",
        transaction_date=date(2026, 6, 1),
    )


def test_auto_apply_is_silent() -> None:
    decision = Decision(Outcome.AUTO_APPLY, None, StrengthTier.PROOF, "sufficient")
    assert (
        classify_attention(
            decision, _ctx("-5.00"), MerchantClass.UNKNOWN, cap_minor=CAP
        )
        is AttentionKind.SILENT
    )


def test_small_unknown_is_queued() -> None:
    decision = Decision(Outcome.REVIEW, None, StrengthTier.NONE, "no_evidence")
    assert (
        classify_attention(
            decision, _ctx("-4.50", "NEW CAFE"), MerchantClass.UNKNOWN, cap_minor=CAP
        )
        is AttentionKind.QUEUE
    )


def test_large_unknown_interrupts() -> None:
    decision = Decision(Outcome.REVIEW, None, StrengthTier.NONE, "no_evidence")
    assert (
        classify_attention(
            decision,
            _ctx("-250.00", "MYSTERY LTD"),
            MerchantClass.UNKNOWN,
            cap_minor=CAP,
        )
        is AttentionKind.INTERRUPT
    )


def test_large_known_merchant_does_not_use_unknown_tripwire() -> None:
    decision = Decision(Outcome.REVIEW, None, StrengthTier.WEAK, "insufficient")
    assert (
        classify_attention(
            decision,
            _ctx("-250.00", "TESCO"),
            MerchantClass.SINGLE_CATEGORY,
            cap_minor=CAP,
            merchant_known=True,
        )
        is AttentionKind.QUEUE
    )


def test_contested_interrupts() -> None:
    decision = Decision(Outcome.REVIEW, None, StrengthTier.STRONG, "contested")
    assert (
        classify_attention(
            decision, _ctx("-5.00"), MerchantClass.UNKNOWN, cap_minor=CAP
        )
        is AttentionKind.INTERRUPT
    )
