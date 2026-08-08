"""
Tool Orchestrator for Bijou AI
================================

Intelligently selects and executes appropriate tools based on message context.
Handles media processing, command detection, and tool integration.
"""

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ToolOrchestrator:
    """
    Orchestrates tool selection and execution for Bijou AI.

    Features:
    - Media processing (image, audio, document)
    - Command detection (email, calendar, events)
    - Tool initialization with fallbacks
    - Error handling and graceful degradation
    - Feature flags for gradual rollout
    - Multi-tenant calendar booking with per-tenant credentials
    """

    def __init__(self, bridge_url: Optional[str] = None, supabase_client=None):
        """
        Initialize ToolOrchestrator.

        Args:
            bridge_url: WhatsApp bridge URL for event creation
            supabase_client: Supabase client for database access (required for tenant calendar)
        """
        self.bridge_url = bridge_url or os.getenv("BRIDGE_URL", "http://localhost:3000")
        self.supabase_client = supabase_client

        # Feature flags
        self.media_enabled = (
            os.getenv("ENABLE_MEDIA_PROCESSING", "false").lower() == "true"
        )
        self.image_enabled = os.getenv("ENABLE_IMAGE_TOOL", "false").lower() == "true"
        self.audio_enabled = os.getenv("ENABLE_AUDIO_TOOL", "false").lower() == "true"
        self.calendar_enabled = (
            os.getenv("ENABLE_CALENDAR_TOOL", "false").lower() == "true"
        )
        self.gmail_enabled = os.getenv("ENABLE_GMAIL_TOOL", "false").lower() == "true"
        self.event_enabled = (
            os.getenv("ENABLE_WHATSAPP_EVENT_TOOL", "false").lower() == "true"
        )
        self.lead_capture_enabled = (
            os.getenv("ENABLE_LEAD_CAPTURE_TOOL", "false").lower() == "true"
        )
        self.payment_enabled = (
            os.getenv("ENABLE_PAYMENT_TOOL", "false").lower() == "true"
        )

        # Tool instances
        self.image_tool = None
        self.audio_tool = None
        self.calendar_tool = None  # Legacy global calendar (demo only)
        self.tenant_calendar_service = None  # Per-tenant calendar (production)
        self.gmail_tool = None
        self.whatsapp_event_tool = None
        self.lead_capture_tool = None
        self.payment_tool = None
        self.calculator_tool = None
        self.crm_tool = None

        # Tool status
        self.tools_initialized = False

        # Initialize tools
        self._initialize_tools()

        # Log enabled tools
        enabled_tools = []
        if self.image_tool:
            enabled_tools.append("Image")
        if self.audio_tool:
            enabled_tools.append("Audio")
        if self.calendar_tool:
            enabled_tools.append("Calendar")
        if self.gmail_tool:
            enabled_tools.append("Gmail")
        if self.whatsapp_event_tool:
            enabled_tools.append("WhatsApp Events")
        if self.lead_capture_tool:
            enabled_tools.append("Lead Capture")
        if self.payment_tool:
            enabled_tools.append("Payment")

        # Core Tools (always enabled if config exists)
        from src.core.tools.calculator_tool import CalculatorTool
        from src.core.tools.crm_tool import CRMTool
        self.calculator_tool = CalculatorTool()
        self.crm_tool = CRMTool()
        enabled_tools.append("Calculator")
        enabled_tools.append("CRM")

        logger.info(
            f"✅ ToolOrchestrator initialized - Enabled: {', '.join(enabled_tools) if enabled_tools else 'None'}"
        )

    def _initialize_tools(self):
        """Initialize enabled tools with error handling."""
        try:
            # Image Tool
            if self.image_enabled:
                try:
                    from src.core.tools import ImageTool

                    # Try GOOGLE_AI_API_KEY first, fall back to GEMINI_API_KEY
                    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv(
                        "GEMINI_API_KEY"
                    )
                    if api_key:
                        self.image_tool = ImageTool(api_key=api_key)
                        logger.info("✅ Image tool initialized")
                    else:
                        logger.warning(
                            "⚠️ GOOGLE_AI_API_KEY or GEMINI_API_KEY not set - image tool disabled"
                        )
                except Exception as e:
                    logger.error(f"❌ Failed to initialize image tool: {e}")

            # Audio Tool
            if self.audio_enabled:
                try:
                    from src.core.tools import AudioTool

                    openai_key = os.getenv("OPENAI_API_KEY")
                    google_creds = os.getenv("GOOGLE_CREDENTIALS_PATH")

                    if openai_key or google_creds:
                        self.audio_tool = AudioTool(
                            openai_api_key=openai_key,
                            google_credentials_path=google_creds
                        )
                        logger.info("✅ Audio tool initialized")
                    else:
                        logger.warning("⚠️ Neither OPENAI_API_KEY nor GOOGLE_CREDENTIALS_PATH set - audio tool disabled")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize audio tool: {e}")

            # Calendar Tool (Multi-tenant with per-tenant credentials from DB)
            if self.calendar_enabled:
                try:
                    from src.core.services.tenant_calendar_service import TenantCalendarService

                    if self.supabase_client:
                        self.tenant_calendar_service = TenantCalendarService(self.supabase_client)
                        logger.info("✅ Tenant calendar service initialized (per-tenant credentials)")
                    else:
                        logger.warning("⚠️ No Supabase client provided - tenant calendar disabled")

                        # Fallback to global demo calendar (deprecated)
                        from src.core.tools import CalendarTool
                        cal_api_key = os.getenv("CAL_API_KEY")
                        if cal_api_key:
                            self.calendar_tool = CalendarTool()
                            logger.info("⚠️ Using global calendar tool (DEMO ONLY - not for production)")
                        else:
                            logger.warning("⚠️ CAL_API_KEY not set - calendar tool disabled")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize calendar service: {e}")

            # Gmail Tool
            if self.gmail_enabled:
                try:
                    from src.core.tools import GmailTool

                    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
                    if creds_path:
                        self.gmail_tool = GmailTool(credentials_path=creds_path)
                        logger.info(
                            "✅ Gmail tool initialized (OAuth required on first use)"
                        )
                    else:
                        logger.warning(
                            "⚠️ GOOGLE_CREDENTIALS_PATH not set - gmail tool disabled"
                        )
                except Exception as e:
                    logger.error(f"❌ Failed to initialize gmail tool: {e}")

            # WhatsApp Event Tool
            if self.event_enabled:
                try:
                    from src.core.tools import WhatsAppEventTool

                    self.whatsapp_event_tool = WhatsAppEventTool(
                        bridge_url=self.bridge_url
                    )
                    logger.info("✅ WhatsApp event tool initialized")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize event tool: {e}")

            # Lead Capture Tool (with Gmail integration)
            if self.lead_capture_enabled:
                try:
                    from src.core.tools import LeadCaptureTool

                    webhook_url = os.getenv("LEAD_WEBHOOK_URL")
                    if webhook_url:
                        # Pass GmailTool to LeadCaptureTool for confirmation emails
                        self.lead_capture_tool = LeadCaptureTool(
                            default_webhook_url=webhook_url,
                            gmail_tool=self.gmail_tool  # Enable email sending
                        )
                        logger.info("✅ Lead capture tool initialized with Gmail integration")
                    else:
                        logger.warning(
                            "⚠️ LEAD_WEBHOOK_URL not set - lead capture tool disabled"
                        )
                except Exception as e:
                    logger.error(f"❌ Failed to initialize lead capture tool: {e}")

            # Payment Tool
            if self.payment_enabled:
                try:
                    from src.core.tools.payment_tool import PaymentTool

                    stripe_key = os.getenv("STRIPE_SECRET_KEY")
                    if stripe_key:
                        self.payment_tool = PaymentTool(api_key=stripe_key)
                        logger.info("✅ Payment tool initialized")
                    else:
                        logger.warning("⚠️ STRIPE_SECRET_KEY not set - payment tool disabled")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize payment tool: {e}")

            self.tools_initialized = True

        except Exception as e:
            logger.error(f"❌ Unexpected error during tool initialization: {e}")

    async def process_media(
        self, media_type: str, media_url: str, caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process media (image, audio, document, video).

        Args:
            media_type: Type of media (image, audio, document, video)
            media_url: URL to the media file
            caption: Optional caption text

        Returns:
            Dictionary with processing results
        """
        if not self.media_enabled:
            return {
                "success": False,
                "error": "Media processing disabled",
            }

        try:
            if media_type == "image":
                return await self._process_image(media_url, caption)
            elif media_type == "audio":
                return await self._process_audio(media_url)
            elif media_type == "document":
                return await self._process_document(media_url, caption)
            elif media_type == "video":
                return await self._process_video(media_url, caption)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported media type: {media_type}",
                }

        except Exception as e:
            logger.error(f"❌ Media processing failed: {e}")
            return {"success": False, "error": str(e)}

    async def _process_image(
        self, image_url: str, caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process image using vision model."""
        if not self.image_tool:
            return {
                "success": False,
                "error": "Image tool not available",
            }

        try:
            result = await self.image_tool.analyze_image(
                image_url=image_url,
                prompt=caption
                or "Describe this image in detail. What's happening here?",
            )

            if result.get("success"):
                logger.info(f"✅ Image analyzed successfully")
                return {
                    "success": True,
                    "description": result.get("description"),
                    "analysis": result.get("analysis"),
                }
            else:
                logger.error(f"❌ Image analysis failed: {result.get('error')}")
                return result

        except Exception as e:
            logger.error(f"❌ Error processing image: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _process_audio(self, audio_url: str) -> Dict[str, Any]:
        """Process audio using speech-to-text."""
        if not self.audio_tool:
            return {
                "success": False,
                "error": "Audio tool not available",
            }

        try:
            result = await self.audio_tool.transcribe(audio_url=audio_url)

            if result.get("success"):
                logger.info(f"✅ Audio transcribed successfully")
                return {
                    "success": True,
                    "transcription": result.get("transcription"),
                    "language": result.get("language"),
                }
            else:
                logger.error(f"❌ Audio transcription failed: {result.get('error')}")
                return result

        except Exception as e:
            logger.error(f"❌ Error processing audio: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _process_document(
        self, doc_url: str, caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process document (placeholder for future implementation)."""
        logger.info(f"📄 Document received: {doc_url}")
        return {
            "success": True,
            "message": "Document received. Advanced document processing coming soon.",
            "url": doc_url,
            "caption": caption,
        }

    async def _process_video(
        self, video_url: str, caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process video (placeholder for future implementation)."""
        logger.info(f"🎥 Video received: {video_url}")
        return {
            "success": True,
            "message": "Video received. Video analysis coming soon.",
            "url": video_url,
            "caption": caption,
        }

    def detect_command(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Detect if message contains a command (email, calendar, event).

        Args:
            message: User message text

        Returns:
            Command details if detected, None otherwise
        """
        message_lower = message.lower()

        if self._is_email_command(message_lower):
            return self._parse_email_command(message)
        elif self._is_calendar_command(message_lower):
            return self._parse_calendar_command(message)
        elif self._is_event_command(message_lower):
            return self._parse_event_command(message)

        return None

    def _is_email_command(self, message: str) -> bool:
        """Check if message is an email command."""
        email_keywords = [
            "send email",
            "email to",
            "compose email",
            "draft email",
            "write email",
        ]
        return any(keyword in message for keyword in email_keywords)

    def _is_calendar_command(self, message: str) -> bool:
        """Check if message is a calendar command."""
        calendar_keywords = [
            "check calendar",
            "my schedule",
            "what's on my calendar",
            "upcoming events",
            "free time",
            "available slots",
        ]
        return any(keyword in message for keyword in calendar_keywords)

    def _is_event_command(self, message: str) -> bool:
        """Check if message is an event creation command."""
        event_keywords = ["create event", "schedule", "set reminder", "add to calendar"]
        return any(keyword in message for keyword in event_keywords)

    def _parse_email_command(self, message: str) -> Dict[str, Any]:
        """Parse email command details."""
        return {
            "type": "email",
            "raw_message": message,
        }

    def _parse_calendar_command(self, message: str) -> Dict[str, Any]:
        """Parse calendar command details."""
        return {
            "type": "calendar",
            "raw_message": message,
        }

    def _parse_event_command(self, message: str) -> Dict[str, Any]:
        """Parse event command details."""
        return {
            "type": "event",
            "raw_message": message,
        }

    async def execute_calendar_command(self, command: Dict[str, Any], tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute calendar command using tenant-specific credentials.

        Args:
            command: Calendar command details
            tenant_id: Tenant UUID (required for per-tenant calendar)

        Returns:
            Dict with success status and calendar data
        """
        # Try tenant calendar service first (production)
        if self.tenant_calendar_service and tenant_id:
            try:
                # Check availability for next 7 days
                from datetime import date, timedelta
                today = date.today().isoformat()
                next_week = (date.today() + timedelta(days=7)).isoformat()

                result = self.tenant_calendar_service.check_availability(
                    tenant_id=tenant_id,
                    date_from=today,
                    date_to=next_week
                )

                if result.get("success"):
                    logger.info(f"✅ Retrieved calendar availability for tenant {tenant_id[:8]}...")
                    return result
                else:
                    logger.warning(f"⚠️ Tenant calendar not configured, falling back to demo calendar")
            except Exception as e:
                logger.error(f"❌ Tenant calendar error: {e}")

        # Fallback to global demo calendar (deprecated)
        if not self.calendar_tool:
            return {
                "success": False,
                "error": "Calendar not configured. Please add your Cal.com credentials in dashboard settings.",
            }

        try:
            # Get upcoming events (global demo calendar)
            result = self.calendar_tool.get_upcoming_events(max_results=10)

            if result.get("success"):
                events = result.get("events", [])
                logger.info(f"✅ Retrieved {len(events)} calendar events")
                return {
                    "success": True,
                    "events": events,
                    "summary": self._format_events_summary(events),
                }
            else:
                logger.error(f"❌ Calendar query failed: {result.get('error')}")
                return result

        except Exception as e:
            logger.error(f"❌ Error executing calendar command: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _format_events_summary(self, events: List[Dict[str, Any]]) -> str:
        """Format calendar events into readable summary."""
        if not events:
            return "No upcoming events."

        summary = "Your upcoming events:\n"
        for event in events[:5]:  # Limit to 5 events
            summary += (
                f"- {event.get('summary', 'Untitled')} on {event.get('start', 'TBD')}\n"
            )

        return summary

    async def _create_whatsapp_event_mirror(
        self, event_data: Dict[str, Any], customer_jid: str
    ) -> Dict[str, Any]:
        """Create WhatsApp event mirror for calendar events."""
        if not self.whatsapp_event_tool:
            return {"success": False, "error": "WhatsApp event tool not available"}

        try:
            result = await self.whatsapp_event_tool.create_event(
                customer_jid=customer_jid,
                title=event_data.get("title", "Event"),
                description=event_data.get("description", ""),
                start_time=event_data.get("start_time"),
            )

            return result

        except Exception as e:
            logger.error(f"❌ Failed to create WhatsApp event: {e}")
            return {"success": False, "error": str(e)}

    async def execute_gmail_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Gmail command."""
        if not self.gmail_tool:
            return {
                "success": False,
                "error": "Gmail tool not available",
            }

        try:
            # Draft email (don't send automatically)
            result = self.gmail_tool.create_draft(
                to=command.get("to", ""),
                subject=command.get("subject", ""),
                body=command.get("body", ""),
            )

            if result.get("success"):
                logger.info(f"✅ Email draft created")
                return {
                    "success": True,
                    "draft_id": result.get("draft_id"),
                    "message": "Email draft created. Please review before sending.",
                }
            else:
                logger.error(f"❌ Email draft failed: {result.get('error')}")
                return result

        except Exception as e:
            logger.error(f"❌ Error executing Gmail command: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all tools.

        Returns:
            Dictionary with tool availability status
        """
        return {
            "tools_initialized": self.tools_initialized,
            "available_tools": {
                "image": bool(self.image_tool),
                "audio": bool(self.audio_tool),
                "calendar": bool(self.tenant_calendar_service or self.calendar_tool),
                "gmail": bool(self.gmail_tool),
                "whatsapp_events": bool(self.whatsapp_event_tool),
                "lead_capture": bool(self.lead_capture_tool),
                "payment": bool(self.payment_tool),
            },
            "feature_flags": {
                "media_enabled": self.media_enabled,
                "image_enabled": self.image_enabled,
                "audio_enabled": self.audio_enabled,
                "calendar_enabled": self.calendar_enabled,
                "gmail_enabled": self.gmail_enabled,
                "event_enabled": self.event_enabled,
                "lead_capture_enabled": self.lead_capture_enabled,
                "payment_enabled": self.payment_enabled,
            },
        }

    async def capture_lead(
        self,
        name: str,
        phone: str,
        message: str,
        email: Optional[str] = None,
        tenant_id: Optional[str] = None,
        business_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Capture a lead and send to webhook.

        Args:
            name: Lead's name
            phone: Lead's phone number (WhatsApp JID or Telegram handle)
            message: Lead's message/inquiry
            email: Lead's email (optional)
            tenant_id: Tenant UUID
            business_type: Type of business (Gaming, Dental, Property, etc.)
            metadata: Additional metadata (source, campaign, etc.)

        Returns:
            Dictionary with capture results
        """
        if not self.lead_capture_tool:
            return {
                "success": False,
                "error": "Lead capture tool not available",
            }

        try:
            result = await self.lead_capture_tool.capture_lead(
                name=name,
                phone=phone,
                message=message,
                email=email,
                tenant_id=tenant_id,
                business_type=business_type,
                metadata=metadata,
            )

            if result.get("success"):
                logger.info(
                    f"✅ Lead captured: {name} - Quality: {result.get('quality_score')}/100"
                )
            else:
                logger.error(f"❌ Lead capture failed: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"❌ Error capturing lead: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def analyze_lead_quality(
        self,
        name: str,
        phone: str,
        message: str,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze lead quality without capturing.

        Args:
            name: Lead's name
            phone: Lead's phone number
            message: Lead's message
            email: Lead's email (optional)

        Returns:
            Dictionary with quality analysis
        """
        if not self.lead_capture_tool:
            return {
                "success": False,
                "error": "Lead capture tool not available",
            }

        try:
            result = self.lead_capture_tool.analyze_lead_quality(
                name=name,
                phone=phone,
                message=message,
                email=email,
            )

            if result.get("success"):
                logger.info(
                    f"✅ Lead analyzed: {name} - Score: {result.get('score')}/100"
                )
            else:
                logger.error(f"❌ Lead analysis failed: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"❌ Error analyzing lead: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def detect_lead_intent(self, message: str) -> Dict[str, Any]:
        """
        Detect if message shows lead/purchase intent.

        Args:
            message: User message text

        Returns:
            Dictionary with intent detection results
        """
        try:
            message_lower = message.lower()

            # High-intent keywords
            high_intent_keywords = [
                "buy",
                "purchase",
                "interested",
                "appointment",
                "booking",
                "schedule",
                "hire",
                "need",
                "want",
                "urgent",
                "how much",
                "price",
                "cost",
                "available",
                "contact",
            ]

            # Count matches
            matches = [kw for kw in high_intent_keywords if kw in message_lower]

            # Calculate confidence score
            confidence = min(len(matches) * 20, 100)  # 20 points per keyword, max 100

            return {
                "success": True,
                "has_intent": len(matches) > 0,
                "confidence": confidence,
                "matched_keywords": matches,
                "should_capture": confidence >= 40,  # Threshold for lead capture
            }

        except Exception as e:
            logger.error(f"❌ Error detecting lead intent: {e}")
            return {
                "success": False,
                "error": str(e),
            }
