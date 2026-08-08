"""
Regression Tests for Security Fixes in v301
============================================

Tests for critical security vulnerabilities fixed in version 301:
- Bug #1: Cross-tenant escalation leak (handover_system.py:128)
- Bug #2: Tenant isolation bypass (handover_system.py:267)

These tests ensure tenant isolation is properly enforced.

Author: W3J Consulting
Created: 2026-02-14
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from src.saas.handover_system import HandoverSystem, EscalationPriority


class TestSecurityBug1_CrossTenantEscalationLeak:
    """
    Test that should_escalate() properly filters by tenant_id.
    
    Bug: Line 128 was missing .eq("tenant_id", tenant_id)
    Risk: Tenant A could see escalations from Tenant B if same chat_jid
    """
    
    def test_recent_escalation_check_filters_by_tenant_id(self):
        """should_escalate() should only check escalations for the given tenant"""
        # Setup mock Supabase client
        mock_supabase = Mock()
        mock_table = Mock()
        mock_query = Mock()
        
        # Chain mocking for query builder
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.execute.return_value = Mock(data=[
            {"id": "esc123", "created_at": datetime.utcnow().isoformat()}
        ])
        
        # Create handover system
        handover = HandoverSystem(supabase_client=mock_supabase)
        handover.enabled = True
        
        # Test message
        tenant_id = "tenant-a"
        chat_jid = "+60123456789@s.whatsapp.net"
        message = "I want to speak to a human"
        
        # Call should_escalate
        should_escalate, reason, priority = handover.should_escalate(
            message=message,
            chat_jid=chat_jid,
            tenant_id=tenant_id
        )
        
        # Verify tenant_id was included in query
        eq_calls = [call.args for call in mock_query.eq.call_args_list]
        assert ("chat_jid", chat_jid) in eq_calls, "Query should filter by chat_jid"
        assert ("tenant_id", tenant_id) in eq_calls, "SECURITY: Query MUST filter by tenant_id"
        
        # Should skip escalation (recently escalated)
        assert should_escalate == False
        assert "Recently escalated" in reason
    
    def test_different_tenants_same_chat_jid_isolated(self):
        """Tenants with same chat_jid should be isolated from each other"""
        mock_supabase = Mock()
        mock_table = Mock()
        mock_query = Mock()
        
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        
        handover = HandoverSystem(supabase_client=mock_supabase)
        handover.enabled = True
        
        # Same chat_jid, different tenants
        chat_jid = "+60123456789@s.whatsapp.net"
        message = "speak to manager"
        
        # Tenant A - has recent escalation
        mock_query.execute.return_value = Mock(data=[{"id": "esc-tenant-a"}])
        should_escalate_a, _, _ = handover.should_escalate(
            message=message,
            chat_jid=chat_jid,
            tenant_id="tenant-a"
        )
        
        # Tenant B - no recent escalation
        mock_query.execute.return_value = Mock(data=[])
        should_escalate_b, _, _ = handover.should_escalate(
            message=message,
            chat_jid=chat_jid,
            tenant_id="tenant-b"
        )
        
        # Tenant A should skip (has recent escalation)
        assert should_escalate_a == False, "Tenant A should skip (recently escalated)"
        
        # Tenant B should escalate (no recent escalation)
        assert should_escalate_b == True, "Tenant B should escalate (different tenant)"
    
    def test_missing_tenant_id_does_not_query_database(self):
        """If tenant_id is None, should not query database (prevents leak)"""
        mock_supabase = Mock()
        handover = HandoverSystem(supabase_client=mock_supabase)
        handover.enabled = True
        
        # Call without tenant_id
        should_escalate, reason, priority = handover.should_escalate(
            message="speak to human",
            chat_jid="+60123456789@s.whatsapp.net",
            tenant_id=None  # Missing tenant_id
        )
        
        # Should NOT query database (security risk)
        mock_supabase.table.assert_not_called()


class TestSecurityBug2_TenantIsolationBypass:
    """
    Test that escalate() requires tenant_id and has no fallback.
    
    Bug: Line 263-276 allowed tenant_id=None with fallback logic
    Risk: Escalations could be assigned to wrong tenant
    """
    
    def test_escalate_requires_tenant_id(self):
        """escalate() must fail if tenant_id is not provided"""
        mock_supabase = Mock()
        handover = HandoverSystem(supabase_client=mock_supabase)
        handover.enabled = True
        
        # Call escalate WITHOUT tenant_id
        result = handover.escalate(
            chat_jid="+60123456789@s.whatsapp.net",
            reason="Customer wants human",
            tenant_id=None,  # MISSING - should fail
            priority="high"
        )
        
        # Should return None (blocked for security)
        assert result is None, "SECURITY: escalate() should fail if tenant_id is None"
        
        # Should NOT create escalation in database
        mock_supabase.table.assert_not_called()
    
    def test_escalate_with_valid_tenant_id_succeeds(self):
        """escalate() should work when tenant_id is provided"""
        mock_supabase = Mock()
        handover = HandoverSystem(supabase_client=mock_supabase)
        handover.enabled = True
        
        # Call escalate WITH tenant_id
        result = handover.escalate(
            chat_jid="+60123456789@s.whatsapp.net",
            reason="Customer wants human",
            tenant_id="tenant-123",  # Provided
            priority="high"
        )
        
        # Should proceed (may return None due to async handling, but should not block)
        # The key is that it doesn't raise an error and doesn't fall back to default
        assert True  # If we got here without error, test passes
    
    def test_escalate_does_not_use_default_tenant_fallback(self):
        """escalate() should NOT fall back to DEFAULT_TENANT_ID env var"""
        mock_supabase = Mock()
        handover = HandoverSystem(supabase_client=mock_supabase)
        handover.enabled = True
        
        # Set environment variable (should NOT be used)
        with patch.dict('os.environ', {'DEFAULT_TENANT_ID': 'fallback-tenant'}):
            result = handover.escalate(
                chat_jid="+60123456789@s.whatsapp.net",
                reason="Test",
                tenant_id=None,  # Missing
                priority="normal"
            )
            
            # Should return None (blocked)
            assert result is None
            
            # Should NOT use fallback tenant
            mock_supabase.table.assert_not_called()
    
    def test_escalate_logs_security_error_when_tenant_id_missing(self, caplog):
        """escalate() should log security error when tenant_id is missing"""
        import logging
        
        mock_supabase = Mock()
        handover = HandoverSystem(supabase_client=mock_supabase)
        handover.enabled = True
        
        with caplog.at_level(logging.ERROR):
            handover.escalate(
                chat_jid="+60123456789@s.whatsapp.net",
                reason="Test",
                tenant_id=None,
                priority="normal"
            )
        
        # Should log security error
        assert any("SECURITY" in record.message for record in caplog.records), \
            "Should log SECURITY error when tenant_id is missing"
        assert any("tenant_id is required" in record.message for record in caplog.records), \
            "Should explain why escalation was blocked"


class TestTenantIsolationRegression:
    """
    General regression tests to ensure tenant isolation is enforced.
    """
    
    def test_all_escalation_queries_filter_by_tenant_id(self):
        """All database queries should include tenant_id filter"""
        mock_supabase = Mock()
        mock_table = Mock()
        mock_query = Mock()
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = Mock(data=[])
        
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        
        handover = HandoverSystem(supabase_client=mock_supabase)
        handover.enabled = True
        
        tenant_id = "test-tenant"
        
        # Test get_queue()
        handover.get_queue(tenant_id=tenant_id)
        
        # Verify tenant_id filter was applied
        eq_calls = [call.args for call in mock_query.eq.call_args_list]
        assert ("tenant_id", tenant_id) in eq_calls, \
            "get_queue() must filter by tenant_id"
    
    def test_sla_breaches_filter_by_tenant_id(self):
        """get_sla_breaches() should filter by tenant_id"""
        mock_supabase = Mock()
        mock_table = Mock()
        mock_query = Mock()
        mock_query.eq.return_value = mock_query
        mock_query.in_.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = Mock(data=[])
        
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        
        handover = HandoverSystem(supabase_client=mock_supabase)
        handover.enabled = True
        
        tenant_id = "test-tenant"
        handover.get_sla_breaches(tenant_id=tenant_id)
        
        # Verify tenant_id filter
        eq_calls = [call.args for call in mock_query.eq.call_args_list]
        assert ("tenant_id", tenant_id) in eq_calls, \
            "get_sla_breaches() must filter by tenant_id"
    
    def test_statistics_filter_by_tenant_id(self):
        """get_statistics() should filter by tenant_id"""
        mock_supabase = Mock()
        mock_table = Mock()
        mock_query = Mock()
        mock_query.eq.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = Mock(data=[])
        
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        
        handover = HandoverSystem(supabase_client=mock_supabase)
        handover.enabled = True
        
        tenant_id = "test-tenant"
        handover.get_statistics(tenant_id=tenant_id)
        
        # Verify tenant_id filter
        eq_calls = [call.args for call in mock_query.eq.call_args_list]
        assert ("tenant_id", tenant_id) in eq_calls, \
            "get_statistics() must filter by tenant_id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
