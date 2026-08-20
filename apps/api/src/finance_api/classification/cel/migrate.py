"""Mechanical migration of regex / rule-engine expressions to CEL."""

from __future__ import annotations

import re

_DSL_PATTERN = re.compile(r'=~\s*"((?:\\.|[^"])*)"')


def _escape_cel_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def looks_like_cel(expression: str) -> bool:
    """True when the stored string is already a CEL boolean over ``txn``."""
    stripped = expression.strip()
    if not stripped:
        return False
    return (
        stripped.startswith("txn.")
        or ".matches(" in stripped
        or "&&" in stripped
        or "||" in stripped
    )


def cel_for_merchant(key: str) -> str:
    """CEL predicate matching a merchant token in the description (case-insensitive)."""
    return migrate_rule_expression(f"(?i){re.escape(key)}")


def migrate_rule_expression(raw: str) -> str:
    """Convert a stored rule to CEL. Idempotent for expressions already in CEL.

    Accepts:
    - CEL (``txn.description.matches(...)``)
    - legacy DSL (``description =~ "PAT"``)
    - a raw Python/regex pattern over the description
    """
    stripped = raw.strip()
    if looks_like_cel(stripped):
        return stripped
    dsl = _DSL_PATTERN.search(stripped)
    if dsl:
        return f'txn.description.matches("{_escape_cel_string(dsl.group(1))}")'
    return f'txn.description.matches("{_escape_cel_string(stripped)}")'
