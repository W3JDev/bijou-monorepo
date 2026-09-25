"""Tests for the gateway-primary agent loop: unit (mock client) + real integration."""
import json
import os
from types import SimpleNamespace

import pytest

from src.core.agent_loop import Budget
from src.core.gateway_agent import history_to_openai, run_gateway_agent, to_openai_tools


# ---- helpers to fake an OpenAI-style response ----
def _msg(content=None, tool_calls=None):
    tcs = None
    if tool_calls:
        tcs = [
            SimpleNamespace(id=f"tc{i}", function=SimpleNamespace(name=n, arguments=json.dumps(a)))
            for i, (n, a) in enumerate(tool_calls)
        ]
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=tcs))])


def _client(responses):
    """A fake client whose chat.completions.create yields each response in turn."""
    calls = {"n": 0}

    def create(**kwargs):
        i = min(calls["n"], len(responses) - 1)
        calls["n"] += 1
        return responses[i]

    c = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    c._calls = calls
    return c


async def _echo_exec(name, args):
    return {"status": "success", "tool": name, "args": args}


def test_to_openai_tools_wraps_declarations():
    out = to_openai_tools([{"name": "book", "description": "b", "parameters": {"type": "object"}}])
    assert out == [{"type": "function", "function": {"name": "book", "description": "b", "parameters": {"type": "object"}}}]


def test_history_maps_model_to_assistant():
    h = [{"role": "user", "parts": [{"text": "hi"}]}, {"role": "model", "parts": [{"text": "eh hello"}]}]
    assert history_to_openai(h) == [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "eh hello"}]


async def test_returns_text_when_no_tool_calls():
    client = _client([_msg(content="Eh hello boss!")])
    r = await run_gateway_agent(system="s", user_message="hi", history=[], declarations=[],
                                client=client, model_chain=["m"], execute_tool=_echo_exec)
    assert r["reply"] == "Eh hello boss!" and r["steps"] == []


async def test_executes_tool_then_answers():
    client = _client([_msg(tool_calls=[("book_appointment", {"day": "Mon"})]), _msg(content="Booked lah!")])
    r = await run_gateway_agent(system="s", user_message="book", history=[],
                                declarations=[{"name": "book_appointment", "parameters": {"type": "object"}}],
                                client=client, model_chain=["m"], execute_tool=_echo_exec)
    assert r["reply"] == "Booked lah!"
    assert len(r["steps"]) == 1 and r["steps"][0]["tool"] == "book_appointment"
    assert r["steps"][0]["result"]["status"] == "success"


async def test_guard_blocks_consequential_tool_without_executing():
    executed = {"hit": False}

    async def exec_tool(name, args):
        executed["hit"] = True
        return {"status": "success"}

    client = _client([_msg(tool_calls=[("book_appointment", {"day": "Mon"})]), _msg(content="Shall I confirm ah?")])
    r = await run_gateway_agent(system="s", user_message="book", history=[],
                                declarations=[{"name": "book_appointment", "parameters": {"type": "object"}}],
                                client=client, model_chain=["m"], execute_tool=exec_tool,
                                guard=lambda n: "confirm")
    assert executed["hit"] is False  # blocked -> executor never ran
    assert r["steps"][0]["result"]["status"] == "blocked"


async def test_stops_at_step_budget():
    # model ALWAYS asks for a tool -> must bail at budget, then do a final wrap-up call
    client = _client([_msg(tool_calls=[("search", {})])])
    r = await run_gateway_agent(system="s", user_message="x", history=[],
                                declarations=[{"name": "search", "parameters": {"type": "object"}}],
                                client=client, model_chain=["m"], execute_tool=_echo_exec, budget=Budget(max_steps=2))
    assert len(r["steps"]) == 2  # exactly max_steps tool rounds


# ---- real integration: drive the loop against the live gateway ----
@pytest.mark.integration
async def test_real_gateway_full_tool_loop():
    # Credentials come from the environment, like everything else here.
    #
    # This used to read an absolute path into a DIFFERENT, pre-monorepo repo on
    # one developer's machine:
    #   C:/Users/.../Bijou-AI---Digital-Employee-main/.env
    # Anywhere else that is FileNotFoundError, raised inside open() BEFORE the
    # `pytest.skip("no gateway creds")` two lines below could run — so a test
    # that already meant to skip without credentials instead failed the suite
    # for everyone. The legacy path is still honoured if it happens to exist,
    # so nothing is lost on the machine it was written for.
    #
    # The misspelled CUSTOME_* names are kept: they are what that .env
    # actually contains.
    import os

    def _from_env(*names):
        for n in names:
            v = os.getenv(n)
            if v and v.strip():
                return v.strip()
        return None

    def _from_legacy_env_file(*names):
        land = os.getenv(
            "BIJOU_LEGACY_ENV_FILE",
            r"C:/Users/W3jde/local-projects/Bijou-AI---Digital-Employee-main/Bijou-AI---Digital-Employee-main/.env",
        )
        if not os.path.isfile(land):
            return None
        with open(land, encoding="utf-8", errors="ignore") as fh:
            for ln in fh:
                for n in names:
                    if ln.strip().startswith(n + "="):
                        return ln.split("=", 1)[1].strip()
        return None

    ep = _from_env("CUSTOM_API_ENDPOINT", "CUSTOME_API_ENDOINT") or _from_legacy_env_file(
        "CUSTOM_API_ENDPOINT", "CUSTOME_API_ENDOINT"
    )
    key = _from_env("CUSTOM_API_KEY", "CUSTOME_API_KEY") or _from_legacy_env_file(
        "CUSTOM_API_KEY", "CUSTOME_API_KEY"
    )
    if not ep or not key:
        pytest.skip("no gateway creds (set CUSTOM_API_ENDPOINT and CUSTOM_API_KEY)")
    from openai import OpenAI

    client = OpenAI(base_url=ep, api_key=key)
    decls = [{"name": "book_appointment", "description": "Book a call appointment",
              "parameters": {"type": "object",
                             "properties": {"day": {"type": "string"}, "time": {"type": "string"}}}}]
    seen = {}

    async def exec_tool(name, args):
        seen["name"] = name
        seen["args"] = args
        return {"status": "success", "confirmation": "BK123"}

    r = await run_gateway_agent(
        system="You are Bijou. Use tools when the user asks to book.",
        user_message="Book me a call for Monday at 3pm", history=[], declarations=decls,
        client=client, model_chain=["cc/claude-haiku-4-5-20251001"], execute_tool=exec_tool,
    )
    assert seen.get("name") == "book_appointment", f"gateway should have called the tool; got {seen}"
    assert isinstance(r["reply"], str) and r["reply"]  # got a final natural-language reply
