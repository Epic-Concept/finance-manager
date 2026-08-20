"""DB-backed gatherer sources and rule application.

Closes the bootstrap loop: confirmed cluster proposals are written as
``ClassificationRule`` rows (``rule_expression`` holds CEL), and
``DbRuleSource`` reads them back as the ``RulePattern`` list the
``RuleGatherer`` consumes. Legacy regex strings are migrated on write.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.classification.bootstrap import ClusterProposal
from finance_api.classification.cel import migrate_rule_expression
from finance_api.classification.gatherers.history import HistoryOutcome
from finance_api.classification.gatherers.rules import RulePattern
from finance_api.classification.learning import merchant_key
from finance_api.classification.policy import Outcome
from finance_api.models.classification_decision import ClassificationDecision
from finance_api.models.classification_rule import ClassificationRule
from finance_api.models.transaction import Transaction


def apply_proposals(
    session: Session,
    confirmed: Sequence[tuple[ClusterProposal, int | None]],
) -> int:
    """Write confirmed cluster proposals as active classification rules.

    Each entry pairs a proposal with the human-confirmed category id (or None to
    skip). Returns the number of rules created.
    """
    created = 0
    for proposal, category_id in confirmed:
        if category_id is None:
            continue
        session.add(
            ClassificationRule(
                name=proposal.cluster_key,
                rule_expression=migrate_rule_expression(proposal.suggested_pattern),
                category_id=category_id,
                priority=0,
                is_active=True,
            )
        )
        created += 1
    session.flush()
    return created


class DbRuleSource:
    """Reads active classification rules as RulePatterns (priority order)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def active_rules(self) -> list[RulePattern]:
        stmt = (
            select(ClassificationRule)
            .where(ClassificationRule.is_active.is_(True))
            .order_by(ClassificationRule.priority, ClassificationRule.id)
        )
        return [
            RulePattern(
                pattern=rule.rule_expression,
                category_id=rule.category_id,
                name=rule.name,
            )
            for rule in self._session.scalars(stmt)
        ]


class DbHistorySource:
    """Reads prior per-merchant outcomes from persisted classification decisions.

    Surfaces the category a merchant resolved to before, so the HistoryGatherer
    can contribute in production. Only applied (``AUTO_APPLY``) or human-confirmed
    single-category decisions count; the ``human_confirmed`` flag lets the
    gatherer's self-confirmation guard gate STRONG promotion.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def outcomes_for(self, description: str) -> list[HistoryOutcome]:
        key = merchant_key(description)
        if not key:
            return []

        stmt = (
            select(ClassificationDecision, Transaction.description)
            .join(Transaction, ClassificationDecision.transaction_id == Transaction.id)
            .where(Transaction.description.ilike(f"%{key}%"))
        )
        outcomes: list[HistoryOutcome] = []
        for decision, txn_description in self._session.execute(stmt):
            if merchant_key(txn_description) != key:
                continue
            applied = decision.outcome == Outcome.AUTO_APPLY.value or decision.confirmed
            if not applied or len(decision.splits) != 1:
                continue
            outcomes.append(
                HistoryOutcome(
                    category_id=decision.splits[0].category_id,
                    human_confirmed=decision.confirmed,
                )
            )
        return outcomes
