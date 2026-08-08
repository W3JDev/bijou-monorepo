"""Gateway-primary agent (Phase 2 integration).

Routes the WhatsApp agent's tool-calling loop through the OmniRoute gateway
(OpenAI-compatible) instead of Gemini's native function-calling. Bounded loop +
budget, ActionGuard-aware, async-native. Provider is injected (the OpenAI-style
client), so it's unit-testable with fakes; the real gateway is integration-tested
separately. It NEVER runs unless explicitly enabled and, on any error, the caller
falls back to the existing Gemini path — so it cannot break replies.
"""
import asyncio
import json
import logging

from src.core.agent_loop import Budget

logger = logging.getLogger(__name__)


def to_openai_tools(declarations):
    """Gemini-style [{name,description,parameters}] -> OpenAI [{type:function, function:{...}}]."""
    return [{"type": "function", "function": d} for d in (declarations or [])]


def history_to_openai(history):
    """Bijou history [{role, parts:[{text}]}] -> OpenAI [{role, content}] (role 'model'->'assistant')."""
    out = []
    for m in (history or [])[-10:]:
        parts = m.get("parts", []) or []
        text = parts[0].get("text", "") if parts else ""
        if text:
            out.append({"role": "assistant" if m.get("role") == "model" else "user", "content": text})
    return out


async def _complete(client, model_chain, messages, tools):
    """Try each model in the chain until one succeeds; returns the OpenAI response."""
    last_err = None
    for model in model_chain:
        try:
            return await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=messages,
                tools=(tools or None),
                tool_choice=("auto" if tools else None),
                temperature=0.7,
                max_tokens=1024,
            )
        except Exception as e:
            last_err = e
            logger.warning(f"gateway model {model} failed: {e}")
    raise last_err or RuntimeError("all gateway models failed")


async def run_gateway_agent(
    *, system, user_message, history, declarations, client, model_chain,
    execute_tool, guard=None, budget=None,
):
    """Bounded gateway tool-calling loop.

    execute_tool: async (name, args) -> result dict.
    guard: optional (name) -> 'allow' | 'confirm' | 'deny'.
    Returns {"reply": str, "steps": list}.
    """
    budget = budget or Budget()
    tools = to_openai_tools(declarations)
    messages = (
        [{"role": "system", "content": system}]
        + history_to_openai(history)
        + [{"role": "user", "content": user_message}]
    )
    steps = []

    for _ in range(budget.max_steps):
        resp = await _complete(client, model_chain, messages, tools)
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            return {"reply": (msg.content or "").strip(), "steps": steps}

        # Preserve the assistant turn (with its tool_calls) for the model's context.
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            mode = guard(name) if guard else "allow"
            if mode != "allow":
                result = {
                    "status": "blocked",
                    "guard": mode,
                    "message": (
                        f"Action '{name}' needs confirmation before it runs."
                        if mode == "confirm" else f"Action '{name}' is not permitted."
                    ),
                }
            else:
                result = await execute_tool(name, args)
            steps.append({"tool": name, "args": args, "result": result})
            messages.append({
                "role": "tool", "tool_call_id": tc.id,
                "content": json.dumps(result, default=str),
            })

    # Step budget hit while still calling tools — one final text wrap-up (no tools).
    resp = await _complete(client, model_chain, messages, None)
    return {"reply": (resp.choices[0].message.content or "").strip(), "steps": steps}
