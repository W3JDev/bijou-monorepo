"""
Tests for D-ONB-1: the onboarding business_type picker must actually configure
the agent's vertical.

POST /api/business/profile writes business_type into business_profiles, but
vertical_loader.get_tenant_vertical_prompt reads the SEPARATE tenant_verticals
table. business_profile_api now ALSO upserts the mapped vertical into
tenant_verticals so the onboard dropdown wires through.

Covers:
- a known business_type ("restaurant") upserts vertical_id="fnb"
- "realestate" maps to "property"
- an unknown business_type ("ecommerce") does NOT write an invalid vertical

Supabase is stubbed with unittest.mock; the session is supplied through
FastAPI's dependency_overrides (mirrors tests/unit/test_shared_context.py).
"""
from __future__ import annotations

from typing import Any, Dict, Tuple
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

TENANT_ID = "607690ec-4ff7-4ef4-b98e-bfb00442fe95"


@pytest.fixture
def app() -> FastAPI:
    from src.saas.business_profile_api import router
    from src.core.dashboard_api_simple import verify_session

    a = FastAPI()
    a.include_router(router)
    # verify_session is captured by Depends() at import; the override registry
    # is the only seam. Resolve it to our fixed tenant for the whole app.
    a.dependency_overrides[verify_session] = lambda: TENANT_ID
    return a


def _make_supabase(business_type: str) -> Tuple[MagicMock, Dict[str, Any]]:
    """Build a chainable Supabase stub with a distinct mock per table and
    capture what gets written to tenant_verticals."""
    captured: Dict[str, Any] = {"vertical_inserts": [], "vertical_deletes": 0}

    # tenants — used by verify_tenant() and the phone/name sync
    tenants_tbl = MagicMock()
    tenants_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": TENANT_ID}]
    )
    tenants_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{}]
    )

    # business_profiles — no existing row -> insert path
    profiles_tbl = MagicMock()
    profiles_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    profiles_tbl.insert.return_value.execute.return_value = MagicMock(
        data=[{
            "business_name": "Test Biz",
            "owner_name": "Ali",
            "business_type": business_type,
            "handover_contacts": [],
            "business_hours": None,
            "notes": f"business_type={business_type}",
            "created_at": None,
            "updated_at": None,
        }]
    )

    # tenant_verticals — capture delete/insert
    verticals_tbl = MagicMock()

    def _do_delete() -> MagicMock:
        chain = MagicMock()

        def _eq(_k: str, _v: str) -> MagicMock:
            captured["vertical_deletes"] += 1
            c2 = MagicMock()
            c2.execute.return_value = MagicMock(data=[])
            return c2

        chain.eq.side_effect = _eq
        return chain

    def _do_insert(row: Dict[str, Any]) -> MagicMock:
        captured["vertical_inserts"].append(row)
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[row])
        return chain

    verticals_tbl.delete.side_effect = _do_delete
    verticals_tbl.insert.side_effect = _do_insert

    tables = {
        "tenants": tenants_tbl,
        "business_profiles": profiles_tbl,
        "tenant_verticals": verticals_tbl,
    }
    sb = MagicMock()
    sb.table.side_effect = lambda name: tables[name]
    return sb, captured


def _post(app: FastAPI, sb: MagicMock, business_type: str):
    with patch("src.saas.business_profile_api.get_supabase", return_value=sb):
        client = TestClient(app)
        return client.post(
            "/api/business/profile",
            json={
                "tenant_id": TENANT_ID,
                "business_name": "Test Biz",
                "owner_name": "Ali",
                "business_type": business_type,
            },
        )


@pytest.mark.parametrize(
    "business_type, expected_vertical",
    [("restaurant", "fnb"), ("realestate", "property"), ("healthcare", "dental")],
)
def test_known_business_type_upserts_vertical(app, business_type, expected_vertical):
    sb, captured = _make_supabase(business_type)
    r = _post(app, sb, business_type)

    assert r.status_code == 200, r.text
    assert len(captured["vertical_inserts"]) == 1
    written = captured["vertical_inserts"][0]
    assert written["tenant_id"] == TENANT_ID
    assert written["vertical_id"] == expected_vertical
    assert written["enabled"] is True
    # Idempotent: prior mapping cleared before the insert.
    assert captured["vertical_deletes"] == 1


def test_unknown_business_type_writes_no_vertical(app):
    sb, captured = _make_supabase("ecommerce")
    r = _post(app, sb, "ecommerce")

    # The profile write still succeeds...
    assert r.status_code == 200, r.text
    # ...but no invalid vertical is written and nothing is deleted.
    assert captured["vertical_inserts"] == []
    assert captured["vertical_deletes"] == 0
