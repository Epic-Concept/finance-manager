"""CEL synthesis for a cohort: templates first, LLM only on template failure."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any, Protocol

from finance_api.classification.cel import (
    CelEvaluator,
    looks_like_cel,
    migrate_rule_expression,
)
from finance_api.classification.cel.activation import amount_to_minor
from finance_api.classification.cohorts.clustering import CohortCluster
from finance_api.classification.llm import extract_json
from finance_api.services.transaction_clustering_service import (
    TransactionClusteringService,
)

_LLM_SYSTEM = (
    "You write a CEL boolean over txn.* that matches ONLY the sample "
    "transactions. Allowed fields: txn.description, txn.merchant, "
    "txn.account, txn.amount_minor (int), txn.day_of_month, txn.is_debit. "
    'Use matches("(?i)...") for descriptions. No custom functions. '
    'Respond ONLY with JSON {"expression": "<cel>"}.'
)


class _LLM(Protocol):
    def complete(self, system: str, user: str) -> str: ...


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def template_cel(
    cluster: CohortCluster,
    clustering: TransactionClusteringService | None = None,
) -> str:
    """Deterministic CEL covering a cluster (merchant, optional sign/account/amount)."""
    clustering = clustering or TransactionClusteringService()
    txns = list(cluster.transactions)
    merchant = clustering.extract_cluster_key(txns[0].description or "")
    parts = [f'txn.description.matches("(?i){_escape(re.escape(merchant))}")']

    minors = {amount_to_minor(t.amount) for t in txns}
    signs = {m < 0 for m in minors}
    if signs == {True}:
        parts.append("txn.is_debit")
    elif signs == {False}:
        parts.append("!txn.is_debit")

    accounts = {getattr(t, "account_name", None) or "" for t in txns}
    if cluster.stage in {"A", "B"} and len(accounts) == 1:
        account = next(iter(accounts))
        if account:
            parts.append(f'txn.account == "{_escape(account)}"')

    if cluster.stage == "A" and len(minors) == 1:
        parts.append(f"txn.amount_minor == {next(iter(minors))}")

    if cluster.stage == "D":
        days = {t.transaction_date.day for t in txns}
        parts.append(
            f"txn.day_of_month >= {min(days)} && txn.day_of_month <= {max(days)}"
        )
        if len(minors) == 1:
            parts.append(f"txn.amount_minor == {next(iter(minors))}")

    return " && ".join(parts)


def llm_cel(
    cluster: CohortCluster,
    client: _LLM,
    evaluator: CelEvaluator | None = None,
) -> str | None:
    """Ask the LLM for CEL; discard anything that does not compile."""
    evaluator = evaluator or CelEvaluator()
    samples = "\n".join(f"- {s}" for s in cluster.sample_descriptions)
    user = f"Cluster key: {cluster.cluster_key}\nSamples:\n{samples}"
    try:
        data = extract_json(client.complete(_LLM_SYSTEM, user))
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    raw = data.get("expression")
    if not isinstance(raw, str) or not looks_like_cel(raw):
        return None
    expression = migrate_rule_expression(raw)
    if evaluator.compile(expression) is None:
        return None
    return expression


def labelled_false_positives(
    expression: str,
    universe: Sequence[Any],
    cohort_ids: set[int],
    labelled: dict[int, int],
    evaluator: CelEvaluator | None = None,
) -> list[Any]:
    """Matches labelled as a different nominal than any in-cohort label."""
    evaluator = evaluator or CelEvaluator()
    in_cohort_labels = {labelled[i] for i in cohort_ids if i in labelled}
    fps = []
    from finance_api.classification.cel import activation_from_transaction

    for txn in universe:
        txn_id = txn.id
        if txn_id in cohort_ids:
            continue
        if evaluator.matches(expression, activation_from_transaction(txn)) is not True:
            continue
        label = labelled.get(txn_id)
        if label is not None and in_cohort_labels and label not in in_cohort_labels:
            fps.append(txn)
        elif label is not None and not in_cohort_labels:
            fps.append(txn)
    return fps
