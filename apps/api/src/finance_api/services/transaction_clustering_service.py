"""TransactionClusteringService for grouping similar transactions."""

import hashlib
import re
from dataclasses import dataclass, field

from finance_api.models.transaction import Transaction


@dataclass
class TransactionCluster:
    """Represents a cluster of similar transactions."""

    cluster_key: str
    cluster_hash: str
    transactions: list[Transaction] = field(default_factory=list)
    sample_descriptions: list[str] = field(default_factory=list)

    @property
    def size(self) -> int:
        """Return the number of transactions in the cluster."""
        return len(self.transactions)


@dataclass
class ClusterStatistics:
    """Statistics about clustering results."""

    total_transactions: int
    total_clusters: int
    clustered_transactions: int
    coverage_percentage: float
    largest_cluster_size: int
    smallest_cluster_size: int
    average_cluster_size: float


class TransactionClusteringService:
    """Service for clustering transactions by description patterns.

    Groups similar transactions using token-based normalization and extraction.
    Designed for structured bank transaction descriptions.
    """

    # Suffixes to remove during normalization
    REMOVABLE_SUFFIXES = frozenset(
        [
            "STORES",
            "STORE",
            "LTD",
            "LIMITED",
            "S.A.",
            "INC",
            "ORDER",
            "PAYMENT",
            "EXPRESS",
            "ONLINE",
            "DIRECT",
            "DEBIT",
            "CARD",
            "UK",
            "GB",
            "PLC",
            "CO",
            "LLC",
            "COM",
            "ORG",
            "NET",
        ]
    )

    # Patterns to remove during normalization
    REMOVAL_PATTERNS = [
        r"\d+",  # Numbers (store IDs, reference numbers)
        r"[*#@.]",  # Special characters including dots
        r"\s{2,}",  # Multiple spaces
    ]

    def __init__(self, min_cluster_size: int = 2, max_samples: int = 5) -> None:
        """Initialize the clustering service.

        Args:
            min_cluster_size: Minimum transactions required to form a cluster.
            max_samples: Maximum number of sample descriptions per cluster.
        """
        self._min_cluster_size = min_cluster_size
        self._max_samples = max_samples
        self._compiled_patterns = [re.compile(p) for p in self.REMOVAL_PATTERNS]

    def normalize_description(self, description: str) -> str:
        """Normalize a transaction description for clustering.

        Pipeline:
        1. Convert to uppercase
        2. Remove numbers and special characters
        3. Strip removable suffixes
        4. Clean up whitespace

        Args:
            description: Raw transaction description.

        Returns:
            Normalized description string.
        """
        # Step 1: Uppercase
        normalized = description.upper()

        # Step 2: Remove patterns
        for pattern in self._compiled_patterns:
            normalized = pattern.sub(" ", normalized)

        # Step 3: Clean whitespace
        normalized = " ".join(normalized.split())

        # Step 4: Remove suffixes
        words = normalized.split()
        filtered_words = [w for w in words if w not in self.REMOVABLE_SUFFIXES]

        return " ".join(filtered_words).strip()

    def extract_cluster_key(self, description: str) -> str:
        """Extract the cluster key from a description.

        Takes the first significant token after normalization as the key.
        This provides fast, deterministic clustering.

        Args:
            description: Raw transaction description.

        Returns:
            Cluster key string.
        """
        normalized = self.normalize_description(description)
        words = normalized.split()

        if not words:
            return "UNCLUSTERED"

        # Return first word as cluster key
        # This handles most merchant names well
        return words[0]

    def compute_cluster_hash(self, cluster_key: str) -> str:
        """Compute a unique hash for a cluster.

        Args:
            cluster_key: The cluster key string.

        Returns:
            SHA-256 hash of the cluster key.
        """
        return hashlib.sha256(cluster_key.encode("utf-8")).hexdigest()

    def cluster_transactions(
        self, transactions: list[Transaction]
    ) -> list[TransactionCluster]:
        """Cluster transactions by description similarity.

        Args:
            transactions: List of transactions to cluster.

        Returns:
            List of TransactionCluster objects, sorted by size (largest first).
        """
        # Group by cluster key
        clusters_dict: dict[str, list[Transaction]] = {}

        for txn in transactions:
            if not txn.description:
                continue

            key = self.extract_cluster_key(txn.description)
            if key not in clusters_dict:
                clusters_dict[key] = []
            clusters_dict[key].append(txn)

        # Convert to TransactionCluster objects
        clusters: list[TransactionCluster] = []

        for key, txns in clusters_dict.items():
            if len(txns) < self._min_cluster_size:
                continue

            # Get unique sample descriptions
            unique_descriptions = list(
                dict.fromkeys(t.description for t in txns if t.description)
            )
            samples = unique_descriptions[: self._max_samples]

            cluster = TransactionCluster(
                cluster_key=key,
                cluster_hash=self.compute_cluster_hash(key),
                transactions=txns,
                sample_descriptions=samples,
            )
            clusters.append(cluster)

        # Sort by size (largest first)
        clusters.sort(key=lambda c: c.size, reverse=True)

        return clusters

    def get_cluster_statistics(
        self, clusters: list[TransactionCluster], total_transactions: int
    ) -> ClusterStatistics:
        """Calculate statistics about clustering results.

        Args:
            clusters: List of clusters produced by cluster_transactions().
            total_transactions: Total number of transactions (including unclustered).

        Returns:
            ClusterStatistics with coverage and size metrics.
        """
        if not clusters:
            return ClusterStatistics(
                total_transactions=total_transactions,
                total_clusters=0,
                clustered_transactions=0,
                coverage_percentage=0.0,
                largest_cluster_size=0,
                smallest_cluster_size=0,
                average_cluster_size=0.0,
            )

        clustered_count = sum(c.size for c in clusters)
        sizes = [c.size for c in clusters]

        return ClusterStatistics(
            total_transactions=total_transactions,
            total_clusters=len(clusters),
            clustered_transactions=clustered_count,
            coverage_percentage=(
                (clustered_count / total_transactions * 100)
                if total_transactions > 0
                else 0.0
            ),
            largest_cluster_size=max(sizes),
            smallest_cluster_size=min(sizes),
            average_cluster_size=sum(sizes) / len(sizes),
        )

    def get_unclustered_transactions(
        self, transactions: list[Transaction], clusters: list[TransactionCluster]
    ) -> list[Transaction]:
        """Get transactions that weren't placed in any cluster.

        Args:
            transactions: Original list of all transactions.
            clusters: Clusters produced by cluster_transactions().

        Returns:
            List of transactions not in any cluster.
        """
        clustered_ids = set()
        for cluster in clusters:
            for txn in cluster.transactions:
                clustered_ids.add(txn.id)

        return [t for t in transactions if t.id not in clustered_ids]

    def rank_clusters_by_size(
        self, clusters: list[TransactionCluster]
    ) -> list[TransactionCluster]:
        """Rank clusters by size (most prevalent first).

        Args:
            clusters: List of clusters to rank.

        Returns:
            Sorted list of clusters (largest first).
        """
        return sorted(clusters, key=lambda c: c.size, reverse=True)

    def filter_clusters_by_min_size(
        self, clusters: list[TransactionCluster], min_size: int
    ) -> list[TransactionCluster]:
        """Filter clusters to only include those above a minimum size.

        Args:
            clusters: List of clusters to filter.
            min_size: Minimum cluster size to include.

        Returns:
            Filtered list of clusters.
        """
        return [c for c in clusters if c.size >= min_size]
