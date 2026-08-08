"""
Minimal route debugging test
=============================

This test helps debug why routes return 404 in the full test suite.
"""

import pytest
from fastapi.testclient import TestClient


def test_app_loads():
    """Test 1: Can we import the app?"""
    from src.core.bijou import app

    assert app is not None
    print("\n✅ App imported successfully")


def test_routes_registered():
    """Test 2: Are routes actually registered?"""
    from src.core.bijou import app

    routes = [r.path for r in app.routes if hasattr(r, "path")]

    print(f"\n📋 Total routes registered: {len(routes)}")

    # Check for our specific routes
    knowledge_routes = [r for r in routes if "/api/knowledge" in r]
    settings_routes = [r for r in routes if "/api/settings" in r]

    print(f"\n📚 Knowledge routes: {knowledge_routes}")
    print(f"\n⚙️  Settings routes: {settings_routes}")

    assert "/api/knowledge/upload" in routes, "Knowledge upload route not found!"
    assert "/api/settings/testing-mode" in routes, (
        "Settings testing-mode route not found!"
    )


def test_knowledge_upload_simple():
    """Test 3: Can we hit the knowledge upload endpoint?"""
    from src.core.bijou import app

    client = TestClient(app)

    # Try without authentication first
    files = {"file": ("test.txt", b"Test content", "text/plain")}
    headers = {"X-Tenant-ID": "test-tenant-123"}

    response = client.post("/api/knowledge/upload", files=files, headers=headers)

    print(f"\n📤 POST /api/knowledge/upload")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")

    # Don't assert success yet - just see what happens
    assert response.status_code in [200, 404, 500], (
        f"Unexpected status: {response.status_code}"
    )


def test_settings_testing_mode_simple():
    """Test 4: Can we hit the settings testing-mode endpoint?"""
    from src.core.bijou import app

    client = TestClient(app)

    payload = {"testing_mode": True, "test_numbers": ["+60100000001"]}
    headers = {"X-Tenant-ID": "test-tenant-123"}

    response = client.put("/api/settings/testing-mode", json=payload, headers=headers)

    print(f"\n🧪 PUT /api/settings/testing-mode")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")

    # Don't assert success yet - just see what happens
    assert response.status_code in [200, 404, 500], (
        f"Unexpected status: {response.status_code}"
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
