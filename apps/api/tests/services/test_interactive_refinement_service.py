"""Unit tests for InteractiveRefinementService (OpenAI-backed)."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from finance_api.models.category import Category
from finance_api.services.interactive_refinement_service import (
    InteractiveRefinementError,
    InteractiveRefinementService,
)
from finance_api.services.transaction_clustering_service import TransactionCluster


@dataclass
class _FakeTxn:
    id: int
    description: str


class _FakeCompletions:
    def __init__(
        self, reply: str | None = None, error: Exception | None = None
    ) -> None:
        self.reply = reply or ""
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        message = SimpleNamespace(content=self.reply)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeOpenAI:
    def __init__(
        self, reply: str | None = None, error: Exception | None = None
    ) -> None:
        self._completions = _FakeCompletions(reply=reply, error=error)
        self.chat = _FakeChat(self._completions)

    @property
    def calls(self) -> list[dict[str, Any]]:
        return self._completions.calls


PROPOSAL_REPLY = """Here is my proposal:

```json
{
  "proposals": [
    {
      "pattern": "txn.description.matches(\\"(?i)tesco\\") && txn.is_debit",
      "category_id": 1,
      "category_name": "Groceries",
      "confidence": "high",
      "reasoning": "All samples are Tesco"
    }
  ]
}
```
"""


def _category(cat_id: int = 1, name: str = "Groceries") -> Category:
    return Category(id=cat_id, name=name, description="Food shopping")


def _cluster() -> TransactionCluster:
    txns = [_FakeTxn(id=i, description=f"TESCO STORE {i}") for i in range(1, 4)]
    return TransactionCluster(
        cluster_key="TESCO",
        cluster_hash="abc",
        transactions=txns,  # type: ignore[arg-type]
        sample_descriptions=[t.description for t in txns],
    )


class TestInteractiveRefinementServiceOpenAI:
    def test_defaults_to_gpt_5_6_luna(self) -> None:
        client = _FakeOpenAI(reply="ok")
        service = InteractiveRefinementService(client=client)
        assert service._model == "gpt-5.6-luna"

    def test_start_session_uses_chat_completions_and_parses_proposals(self) -> None:
        client = _FakeOpenAI(reply=PROPOSAL_REPLY)
        service = InteractiveRefinementService(
            client=client, model="gpt-5.6-luna", api_key="test-key"
        )
        response = service.start_session(_cluster(), [_category()])

        assert len(client.calls) == 1
        call = client.calls[0]
        assert call["model"] == "gpt-5.6-luna"
        assert call["messages"][0]["role"] == "system"
        assert call["messages"][1]["role"] == "user"
        assert "max_completion_tokens" in call
        assert len(response.proposed_rules) == 1
        assert response.proposed_rules[0].category_name == "Groceries"
        assert "(?i)tesco" in response.proposed_rules[0].pattern

    def test_continue_session_appends_history_and_user_message(self) -> None:
        client = _FakeOpenAI(reply=PROPOSAL_REPLY)
        service = InteractiveRefinementService(client=client)
        history = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
        ]
        service.continue_session(
            history, "tighten the pattern", _cluster(), [_category()]
        )

        messages = client.calls[0]["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "first"}
        assert messages[2] == {"role": "assistant", "content": "reply"}
        assert messages[3] == {"role": "user", "content": "tighten the pattern"}

    def test_start_session_wraps_client_errors(self) -> None:
        client = _FakeOpenAI(error=RuntimeError("boom"))
        service = InteractiveRefinementService(client=client)
        with pytest.raises(InteractiveRefinementError, match="Failed to start session"):
            service.start_session(_cluster(), [_category()])
