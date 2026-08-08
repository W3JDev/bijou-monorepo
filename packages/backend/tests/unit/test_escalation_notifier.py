"""
Unit Tests for Escalation Notifier
====================================

Tests email and SMS notification functionality for escalations

Author: W3J Consulting
Date: 2026-02-25
Phase: BUG-002 Fix
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.saas.escalation_notifier import EscalationNotifier, NotificationChannel


# Test fixtures
@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    mock_client = Mock()
    
    # Mock table operations
    mock_table = Mock()
    mock_insert = Mock()
    mock_execute = Mock()
    
    mock_execute.return_value = Mock(data=[{"id": "test-notification-id"}])
    mock_insert.execute = mock_execute
    mock_table.insert = Mock(return_value=mock_insert)
    mock_client.table = Mock(return_value=mock_table)
    
    return mock_client


@pytest.fixture
def sample_agent_data():
    """Sample agent data for testing"""
    return {
        "agent_name": "John Doe",
        "email": "john@example.com",
        "phone_number": "+60123456789",
        "whatsapp_number": "+60123456789",
        "notification_preferences": ["email", "whatsapp"]
    }


@pytest.fixture
def sample_escalation_data():
    """Sample escalation data for testing"""
    return {
        "id": "test-escalation-id",
        "chat_jid": "+60198765432@s.whatsapp.net",
        "reason": "Customer requested human agent",
        "priority": "high",
        "escalation_type": "general",
        "customer_context": {
            "name": "Jane Customer"
        },
        "conversation_context": {
            "recent_messages": [
                {"message_content": "I need help with my order", "is_from_me": False},
                {"message_content": "I can help you with that", "is_from_me": True},
                {"message_content": "I want to speak to a human", "is_from_me": False}
            ]
        }
    }


@pytest.fixture
def notifier(mock_supabase):
    """Create notifier instance with mocked dependencies"""
    return EscalationNotifier(
        supabase_client=mock_supabase,
        whatsapp_bridge_url="https://test-bridge.example.com"
    )


class TestEscalationNotifier:
    """Test suite for EscalationNotifier"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_supabase):
        """Test notifier initialization"""
        notifier = EscalationNotifier(
            supabase_client=mock_supabase,
            whatsapp_bridge_url="https://test.example.com"
        )
        
        assert notifier.db is not None
        assert notifier.whatsapp_bridge_url == "https://test.example.com"
        assert notifier.available_channels[NotificationChannel.EMAIL] is True
        assert notifier.available_channels[NotificationChannel.WHATSAPP] is True
    
    @pytest.mark.asyncio
    async def test_email_notification_no_credentials(self, notifier, sample_agent_data, sample_escalation_data):
        """Test email notification fails gracefully without SMTP credentials"""
        with patch.dict(os.environ, {}, clear=True):
            context = notifier._build_notification_context(
                sample_escalation_data,
                sample_agent_data
            )
            
            result = await notifier._send_email(sample_agent_data, context)
            assert result is False  # Should fail without credentials
    
    @pytest.mark.asyncio
    @patch('src.saas.escalation_notifier.smtplib.SMTP')
    async def test_email_notification_success(self, mock_smtp, notifier, sample_agent_data, sample_escalation_data):
        """Test successful email notification"""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Set environment variables
        with patch.dict(os.environ, {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'test-password'
        }):
            context = notifier._build_notification_context(
                sample_escalation_data,
                sample_agent_data
            )
            
            result = await notifier._send_email(sample_agent_data, context)
            
            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with('test@example.com', 'test-password')
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sms_notification_no_credentials(self, notifier, sample_agent_data, sample_escalation_data):
        """Test SMS notification fails gracefully without Twilio credentials"""
        with patch.dict(os.environ, {}, clear=True):
            context = notifier._build_notification_context(
                sample_escalation_data,
                sample_agent_data
            )
            
            result = await notifier._send_sms(sample_agent_data, context)
            assert result is False  # Should fail without credentials
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_sms_notification_success(self, mock_httpx, notifier, sample_agent_data, sample_escalation_data):
        """Test successful SMS notification via Twilio"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Set Twilio environment variables
        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': 'test-sid',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_FROM_NUMBER': '+15551234567'
        }):
            context = notifier._build_notification_context(
                sample_escalation_data,
                sample_agent_data
            )
            
            result = await notifier._send_sms(sample_agent_data, context)
            
            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert 'https://api.twilio.com' in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_notification_context_building(self, notifier, sample_agent_data, sample_escalation_data):
        """Test building notification context from escalation data"""
        context = notifier._build_notification_context(
            sample_escalation_data,
            sample_agent_data
        )
        
        assert context['customer_name'] == "Jane Customer"
        assert context['priority'] == "HIGH"
        assert context['escalation_type'] == "general"
        assert context['reason'] == "Customer requested human agent"
        assert 'conversation_preview' in context
        assert 'dashboard_url' in context
    
    @pytest.mark.asyncio
    async def test_track_notification_success(self, notifier):
        """Test notification tracking in database"""
        await notifier._track_notification(
            escalation_id="test-escalation-id",
            tenant_id="test-tenant-id",
            channel="email",
            recipient="test@example.com",
            success=True
        )
        
        # Verify database insert was called
        notifier.db.table.assert_called_with("escalation_notifications")
    
    @pytest.mark.asyncio
    async def test_track_notification_with_error(self, notifier):
        """Test notification tracking with error message"""
        await notifier._track_notification(
            escalation_id="test-escalation-id",
            tenant_id="test-tenant-id",
            channel="email",
            recipient="test@example.com",
            success=False,
            error_message="SMTP connection failed",
            retry_count=2
        )
        
        # Verify database insert was called
        notifier.db.table.assert_called_with("escalation_notifications")
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, notifier, sample_agent_data, sample_escalation_data):
        """Test retry logic with exponential backoff"""
        context = notifier._build_notification_context(
            sample_escalation_data,
            sample_agent_data
        )
        
        # Mock _send_email to fail first 2 times, succeed on 3rd
        call_count = 0
        async def mock_send_email(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return False
            return True
        
        with patch.object(notifier, '_send_email', side_effect=mock_send_email):
            with patch('asyncio.sleep'):  # Speed up test by mocking sleep
                success, error = await notifier._send_with_retry(
                    NotificationChannel.EMAIL,
                    sample_agent_data,
                    context,
                    "test-escalation-id",
                    "test-tenant-id",
                    max_retries=3
                )
        
        assert success is True
        assert call_count == 3  # Should have tried 3 times
    
    @pytest.mark.asyncio
    async def test_get_agent_notification_channels(self, notifier):
        """Test determining notification channels for agent"""
        agent_data = {
            "email": "test@example.com",
            "phone_number": "+60123456789",
            "notification_preferences": ["email", "sms"]
        }
        
        channels = notifier._get_agent_notification_channels(agent_data)
        
        assert NotificationChannel.EMAIL in channels
        assert NotificationChannel.SMS in channels
        assert NotificationChannel.WHATSAPP not in channels
    
    @pytest.mark.asyncio
    async def test_no_email_address_handling(self, notifier, sample_escalation_data):
        """Test handling when agent has no email address"""
        agent_data = {
            "agent_name": "John Doe"
            # No email field
        }
        
        context = notifier._build_notification_context(
            sample_escalation_data,
            agent_data
        )
        
        result = await notifier._send_email(agent_data, context)
        assert result is False  # Should fail without email
    
    @pytest.mark.asyncio
    async def test_dashboard_url_generation(self, notifier):
        """Test dashboard URL generation"""
        url = notifier._get_dashboard_url("test-escalation-123")
        assert "test-escalation-123" in url
        assert "escalations" in url
    
    @pytest.mark.asyncio
    async def test_conversation_preview(self, notifier, sample_escalation_data):
        """Test conversation preview extraction"""
        preview = notifier._get_conversation_preview(sample_escalation_data)
        
        assert "Customer: I need help" in preview
        assert "Bot: I can help" in preview
        assert "Customer: I want to speak to a human" in preview


# Integration-like tests (require environment setup)
class TestEscalationNotifierIntegration:
    """Integration tests (only run if environment variables are set)"""
    
    @pytest.mark.skipif(
        not os.getenv("SMTP_USER"),
        reason="SMTP credentials not configured"
    )
    @pytest.mark.asyncio
    async def test_real_email_send(self, notifier, sample_agent_data, sample_escalation_data):
        """Test actual email sending (requires real SMTP credentials)"""
        context = notifier._build_notification_context(
            sample_escalation_data,
            sample_agent_data
        )
        
        # This will actually send an email if credentials are set
        result = await notifier._send_email(sample_agent_data, context)
        assert result is True
    
    @pytest.mark.skipif(
        not os.getenv("TWILIO_ACCOUNT_SID"),
        reason="Twilio credentials not configured"
    )
    @pytest.mark.asyncio
    async def test_real_sms_send(self, notifier, sample_agent_data, sample_escalation_data):
        """Test actual SMS sending (requires real Twilio credentials)"""
        context = notifier._build_notification_context(
            sample_escalation_data,
            sample_agent_data
        )
        
        # This will actually send an SMS if credentials are set
        result = await notifier._send_sms(sample_agent_data, context)
        assert result is True
