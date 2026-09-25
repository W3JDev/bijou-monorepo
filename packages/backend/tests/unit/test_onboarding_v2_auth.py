"""Authentication for the /api/onboarding/v2/* routes.

The hole
--------
`src/saas/onboarding_complete.py` mounts eight routes that take a `{tenant_id}`
straight out of the URL path and then write through the **service-role**
Supabase client, which bypasses RLS. Verified during the 2026-09-06 audit:

    $ grep -c "verify_session\\|Depends" src/saas/onboarding_complete.py
    0

So anyone who could guess or obtain a tenant UUID could overwrite that tenant's
business details, re-provision its WhatsApp device, read its QR code (i.e. take
over the WhatsApp session), and insert into its knowledge base and handover
agents. The routes are mounted in `src/core/bijou.py:631` and live.

The credential
--------------
`tenants.signup_token`. It already exists, both signup paths issue it, the
browser is sitting on `/onboard/{token}` when it calls these routes, and
`src/saas/onboarding_api.py` resolves the same token to a tenant for
`/api/onboarding/status/{token}`. It is presented as a header — see
`require_signup_token`'s docstring for why a header and not the body.

`POST /signup` stays public: it is what creates the tenant, so there is nobody
to authenticate yet.
"""

import importlib
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


TENANT = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT = "22222222-2222-2222-2222-222222222222"
TOKEN = "signup-token-for-tenant-one-aaaaaaaaaaaa"
OTHER_TOKEN = "signup-token-for-tenant-two-bbbbbbbbbbbb"


# ── A Supabase stand-in ────────────────────────────────────────────────────
# Only the postgrest surface these routes actually use: table().select().eq()
# .limit().execute(), plus insert()/update() so the happy paths can run.


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, store, table):
        self._store = store
        self._table = table
        self._filters = []
        self._op = "select"
        self._payload = None

    def select(self, *_a, **_k):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def limit(self, _n):
        return self

    def _matches(self, row):
        return all(row.get(c) == v for c, v in self._filters)

    def execute(self):
        rows = self._store.setdefault(self._table, [])
        if self._op == "select":
            return _Result([r for r in rows if self._matches(r)])
        if self._op == "insert":
            row = dict(self._payload)
            row.setdefault("id", str(uuid.uuid4()))
            rows.append(row)
            return _Result([row])
        for row in rows:
            if self._matches(row):
                row.update(self._payload)
        return _Result([r for r in rows if self._matches(r)])


class FakeSupabase:
    def __init__(self, store):
        self._store = store

    def table(self, name):
        return _Query(self._store, name)


@pytest.fixture
def mod():
    return importlib.import_module("src.saas.onboarding_complete")


@pytest.fixture
def store():
    return {
        "tenants": [
            {"id": TENANT, "signup_token": TOKEN, "business_name": "Kedai Satu"},
            {"id": OTHER_TENANT, "signup_token": OTHER_TOKEN, "business_name": "Kedai Dua"},
        ],
        "onboarding_progress": [{"tenant_id": TENANT}],
        "whatsapp_devices": [],
    }


@pytest.fixture
def client(mod, store, monkeypatch):
    monkeypatch.setattr(mod, "get_supabase", lambda: FakeSupabase(store))
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app, raise_server_exceptions=False)


# Every mounted route that takes a tenant_id out of the path, as
# (method, path template, concrete path, request kwargs). The kwargs carry a
# body good enough to reach the handler if authentication ever let it through,
# so a 401/403 proves the rejection came from auth and not from validation.
PROTECTED = [
    ("POST", "/api/onboarding/v2/details/{tenant_id}",
     f"/api/onboarding/v2/details/{TENANT}", {"json": {"business_hours": {}}}),
    ("GET", "/api/onboarding/v2/whatsapp/qr/{tenant_id}",
     f"/api/onboarding/v2/whatsapp/qr/{TENANT}", {}),
    ("GET", "/api/onboarding/v2/whatsapp/qr-image/{tenant_id}/{qr_filename}",
     f"/api/onboarding/v2/whatsapp/qr-image/{TENANT}/abc.png", {}),
    ("POST", "/api/onboarding/v2/whatsapp/connected/{tenant_id}",
     f"/api/onboarding/v2/whatsapp/connected/{TENANT}", {}),
    ("POST", "/api/onboarding/v2/knowledge/upload/{tenant_id}",
     f"/api/onboarding/v2/knowledge/upload/{TENANT}",
     {"files": {"files": ("kb.txt", b"hello", "text/plain")}}),
    ("POST", "/api/onboarding/v2/agents/add/{tenant_id}",
     f"/api/onboarding/v2/agents/add/{TENANT}", {"json": {"agent_name": "Ali"}}),
    ("POST", "/api/onboarding/v2/complete/{tenant_id}",
     f"/api/onboarding/v2/complete/{TENANT}", {}),
    ("GET", "/api/onboarding/v2/status/{tenant_id}",
     f"/api/onboarding/v2/status/{TENANT}", {}),
]

_CASES = [(m, path, kw) for m, tmpl, path, kw in PROTECTED]
_IDS = [tmpl for _, tmpl, _, _ in PROTECTED]


@pytest.mark.parametrize("method,path,kw", _CASES, ids=_IDS)
def test_no_token_is_rejected(client, method, path, kw):
    """Absent credential must be 401, never a silent success."""
    assert client.request(method, path, **kw).status_code == 401


@pytest.mark.parametrize("method,path,kw", _CASES, ids=_IDS)
def test_wrong_token_is_rejected(client, method, path, kw):
    resp = client.request(method, path, headers={"X-Onboarding-Token": "nope"}, **kw)
    assert resp.status_code == 403


@pytest.mark.parametrize("method,path,kw", _CASES, ids=_IDS)
def test_another_tenants_token_is_rejected(client, method, path, kw):
    """The whole point: a valid token must not unlock a different tenant."""
    resp = client.request(method, path, headers={"X-Onboarding-Token": OTHER_TOKEN}, **kw)
    assert resp.status_code == 403


def test_every_tenant_id_route_is_covered(mod):
    """Guard against a new {tenant_id} route being added without auth."""
    mounted = {
        (m, r.path)
        for r in mod.router.routes
        for m in getattr(r, "methods", set()) or set()
        if "{tenant_id}" in getattr(r, "path", "")
    }
    listed = {(m, tmpl) for m, tmpl, _, _ in PROTECTED}
    assert mounted == listed


def test_correct_token_is_accepted(client, store):
    resp = client.post(
        f"/api/onboarding/v2/whatsapp/connected/{TENANT}",
        headers={"X-Onboarding-Token": TOKEN},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["next_step"] == "knowledge"
    tenant = next(r for r in store["tenants"] if r["id"] == TENANT)
    assert tenant["onboarding_step"] == "knowledge"


def test_bearer_header_is_accepted(client):
    resp = client.post(
        f"/api/onboarding/v2/whatsapp/connected/{TENANT}",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status_code == 200, resp.text


def test_unknown_tenant_does_not_leak_existence(client):
    """403, not 404 — otherwise the routes are a tenant-enumeration oracle."""
    ghost = "33333333-3333-3333-3333-333333333333"
    resp = client.post(
        f"/api/onboarding/v2/whatsapp/connected/{ghost}",
        headers={"X-Onboarding-Token": TOKEN},
    )
    assert resp.status_code == 403


def test_tenant_without_a_signup_token_cannot_be_unlocked(client, store):
    """A NULL/empty token must not be matchable by an empty presented value."""
    store["tenants"].append({"id": OTHER_TENANT + "x", "signup_token": None})
    resp = client.post(
        f"/api/onboarding/v2/whatsapp/connected/{OTHER_TENANT}x",
        headers={"X-Onboarding-Token": ""},
    )
    assert resp.status_code in (401, 403)


def test_comparison_is_constant_time(client, mod, monkeypatch):
    """`==` on a secret leaks its prefix through response timing."""
    calls = []
    real = mod.hmac.compare_digest

    def spy(a, b):
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(mod.hmac, "compare_digest", spy)
    client.post(
        f"/api/onboarding/v2/whatsapp/connected/{TENANT}",
        headers={"X-Onboarding-Token": TOKEN},
    )
    assert (TOKEN, TOKEN) in calls


def test_lookup_failure_fails_closed(client, mod, monkeypatch):
    """A database that cannot answer must not mean 'allowed'."""
    def boom():
        raise RuntimeError("postgrest unreachable")

    monkeypatch.setattr(mod, "get_supabase", boom)
    resp = client.post(
        f"/api/onboarding/v2/whatsapp/connected/{TENANT}",
        headers={"X-Onboarding-Token": TOKEN},
    )
    assert resp.status_code == 503


def test_signup_stays_public(client, store):
    """It creates the tenant; there is no credential to present yet."""
    resp = client.post(
        "/api/onboarding/v2/signup",
        json={
            "business_name": "Warung Baru",
            "email": "baru@example.com",
            "phone": "+60123456789",
            "plan": "free",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signup_token"]
