"""Tests for persisting classification decisions (transaction-classification spec).

Covers the categorization-as-splits data model, evidence-chain persistence, and
review-queue routing.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from finance_api.classification.evidence import (
    Claim,
    Evidence,
    EvidenceType,
    Split,
    StrengthTier,
)
from finance_api.classification.policy import Decision, MerchantClass, Outcome
from finance_api.models.category import Category
from finance_api.models.transaction import Transaction
from finance_api.repositories.classification_decision_repository import (
    ClassificationDecisionRepository,
)


def _txn(session: Session, amount: str = "20.00") -> Transaction:
    txn = Transaction(
        transaction_date=date(2026, 6, 1),
        description="AMZN MKTP",
        amount=Decimal(amount),
    )
    session.add(txn)
    session.flush()
    return txn


def _cat(session: Session, name: str) -> Category:
    cat = Category(name=name)
    session.add(cat)
    session.flush()
    return cat


def _ev(claim: Claim, strength: StrengthTier, itemized: bool = False) -> Evidence:
    return Evidence(
        claim=claim,
        evidence_type=EvidenceType.RECEIPT if itemized else EvidenceType.RULE,
        source="src",
        strength=strength,
        itemized=itemized,
    )


class TestRecordAutoApply:
    def test_single_category_persists_one_split_for_full_total(
        self, db_session: Session
    ) -> None:
        txn = _txn(db_session, "20.00")
        cat = _cat(db_session, "Groceries")
        claim = Claim.single_category(cat.id)
        decision = Decision(
            Outcome.AUTO_APPLY,
            claim,
            StrengthTier.STRONG,
            "sufficient",
            (_ev(claim, StrengthTier.STRONG),),
        )

        repo = ClassificationDecisionRepository(db_session)
        recorded = repo.record(
            transaction_id=txn.id,
            transaction_amount=txn.amount,
            decision=decision,
            merchant_class=MerchantClass.SINGLE_CATEGORY,
        )

        assert recorded.outcome == "auto_apply"
        assert len(recorded.splits) == 1
        assert recorded.splits[0].category_id == cat.id
        assert recorded.splits[0].amount == Decimal("20.00")
        assert len(recorded.evidence) == 1
        assert recorded.evidence[0].evidence_type == "rule"

    def test_itemized_split_persists_each_line_summing_to_total(
        self, db_session: Session
    ) -> None:
        txn = _txn(db_session, "20.00")
        c1 = _cat(db_session, "Books")
        c2 = _cat(db_session, "Toys")
        claim = Claim.split(
            [Split(c1.id, Decimal("12.00")), Split(c2.id, Decimal("8.00"))]
        )
        decision = Decision(
            Outcome.AUTO_APPLY,
            claim,
            StrengthTier.PROOF,
            "sufficient",
            (_ev(claim, StrengthTier.PROOF, itemized=True),),
        )

        repo = ClassificationDecisionRepository(db_session)
        recorded = repo.record(
            transaction_id=txn.id,
            transaction_amount=txn.amount,
            decision=decision,
            merchant_class=MerchantClass.SPLITTABLE,
        )

        amounts = sorted(s.amount for s in recorded.splits)
        assert amounts == [Decimal("8.00"), Decimal("12.00")]
        assert sum(s.amount for s in recorded.splits) == txn.amount


class TestReviewRouting:
    def test_review_decision_is_persisted_with_review_outcome(
        self, db_session: Session
    ) -> None:
        txn = _txn(db_session)
        decision = Decision(Outcome.REVIEW, None, StrengthTier.NONE, "no_evidence", ())
        repo = ClassificationDecisionRepository(db_session)
        recorded = repo.record(
            transaction_id=txn.id,
            transaction_amount=txn.amount,
            decision=decision,
            merchant_class=MerchantClass.UNKNOWN,
        )
        assert recorded.outcome == "review"
        assert recorded.splits == []

    def test_pending_reviews_returns_only_review_decisions(
        self, db_session: Session
    ) -> None:
        txn1 = _txn(db_session)
        txn2 = _txn(db_session)
        cat = _cat(db_session, "Groceries")
        repo = ClassificationDecisionRepository(db_session)

        applied_claim = Claim.single_category(cat.id)
        repo.record(
            transaction_id=txn1.id,
            transaction_amount=txn1.amount,
            decision=Decision(
                Outcome.AUTO_APPLY, applied_claim, StrengthTier.STRONG, "sufficient", ()
            ),
            merchant_class=MerchantClass.SINGLE_CATEGORY,
        )
        repo.record(
            transaction_id=txn2.id,
            transaction_amount=txn2.amount,
            decision=Decision(
                Outcome.REVIEW, None, StrengthTier.WEAK, "insufficient_evidence", ()
            ),
            merchant_class=MerchantClass.UNKNOWN,
        )

        pending = repo.pending_reviews()
        assert [d.transaction_id for d in pending] == [txn2.id]
