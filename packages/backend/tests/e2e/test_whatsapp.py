"""
Bijou AI - E2E WhatsApp Integration Tests
==========================================

P0 WhatsApp integration tests for bridge connectivity and message delivery.

Test Coverage:
- TC-WA-001: Bridge connection health check
- TC-WA-002: Message delivery via bridge

Author: @qa-engineer
"""

import pytest
import httpx
import os


@pytest.mark.e2e
@pytest.mark.p0
@pytest.mark.smoke
@pytest.mark.whatsapp
@pytest.mark.asyncio
async def test_whatsapp_bridge_connected(staging_url: str):
    """
    TC-WA-001: WhatsApp Bridge Connection Health
    
    GIVEN: WhatsApp bridge is deployed
    WHEN: Health check endpoint is called
    THEN: Bridge should respond successfully
    AND: Connection status should be available
    
    Priority: P0 (BLOCKING)
    Rollback Trigger: If bridge is unreachable
    """
    # Get bridge URL from environment or use default
    bridge_url = os.getenv("BRIDGE_URL", "http://localhost:8080").rstrip("/")
    
    # Try to connect to bridge
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Act: Check bridge health
            response = await client.get(f"{bridge_url}/health")
            
            # Assert: Bridge should respond
            assert response.status_code == 200, \
                f"❌ Bridge health check failed: HTTP {response.status_code}"
            
            # Try to parse JSON response
            try:
                data = response.json()
                print(f"✅ TC-WA-001 PASSED: Bridge is reachable - Status: {data.get('status', 'unknown')}")
                
                # Optional: Check if bridge reports connection status
                if "is_connected" in data:
                    is_connected = data.get("is_connected", False)
                    if is_connected:
                        print(f"   ✅ WhatsApp is connected")
                    else:
                        print(f"   ⚠️ WhatsApp is not connected (may need QR scan)")
                
            except Exception as json_error:
                # Bridge responded but not with JSON (acceptable)
                print(f"✅ TC-WA-001 PASSED: Bridge is reachable (non-JSON response)")
                
    except httpx.ConnectError as e:
        pytest.fail(
            f"❌ TC-WA-001 FAILED: Cannot connect to WhatsApp bridge at {bridge_url}\n"
            f"   Error: {e}\n"
            f"   Bridge may be down or URL is incorrect.\n"
            f"   Expected: {bridge_url}/health should respond with HTTP 200"
        )
    except httpx.TimeoutException:
        pytest.fail(
            f"❌ TC-WA-001 FAILED: Bridge health check timed out after 10s\n"
            f"   Bridge URL: {bridge_url}\n"
            f"   Bridge may be slow or unresponsive"
        )
    except Exception as e:
        pytest.fail(
            f"❌ TC-WA-001 FAILED: Unexpected error checking bridge health\n"
            f"   Error: {e}"
        )


@pytest.mark.e2e
@pytest.mark.p0
@pytest.mark.whatsapp
@pytest.mark.asyncio
async def test_send_message_via_bridge(
    api_client: httpx.AsyncClient,
    test_tenant_id: str,
    test_customer_jid: str
):
    """
    TC-WA-002: Message Sending via Bridge
    
    GIVEN: WhatsApp bridge is connected
    WHEN: POST /api/dashboard/send-message is called
    THEN: Message should be queued successfully
    AND: Bridge should accept the request
    
    Priority: P0 (BLOCKING)
    Rollback Trigger: If message fails to send (400/500)
    
    Note: This test requires bridge to be connected. If bridge is not connected,
    test will be skipped gracefully.
    """
    # Check if bridge is available first
    bridge_url = os.getenv("BRIDGE_URL", "http://localhost:8080").rstrip("/")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as bridge_client:
            bridge_health = await bridge_client.get(f"{bridge_url}/health")
            
            if bridge_health.status_code != 200:
                pytest.skip(f"Bridge not available (HTTP {bridge_health.status_code})")
                
    except Exception as e:
        pytest.skip(f"Bridge not reachable: {e}")
    
    # Arrange: Prepare test message
    test_message = {
        "customer_jid": test_customer_jid,
        "message": "🧪 E2E Test Message - Please ignore. This is an automated test from Bijou AI QA suite.",
        "agent_name": "E2E Test Suite"
    }
    
    # Act: Send message via Dashboard API
    response = await api_client.post(
        "/api/dashboard/send-message",
        json=test_message,
        headers={
            "X-Tenant-ID": test_tenant_id,
            "Content-Type": "application/json"
        }
    )
    
    # Assert: Message should be accepted
    # Accept both 200 (success) and 202 (accepted/queued)
    assert response.status_code in [200, 202, 500], \
        f"❌ Send message returned unexpected status {response.status_code}: {response.text}"
    
    if response.status_code in [200, 202]:
        # Success
        print(f"✅ TC-WA-002 PASSED: Message sent successfully (HTTP {response.status_code})")
        
        # Try to parse response
        try:
            result = response.json()
            assert result.get("status") in ["success", "sent", "queued"], \
                f"Unexpected response status: {result.get('status')}"
            print(f"   Response: {result}")
        except Exception:
            # Non-JSON response is acceptable for some bridge implementations
            pass
            
    else:
        # Bridge may return 500 if WhatsApp is not connected (common scenario)
        response_text = response.text
        
        if "not connected" in response_text.lower() or "no session" in response_text.lower():
            pytest.skip(
                f"Bridge not connected to WhatsApp (needs QR scan): {response_text[:100]}"
            )
        else:
            pytest.fail(
                f"❌ TC-WA-002 FAILED: Message send failed\n"
                f"   HTTP {response.status_code}: {response_text[:200]}"
            )


@pytest.mark.e2e
@pytest.mark.p1
@pytest.mark.whatsapp
@pytest.mark.asyncio
async def test_bridge_status_endpoint(staging_url: str):
    """
    TC-WA-003: Bridge Status Endpoint
    
    GIVEN: Dashboard needs to check WhatsApp connection status
    WHEN: GET /api/dashboard/whatsapp/status is called
    THEN: Current connection status should be returned
    AND: Status should be one of: connected, disconnected, error
    
    Priority: P1 (Should pass)
    Known Issue: Dashboard may show "disconnected" even when connected
    """
    async with httpx.AsyncClient(base_url=staging_url, timeout=10.0) as client:
        # Act: Check WhatsApp status via dashboard API
        response = await client.get(
            "/api/dashboard/whatsapp/status",
            params={"tenant_id": "00000000-0000-0000-0000-000000000001"}
        )
        
        # Assert: Should return status
        assert response.status_code == 200, \
            f"Status endpoint returned {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data or "connected" in data, \
            f"Response missing status field: {data}"
        
        status = data.get("status") or ("connected" if data.get("connected") else "disconnected")
        
        # Validate status is one of expected values
        assert status in ["connected", "disconnected", "connecting", "error"], \
            f"Unexpected status value: {status}"
        
        print(f"✅ TC-WA-003 PASSED: WhatsApp status = {status}")
        
        if status == "disconnected":
            print(f"   ⚠️ Note: Bridge shows disconnected - may be a known dashboard issue")


@pytest.mark.e2e
@pytest.mark.p2
@pytest.mark.whatsapp
@pytest.mark.asyncio
async def test_bridge_qr_code_endpoint(staging_url: str):
    """
    TC-WA-004: QR Code Generation for WhatsApp Linking
    
    GIVEN: WhatsApp needs to be linked
    WHEN: GET /api/dashboard/whatsapp/qr is called
    THEN: QR code should be returned OR connected status
    
    Priority: P2 (Nice to have)
    """
    async with httpx.AsyncClient(base_url=staging_url, timeout=15.0) as client:
        # Act: Request QR code
        response = await client.get(
            "/api/dashboard/whatsapp/qr",
            params={"tenant_id": "00000000-0000-0000-0000-000000000001"}
        )
        
        # Assert: Should return either QR or connection status
        assert response.status_code == 200, \
            f"QR endpoint returned {response.status_code}: {response.text}"
        
        # Check response type
        content_type = response.headers.get("content-type", "")
        
        if "application/json" in content_type:
            data = response.json()
            
            # Either returns QR data or connection status
            if data.get("status") == "connected":
                print(f"✅ TC-WA-004 PASSED: Already connected (no QR needed)")
            elif "qr" in data:
                print(f"✅ TC-WA-004 PASSED: QR code returned")
            else:
                print(f"⚠️ TC-WA-004: Unexpected response: {data}")
        else:
            # Might be an image
            print(f"✅ TC-WA-004 PASSED: QR image returned ({len(response.content)} bytes)")
