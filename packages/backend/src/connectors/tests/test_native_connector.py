import pytest
from src.connectors.base import Action, Health
from src.connectors.native_connector import NativeConnector


@pytest.mark.asyncio
async def test_supports_and_health():
    nc = NativeConnector()
    assert await nc.health() is Health.OK
    assert nc.supports(Action("d", {}, native=lambda t, a: {"success": True}))
    assert not nc.supports(Action("d", {}))


@pytest.mark.asyncio
async def test_execute_sync_dict_envelope():
    def send(tenant_id, args):
        return {"success": True, "draft_id": "abc"}
    nc = NativeConnector()
    r = await nc.execute("t1", Action("d", {}, native=send), {"to": "x"})
    assert r.success and r.backend == "native" and r.data == {"success": True, "draft_id": "abc"}


@pytest.mark.asyncio
async def test_execute_async_callable_and_failure_mapping():
    async def send(tenant_id, args):
        return {"success": False, "error": "no creds"}
    nc = NativeConnector()
    r = await nc.execute("t1", Action("d", {}, native=send), {})
    assert not r.success and r.error == "no creds" and r.backend == "native"


@pytest.mark.asyncio
async def test_execute_catches_exception():
    def boom(tenant_id, args):
        raise RuntimeError("kaboom")
    nc = NativeConnector()
    r = await nc.execute("t1", Action("d", {}, native=boom), {})
    assert not r.success and "kaboom" in r.error and r.backend == "native"
