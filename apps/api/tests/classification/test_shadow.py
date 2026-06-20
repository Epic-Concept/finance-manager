"""Tests for the shadow-mode runner (task 7.3).

Runs the engine over historical transactions without side effects and reports
what would happen (auto-apply vs review, by reason) plus parity against the
existing category assignments.
"""

from datetime import date
from decimal import Decimal

from finance_api.classification.engine import EngineOutcome
from finance_api.classification.evidence import Claim, StrengthTier
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.policy import Decision, MerchantClass, Outcome
from finance_api.classification.shadow import ShadowItem, run_shadow


class _FakeEngine:
    """Returns a preset outcome per transaction id."""

    def __init__(self, outcomes: dict[int, EngineOutcome]) -> None:
        self._outcomes = outcomes

    def classify(self, context: GatherContext) -> EngineOutcome:
        return self._outcomes[context.transaction_id]


def _ctx(txn_id: int) -> GatherContext:
    return GatherContext(
        transaction_id=txn_id,
        description=f"merchant {txn_id}",
        amount=Decimal("10.00"),
        currency="GBP",
        transaction_date=date(2026, 6, 1),
    )


def _auto(category: int) -> EngineOutcome:
    return EngineOutcome(
        decision=Decision(
            Outcome.AUTO_APPLY,
            Claim.single_category(category),
            StrengthTier.STRONG,
            "sufficient",
        ),
        merchant_class=MerchantClass.SINGLE_CATEGORY,
    )


def _review(reason: str) -> EngineOutcome:
    return EngineOutcome(
        decision=Decision(Outcome.REVIEW, None, StrengthTier.WEAK, reason),
        merchant_class=MerchantClass.UNKNOWN,
    )


class TestShadowRunner:
    def test_counts_auto_and_review_by_reason(self) -> None:
        engine = _FakeEngine(
            {1: _auto(5), 2: _review("no_evidence"), 3: _review("contested")}
        )
        items = [ShadowItem(_ctx(1)), ShadowItem(_ctx(2)), ShadowItem(_ctx(3))]
        report = run_shadow(engine, items)
        assert report.total == 3
        assert report.auto_applied == 1
        assert report.review == 2
        assert report.by_reason == {
            "sufficient": 1,
            "no_evidence": 1,
            "contested": 1,
        }

    def test_parity_counts_only_auto_applied_with_known_current_category(self) -> None:
        engine = _FakeEngine({1: _auto(5), 2: _auto(8), 3: _auto(5), 4: _review("x")})
        items = [
            ShadowItem(_ctx(1), current_category_id=5),  # match
            ShadowItem(_ctx(2), current_category_id=9),  # mismatch
            ShadowItem(_ctx(3), current_category_id=None),  # excluded (no current)
            ShadowItem(_ctx(4), current_category_id=5),  # excluded (review)
        ]
        report = run_shadow(engine, items)
        assert report.parity_total == 2
        assert report.parity_matches == 1
        assert report.parity_rate == 0.5
