"""Unit tests for the bounded AgentLoop (Phase 2)."""
from src.core.agent_loop import AgentLoop, Budget


def make_llm(script):
    """Return an llm() that yields each scripted response in turn."""
    calls = {"n": 0}

    def llm(messages):
        i = min(calls["n"], len(script) - 1)
        calls["n"] += 1
        return script[i]

    llm.calls = calls
    return llm


def echo_executor(name, args):
    return {"ok": True, "tool": name, "args": args}


def test_returns_text_immediately_when_no_tool_calls():
    llm = make_llm([{"text": "Eh hello boss!", "tokens": 10}])
    r = AgentLoop(llm, echo_executor).run([{"role": "user", "content": "hi"}])
    assert r.reply == "Eh hello boss!"
    assert r.stop_reason == "final_answer"
    assert r.steps == []
    assert llm.calls["n"] == 1


def test_executes_tool_then_returns_text():
    llm = make_llm([
        {"tool_calls": [{"name": "book_appointment", "args": {"day": "Mon"}}], "tokens": 20},
        {"text": "Booked already lah!", "tokens": 15},
    ])
    r = AgentLoop(llm, echo_executor).run([{"role": "user", "content": "book me"}])
    assert r.reply == "Booked already lah!"
    assert r.stop_reason == "final_answer"
    assert len(r.steps) == 1 and r.steps[0]["tool"] == "book_appointment"
    assert r.tokens_used == 35


def test_stops_at_max_steps_when_model_never_finishes():
    # llm ALWAYS asks for a tool -> must stop at the step budget, not loop forever
    always_tool = make_llm([{"tool_calls": [{"name": "search", "args": {}}], "tokens": 5}])
    r = AgentLoop(always_tool, echo_executor).run([{"role": "user", "content": "x"}], Budget(max_steps=3))
    assert r.stop_reason == "step_budget"
    assert len(r.steps) == 3  # exactly max_steps tool rounds, then bailed
    assert always_tool.calls["n"] == 4  # 3 loop calls + 1 final wrap-up call


def test_respects_token_budget():
    llm = make_llm([{"tool_calls": [{"name": "search", "args": {}}], "tokens": 5000}])
    r = AgentLoop(llm, echo_executor).run([{"role": "user", "content": "x"}], Budget(max_steps=5, max_tokens=100))
    assert r.stop_reason == "token_budget"
    assert r.tokens_used >= 100
    assert len(r.steps) == 1  # stopped after first over-budget round
