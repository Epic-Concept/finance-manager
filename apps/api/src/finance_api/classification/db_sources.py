"""DB-backed gatherer sources and rule application.

Closes the bootstrap loop: confirmed cluster proposals are written as
``ClassificationRule`` rows (the ``rule_expression`` column now holds a regex,
not the retired rule-engine syntax), and ``DbRuleSource`` reads them back as the
``RulePattern`` list the ``RuleGatherer`` consumes.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.classification.bootstrap import ClusterProposal
from finance_api.classification.gatherers.rules import RulePattern
from finance_api.models.classification_rule import ClassificationRule


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
                rule_expression=proposal.suggested_pattern,
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
