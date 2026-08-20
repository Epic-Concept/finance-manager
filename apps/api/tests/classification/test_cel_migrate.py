"""Tests for regex / DSL → CEL migration."""

from finance_api.classification.cel.migrate import (
    looks_like_cel,
    migrate_rule_expression,
)


class TestMigrateRuleExpression:
    def test_raw_regex_wraps_description_matches(self) -> None:
        assert (
            migrate_rule_expression(r"(?i)tesco")
            == 'txn.description.matches("(?i)tesco")'
        )

    def test_dsl_description_operator(self) -> None:
        assert (
            migrate_rule_expression('description =~ "(?i)amazon.co.uk"')
            == 'txn.description.matches("(?i)amazon.co.uk")'
        )

    def test_already_cel_is_idempotent(self) -> None:
        cel = 'txn.is_debit && txn.description.matches("(?i)tesco")'
        assert migrate_rule_expression(cel) == cel

    def test_escaped_merchant_key(self) -> None:
        assert migrate_rule_expression("ZABKA") == 'txn.description.matches("ZABKA")'

    def test_looks_like_cel(self) -> None:
        assert looks_like_cel("txn.amount_minor == 1")
        assert not looks_like_cel(r"(?i)tesco")
