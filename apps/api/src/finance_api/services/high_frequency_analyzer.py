"""HighFrequencyPatternAnalyzer for detecting common patterns in transactions."""

import hashlib
import re
from dataclasses import dataclass, field

from finance_api.models.transaction import Transaction


@dataclass
class HighFrequencyPattern:
    """A pattern detected in many transactions."""

    phrase: str
    frequency: float  # 0.0 to 1.0
    transaction_count: int
    sample_descriptions: list[str] = field(default_factory=list)
    sample_transaction_ids: list[int] = field(default_factory=list)

    @property
    def pattern_hash(self) -> str:
        """Generate a unique hash for this pattern."""
        return hashlib.sha256(self.phrase.encode()).hexdigest()[:16]


class HighFrequencyPatternAnalyzer:
    """Detects n-gram patterns appearing in many transactions.

    This analyzer extracts word-based n-grams from transaction descriptions
    and identifies patterns that appear in a significant percentage of
    transactions. These high-frequency patterns often indicate bank-specific
    features (savings round-ups, automatic transfers) rather than merchants.
    """

    # Patterns to remove before n-gram extraction (numbers, special chars)
    CLEANUP_PATTERNS = [
        re.compile(r"\d+"),  # Numbers
        re.compile(r"[*#@.,]"),  # Special characters
        re.compile(r"\s{2,}"),  # Multiple spaces
    ]

    def __init__(
        self,
        threshold: float = 0.10,
        min_phrase_words: int = 2,
        max_phrase_words: int = 6,
        min_phrase_length: int = 10,
        max_samples: int = 5,
    ) -> None:
        """Initialize the analyzer.

        Args:
            threshold: Minimum frequency (0.0 to 1.0) for a pattern to be detected.
                Default 0.10 means patterns must appear in >=10% of transactions.
            min_phrase_words: Minimum number of words in a pattern. Default 2.
            max_phrase_words: Maximum number of words in a pattern. Default 6.
            min_phrase_length: Minimum character length for a pattern. Default 10.
            max_samples: Maximum number of sample descriptions to collect. Default 5.
        """
        if not 0.0 < threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        if min_phrase_words < 1:
            raise ValueError("min_phrase_words must be at least 1")
        if max_phrase_words < min_phrase_words:
            raise ValueError("max_phrase_words must be >= min_phrase_words")

        self._threshold = threshold
        self._min_phrase_words = min_phrase_words
        self._max_phrase_words = max_phrase_words
        self._min_phrase_length = min_phrase_length
        self._max_samples = max_samples

    def _normalize_description(self, description: str) -> str:
        """Normalize a description for n-gram extraction.

        Args:
            description: Raw transaction description.

        Returns:
            Normalized description (uppercase, no numbers/special chars).
        """
        if not description:
            return ""

        normalized = description.upper()

        for pattern in self.CLEANUP_PATTERNS:
            normalized = pattern.sub(" ", normalized)

        # Collapse whitespace
        return " ".join(normalized.split())

    def _extract_ngrams(self, text: str) -> list[str]:
        """Extract all n-grams from normalized text.

        Args:
            text: Normalized text string.

        Returns:
            List of n-gram phrases (2 to max_phrase_words words).
        """
        words = text.split()
        if len(words) < self._min_phrase_words:
            return []

        ngrams = []
        for n in range(self._min_phrase_words, self._max_phrase_words + 1):
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i : i + n])
                if len(phrase) >= self._min_phrase_length:
                    ngrams.append(phrase)

        return ngrams

    def _remove_overlapping_patterns(
        self,
        patterns: list[tuple[str, int]],
    ) -> list[tuple[str, int]]:
        """Remove shorter patterns that are substrings of longer ones.

        When both "ZAKUP PRZY" and "ZAKUP PRZY UZYCIU KARTY" meet the threshold,
        keep only the longer pattern.

        Args:
            patterns: List of (phrase, count) tuples, sorted by count descending.

        Returns:
            Filtered list with overlapping shorter patterns removed.
        """
        if not patterns:
            return []

        # Sort by phrase length descending (longest first)
        sorted_by_length = sorted(patterns, key=lambda x: len(x[0]), reverse=True)

        kept_patterns: list[tuple[str, int]] = []
        for phrase, count in sorted_by_length:
            # Check if this phrase is a substring of any already-kept pattern
            is_substring = any(phrase in kept[0] for kept in kept_patterns)
            if not is_substring:
                kept_patterns.append((phrase, count))

        # Return in original order (by count)
        kept_set = {p[0] for p in kept_patterns}
        return [(p, c) for p, c in patterns if p in kept_set]

    def analyze(self, transactions: list[Transaction]) -> list[HighFrequencyPattern]:
        """Analyze transactions and return high-frequency patterns.

        Algorithm:
        1. Normalize descriptions (uppercase, remove numbers)
        2. Extract all n-grams (2 to max_phrase_words words)
        3. Count occurrences of each n-gram
        4. Filter by threshold
        5. Remove overlapping patterns (keep longest)
        6. Sort by frequency descending

        Args:
            transactions: List of Transaction objects to analyze.

        Returns:
            List of HighFrequencyPattern objects, sorted by frequency descending.
        """
        if not transactions:
            return []

        total_count = len(transactions)
        min_count = int(total_count * self._threshold)

        # Track which transactions contain each n-gram
        ngram_to_transactions: dict[str, list[tuple[int, str]]] = {}

        for txn in transactions:
            if not txn.description:
                continue

            normalized = self._normalize_description(txn.description)
            ngrams = self._extract_ngrams(normalized)

            # Track unique n-grams per transaction (avoid double-counting)
            seen_in_txn: set[str] = set()
            for ngram in ngrams:
                if ngram not in seen_in_txn:
                    seen_in_txn.add(ngram)
                    if ngram not in ngram_to_transactions:
                        ngram_to_transactions[ngram] = []
                    ngram_to_transactions[ngram].append((txn.id, txn.description))

        # Filter by threshold
        candidates = [
            (phrase, len(txns))
            for phrase, txns in ngram_to_transactions.items()
            if len(txns) >= min_count
        ]

        # Sort by count descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Remove overlapping patterns
        filtered = self._remove_overlapping_patterns(candidates)

        # Build result objects
        results = []
        for phrase, count in filtered:
            txn_data = ngram_to_transactions[phrase]
            frequency = count / total_count

            # Collect samples (unique descriptions)
            seen_descriptions: set[str] = set()
            sample_descriptions: list[str] = []
            sample_ids: list[int] = []

            for txn_id, description in txn_data:
                if description not in seen_descriptions:
                    seen_descriptions.add(description)
                    sample_descriptions.append(description)
                    sample_ids.append(txn_id)
                    if len(sample_descriptions) >= self._max_samples:
                        break

            results.append(
                HighFrequencyPattern(
                    phrase=phrase,
                    frequency=frequency,
                    transaction_count=count,
                    sample_descriptions=sample_descriptions,
                    sample_transaction_ids=sample_ids,
                )
            )

        return results

    def get_all_matching_transaction_ids(
        self,
        pattern: HighFrequencyPattern,
        transactions: list[Transaction],
    ) -> list[int]:
        """Get all transaction IDs that contain a pattern.

        Args:
            pattern: The pattern to search for.
            transactions: List of transactions to search.

        Returns:
            List of transaction IDs containing the pattern.
        """
        matching_ids = []
        pattern_upper = pattern.phrase.upper()

        for txn in transactions:
            if not txn.description:
                continue
            normalized = self._normalize_description(txn.description)
            if pattern_upper in normalized:
                matching_ids.append(txn.id)

        return matching_ids
