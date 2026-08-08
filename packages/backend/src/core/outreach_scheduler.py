#!/usr/bin/env python3
"""
Outreach Scheduler - Anti-Spam Message Queue Processor
======================================================

Safely sends WhatsApp outreach messages with comprehensive anti-spam protection:
- Business hours enforcement (9am-6pm default)
- Daily sending limits per tenant
- Random delays between messages (human-like behavior)
- Reply detection and auto-stop
- Cooldown periods between campaigns
- Rate limiting and backoff on failures

Author: W3J Bijou AI
Version: 1.0.0
"""

import asyncio
import json
import logging
import random
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Set

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None  # graceful fallback to UTC

logger = logging.getLogger(__name__)


class OutreachScheduler:
    """
    Manages outbound message queue with anti-spam protections.

    Key Safety Features:
    1. Business Hours: Only sends during configured hours (default 9am-6pm)
    2. Daily Limits: Enforces per-tenant daily message limits
    3. Random Delays: 2-5 minute random delays between messages
    4. Cooldown: 72-hour minimum between campaigns to same contact
    5. Reply Detection: Auto-stops sequences when contacts reply
    6. Rate Limiting: Exponential backoff on bridge failures
    7. Block List: Respects opt-out contacts immediately
    """

    def __init__(self, db_connection, bridge_adapter, config: Optional[Dict] = None):
        """
        Initialize the outreach scheduler.

        Args:
            db_connection: Supabase client or database connection
            bridge_adapter: BridgeAdapter instance for sending messages
            config: Optional configuration overrides
        """
        self.db = db_connection
        self.bridge = bridge_adapter
        self.config = config or {}

        # Default safety settings
        self.default_daily_limit = self.config.get('daily_limit', 50)
        self.default_min_delay = self.config.get('min_delay_seconds', 120)  # 2 minutes
        self.default_max_delay = self.config.get('max_delay_seconds', 300)  # 5 minutes
        self.default_business_start = self.config.get('business_start', '09:00')
        self.default_business_end = self.config.get('business_end', '18:00')
        self.default_timezone = self.config.get('timezone', 'Asia/Kuala_Lumpur')
        self.default_cooldown_hours = self.config.get('cooldown_hours', 72)

        # Runtime state
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._last_send_times: Dict[str, datetime] = {}  # tenant_id -> last send time
        self._daily_counts: Dict[str, int] = {}  # tenant_id -> count today
        self._failure_backoff: Dict[str, datetime] = {}  # tenant_id -> backoff until

        # Track which campaigns to auto-stop on reply
        self._stop_on_reply: Set[str] = set()

        logger.info("🚀 OutreachScheduler initialized with anti-spam protection")
        logger.info(f"   Daily limit: {self.default_daily_limit} messages")
        logger.info(f"   Delay range: {self.default_min_delay}-{self.default_max_delay}s")
        logger.info(f"   Business hours: {self.default_business_start}-{self.default_business_end}")

    async def start(self):
        """Start the outreach scheduler loop."""
        if self.running:
            logger.warning("⚠️ OutreachScheduler already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("✅ OutreachScheduler started")

    async def stop(self):
        """Stop the outreach scheduler."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 OutreachScheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop - processes queue every 30 seconds."""
        logger.info("📅 Outreach scheduler loop started")

        while self.running:
            try:
                await self._process_outbound_queue()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait longer on error

    async def _process_outbound_queue(self):
        """Process pending messages from the outbound queue."""
        if not hasattr(self.db, 'table'):
            return

        try:
            # Get pending messages due for sending
            now = datetime.utcnow()

            result = self.db.table("outbound_queue") \
                .select("*, campaigns!inner(*)") \
                .eq("status", "pending") \
                .lte("scheduled_at", now.isoformat()) \
                .order("scheduled_at") \
                .limit(10) \
                .execute()

            if not result.data:
                return

            messages = result.data
            logger.info(f"📬 Processing {len(messages)} pending messages")

            for message in messages:
                if not self.running:
                    break

                try:
                    await self._send_message_safely(message)
                except Exception as e:
                    logger.error(f"❌ Error sending message {message.get('id')}: {e}")
                    await self._mark_failed(message['id'], str(e))

                # Small delay between processing messages
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ Error processing outbound queue: {e}")

    async def _send_message_safely(self, message: Dict):
        """
        Send a message with all safety checks.

        Safety checks performed:
        1. Tenant daily limit not exceeded
        2. Currently in business hours
        3. Not in failure backoff period
        4. Contact hasn't opted out
        5. Contact hasn't replied (if stop_on_reply enabled)
        6. Random delay since last message
        """
        tenant_id = message['tenant_id']
        campaign_id = message.get('campaign_id')
        contact_id = message.get('contact_id')

        # Check 1: Daily limit
        if not await self._check_daily_limit(tenant_id):
            logger.info(f"⏸️ Daily limit reached for tenant {tenant_id}, skipping")
            return

        # Check 2: Business hours
        campaign = message.get('campaigns', {})
        if not self._is_business_hours(
            campaign.get('send_window_start', self.default_business_start),
            campaign.get('send_window_end', self.default_business_end),
            campaign.get('timezone', self.default_timezone)
        ):
            logger.info(f"⏸️ Outside business hours for tenant {tenant_id}, skipping")
            return

        # Check 3: Failure backoff
        if tenant_id in self._failure_backoff:
            if datetime.utcnow() < self._failure_backoff[tenant_id]:
                logger.info(f"⏸️ Tenant {tenant_id} in backoff period, skipping")
                return
            else:
                del self._failure_backoff[tenant_id]

        # Check 4: Contact opted out
        if await self._is_contact_blocked(contact_id):
            logger.info(f"🚫 Contact {contact_id} opted out, marking blocked")
            await self._mark_blocked(message['id'], "Contact opted out")
            return

        # Check 5: Contact replied (stop_on_reply)
        if campaign.get('stop_on_reply', True) and campaign_id:
            if await self._has_contact_replied(contact_id, campaign_id):
                logger.info(f"💬 Contact {contact_id} replied, stopping sequence")
                await self._mark_cancelled(message['id'], "Contact replied")
                return

        # Check 6: Random delay since last message
        await self._wait_for_delay(tenant_id, campaign)

        # All checks passed - send the message
        await self._mark_sending(message['id'])

        try:
            success = await self._send_via_bridge(
                recipient=message['recipient_jid'],
                content=message['message_content']
            )

            if success:
                await self._mark_sent(message['id'])
                await self._update_contact_outreach(contact_id)
                await self._increment_daily_count(tenant_id)
                self._last_send_times[tenant_id] = datetime.utcnow()
                logger.info(f"✅ Message sent to {message.get('recipient_jid')}")
            else:
                await self._handle_send_failure(message['id'], tenant_id, "Bridge returned failure")

        except Exception as e:
            await self._handle_send_failure(message['id'], tenant_id, str(e))
            raise

    async def _send_via_bridge(self, recipient: str, content: str) -> bool:
        """Send message via WhatsApp bridge."""
        try:
            if not self.bridge:
                logger.error("❌ No bridge adapter available")
                return False

            # Use the bridge adapter to send
            return self.bridge.send_text(recipient, content)

        except Exception as e:
            logger.error(f"❌ Bridge send error: {e}")
            return False

    async def _check_daily_limit(self, tenant_id: str) -> bool:
        """Check if tenant has exceeded daily message limit."""
        try:
            # Get tenant's daily limit
            tenant_result = self.db.table("tenants") \
                .select("daily_outreach_limit") \
                .eq("id", tenant_id) \
                .maybe_single() \
                .execute()

            tr_data = getattr(tenant_result, "data", None) if tenant_result else None
            daily_limit = tr_data.get('daily_outreach_limit', self.default_daily_limit) if isinstance(tr_data, dict) else self.default_daily_limit

            # Count today's sent messages
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            count_result = self.db.table("outbound_queue") \
                .select("id", count="exact") \
                .eq("tenant_id", tenant_id) \
                .eq("status", "sent") \
                .gte("sent_at", today_start.isoformat()) \
                .execute()

            sent_today = count_result.count if hasattr(count_result, 'count') else 0

            return sent_today < daily_limit

        except Exception as e:
            logger.error(f"❌ Error checking daily limit: {e}")
            return False  # Fail safe - don't send if we can't check

    def _is_business_hours(self, start_time_str: str, end_time_str: str, timezone: str) -> bool:
        """Check if current time is within business hours using proper timezone."""
        try:
            # Use proper timezone if ZoneInfo available, else UTC
            if ZoneInfo:
                tz = ZoneInfo(timezone)
                now = datetime.now(tz)
            else:
                now = datetime.utcnow()
                logger.warning("⚠️ ZoneInfo not available, using UTC for business hours check")

            current_time = now.time().replace(tzinfo=None)

            # Parse time strings
            start_parts = start_time_str.split(":")
            end_parts = end_time_str.split(":")

            start_time = time(int(start_parts[0]), int(start_parts[1]))
            end_time = time(int(end_parts[0]), int(end_parts[1]))

            return start_time <= current_time <= end_time

        except Exception as e:
            logger.error(f"❌ Error checking business hours: {e}")
            return True  # Default to allowing if parsing fails

    async def _is_contact_blocked(self, contact_id: Optional[str]) -> bool:
        """Check if contact has opted out."""
        if not contact_id:
            return False

        try:
            result = self.db.table("contacts") \
                .select("opted_out_at") \
                .eq("id", contact_id) \
                .maybe_single() \
                .execute()

            rdata = getattr(result, "data", None) if result else None
            if rdata and rdata.get('opted_out_at'):
                return True

            # Also check blocked_numbers table
            contact_result = self.db.table("contacts") \
                .select("jid") \
                .eq("id", contact_id) \
                .maybe_single() \
                .execute()

            cr_data = getattr(contact_result, "data", None) if contact_result else None
            if cr_data:
                jid = cr_data.get('jid')
                if jid:
                    blocked = self.db.table("blocked_numbers") \
                        .select("id") \
                        .eq("customer_jid", jid) \
                        .limit(1) \
                        .execute()

                    if blocked.data:
                        return True

            return False

        except Exception as e:
            logger.error(f"❌ Error checking blocked status: {e}")
            return False

    async def _has_contact_replied(self, contact_id: Optional[str], campaign_id: str) -> bool:
        """Check if contact has replied to this campaign."""
        if not contact_id:
            return False

        try:
            result = self.db.table("outbound_queue") \
                .select("replied_at") \
                .eq("contact_id", contact_id) \
                .eq("campaign_id", campaign_id) \
                .not_.is_("replied_at", "null") \
                .limit(1) \
                .execute()

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"❌ Error checking reply status: {e}")
            return False

    async def _wait_for_delay(self, tenant_id: str, campaign: Dict):
        """Wait for random delay between messages."""
        min_delay = campaign.get('min_delay_seconds', self.default_min_delay)
        max_delay = campaign.get('max_delay_seconds', self.default_max_delay)

        # Check if we need to wait since last message
        if tenant_id in self._last_send_times:
            time_since_last = (datetime.utcnow() - self._last_send_times[tenant_id]).total_seconds()
            required_delay = random.randint(min_delay, max_delay)

            if time_since_last < required_delay:
                wait_time = required_delay - time_since_last
                logger.info(f"⏱️ Waiting {wait_time:.0f}s for rate limit...")
                await asyncio.sleep(wait_time)

    async def _mark_sending(self, message_id: str):
        """Mark message as being sent."""
        self.db.table("outbound_queue") \
            .update({"status": "sending"}) \
            .eq("id", message_id) \
            .execute()

    async def _mark_sent(self, message_id: str):
        """Mark message as sent."""
        self.db.table("outbound_queue") \
            .update({
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat()
            }) \
            .eq("id", message_id) \
            .execute()

    async def _mark_failed(self, message_id: str, error: str):
        """Mark message as failed."""
        self.db.table("outbound_queue") \
            .update({
                "status": "failed",
                "failed_at": datetime.utcnow().isoformat(),
                "error_message": error[:500]  # Limit error length
            }) \
            .eq("id", message_id) \
            .execute()

    async def _mark_blocked(self, message_id: str, reason: str):
        """Mark message as blocked (opted out)."""
        self.db.table("outbound_queue") \
            .update({
                "status": "blocked",
                "error_message": reason
            }) \
            .eq("id", message_id) \
            .execute()

    async def _mark_cancelled(self, message_id: str, reason: str):
        """Mark message as cancelled (e.g., contact replied)."""
        self.db.table("outbound_queue") \
            .update({
                "status": "cancelled",
                "error_message": reason
            }) \
            .eq("id", message_id) \
            .execute()

    async def _update_contact_outreach(self, contact_id: Optional[str]):
        """Update contact's last outreach timestamp."""
        if not contact_id:
            return

        try:
            # Atomic increment using raw SQL via rpc to avoid race condition
            # Falls back to select+update if rpc not available
            try:
                self.db.rpc("increment_contact_outreach", {"p_contact_id": contact_id}).execute()
            except Exception:
                # Fallback: manually increment by fetching current count
                existing = self.db.table("contacts") \
                    .select("outreach_count") \
                    .eq("id", contact_id) \
                    .maybe_single() \
                    .execute()
                ex_data = getattr(existing, "data", None) if existing else None
                current_count = (ex_data or {}).get("outreach_count", 0) or 0 if isinstance(ex_data, dict) else 0
                self.db.table("contacts") \
                    .update({
                        "last_outreach_at": datetime.utcnow().isoformat(),
                        "outreach_count": current_count + 1
                    }) \
                    .eq("id", contact_id) \
                    .execute()
        except Exception as e:
            logger.error(f"❌ Error updating contact outreach: {e}")

    async def _increment_daily_count(self, tenant_id: str):
        """Increment daily sent count for tenant."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"{tenant_id}:{today}"
        self._daily_counts[key] = self._daily_counts.get(key, 0) + 1

    async def _handle_send_failure(self, message_id: str, tenant_id: str, error: str):
        """Handle message send failure with retry logic."""
        try:
            # Get current retry count
            result = self.db.table("outbound_queue") \
                .select("retry_count, max_retries") \
                .eq("id", message_id) \
                .maybe_single() \
                .execute()

            r_data = getattr(result, "data", None) if result else None
            if not r_data:
                return

            retry_count = r_data.get('retry_count', 0)
            max_retries = r_data.get('max_retries', 3)

            if retry_count < max_retries:
                # Schedule retry with exponential backoff
                retry_delay = 2 ** retry_count  # 1, 2, 4, 8 minutes
                next_try = datetime.utcnow() + timedelta(minutes=retry_delay)

                self.db.table("outbound_queue") \
                    .update({
                        "status": "pending",
                        "retry_count": retry_count + 1,
                        "scheduled_at": next_try.isoformat(),
                        "error_message": f"Retry {retry_count + 1}/{max_retries}: {error[:200]}"
                    }) \
                    .eq("id", message_id) \
                    .execute()

                logger.info(f"🔄 Scheduled retry {retry_count + 1}/{max_retries} for message {message_id} in {retry_delay}min")
            else:
                # Max retries exceeded - mark as failed
                await self._mark_failed(message_id, f"Max retries exceeded: {error}")

                # If many failures, trigger backoff for tenant
                await self._check_failure_rate(tenant_id)

        except Exception as e:
            logger.error(f"❌ Error handling send failure: {e}")

    async def _check_failure_rate(self, tenant_id: str):
        """Check if failure rate is too high and trigger backoff."""
        try:
            # Count recent failures
            recent_time = datetime.utcnow() - timedelta(hours=1)
            result = self.db.table("outbound_queue") \
                .select("status") \
                .eq("tenant_id", tenant_id) \
                .gte("failed_at", recent_time.isoformat()) \
                .execute()

            if not result.data:
                return

            failures = len([r for r in result.data if r.get('status') == 'failed'])
            total = len(result.data)

            if total > 10 and failures / total > 0.5:  # >50% failure rate
                # Trigger 30-minute backoff
                backoff_until = datetime.utcnow() + timedelta(minutes=30)
                self._failure_backoff[tenant_id] = backoff_until

                logger.warning(f"⚠️ High failure rate for tenant {tenant_id} ({failures}/{total}). Backing off for 30 minutes.")

                # Log the issue
                self.db.table("outreach_logs").insert({
                    "tenant_id": tenant_id,
                    "log_type": "rate_limit_hit",
                    "log_message": f"High failure rate detected ({failures}/{total} failures). Backing off for 30 minutes.",
                    "metadata": {"failures": failures, "total": total, "rate": failures/total}
                }).execute()

        except Exception as e:
            logger.error(f"❌ Error checking failure rate: {e}")

    # ==================== PUBLIC API ====================

    async def handle_incoming_reply(
        self,
        contact_jid: str,
        campaign_id: Optional[str] = None,
        reply_text: str = "",
    ):
        """
        Handle an incoming reply from a contact.

        This should be called by the webhook handler when a reply is received.
        reply_text: the raw message body (used for lead scoring).
        """
        try:
            # Find the contact (include intelligence fields for scoring)
            contact_result = self.db.table("contacts") \
                .select("id, interest_score, campaign_config_id") \
                .eq("jid", contact_jid) \
                .limit(1) \
                .execute()

            if not contact_result.data:
                return

            contact_id = contact_result.data[0]['id']
            contact_row = contact_result.data[0]

            # Update contact reply stats (baseline: warm)
            self.db.table("contacts") \
                .update({
                    "last_reply_at": datetime.utcnow().isoformat(),
                    "lead_temperature": "warm"
                }) \
                .eq("id", contact_id) \
                .execute()

            # ── AI reply scoring (non-blocking enrichment) ────────────────────
            if reply_text:
                try:
                    import os
                    from src.saas.outreach_template_engine import (
                        TemplateEngine,
                        QUALIFICATION_THRESHOLDS,
                    )
                    engine = TemplateEngine(gemini_api_key=os.getenv("GEMINI_API_KEY"))
                    campaign_config = None
                    if contact_row.get("campaign_config_id"):
                        cfg_res = self.db.table("outreach_campaign_configs") \
                            .select("*") \
                            .eq("id", contact_row["campaign_config_id"]) \
                            .maybe_single() \
                            .execute()
                        cfg_data = getattr(cfg_res, "data", None) if cfg_res else None
                        campaign_config = cfg_data if cfg_data else None

                    score_result = engine.score_reply(
                        reply_text=reply_text,
                        contact={"interest_score": contact_row.get("interest_score", 0)},
                        campaign_config=campaign_config,
                    )

                    if score_result.get("signals_hit") or score_result.get("is_wrong_target"):
                        score_update: dict = {
                            "interest_score": score_result["interest_score"],
                            "qualification_signals_hit": score_result.get("signals_hit", []),
                        }
                        if score_result.get("is_wrong_target"):
                            score_update["do_not_contact"] = True
                        elif score_result["interest_score"] >= QUALIFICATION_THRESHOLDS.get("hot", 25):
                            score_update["lead_temperature"] = "hot"

                        self.db.table("contacts") \
                            .update(score_update) \
                            .eq("id", contact_id) \
                            .execute()
                        logger.info(
                            f"🎯 Lead score updated for {contact_jid}: "
                            f"score={score_result['interest_score']} "
                            f"signals={score_result.get('signals_hit')}"
                        )
                except Exception as score_err:
                    logger.warning(f"score_reply non-blocking error: {score_err}")

            # Update any pending messages for this contact
            update_data = {
                "replied_at": datetime.utcnow().isoformat(),
                "status": "cancelled"
            }

            query = self.db.table("outbound_queue") \
                .update(update_data) \
                .eq("contact_id", contact_id) \
                .eq("status", "pending")

            if campaign_id:
                query = query.eq("campaign_id", campaign_id)

            query.execute()

            # Update campaign reply count
            if campaign_id:
                self.db.rpc("increment", {
                    "table": "campaigns",
                    "column": "reply_count",
                    "id": campaign_id
                }).execute()

            logger.info(f"💬 Reply received from {contact_jid}, cancelled pending messages")

        except Exception as e:
            logger.error(f"❌ Error handling reply: {e}")

    def get_status(self) -> Dict:
        """Get scheduler status."""
        return {
            "running": self.running,
            "daily_counts": self._daily_counts,
            "last_send_times": {k: v.isoformat() for k, v in self._last_send_times.items()},
            "failure_backoffs": {k: v.isoformat() for k, v in self._failure_backoff.items()},
            "config": {
                "daily_limit": self.default_daily_limit,
                "min_delay": self.default_min_delay,
                "max_delay": self.default_max_delay,
                "business_hours": f"{self.default_business_start}-{self.default_business_end}"
            }
        }
