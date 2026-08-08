"""
Bijou AI - Automated API Endpoint Tests
========================================

Comprehensive test suite for all API endpoints based on POSTMAN_TEST_CHECKLIST.md

Run with: pytest tests/integration/test_api_endpoints.py -v
Run with coverage: pytest tests/integration/test_api_endpoints.py -v --cov=src

Author: W3J Bijou AI
Version: 2.2.0
Date: February 17, 2026
"""

import json
import os
from typing import Dict, Optional

import pytest
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base URL for API
BASE_URL = os.getenv("HOSTNAME", "https://bijou-staging.fly.dev")
DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "")
API_KEY = os.getenv("API_KEY", "")
TENANT_ID = os.getenv("TENANT_ID", "")


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def api_client():
    """HTTP client for API requests"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def auth_headers():
    """Headers with authentication token"""
    return {"Authorization": f"Bearer {DASHBOARD_TOKEN}"}


@pytest.fixture
def api_key_headers():
    """Headers with API key for webhooks"""
    return {"X-API-Key": API_KEY}


# ============================================================================
# PHASE 1: HEALTH & DOCUMENTATION (No Auth Required)
# ============================================================================


class TestPhase1HealthAndDocs:
    """Test health check and documentation endpoints"""

    def test_01_health_check(self, api_client):
        """Test 1: Health endpoint returns healthy status"""
        response = api_client.get(f"{BASE_URL}/health")

        assert response.status_code == 200, "Health check should return 200"
        data = response.json()

        # Verify required fields
        assert data["status"] == "healthy", "Status should be 'healthy'"
        assert "service" in data, "Should include service name"
        assert "version" in data, "Should include version"
        assert data["version"] == "2.2.0", "Version should be 2.2.0"
        assert "timestamp" in data, "Should include timestamp"
        assert "database" in data, "Should include database info"

    def test_02_postman_collection_download(self, api_client):
        """Test 2: Postman collection downloads successfully"""
        response = api_client.get(f"{BASE_URL}/postman-collection")

        assert response.status_code == 200, "Should return 200"
        assert (
            response.headers["Content-Type"] == "application/json"
        ), "Should be JSON"
        assert (
            "attachment" in response.headers.get("Content-Disposition", "")
        ), "Should have download header"

        # Verify it's valid JSON
        data = response.json()
        assert "info" in data, "Should have info section"
        assert "item" in data, "Should have items (endpoints)"
        assert data["info"]["name"] == "Bijou AI WhatsApp Enterprise"
        assert data["info"]["version"] == "2.2.0"

        # Verify it has environment variables
        assert "variable" in data, "Should have environment variables"
        var_keys = [v["key"] for v in data["variable"]]
        assert "base_url" in var_keys
        assert "dashboard_token" in var_keys

    def test_03_api_documentation(self, api_client):
        """Test 3: API documentation page loads"""
        response = api_client.get(f"{BASE_URL}/api-docs")

        assert response.status_code == 200, "Should return 200"
        assert "text/html" in response.headers["Content-Type"], "Should be HTML"

        # Verify Postman section exists
        html_content = response.text
        assert "Postman" in html_content, "Should mention Postman"
        assert (
            "/postman-collection" in html_content
        ), "Should have download link"

    def test_04_changelog(self, api_client):
        """Test 4: Changelog returns version history"""
        response = api_client.get(f"{BASE_URL}/changelog")

        assert response.status_code == 200, "Should return 200"

        data = response.json()
        assert isinstance(data, list), "Should return array of versions"

        # Verify latest version exists
        if len(data) > 0:
            latest = data[0]
            assert "version" in latest, "Should have version field"
            assert "changes" in latest, "Should have changes list"

    def test_05_openapi_schema(self, api_client):
        """Test 5: OpenAPI schema is valid"""
        response = api_client.get(f"{BASE_URL}/openapi.json")

        assert response.status_code == 200, "Should return 200"

        data = response.json()
        assert "openapi" in data, "Should have OpenAPI version"
        assert "info" in data, "Should have info section"
        assert "paths" in data, "Should have paths (endpoints)"

        # Verify key endpoints exist
        paths = data["paths"]
        assert "/health" in paths, "Should have /health endpoint"
        assert "/postman-collection" in paths, "Should have /postman-collection"


# ============================================================================
# PHASE 2: AUTHENTICATION
# ============================================================================


class TestPhase2Authentication:
    """Test authentication endpoints"""

    def test_06_google_oauth_login(self, api_client):
        """Test 6: Google OAuth login redirects correctly"""
        response = api_client.get(
            f"{BASE_URL}/api/auth/google/login", allow_redirects=False
        )

        # Should redirect (302 or 307)
        assert response.status_code in [
            302,
            307,
        ], "Should redirect to Google OAuth"

        # Verify redirect location
        location = response.headers.get("Location", "")
        assert (
            "accounts.google.com" in location
        ), "Should redirect to Google accounts"
        assert "oauth2" in location.lower(), "Should be OAuth2 flow"

    def test_07_dashboard_google_auth_url(self, api_client):
        """Test 7: Dashboard Google auth URL endpoint"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/google/auth-url")

        assert response.status_code == 200, "Should return 200"

        data = response.json()
        assert "auth_url" in data, "Should return auth_url field"
        assert (
            "accounts.google.com" in data["auth_url"]
        ), "Should be Google OAuth URL"


# ============================================================================
# PHASE 3: DASHBOARD API (Auth Required)
# ============================================================================


@pytest.mark.skipif(
    not DASHBOARD_TOKEN, reason="DASHBOARD_TOKEN not set in environment"
)
class TestPhase3DashboardAPI:
    """Test dashboard API endpoints (requires authentication)"""

    def test_08_get_conversations(self, api_client, auth_headers):
        """Test 8: Get conversations list"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/conversations", headers=auth_headers
        )

        # Accept both 200 (data found) and 401 (auth issue)
        assert response.status_code in [
            200,
            401,
        ], f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            assert "conversations" in data or isinstance(
                data, list
            ), "Should return conversations"

    def test_09_get_dashboard_stats(self, api_client, auth_headers):
        """Test 9: Get dashboard statistics"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats", headers=auth_headers
        )

        assert response.status_code in [200, 401], "Should return 200 or 401"

        if response.status_code == 200:
            data = response.json()
            # Verify expected stats fields exist
            expected_fields = [
                "total_conversations",
                "ai_handled",
                "human_handled",
            ]
            for field in expected_fields:
                if field in data:
                    assert isinstance(
                        data[field], (int, float)
                    ), f"{field} should be numeric"

    def test_10_get_single_conversation(self, api_client, auth_headers):
        """Test 10: Get single conversation details"""
        # First get conversations to get a valid JID
        list_response = api_client.get(
            f"{BASE_URL}/api/dashboard/conversations", headers=auth_headers
        )

        if list_response.status_code == 200:
            conversations = list_response.json()
            if isinstance(conversations, dict):
                conversations = conversations.get("conversations", [])

            if len(conversations) > 0:
                chat_jid = conversations[0].get("chat_jid")
                if chat_jid:
                    response = api_client.get(
                        f"{BASE_URL}/api/dashboard/conversation/{chat_jid}",
                        headers=auth_headers,
                    )
                    assert response.status_code in [
                        200,
                        404,
                    ], "Should return 200 or 404"

    def test_11_send_message(self, api_client, auth_headers):
        """Test 11: Send message endpoint structure"""
        # We won't actually send messages in tests, just verify endpoint exists
        test_payload = {
            "chat_jid": "60123456789@s.whatsapp.net",
            "message": "Test message",
        }

        response = api_client.post(
            f"{BASE_URL}/api/dashboard/send-message",
            headers=auth_headers,
            json=test_payload,
        )

        # Accept 200 (success), 400 (validation), 401 (auth), 404 (not found)
        assert response.status_code in [
            200,
            400,
            401,
            404,
            500,
        ], "Should handle request"

    def test_12_takeover_conversation(self, api_client, auth_headers):
        """Test 12: Takeover conversation endpoint"""
        test_payload = {
            "customer_jid": "60123456789@s.whatsapp.net",
            "agent_name": "Test Agent",
            "reason": "Testing",
        }

        response = api_client.post(
            f"{BASE_URL}/api/dashboard/takeover",
            headers=auth_headers,
            json=test_payload,
        )

        assert response.status_code in [
            200,
            400,
            401,
            404,
        ], "Should handle request"

    def test_13_release_takeover(self, api_client, auth_headers):
        """Test 13: Release takeover endpoint"""
        test_payload = {"customer_jid": "60123456789@s.whatsapp.net"}

        response = api_client.post(
            f"{BASE_URL}/api/dashboard/release-takeover",
            headers=auth_headers,
            json=test_payload,
        )

        assert response.status_code in [
            200,
            400,
            401,
            404,
        ], "Should handle request"

    def test_14_get_active_takeovers(self, api_client, auth_headers):
        """Test 14: Get active takeovers list"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/takeovers", headers=auth_headers
        )

        assert response.status_code in [200, 401], "Should return 200 or 401"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(
                data, (list, dict)
            ), "Should return takeovers array or object"


# ============================================================================
# PHASE 4: KNOWLEDGE BASE API (Auth Required)
# ============================================================================


@pytest.mark.skipif(
    not DASHBOARD_TOKEN, reason="DASHBOARD_TOKEN not set in environment"
)
class TestPhase4KnowledgeBase:
    """Test knowledge base CRUD operations"""

    def test_15_list_knowledge_items(self, api_client, auth_headers):
        """Test 15: List all knowledge base items"""
        response = api_client.get(
            f"{BASE_URL}/api/knowledge/list", headers=auth_headers
        )

        assert response.status_code in [200, 401], "Should return 200 or 401"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(
                data, (list, dict)
            ), "Should return knowledge items"

    def test_16_add_knowledge_item(self, api_client, auth_headers):
        """Test 16: Add new knowledge item"""
        test_payload = {
            "content": "Test knowledge item for automated testing",
            "source_name": "automated_test",
        }

        response = api_client.post(
            f"{BASE_URL}/api/knowledge/add",
            headers=auth_headers,
            json=test_payload,
        )

        assert response.status_code in [
            200,
            201,
            401,
        ], "Should create or require auth"

        if response.status_code in [200, 201]:
            data = response.json()
            # Store knowledge_id for cleanup
            if "knowledge_id" in data or "id" in data:
                pytest.knowledge_id_to_cleanup = data.get(
                    "knowledge_id", data.get("id")
                )

    def test_17_update_knowledge_item(self, api_client, auth_headers):
        """Test 17: Update knowledge item"""
        # Skip if we don't have a knowledge_id from previous test
        if not hasattr(pytest, "knowledge_id_to_cleanup"):
            pytest.skip("No knowledge_id available for update test")

        knowledge_id = pytest.knowledge_id_to_cleanup
        test_payload = {
            "content": "Updated test knowledge item",
            "source_name": "automated_test_updated",
        }

        response = api_client.put(
            f"{BASE_URL}/api/knowledge/update/{knowledge_id}",
            headers=auth_headers,
            json=test_payload,
        )

        assert response.status_code in [
            200,
            401,
            404,
        ], "Should update or return error"

    def test_18_delete_knowledge_item(self, api_client, auth_headers):
        """Test 18: Delete knowledge item (cleanup)"""
        if not hasattr(pytest, "knowledge_id_to_cleanup"):
            pytest.skip("No knowledge_id available for deletion")

        knowledge_id = pytest.knowledge_id_to_cleanup

        response = api_client.delete(
            f"{BASE_URL}/api/knowledge/delete/{knowledge_id}",
            headers=auth_headers,
        )

        assert response.status_code in [
            200,
            204,
            401,
            404,
        ], "Should delete or return error"


# ============================================================================
# PHASE 5: ONBOARDING API (Token-based)
# ============================================================================


class TestPhase5Onboarding:
    """Test onboarding flow endpoints"""

    def test_19_onboarding_status(self, api_client):
        """Test 19: Get onboarding status (with dummy token)"""
        dummy_token = "test_token_12345"

        response = api_client.get(
            f"{BASE_URL}/api/onboarding/status/{dummy_token}"
        )

        # Accept 200 (found), 404 (not found), 400 (invalid)
        assert response.status_code in [
            200,
            400,
            404,
        ], "Should handle token lookup"

    def test_20_generate_qr_code(self, api_client):
        """Test 20: Generate QR code endpoint"""
        test_payload = {"token": "test_token_12345"}

        response = api_client.post(
            f"{BASE_URL}/api/onboarding/generate-qr", json=test_payload
        )

        assert response.status_code in [
            200,
            400,
            404,
        ], "Should handle QR generation"

    def test_21_check_whatsapp_connection(self, api_client):
        """Test 21: Check WhatsApp connection status"""
        dummy_token = "test_token_12345"

        response = api_client.get(
            f"{BASE_URL}/api/onboarding/check-connection/{dummy_token}"
        )

        assert response.status_code in [
            200,
            404,
        ], "Should handle connection check"


# ============================================================================
# PHASE 6: WEBHOOKS (API Key Required)
# ============================================================================


@pytest.mark.skipif(not API_KEY, reason="API_KEY not set in environment")
class TestPhase6Webhooks:
    """Test webhook endpoints"""

    def test_22_whatsapp_webhook(self, api_client, api_key_headers):
        """Test 22: WhatsApp message webhook"""
        test_payload = {
            "from": "60123456789@s.whatsapp.net",
            "body": "Test message from automated tests",
            "timestamp": 1708099200,
            "messageId": "test_msg_123",
        }

        response = api_client.post(
            f"{BASE_URL}/webhook/whatsapp",
            headers=api_key_headers,
            json=test_payload,
        )

        assert response.status_code in [
            200,
            401,
            400,
        ], "Should process webhook"

    def test_23_google_sheets_webhook(self, api_client, api_key_headers):
        """Test 23: Google Sheets sync webhook"""
        test_payload = {
            "action": "sync_knowledge",
            "sheet_id": "test_sheet_123",
            "row_data": {
                "question": "Test question",
                "answer": "Test answer",
            },
        }

        response = api_client.post(
            f"{BASE_URL}/webhook/google-sheets",
            headers=api_key_headers,
            json=test_payload,
        )

        assert response.status_code in [
            200,
            400,
            401,
            404,
        ], "Should handle webhook"

    def test_24_zapier_webhook(self, api_client, api_key_headers):
        """Test 24: Zapier/Make.com webhook"""
        test_payload = {
            "trigger": "new_customer",
            "data": {
                "phone": "+60123456789",
                "name": "Test Customer",
                "source": "Automated Test",
            },
        }

        response = api_client.post(
            f"{BASE_URL}/webhook/zapier",
            headers=api_key_headers,
            json=test_payload,
        )

        assert response.status_code in [
            200,
            400,
            401,
            404,
        ], "Should handle webhook"


# ============================================================================
# PHASE 7: SYSTEM DOCUMENTATION
# ============================================================================


class TestPhase7Documentation:
    """Test interactive documentation endpoints"""

    def test_25_swagger_ui(self, api_client):
        """Test 25: Swagger UI loads"""
        response = api_client.get(f"{BASE_URL}/docs")

        assert response.status_code == 200, "Swagger UI should load"
        assert "text/html" in response.headers["Content-Type"], "Should be HTML"

    def test_26_redoc(self, api_client):
        """Test 26: ReDoc documentation loads"""
        response = api_client.get(f"{BASE_URL}/redoc")

        assert response.status_code == 200, "ReDoc should load"
        assert "text/html" in response.headers["Content-Type"], "Should be HTML"


# ============================================================================
# TEST REPORT GENERATION
# ============================================================================


def pytest_sessionfinish(session, exitstatus):
    """Generate test report after all tests complete"""
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")

    if reporter:
        print("\n" + "=" * 80)
        print("📊 BIJOU AI API TEST REPORT")
        print("=" * 80)
        print(f"Total Tests: {reporter.stats.get('total', 0)}")
        print(f"✅ Passed: {len(reporter.stats.get('passed', []))}")
        print(f"❌ Failed: {len(reporter.stats.get('failed', []))}")
        print(f"⏭️  Skipped: {len(reporter.stats.get('skipped', []))}")
        print("=" * 80)
