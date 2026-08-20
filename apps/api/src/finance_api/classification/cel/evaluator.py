"""Compile-once, eval-many CEL evaluator. Invalid expressions are skipped."""

from __future__ import annotations

import logging
from typing import Any

import celpy

from finance_api.classification.cel.activation import TxnActivation
from finance_api.classification.cel.migrate import migrate_rule_expression

logger = logging.getLogger(__name__)


class CelEvaluator:
    """Evaluates boolean CEL rules against a :class:`TxnActivation`.

    Compile failures and evaluation errors return ``None`` (skip) rather than
    raising, so a bad rule cannot abort classification.
    """

    def __init__(self) -> None:
        self._env = celpy.Environment()
        self._programs: dict[str, Any] = {}

    def compile(self, expression: str) -> Any | None:
        cel = migrate_rule_expression(expression)
        if cel in self._programs:
            return self._programs[cel]
        try:
            program = self._env.program(self._env.compile(cel))
        except Exception as exc:  # noqa: BLE001 - skip invalid, never fatal
            logger.warning("skipping invalid CEL '%s': %s", cel, exc)
            self._programs[cel] = None
            return None
        self._programs[cel] = program
        return program

    def matches(self, expression: str, activation: TxnActivation) -> bool | None:
        """Return True/False, or None when the expression cannot be evaluated."""
        program = self.compile(expression)
        if program is None:
            return None
        try:
            result = program.evaluate(
                {"txn": celpy.json_to_cel(activation.as_cel_map())}
            )
        except Exception as exc:  # noqa: BLE001 - skip invalid, never fatal
            logger.warning("skipping CEL eval '%s': %s", expression, exc)
            return None
        return bool(result)
