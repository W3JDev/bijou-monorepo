from src.connectors.base import Health, Policy, ToolResult, Action


def test_toolresult_defaults():
    r = ToolResult(success=True, data={"ok": 1})
    assert r.success and r.data == {"ok": 1}
    assert r.error is None and r.backend is None and r.user_message is None


def test_action_defaults_to_native_only():
    a = Action(description="x", input_schema={})
    assert a.policy is Policy.NATIVE_ONLY
    assert a.native is None and a.composio_slug is None


def test_health_values():
    assert {Health.OK, Health.DEGRADED, Health.DOWN}
