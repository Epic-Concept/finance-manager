"""ADHD interrupt budget: silent / queue / interrupt-now."""

from __future__ import annotations

from enum import Enum

from finance_api.classification.cel.activation import amount_to_minor
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.policy import Decision, MerchantClass, Outcome


class AttentionKind(Enum):
    SILENT = "silent"
    QUEUE = "queue"
    INTERRUPT = "interrupt"


def classify_attention(
    decision: Decision,
    context: GatherContext,
    merchant_class: MerchantClass,
    *,
    cap_minor: int,
    merchant_known: bool = False,
) -> AttentionKind:
    """Decide how loudly to bother a human about this decision."""
    abs_minor = abs(amount_to_minor(context.amount))
    known = merchant_known or merchant_class is MerchantClass.SINGLE_CATEGORY

    if decision.outcome is Outcome.AUTO_APPLY:
        return AttentionKind.SILENT
    if decision.reason == "contested":
        return AttentionKind.INTERRUPT
    if (
        merchant_class is MerchantClass.SPLITTABLE
        and abs_minor >= cap_minor
        and decision.reason == "split_requires_itemized_proof"
    ):
        return AttentionKind.INTERRUPT
    if abs_minor >= cap_minor and not known:
        return AttentionKind.INTERRUPT
    return AttentionKind.QUEUE
