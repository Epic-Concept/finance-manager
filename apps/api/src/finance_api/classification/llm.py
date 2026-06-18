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
import logging
import re
from collections.abc import Callable
from typing import Any, Protocol

import httpx

from finance_api.core.config import settings

logger = logging.getLogger(__name__)

# A chat step: given (messages, tools) return the assistant message dict
# (with optional "content" and "tool_calls"). Injected so the loop is testable.
ChatFn = Callable[[list[dict[str, Any]], list[dict[str, Any]] | None], dict[str, Any]]
ToolExecutor = Callable[[dict[str, Any]], str]


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

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """One tool-aware chat step; returns the raw assistant message dict."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": 0,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        message: dict[str, Any] = response.json()["choices"][0]["message"]
        return message


def run_tool_loop(
    chat_fn: ChatFn,
    executors: dict[str, ToolExecutor],
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    max_iterations: int = 6,
) -> str:
    """Drive a tool-using conversation until the model answers or iterations run out.

    The model emits ``tool_calls``; each is executed via ``executors`` and the
    result fed back as a ``tool`` message. A tool that raises has its error fed
    back (never fatal). ``max_iterations`` bounds the back-and-forth.
    """
    for _ in range(max_iterations):
        message = chat_fn(messages, tools)
        messages.append(message)
        tool_calls = message.get("tool_calls")
        if not tool_calls:
            return message.get("content") or ""
        for call in tool_calls:
            fn = call["function"]
            name = fn["name"]
            try:
                args = json.loads(fn.get("arguments") or "{}")
                result = executors[name](args)
            except Exception as exc:  # noqa: BLE001 - tool errors degrade, never crash
                result = f"error: {exc}"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "content": result,
                }
            )
    return ""


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
