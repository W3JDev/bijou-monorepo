"""
Bijou AI - Comprehensive Dashboard E2E Test Suite
==================================================

Test all critical dashboard flows to prevent regressions.

Author: QA Engineer
Created: 2026-02-14
Issue: Dashboard broken for 24 hours - prevent future regressions

Usage:
    pytest tests/e2e/test_dashboard_complete.py -v
    pytest tests/e2e/test_dashboard_complete.py -v -m smoke
    pytest tests/e2e/test_dashboard_complete.py -v -k phone_number

Test Coverage:
    1. Phone Number Tests - Verify real phone numbers (not device IDs)
    2. Analytics Tests - Stats endpoint returns valid metrics
    3. Escalations Tests - All statuses visible
    4. WhatsApp Tests - QR endpoint accessible
    5. Integration Tests - Full flow works
    6. Regression Tests - Security fixes active
"""

import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pytest
from httpx import AsyncClient

# Test configuration
#
# The default used to be https://bijou-staging.fly.dev. That host no longer
# resolves, so every test in this file died in DNS lookup without exercising a
# single line of the product. The default is now the local stack from
# docker-compose.local.yml — backend on :8080, the Supabase gateway (GoTrue +
# PostgREST) on :9321, Mailpit on :8025 — which runs the real production
# schema. Point TEST_API_URL at a deployed environment to run the same suite
# against it.
STAGING_API = os.getenv("TEST_API_URL", "http://localhost:8080")
MAILPIT_API = os.getenv("TEST_MAILPIT_URL", "http://localhost:8025")
SUPABASE_REST_URL = os.getenv("TEST_SUPABASE_URL", "http://localhost:9321")
TIMEOUT = 30  # seconds

REPO_ROOT = Path(__file__).resolve().parents[4]
LOCAL_ENV_FILE = REPO_ROOT / "ops" / "local" / ".env.local"

# Password used for the throwaway account these tests sign up with. Must satisfy
# GoTrue's minimum length; nothing else about it matters.
E2E_PASSWORD = "E2eDashPass!2026"


# ==================== LIVE STACK HELPERS ====================


def _stack_is_up(base_url: str) -> bool:
    """True when the backend answers /health."""
    try:
        return httpx.get(f"{base_url}/health", timeout=5.0).status_code == 200
    except httpx.HTTPError:
        return False


def _service_role_key() -> Optional[str]:
    """Service-role key for the Supabase stack under test.

    The local key is minted by ops/local/gen-local-keys.sh into
    ops/local/.env.local and nowhere else: PostgREST validates it against the
    local JWT secret, so a placeholder string will not do. An explicit env var
    wins so the same suite can be pointed at another stack.
    """
    key = os.getenv("TEST_SUPABASE_SERVICE_KEY")
    if key:
        return key

    if not LOCAL_ENV_FILE.exists():
        return None

    from dotenv import dotenv_values

    values = dotenv_values(LOCAL_ENV_FILE)
    return (
        values.get("SUPABASE_SERVICE_KEY")
        or values.get("SUPABASE_SERVICE_ROLE_KEY")
        or values.get("SUPABASE_KEY")
    )


def _confirmation_link(client: httpx.Client, email: str) -> Optional[str]:
    """Pull the GoTrue confirmation link for `email` out of Mailpit.

    Taken verbatim from the message body — GoTrue builds the link from the
    ORIGIN of API_EXTERNAL_URL and drops the path, so rewriting it by hand is
    how a previous fix looked green while still being broken.
    """
    for _ in range(30):
        listing = client.get(f"{MAILPIT_API}/api/v1/messages?limit=50")
        for summary in listing.json().get("messages", []):
            recipients = [t.get("Address", "") for t in (summary.get("To") or [])]
            if email not in recipients:
                continue
            body = client.get(f"{MAILPIT_API}/api/v1/message/{summary['ID']}").json()
            text = (body.get("Text") or "") + (body.get("HTML") or "")
            match = re.search(r'https?://[^\s"\'<>]*verify[^\s"\'<>]*', text)
            if match:
                return match.group(0).replace("&amp;", "&")
        time.sleep(1)
    return None


def _provision_login(base_url: str) -> Dict[str, str]:
    """Sign up, confirm the email and log in — the real browser flow.

    verify_session (src/core/dashboard_api_simple.py:298) resolves the tenant
    from a Supabase JWT via the tenant_users table, so the synthetic
    "Bearer test-token-<uuid>" this file used to send was never authenticated:
    every request came back 400/401 and every body assertion was skipped. Only
    a session minted by the running stack is real.
    """
    email = f"e2e-dashboard-{uuid.uuid4().hex[:10]}@bijou-e2e.example.com"

    with httpx.Client(timeout=60.0, follow_redirects=False) as client:
        signup = client.post(
            f"{base_url}/api/auth/signup",
            json={
                "email": email,
                "password": E2E_PASSWORD,
                "business_name": "E2E Dashboard Suite",
                "phone": "+60123456789",
            },
        )
        if signup.status_code != 200:
            pytest.skip(f"Could not provision E2E account: {signup.status_code} {signup.text}")

        link = _confirmation_link(client, email)
        if not link:
            pytest.skip("No confirmation email arrived in Mailpit")
        client.get(link)

        login = client.post(
            f"{base_url}/api/auth/login",
            json={"email": email, "password": E2E_PASSWORD},
        )
        if login.status_code != 200:
            pytest.skip(f"Could not log in as E2E account: {login.status_code} {login.text}")

        payload = login.json()
        return {
            "email": email,
            "access_token": payload["access_token"],
            "tenant_id": payload["tenant_id"],
            "user_id": payload["user"]["id"],
        }


# ==================== FIXTURES ====================


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Base URL for API tests. Skips the suite when nothing is listening."""
    if not _stack_is_up(STAGING_API):
        pytest.skip(f"No API reachable at {STAGING_API} (set TEST_API_URL)")
    return STAGING_API


@pytest.fixture(scope="session")
def service_supabase(api_base_url: str):
    """Service-role Supabase client for seeding and cleaning test rows.

    RLS drops every permissive policy in this schema (ops/_fix_rls_v6.js), so
    the service role is the only role that can write here.
    """
    key = _service_role_key()
    if not key:
        pytest.skip(f"No Supabase service-role key (looked in {LOCAL_ENV_FILE})")

    from supabase import create_client

    return create_client(SUPABASE_REST_URL, key)


@pytest.fixture(scope="session")
def live_dashboard_login(api_base_url: str, service_supabase) -> Dict[str, str]:
    """A real, confirmed account + tenant for the whole module.

    Torn down afterwards so repeated runs do not accumulate tenants in the
    shared local stack.
    """
    session = _provision_login(api_base_url)
    yield session

    tenant_id = session["tenant_id"]
    for table in ("messages", "conversations", "escalations", "tenant_users"):
        try:
            service_supabase.table(table).delete().eq("tenant_id", tenant_id).execute()
        except Exception as cleanup_err:  # cleanup must never fail a green run
            print(f"WARN: could not clean {table} for {tenant_id}: {cleanup_err}")
    try:
        service_supabase.table("tenants").delete().eq("id", tenant_id).execute()
        service_supabase.auth.admin.delete_user(session["user_id"])
    except Exception as cleanup_err:
        print(f"WARN: could not remove E2E tenant {tenant_id}: {cleanup_err}")


@pytest.fixture(scope="session")
def test_tenant_id(live_dashboard_login: Dict[str, str]) -> str:
    """Tenant the E2E account owns. Overrides the conftest placeholder."""
    return live_dashboard_login["tenant_id"]


@pytest.fixture
def auth_headers(live_dashboard_login: Dict[str, str]) -> Dict[str, str]:
    """Authorization headers for dashboard API — a genuine Supabase session."""
    return {
        "Authorization": f"Bearer {live_dashboard_login['access_token']}",
        "X-Tenant-ID": live_dashboard_login["tenant_id"],
    }


@pytest.fixture(scope="session", autouse=True)
def seeded_dashboard_data(live_dashboard_login: Dict[str, str], service_supabase):
    """Give the E2E tenant enough data that the body assertions actually run.

    A brand-new tenant returns [] everywhere, which makes every "if
    conversations:" block in this file a no-op — the tests would pass without
    checking anything. Seeded here rather than per test because the assertions
    are all read-only.
    """
    tenant_id = live_dashboard_login["tenant_id"]
    chat_jid = "60123456789@s.whatsapp.net"

    conversations = service_supabase.table("conversations").insert([
        {
            "tenant_id": tenant_id,
            "chat_jid": chat_jid,
            "message_content": "Hi, do you deliver to Penang?",
            "ai_response": "Yes boss, we deliver to Penang!",
            "contact_name": "+60 12 345 6789",
        },
    ]).execute()

    messages = service_supabase.table("messages").insert([
        {"tenant_id": tenant_id, "chat_jid": chat_jid, "role": "user",
         "content": "Hi, do you deliver to Penang?"},
        {"tenant_id": tenant_id, "chat_jid": chat_jid, "role": "assistant",
         "content": "Yes boss, we deliver to Penang!"},
    ]).execute()

    # One escalation per status, so "all statuses visible" and the status
    # filter are both tested against data that could actually break them.
    escalations = service_supabase.table("escalations").insert([
        {"tenant_id": tenant_id, "chat_jid": chat_jid,
         "reason": "Customer asked for a human", "priority": "urgent", "status": "pending"},
        {"tenant_id": tenant_id, "chat_jid": chat_jid,
         "reason": "Agent working on it", "priority": "high", "status": "in_progress"},
        {"tenant_id": tenant_id, "chat_jid": chat_jid,
         "reason": "Already handled", "priority": "normal", "status": "resolved"},
    ]).execute()

    yield {
        "chat_jid": chat_jid,
        "conversation_ids": [row["id"] for row in conversations.data],
        "message_ids": [row["id"] for row in messages.data],
        "escalation_ids": [row["id"] for row in escalations.data],
    }

    for table, rows in (
        ("conversations", conversations.data),
        ("messages", messages.data),
        ("escalations", escalations.data),
    ):
        for row in rows:
            try:
                service_supabase.table(table).delete().eq("id", row["id"]).execute()
            except Exception as cleanup_err:
                print(f"WARN: could not delete {table} row {row['id']}: {cleanup_err}")


@pytest.fixture
async def http_client(api_base_url: str) -> AsyncClient:
    """Async HTTP client for testing"""
    async with AsyncClient(base_url=api_base_url, timeout=TIMEOUT) as client:
        yield client


# ==================== PHONE NUMBER TESTS ====================


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_conversations_show_real_phone_numbers(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    CRITICAL: Verify conversations show real phone numbers, not device IDs.
    
    Bug: Dashboard was showing @lid:XXXXX instead of +60 phone numbers.
    Fix: Pre-processing filters out lid markers before storage.
    Regression: This test ensures phone numbers are ALWAYS displayed correctly.
    """
    # Act
    response = await http_client.get(
        "/api/dashboard/conversations",
        headers=auth_headers,
    )
    
    # Assert
    assert response.status_code in [200, 401], \
        f"Conversations endpoint should be accessible (got {response.status_code})"
    
    if response.status_code == 200:
        data = response.json()
        # API returns direct list, not wrapped in object
        conversations = data if isinstance(data, list) else data.get("conversations", [])
        
        # If we have conversations, verify phone number format
        if conversations:
            for conv in conversations[:5]:  # Check first 5
                chat_jid = conv.get("chat_jid", "")
                customer_name = conv.get("customer_name", "")
                
                # CRITICAL: No @lid markers should be present
                assert "@lid:" not in chat_jid, \
                    f"❌ Found @lid in chat_jid: {chat_jid} (device ID leak!)"
                assert "@lid:" not in customer_name, \
                    f"❌ Found @lid in customer_name: {customer_name} (device ID leak!)"
                
                # Verify phone number format (should be +XX or XXXXX@s.whatsapp.net)
                if chat_jid and "@" in chat_jid:
                    phone_part = chat_jid.split("@")[0]
                    assert phone_part.startswith("+") or phone_part.isdigit(), \
                        f"❌ Invalid phone format in chat_jid: {chat_jid}"
                
                print(f"OK: Valid phone number: {chat_jid}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_phone_numbers_in_correct_format(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    Verify phone numbers are formatted correctly for display.
    
    Expected format: +60 12-345 6789 (Malaysia)
                    +XX XXXXXXXXXX (Other countries)
    """
    # Act
    response = await http_client.get(
        "/api/dashboard/conversations",
        headers=auth_headers,
    )
    
    # Assert
    if response.status_code == 200:
        data = response.json()
        # API returns direct list, not wrapped in object
        conversations = data if isinstance(data, list) else data.get("conversations", [])
        
        # Regex for valid international phone format
        phone_pattern = re.compile(r'^\+\d{1,3}[\s\d-]+$')
        
        if conversations:
            for conv in conversations[:5]:
                display_phone = conv.get("customer_name", "")
                
                # Skip if it's a name (not a phone number)
                if not display_phone.startswith("+"):
                    continue
                
                # Verify format
                assert phone_pattern.match(display_phone), \
                    f"❌ Invalid phone format: {display_phone}"
                
                print(f"OK: Correctly formatted: {display_phone}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_no_device_ids_in_messages(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    REGRESSION TEST: Ensure device IDs never appear in message history.
    
    Bug: @lid:XXXXX was appearing in conversation history.
    Impact: Breaks UX, confuses users.
    Fix: Pre-filter all incoming JIDs before storage.
    """
    # Act
    response = await http_client.get(
        "/api/dashboard/conversations",
        headers=auth_headers,
    )
    
    # Assert
    if response.status_code == 200:
        data = response.json()
        # API returns direct list, not wrapped in object
        conversations = data if isinstance(data, list) else data.get("conversations", [])
        
        if conversations:
            # Get messages for first conversation
            first_conv = conversations[0]
            customer_jid = first_conv.get("chat_jid", "")
            
            messages_response = await http_client.get(
                f"/api/dashboard/messages/{customer_jid}",
                headers=auth_headers,
            )
            
            if messages_response.status_code == 200:
                messages_data = messages_response.json()
                # /api/dashboard/messages/{chat_jid} returns a bare JSON array
                # (dashboard_api_simple.py:2568). The old .get("messages") call
                # raised AttributeError on that list.
                messages = (
                    messages_data
                    if isinstance(messages_data, list)
                    else messages_data.get("messages", [])
                )

                # Verify NO @lid in any message field
                for msg in messages:
                    msg_str = str(msg)
                    assert "@lid:" not in msg_str, \
                        f"❌ Device ID leaked in message: {msg}"
                
                print(f"OK: Checked {len(messages)} messages - no device IDs found")


# ==================== ANALYTICS TESTS ====================


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_stats_endpoint_returns_valid_metrics(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    Verify stats endpoint returns non-zero, reasonable metrics.
    
    Expected fields:
        - total_conversations (int >= 0)
        - messages_today (int >= 0)
        - avg_response_time (float >= 0)
        - active_escalations (int >= 0)
    """
    # Act
    response = await http_client.get(
        "/api/dashboard/stats",
        headers=auth_headers,
    )
    
    # Assert
    assert response.status_code in [200, 401], \
        f"Stats endpoint should be accessible (got {response.status_code})"
    
    if response.status_code == 200:
        data = response.json()
        
        # Required fields (matching ACTUAL API response)
        required_fields = [
            "active_conversations",  # Not total_conversations
            "ai_handled",
            "human_handled",
            "leads_generated_today",
        ]
        
        for field in required_fields:
            assert field in data, f"❌ Missing required field: {field}"
            value = data[field]
            
            # Verify type and reasonable value - all should be integers
            assert isinstance(value, int), \
                f"❌ {field} should be int (got {type(value)})"
            assert value >= 0, f"❌ {field} cannot be negative"
            assert value < 1_000_000, f"❌ {field} unreasonably large"
            
            print(f"OK: {field}: {value}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analytics_data_consistency(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    Verify analytics data is internally consistent.
    
    Example: If total_conversations > 0, should have messages_today >= 0
    """
    # Act
    response = await http_client.get(
        "/api/dashboard/stats",
        headers=auth_headers,
    )
    
    # Assert
    if response.status_code == 200:
        data = response.json()
        
        active_conv = data.get("active_conversations", 0)
        ai_handled = data.get("ai_handled", 0)
        human_handled = data.get("human_handled", 0)
        
        # Consistency checks
        if active_conv > 0:
            print(f"OK: Has {active_conv} active conversations")
        
        # Total handled should not wildly exceed active conversations
        total_handled = ai_handled + human_handled
        if total_handled > active_conv * 10:
            pytest.fail(
                f"❌ Inconsistent: {total_handled} handled but only {active_conv} active conversations"
            )
        
        print("OK: Analytics data is internally consistent")


# ==================== ESCALATIONS TESTS ====================


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_escalations_returns_all_statuses(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    CRITICAL: Verify escalations endpoint returns ALL statuses.
    
    Bug: Was only showing 'pending' escalations.
    Fix: Removed status filter, now shows all.
    Regression: Ensure ALL statuses visible (pending, in_progress, resolved).
    """
    # Act - Get all escalations (no status filter)
    response = await http_client.get(
        "/api/dashboard/escalations",
        headers=auth_headers,
    )
    
    # Assert
    assert response.status_code in [200, 401], \
        f"Escalations endpoint should be accessible (got {response.status_code})"
    
    if response.status_code == 200:
        data = response.json()
        # API returns direct list, not wrapped in object
        escalations = data if isinstance(data, list) else data.get("escalations", [])
        
        if escalations:
            # Collect all unique statuses
            statuses = set(esc.get("status") for esc in escalations)
            
            print(f"OK: Found escalations with statuses: {statuses}")
            
            # Should have at least one status
            assert len(statuses) > 0, "❌ No escalation statuses found"
            
            # Verify valid statuses
            valid_statuses = {"pending", "in_progress", "resolved", "cancelled"}
            for status in statuses:
                assert status in valid_statuses, \
                    f"❌ Invalid escalation status: {status}"
        else:
            print("WARN:  No escalations found (may be expected for test tenant)")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_escalations_status_filter_works(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    Verify status filter works when explicitly provided.
    """
    # Test each status
    for status in ["pending", "in_progress", "resolved"]:
        # Act
        response = await http_client.get(
            f"/api/dashboard/escalations?status={status}",
            headers=auth_headers,
        )
        
        # Assert
        if response.status_code == 200:
            data = response.json()
            # API returns direct list, not wrapped in object
            escalations = data if isinstance(data, list) else data.get("escalations", [])
            
            # If escalations exist, verify they match the filter
            for esc in escalations:
                assert esc.get("status") == status, \
                    f"❌ Filter failed: expected {status}, got {esc.get('status')}"
            
            print(f"OK: Status filter '{status}' works ({len(escalations)} results)")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_escalations_data_structure(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    Verify escalations have proper data structure.
    
    Required fields:
        - id (UUID)
        - tenant_id (UUID)
        - chat_jid (phone number)
        - status (pending/in_progress/resolved)
        - priority (low/normal/high/urgent)
        - created_at (ISO timestamp)
    """
    # Act
    response = await http_client.get(
        "/api/dashboard/escalations",
        headers=auth_headers,
    )
    
    # Assert
    if response.status_code == 200:
        data = response.json()
        # API returns direct list, not wrapped in object
        escalations = data if isinstance(data, list) else data.get("escalations", [])
        
        if escalations:
            first_esc = escalations[0]
            
            # Required fields
            required_fields = ["id", "tenant_id", "chat_jid", "status", "priority"]
            
            for field in required_fields:
                assert field in first_esc, f"❌ Missing required field: {field}"
            
            # Verify UUID format for id
            esc_id = first_esc.get("id", "")
            uuid_pattern = re.compile(
                r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            )
            assert uuid_pattern.match(esc_id), f"❌ Invalid UUID format: {esc_id}"
            
            # Verify NO @lid in chat_jid
            chat_jid = first_esc.get("chat_jid", "")
            assert "@lid:" not in chat_jid, \
                f"❌ Device ID in escalation chat_jid: {chat_jid}"
            
            print(f"OK: Escalation data structure valid")


# ==================== WHATSAPP TESTS ====================


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_whatsapp_qr_endpoint_accessible(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    Verify QR code endpoint is accessible (not 401).
    
    Should return either:
        - QR code data (if not connected)
        - Status "connected" (if already connected)
    """
    # Act
    response = await http_client.get(
        "/api/dashboard/whatsapp/qr",
        headers=auth_headers,
    )
    
    # Assert
    assert response.status_code in [200, 401, 404], \
        f"QR endpoint should be accessible (got {response.status_code})"
    
    if response.status_code == 200:
        data = response.json()
        
        # Should have either qr_code or status
        has_qr = "qr_code" in data
        has_status = "status" in data
        
        assert has_qr or has_status, \
            "❌ Response should contain qr_code or status"
        
        if has_qr:
            print(f"OK: QR code available (length: {len(data['qr_code'])})")
        else:
            print(f"OK: WhatsApp status: {data.get('status')}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_whatsapp_connection_status(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    Verify WhatsApp connection status endpoint.
    """
    # Act
    response = await http_client.get(
        "/api/dashboard/whatsapp/status",
        headers=auth_headers,
    )
    
    # Assert
    assert response.status_code in [200, 401, 404], \
        f"Status endpoint should be accessible (got {response.status_code})"
    
    if response.status_code == 200:
        data = response.json()
        
        # Should have status field
        assert "status" in data, "❌ Missing 'status' field"

        status = data.get("status")
        # The endpoint's real vocabulary, read off every return in
        # get_whatsapp_status (dashboard_api_simple.py:2009-2156). The old list
        # here ("connecting", "qr_needed") named two states the endpoint never
        # returns and omitted the two it returns most: "not_configured" for a
        # tenant with no device, "error" when the bridge is unreachable.
        valid_statuses = ["connected", "disconnected", "not_configured", "error"]

        assert status in valid_statuses, \
            f"❌ Invalid status: {status} (expected one of {valid_statuses})"

        # `connected` and `status` are two views of one fact and must agree,
        # or the dashboard shows a connected badge over a dead session.
        assert data.get("connected") is (status == "connected"), \
            f"❌ connected={data.get('connected')} contradicts status={status}"

        print(f"OK: WhatsApp status: {status}")


# ==================== INTEGRATION TESTS ====================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_flow_conversations_to_messages(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    Integration test: Full flow from conversations → messages → display.
    
    Flow:
        1. Get conversations list
        2. Get messages for first conversation
        3. Verify data consistency
        4. Verify no device IDs anywhere
    """
    # Step 1: Get conversations
    conv_response = await http_client.get(
        "/api/dashboard/conversations",
        headers=auth_headers,
    )
    
    assert conv_response.status_code in [200, 401], \
        "Conversations endpoint should be accessible"
    
    if conv_response.status_code != 200:
        pytest.skip("Cannot test without auth token")
    
    conv_data = conv_response.json()
    # API returns direct list, not wrapped in object
    conversations = conv_data if isinstance(conv_data, list) else conv_data.get("conversations", [])
    
    if not conversations:
        pytest.skip("No conversations found for test tenant")
    
    # Step 2: Get messages for first conversation
    first_conv = conversations[0]
    customer_jid = first_conv.get("chat_jid", "")
    
    assert customer_jid, "❌ chat_jid missing from conversation"
    assert "@lid:" not in customer_jid, "❌ Device ID in chat_jid"
    
    messages_response = await http_client.get(
        f"/api/dashboard/messages/{customer_jid}",
        headers=auth_headers,
    )
    
    assert messages_response.status_code in [200, 404], \
        "Messages endpoint should be accessible"
    
    if messages_response.status_code == 200:
        messages_data = messages_response.json()
        # Bare JSON array, same as above — see dashboard_api_simple.py:2568.
        messages = (
            messages_data
            if isinstance(messages_data, list)
            else messages_data.get("messages", [])
        )

        # Step 3: Verify data consistency
        assert isinstance(messages, list), "❌ Messages should be a list"
        
        if messages:
            # Step 4: Verify no device IDs
            for msg in messages:
                msg_str = str(msg)
                assert "@lid:" not in msg_str, \
                    f"❌ Device ID leaked in message: {msg}"
            
            print(f"OK: Full flow test passed: {len(conversations)} conversations, {len(messages)} messages")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tenant_isolation_still_works(
    http_client: AsyncClient,
    test_tenant_id: str,
):
    """
    SECURITY TEST: Verify tenant isolation is enforced.
    
    Should NOT be able to access data from other tenants.
    """
    # Act - Try to access with wrong tenant ID
    fake_tenant_id = "00000000-0000-0000-0000-000000000000"
    fake_headers = {
        "Authorization": f"Bearer test-token-{fake_tenant_id}",
        "X-Tenant-ID": fake_tenant_id,
    }
    
    response = await http_client.get(
        "/api/dashboard/conversations",
        headers=fake_headers,
    )
    
    # Assert - Should get auth error or empty results (NOT other tenant's data)
    assert response.status_code in [401, 403, 200], \
        "Should handle invalid tenant gracefully"
    
    if response.status_code == 200:
        data = response.json()
        # API returns direct list, not wrapped in object
        conversations = data if isinstance(data, list) else data.get("conversations", [])
        
        # If we get data, verify it doesn't belong to the test tenant
        for conv in conversations:
            tenant_id = conv.get("tenant_id", "")
            assert tenant_id != test_tenant_id, \
                f"❌ SECURITY BREACH: Got data from tenant {test_tenant_id} with fake auth!"
        
        print(f"OK: Tenant isolation enforced ({len(conversations)} results for fake tenant)")


# ==================== REGRESSION TESTS ====================


@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.asyncio
async def test_security_fixes_still_active(
    http_client: AsyncClient,
    test_tenant_id: str,
):
    """
    REGRESSION TEST: dashboard endpoints must never be publicly readable.

    The skip this test carried ("Dashboard API currently has NO AUTH") is out
    of date. verify_session fails closed under the default DASHBOARD_MODE
    ("strict"), and both shapes of an unauthenticated request are refused:

      - no credentials, no tenant  -> 400, no tenant is even resolved
        (dashboard_api_simple.py:369)
      - no credentials, real tenant id -> 401
        (dashboard_api_simple.py:417)

    400 is the weaker of the two codes for "not authenticated", but it is
    still a refusal — nothing crosses the boundary. Both responses are checked
    for a leaked conversation list as well as for the status code, so this
    cannot pass just because the code changed.
    """
    # Test 1: CORS headers
    response = await http_client.options(
        "/api/dashboard/conversations",
        headers={"Origin": "https://example.com"},
    )

    # Should have CORS headers or OPTIONS support
    print(f"OK: OPTIONS request handled (status: {response.status_code})")

    # Test 2: a stranger with no credentials at all
    response_no_auth = await http_client.get("/api/dashboard/conversations")

    if response_no_auth.status_code == 200:
        pytest.fail(
            "🚨 CRITICAL SECURITY ISSUE: Dashboard endpoint is PUBLIC! "
            "Expected 400/401/403 for unauthorized access, got 200. "
            "This allows ANYONE to access tenant data."
        )

    assert response_no_auth.status_code in [400, 401, 403], \
        f"❌ SECURITY: Endpoint accessible without auth (got {response_no_auth.status_code})"
    assert not isinstance(response_no_auth.json(), list), \
        "❌ SECURITY: unauthenticated request returned a conversation list"

    # Test 3: a stranger who knows a real tenant id — the case that matters,
    # because tenant ids travel in dashboard URLs.
    response_guessed_tenant = await http_client.get(
        "/api/dashboard/conversations",
        headers={"X-Tenant-ID": test_tenant_id},
    )

    assert response_guessed_tenant.status_code in [401, 403], \
        f"❌ SECURITY: a known tenant id was enough (got {response_guessed_tenant.status_code})"
    assert not isinstance(response_guessed_tenant.json(), list), \
        "❌ SECURITY: unauthenticated request returned a conversation list"

    print("OK: Auth requirement enforced")


@pytest.mark.e2e
@pytest.mark.regression
@pytest.mark.asyncio
async def test_no_data_leakage_between_tenants(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    REGRESSION TEST: Ensure no data leakage between tenants.
    
    This was a critical bug in v1.0 - must never regress.
    """
    # Get conversations
    response = await http_client.get(
        "/api/dashboard/conversations",
        headers=auth_headers,
    )
    
    if response.status_code == 200:
        data = response.json()
        # API returns direct list, not wrapped in object
        conversations = data if isinstance(data, list) else data.get("conversations", [])
        
        if conversations:
            # Verify ALL conversations have the correct tenant_id
            test_tenant = auth_headers.get("X-Tenant-ID")
            
            for conv in conversations:
                tenant_id = conv.get("tenant_id", "")
                
                # If tenant_id is present, it MUST match
                if tenant_id:
                    assert tenant_id == test_tenant, \
                        f"❌ DATA LEAK: Got conversation from tenant {tenant_id} instead of {test_tenant}"
            
            print(f"OK: No data leakage detected in {len(conversations)} conversations")


# ==================== SMOKE TEST SUITE ====================


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_health_check_all_endpoints(
    http_client: AsyncClient,
):
    """
    Smoke test: Verify all critical endpoints are responsive.
    
    This is the first test that should run on every deployment.
    """
    endpoints = [
        "/health",
        "/api/dashboard/conversations",
        "/api/dashboard/stats",
        "/api/dashboard/escalations",
        "/api/dashboard/whatsapp/status",
    ]
    
    results = []
    
    for endpoint in endpoints:
        try:
            response = await http_client.get(endpoint)
            status = response.status_code
            
            # Any response (even 401) means endpoint exists
            is_alive = status < 500
            results.append((endpoint, is_alive, status))
            
            print(f"{'OK:' if is_alive else 'FAIL:'} {endpoint}: {status}")
        except Exception as e:
            results.append((endpoint, False, str(e)))
            print(f"FAIL: {endpoint}: {e}")
    
    # All endpoints should be responsive
    failed = [r for r in results if not r[1]]
    
    assert len(failed) == 0, \
        f"❌ {len(failed)} endpoints failed: {failed}"
    
    print(f"\nOK: All {len(endpoints)} endpoints responsive")


# ==================== PERFORMANCE TESTS ====================


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_response_times_acceptable(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    Performance test: Verify API response times are acceptable.
    
    Targets:
        - /health: < 500ms
        - /conversations: < 2000ms
        - /stats: < 1000ms
    """
    import time
    
    endpoints = [
        ("/health", 500),
        ("/api/dashboard/conversations", 2000),
        ("/api/dashboard/stats", 1000),
    ]
    
    for endpoint, max_ms in endpoints:
        start = time.time()
        
        headers = {} if endpoint == "/health" else auth_headers
        response = await http_client.get(endpoint, headers=headers)
        
        duration_ms = (time.time() - start) * 1000
        
        # Skip if auth failed
        if response.status_code in [401, 403]:
            print(f"WARN:  {endpoint}: Skipped (auth required)")
            continue
        
        assert duration_ms < max_ms, \
            f"❌ {endpoint} too slow: {duration_ms:.0f}ms (max {max_ms}ms)"
        
        print(f"OK: {endpoint}: {duration_ms:.0f}ms (< {max_ms}ms)")
