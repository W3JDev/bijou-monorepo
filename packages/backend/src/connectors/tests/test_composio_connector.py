import pytest
from src.connectors.base import Action, Health
from src.connectors.composio_connector import ComposioConnector


class FakeTools:
    def __init__(self, result=None, exc=None):
        self._r, self._e = result, exc

    def execute(self, slug, arguments=None, *, user_id=None, **kwargs):
        if self._e:
            raise self._e
        self.captured = {"slug": slug, "user_id": user_id, "arguments": arguments}
        self.version_kwargs = kwargs
        return self._r


class FakeClient:
    def __init__(self, result=None, exc=None):
        self.tools = FakeTools(result, exc)


@pytest.mark.asyncio
async def test_supports_and_health():
    cc = ComposioConnector(client=FakeClient(), health_state=Health.DOWN)
    assert cc.supports(Action("d", {}, composio_slug="GOOGLESHEETS_X"))
    assert not cc.supports(Action("d", {}))
    assert await cc.health() is Health.DOWN


@pytest.mark.asyncio
async def test_execute_maps_success_envelope():
    client = FakeClient(result={"successful": True, "data": {"row": 5}, "error": None})
    cc = ComposioConnector(client=client)
    action = Action("d", {}, composio_slug="GOOGLESHEETS_APPEND")
    r = await cc.execute("tenant-1", action, {"values": ["a", "b"]})
    assert r.success and r.data == {"row": 5} and r.backend == "composio"
    assert client.tools.captured == {
        "slug": "GOOGLESHEETS_APPEND", "user_id": "tenant-1",
        "arguments": {"values": ["a", "b"]},
    }


@pytest.mark.asyncio
async def test_execute_maps_failure_envelope():
    client = FakeClient(result={"successful": False, "data": None, "error": "not connected"})
    cc = ComposioConnector(client=client)
    r = await cc.execute("t", Action("d", {}, composio_slug="X"), {})
    assert not r.success and r.error == "not connected" and r.backend == "composio"


@pytest.mark.asyncio
async def test_execute_catches_exception():
    cc = ComposioConnector(client=FakeClient(exc=RuntimeError("connect.composio.dev unreachable")))
    r = await cc.execute("t", Action("d", {}, composio_slug="X"), {})
    assert not r.success and "unreachable" in r.error and r.backend == "composio"


@pytest.mark.asyncio
async def test_execute_passes_version_directive():
    """Composio requires a version for manual execution (verified live 2026-07-22):
    skip-check by default, or a pinned version when configured."""
    client = FakeClient(result={"successful": True, "data": {}, "error": None})
    await ComposioConnector(client=client).execute("t", Action("d", {}, composio_slug="X"), {})
    assert client.tools.version_kwargs == {"dangerously_skip_version_check": True}

    client2 = FakeClient(result={"successful": True, "data": {}, "error": None})
    await ComposioConnector(client=client2, tool_version="20250101").execute("t", Action("d", {}, composio_slug="X"), {})
    assert client2.tools.version_kwargs == {"version": "20250101"}


@pytest.mark.asyncio
async def test_execute_maps_real_toolexecuteresponse():
    """Contract test against the REAL SDK response object (composio 0.18.0),
    not just a dict — proves the getattr mapping matches ToolExecuteResponse."""
    pytest.importorskip("composio_client")
    from composio_client.types.tool_execute_response import ToolExecuteResponse
    resp = ToolExecuteResponse(data={"row": 9}, error=None, successful=True)
    cc = ComposioConnector(client=FakeClient(result=resp))
    r = await cc.execute("t", Action("d", {}, composio_slug="GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND"), {"values": ["x"]})
    assert r.success and r.data == {"row": 9} and r.backend == "composio"
