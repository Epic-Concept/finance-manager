"""Tests for TransactionClusteringService."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from finance_api.models.transaction import Transaction
from finance_api.services.transaction_clustering_service import (
    ClusterStatistics,
    TransactionCluster,
    TransactionClusteringService,
)


def create_mock_transaction(
    id: int, description: str, amount: Decimal | None = None
) -> Transaction:
    """Create a mock Transaction for testing."""
    txn = MagicMock(spec=Transaction)
    txn.id = id
    txn.description = description
    txn.amount = amount or Decimal("-10.00")
    txn.transaction_date = date(2024, 1, 1)
    return txn


class TestNormalizeDescription:
    """Tests for description normalization."""

    def test_converts_to_uppercase(self) -> None:
        """Test that descriptions are converted to uppercase."""
        service = TransactionClusteringService()

        result = service.normalize_description("tesco stores")

        assert result == "TESCO"

    def test_removes_numbers(self) -> None:
        """Test that numbers are removed."""
        service = TransactionClusteringService()

        result = service.normalize_description("TESCO STORES 1234")

        assert "1234" not in result
        assert result == "TESCO"

    def test_removes_store_suffixes(self) -> None:
        """Test that common suffixes are removed."""
        service = TransactionClusteringService()

        assert service.normalize_description("TESCO STORES") == "TESCO"
        assert service.normalize_description("TESCO STORE") == "TESCO"
        assert service.normalize_description("TESCO LTD") == "TESCO"
        assert service.normalize_description("TESCO LIMITED") == "TESCO"
        assert service.normalize_description("AMAZON UK") == "AMAZON"

    def test_removes_payment_suffixes(self) -> None:
        """Test that payment-related suffixes are removed."""
        service = TransactionClusteringService()

        assert service.normalize_description("NETFLIX PAYMENT") == "NETFLIX"
        assert service.normalize_description("NETFLIX ORDER") == "NETFLIX"
        assert service.normalize_description("NETFLIX DIRECT") == "NETFLIX"

    def test_removes_multiple_spaces(self) -> None:
        """Test that multiple spaces are collapsed."""
        service = TransactionClusteringService()

        result = service.normalize_description("TESCO   STORES   1234")

        assert "  " not in result

    def test_removes_special_characters(self) -> None:
        """Test that special characters are removed."""
        service = TransactionClusteringService()

        result = service.normalize_description("AMAZON*PRIME")

        assert "*" not in result

    def test_handles_empty_string(self) -> None:
        """Test handling of empty string."""
        service = TransactionClusteringService()

        result = service.normalize_description("")

        assert result == ""

    def test_handles_only_removable_content(self) -> None:
        """Test handling when everything is removed."""
        service = TransactionClusteringService()

        result = service.normalize_description("1234 STORES 5678")

        assert result == ""

    def test_preserves_merchant_name(self) -> None:
        """Test that core merchant name is preserved."""
        service = TransactionClusteringService()

        assert "AMAZON" in service.normalize_description("AMAZON.CO.UK")
        assert "NETFLIX" in service.normalize_description("NETFLIX.COM")


class TestExtractClusterKey:
    """Tests for cluster key extraction."""

    def test_extracts_first_word(self) -> None:
        """Test extracting first word as cluster key."""
        service = TransactionClusteringService()

        result = service.extract_cluster_key("TESCO STORES 1234")

        assert result == "TESCO"

    def test_handles_single_word(self) -> None:
        """Test handling single word descriptions."""
        service = TransactionClusteringService()

        result = service.extract_cluster_key("NETFLIX")

        assert result == "NETFLIX"

    def test_returns_unclustered_for_empty(self) -> None:
        """Test that empty descriptions get UNCLUSTERED key."""
        service = TransactionClusteringService()

        result = service.extract_cluster_key("")

        assert result == "UNCLUSTERED"

    def test_returns_unclustered_for_numbers_only(self) -> None:
        """Test that number-only descriptions get UNCLUSTERED key."""
        service = TransactionClusteringService()

        result = service.extract_cluster_key("1234567890")

        assert result == "UNCLUSTERED"

    def test_different_formats_same_merchant(self) -> None:
        """Test that different formats of same merchant cluster together."""
        service = TransactionClusteringService()

        keys = [
            service.extract_cluster_key("TESCO STORES 1234"),
            service.extract_cluster_key("TESCO EXPRESS 5678"),
            service.extract_cluster_key("TESCO PLC"),
            service.extract_cluster_key("Tesco.com"),
        ]

        assert all(k == "TESCO" for k in keys)


class TestComputeClusterHash:
    """Tests for cluster hash computation."""

    def test_produces_consistent_hash(self) -> None:
        """Test that same key produces same hash."""
        service = TransactionClusteringService()

        hash1 = service.compute_cluster_hash("TESCO")
        hash2 = service.compute_cluster_hash("TESCO")

        assert hash1 == hash2

    def test_different_keys_different_hashes(self) -> None:
        """Test that different keys produce different hashes."""
        service = TransactionClusteringService()

        hash1 = service.compute_cluster_hash("TESCO")
        hash2 = service.compute_cluster_hash("AMAZON")

        assert hash1 != hash2

    def test_hash_is_64_characters(self) -> None:
        """Test that hash is SHA-256 length."""
        service = TransactionClusteringService()

        result = service.compute_cluster_hash("TESCO")

        assert len(result) == 64


class TestClusterTransactions:
    """Tests for transaction clustering."""

    def test_clusters_similar_transactions(self) -> None:
        """Test that similar transactions are clustered together."""
        service = TransactionClusteringService()
        transactions = [
            create_mock_transaction(1, "TESCO STORES 1234"),
            create_mock_transaction(2, "TESCO EXPRESS 5678"),
            create_mock_transaction(3, "TESCO PLC"),
        ]

        clusters = service.cluster_transactions(transactions)

        assert len(clusters) == 1
        assert clusters[0].size == 3
        assert clusters[0].cluster_key == "TESCO"

    def test_separates_different_merchants(self) -> None:
        """Test that different merchants are in separate clusters."""
        service = TransactionClusteringService()
        transactions = [
            create_mock_transaction(1, "TESCO STORES"),
            create_mock_transaction(2, "TESCO EXPRESS"),
            create_mock_transaction(3, "AMAZON UK"),
            create_mock_transaction(4, "AMAZON.CO.UK"),
        ]

        clusters = service.cluster_transactions(transactions)

        assert len(clusters) == 2
        cluster_keys = {c.cluster_key for c in clusters}
        assert "TESCO" in cluster_keys
        assert "AMAZON" in cluster_keys

    def test_filters_by_min_size(self) -> None:
        """Test that clusters below min size are filtered out."""
        service = TransactionClusteringService(min_cluster_size=3)
        transactions = [
            create_mock_transaction(1, "TESCO STORES"),
            create_mock_transaction(2, "TESCO EXPRESS"),
            create_mock_transaction(3, "AMAZON UK"),  # Only 1 Amazon
        ]

        clusters = service.cluster_transactions(transactions)

        assert len(clusters) == 0  # Neither cluster reaches min size of 3

    def test_sorts_by_size_largest_first(self) -> None:
        """Test that clusters are sorted by size."""
        service = TransactionClusteringService(min_cluster_size=2)
        transactions = [
            create_mock_transaction(1, "AMAZON UK"),
            create_mock_transaction(2, "AMAZON.COM"),
            create_mock_transaction(3, "TESCO STORES"),
            create_mock_transaction(4, "TESCO EXPRESS"),
            create_mock_transaction(5, "TESCO PLC"),
            create_mock_transaction(6, "TESCO EXTRA"),
        ]

        clusters = service.cluster_transactions(transactions)

        assert len(clusters) == 2
        assert clusters[0].cluster_key == "TESCO"  # Larger (4)
        assert clusters[1].cluster_key == "AMAZON"  # Smaller (2)

    def test_collects_sample_descriptions(self) -> None:
        """Test that unique sample descriptions are collected."""
        service = TransactionClusteringService(max_samples=3)
        transactions = [
            create_mock_transaction(1, "TESCO STORES 1234"),
            create_mock_transaction(2, "TESCO EXPRESS 5678"),
            create_mock_transaction(3, "TESCO PLC 9999"),
            create_mock_transaction(4, "TESCO STORES 1234"),  # Duplicate
        ]

        clusters = service.cluster_transactions(transactions)

        assert len(clusters) == 1
        # Should have 3 unique descriptions (not 4, as one is duplicate)
        assert len(clusters[0].sample_descriptions) == 3

    def test_limits_sample_descriptions(self) -> None:
        """Test that sample descriptions are limited."""
        service = TransactionClusteringService(max_samples=2)
        transactions = [
            create_mock_transaction(1, "TESCO 1"),
            create_mock_transaction(2, "TESCO 2"),
            create_mock_transaction(3, "TESCO 3"),
            create_mock_transaction(4, "TESCO 4"),
        ]

        clusters = service.cluster_transactions(transactions)

        assert len(clusters[0].sample_descriptions) == 2

    def test_handles_empty_descriptions(self) -> None:
        """Test handling of transactions with empty descriptions."""
        service = TransactionClusteringService(min_cluster_size=1)
        transactions = [
            create_mock_transaction(1, ""),
            create_mock_transaction(2, "TESCO STORES"),
        ]

        clusters = service.cluster_transactions(transactions)

        # Only TESCO should be clustered
        assert len(clusters) == 1
        assert clusters[0].cluster_key == "TESCO"

    def test_handles_none_descriptions(self) -> None:
        """Test handling of transactions with None descriptions."""
        service = TransactionClusteringService(min_cluster_size=1)
        txn1 = create_mock_transaction(1, "TESCO")
        txn2 = create_mock_transaction(2, "")
        txn2.description = None

        transactions = [txn1, txn2]
        clusters = service.cluster_transactions(transactions)

        assert len(clusters) == 1

    def test_empty_transactions_list(self) -> None:
        """Test handling of empty transaction list."""
        service = TransactionClusteringService()

        clusters = service.cluster_transactions([])

        assert len(clusters) == 0


class TestGetClusterStatistics:
    """Tests for cluster statistics."""

    def test_calculates_coverage_percentage(self) -> None:
        """Test coverage percentage calculation."""
        service = TransactionClusteringService()
        clusters = [
            TransactionCluster(
                cluster_key="A",
                cluster_hash="hash_a",
                transactions=[
                    create_mock_transaction(1, "A"),
                    create_mock_transaction(2, "A"),
                ],
            ),
        ]

        stats = service.get_cluster_statistics(clusters, total_transactions=10)

        assert stats.coverage_percentage == 20.0

    def test_calculates_cluster_sizes(self) -> None:
        """Test cluster size statistics."""
        service = TransactionClusteringService()
        clusters = [
            TransactionCluster(
                cluster_key="A",
                cluster_hash="hash_a",
                transactions=[create_mock_transaction(i, "A") for i in range(10)],
            ),
            TransactionCluster(
                cluster_key="B",
                cluster_hash="hash_b",
                transactions=[create_mock_transaction(i + 10, "B") for i in range(5)],
            ),
            TransactionCluster(
                cluster_key="C",
                cluster_hash="hash_c",
                transactions=[create_mock_transaction(i + 15, "C") for i in range(2)],
            ),
        ]

        stats = service.get_cluster_statistics(clusters, total_transactions=20)

        assert stats.largest_cluster_size == 10
        assert stats.smallest_cluster_size == 2
        assert stats.average_cluster_size == (10 + 5 + 2) / 3

    def test_handles_empty_clusters(self) -> None:
        """Test statistics for empty cluster list."""
        service = TransactionClusteringService()

        stats = service.get_cluster_statistics([], total_transactions=100)

        assert stats.total_clusters == 0
        assert stats.clustered_transactions == 0
        assert stats.coverage_percentage == 0.0
        assert stats.largest_cluster_size == 0
        assert stats.smallest_cluster_size == 0

    def test_handles_zero_total_transactions(self) -> None:
        """Test statistics when total_transactions is zero."""
        service = TransactionClusteringService()

        stats = service.get_cluster_statistics([], total_transactions=0)

        assert stats.coverage_percentage == 0.0


class TestGetUnclusteredTransactions:
    """Tests for getting unclustered transactions."""

    def test_returns_unclustered_transactions(self) -> None:
        """Test returning transactions not in any cluster."""
        service = TransactionClusteringService()
        all_transactions = [
            create_mock_transaction(1, "TESCO"),
            create_mock_transaction(2, "TESCO"),
            create_mock_transaction(3, "UNIQUE"),
        ]
        clusters = [
            TransactionCluster(
                cluster_key="TESCO",
                cluster_hash="hash",
                transactions=all_transactions[:2],
            ),
        ]

        unclustered = service.get_unclustered_transactions(all_transactions, clusters)

        assert len(unclustered) == 1
        assert unclustered[0].id == 3

    def test_returns_empty_when_all_clustered(self) -> None:
        """Test returning empty list when all transactions are clustered."""
        service = TransactionClusteringService()
        all_transactions = [
            create_mock_transaction(1, "TESCO"),
            create_mock_transaction(2, "TESCO"),
        ]
        clusters = [
            TransactionCluster(
                cluster_key="TESCO",
                cluster_hash="hash",
                transactions=all_transactions,
            ),
        ]

        unclustered = service.get_unclustered_transactions(all_transactions, clusters)

        assert len(unclustered) == 0


class TestRankClustersBySize:
    """Tests for ranking clusters."""

    def test_ranks_largest_first(self) -> None:
        """Test that clusters are ranked largest first."""
        service = TransactionClusteringService()
        clusters = [
            TransactionCluster(
                cluster_key="SMALL",
                cluster_hash="s",
                transactions=[create_mock_transaction(1, "S")],
            ),
            TransactionCluster(
                cluster_key="LARGE",
                cluster_hash="l",
                transactions=[create_mock_transaction(i, "L") for i in range(10)],
            ),
            TransactionCluster(
                cluster_key="MEDIUM",
                cluster_hash="m",
                transactions=[create_mock_transaction(i + 10, "M") for i in range(5)],
            ),
        ]

        ranked = service.rank_clusters_by_size(clusters)

        assert ranked[0].cluster_key == "LARGE"
        assert ranked[1].cluster_key == "MEDIUM"
        assert ranked[2].cluster_key == "SMALL"


class TestFilterClustersByMinSize:
    """Tests for filtering clusters by size."""

    def test_filters_below_minimum(self) -> None:
        """Test filtering clusters below minimum size."""
        service = TransactionClusteringService()
        clusters = [
            TransactionCluster(
                cluster_key="SMALL",
                cluster_hash="s",
                transactions=[create_mock_transaction(1, "S")],
            ),
            TransactionCluster(
                cluster_key="LARGE",
                cluster_hash="l",
                transactions=[create_mock_transaction(i, "L") for i in range(10)],
            ),
        ]

        filtered = service.filter_clusters_by_min_size(clusters, min_size=5)

        assert len(filtered) == 1
        assert filtered[0].cluster_key == "LARGE"

    def test_includes_exact_minimum(self) -> None:
        """Test that clusters at exact minimum size are included."""
        service = TransactionClusteringService()
        clusters = [
            TransactionCluster(
                cluster_key="EXACT",
                cluster_hash="e",
                transactions=[create_mock_transaction(i, "E") for i in range(5)],
            ),
        ]

        filtered = service.filter_clusters_by_min_size(clusters, min_size=5)

        assert len(filtered) == 1


class TestTransactionCluster:
    """Tests for TransactionCluster dataclass."""

    def test_size_property(self) -> None:
        """Test that size property returns correct count."""
        cluster = TransactionCluster(
            cluster_key="TEST",
            cluster_hash="hash",
            transactions=[
                create_mock_transaction(1, "T"),
                create_mock_transaction(2, "T"),
                create_mock_transaction(3, "T"),
            ],
        )

        assert cluster.size == 3

    def test_empty_cluster_size(self) -> None:
        """Test size of empty cluster."""
        cluster = TransactionCluster(
            cluster_key="EMPTY",
            cluster_hash="hash",
        )

        assert cluster.size == 0


class TestStripPatterns:
    """Tests for strip patterns functionality."""

    def test_strips_pattern_from_description(self) -> None:
        """Test that strip patterns are removed from descriptions."""
        service = TransactionClusteringService(
            strip_patterns=["ZAKUP PRZY KARTY"]
        )

        result = service.normalize_description("TESCO ZAKUP PRZY KARTY 123")

        assert "ZAKUP PRZY KARTY" not in result
        assert "TESCO" in result

    def test_strips_multiple_patterns(self) -> None:
        """Test stripping multiple patterns."""
        service = TransactionClusteringService(
            strip_patterns=["PATTERN ONE", "PATTERN TWO"]
        )

        result = service.normalize_description("DATA PATTERN ONE PATTERN TWO END")

        assert "PATTERN ONE" not in result
        assert "PATTERN TWO" not in result
        assert "DATA" in result
        assert "END" in result

    def test_strip_is_case_insensitive(self) -> None:
        """Test that strip patterns work case-insensitively."""
        service = TransactionClusteringService(
            strip_patterns=["pattern text"]
        )

        result = service.normalize_description("DATA PATTERN TEXT HERE")

        assert "PATTERN TEXT" not in result

    def test_no_strip_patterns_by_default(self) -> None:
        """Test that no patterns are stripped by default."""
        service = TransactionClusteringService()

        result = service.normalize_description("TESCO ZAKUP PRZY KARTY")

        assert "ZAKUP" in result
        assert "PRZY" in result
        assert "KARTY" in result

    def test_cluster_key_after_stripping(self) -> None:
        """Test that cluster key changes after stripping prefix pattern."""
        # Without stripping
        service_no_strip = TransactionClusteringService()
        key_no_strip = service_no_strip.extract_cluster_key("ZAKUP TESCO STORES")

        # With stripping
        service_strip = TransactionClusteringService(strip_patterns=["ZAKUP"])
        key_strip = service_strip.extract_cluster_key("ZAKUP TESCO STORES")

        # Without strip, key is "ZAKUP", with strip, key is "TESCO"
        assert key_no_strip == "ZAKUP"
        assert key_strip == "TESCO"

    def test_clustering_with_strip_patterns(self) -> None:
        """Test that clustering works correctly with strip patterns."""
        service = TransactionClusteringService(
            min_cluster_size=2,
            strip_patterns=["ZAKUP PRZY KARTY"]
        )

        transactions = [
            create_mock_transaction(1, "ZAKUP PRZY KARTY TESCO 123"),
            create_mock_transaction(2, "ZAKUP PRZY KARTY TESCO 456"),
            create_mock_transaction(3, "AMAZON UK"),
        ]

        clusters = service.cluster_transactions(transactions)

        # TESCO should cluster together, AMAZON alone won't meet min_size
        assert len(clusters) == 1
        assert clusters[0].cluster_key == "TESCO"
        assert clusters[0].size == 2
