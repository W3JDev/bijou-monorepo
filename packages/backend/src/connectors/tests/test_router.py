import pytest
from src.connectors.base import Action, Policy, Health
from src.connectors.native_connector import NativeConnector
from src.connectors.composio_connector import ComposioConnector
from src.connectors.router import ConnectorRouter


def _client_ok(row=1):
    class T:
        def execute(self, slug, arguments=None, *, user_id=None, **kwargs):
            return {"successful": True, "data": {"row": row}, "error": None}

    class C:
        tools = T()
    return C()


def _registry():
    return {
        "email.send": Action("send email", {}, native=lambda t, a: {"success": True, "data": "sent"},
                             policy=Policy.NATIVE_ONLY),
        "calendar.book_slot": Action("book", {}, native=lambda t, a: {"success": True, "data": "booked"},
                                     composio_slug="GOOGLECALENDAR_CREATE_EVENT", policy=Policy.NATIVE_FIRST),
        "sheets.append_row": Action("append", {}, composio_slug="GOOGLESHEETS_APPEND",
                                    policy=Policy.COMPOSIO_ONLY,
                                    degrade_message="Aiyo boss, cannot update the sheet right now — I noted it down first."),
    }


@pytest.mark.asyncio
async def test_composio_only_success():
    router = ConnectorRouter({"native": NativeConnector(),
                              "composio": ComposioConnector(client=_client_ok(row=7))})
    r = await router.execute("t1", "sheets.append_row", {"values": ["x"]}, _registry())
    assert r.success and r.backend == "composio" and r.data == {"row": 7}


@pytest.mark.asyncio
async def test_native_first_prefers_native():
    router = ConnectorRouter({"native": NativeConnector(),
                              "composio": ComposioConnector(client=_client_ok())})
    r = await router.execute("t1", "calendar.book_slot", {}, _registry())
    assert r.success and r.backend == "native"      # composio never touched


@pytest.mark.asyncio
async def test_resilience_composio_down():
    """THE resilience proof: Composio DOWN -> native_first still works, composio_only degrades gracefully."""
    router = ConnectorRouter({
        "native": NativeConnector(),
        "composio": ComposioConnector(client=_client_ok(), health_state=Health.DOWN),
    })
    reg = _registry()
    # critical NATIVE_FIRST action survives
    booked = await router.execute("t1", "calendar.book_slot", {}, reg)
    assert booked.success and booked.backend == "native"
    # long-tail COMPOSIO_ONLY action degrades — no raise, friendly message, no backend
    sheet = await router.execute("t1", "sheets.append_row", {"values": ["x"]}, reg)
    assert sheet.success is False
    assert sheet.backend is None
    assert "noted it down" in sheet.user_message


@pytest.mark.asyncio
async def test_unknown_action_degrades():
    router = ConnectorRouter({"native": NativeConnector()})
    r = await router.execute("t1", "does.not.exist", {}, _registry())
    assert r.success is False and r.user_message
