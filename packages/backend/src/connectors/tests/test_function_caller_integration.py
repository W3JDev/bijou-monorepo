"""Integration: the connector router wired into FunctionCaller (src/saas/function_caller.py).

Constructs FunctionCaller with enabled=False (no Gemini client needed) and an
injected router, so these run in the isolated venv without google.genai.
"""
import pytest
from src.connectors.base import Action, Policy, Health
from src.connectors.router import ConnectorRouter
from src.connectors.native_connector import NativeConnector
from src.connectors.composio_connector import ComposioConnector
from src.saas.function_caller import FunctionCaller


class _FakeTools:
    def execute(self, slug, arguments=None, *, user_id=None, **kwargs):
        return {"successful": True, "data": {"slug": slug, "user": user_id, "args": arguments}, "error": None}


class _FakeClient:
    tools = _FakeTools()


def _registry():
    return {
        "sheets.append_row": Action(
            "Append a row to the tenant's Google Sheet",
            {"type": "object", "properties": {"values": {"type": "array"}}},
            composio_slug="GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND",
            policy=Policy.COMPOSIO_ONLY,
            degrade_message="Aiyo boss, cannot update the sheet right now — I noted it down first.",
        ),
    }


def _make_fc(monkeypatch, composio_client=None, health_state=Health.OK, enabled=True):
    monkeypatch.setenv("ENABLE_COMPOSIO", "true" if enabled else "false")
    router = None
    if composio_client is not None:
        router = ConnectorRouter({
            "native": NativeConnector(),
            "composio": ComposioConnector(client=composio_client, health_state=health_state),
        })
    return FunctionCaller(
        tool_orchestrator=None, gemini_api_key=None,
        connector_router=router, connector_registry=_registry() if enabled else None,
    )


def test_declarations_include_composio_long_tail(monkeypatch):
    fc = _make_fc(monkeypatch, composio_client=_FakeClient())
    names = {f["name"] for f in fc.get_function_declarations()}
    assert "sheets_append_row" in names  # dotted canonical -> Gemini-safe name


@pytest.mark.asyncio
async def test_call_function_routes_to_composio(monkeypatch):
    fc = _make_fc(monkeypatch, composio_client=_FakeClient())
    out = await fc._call_function(
        "sheets_append_row", {"values": ["a", "b"]}, {"tenant_id": "tenant-42"})
    assert out["success"] is True
    assert out["backend"] == "composio"
    assert out["data"]["user"] == "tenant-42"       # tenant_id flowed to Composio user_id
    assert out["data"]["slug"] == "GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND"


@pytest.mark.asyncio
async def test_call_function_degrades_when_composio_down(monkeypatch):
    fc = _make_fc(monkeypatch, composio_client=_FakeClient(), health_state=Health.DOWN)
    out = await fc._call_function("sheets_append_row", {"values": ["x"]}, {"tenant_id": "t1"})
    assert out["success"] is False
    assert out["backend"] is None
    assert "noted it down" in out["user_message"]   # friendly, no raise


@pytest.mark.asyncio
async def test_flag_off_is_a_noop_and_unknown_still_raises(monkeypatch):
    """ENABLE_COMPOSIO=false -> connector path never runs; unknown fn raises as before."""
    fc = _make_fc(monkeypatch, composio_client=None, enabled=False)
    assert fc.composio_enabled is False
    with pytest.raises(ValueError, match="Unknown function"):
        await fc._call_function("sheets_append_row", {"values": ["x"]}, {"tenant_id": "t1"})
