"""The shadow learner (classification-learning spec, group 8).

An asynchronous observer of confirmed ``(evidence -> decision)`` outcomes. It
runs entirely off the classification hot path (it consumes a stream of persisted
observations; it is never called from ``ClassificationEngine.classify``) and:

- proposes deterministic merchant->category rules from repeated, consistent,
  human-confirmed outcomes (self-confirmation guard: at least one human
  confirmation is required);
- respects the cache asymmetry: single-category mappings are cacheable, variable
  splits are not -- only an exact, recurring identical charge yields a split
  template;
- keeps the policy gate human-owned: it only *recommends* recalibration, never
  applies it (no method mutates the required-tier table).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from finance_api.classification.cel import cel_for_merchant
from finance_api.classification.evidence import Claim
from finance_api.classification.gatherers.mailbox import merchant_terms


def merchant_key(description: str) -> str:
    """The first significant token of a description, used to group observations."""
    terms = merchant_terms(description)
    return terms[0] if terms else ""


def observe(
    description: str, claim: Claim, human_confirmed: bool
) -> LearningObservation:
    """Build a learning observation from a confirmed categorization (task 8.1).

    This is the event-stream emission: confirmed outcomes are turned into
    observations and consumed by the learner asynchronously, never on the
    classification hot path.
    """
    key = merchant_key(description)
    if claim.itemized:
        signature = tuple(
            (s.category_id, s.amount if s.amount is not None else Decimal("0"))
            for s in claim.splits
        )
        total = sum((amount for _, amount in signature), Decimal("0"))
        return LearningObservation(
            merchant_key=key,
            category_id=claim.splits[0].category_id,
            human_confirmed=human_confirmed,
            is_split=True,
            total_amount=total,
            split_signature=signature,
        )
    return LearningObservation(
        merchant_key=key,
        category_id=claim.category_ids[0],
        human_confirmed=human_confirmed,
        is_split=False,
    )


@dataclass(frozen=True)
class LearningObservation:
    """A confirmed outcome emitted to the learner (the event-stream payload)."""

    merchant_key: str
    category_id: int
    human_confirmed: bool
    is_split: bool = False
    total_amount: Decimal | None = None
    # ((category_id, amount), ...) identifying an exact split, for recurring detection
    split_signature: tuple[tuple[int, Decimal], ...] | None = None


@dataclass(frozen=True)
class ProposedRule:
    merchant_key: str
    category_id: int
    support: int
    expression: str


@dataclass(frozen=True)
class SplitTemplate:
    merchant_key: str
    total_amount: Decimal
    splits: tuple[tuple[int, Decimal], ...]
    support: int


@dataclass(frozen=True)
class RecalibrationRecommendation:
    """A surfaced, advisory recalibration suggestion. Never auto-applied."""

    message: str
    requires_human_approval: bool = True


class ShadowLearner:
    """Turns confirmed outcomes into rule proposals; recommends, never applies."""

    def __init__(self, min_observations: int = 3) -> None:
        self._min = min_observations

    def propose_rules(
        self, observations: Iterable[LearningObservation]
    ) -> list[ProposedRule]:
        """Propose merchant->single-category rules from stable confirmed outcomes."""
        by_merchant: dict[str, list[LearningObservation]] = {}
        for obs in observations:
            if obs.is_split:
                continue  # splits never become merchant->category rules
            by_merchant.setdefault(obs.merchant_key, []).append(obs)

        proposals: list[ProposedRule] = []
        for key, group in by_merchant.items():
            categories = {o.category_id for o in group}
            if len(categories) != 1:
                continue  # not unanimous
            if len(group) < self._min:
                continue  # not enough support
            if not any(o.human_confirmed for o in group):
                continue  # self-confirmation guard
            proposals.append(
                ProposedRule(
                    key,
                    next(iter(categories)),
                    len(group),
                    cel_for_merchant(key),
                )
            )
        return proposals

    def detect_recurring_splits(
        self, observations: Iterable[LearningObservation]
    ) -> list[SplitTemplate]:
        """Propose split templates only for exact, recurring identical charges."""
        groups: dict[
            tuple[str, Decimal | None, tuple[tuple[int, Decimal], ...]],
            list[LearningObservation],
        ] = {}
        for obs in observations:
            if not obs.is_split or obs.split_signature is None:
                continue
            groups.setdefault(
                (obs.merchant_key, obs.total_amount, obs.split_signature), []
            ).append(obs)

        templates: list[SplitTemplate] = []
        for (key, total, signature), group in groups.items():
            if len(group) < self._min:
                continue
            if not any(o.human_confirmed for o in group):
                continue
            templates.append(
                SplitTemplate(
                    merchant_key=key,
                    total_amount=total if total is not None else Decimal("0"),
                    splits=signature,
                    support=len(group),
                )
            )
        return templates

    def recommend_recalibration(
        self, observed_accuracy: float, label: str
    ) -> RecalibrationRecommendation:
        """Surface a recalibration suggestion for human approval (never applied)."""
        if observed_accuracy >= 0.99:
            msg = (
                f"{label}: {observed_accuracy:.1%} confirmed-correct — "
                "safe to consider loosening the required tier."
            )
        elif observed_accuracy < 0.95:
            msg = (
                f"{label}: {observed_accuracy:.1%} confirmed-correct — "
                "consider tightening the required tier."
            )
        else:
            msg = f"{label}: {observed_accuracy:.1%} — within the expected range."
        return RecalibrationRecommendation(message=msg, requires_human_approval=True)
