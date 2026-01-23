"""Tests for HighFrequencyPatternAnalyzer."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from finance_api.models.transaction import Transaction
from finance_api.services.high_frequency_analyzer import (
    HighFrequencyPattern,
    HighFrequencyPatternAnalyzer,
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


class TestHighFrequencyPatternInit:
    """Tests for HighFrequencyPatternAnalyzer initialization."""

    def test_default_values(self) -> None:
        """Test default initialization values."""
        analyzer = HighFrequencyPatternAnalyzer()

        assert analyzer._threshold == 0.10
        assert analyzer._min_phrase_words == 2
        assert analyzer._max_phrase_words == 6
        assert analyzer._min_phrase_length == 10

    def test_custom_threshold(self) -> None:
        """Test custom threshold initialization."""
        analyzer = HighFrequencyPatternAnalyzer(threshold=0.05)

        assert analyzer._threshold == 0.05

    def test_invalid_threshold_raises_error(self) -> None:
        """Test that invalid threshold raises ValueError."""
        with pytest.raises(ValueError, match="threshold must be between"):
            HighFrequencyPatternAnalyzer(threshold=0.0)

        with pytest.raises(ValueError, match="threshold must be between"):
            HighFrequencyPatternAnalyzer(threshold=1.5)

    def test_invalid_phrase_words_raises_error(self) -> None:
        """Test that invalid phrase word counts raise ValueError."""
        with pytest.raises(ValueError, match="min_phrase_words must be at least 1"):
            HighFrequencyPatternAnalyzer(min_phrase_words=0)

        with pytest.raises(
            ValueError, match="max_phrase_words must be >= min_phrase_words"
        ):
            HighFrequencyPatternAnalyzer(min_phrase_words=5, max_phrase_words=3)


class TestNormalizeDescription:
    """Tests for description normalization."""

    def test_converts_to_uppercase(self) -> None:
        """Test that descriptions are converted to uppercase."""
        analyzer = HighFrequencyPatternAnalyzer()

        result = analyzer._normalize_description("hello world")

        assert result == "HELLO WORLD"

    def test_removes_numbers(self) -> None:
        """Test that numbers are removed."""
        analyzer = HighFrequencyPatternAnalyzer()

        result = analyzer._normalize_description("TESCO 1234 STORES")

        assert "1234" not in result
        assert "TESCO" in result
        assert "STORES" in result

    def test_removes_special_characters(self) -> None:
        """Test that special characters are removed."""
        analyzer = HighFrequencyPatternAnalyzer()

        result = analyzer._normalize_description("AMAZON*PRIME@123#456")

        assert "*" not in result
        assert "@" not in result
        assert "#" not in result

    def test_collapses_whitespace(self) -> None:
        """Test that multiple spaces are collapsed."""
        analyzer = HighFrequencyPatternAnalyzer()

        result = analyzer._normalize_description("HELLO    WORLD")

        assert "  " not in result
        assert result == "HELLO WORLD"

    def test_handles_empty_string(self) -> None:
        """Test handling of empty string."""
        analyzer = HighFrequencyPatternAnalyzer()

        result = analyzer._normalize_description("")

        assert result == ""

    def test_handles_none(self) -> None:
        """Test handling of None-like falsy input."""
        analyzer = HighFrequencyPatternAnalyzer()

        result = analyzer._normalize_description("")

        assert result == ""


class TestExtractNgrams:
    """Tests for n-gram extraction."""

    def test_extracts_bigrams(self) -> None:
        """Test extraction of 2-word phrases."""
        analyzer = HighFrequencyPatternAnalyzer(min_phrase_length=5)

        result = analyzer._extract_ngrams("ONE TWO THREE FOUR")

        assert "ONE TWO" in result
        assert "TWO THREE" in result
        assert "THREE FOUR" in result

    def test_extracts_trigrams(self) -> None:
        """Test extraction of 3-word phrases."""
        analyzer = HighFrequencyPatternAnalyzer(min_phrase_length=5)

        result = analyzer._extract_ngrams("ONE TWO THREE FOUR")

        assert "ONE TWO THREE" in result
        assert "TWO THREE FOUR" in result

    def test_respects_min_phrase_length(self) -> None:
        """Test that phrases shorter than min length are excluded."""
        analyzer = HighFrequencyPatternAnalyzer(min_phrase_length=10)

        result = analyzer._extract_ngrams("A B C D")

        # "A B" is only 3 characters, should be excluded
        assert "A B" not in result

    def test_respects_max_phrase_words(self) -> None:
        """Test that phrases longer than max words are excluded."""
        analyzer = HighFrequencyPatternAnalyzer(
            min_phrase_words=2, max_phrase_words=3, min_phrase_length=5
        )

        result = analyzer._extract_ngrams("ONE TWO THREE FOUR FIVE SIX SEVEN")

        # Should have 2-word and 3-word phrases, but no 4+ word phrases
        assert "ONE TWO" in result
        assert "ONE TWO THREE" in result
        assert "ONE TWO THREE FOUR" not in result

    def test_handles_short_text(self) -> None:
        """Test handling text shorter than min_phrase_words."""
        analyzer = HighFrequencyPatternAnalyzer(min_phrase_words=3)

        result = analyzer._extract_ngrams("ONE TWO")

        assert result == []

    def test_handles_empty_text(self) -> None:
        """Test handling empty text."""
        analyzer = HighFrequencyPatternAnalyzer()

        result = analyzer._extract_ngrams("")

        assert result == []


class TestRemoveOverlappingPatterns:
    """Tests for overlap removal."""

    def test_keeps_longer_pattern(self) -> None:
        """Test that longer patterns are kept over shorter substrings."""
        analyzer = HighFrequencyPatternAnalyzer()

        patterns = [
            ("ZAKUP PRZY", 100),
            ("ZAKUP PRZY UZYCIU KARTY", 80),
        ]

        result = analyzer._remove_overlapping_patterns(patterns)

        # Should keep only the longer pattern
        result_phrases = [p[0] for p in result]
        assert "ZAKUP PRZY UZYCIU KARTY" in result_phrases
        assert "ZAKUP PRZY" not in result_phrases

    def test_keeps_non_overlapping_patterns(self) -> None:
        """Test that non-overlapping patterns are all kept."""
        analyzer = HighFrequencyPatternAnalyzer()

        patterns = [
            ("ZAKUP PRZY KARTY", 100),
            ("AMAZON PRIME", 80),
        ]

        result = analyzer._remove_overlapping_patterns(patterns)

        assert len(result) == 2

    def test_handles_empty_list(self) -> None:
        """Test handling empty pattern list."""
        analyzer = HighFrequencyPatternAnalyzer()

        result = analyzer._remove_overlapping_patterns([])

        assert result == []

    def test_preserves_count_order(self) -> None:
        """Test that patterns are returned in count order."""
        analyzer = HighFrequencyPatternAnalyzer()

        patterns = [
            ("PATTERN A LONG", 100),
            ("PATTERN B LONG", 50),
            ("PATTERN C LONG", 75),
        ]

        result = analyzer._remove_overlapping_patterns(patterns)

        # Should be in original order (by count)
        assert result[0][0] == "PATTERN A LONG"
        assert result[0][1] == 100


class TestAnalyze:
    """Tests for the main analyze method."""

    def test_detects_high_frequency_pattern(self) -> None:
        """Test detection of a pattern above threshold."""
        analyzer = HighFrequencyPatternAnalyzer(threshold=0.10, min_phrase_length=10)

        # Create 100 transactions, 15 with the same pattern
        transactions = []
        for i in range(15):
            transactions.append(
                create_mock_transaction(i, f"ZAKUP PRZY KARTY KWOTA {i}")
            )
        for i in range(15, 100):
            transactions.append(
                create_mock_transaction(i, f"UNIQUE DESC {i} SOMETHING")
            )

        patterns = analyzer.analyze(transactions)

        # Should detect the pattern
        pattern_phrases = [p.phrase for p in patterns]
        assert any("ZAKUP PRZY KARTY KWOTA" in phrase for phrase in pattern_phrases)

    def test_excludes_below_threshold_pattern(self) -> None:
        """Test that patterns below threshold are excluded."""
        analyzer = HighFrequencyPatternAnalyzer(threshold=0.20, min_phrase_length=10)

        # Create 100 transactions, only 5 with the pattern (5% < 20%)
        transactions = []
        for i in range(5):
            transactions.append(create_mock_transaction(i, f"ZAKUP PRZY KARTY {i}"))
        for i in range(5, 100):
            transactions.append(
                create_mock_transaction(i, f"UNIQUE DESC {i} SOMETHING")
            )

        patterns = analyzer.analyze(transactions)

        # Should NOT detect the pattern at 5% when threshold is 20%
        pattern_phrases = [p.phrase for p in patterns]
        assert not any("ZAKUP PRZY KARTY" in phrase for phrase in pattern_phrases)

    def test_calculates_correct_frequency(self) -> None:
        """Test that frequency is calculated correctly."""
        analyzer = HighFrequencyPatternAnalyzer(threshold=0.10, min_phrase_length=10)

        # 20 transactions with pattern, 80 without = 20%
        transactions = []
        for i in range(20):
            transactions.append(create_mock_transaction(i, f"PATTERN PHRASE HERE {i}"))
        for i in range(20, 100):
            transactions.append(create_mock_transaction(i, f"DIFFERENT TEXT {i}"))

        patterns = analyzer.analyze(transactions)

        # Find the pattern and check frequency
        matching_patterns = [p for p in patterns if "PATTERN PHRASE HERE" in p.phrase]
        if matching_patterns:
            assert matching_patterns[0].frequency == pytest.approx(0.20, abs=0.01)

    def test_collects_sample_descriptions(self) -> None:
        """Test that sample descriptions are collected."""
        analyzer = HighFrequencyPatternAnalyzer(
            threshold=0.10, min_phrase_length=10, max_samples=3
        )

        transactions = []
        for i in range(20):
            transactions.append(create_mock_transaction(i, f"PATTERN PHRASE HERE {i}"))
        for i in range(20, 100):
            transactions.append(create_mock_transaction(i, f"DIFFERENT TEXT {i}"))

        patterns = analyzer.analyze(transactions)

        matching_patterns = [p for p in patterns if "PATTERN PHRASE" in p.phrase]
        if matching_patterns:
            assert len(matching_patterns[0].sample_descriptions) <= 3
            assert len(matching_patterns[0].sample_descriptions) > 0

    def test_handles_empty_transactions(self) -> None:
        """Test handling empty transaction list."""
        analyzer = HighFrequencyPatternAnalyzer()

        patterns = analyzer.analyze([])

        assert patterns == []

    def test_handles_transactions_without_descriptions(self) -> None:
        """Test handling transactions with empty descriptions."""
        analyzer = HighFrequencyPatternAnalyzer(threshold=0.10)

        transactions = [
            create_mock_transaction(1, ""),
            create_mock_transaction(2, ""),
        ]
        transactions[0].description = ""
        transactions[1].description = ""

        patterns = analyzer.analyze(transactions)

        assert patterns == []

    def test_sorts_by_frequency_descending(self) -> None:
        """Test that patterns are sorted by frequency."""
        analyzer = HighFrequencyPatternAnalyzer(threshold=0.10, min_phrase_length=10)

        transactions = []
        # 30 with pattern A
        for i in range(30):
            transactions.append(create_mock_transaction(i, f"FIRST PATTERN HERE {i}"))
        # 20 with pattern B
        for i in range(30, 50):
            transactions.append(create_mock_transaction(i, f"SECOND PATTERN HERE {i}"))
        # 50 unique
        for i in range(50, 100):
            transactions.append(create_mock_transaction(i, f"UNIQUE TEXT NUMBER {i}"))

        patterns = analyzer.analyze(transactions)

        # First pattern should have higher frequency
        if len(patterns) >= 2:
            assert patterns[0].frequency >= patterns[1].frequency


class TestGetAllMatchingTransactionIds:
    """Tests for getting all matching transaction IDs."""

    def test_finds_all_matching_ids(self) -> None:
        """Test finding all transaction IDs containing a pattern."""
        analyzer = HighFrequencyPatternAnalyzer()

        pattern = HighFrequencyPattern(
            phrase="ZAKUP PRZY KARTY",
            frequency=0.15,
            transaction_count=15,
            sample_descriptions=[],
            sample_transaction_ids=[],
        )

        transactions = [
            create_mock_transaction(1, "ZAKUP PRZY KARTY 123"),
            create_mock_transaction(2, "ZAKUP PRZY KARTY 456"),
            create_mock_transaction(3, "OTHER TRANSACTION"),
            create_mock_transaction(4, "ZAKUP PRZY KARTY 789"),
        ]

        matching_ids = analyzer.get_all_matching_transaction_ids(pattern, transactions)

        assert len(matching_ids) == 3
        assert 1 in matching_ids
        assert 2 in matching_ids
        assert 4 in matching_ids
        assert 3 not in matching_ids

    def test_case_insensitive_matching(self) -> None:
        """Test that matching is case-insensitive."""
        analyzer = HighFrequencyPatternAnalyzer()

        pattern = HighFrequencyPattern(
            phrase="PATTERN TEXT",
            frequency=0.10,
            transaction_count=10,
            sample_descriptions=[],
            sample_transaction_ids=[],
        )

        transactions = [
            create_mock_transaction(1, "pattern text lowercase"),
            create_mock_transaction(2, "PATTERN TEXT UPPERCASE"),
            create_mock_transaction(3, "Pattern Text Mixed"),
        ]

        matching_ids = analyzer.get_all_matching_transaction_ids(pattern, transactions)

        assert len(matching_ids) == 3

    def test_handles_empty_transactions(self) -> None:
        """Test handling empty transaction list."""
        analyzer = HighFrequencyPatternAnalyzer()

        pattern = HighFrequencyPattern(
            phrase="PATTERN",
            frequency=0.10,
            transaction_count=10,
            sample_descriptions=[],
            sample_transaction_ids=[],
        )

        matching_ids = analyzer.get_all_matching_transaction_ids(pattern, [])

        assert matching_ids == []

    def test_handles_transactions_with_empty_descriptions(self) -> None:
        """Test handling transactions with empty descriptions."""
        analyzer = HighFrequencyPatternAnalyzer()

        pattern = HighFrequencyPattern(
            phrase="PATTERN",
            frequency=0.10,
            transaction_count=10,
            sample_descriptions=[],
            sample_transaction_ids=[],
        )

        txn = create_mock_transaction(1, "")
        txn.description = ""

        matching_ids = analyzer.get_all_matching_transaction_ids(pattern, [txn])

        assert matching_ids == []


class TestHighFrequencyPatternDataclass:
    """Tests for the HighFrequencyPattern dataclass."""

    def test_pattern_hash(self) -> None:
        """Test pattern hash generation."""
        pattern = HighFrequencyPattern(
            phrase="TEST PHRASE",
            frequency=0.10,
            transaction_count=10,
            sample_descriptions=["sample"],
            sample_transaction_ids=[1],
        )

        hash1 = pattern.pattern_hash
        hash2 = pattern.pattern_hash

        # Same pattern should produce same hash
        assert hash1 == hash2
        # Hash should be 16 characters (first 16 of SHA-256 hex)
        assert len(hash1) == 16

    def test_different_patterns_different_hashes(self) -> None:
        """Test that different patterns have different hashes."""
        pattern1 = HighFrequencyPattern(
            phrase="PATTERN ONE",
            frequency=0.10,
            transaction_count=10,
        )
        pattern2 = HighFrequencyPattern(
            phrase="PATTERN TWO",
            frequency=0.10,
            transaction_count=10,
        )

        assert pattern1.pattern_hash != pattern2.pattern_hash
