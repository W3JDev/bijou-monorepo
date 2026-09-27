"""Linking a NEW client's WhatsApp: QR, connect detection, disconnect.

The fake bridge below answers with the exact shapes the pinned GOWA image
returned when probed on 2026-09-27 (POST /devices, GET /app/login,
DEVICE_NOT_FOUND, ALREADY_LOGGED_IN, DELETE /devices/{id}; /device/{id} is not
a route and answers 400 DEVICE_ID_REQUIRED).

Bugs these pin:
  * No whatsapp_devices row was ever written when the bridge device already
    existed, and connect detection wrote tenants only — inbound routing
    (whatsapp_devices.whatsapp_jid) then fell back to a JID several tenants share.
  * Bridge down -> 500 with a raw httpx message instead of a 503.
  * Dashboard disconnect called DELETE /device/{id}, so the phone stayed linked.
  * v2 QR forced https:// onto the plain-HTTP internal bridge.
"""

import asyncio

import httpx
import pytest
from fastapi import HTTPException

from src.saas import onboarding_api

TENANT = "11111111-2222-3333-4444-555555555555"
PNG = b"\x89PNG\r\n\x1a\nfake"


class FakeTable:
    def __init__(self, db, name):
        self.db, self.name, self.op, self.payload, self.kw = db, name, "select", None, {}

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a):
        return self

    def limit(self, *_a):
        return self

    def upsert(self, payload, **kw):
        self.op, self.payload, self.kw = "upsert", payload, kw
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    def execute(self):
        self.db.calls.append((self.name, self.op, self.payload, self.kw))
        data = self.db.rows.get(self.name, []) if self.op == "select" else []
        return type("R", (), {"data": data})()


class FakeDB:
    def __init__(self, rows=None):
        self.rows, self.calls = rows or {}, []

    def table(self, name):
        return FakeTable(self, name)

    def writes(self, table):
        return [c for c in self.calls if c[0] == table and c[1] != "select"]


@pytest.fixture
def bridge(monkeypatch):
    """A fake GOWA on http://bridge:3000. `state` controls its answers."""
    monkeypatch.setenv("WHATSAPP_BRIDGE_URL", "http://bridge:3000")
    monkeypatch.setenv("BRIDGE_USER", "u")
    monkeypatch.setenv("BRIDGE_PASSWORD", "p")
    state = {"devices": {f"bijou-{TENANT}"}, "down": False, "logged_in": False, "seen": []}

    def handler(req: httpx.Request):
        state["seen"].append(f"{req.method} {req.url.path}")
        if state["down"]:
            raise httpx.ConnectError("All connection attempts failed")
        dev = req.url.params.get("device_id") or req.headers.get("X-Device-Id")
        p = req.url.path
        if req.method == "POST" and p == "/devices":
            state["devices"].add(dev := __import__("json").loads(req.content)["device_id"])
            return httpx.Response(200, json={"code": "SUCCESS", "results": {"id": dev}})
        if p == "/app/login":
            if dev not in state["devices"]:
                return httpx.Response(404, json={"code": "DEVICE_NOT_FOUND"})
            if state["logged_in"]:
                return httpx.Response(400, json={"code": "ALREADY_LOGGED_IN"})
            return httpx.Response(200, json={"code": "SUCCESS", "results": {
                "qr_link": "http://bridge:3000/statics/qrcode/scan-qr-x.png"}})
        if p.startswith("/statics/"):
            return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
        if p == "/app/logout":
            return httpx.Response(200, json={"code": "SUCCESS"})
        if req.method == "DELETE" and p.startswith("/devices/"):
            state["devices"].discard(p.rsplit("/", 1)[1])
            return httpx.Response(200, json={"code": "SUCCESS", "message": "Device removed"})
        return httpx.Response(400, json={"code": "DEVICE_ID_REQUIRED"})

    real = httpx.AsyncClient

    def client(*a, **k):
        k["transport"] = httpx.MockTransport(handler)
        return real(*a, **k)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    return state


def run(coro):
    return asyncio.run(coro)


def test_existing_bridge_device_without_row_gets_a_mapping(bridge):
    db = FakeDB()
    assert run(onboarding_api.bridge_qr_png(db, TENANT, "Kedai")) == PNG
    ups = db.writes("whatsapp_devices")
    assert ups and ups[0][2]["device_id"] == f"bijou-{TENANT}"
    assert ups[0][3] == {"on_conflict": "tenant_id"}


def test_missing_bridge_device_is_provisioned_with_our_id(bridge):
    bridge["devices"].clear()
    db = FakeDB()
    assert run(onboarding_api.bridge_qr_png(db, TENANT, "Kedai")) == PNG
    assert "POST /devices" in bridge["seen"]
    assert db.writes("whatsapp_devices")[0][2]["device_id"] == f"bijou-{TENANT}"


def test_stored_mapping_is_not_rewritten_on_every_refresh(bridge):
    db = FakeDB({"whatsapp_devices": [{"device_id": f"bijou-{TENANT}"}]})
    run(onboarding_api.bridge_qr_png(db, TENANT, "Kedai"))
    assert db.writes("whatsapp_devices") == []


def test_bridge_down_is_503_not_500(bridge):
    bridge["down"] = True
    with pytest.raises(HTTPException) as e:
        run(onboarding_api.bridge_qr_png(FakeDB(), TENANT, "Kedai"))
    assert e.value.status_code == 503


def test_already_logged_in_is_409(bridge):
    bridge["logged_in"] = True
    with pytest.raises(HTTPException) as e:
        run(onboarding_api.bridge_qr_png(FakeDB(), TENANT, "Kedai"))
    assert e.value.status_code == 409


def test_connect_records_normalised_jid_for_routing():
    db = FakeDB()
    onboarding_api.record_connected_device(db, TENANT, "dev-1", "60123456789:7@s.whatsapp.net")
    (_, op, payload, kw), = db.writes("whatsapp_devices")
    assert op == "upsert" and kw == {"on_conflict": "tenant_id"}
    assert payload["whatsapp_jid"] == "60123456789@s.whatsapp.net"
    assert payload["device_id"] == "dev-1"


def test_dashboard_disconnect_uses_real_gowa_route(bridge, monkeypatch):
    from src.core import dashboard_api_simple as dash

    db = FakeDB()  # no mapping row: must still reach the bridge
    monkeypatch.setattr(dash, "get_supabase", lambda: db)
    out = run(dash.disconnect_whatsapp(tenant_id=TENANT))
    assert out["success"] is True
    assert f"DELETE /devices/bijou-{TENANT}" in bridge["seen"]
    assert f"bijou-{TENANT}" not in bridge["devices"]


def test_dashboard_qr_works_without_mapping_row(bridge, monkeypatch):
    from src.core import dashboard_api_simple as dash

    db = FakeDB({"tenants": [{"business_name": "Kedai"}]})
    monkeypatch.setattr(dash, "get_supabase", lambda: db)
    out = run(dash.get_whatsapp_qr(tenant_id=TENANT))
    assert out["status"] == "success" and out["qr"].startswith("data:image/png;base64,")


def test_keepalive_never_deletes_device_mappings():
    """Every backend on the prod DB runs this against its OWN bridge; pruning
    by one bridge's view wiped the others' tenants (the table went empty)."""
    import inspect

    from src.core import bijou

    src = inspect.getsource(bijou._wa_keepalive_monitor)
    assert ".delete()" not in src


def test_v2_qr_returns_data_uri_over_plain_http_bridge(bridge, monkeypatch):
    from src.saas import onboarding_complete as v2

    db = FakeDB({"tenants": [{"business_name": "Kedai"}]})
    monkeypatch.setattr(v2, "get_supabase", lambda: db)
    out = run(v2.get_whatsapp_qr(TENANT))
    assert out["results"]["qr_link"].startswith("data:image/png;base64,")
