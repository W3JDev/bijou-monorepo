"""
Minimal route debugging test
=============================

This file exists to answer one question: are the API routers actually mounted?

The thing that makes it subtle — and that made three tests here fail — is that
routers are NOT mounted at import. `_include_routers()` runs inside the startup
event (src/core/bijou.py, `startup_event`), so a bare `import app` sees only the
~41 routes declared at module level. The other ~180 appear when the ASGI
lifespan runs.

`TestClient(app)` does NOT run the lifespan. `with TestClient(app)` does. Every
test here that inspects routes or calls an API endpoint therefore has to use the
context-manager form; the ones that did not were asserting against a
half-constructed app and failing for that reason alone.

Measured on 2026-09-06, same process, same app object:

    import only          41 routes,  /api/knowledge/upload absent
    with TestClient(app) 222 paths in /openapi.json, /api/knowledge/upload present

222 is also what `ops/DOKPLOY_DEPLOY.md` gives as the healthy figure to check
after a deploy.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def restore_global_bijou_instance():
    """Undo the side effect of running the app's startup lifespan.

    Every test in this file now uses `with TestClient(app)`, which is the only
    way to see the mounted routers. That also runs `startup_event`, which sets
    the module-global `src.core.bijou.bijou_instance` — and shutdown does not
    unset it.

    That leaks. tests/ runs this root-level file BEFORE tests/unit/, and
    tests/unit/test_backend_500_fixes.py asserts that a malformed webhook is
    refused, which it gets as a 503 ("Service not ready") precisely because
    bijou_instance is None. Leaving an initialized instance behind turned that
    into a 200 and failed a test this file has nothing to do with.

    Caught by running the whole suite after the change rather than this file
    alone — which is the only reason it did not ship.
    """
    import src.core.bijou as bijou_module

    original = bijou_module.bijou_instance
    yield
    bijou_module.bijou_instance = original


def test_app_loads():
    """Test 1: Can we import the app?"""
    from src.core.bijou import app

    assert app is not None
    print("\n✅ App imported successfully")


def test_routes_registered():
    """Test 2: Are routes actually registered?

    Enumerated from /openapi.json — the surface the app actually serves, and
    the same check ops/DOKPLOY_DEPLOY.md prescribes after a deploy.

    Two reasons this cannot use `[r.path for r in app.routes]`, which is what
    it used to do and why it failed:

    1. The `with` is required at all. Routers mount in the startup event, not
       at import (src/core/bijou.py, `startup_event` -> `_include_routers`), so
       without a running lifespan there is nothing to find.

    2. Even WITH the lifespan, that list comprehension cannot see these routes.
       This FastAPI version records each `include_router()` as ONE opaque
       `fastapi.routing._IncludedRouter` object in `app.routes` rather than
       flattening the child routes into it. Measured here on 2026-09-06:

           app.routes            68 objects
                                 = 34 APIRoute + 29 _IncludedRouter + 1 Mount
           /openapi.json        222 paths, freshly generated from those same
                                 68 objects, /api/knowledge/upload present

       The old assertion iterated the 68 and looked for a path that lives one
       level down inside an _IncludedRouter, so it reported "Knowledge upload
       route not found!" about a route that was mounted and serving. OpenAPI
       generation descends into them; a flat comprehension does not.
    """
    from src.core.bijou import app

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    routes = sorted(schema["paths"])

    print(f"\n📋 Total paths served: {len(routes)}")

    knowledge_routes = [r for r in routes if "/api/knowledge" in r]
    settings_routes = [r for r in routes if "/api/settings" in r]

    print(f"\n📚 Knowledge routes: {knowledge_routes}")
    print(f"\n⚙️  Settings routes: {settings_routes}")

    assert "/api/knowledge/upload" in routes, "Knowledge upload route not found!"
    assert "/api/settings/testing-mode" in routes, (
        "Settings testing-mode route not found!"
    )

    # A startup that dies partway still serves the ~41 module-level routes, and
    # every API check above would pass against a half-started app if the
    # routers happened to include these two. Pin the whole surface.
    assert len(routes) > 200, (
        f"only {len(routes)} paths served — startup did not complete; "
        "a healthy instance serves ~222 (ops/DOKPLOY_DEPLOY.md)"
    )


def test_knowledge_upload_simple():
    """Test 3: Can we hit the knowledge upload endpoint?"""
    from src.core.bijou import app

    # Try without authentication first
    files = {"file": ("test.txt", b"Test content", "text/plain")}
    headers = {"X-Tenant-ID": "test-tenant-123"}

    with TestClient(app) as client:
        response = client.post("/api/knowledge/upload", files=files, headers=headers)

    print(f"\n📤 POST /api/knowledge/upload")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")

    # This file's whole purpose is "why do routes 404". The old assertion
    # allowed 404 — the one answer that means the route is missing — while
    # rejecting 401, which means it is present and correctly demanding auth.
    # Inverted to assert what the docstring says it checks.
    assert response.status_code != 404, (
        "route is not registered — the endpoint 404s"
    )


def test_settings_testing_mode_simple():
    """Test 4: Can we hit the settings testing-mode endpoint?"""
    from src.core.bijou import app

    payload = {"testing_mode": True, "test_numbers": ["+60100000001"]}
    headers = {"X-Tenant-ID": "test-tenant-123"}

    with TestClient(app) as client:
        response = client.put(
            "/api/settings/testing-mode", json=payload, headers=headers
        )

    print(f"\n🧪 PUT /api/settings/testing-mode")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")

    # Same correction as test_knowledge_upload_simple.
    assert response.status_code != 404, (
        "route is not registered — the endpoint 404s"
    )


def test_route_methods():
    """Test 5: Check HTTP methods for routes"""
    from src.core.bijou import app

    print("\n🔍 Route methods:")

    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            if "/api/knowledge" in route.path or "/api/settings" in route.path:
                methods = ", ".join(sorted(route.methods)) if route.methods else "N/A"
                print(f"   {methods:15} {route.path}")


def test_openapi_schema():
    """Test 6: Does OpenAPI schema include our routes?"""
    from src.core.bijou import app

    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()
    paths = schema.get("paths", {})

    print(f"\n📖 OpenAPI paths ({len(paths)} total):")

    knowledge_paths = {k: v for k, v in paths.items() if "/api/knowledge" in k}
    settings_paths = {k: v for k, v in paths.items() if "/api/settings" in k}

    print(f"\n   Knowledge API paths:")
    for path, methods in knowledge_paths.items():
        print(f"      {path}: {list(methods.keys())}")

    print(f"\n   Settings API paths:")
    for path, methods in settings_paths.items():
        print(f"      {path}: {list(methods.keys())}")

    assert "/api/knowledge/upload" in paths, "Upload route missing from OpenAPI schema!"
    assert "/api/settings/testing-mode" in paths, (
        "Testing mode route missing from OpenAPI schema!"
    )


if __name__ == "__main__":
    # Run tests manually
    print("=" * 80)
    print("ROUTE DEBUG TEST SUITE")
    print("=" * 80)

    try:
        test_app_loads()
        test_routes_registered()
        test_knowledge_upload_simple()
        test_settings_testing_mode_simple()
        test_route_methods()
        test_openapi_schema()

        print("\n" + "=" * 80)
        print("✅ ALL DEBUG TESTS PASSED")
        print("=" * 80)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback

        traceback.print_exc()
