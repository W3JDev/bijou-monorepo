"""Tests for GET /api/proactive/status.

The endpoint returned a 500 to anyone who asked (it read a `_running`
attribute that ProactiveMessagingSystem does not have), and it did so
without any session check. These tests pin down the three answers it is
allowed to give: 401/403 unauthenticated, 503 when the scheduler is not
wired up, 200 with the real scheduler state otherwise.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.core.dashboard_api_simple import verify_session
from src.core.proactive_api import router
from src.core.proactive_messaging import ProactiveMessagingSystem


TENANT_ID = "607690ec-4ff7-4ef4-b98e-bfb00442fe95"


def _make_client(bijou=None, authenticated=True) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.bijou = bijou

    if authenticated:
        app.dependency_overrides[verify_session] = lambda: TENANT_ID
    else:
        def _reject():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[verify_session] = _reject

    # raise_server_exceptions=False so an unhandled exception surfaces as the
    # 500 a real client would see, instead of blowing up the test.
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def real_system() -> ProactiveMessagingSystem:
    """The real class, not a MagicMock — a mock would happily answer to any
    attribute name and hide exactly the bug this file exists for."""
    return ProactiveMessagingSystem(db_connection=MagicMock(), channel_adapter=MagicMock())


def test_status_requires_a_session(real_system):
    bijou = MagicMock()
    bijou.proactive_messaging = real_system

    resp = _make_client(bijou=bijou, authenticated=False).get("/api/proactive/status")

    assert resp.status_code in (401, 403), resp.text


def test_status_returns_scheduler_state_when_running(real_system):
    real_system.running = True
    bijou = MagicMock()
    bijou.proactive_messaging = real_system

    resp = _make_client(bijou=bijou).get("/api/proactive/status")

    assert resp.status_code == 200, resp.text
    assert resp.json()["system_active"] is True


def test_status_reports_stopped_scheduler(real_system):
    bijou = MagicMock()
    bijou.proactive_messaging = real_system

    resp = _make_client(bijou=bijou).get("/api/proactive/status")

    assert resp.status_code == 200, resp.text
    assert resp.json()["system_active"] is False


def test_status_is_503_when_proactive_messaging_is_absent():
    bijou = MagicMock()
    bijou.proactive_messaging = None

    resp = _make_client(bijou=bijou).get("/api/proactive/status")

    assert resp.status_code == 503, resp.text
    assert "proactive" in resp.json()["detail"].lower()


def test_status_is_503_when_bijou_is_absent():
    resp = _make_client(bijou=None).get("/api/proactive/status")

    assert resp.status_code == 503, resp.text
