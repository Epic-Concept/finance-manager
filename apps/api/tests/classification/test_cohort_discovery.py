"""Tests for hierarchical clustering, CEL templates, and sequential covering."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from finance_api.classification.cel import CelEvaluator, activation_from_transaction
from finance_api.classification.cohorts import (
    CohortDiscovery,
    hierarchical_clusters,
    llm_cel,
    template_cel,
)
from finance_api.models.category import Category
from finance_api.models.transaction import Transaction


def _txn(
    session: Session | None,
    *,
    description: str,
    amount: str,
    account: str = "Current",
    day: int = 1,
    txn_id: int | None = None,
) -> Transaction:
    txn = Transaction(
        transaction_date=date(2026, 6, day),
        description=description,
        amount=Decimal(amount),
        currency="GBP",
        account_name=account,
    )
    if session is not None:
        session.add(txn)
        session.flush()
    elif txn_id is not None:
        txn.id = txn_id
    return txn


class TestHierarchicalClusters:
    def test_subscriptions_separate_from_variable_tickets(self) -> None:
        netflix = [
            _txn(None, description="NETFLIX.COM", amount="-12.99", txn_id=i, day=5)
            for i in range(1, 5)
        ]
        extras = [
            _txn(
                None,
                description="NETFLIX.COM",
                amount=f"-{20 + i}.00",
                txn_id=10 + i,
                day=12,
            )
            for i in range(3)
        ]
        clusters, leftovers = hierarchical_clusters(netflix + extras, min_size=2)
        stages = {c.stage for c in clusters}
        assert "A" in stages
        stage_a = next(c for c in clusters if c.stage == "A")
        assert stage_a.size == 4
        assert all(t.amount == Decimal("-12.99") for t in stage_a.transactions)

    def test_polluted_first_token_does_not_merge_after_specific_stage(self) -> None:
        tesco = [
            _txn(None, description="TESCO STORES", amount="-40.00", txn_id=i)
            for i in range(1, 4)
        ]
        other = [
            _txn(None, description="TESCO BANK", amount="-5.00", txn_id=20 + i)
            for i in range(3)
        ]
        clusters, _ = hierarchical_clusters(tesco + other, min_size=2)
        # Stage A keys include amount, so the two groups stay apart.
        keys = {c.cluster_key for c in clusters if c.stage == "A"}
        assert len(keys) == 2


class TestTemplateCel:
    def test_fixed_amount_includes_amount_minor(self) -> None:
        txns = [
            _txn(None, description="NETFLIX.COM", amount="-12.99", txn_id=i)
            for i in range(1, 4)
        ]
        clusters, _ = hierarchical_clusters(txns, min_size=2)
        expr = template_cel(clusters[0])
        assert "amount_minor" in expr
        assert "is_debit" in expr
        ev = CelEvaluator()
        assert ev.matches(expr, activation_from_transaction(txns[0])) is True


class TestCohortDiscovery:
    def test_residual_shrinks_on_confirm(self, db_session: Session) -> None:
        groceries = Category(name="Groceries")
        db_session.add(groceries)
        db_session.flush()
        txns = [
            _txn(db_session, description="TESCO STORES", amount="-20.00")
            for _ in range(4)
        ]
        leftover = _txn(db_session, description="UNKNOWN CAFE", amount="-4.00")
        discovery = CohortDiscovery(txns + [leftover], txns + [leftover], min_size=2)
        proposals = discovery.proposals()
        assert proposals
        before = len(discovery.residual)
        discovery.confirm(db_session, proposals[0], groceries.id)
        assert len(discovery.residual) < before
        assert leftover in discovery.residual

    def test_polluted_labelled_cluster_is_not_proposed(
        self, db_session: Session
    ) -> None:
        groceries = Category(name="Groceries")
        transfer = Category(name="Internal Transfer")
        db_session.add_all([groceries, transfer])
        db_session.flush()
        spend = [
            _txn(db_session, description="PRZELEW JAN", amount="-50.00")
            for _ in range(3)
        ]
        xfer = [
            _txn(db_session, description="PRZELEW JAN", amount="-50.00")
            for _ in range(3)
        ]
        labelled = {t.id: groceries.id for t in spend}
        labelled.update({t.id: transfer.id for t in xfer})
        discovery = CohortDiscovery(
            spend + xfer, spend + xfer, labelled=labelled, min_size=2
        )
        assert discovery.proposals() == []

    def test_invalid_llm_cel_is_discarded(self) -> None:
        class _Bad:
            def complete(self, system: str, user: str) -> str:
                return '{"expression": "txn.description.matches("}'

        txns = [
            _txn(None, description="TESCO STORES", amount="-10.00", txn_id=i)
            for i in range(1, 4)
        ]
        clusters, _ = hierarchical_clusters(txns, min_size=2)
        assert llm_cel(clusters[0], _Bad()) is None

    def test_template_path_does_not_need_llm(self) -> None:
        txns = [
            _txn(None, description="TESCO STORES", amount="-10.00", txn_id=i)
            for i in range(1, 4)
        ]
        discovery = CohortDiscovery(txns, txns, min_size=2)
        proposals = discovery.proposals()
        assert proposals
        assert proposals[0].source == "template"
        assert "matches" in proposals[0].expression
