"""Cold-start guard: do not dump a per-row review firehose."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finance_api.models.classification_rule import ClassificationRule
from finance_api.models.transaction import Transaction

DEFAULT_RESIDUAL_THRESHOLD = 50


class ColdStartBlocked(RuntimeError):
    """Raised when classify-to-review would enqueue a firehose before cohorts."""


def cold_start_should_block(
    session: Session,
    *,
    residual_threshold: int = DEFAULT_RESIDUAL_THRESHOLD,
    cohorts_offered: bool = False,
) -> bool:
    rule_count = (
        session.scalar(
            select(func.count())
            .select_from(ClassificationRule)
            .where(ClassificationRule.is_active.is_(True))
        )
        or 0
    )
    txn_count = session.scalar(select(func.count()).select_from(Transaction)) or 0
    return (
        not cohorts_offered
        and int(rule_count) == 0
        and int(txn_count) >= residual_threshold
    )
