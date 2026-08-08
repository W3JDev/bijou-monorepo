"""
Pytest Configuration & Fixtures
=================================

Global test configuration and shared fixtures for Bijou AI test suite.

Fixtures provided:
- mock_bridge: Mock WhatsApp bridge
- mock_supabase: Mock Supabase client
- test_tenant: Synthetic test tenant
- test_client: FastAPI test client

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Date: 2026-02-07
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Enable pytest-asyncio plugin
pytest_plugins = ("pytest_asyncio",)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import test fixtures and mocks
from tests.fixtures.test_tenants import get_test_tenants
from tests.mocks.whatsapp_mock import MockWhatsAppBridge, create_mock_bridge

# ════════════════════════════════════════════════════════════════
# ENVIRONMENT SETUP
# ════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the test session.

    This fixture is required for pytest-asyncio to work properly.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables"""
    os.environ["TESTING"] = "true"
    os.environ["DB_TYPE"] = "mock"
    os.environ["SUPABASE_URL"] = "https://mock-supabase.test"
    os.environ["SUPABASE_SERVICE_KEY"] = "mock-service-key-for-testing"
    os.environ["GEMINI_API_KEY"] = "mock-gemini-api-key"
    os.environ["OPENAI_API_KEY"] = "mock-openai-api-key"
    os.environ["WEBHOOK_MODE"] = "true"
    os.environ["ENABLE_MULTI_TENANT"] = "true"
    os.environ["BRIDGE_URL"] = "http://mock-bridge:8080"


# ════════════════════════════════════════════════════════════════
# MOCK FIXTURES
# ════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_bridge() -> MockWhatsAppBridge:
    """
    Mock WhatsApp bridge for testing.

    Returns a fresh mock bridge instance for each test.
    """
    bridge = create_mock_bridge()
    yield bridge
    bridge.reset()


@pytest.fixture
def mock_supabase():
    """
    Mock Supabase client for database operations.

    Returns a MagicMock that simulates Supabase API.
    """
    mock = MagicMock()
    table_mocks = {}

    # Mock table query builder pattern
    def create_table_mock(table_name: str):
        table_mock = MagicMock()
        table_mock.select = MagicMock(return_value=table_mock)
        table_mock.insert = MagicMock(return_value=table_mock)
        table_mock.update = MagicMock(return_value=table_mock)
        table_mock.delete = MagicMock(return_value=table_mock)
        table_mock.eq = MagicMock(return_value=table_mock)
        table_mock.neq = MagicMock(return_value=table_mock)
        table_mock.order = MagicMock(return_value=table_mock)
        table_mock.limit = MagicMock(return_value=table_mock)

        # Mock execute() to return empty data by default
        execute_result = MagicMock()
        execute_result.data = []
        execute_result.count = 0
        table_mock.execute = MagicMock(return_value=execute_result)

        return table_mock

    def get_table_mock(table_name: str):
        if table_name not in table_mocks:
            table_mocks[table_name] = create_table_mock(table_name)
        return table_mocks[table_name]

    mock.table = MagicMock(side_effect=get_table_mock)

    return mock


@pytest.fixture
def mock_supabase_with_tenant(mock_supabase, test_tenants):
    """
    Mock Supabase with test tenants pre-populated.

    Use this fixture when tests need tenant data to exist in the database.
    Returns the first test tenant (Harmoni Residence - Property).
    """
    # Configure mock to return test tenants
    tenant = test_tenants[0]  # Use first tenant (Property)

    # Mock tenant lookup
    execute_result = MagicMock()
    execute_result.data = [tenant]
    execute_result.count = 1

    mock_supabase.table("tenants").select().eq().execute.return_value = execute_result

    return mock_supabase


# ════════════════════════════════════════════════════════════════
# TENANT FIXTURES
# ════════════════════════════════════════════════════════════════


@pytest.fixture
def test_tenants() -> list:
    """Get all 4 synthetic test tenants"""
    return get_test_tenants()


@pytest.fixture
def property_tenant(test_tenants) -> Dict:
    """Harmoni Residence (Property) tenant"""
    return test_tenants[0]


@pytest.fixture
def gaming_tenant(test_tenants) -> Dict:
    """GameHub Arena (Gaming) tenant"""
    return test_tenants[1]


@pytest.fixture
def dental_tenant(test_tenants) -> Dict:
    """SmileCare Dental (Healthcare) tenant"""
    return test_tenants[2]


@pytest.fixture
def fnb_tenant(test_tenants) -> Dict:
    """Bistro Delights (F&B) tenant"""
    return test_tenants[3]


# ════════════════════════════════════════════════════════════════
# APPLICATION FIXTURES
# ════════════════════════════════════════════════════════════════


@pytest.fixture
def test_app():
    """
    FastAPI test application.

    Returns TestClient for making HTTP requests to API.
    """
    # Import app here to avoid circular imports
    from src.core.bijou import app

    return app


@pytest.fixture
def test_client(test_app) -> TestClient:
    """
    FastAPI test client.

    Use this to make HTTP requests in tests:
    response = test_client.post("/api/endpoint", json={...})
    """
    return TestClient(test_app)


# ════════════════════════════════════════════════════════════════
# HELPER FIXTURES
# ════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_tenant_id() -> str:
    """Mock tenant UUID for testing"""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def mock_session_id() -> str:
    """Mock WhatsApp session ID"""
    return "test-session-12345"


@pytest.fixture
def mock_phone_number() -> str:
    """Mock test phone number"""
    return "+60100000001"


@pytest.fixture
def mock_whatsapp_jid(mock_phone_number) -> str:
    """Mock WhatsApp JID"""
    return f"{mock_phone_number.replace('+', '')}@s.whatsapp.net"


# ════════════════════════════════════════════════════════════════
# CLEANUP FIXTURES
# ════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def reset_test_state():
    """
    Reset test state after each test.

    Runs automatically for every test function.
    """
    yield
    # Cleanup code here if needed


# ════════════════════════════════════════════════════════════════
# PYTEST CONFIGURATION
# ════════════════════════════════════════════════════════════════


def pytest_configure(config):
    """
    Pytest configuration hook.

    Register custom markers for test organization.
    """
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (slower)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (slowest, full stack)")
    config.addinivalue_line("markers", "smoke: Smoke tests (critical paths only)")
    config.addinivalue_line("markers", "slow: Tests that take >5 seconds")


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection.

    Auto-mark tests based on file location.
    """
    for item in items:
        # Auto-mark E2E tests
        if "test_e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)

        # Auto-mark integration tests
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Auto-mark unit tests
        if "test_unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
