"""Tests for the DB-backed gatherer sources and rule application.

Closes the bootstrap loop: confirmed cluster proposals become ClassificationRule
rows; DbRuleSource reads them back as RulePattern for the RuleGatherer.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from finance_api.classification.bootstrap import ClusterProposal
from finance_api.classification.db_sources import DbRuleSource, apply_proposals
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.gatherers.rules import RuleGatherer
from finance_api.models.category import Category


def _cat(session: Session, name: str) -> Category:
    cat = Category(name=name)
    session.add(cat)
    session.flush()
    return cat


def _proposal(key: str, category_id: int) -> ClusterProposal:
    return ClusterProposal(
        cluster_key=key,
        transaction_count=10,
        sample_descriptions=(f"{key} shop",),
        proposed_category_id=category_id,
        proposed_category_name="x",
        confidence="high",
        suggested_pattern=f"(?i){key}",
    )


class TestApplyProposals:
    def test_confirmed_proposals_become_active_rules(self, db_session: Session) -> None:
        groceries = _cat(db_session, "Groceries")
        count = apply_proposals(
            db_session, [(_proposal("ZABKA", groceries.id), groceries.id)]
        )
        assert count == 1
        rules = DbRuleSource(db_session).active_rules()
        assert len(rules) == 1
        assert rules[0].pattern == "(?i)ZABKA"
        assert rules[0].category_id == groceries.id
        assert rules[0].name == "ZABKA"

    def test_unresolved_proposal_is_skipped(self, db_session: Session) -> None:
        # category_id None (the human didn't confirm a category) -> no rule
        count = apply_proposals(db_session, [(_proposal("MYSTERY", 0), None)])
        assert count == 0
        assert DbRuleSource(db_session).active_rules() == []


class TestDbRuleSourceWithGatherer:
    def test_rule_gatherer_classifies_via_bootstrapped_rule(
        self, db_session: Session
    ) -> None:
        groceries = _cat(db_session, "Groceries")
        apply_proposals(db_session, [(_proposal("ZABKA", groceries.id), groceries.id)])

        gatherer = RuleGatherer(DbRuleSource(db_session))
        context = GatherContext(
            transaction_id=1,
            description="ZABKA ZE733 K.1",
            amount=Decimal("4.50"),
            currency="PLN",
            transaction_date=date(2026, 6, 1),
        )
        evidence = gatherer.gather(context)
        assert len(evidence) == 1
        assert evidence[0].claim.category_ids == (groceries.id,)
