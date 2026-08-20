"""Hierarchical residual clustering for cohort discovery (stages A–E)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from finance_api.classification.cel.activation import amount_to_minor
from finance_api.services.transaction_clustering_service import (
    TransactionClusteringService,
)


@dataclass(frozen=True)
class CohortCluster:
    """A group of residual transactions sharing a hierarchical key."""

    stage: str
    cluster_key: str
    transactions: tuple[Any, ...]
    sample_descriptions: tuple[str, ...]

    @property
    def size(self) -> int:
        return len(self.transactions)


def _merchant_key(txn: Any, clustering: TransactionClusteringService) -> str:
    description = getattr(txn, "description", None) or ""
    return clustering.extract_cluster_key(description)


def _account(txn: Any) -> str:
    return getattr(txn, "account_name", None) or ""


def _amount_minor(txn: Any) -> int | None:
    amount = getattr(txn, "amount", None)
    if amount is None:
        return None
    return amount_to_minor(amount)


def hierarchical_clusters(
    transactions: Sequence[Any],
    *,
    min_size: int = 2,
    max_samples: int = 5,
    clustering: TransactionClusteringService | None = None,
) -> tuple[list[CohortCluster], list[Any]]:
    """Assign residual rows to the most specific cluster that meets ``min_size``.

    Stages:
    A ``(merchant, amount_minor, account)`` — subscriptions / rent
    B ``(merchant, sign, account)`` — same shop, variable ticket
    C merchant token — bulk grocery / transit (existing first-token service)
    D ``(amount_minor, day_of_month)`` — messy descriptions, same cadence
    E leftovers — singletons / unclustered
    """
    clustering = clustering or TransactionClusteringService(min_cluster_size=min_size)
    remaining = list(transactions)
    clusters: list[CohortCluster] = []

    def _take(stage: str, key_fn: Any) -> None:
        nonlocal remaining
        buckets: dict[str, list[Any]] = defaultdict(list)
        for txn in remaining:
            key = key_fn(txn)
            if key:
                buckets[key].append(txn)
        taken: set[int] = set()
        for key, group in buckets.items():
            if len(group) < min_size:
                continue
            samples = tuple(
                dict.fromkeys(
                    t.description for t in group if getattr(t, "description", None)
                )
            )[:max_samples]
            clusters.append(
                CohortCluster(
                    stage=stage,
                    cluster_key=key,
                    transactions=tuple(group),
                    sample_descriptions=samples,
                )
            )
            taken.update(t.id for t in group)
        remaining = [t for t in remaining if t.id not in taken]

    def _stage_a(t: Any) -> str:
        minor = _amount_minor(t)
        if not getattr(t, "description", None) or minor is None:
            return ""
        return f"{_merchant_key(t, clustering)}|{minor}|{_account(t)}"

    def _stage_b(t: Any) -> str:
        minor = _amount_minor(t)
        if not getattr(t, "description", None) or minor is None:
            return ""
        return f"{_merchant_key(t, clustering)}|{int(minor < 0)}|{_account(t)}"

    _take("A", _stage_a)
    _take("B", _stage_b)
    _take(
        "C",
        lambda t: (
            _merchant_key(t, clustering) if getattr(t, "description", None) else ""
        ),
    )
    _take(
        "D",
        lambda t: (
            f"{amount_to_minor(t.amount)}|{t.transaction_date.day}"
            if getattr(t, "amount", None) is not None
            and getattr(t, "transaction_date", None) is not None
            else ""
        ),
    )

    clusters.sort(key=lambda c: c.size, reverse=True)
    return clusters, remaining
