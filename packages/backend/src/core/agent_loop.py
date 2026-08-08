"""Bounded Reason->Act->Observe agent loop for Bijou (Phase 2).

Provider-agnostic and side-effect-free by construction: the LLM call and the
tool executor are INJECTED, so this is fully unit-testable with fakes and does
not touch the live message path until it is explicitly wired in (behind
ENABLE_AGENT_LOOP). Hard step + token budgets prevent runaway loops (cost/429).

llm(messages) -> {"text": str|None, "tool_calls": [{"name","args"}], "tokens": int}
executor(name, args) -> result (any JSON-serializable)
"""
from dataclasses import dataclass, field


@dataclass
class Budget:
    max_steps: int = 3
    max_tokens: int = 4000


@dataclass
class LoopResult:
    reply: str
    steps: list = field(default_factory=list)
    stop_reason: str = ""
    tokens_used: int = 0


class AgentLoop:
    def __init__(self, llm, executor):
        self.llm = llm
        self.executor = executor

    def run(self, messages: list, budget: Budget | None = None) -> LoopResult:
        budget = budget or Budget()
        messages = list(messages)  # don't mutate caller's list
        steps: list = []
        tokens_used = 0

        for _ in range(budget.max_steps):
            out = self.llm(messages) or {}
            tokens_used += int(out.get("tokens", 0) or 0)
            tool_calls = out.get("tool_calls") or []

            if not tool_calls:
                # Model produced a final answer — done.
                return LoopResult(
                    reply=(out.get("text") or "").strip(),
                    steps=steps,
                    stop_reason="final_answer",
                    tokens_used=tokens_used,
                )

            # Act + Observe: run each tool, feed results back into context.
            for tc in tool_calls:
                result = self.executor(tc["name"], tc.get("args") or {})
                steps.append({"tool": tc["name"], "args": tc.get("args") or {}, "result": result})
                messages.append({"role": "tool", "name": tc["name"], "content": result})

            if tokens_used >= budget.max_tokens:
                return LoopResult(
                    reply=(out.get("text") or "").strip(),
                    steps=steps,
                    stop_reason="token_budget",
                    tokens_used=tokens_used,
                )

        # Step budget hit while still wanting tools — ask once more for a text wrap-up.
        final = self.llm(messages) or {}
        tokens_used += int(final.get("tokens", 0) or 0)
        return LoopResult(
            reply=(final.get("text") or "").strip(),
            steps=steps,
            stop_reason="step_budget",
            tokens_used=tokens_used,
        )
