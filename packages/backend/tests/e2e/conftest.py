"""
Bijou AI - E2E Test Fixtures
=============================

Shared test fixtures for end-to-end testing.

Author: @qa-engineer
"""

import os
import pytest
import httpx
from typing import Dict, Any, Optional
from supabase import Client, create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test Configuration
STAGING_URL = "https://bijou-staging.fly.dev"
TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"
TIMEOUT = 30.0


@pytest.fixture(scope="session")
def staging_url() -> str:
    """Get staging environment URL."""
    return os.getenv("STAGING_URL", STAGING_URL)


@pytest.fixture(scope="session")
def test_tenant_id() -> str:
    """Get test tenant ID."""
    return os.getenv("TEST_TENANT_ID", TEST_TENANT_ID)


@pytest.fixture(scope="session")
def supabase_client() -> Client:
    """
    Create Supabase client for E2E tests.
    
    Uses service role key for full database access (bypasses RLS).
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        pytest.skip("Missing Supabase credentials")
    
    return create_client(supabase_url, supabase_key)


@pytest.fixture
async def api_client(staging_url: str) -> httpx.AsyncClient:
    """
    Create async HTTP client for API testing.
    
    Usage:
        async def test_endpoint(api_client):
            response = await api_client.get("/health")
            assert response.status_code == 200
    """
    async with httpx.AsyncClient(
        base_url=staging_url,
        timeout=TIMEOUT,
        follow_redirects=True
    ) as client:
        yield client


@pytest.fixture
def api_headers(test_tenant_id: str) -> Dict[str, str]:
    """
    Get API headers with tenant isolation.
    
    Returns headers with X-Tenant-ID for multi-tenant requests.
    """
    return {
        "X-Tenant-ID": test_tenant_id,
        "Content-Type": "application/json"
    }


@pytest.fixture
async def test_conversation(supabase_client: Client, test_tenant_id: str) -> Dict[str, Any]:
    """
    Create a test conversation for testing.
    
    Automatically cleaned up after test completes.
    """
    # Create test conversation
    test_data = {
        "tenant_id": test_tenant_id,
        "chat_jid": "60100000001@s.whatsapp.net",
        "message_content": "Test message for E2E testing",
        "ai_response": "This is a test AI response",
        "detected_language": "english",
        "contact_name": "+60 10 000 0001"
    }
    
    response = supabase_client.table("conversations").insert(test_data).execute()
    
    if not response.data:
        pytest.fail("Failed to create test conversation")
    
    conversation = response.data[0]
    
    yield conversation
    
    # Cleanup: Delete test conversation
    try:
        supabase_client.table("conversations").delete().eq("id", conversation["id"]).execute()
    except Exception as e:
        print(f"Warning: Failed to cleanup test conversation: {e}")


@pytest.fixture
async def test_escalation(supabase_client: Client, test_tenant_id: str) -> Dict[str, Any]:
    """
    Create a test escalation for testing.
    
    Automatically cleaned up after test completes.
    """
    from datetime import datetime, timedelta
    
    # Create test escalation
    test_data = {
        "tenant_id": test_tenant_id,
        "chat_jid": "60100000002@s.whatsapp.net",
        "reason": "Test escalation for E2E testing",
        "priority": "normal",
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "sla_deadline": (datetime.now() + timedelta(hours=1)).isoformat()
    }
    
    response = supabase_client.table("escalations").insert(test_data).execute()
    
    if not response.data:
        pytest.fail("Failed to create test escalation")
    
    escalation = response.data[0]
    
    yield escalation
    
    # Cleanup: Delete test escalation
    try:
        supabase_client.table("escalations").delete().eq("id", escalation["id"]).execute()
    except Exception as e:
        print(f"Warning: Failed to cleanup test escalation: {e}")


@pytest.fixture
async def cleanup_test_data(supabase_client: Client, test_tenant_id: str):
    """
    Cleanup fixture that runs after all tests.
    
    Ensures test data doesn't pollute the database.
    """
    yield
    
    # Cleanup all test conversations for test tenant
    try:
        supabase_client.table("conversations").delete().eq("tenant_id", test_tenant_id).execute()
    except Exception as e:
        print(f"Warning: Failed to cleanup conversations: {e}")
    
    # Cleanup all test escalations for test tenant
    try:
        supabase_client.table("escalations").delete().eq("tenant_id", test_tenant_id).execute()
    except Exception as e:
        print(f"Warning: Failed to cleanup escalations: {e}")


@pytest.fixture
def test_customer_jid() -> str:
    """Get test customer WhatsApp JID."""
    return "60100000001@s.whatsapp.net"


@pytest.fixture
def second_tenant_id() -> str:
    """Get second tenant ID for cross-tenant isolation tests."""
    return "00000000-0000-0000-0000-000000000002"


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "p0: Priority 0 tests (deployment blocking)"
    )
    config.addinivalue_line(
        "markers", "p1: Priority 1 tests (should pass)"
    )
    config.addinivalue_line(
        "markers", "p2: Priority 2 tests (monitoring)"
    )
    config.addinivalue_line(
        "markers", "security: Security-related tests"
    )
    config.addinivalue_line(
        "markers", "whatsapp: WhatsApp integration tests"
    )
    config.addinivalue_line(
        "markers", "dashboard: Dashboard API tests"
    )
