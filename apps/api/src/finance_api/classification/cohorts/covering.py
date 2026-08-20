"""Sequential covering: propose CEL cohorts, confirm to mint rules."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.classification.cel import migrate_rule_expression
from finance_api.classification.cohorts.clustering import (
    CohortCluster,
    hierarchical_clusters,
)
from finance_api.classification.cohorts.synthesize import (
    labelled_false_positives,
    llm_cel,
    template_cel,
)
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.classification.policy import Outcome
from finance_api.models.classification_decision import ClassificationDecision
from finance_api.models.classification_rule import ClassificationRule
from finance_api.models.transaction import Transaction


def pending_review_transactions(session: Session) -> list[Transaction]:
    """Transactions whose latest decision is unconfirmed review."""
    stmt = (
        select(Transaction)
        .join(
            ClassificationDecision,
            ClassificationDecision.transaction_id == Transaction.id,
        )
        .where(ClassificationDecision.outcome == Outcome.REVIEW.value)
        .where(ClassificationDecision.confirmed.is_(False))
    )
    return list(session.scalars(stmt))


@dataclass(frozen=True)
class CohortProposal:
    """A confirmable group: CEL predicate + residual transaction ids."""

    cohort_id: str
    stage: str
    cluster_key: str
    expression: str
    transaction_ids: tuple[int, ...]
    sample_descriptions: tuple[str, ...]
    proposed_category_id: int | None
    proposed_category_name: str
    labelled_false_positives: int
    source: str  # template | llm


def _cohort_id(stage: str, key: str, ids: Sequence[int]) -> str:
    payload = f"{stage}|{key}|{','.join(str(i) for i in sorted(ids))}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class CohortDiscovery:
    """Yield high-precision CEL cohorts from residual transactions.

    Confirm writes a rule and removes matching residual ids. Skip records the
    cluster key so it is not immediately re-proposed. No rule is written
    without confirm.
    """

    def __init__(
        self,
        residual: Sequence[Any],
        universe: Sequence[Any],
        labelled: dict[int, int] | None = None,
        categories: Sequence[CategoryRef] | None = None,
        llm: Any | None = None,
        min_size: int = 2,
    ) -> None:
        self._residual = list(residual)
        self._universe = list(universe)
        self._labelled = dict(labelled or {})
        self._categories = list(categories or [])
        self._llm = llm
        self._min_size = min_size
        self._skipped: set[str] = set()

    @property
    def residual(self) -> list[Any]:
        return list(self._residual)

    def _from_cluster(
        self, cluster: CohortCluster, category_id: int | None = None
    ) -> CohortProposal | None:
        if cluster.cluster_key in self._skipped:
            return None
        ids = tuple(int(t.id) for t in cluster.transactions)
        in_labels = {self._labelled[i] for i in ids if i in self._labelled}
        if len(in_labels) > 1:
            return None  # mixed intents in one token; split rather than overfit
        expression = template_cel(cluster)
        fps = labelled_false_positives(
            expression, self._universe, set(ids), self._labelled
        )
        source = "template"
        if fps and self._llm is not None:
            llm_expr = llm_cel(cluster, self._llm)
            if llm_expr is not None:
                llm_fps = labelled_false_positives(
                    llm_expr, self._universe, set(ids), self._labelled
                )
                if len(llm_fps) < len(fps):
                    expression, fps, source = llm_expr, llm_fps, "llm"
        if fps:
            return None  # mixed cluster: split by not proposing a catch-all
        name = ""
        if category_id is not None:
            for cat in self._categories:
                if cat.id == category_id:
                    name = cat.name
                    break
        return CohortProposal(
            cohort_id=_cohort_id(cluster.stage, cluster.cluster_key, ids),
            stage=cluster.stage,
            cluster_key=cluster.cluster_key,
            expression=expression,
            transaction_ids=ids,
            sample_descriptions=cluster.sample_descriptions,
            proposed_category_id=category_id,
            proposed_category_name=name,
            labelled_false_positives=0,
            source=source,
        )

    def proposals(self, top_n: int = 100) -> list[CohortProposal]:
        clusters, _leftovers = hierarchical_clusters(
            self._residual, min_size=self._min_size
        )
        out: list[CohortProposal] = []
        for cluster in clusters:
            proposal = self._from_cluster(cluster)
            if proposal is not None:
                out.append(proposal)
            if len(out) >= top_n:
                break
        return out

    def leftovers(self) -> list[Any]:
        _clusters, leftovers = hierarchical_clusters(
            self._residual, min_size=self._min_size
        )
        return leftovers

    def confirm(
        self,
        session: Session,
        proposal: CohortProposal,
        category_id: int,
        *,
        name: str | None = None,
    ) -> ClassificationRule:
        rule = ClassificationRule(
            name=name or proposal.cluster_key[:100],
            rule_expression=migrate_rule_expression(proposal.expression),
            category_id=category_id,
            priority=0,
            is_active=True,
        )
        session.add(rule)
        session.flush()
        covered = set(proposal.transaction_ids)
        self._residual = [t for t in self._residual if t.id not in covered]
        return rule

    def skip(self, proposal: CohortProposal) -> None:
        self._skipped.add(proposal.cluster_key)
