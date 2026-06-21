"""Unit tests for bootstrap cluster-coverage reporting."""

from __future__ import annotations

from finance_api.classification.bootstrap import cluster_coverage, resolve_choice
from finance_api.services.transaction_clustering_service import TransactionCluster


def _cluster(size: int, key: str = "k") -> TransactionCluster:
    return TransactionCluster(
        cluster_key=key,
        cluster_hash=key,
        transactions=list(range(size)),  # type: ignore[arg-type]
    )


def test_top_clusters_coverage_fraction() -> None:
    clusters = [_cluster(50, "a"), _cluster(30, "b"), _cluster(20, "c")]  # total 100

    report = cluster_coverage(clusters, top_n=2)

    assert report.total == 100
    assert report.covered == 80
    assert report.cluster_count == 2
    assert report.fraction == 0.8


def test_coverage_without_limit_is_full() -> None:
    clusters = [_cluster(10, "a"), _cluster(5, "b")]

    report = cluster_coverage(clusters)

    assert report.covered == 15
    assert report.total == 15
    assert report.fraction == 1.0


def test_coverage_of_empty_is_zero() -> None:
    report = cluster_coverage([])
    assert report.total == 0
    assert report.covered == 0
    assert report.fraction == 0.0


def test_resolve_choice_confirm_correct_skip() -> None:
    assert resolve_choice("", proposed_category_id=7) == 7  # blank confirms
    assert resolve_choice("y", proposed_category_id=7) == 7
    assert resolve_choice("12", proposed_category_id=7) == 12  # override
    assert resolve_choice("s", proposed_category_id=7) is None  # skip
    assert resolve_choice("n", proposed_category_id=7) is None
    assert resolve_choice("", proposed_category_id=None) is None  # nothing proposed
