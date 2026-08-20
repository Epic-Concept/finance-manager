"""The gatherer contract.

All evidence gatherers (rules, history, web lookup, receipt hunt, LLM
inference) implement this single interface, so gatherers can be added or
removed without changing the policy. A gatherer only *produces* evidence; it
never makes the final decision.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finance_api.classification.evidence import Evidence, EvidenceType


@dataclass(frozen=True)
class GatherContext:
    """The transaction context handed to gatherers.

    Decoupled from the persistence layer so the classification core can be
    tested without a database.
    """

    transaction_id: int
    description: str
    amount: Decimal
    currency: str
    transaction_date: date
    account_name: str | None = None
    merchant_name: str | None = None


class Gatherer(ABC):
    """Base class for all evidence gatherers.

    Subclasses declare :attr:`produced_types` and implement :meth:`gather`,
    returning typed :class:`Evidence` with honest (possibly degraded) strength.
    """

    #: The evidence types this gatherer can produce.
    produced_types: frozenset[EvidenceType] = frozenset()

    @abstractmethod
    def gather(self, context: GatherContext) -> list[Evidence]:
        """Produce evidence for the given transaction context.

        Returns a (possibly empty) list of :class:`Evidence`. Must never assign
        a final category to the transaction.
        """
        raise NotImplementedError
