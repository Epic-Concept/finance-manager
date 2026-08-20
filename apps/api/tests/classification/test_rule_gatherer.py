"""Tests for the rule gatherer (transaction-classification spec).

A description-matching rule is the deterministic fast-path: a matched approved
rule is itemized=False PROOF evidence for a single category.
"""

from datetime import date
from decimal import Decimal

from finance_api.classification.evidence import EvidenceType, StrengthTier
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.gatherers.rules import RuleGatherer, RulePattern


class _FakeRuleSource:
    def __init__(self, rules: list[RulePattern]) -> None:
        self._rules = rules

    def active_rules(self) -> list[RulePattern]:
        return list(self._rules)


def _context(description: str) -> GatherContext:
    return GatherContext(
        transaction_id=1,
        description=description,
        amount=Decimal("2.80"),
        currency="GBP",
        transaction_date=date(2026, 6, 1),
    )


class TestRuleGatherer:
    def test_match_emits_single_proof_rule_evidence(self) -> None:
        gatherer = RuleGatherer(
            _FakeRuleSource([RulePattern(r"(?i)tfl", 7, "tfl-travel")])
        )
        evidence = gatherer.gather(_context("TFL TRAVEL CH"))
        assert len(evidence) == 1
        ev = evidence[0]
        assert ev.evidence_type is EvidenceType.RULE
        assert ev.strength is StrengthTier.PROOF
        assert ev.itemized is False
        assert ev.claim.category_ids == (7,)
        assert "tfl-travel" in ev.source

    def test_no_match_emits_nothing(self) -> None:
        gatherer = RuleGatherer(
            _FakeRuleSource([RulePattern(r"(?i)tesco", 3, "tesco")])
        )
        assert gatherer.gather(_context("TFL TRAVEL")) == []

    def test_highest_priority_match_wins(self) -> None:
        # Source returns rules in priority order; first match wins.
        gatherer = RuleGatherer(
            _FakeRuleSource(
                [
                    RulePattern(r"(?i)amzn", 1, "amazon-specific"),
                    RulePattern(r"(?i).*", 99, "catch-all"),
                ]
            )
        )
        evidence = gatherer.gather(_context("AMZN MKTP"))
        assert len(evidence) == 1
        assert evidence[0].claim.category_ids == (1,)

    def test_invalid_regex_is_skipped_not_crashing(self) -> None:
        gatherer = RuleGatherer(
            _FakeRuleSource(
                [
                    RulePattern(r"(?i)[unclosed", 1, "broken"),
                    RulePattern(r"(?i)tfl", 7, "tfl"),
                ]
            )
        )
        evidence = gatherer.gather(_context("TFL TRAVEL"))
        assert len(evidence) == 1
        assert evidence[0].claim.category_ids == (7,)

    def test_amount_constraint(self) -> None:
        gatherer = RuleGatherer(
            _FakeRuleSource([RulePattern("txn.amount_minor == 28000", 9, "exact-fare")])
        )
        assert gatherer.gather(_context("ANY"))[0].claim.category_ids == (9,)
        miss = GatherContext(
            transaction_id=1,
            description="ANY",
            amount=Decimal("3.00"),
            currency="GBP",
            transaction_date=date(2026, 6, 1),
        )
        assert gatherer.gather(miss) == []

    def test_account_constraint(self) -> None:
        gatherer = RuleGatherer(
            _FakeRuleSource(
                [
                    RulePattern(
                        'txn.account == "Joint" && txn.description.matches("(?i)mortgage")',
                        2,
                        "mortgage",
                    )
                ]
            )
        )
        hit = GatherContext(
            transaction_id=1,
            description="MORTGAGE PAYMENT",
            amount=Decimal("-800.00"),
            currency="GBP",
            transaction_date=date(2026, 6, 1),
            account_name="Joint",
        )
        assert gatherer.gather(hit)[0].claim.category_ids == (2,)
        other = GatherContext(
            transaction_id=1,
            description="MORTGAGE PAYMENT",
            amount=Decimal("-800.00"),
            currency="GBP",
            transaction_date=date(2026, 6, 1),
            account_name="Personal",
        )
        assert gatherer.gather(other) == []

    def test_requires_disambiguation_sets_requires_receipt(self) -> None:
        gatherer = RuleGatherer(
            _FakeRuleSource(
                [RulePattern(r"(?i)amzn", 1, "amazon", requires_disambiguation=True)]
            )
        )
        ev = gatherer.gather(_context("AMZN MKTP"))[0]
        assert ev.strength is StrengthTier.PROOF
        assert ev.requires_receipt is True
