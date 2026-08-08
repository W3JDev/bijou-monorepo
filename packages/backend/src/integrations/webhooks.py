#!/usr/bin/env python3
"""
Webhook Notification System for Bijou AI
========================================

Production-ready webhook system for owner notifications via Slack, Discord, and WhatsApp.
Supports urgent escalations, system alerts, and business metrics.

Author: W3J Bijou AI
Version: 2.1.0
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

import aiohttp
import requests


class NotificationPriority(Enum):
    """Notification priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """Supported notification channels"""

    SLACK = "slack"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class NotificationConfig:
    """Configuration for notification channels"""

    channel: NotificationChannel
    webhook_url: str
    enabled: bool = True
    priority_threshold: NotificationPriority = NotificationPriority.NORMAL
    retry_attempts: int = 3
    timeout: int = 10


class WebhookNotificationSystem:
    """
    Multi-channel notification system for production alerts
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.configs: Dict[NotificationChannel, NotificationConfig] = {}
        self.owner_whatsapp = os.getenv("OWNER_WHATSAPP_JID", "")
        if not self.owner_whatsapp:
            logger.warning("⚠️ OWNER_WHATSAPP_JID not set - owner notifications disabled")

        # Load configurations from environment
        self._load_configurations()

    def _load_configurations(self):
        """Load webhook configurations from environment variables"""

        # Slack configuration
        slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        if slack_webhook:
            self.configs[NotificationChannel.SLACK] = NotificationConfig(
                channel=NotificationChannel.SLACK,
                webhook_url=slack_webhook,
                enabled=os.getenv("SLACK_NOTIFICATIONS_ENABLED", "true").lower()
                == "true",
                priority_threshold=NotificationPriority(
                    os.getenv("SLACK_PRIORITY_THRESHOLD", "normal")
                ),
            )

        # Discord configuration
        discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        if discord_webhook:
            self.configs[NotificationChannel.DISCORD] = NotificationConfig(
                channel=NotificationChannel.DISCORD,
                webhook_url=discord_webhook,
                enabled=os.getenv("DISCORD_NOTIFICATIONS_ENABLED", "true").lower()
                == "true",
                priority_threshold=NotificationPriority(
                    os.getenv("DISCORD_PRIORITY_THRESHOLD", "high")
                ),
            )

        # Custom webhook configuration
        custom_webhook = os.getenv("CUSTOM_WEBHOOK_URL")
        if custom_webhook:
            self.configs[NotificationChannel.WEBHOOK] = NotificationConfig(
                channel=NotificationChannel.WEBHOOK,
                webhook_url=custom_webhook,
                enabled=os.getenv("CUSTOM_WEBHOOK_ENABLED", "true").lower() == "true",
                priority_threshold=NotificationPriority(
                    os.getenv("CUSTOM_WEBHOOK_PRIORITY_THRESHOLD", "normal")
                ),
            )

    def get_priority_emoji(self, priority: NotificationPriority) -> str:
        """Get emoji for priority level"""
        priority_emojis = {
            NotificationPriority.LOW: "💙",
            NotificationPriority.NORMAL: "📢",
            NotificationPriority.HIGH: "⚠️",
            NotificationPriority.URGENT: "🚨",
            NotificationPriority.CRITICAL: "🔥",
        }
        return priority_emojis.get(priority, "📢")

    def should_notify(
        self, channel: NotificationChannel, priority: NotificationPriority
    ) -> bool:
        """Check if notification should be sent based on priority threshold"""
        config = self.configs.get(channel)
        if not config or not config.enabled:
            return False

        # Priority hierarchy: CRITICAL > URGENT > HIGH > NORMAL > LOW
        priority_levels = {
            NotificationPriority.LOW: 0,
            NotificationPriority.NORMAL: 1,
            NotificationPriority.HIGH: 2,
            NotificationPriority.URGENT: 3,
            NotificationPriority.CRITICAL: 4,
        }

        return priority_levels[priority] >= priority_levels[config.priority_threshold]

    async def send_slack_notification(
        self,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Send notification to Slack"""

        config = self.configs.get(NotificationChannel.SLACK)
        if not config or not self.should_notify(NotificationChannel.SLACK, priority):
            return False

        emoji = self.get_priority_emoji(priority)

        # Slack webhook payload
        payload = {
            "text": f"{emoji} *Bijou AI Alert*",
            "attachments": [
                {
                    "color": self._get_priority_color(priority),
                    "fields": [
                        {
                            "title": f"{priority.value.upper()} Alert",
                            "value": message,
                            "short": False,
                        },
                        {
                            "title": "Timestamp",
                            "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True,
                        },
                    ],
                }
            ],
        }

        if metadata:
            for key, value in metadata.items():
                payload["attachments"][0]["fields"].append(
                    {
                        "title": key.replace("_", " ").title(),
                        "value": str(value),
                        "short": True,
                    }
                )

        return await self._send_webhook_request(config, payload)

    async def send_discord_notification(
        self,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Send notification to Discord"""

        config = self.configs.get(NotificationChannel.DISCORD)
        if not config or not self.should_notify(NotificationChannel.DISCORD, priority):
            return False

        emoji = self.get_priority_emoji(priority)

        # Discord webhook payload
        embed = {
            "title": f"{emoji} Bijou AI Alert",
            "description": message,
            "color": self._get_priority_color_int(priority),
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {"name": "Priority", "value": priority.value.upper(), "inline": True}
            ],
        }

        if metadata:
            for key, value in metadata.items():
                embed["fields"].append(
                    {
                        "name": key.replace("_", " ").title(),
                        "value": str(value),
                        "inline": True,
                    }
                )

        payload = {"embeds": [embed]}

        return await self._send_webhook_request(config, payload)

    async def send_custom_webhook_notification(
        self,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Send notification to custom webhook"""

        config = self.configs.get(NotificationChannel.WEBHOOK)
        if not config or not self.should_notify(NotificationChannel.WEBHOOK, priority):
            return False

        # Generic webhook payload
        payload = {
            "alert_type": "bijou_ai_notification",
            "message": message,
            "priority": priority.value,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        return await self._send_webhook_request(config, payload)

    async def _send_webhook_request(
        self, config: NotificationConfig, payload: Dict
    ) -> bool:
        """Send webhook request with retries"""

        for attempt in range(config.retry_attempts):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=config.timeout)
                ) as session:
                    async with session.post(
                        config.webhook_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    ) as response:
                        if response.status < 400:
                            self.logger.info(
                                f"Webhook notification sent successfully to {config.channel.value}"
                            )
                            return True
                        else:
                            self.logger.warning(
                                f"Webhook failed with status {response.status} on attempt {attempt + 1}"
                            )

            except Exception as e:
                self.logger.error(f"Webhook error on attempt {attempt + 1}: {e}")

            # Wait before retry (exponential backoff)
            if attempt < config.retry_attempts - 1:
                await asyncio.sleep(2**attempt)

        self.logger.error(
            f"Failed to send webhook notification after {config.retry_attempts} attempts"
        )
        return False

    def _get_priority_color(self, priority: NotificationPriority) -> str:
        """Get color hex code for priority (Slack format)"""
        colors = {
            NotificationPriority.LOW: "#36a64f",  # Green
            NotificationPriority.NORMAL: "#2196F3",  # Blue
            NotificationPriority.HIGH: "#ff9800",  # Orange
            NotificationPriority.URGENT: "#f44336",  # Red
            NotificationPriority.CRITICAL: "#9c27b0",  # Purple
        }
        return colors.get(priority, "#2196F3")

    def _get_priority_color_int(self, priority: NotificationPriority) -> int:
        """Get color integer for priority (Discord format)"""
        colors = {
            NotificationPriority.LOW: 3581519,  # Green
            NotificationPriority.NORMAL: 2196243,  # Blue
            NotificationPriority.HIGH: 16753920,  # Orange
            NotificationPriority.URGENT: 15951670,  # Red
            NotificationPriority.CRITICAL: 10239155,  # Purple
        }
        return colors.get(priority, 2196243)

    async def notify_owner(
        self,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[NotificationChannel]] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[NotificationChannel, bool]:
        """
        Send notification to owner via configured channels

        Args:
            message: Alert message
            priority: Notification priority level
            channels: Specific channels to use (default: all configured)
            metadata: Additional data to include

        Returns:
            Dict of channel success status
        """

        if channels is None:
            channels = list(self.configs.keys())

        results = {}

        # Send to each channel concurrently
        tasks = []

        for channel in channels:
            if channel == NotificationChannel.SLACK:
                tasks.append(self.send_slack_notification(message, priority, metadata))
            elif channel == NotificationChannel.DISCORD:
                tasks.append(
                    self.send_discord_notification(message, priority, metadata)
                )
            elif channel == NotificationChannel.WEBHOOK:
                tasks.append(
                    self.send_custom_webhook_notification(message, priority, metadata)
                )

        if tasks:
            channel_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, channel in enumerate([ch for ch in channels if ch in self.configs]):
                results[channel] = (
                    not isinstance(channel_results[i], Exception) and channel_results[i]
                )

        return results

    async def notify_human_escalation(
        self,
        chat_jid: str,
        escalation_id: str,
        reason: str = "user_request",
        customer_info: Optional[Dict] = None,
    ) -> Dict[NotificationChannel, bool]:
        """Send urgent notification for human escalation"""

        message = f"""🆘 **HUMAN ESCALATION REQUESTED**

**Chat:** {chat_jid}
**Escalation ID:** {escalation_id}
**Reason:** {reason}
**Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Please take over this conversation immediately."""

        metadata = {
            "escalation_id": escalation_id,
            "chat_jid": chat_jid,
            "reason": reason,
        }

        if customer_info:
            metadata.update(customer_info)

        return await self.notify_owner(
            message=message, priority=NotificationPriority.URGENT, metadata=metadata
        )

    async def notify_system_alert(
        self,
        alert_type: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.HIGH,
        system_info: Optional[Dict] = None,
    ) -> Dict[NotificationChannel, bool]:
        """Send system alert notification"""

        formatted_message = f"""⚠️ **SYSTEM ALERT: {alert_type.upper()}**

{message}

**Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""

        metadata = {
            "alert_type": alert_type,
            "system_timestamp": datetime.utcnow().isoformat(),
        }

        if system_info:
            metadata.update(system_info)

        return await self.notify_owner(
            message=formatted_message, priority=priority, metadata=metadata
        )

    async def notify_business_metrics(
        self,
        metrics: Dict,
        period: str = "daily",
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> Dict[NotificationChannel, bool]:
        """Send business metrics summary"""

        message = f"""📊 **BUSINESS METRICS ({period.upper()})**

**Messages Processed:** {metrics.get("messages_processed", 0)}
**Human Escalations:** {metrics.get("escalations", 0)}
**Active Tenants:** {metrics.get("active_tenants", 0)}
**Success Rate:** {metrics.get("success_rate", 0):.1f}%
**Average Response Time:** {metrics.get("avg_response_time", 0):.2f}s

**Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""

        return await self.notify_owner(
            message=message, priority=priority, metadata=metrics
        )

    def get_webhook_health_check(self) -> Dict:
        """Get health status of all configured webhooks"""

        health_status = {"timestamp": datetime.utcnow().isoformat(), "channels": {}}

        for channel, config in self.configs.items():
            health_status["channels"][channel.value] = {
                "enabled": config.enabled,
                "webhook_configured": bool(config.webhook_url),
                "priority_threshold": config.priority_threshold.value,
            }

        return health_status


# Production webhook system instance
webhook_system = WebhookNotificationSystem()


# Convenience functions for common use cases
async def notify_escalation(
    chat_jid: str, escalation_id: str, reason: str = "user_request"
) -> bool:
    """Quick escalation notification"""
    results = await webhook_system.notify_human_escalation(
        chat_jid, escalation_id, reason
    )
    return any(results.values())


async def notify_system_error(
    error_message: str, error_details: Optional[Dict] = None
) -> bool:
    """Quick system error notification"""
    results = await webhook_system.notify_system_alert(
        alert_type="system_error",
        message=error_message,
        priority=NotificationPriority.CRITICAL,
        system_info=error_details,
    )
    return any(results.values())


async def notify_tenant_offline(tenant_id: str, reason: str = "unknown") -> bool:
    """Quick tenant offline notification"""
    results = await webhook_system.notify_system_alert(
        alert_type="tenant_offline",
        message=f"Tenant {tenant_id} has gone offline. Reason: {reason}",
        priority=NotificationPriority.HIGH,
        system_info={"tenant_id": tenant_id, "reason": reason},
    )
    return any(results.values())


if __name__ == "__main__":
    """Test webhook system"""
    import asyncio

    async def test_webhooks():
        print("🧪 Testing Webhook Notification System")
        print("=" * 50)

        # Test health check
        health = webhook_system.get_webhook_health_check()
        print(f"Health Status: {json.dumps(health, indent=2)}")

        # Test escalation notification
        print("\nTesting escalation notification...")
        results = await notify_escalation(
            "test_customer@s.whatsapp.net", "ESC-TEST-123", "testing_system"
        )
        print(f"Escalation notification result: {results}")

        # Test system alert
        print("\nTesting system alert...")
        results = await notify_system_error(
            "Test system error for webhook validation",
            {"component": "webhook_test", "severity": "test"},
        )
        print(f"System alert result: {results}")

        print("\n✅ Webhook system test completed!")

    asyncio.run(test_webhooks())
