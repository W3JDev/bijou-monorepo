"""HTTP-layer tests for the connector OAuth API via FastAPI TestClient.

Composio + Supabase are mocked and the auth dependency (require_tenant) is
overridden, so these verify routing, auth wiring, status codes, ownership checks,
and persistence without any live call.
"""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.connectors import oauth_api

_AUTH_ENVS = [
    "COMPOSIO_AUTH_ID_GOOGLE_SHEETS", "COMPOSIO_AUTH_ID_GOOGLE_CALENDAR",
    "COMPOSIO_AUTH_ID_GOOGLE_DRIVE", "COMPOSIO_AUTH_ID_GOOGLE_DOCS",
    "COMPOSIO_AUTH_ID_GOOGLE_TASKS", "COMPOSIO_AUTH_ID_LINKEDIN",
    "COMPOSIO_AUTH_ID_INSTAGRAM",
]


def _client(tenant="t1"):
    app = FastAPI()
    app.include_router(oauth_api.router)
    if tenant is not None:
        app.dependency_overrides[oauth_api.require_tenant] = lambda: tenant
    return TestClient(app)


def _only(monkeypatch, **envs):
    for k in _AUTH_ENVS:
        monkeypatch.delenv(k, raising=False)
    for k, v in envs.items():
        monkeypatch.setenv(k, v)


def _sup_owned_by(owner_tenant):
    """Supabase mock whose ownership SELECT returns a row for owner_tenant (or none)."""
    sup = MagicMock()
    row = MagicMock()
    row.data = [{"tenant_id": owner_tenant}] if owner_tenant else []
    sup.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = row
    return sup


def test_toolkits_lists_only_configured(monkeypatch):
    _only(monkeypatch, COMPOSIO_AUTH_ID_GOOGLE_SHEETS="ac_1", COMPOSIO_AUTH_ID_LINKEDIN="ac_2")
    r = _client().get("/connectors/toolkits")
    assert r.status_code == 200
    assert set(r.json()["toolkits"]) == {"googlesheets", "linkedin"}


def test_initiate_uses_session_tenant_and_persists(monkeypatch):
    _only(monkeypatch, COMPOSIO_AUTH_ID_GOOGLE_SHEETS="ac_sheets")
    fake_conn = MagicMock()
    fake_conn.initiate_connection.return_value = {
        "connection_id": "ca_1", "redirect_url": "https://accounts.google.com/o", "status": "INITIATED"}
    sup = MagicMock()
    with patch.object(oauth_api, "ComposioConnector", return_value=fake_conn), \
         patch.object(oauth_api, "_supabase", return_value=sup):
        r = _client(tenant="tenant-from-session").post(
            "/connectors/initiate", json={"toolkit": "googlesheets"})  # NOTE: no tenant_id in body
    assert r.status_code == 200
    assert r.json() == {"redirect_url": "https://accounts.google.com/o", "connection_id": "ca_1"}
    # tenant used is the SESSION tenant, not anything client-supplied
    fake_conn.initiate_connection.assert_called_once()
    assert fake_conn.initiate_connection.call_args.args[0] == "tenant-from-session"
    persisted = sup.table.return_value.upsert.call_args.args[0]
    assert persisted["tenant_id"] == "tenant-from-session"


def test_initiate_fails_closed_without_auth_override(monkeypatch):
    """If the app never wires verify_session, require_tenant raises and the request
    is refused — it never falls back to trusting client input."""
    _only(monkeypatch, COMPOSIO_AUTH_ID_GOOGLE_SHEETS="ac_sheets")
    with pytest.raises(RuntimeError, match="require_tenant is not configured"):
        _client(tenant=None).post("/connectors/initiate", json={"toolkit": "googlesheets"})


def test_initiate_unknown_toolkit_is_400(monkeypatch):
    _only(monkeypatch)
    r = _client().post("/connectors/initiate", json={"toolkit": "does_not_exist"})
    assert r.status_code == 400


def test_initiate_composio_error_is_502(monkeypatch):
    _only(monkeypatch, COMPOSIO_AUTH_ID_GOOGLE_SHEETS="ac_sheets")
    fake_conn = MagicMock()
    fake_conn.initiate_connection.return_value = {"error": "composio down"}
    with patch.object(oauth_api, "ComposioConnector", return_value=fake_conn), \
         patch.object(oauth_api, "_supabase", return_value=MagicMock()):
        r = _client().post("/connectors/initiate", json={"toolkit": "googlesheets"})
    assert r.status_code == 502


def test_status_returns_state_for_owned_connection():
    fake_conn = MagicMock()
    fake_conn.connection_status.return_value = "ACTIVE"
    with patch.object(oauth_api, "ComposioConnector", return_value=fake_conn), \
         patch.object(oauth_api, "_supabase", return_value=_sup_owned_by("t1")):
        r = _client(tenant="t1").get("/connectors/status/ca_1")
    assert r.status_code == 200
    assert r.json() == {"connection_id": "ca_1", "status": "ACTIVE"}


def test_status_foreign_connection_is_404():
    """A tenant cannot poll a connection owned by someone else."""
    fake_conn = MagicMock()
    with patch.object(oauth_api, "ComposioConnector", return_value=fake_conn), \
         patch.object(oauth_api, "_supabase", return_value=_sup_owned_by("someone-else")):
        r = _client(tenant="t1").get("/connectors/status/ca_1")
    assert r.status_code == 404
    fake_conn.connection_status.assert_not_called()  # never queried Composio for a foreign id
