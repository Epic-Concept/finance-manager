"""Tests for the agentic tool-calling loop.

The loop drives a tool-using conversation: the model emits tool_calls, we execute
them and feed results back, until it returns a final answer or hits the iteration
cap. The chat function is injected, so the loop is tested with no network.
"""

import json

from finance_api.classification.llm import run_tool_loop


def _assistant(content=None, tool_calls=None):
    return {"role": "assistant", "content": content, "tool_calls": tool_calls}


def _tool_call(call_id: str, name: str, args: dict):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


class TestRunToolLoop:
    def test_immediate_answer_no_tools(self) -> None:
        calls = []

        def chat(messages, tools):
            calls.append(list(messages))
            return _assistant(content="done")

        result = run_tool_loop(chat, {}, [{"role": "user", "content": "hi"}])
        assert result == "done"
        assert len(calls) == 1

    def test_executes_tool_then_returns_answer(self) -> None:
        executed = []

        def search(args: dict) -> str:
            executed.append(args)
            return "Seeed sells electronics"

        responses = iter(
            [
                _assistant(
                    tool_calls=[_tool_call("c1", "web_search", {"query": "Seeed"})]
                ),
                _assistant(content="electronics"),
            ]
        )

        def chat(messages, tools):
            return next(responses)

        result = run_tool_loop(
            chat,
            {"web_search": search},
            [{"role": "user", "content": "classify Seeed"}],
        )
        assert result == "electronics"
        assert executed == [{"query": "Seeed"}]

    def test_tool_error_is_fed_back_not_fatal(self) -> None:
        def boom(args: dict) -> str:
            raise RuntimeError("search down")

        fed: list = []
        responses = iter(
            [
                _assistant(tool_calls=[_tool_call("c1", "web_search", {"query": "x"})]),
                _assistant(content="fallback answer"),
            ]
        )

        def chat(messages, tools):
            fed.append(list(messages))
            return next(responses)

        result = run_tool_loop(
            chat, {"web_search": boom}, [{"role": "user", "content": "go"}]
        )
        assert result == "fallback answer"
        # the second chat call saw a tool message carrying the error
        tool_msgs = [m for m in fed[-1] if m.get("role") == "tool"]
        assert tool_msgs and "search down" in tool_msgs[0]["content"]

    def test_iteration_cap_stops_runaway(self) -> None:
        chat_count = 0

        def always_tool(messages, tools):
            nonlocal chat_count
            chat_count += 1
            return _assistant(tool_calls=[_tool_call(f"c{chat_count}", "noop", {})])

        run_tool_loop(
            always_tool,
            {"noop": lambda args: "ok"},
            [{"role": "user", "content": "loop"}],
            max_iterations=3,
        )
        assert chat_count <= 3
