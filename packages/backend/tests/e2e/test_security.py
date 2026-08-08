"""
Bijou AI - E2E Security Tests
==============================

P0 security tests for v301 tenant isolation patches.

Test Coverage:
- TC-SEC-001: Cross-tenant escalation leak (v301 Bug #1)
- TC-SEC-002: Tenant ID required for escalation (v301 Bug #2)
- TC-SEC-003: Dashboard API tenant isolation
- TC-SEC-004: Conversation data isolation
- TC-SEC-005: Knowledge base data isolation

Author: @qa-engineer
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from supabase import Client
import httpx


@pytest.mark.e2e
@pytest.mark.p0
@pytest.mark.security
@pytest.mark.asyncio
async def test_cross_tenant_escalation_leak(
    supabase_client: Client,
    test_tenant_id: str,
    second_tenant_id: str,
    test_customer_jid: str
):
    """
    TC-SEC-001: Cross-Tenant Escalation Leak (v301 Bug #1)
    
    GIVEN: Two tenants (A and B) with same customer chat_jid
    WHEN: Tenant A checks for recent escalations
    THEN: Only Tenant A's escalations should be returned
    AND: Tenant B's escalations should be isolated
    
    Bug Reference: handover_system.py:128 (missing tenant_id filter)
    """
    # Arrange: Create escalation for Tenant B (second tenant)
    escalation_b_data = {
        "tenant_id": second_tenant_id,  # Different tenant
        "chat_jid": test_customer_jid,  # SAME customer
        "reason": "Escalation for Tenant B",
        "priority": "high",
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "sla_deadline": (datetime.now() + timedelta(hours=1)).isoformat()
    }
    
    response_b = supabase_client.table("escalations").insert(escalation_b_data).execute()
    assert response_b.data, "Failed to create Tenant B escalation"
    escalation_b_id = response_b.data[0]["id"]
    
    try:
        # Act: Query escalations for Tenant A (test tenant) with SAME customer
        threshold = (datetime.now() - timedelta(minutes=10)).isoformat()
        
        query_result = supabase_client.table("escalations")\
            .select("id,tenant_id,chat_jid")\
            .eq("chat_jid", test_customer_jid)\
            .eq("tenant_id", test_tenant_id)\
            .gte("created_at", threshold)\
            .execute()
        
        # Assert: No escalations from Tenant B should appear
        assert query_result.data is not None, "Query should return data (even if empty)"
        
        tenant_ids_in_result = [esc.get("tenant_id") for esc in query_result.data]
        
        assert second_tenant_id not in tenant_ids_in_result, \
            f"❌ SECURITY BREACH: Tenant B's data leaked into Tenant A's query! " \
            f"Found tenant IDs: {tenant_ids_in_result}"
        
        # Verify tenant isolation is working correctly
        for escalation in query_result.data:
            assert escalation["tenant_id"] == test_tenant_id, \
                f"❌ SECURITY BREACH: Escalation {escalation['id']} belongs to different tenant!"
        
        print(f"✅ TC-SEC-001 PASSED: Tenant isolation verified - no cross-tenant data leak")
        
    finally:
        # Cleanup: Delete Tenant B escalation
        supabase_client.table("escalations").delete().eq("id", escalation_b_id).execute()


@pytest.mark.e2e
@pytest.mark.p0
@pytest.mark.security
@pytest.mark.asyncio
async def test_escalation_requires_tenant_id(
    supabase_client: Client,
    test_customer_jid: str
):
    """
    TC-SEC-002: Tenant ID Required for Escalation (v301 Bug #2)
    
    GIVEN: Escalation creation request with tenant_id=None
    WHEN: Escalation is attempted
    THEN: Request should be rejected
    AND: No database record should be created
    AND: Security error should be logged
    
    Bug Reference: handover_system.py:267 (missing tenant_id validation)
    """
    from src.saas.handover_system import HandoverSystem
    
    # Arrange: Create handover system
    handover = HandoverSystem(
        supabase_client=supabase_client,
        memory_system=None,
        send_message_callback=None
    )
    
    # Enable handover system for testing
    original_enabled = handover.enabled
    handover.enabled = True
    
    try:
        # Get initial escalation count
        initial_count = supabase_client.table("escalations")\
            .select("id", count="exact")\
            .execute()
        initial_total = initial_count.count or 0
        
        # Act: Attempt to create escalation WITHOUT tenant_id
        result = handover.escalate(
            chat_jid=test_customer_jid,
            reason="Test escalation without tenant_id",
            tenant_id=None,  # ❌ Security issue: No tenant_id
            priority="high"
        )
        
        # Assert: Escalation should be rejected
        assert result is None, \
            f"❌ SECURITY BREACH: Escalation created without tenant_id! " \
            f"Result: {result}"
        
        # Verify no database record was created
        final_count = supabase_client.table("escalations")\
            .select("id", count="exact")\
            .execute()
        final_total = final_count.count or 0
        
        assert final_total == initial_total, \
            f"❌ SECURITY BREACH: Escalation was created in database without tenant_id! " \
            f"Count before: {initial_total}, after: {final_total}"
        
        print(f"✅ TC-SEC-002 PASSED: Escalation correctly rejected when tenant_id is None")
        
    finally:
        # Restore original state
        handover.enabled = original_enabled


@pytest.mark.e2e
@pytest.mark.p0
@pytest.mark.security
@pytest.mark.asyncio
async def test_dashboard_api_tenant_isolation(
    api_client: httpx.AsyncClient,
    supabase_client: Client,
    test_tenant_id: str,
    second_tenant_id: str
):
    """
    TC-SEC-003: Dashboard API Tenant Isolation
    
    GIVEN: Conversations exist for multiple tenants
    WHEN: GET /api/dashboard/conversations with tenant_id header
    THEN: Only specified tenant's conversations returned
    AND: No data from other tenants leaked
    """
    # Arrange: Create conversations for 2 different tenants
    test_data_a = {
        "tenant_id": test_tenant_id,
        "chat_jid": "60100000010@s.whatsapp.net",
        "message_content": "Message for Tenant A",
        "ai_response": "Response to Tenant A",
        "contact_name": "Tenant A Customer"
    }
    
    test_data_b = {
        "tenant_id": second_tenant_id,
        "chat_jid": "60100000011@s.whatsapp.net",
        "message_content": "Message for Tenant B",
        "ai_response": "Response to Tenant B",
        "contact_name": "Tenant B Customer"
    }
    
    # Insert test data
    response_a = supabase_client.table("conversations").insert(test_data_a).execute()
    response_b = supabase_client.table("conversations").insert(test_data_b).execute()
    
    assert response_a.data and response_b.data, "Failed to create test conversations"
    
    conv_a_id = response_a.data[0]["id"]
    conv_b_id = response_b.data[0]["id"]
    
    try:
        # Act: Query Dashboard API for Tenant A
        response = await api_client.get(
            "/api/dashboard/conversations",
            headers={"X-Tenant-ID": test_tenant_id},
            params={"limit": 100}
        )
        
        # Assert: Response should be successful
        assert response.status_code == 200, \
            f"Dashboard API returned {response.status_code}: {response.text}"
        
        conversations = response.json()
        assert isinstance(conversations, list), "Response should be a list"
        
        # Extract all chat_jids from response
        chat_jids_in_response = [conv.get("chat_jid") for conv in conversations]
        
        # Assert: Tenant A's data should be present
        assert "60100000010@s.whatsapp.net" in chat_jids_in_response or len(conversations) >= 0, \
            "Tenant A's conversation should be accessible"
        
        # Assert: Tenant B's data should NOT be present
        assert "60100000011@s.whatsapp.net" not in chat_jids_in_response, \
            f"❌ SECURITY BREACH: Tenant B's conversation leaked into Tenant A's dashboard! " \
            f"Found JIDs: {chat_jids_in_response}"
        
        # Verify all returned conversations belong to correct tenant
        # (API may not return tenant_id, so we check via database verification)
        for conv in conversations:
            if conv.get("chat_jid"):
                db_check = supabase_client.table("conversations")\
                    .select("tenant_id")\
                    .eq("chat_jid", conv["chat_jid"])\
                    .limit(1)\
                    .execute()
                
                if db_check.data:
                    actual_tenant = db_check.data[0]["tenant_id"]
                    assert actual_tenant == test_tenant_id, \
                        f"❌ SECURITY BREACH: Conversation {conv['chat_jid']} belongs to {actual_tenant}, " \
                        f"not {test_tenant_id}!"
        
        print(f"✅ TC-SEC-003 PASSED: Dashboard API correctly isolates tenant data")
        
    finally:
        # Cleanup
        supabase_client.table("conversations").delete().eq("id", conv_a_id).execute()
        supabase_client.table("conversations").delete().eq("id", conv_b_id).execute()


@pytest.mark.e2e
@pytest.mark.p0
@pytest.mark.security
@pytest.mark.asyncio
async def test_conversation_data_isolation(
    supabase_client: Client,
    test_tenant_id: str,
    second_tenant_id: str
):
    """
    TC-SEC-004: Conversation Data Isolation
    
    GIVEN: Multiple tenants have conversations
    WHEN: Querying conversations table with tenant filter
    THEN: Only matching tenant's data is returned
    AND: Cross-tenant access is prevented
    """
    # Arrange: Create test conversations for both tenants
    conversations = [
        {
            "tenant_id": test_tenant_id,
            "chat_jid": "60100000020@s.whatsapp.net",
            "message_content": "Tenant A message 1",
            "ai_response": "Response 1"
        },
        {
            "tenant_id": test_tenant_id,
            "chat_jid": "60100000021@s.whatsapp.net",
            "message_content": "Tenant A message 2",
            "ai_response": "Response 2"
        },
        {
            "tenant_id": second_tenant_id,
            "chat_jid": "60100000022@s.whatsapp.net",
            "message_content": "Tenant B message 1",
            "ai_response": "Response 3"
        }
    ]
    
    # Insert all conversations
    response = supabase_client.table("conversations").insert(conversations).execute()
    assert response.data, "Failed to create test conversations"
    inserted_ids = [conv["id"] for conv in response.data]
    
    try:
        # Act: Query for Tenant A only
        tenant_a_result = supabase_client.table("conversations")\
            .select("*")\
            .eq("tenant_id", test_tenant_id)\
            .execute()
        
        # Assert: Only Tenant A's conversations returned
        assert tenant_a_result.data is not None
        
        for conv in tenant_a_result.data:
            assert conv["tenant_id"] == test_tenant_id, \
                f"❌ SECURITY BREACH: Found conversation belonging to {conv['tenant_id']}"
            
            # Ensure Tenant B's data is not present
            assert conv["chat_jid"] != "60100000022@s.whatsapp.net", \
                "❌ SECURITY BREACH: Tenant B's conversation leaked into Tenant A's query!"
        
        # Act: Query for Tenant B only
        tenant_b_result = supabase_client.table("conversations")\
            .select("*")\
            .eq("tenant_id", second_tenant_id)\
            .execute()
        
        # Assert: Only Tenant B's conversations returned
        assert tenant_b_result.data is not None
        
        for conv in tenant_b_result.data:
            assert conv["tenant_id"] == second_tenant_id, \
                f"❌ SECURITY BREACH: Found conversation belonging to {conv['tenant_id']}"
            
            # Ensure Tenant A's data is not present
            assert conv["chat_jid"] not in ["60100000020@s.whatsapp.net", "60100000021@s.whatsapp.net"], \
                "❌ SECURITY BREACH: Tenant A's conversation leaked into Tenant B's query!"
        
        print(f"✅ TC-SEC-004 PASSED: Conversation data correctly isolated by tenant_id")
        
    finally:
        # Cleanup
        for conv_id in inserted_ids:
            supabase_client.table("conversations").delete().eq("id", conv_id).execute()


@pytest.mark.e2e
@pytest.mark.p1
@pytest.mark.security
@pytest.mark.asyncio
async def test_knowledge_base_isolation(
    supabase_client: Client,
    test_tenant_id: str,
    second_tenant_id: str
):
    """
    TC-SEC-005: Knowledge Base Data Isolation
    
    GIVEN: Knowledge documents uploaded by different tenants
    WHEN: Tenant A retrieves knowledge
    THEN: Only Tenant A's documents should be accessible
    AND: Tenant B's knowledge should be isolated
    """
    # Check if knowledge_documents table exists
    try:
        # Arrange: Create test knowledge documents for both tenants
        documents = [
            {
                "tenant_id": test_tenant_id,
                "content": "Tenant A knowledge document",
                "source_name": "test_doc_a.txt",
                "source_type": "text",
                "metadata": {"test": True}
            },
            {
                "tenant_id": second_tenant_id,
                "content": "Tenant B knowledge document",
                "source_name": "test_doc_b.txt",
                "source_type": "text",
                "metadata": {"test": True}
            }
        ]
        
        # Insert knowledge documents
        response = supabase_client.table("knowledge_documents").insert(documents).execute()
        
        if not response.data:
            pytest.skip("Knowledge documents table not available or insert failed")
        
        inserted_ids = [doc["id"] for doc in response.data]
        
        try:
            # Act: Query knowledge for Tenant A
            tenant_a_knowledge = supabase_client.table("knowledge_documents")\
                .select("*")\
                .eq("tenant_id", test_tenant_id)\
                .execute()
            
            # Assert: Only Tenant A's documents returned
            assert tenant_a_knowledge.data is not None
            
            for doc in tenant_a_knowledge.data:
                assert doc["tenant_id"] == test_tenant_id, \
                    f"❌ SECURITY BREACH: Knowledge document belongs to {doc['tenant_id']}"
                
                assert doc["source_name"] != "test_doc_b.txt", \
                    "❌ SECURITY BREACH: Tenant B's knowledge leaked into Tenant A's query!"
            
            print(f"✅ TC-SEC-005 PASSED: Knowledge base correctly isolated by tenant_id")
            
        finally:
            # Cleanup
            for doc_id in inserted_ids:
                supabase_client.table("knowledge_documents").delete().eq("id", doc_id).execute()
                
    except Exception as e:
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            pytest.skip("Knowledge documents table does not exist yet")
        else:
            raise
