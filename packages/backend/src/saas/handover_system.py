"""
Bijou AI - Human Handover System
==================================

Intelligent human escalation queue for complex customer issues.

Features:
- Auto-detection of escalation triggers (frustration, complexity, explicit request)
- Priority-based queue management
- Agent assignment and routing
- SLA tracking
- Analytics and reporting

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Import Google Sheets webhook
try:
    from src.integrations.sheets_webhook import sheets_webhook
    SHEETS_WEBHOOK_AVAILABLE = True
except ImportError:
    sheets_webhook = None  # type: ignore
    SHEETS_WEBHOOK_AVAILABLE = False


class EscalationPriority(str, Enum):
    """Priority levels for escalations"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EscalationStatus(str, Enum):
    """Status of escalation"""

    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class HandoverSystem:
    """
    Manages human handover queue and escalations.

    Detects when AI should hand over to human agent and manages the queue.
    """

    def __init__(
        self,
        supabase_client=None,
        memory_system=None,
        send_message_callback=None,
    ):
        """
        Initialize handover system.

        Args:
            supabase_client: Supabase client for queue storage
            memory_system: ConversationMemory instance
            send_message_callback: Function to send WhatsApp messages
        """
        self.supabase = supabase_client
        self.memory = memory_system
        self.send_message = send_message_callback

        # Feature flag
        self.enabled = os.getenv("ENABLE_HANDOVER_QUEUE", "false").lower() == "true"

        # SLA times (in minutes)
        self.sla_response_time = {
            EscalationPriority.URGENT: 5,
            EscalationPriority.HIGH: 15,
            EscalationPriority.NORMAL: 60,
            EscalationPriority.LOW: 240,
        }

        # Escalation triggers (keywords that trigger escalation)
        self.escalation_keywords = [
            "speak to human",
            "talk to person",
            "real person",
            "human agent",
            "manager",
            "supervisor",
            "escalate",
            "frustrated",
            "angry",
            "unacceptable",
            "complaint",
            "legal action",
            "lawyer",
        ]

        logger.info(f"✅ HandoverSystem initialized (enabled={self.enabled})")

    def should_escalate(
        self,
        message: str,
        chat_jid: Optional[str] = None,
        emotion: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        tenant_id: Optional[str] = None,
    ) -> Tuple[bool, str, EscalationPriority]:
        """
        Determine if conversation should be escalated to human.

        Args:
            message: User message
            chat_jid: Customer WhatsApp JID
            emotion: Detected emotion (from ASI)
            conversation_history: Recent conversation history
            tenant_id: Tenant ID (REQUIRED for multi-tenant isolation)

        Returns:
            Tuple of (should_escalate, reason, priority)
        """
        if not self.enabled:
            return (False, "", EscalationPriority.NORMAL)

        # NEW: Check if this chat was escalated recently (within 10 minutes)
        if chat_jid and tenant_id and self.supabase:
            try:
                from datetime import datetime, timedelta
                recent_threshold = (datetime.utcnow() - timedelta(minutes=10)).isoformat()

                # Check for recent escalations for this customer (TENANT-ISOLATED)
                recent_escalations = self.supabase.table("escalations")\
                    .select("id,created_at")\
                    .eq("chat_jid", chat_jid)\
                    .eq("tenant_id", tenant_id)\
                    .gte("created_at", recent_threshold)\
                    .execute()

                if recent_escalations.data:
                    logger.info(f"⏭️ Skipping escalation - chat was escalated {len(recent_escalations.data)} time(s) in last 10 min (tenant={tenant_id})")
                    return (False, "Recently escalated", EscalationPriority.NORMAL)
            except Exception as e:
                logger.warning(f"Could not check recent escalations: {e}")

        # NEW: Try AI-powered intent detection first (more accurate than keywords)
        use_ai = os.getenv("ENABLE_AI_HANDOVER_DETECTION", "true").lower() == "true"
        if use_ai:
            try:
                from src.saas.ai_handover_detector import detect_handover_intent

                wants_human, reason, urgency = detect_handover_intent(message)

                if wants_human:
                    # Map urgency string to priority enum
                    priority_map = {
                        "urgent": EscalationPriority.URGENT,
                        "high": EscalationPriority.HIGH,
                        "normal": EscalationPriority.NORMAL,
                        "none": EscalationPriority.NORMAL,
                    }
                    priority = priority_map.get(urgency.lower(), EscalationPriority.NORMAL)

                    return (True, f"AI detected: {reason}", priority)
            except Exception as e:
                logger.warning(f"⚠️ AI handover detection failed, falling back to keywords: {e}")

        message_lower = message.lower()

        # Fallback: Explicit request for human (keyword matching)
        for keyword in self.escalation_keywords:
            if keyword in message_lower:
                priority = EscalationPriority.HIGH
                if any(
                    word in message_lower
                    for word in ["urgent", "immediately", "asap", "now"]
                ):
                    priority = EscalationPriority.URGENT
                return (
                    True,
                    f"Explicit request: '{keyword}'",
                    priority,
                )

        # High negative emotion
        if emotion in ["anger", "disgust", "fear"]:
            return (
                True,
                f"High negative emotion detected: {emotion}",
                EscalationPriority.HIGH,
            )

        # Repeated issues (same customer, multiple negative interactions)
        if conversation_history and len(conversation_history) > 5:
            negative_count = sum(
                1
                for msg in conversation_history[-10:]
                if msg.get("detected_emotion") in ["anger", "sadness", "fear"]
            )
            if negative_count >= 3:
                return (
                    True,
                    "Repeated negative interactions",
                    EscalationPriority.HIGH,
                )

        # NOTE: complex-multi-part and legal-keyword fallbacks removed.
        # Both are now handled by _keyword_fallback() via INTENT_CATEGORIES
        # in ai_handover_detector.py (v3.0). Multi-question (3+ ?) messages
        # explicitly do NOT escalate — they are answered sequentially by AI.

        return (False, "", EscalationPriority.NORMAL)

    def escalate(
        self,
        chat_jid: str,
        reason: str,
        tenant_id: str,
        priority: str = "normal",
        customer_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Convenience wrapper for create_escalation with simplified parameters.
        Used by lead_converter and other systems.

        Args:
            chat_jid: Customer WhatsApp JID
            reason: Escalation reason
            tenant_id: Tenant ID (REQUIRED - no fallback for security)
            priority: Priority level as string ("low", "normal", "high", "urgent")
            customer_context: Customer metadata

        Returns:
            Escalation ID or None if failed
        """
        if not self.enabled:
            logger.info(f"Escalation skipped (handover disabled): {reason}")
            return None

        # SECURITY: Validate tenant_id is provided (no fallback to prevent cross-tenant leaks)
        if not tenant_id:
            logger.error(f"❌ SECURITY: Escalation blocked - tenant_id is required (chat_jid={chat_jid})")
            return None

        # Convert string priority to enum
        priority_map = {
            "low": EscalationPriority.LOW,
            "normal": EscalationPriority.NORMAL,
            "high": EscalationPriority.HIGH,
            "urgent": EscalationPriority.URGENT,
        }
        priority_enum = priority_map.get(priority.lower(), EscalationPriority.NORMAL)

        # Call create_escalation with proper async handling
        import asyncio
        try:
            # Create event loop if not already in async context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context, schedule as task
                escalation_id = asyncio.create_task(
                    self.create_escalation(
                        tenant_id=tenant_id,
                        chat_jid=chat_jid,
                        reason=reason,
                        priority=priority_enum,
                        metadata=customer_context
                    )
                )
                return None  # Can't wait for result in sync context
            else:
                # Not in async context, run until complete
                escalation_id = loop.run_until_complete(
                    self.create_escalation(
                        tenant_id=tenant_id,
                        chat_jid=chat_jid,
                        reason=reason,
                        priority=priority_enum,
                        metadata=customer_context
                    )
                )
                return escalation_id
        except Exception as e:
            logger.error(f"Error in escalate wrapper: {e}")
            return None

    async def select_best_agent(
        self,
        tenant_id: str,
        priority: EscalationPriority,
        required_skills: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Select the best available agent for escalation based on priority and skills.

        Args:
            tenant_id: Tenant identifier
            priority: Escalation priority
            required_skills: Skills required for the escalation

        Returns:
            Agent data or None if no agents available
        """
        if not self.supabase:
            return None

        try:
            # Query active agents for this tenant, ordered by priority
            agents_response = (
                self.supabase.table("handover_agents")
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("is_active", True)
                .order("priority_level", desc=False)  # Lower number = higher priority
                .execute()
            )

            if not agents_response.data:
                logger.warning(f"⚠️ No active agents found for tenant {tenant_id}")
                return None

            agents = agents_response.data

            # If skills required, filter agents by skills
            if required_skills:
                skilled_agents = []
                for agent in agents:
                    agent_skills = agent.get("skills", [])
                    if isinstance(agent_skills, list) and any(
                        skill in agent_skills for skill in required_skills
                    ):
                        skilled_agents.append(agent)

                if skilled_agents:
                    agents = skilled_agents

            # For urgent priorities, prefer agents with priority level 1
            if priority == EscalationPriority.URGENT:
                urgent_agents = [
                    agent for agent in agents if agent.get("priority_level", 1) == 1
                ]
                if urgent_agents:
                    agents = urgent_agents

            # Return the first (highest priority) agent
            selected_agent = agents[0]
            logger.info(
                f"✅ Selected agent {selected_agent['agent_name']} "
                f"(priority: {selected_agent.get('priority_level', 1)}) for tenant {tenant_id}"
            )

            return selected_agent

        except Exception as e:
            logger.error(f"❌ Failed to select agent: {e}")
            return None

    async def create_escalation(
        self,
        tenant_id: str,
        chat_jid: str,  # old: customer_jid — renamed to match DB column
        reason: str,
        priority: EscalationPriority = EscalationPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Create new escalation in queue.

        Args:
            tenant_id: Tenant identifier
            chat_jid: Customer WhatsApp JID (DB column name)
            reason: Escalation reason
            priority: Priority level
            metadata: Additional metadata

        Returns:
            Escalation ID or None if failed
        """
        if not self.enabled or not self.supabase:
            return None

        try:
            # Select best available agent for this escalation
            required_skills = metadata.get("required_skills", []) if metadata else []
            selected_agent = await self.select_best_agent(
                tenant_id, priority, required_skills
            )

            # Get customer context
            customer_context = {}
            if self.memory:
                context = self.memory.get_context_summary(chat_jid)
                if context:
                    customer_context = {
                        "name": context.get("customer_name"),
                        "total_messages": context.get("total_messages"),
                        "avg_sentiment": context.get("avg_sentiment"),
                        "escalation_count": context.get("escalation_count", 0),
                    }

            # Create escalation record
            # Auto-detect reason_type from the reason string using INTENT_CATEGORIES
            # (reason contains matched phrase, e.g. "...matched: 'speak to owner'")
            try:
                from src.saas.ai_handover_detector import classify_intent_type
                _reason_type = classify_intent_type(reason.lower())
            except Exception:
                _reason_type = None

            escalation_data = {
                "tenant_id": tenant_id,
                "chat_jid": chat_jid,
                "reason": reason,
                "priority": priority.value,
                "status": EscalationStatus.PENDING.value,
                "customer_context": customer_context,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "sla_deadline": (
                    datetime.now() + timedelta(minutes=self.sla_response_time[priority])
                ).isoformat(),
            }
            if _reason_type:
                escalation_data["reason_type"] = _reason_type

            # Add agent assignment if agent selected
            if selected_agent:
                escalation_data["assigned_agent_id"] = selected_agent["id"]
                escalation_data["assigned_to"] = selected_agent["agent_name"]

            response = (
                self.supabase.table("escalations").insert(escalation_data).execute()
            )

            if response.data:
                escalation_id = response.data[0]["id"]
                logger.info(
                    f"✅ Created escalation {escalation_id} for {chat_jid} "
                    f"(priority: {priority.value}, reason: {reason})"
                )

                # Update customer context
                if self.memory:
                    self.memory.increment_escalation(chat_jid)

                # Send escalation event to Google Sheets
                if SHEETS_WEBHOOK_AVAILABLE and sheets_webhook:
                    # Extract customer phone from JID
                    customer_phone = chat_jid.split("@")[0] if "@" in chat_jid else chat_jid
                    if not customer_phone.startswith("+"):
                        customer_phone = f"+{customer_phone}"

                    # Get customer name from escalation data or use phone as fallback
                    customer_name = escalation_data.get("customer_name", customer_phone)

                    asyncio.create_task(
                        sheets_webhook.send_escalation_event(
                            tenant_id=tenant_id,
                            customer_jid=chat_jid,
                            customer_phone=customer_phone,
                            customer_name=customer_name,
                            escalation_id=escalation_id,
                            reason=reason,
                            priority=priority.value,
                        )
                    )
                    logger.debug(f"📊 Sheets escalation webhook queued for {escalation_id}")

                return str(escalation_id)

            return None

        except Exception as e:
            logger.error(f"Error creating escalation: {e}")
            return None

    def get_queue(
        self,
        tenant_id: str,
        status: Optional[EscalationStatus] = None,
        priority: Optional[EscalationPriority] = None,
        assigned_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get escalations from queue.

        Args:
            tenant_id: Tenant identifier
            status: Filter by status
            priority: Filter by priority
            assigned_to: Filter by assigned agent

        Returns:
            List of escalation records
        """
        if not self.enabled or not self.supabase:
            return []

        try:
            query = (
                self.supabase.table("escalations")
                .select("*")
                .eq("tenant_id", tenant_id)
                .order("priority", desc=True)
                .order("created_at", desc=False)
            )

            if status:
                query = query.eq("status", status.value)
            if priority:
                query = query.eq("priority", priority.value)
            if assigned_to:
                query = query.eq("assigned_to", assigned_to)

            response = query.execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error fetching queue: {e}")
            return []

    def claim_escalation(
        self, escalation_id: str, agent_id: str, tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Claim an escalation from queue.

        Args:
            escalation_id: Escalation ID
            agent_id: Agent identifier
            tenant_id: Tenant ID for isolation

        Returns:
            Updated escalation record or None
        """
        if not self.enabled or not self.supabase:
            return None

        try:
            response = (
                self.supabase.table("escalations")
                .update(
                    {
                        "status": EscalationStatus.CLAIMED.value,
                        "assigned_to": agent_id,
                        "claimed_at": datetime.now().isoformat(),
                    }
                )
                .eq("tenant_id", tenant_id)
                .eq("id", escalation_id)
                .eq("status", EscalationStatus.PENDING.value)
                .execute()
            )

            if response.data:
                logger.info(f"✅ Escalation {escalation_id} claimed by {agent_id}")
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"Error claiming escalation: {e}")
            return None

    def resolve_escalation(
        self,
        escalation_id: str,
        resolution_notes: Optional[str] = None,
        tenant_id: Optional[str] = None,
        conversation_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Mark escalation as resolved.

        Optionally fires a fire-and-forget live learning extraction task if
        ``tenant_id`` and ``conversation_messages`` are provided.

        Args:
            escalation_id: Escalation ID
            resolution_notes: Optional resolution notes
            tenant_id: Optional tenant UUID — required for live learning.
            conversation_messages: Optional list of message dicts from the
                resolved conversation — passed to the live learning extractor.

        Returns:
            True if successful
        """
        if not self.enabled or not self.supabase:
            return False

        try:
            query = self.supabase.table("escalations").update(
                {
                    "status": EscalationStatus.RESOLVED.value,
                    "resolved_at": datetime.now().isoformat(),
                    "resolution_notes": resolution_notes,
                }
            )

            if tenant_id:
                query = query.eq("tenant_id", tenant_id)

            query.eq("id", escalation_id).execute()

            logger.info(f"✅ Escalation {escalation_id} resolved")

            # Fire-and-forget live learning extraction (non-fatal)
            if tenant_id and conversation_messages:
                try:
                    import asyncio
                    from src.saas.live_learning import extract_and_save_live_learning

                    asyncio.create_task(
                        extract_and_save_live_learning(
                            tenant_id=tenant_id,
                            conversation_messages=conversation_messages,
                            supabase_client=self.supabase,
                        )
                    )
                    logger.info(
                        f"🧠 Live learning extraction queued for escalation "
                        f"{escalation_id} (tenant={tenant_id})"
                    )
                except Exception as ll_err:
                    logger.warning(
                        f"⚠️ Live learning extraction failed to queue "
                        f"(non-fatal): {ll_err}"
                    )

            return True

        except Exception as e:
            logger.error(f"Error resolving escalation: {e}")
            return False

    def get_sla_breaches(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Get escalations that have breached SLA.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of breached escalations
        """
        if not self.enabled or not self.supabase:
            return []

        try:
            now = datetime.now().isoformat()
            response = (
                self.supabase.table("escalations")
                .select("*")
                .eq("tenant_id", tenant_id)
                .in_(
                    "status",
                    [
                        EscalationStatus.PENDING.value,
                        EscalationStatus.CLAIMED.value,
                    ],
                )
                .lt("sla_deadline", now)
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error fetching SLA breaches: {e}")
            return []

    def get_statistics(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get escalation queue statistics.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Statistics dictionary
        """
        if not self.enabled or not self.supabase:
            return {}

        try:
            # Get all escalations for tenant
            all_escalations = (
                self.supabase.table("escalations")
                .select("*")
                .eq("tenant_id", tenant_id)
                .execute()
            )

            if not all_escalations.data:
                return {
                    "total": 0,
                    "pending": 0,
                    "claimed": 0,
                    "resolved": 0,
                    "sla_breaches": 0,
                    "avg_resolution_time": 0,
                }

            escalations = all_escalations.data

            # Calculate statistics
            total = len(escalations)
            pending = sum(
                1 for e in escalations if e["status"] == EscalationStatus.PENDING.value
            )
            claimed = sum(
                1 for e in escalations if e["status"] == EscalationStatus.CLAIMED.value
            )
            resolved = sum(
                1 for e in escalations if e["status"] == EscalationStatus.RESOLVED.value
            )

            # SLA breaches
            now = datetime.now()
            sla_breaches = sum(
                1
                for e in escalations
                if e["status"]
                in [EscalationStatus.PENDING.value, EscalationStatus.CLAIMED.value]
                and datetime.fromisoformat(e["sla_deadline"]) < now
            )

            # Average resolution time
            resolution_times = []
            for e in escalations:
                if e["status"] == EscalationStatus.RESOLVED.value and e.get(
                    "resolved_at"
                ):
                    created = datetime.fromisoformat(e["created_at"])
                    resolved = datetime.fromisoformat(e["resolved_at"])
                    resolution_times.append(
                        (resolved - created).total_seconds() / 60
                    )  # minutes

            avg_resolution_time = (
                sum(resolution_times) / len(resolution_times) if resolution_times else 0
            )

            return {
                "total": total,
                "pending": pending,
                "claimed": claimed,
                "resolved": resolved,
                "sla_breaches": sla_breaches,
                "avg_resolution_time": avg_resolution_time,
                "resolution_rate": (resolved / total * 100) if total > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {}

    def format_queue_message(self, escalations: List[Dict[str, Any]]) -> str:
        """
        Format queue list as WhatsApp message.

        Args:
            escalations: List of escalation records

        Returns:
            Formatted message
        """
        if not escalations:
            return "📋 **Queue is empty!**\n\nNo pending escalations. Great job! 🎉"

        lines = ["📋 **Escalation Queue**\n"]

        for i, esc in enumerate(escalations[:10], 1):  # Show max 10
            priority_emoji = {
                "urgent": "🔴",
                "high": "🟠",
                "normal": "🟡",
                "low": "🟢",
            }
            emoji = priority_emoji.get(esc["priority"], "⚪")

            # Calculate time in queue
            created = datetime.fromisoformat(esc["created_at"])
            time_in_queue = datetime.now() - created
            hours = int(time_in_queue.total_seconds() / 3600)
            minutes = int((time_in_queue.total_seconds() % 3600) / 60)

            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

            lines.append(
                f"{emoji} **#{esc['id']}** - {esc['reason'][:50]}\n"
                f"   Customer: {esc['customer_jid'][:20]}...\n"
                f"   Status: {esc['status']} | Time: {time_str}\n"
            )

        if len(escalations) > 10:
            lines.append(f"\n... and {len(escalations) - 10} more")

        lines.append(
            "\n**Commands:**\n"
            "/admin queue claim [id] - Claim escalation\n"
            "/admin queue resolve [id] - Mark resolved"
        )

        return "\n".join(lines)

    async def cleanup_stale_escalations(self, timeout_hours: int = 48) -> int:
        """
        Auto-close escalations that have been in_progress for >timeout_hours with no activity.

        Args:
            timeout_hours: Hours of inactivity before auto-close (default 48)

        Returns:
            Number of escalations closed
        """
        if not self.enabled or not self.supabase:
            return 0

        try:
            # Calculate cutoff time
            cutoff = datetime.now(timezone.utc) - timedelta(hours=timeout_hours)
            cutoff_iso = cutoff.isoformat()

            # Find stale escalations (in_progress, not updated recently)
            # NOTE: We need to check ALL tenants' escalations (not filtered by tenant_id)
            # because this is a global cleanup task that runs for all tenants
            result = (
                self.supabase.table("escalations")  # noaudit - cross-tenant cleanup task; each record processed with its own tenant_id
                .select("*")
                .eq("status", "in_progress")
                .lt("updated_at", cutoff_iso)
                .execute()
            )

            if not result.data:
                return 0

            closed_count = 0
            for esc in result.data:
                esc_tenant_id = esc.get("tenant_id")
                if not esc_tenant_id:
                    logger.warning(f"⚠️ Escalation {esc['id']} has no tenant_id, skipping")
                    continue

                # Check if human recently sent messages (activity check)
                try:
                    recent_messages = self.supabase.table("messages") \
                        .select("id") \
                        .eq("tenant_id", esc_tenant_id) \
                        .eq("chat_jid", esc["chat_jid"]) \
                        .eq("is_from_me", True) \
                        .gte("created_at", cutoff_iso) \
                        .limit(1) \
                        .execute()

                    if recent_messages.data:
                        logger.info(
                            f"✋ Skipping auto-close for {esc['id']} - "
                            f"human recently active in chat"
                        )
                        continue
                except Exception as e:
                    logger.warning(f"⚠️ Activity check failed for {esc['id']}: {e}")
                    # Continue with timeout if can't verify activity

                # Close the stale escalation
                logger.warning(
                    f"⏰ Auto-closing stale escalation {esc['id']} "
                    f"({timeout_hours}h+ old, chat_jid={esc['chat_jid']})"
                )

                self.supabase.table("escalations").update({
                    "status": "resolved",
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "resolution_notes": f"Auto-closed after {timeout_hours}h timeout"
                }).eq("id", esc["id"]).eq("tenant_id", esc_tenant_id).execute()

                closed_count += 1

                # Notify via WhatsApp if callback available
                if self.send_message:
                    try:
                        owner_msg = (
                            f"⏰ Escalation auto-closed for {esc['chat_jid']}\n"
                            f"Reason: {esc['reason']}\n"
                            f"Age: {timeout_hours}+ hours\n"
                            f"AI will now respond to this customer again."
                        )
                        # Send to tenant owner (would need tenant lookup)
                        # self.send_message(owner_jid, owner_msg, ...)
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to notify owner: {e}")

            if closed_count > 0:
                logger.info(f"✅ Auto-closed {closed_count} stale escalation(s)")

            return closed_count

        except Exception as e:
            logger.error(f"❌ Stale escalation cleanup failed: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get handover system statistics"""
        return {
            "enabled": self.enabled,
            "escalation_keywords": len(self.escalation_keywords),
            "sla_times": {
                priority.value: time
                for priority, time in self.sla_response_time.items()
            },
        }
