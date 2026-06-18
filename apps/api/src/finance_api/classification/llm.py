"""Local LLM client for classification gatherers.

Targets the litellm gateway on ``gb10.local`` (OpenAI-compatible). The default
model (``qwen3.6-35b``) is a *reasoning* model: it emits chain-of-thought in a
separate ``reasoning_content`` field and the usable answer in ``content``, so a
generous ``max_tokens`` is required to get past reasoning to the answer.

Raw mailbox/financial content handed to this client stays on-prem (the gateway
and model both run on ``gb10.local``).
"""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

import httpx

from finance_api.core.config import settings


class LLMClient(Protocol):
    """Minimal text-in/text-out completion contract used by gatherers."""

    def complete(self, system: str, user: str) -> str: ...


class LiteLLMClient:
    """OpenAI-compatible client for the litellm gateway."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self._base_url = (base_url or settings.litellm_base_url).rstrip("/")
        self._api_key = api_key if api_key is not None else settings.litellm_api_key
        self._model = model or settings.litellm_model
        self._max_tokens = max_tokens or settings.litellm_max_tokens
        self._timeout = timeout or settings.litellm_timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    def complete(self, system: str, user: str) -> str:
        """Return the model's ``content`` for a system+user prompt."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": self._max_tokens,
            "temperature": 0,
        }
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"].get("content")
        return content or ""


def extract_json(text: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from model output.

    Tolerates reasoning preambles, surrounding prose, and ```json fences.
    Raises ``ValueError`` if no JSON object can be parsed.
    """
    stripped = text.strip()
    fence = re.search(
        r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL | re.IGNORECASE
    )
    if fence:
        stripped = fence.group(1).strip()
    try:
        return json.loads(stripped)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        pass
    # Fall back to the first balanced {...} object in the text.
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(stripped[start : end + 1])  # type: ignore[no-any-return]
        except json.JSONDecodeError as exc:
            raise ValueError(f"no parseable JSON object: {exc}") from exc
    raise ValueError("no JSON object found in model output")
