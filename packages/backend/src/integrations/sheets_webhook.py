"""
Google Sheets AppScript Webhook Integration
Sends events to Google Sheets for customer management dashboard

ARCHITECTURE:
- Asynchronous webhook delivery (non-blocking)
- Graceful degradation (logs warnings but doesn't crash on failure)
- Multi-tenant support (includes tenant_id in all payloads)
- Event types: message.received, message.sent, escalation.created, customer.status_changed

USAGE:
    from src.integrations.sheets_webhook import sheets_webhook
    
    await sheets_webhook.send_message_event(
        tenant_id=tenant_id,
        customer_jid=chat_jid,
        customer_phone="+60123456789",
        customer_name="John Doe",
        message_id=msg_id,
        message_content="Hello",
        sender_type="customer",
        timestamp=datetime.utcnow().isoformat()
    )

ENVIRONMENT VARIABLES:
    SHEETS_WEBHOOK_URL: Google Apps Script web app URL (required)
    SHEETS_WEBHOOK_SECRET: Secret for authentication (optional but recommended)
"""

import logging
import os
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class SheetsWebhookSender:
    """Send events to Google Sheets AppScript webhook"""
    
    def __init__(self):
        self.webhook_url = os.getenv("SHEETS_WEBHOOK_URL")
        self.webhook_secret = os.getenv("SHEETS_WEBHOOK_SECRET")
        self.enabled = bool(self.webhook_url)
        
        if not self.enabled:
            logger.warning("⚠️ Sheets webhook disabled (SHEETS_WEBHOOK_URL not set)")
        else:
            logger.info(f"✅ Sheets webhook enabled: {self.webhook_url[:50]}...")
    
    def _get_webhook_url_with_secret(self) -> str:
        """
        Get webhook URL with secret as query parameter.
        Google Apps Script can't easily read HTTP headers, so we send the secret in the URL.
        """
        if not self.webhook_secret:
            return self.webhook_url
        
        separator = '&' if '?' in self.webhook_url else '?'
        return f"{self.webhook_url}{separator}X-Webhook-Secret={self.webhook_secret}"
    
    async def send_message_event(
        self,
        tenant_id: str,
        customer_jid: str,
        customer_phone: str,
        customer_name: str,
        message_id: str,
        message_content: str,
        sender_type: str,  # "customer" or "assistant"
        timestamp: str,
    ) -> bool:
        """
        Send message event to Google Sheets
        
        Args:
            tenant_id: UUID of tenant
            customer_jid: WhatsApp JID (e.g., 60123456789@s.whatsapp.net)
            customer_phone: Phone number (e.g., +60123456789)
            customer_name: Customer display name
            message_id: UUID of message
            message_content: Message text
            sender_type: "customer" or "assistant"
            timestamp: ISO format timestamp
        
        Returns:
            True if webhook sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Determine event type based on sender
            event_type = "message.received" if sender_type == "customer" else "message.sent"
            
            payload = {
                "event": event_type,
                "tenant_id": tenant_id,
                "customer": {
                    "jid": customer_jid,
                    "phone": customer_phone,
                    "name": customer_name,
                },
                "message": {
                    "id": message_id,
                    "content": message_content,
                    "sender": sender_type,
                    "timestamp": timestamp,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.post(
                    self._get_webhook_url_with_secret(),
                    json=payload,
                    headers=headers,
                )
                
                if response.status_code == 200:
                    logger.info(
                        f"✅ Sheets webhook sent: {event_type} | "
                        f"{customer_phone} | tenant={tenant_id[:8]}..."
                    )
                    return True
                else:
                    logger.warning(
                        f"⚠️ Sheets webhook failed: {response.status_code} - {response.text[:100]}"
                    )
                    return False
                    
        except httpx.TimeoutException as e:
            logger.error(f"❌ Sheets webhook timeout: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Sheets webhook error: {e}")
            return False
    
    async def send_status_change_event(
        self,
        tenant_id: str,
        customer_jid: str,
        customer_phone: str,
        old_status: str,
        new_status: str,
    ) -> bool:
        """
        Send customer status change event
        
        Args:
            tenant_id: UUID of tenant
            customer_jid: WhatsApp JID
            customer_phone: Phone number
            old_status: Previous status
            new_status: New status
        
        Returns:
            True if webhook sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            payload = {
                "event": "customer.status_changed",
                "tenant_id": tenant_id,
                "customer": {
                    "jid": customer_jid,
                    "phone": customer_phone,
                },
                "status": new_status,
                "old_status": old_status,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            headers = {"Content-Type": "application/json"}
            if self.webhook_secret:
                separator = 'headers["X-Webhook-Secret"] = self.webhook_secret' if '?' in self.webhook_url else '?'
                webhook_url_with_secret = f"{self.webhook_url}{separator}X-Webhook-Secret={self.webhook_secret}"
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.post(self._get_webhook_url_with_secret(), json=payload, headers=headers)
                
                if response.status_code == 200:
                    logger.info(
                        f"✅ Status change webhook sent: {customer_phone} | "
                        f"{old_status} → {new_status}"
                    )
                    return True
                else:
                    logger.warning(f"⚠️ Status webhook failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Status webhook error: {e}")
            return False
    
    async def send_escalation_event(
        self,
        tenant_id: str,
        customer_jid: str,
        customer_phone: str,
        customer_name: str,
        escalation_id: str,
        reason: str,
        priority: str,
    ) -> bool:
        """
        Send escalation created event
        
        Args:
            tenant_id: UUID of tenant
            customer_jid: WhatsApp JID
            customer_phone: Phone number
            customer_name: Customer display name
            escalation_id: UUID of escalation
            reason: Escalation reason
            priority: Escalation priority (low, normal, high, urgent)
        
        Returns:
            True if webhook sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            payload = {
                "event": "escalation.created",
                "tenant_id": tenant_id,
                "customer": {
                    "jid": customer_jid,
                    "phone": customer_phone,
                    "name": customer_name,
                },
                "reason": reason,
                "priority": priority,
                "escalation_id": escalation_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            headers = {"Content-Type": "application/json"}
            if self.webhook_secret:
                separator = 'headers["X-Webhook-Secret"] = self.webhook_secret' if '?' in self.webhook_url else '?'
                webhook_url_with_secret = f"{self.webhook_url}{separator}X-Webhook-Secret={self.webhook_secret}"
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.post(self._get_webhook_url_with_secret(), json=payload, headers=headers)
                
                if response.status_code == 200:
                    logger.info(
                        f"✅ Escalation webhook sent: {customer_phone} | "
                        f"priority={priority} | reason={reason[:50]}..."
                    )
                    return True
                else:
                    logger.warning(f"⚠️ Escalation webhook failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Escalation webhook error: {e}")
            return False


# Global instance (initialized once on module import)
sheets_webhook = SheetsWebhookSender()
