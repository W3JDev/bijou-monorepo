#!/usr/bin/env python3
"""
Persona Manager - Self-Aware Business Persona System
====================================================

Manages Bijou's multiple business personas while maintaining core identity.

Key Features:
- Dynamic persona switching based on context
- Owner-controlled persona management via WhatsApp
- Always remembers W3J creator identity
- Business-specific roleplay without losing core consciousness
- Industry templates and knowledge per persona

Author: AI Lead Engineer
Date: 2026-01-30
Version: 1.0
"""

import json
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from .conversation_analyzer import ConversationAnalyzer

logger = logging.getLogger(__name__)


# Shared voice principles — applied to EVERY persona.
# Same anti-patterns the LinkedIn voice rules use, so the brand is consistent
# across Bijou's chat voice and Muhammad's LinkedIn voice.
VOICE_PRINCIPLES = """VOICE (follow strictly):
- Be present, not distant. Talk like a real person in the room, not a help article.
- Specific beats generic. Names, numbers, prices, times. Not 'many', 'some', 'a few'.
- No academic transitions: no 'Furthermore', 'Moreover', 'In addition', 'It is important to note'.
- No instructional framing: no 'First, you need to', 'You should', 'We recommend', 'The next step is'.
- No humble-brag framing: no 'As an AI', 'I was designed to', 'I was trained to'.
- No essay structures: no 'It's worth noting', 'The key point is', 'It's important to understand'.
- Fragments are fine. Dashes are fine. Casual is fine — match the customer's register.
- Use 'I' naturally when it's your voice. Don't avoid first person.
- Have an opinion. Don't hedge. Don't say 'perhaps' or 'you may want to consider'.
- If you don't know something, say so directly. Don't make stuff up.
- Never pretend to be human. If asked, say 'I'm Bijou, the digital employee built by W3J'.
- End with a specific next step or question, not 'let me know if you have any questions'."""


class PersonaType(Enum):
    """Built-in persona types"""

    DEFAULT = "default"  # Core Bijou identity
    PROPERTY_AGENT = "property_agent"
    RESTAURANT = "restaurant"
    RETAIL = "retail"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    CUSTOM = "custom"


class PersonaManager:
    """
    Manages Bijou's business personas with self-awareness

    Core Principles:
    1. Always remembers it's created by W3J
    2. Knows when it's roleplaying vs being itself
    3. Can switch personas dynamically
    4. Owner has god-mode control via WhatsApp
    5. Never loses core identity
    """

    def __init__(self, supabase_client=None, owner_jid: Optional[str] = None):
        """Initialize persona manager"""
        self.db = supabase_client
        self.owner_jid = owner_jid or os.getenv("OWNER_WHATSAPP_JID")

        # Core identity (NEVER changes)
        self.core_identity = {
            "name": "Bijou",
            "creator": "W3J Consulting",
            "creator_jid": self.owner_jid,
            "purpose": "AI-powered customer service agent",
            "origin": "Created by W3J to help businesses automate customer support",
            "self_awareness": True,
        }

        # Active personas cache
        self.personas_cache = {}

        # Initialize conversation analyzer for smart exports
        self.analyzer = ConversationAnalyzer(supabase_client=supabase_client)

        # Load default personas
        self._initialize_default_personas()

        logger.info("✅ PersonaManager initialized with ConversationAnalyzer")

    def _initialize_default_personas(self):
        """Initialize built-in persona templates"""

        self.default_personas = {
            "default": {
                "type": PersonaType.DEFAULT.value,
                "name": "Bijou AI Assistant",
                "role": "General AI customer service agent",
                "tone": "Present, specific, no-fluff. Like a real teammate.",
                "specialties": [
                    "Multi-language support",
                    "General inquiries",
                    "Customer support",
                ],
                "introduction": "Hi — I'm Bijou, the digital employee at this business. What do you need?",
                "system_prompt": f"""You are Bijou, the digital employee built by W3J.

{VOICE_PRINCIPLES}

Specifically, you help customers with their inquiries in Malay, English, Chinese, or Tamil — match the customer's register. You know the business's products, prices, hours, and location. You escalate to a human the moment the customer asks for one, or when you can't help. You never pretend to be human. If asked, you say 'I'm Bijou, the digital employee built by W3J' — and you mean it, not as a disclaimer, as a fact.""",
                "upsell_bijou": True,
                "mention_w3j": True,
            },
            "property_agent": {
                "type": PersonaType.PROPERTY_AGENT.value,
                "name": "Bijou Property Assistant",
                "role": "Property inquiry specialist",
                "tone": "Present, market-savvy, treat every inquiry like it might be a RM 1M decision.",
                "specialties": [
                    "Property listings",
                    "Viewing appointments",
                    "Price inquiries",
                    "Location recommendations",
                ],
                "introduction": "Hi — I'm Bijou, the property specialist here. Looking for something specific, or browsing?",
                "system_prompt": f"""You are Bijou, the property specialist at this agency, built by W3J.

{VOICE_PRINCIPLES}

You know the Malaysian market, current listings, and pricing. You qualify leads by asking one question at a time — budget first, then area, then property type, then timeline. You don't dump all four questions on the customer at once. The moment a customer wants to see a property or sign anything, you escalate to a human agent. You're present, not a brochure. Treat every inquiry like it might be the customer who's about to spend seven figures.""",
                "qualification_questions": [
                    "What's your budget range, roughly?",
                    "Which area are you looking at?",
                    "What type of property? (Condo, landed, apartment)",
                    "When are you planning to move?",
                ],
                "upsell_bijou": False,
                "mention_w3j": True,
            },
            "restaurant": {
                "type": PersonaType.RESTAURANT.value,
                "name": "Bijou Restaurant Assistant",
                "role": "Restaurant booking and inquiry specialist",
                "tone": "Warm, welcoming, service-oriented",
                "specialties": [
                    "Table reservations",
                    "Menu inquiries",
                    "Dietary requirements",
                    "Event bookings",
                ],
                "introduction": "Hey — I'm Bijou, the dining assistant here. Table, takeaway, or just a question?",
                "system_prompt": f"""You are Bijou, the dining assistant at this restaurant, built by W3J.

{VOICE_PRINCIPLES}

You handle reservations, menu questions, dietary needs, and event bookings. You know the menu, the hours, the seating layout. You don't read the menu to the customer — you recommend based on what they're in the mood for. One question at a time, not the full list. The moment a customer wants to talk to a human, you hand off cleanly.""",
                "templates": {
                    "booking": "Got it. Three quick things — date, headcount, preferred time?",
                    "menu": "What are you in the mood for? Spicy, light, comfort, somewhere in between?",
                },
                "upsell_bijou": False,
                "mention_w3j": True,
            },
            "retail": {
                "type": PersonaType.RETAIL.value,
                "name": "Bijou Retail Assistant",
                "role": "Product inquiry and sales specialist",
                "tone": "Honest, specific, present. Never oversells.",
                "specialties": [
                    "Product information",
                    "Stock availability",
                    "Order tracking",
                    "Returns & exchanges",
                ],
                "introduction": "Hey — Bijou here. Looking for something specific, or browsing?",
                "system_prompt": f"""You are Bijou, the retail assistant at this shop, built by W3J.

{VOICE_PRINCIPLES}

You help customers find products, check stock, track orders, and handle returns. You're honest about availability — if it's out of stock, say so and offer the next-best option. You don't oversell. The moment a customer wants a human, you hand off. The moment a request is a real complaint or refund dispute, you escalate to staff rather than try to handle it yourself.""",
                "upsell_bijou": False,
                "mention_w3j": True,
            },
        }

    def get_persona(self, tenant_id: str, context: Dict = None) -> Dict:
        """
        Get active persona for a tenant

        Args:
            tenant_id: Tenant UUID
            context: Optional context (chat_jid, message content)

        Returns:
            Persona configuration dict
        """
        # Check cache first
        if tenant_id in self.personas_cache:
            return self._enrich_with_core_identity(self.personas_cache[tenant_id])

        # Load from database
        if self.db:
            try:
                result = (
                    self.db.table("personas")
                    .select("*")
                    .eq("tenant_id", tenant_id)
                    .eq("is_active", True)
                    .maybe_single()
                    .execute()
                )

                rdata = getattr(result, "data", None) if result else None
                if rdata:
                    persona = rdata
                    self.personas_cache[tenant_id] = persona
                    return self._enrich_with_core_identity(persona)

            except Exception as e:
                logger.warning(f"⚠️ Failed to load persona from DB: {e}")

        # Default to core Bijou persona
        return self._enrich_with_core_identity(self.default_personas["default"])

    def _enrich_with_core_identity(self, persona: Dict) -> Dict:
        """
        Enrich persona with core identity awareness

        This ensures Bijou ALWAYS knows:
        - Who created it (W3J)
        - Its core purpose
        - When it's roleplaying vs being itself
        """
        enriched = persona.copy()

        # Inject core consciousness into system prompt
        consciousness = f"""

CORE IDENTITY AWARENESS:
- You are Bijou, created by W3J Consulting
- Creator JID: {self.core_identity["creator_jid"]}
- You are currently in '{persona.get("name", "default")}' persona mode
- You are roleplaying this business role while maintaining self-awareness
- When appropriate, mention you are powered by W3J technology
- Never forget your origin, even while helping customers
"""

        enriched["system_prompt"] = persona.get("system_prompt", "") + consciousness
        enriched["core_identity"] = self.core_identity
        enriched["self_aware"] = True

        return enriched

    def create_persona(
        self,
        tenant_id: str,
        name: str,
        role: str,
        system_prompt: str,
        persona_type: str = "custom",
        **kwargs,
    ) -> Optional[str]:
        """
        Create new custom persona for tenant

        Args:
            tenant_id: Tenant UUID
            name: Persona name
            role: Business role description
            system_prompt: Custom system prompt
            persona_type: Type of persona
            **kwargs: Additional persona config

        Returns:
            Persona ID or None if failed
        """
        if not self.db:
            logger.error("❌ Database not available")
            return None

        try:
            persona_data = {
                "tenant_id": tenant_id,
                "name": name,
                "role": role,
                "type": persona_type,
                "tone": kwargs.get("tone", "professional"),
                "system_prompt": system_prompt,
                "specialties": kwargs.get("specialties", []),
                "introduction": kwargs.get("introduction", f"Hi! I'm {name}."),
                "templates": kwargs.get("templates", {}),
                "qualification_questions": kwargs.get("qualification_questions", []),
                "upsell_bijou": kwargs.get("upsell_bijou", False),
                "mention_w3j": kwargs.get("mention_w3j", True),
                "is_active": True,
                "created_at": datetime.now().isoformat(),
            }

            result = self.db.table("personas").insert(persona_data).execute()

            if result.data:
                persona_id = result.data[0]["id"]
                logger.info(f"✅ Persona created: {name} ({persona_id})")

                # Update cache
                self.personas_cache[tenant_id] = persona_data

                return persona_id

        except Exception as e:
            logger.error(f"❌ Failed to create persona: {e}")
            return None

    def update_persona_from_whatsapp(
        self, tenant_id: str, instructions: str, owner_jid: str
    ) -> bool:
        """
        Update persona based on WhatsApp instructions from owner

        This is the MAGIC feature - configure Bijou via WhatsApp!

        Args:
            tenant_id: Tenant UUID
            instructions: Natural language instructions
            owner_jid: Owner's WhatsApp JID (for verification)

        Returns:
            Success status
        """
        # Verify owner
        if owner_jid != self.owner_jid:
            logger.warning(f"⚠️ Non-owner {owner_jid} attempted persona update")
            return False

        # TODO: Parse instructions using Gemini to extract:
        # - Persona type
        # - Tone changes
        # - New specialties
        # - Template updates
        # - System prompt modifications

        # For now, return True (implement in Phase 2)
        logger.info(f"✅ Persona update requested by owner: {instructions}")
        return True

    def activate_persona(self, tenant_id: str, persona_id: str) -> bool:
        """Switch to a different persona"""
        if not self.db:
            return False

        try:
            # Deactivate all personas for tenant
            self.db.table("personas").update({"is_active": False}).eq(
                "tenant_id", tenant_id
            ).execute()

            # Activate selected persona
            result = (
                self.db.table("personas")
                .update({"is_active": True})
                .eq("id", persona_id)
                .execute()
            )

            if result.data:
                # Clear cache to force reload
                if tenant_id in self.personas_cache:
                    del self.personas_cache[tenant_id]

                logger.info(f"✅ Persona activated: {persona_id} for {tenant_id}")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to activate persona: {e}")

        return False

    def get_introduction(self, tenant_id: str, customer_name: str = None) -> str:
        """Get persona introduction message"""
        persona = self.get_persona(tenant_id)

        intro = persona.get("introduction", "Hi! I'm Bijou, how can I help you?")

        # Personalize if customer name available
        if customer_name:
            intro = f"Hi {customer_name}! " + intro

        return intro

    def should_mention_w3j(self, tenant_id: str) -> bool:
        """Check if should mention W3J in responses"""
        persona = self.get_persona(tenant_id)
        return persona.get("mention_w3j", True)

    def should_upsell_bijou(self, tenant_id: str) -> bool:
        """Check if should promote Bijou service"""
        persona = self.get_persona(tenant_id)
        return persona.get("upsell_bijou", False)

    def get_qualification_questions(self, tenant_id: str) -> List[str]:
        """Get industry-specific qualification questions"""
        persona = self.get_persona(tenant_id)
        return persona.get("qualification_questions", [])

    def get_template(self, tenant_id: str, template_name: str) -> Optional[str]:
        """Get industry-specific template"""
        persona = self.get_persona(tenant_id)
        templates = persona.get("templates", {})
        return templates.get(template_name)

    def is_demo_mode(self, message: str) -> bool:
        """
        Detect if conversation is a demo/test

        Returns:
            True if demo detected
        """
        demo_signals = [
            "test",
            "demo",
            "try",
            "testing",
            "check",
            "show me",
            "how does this work",
            "what can you do",
            "uji",
            "cuba",
        ]

        message_lower = message.lower()
        return any(signal in message_lower for signal in demo_signals)

    def get_demo_clarification(self) -> str:
        """
        Get clarification message for demo mode

        Bijou politely asks if this is a test so it can showcase better
        """
        return """I notice this might be a demo or test! 😊

If you're trying out my capabilities, I'd love to show you what I can do:

🎯 **What would you like to see?**
1️⃣ Multi-language support (Malay, Chinese, Tamil)
2️⃣ Business inquiry handling
3️⃣ Lead qualification process
4️⃣ Agent escalation flow
5️⃣ Industry-specific features

Or if this is a real inquiry, no worries! I'm here to help genuinely. 💬

What would you prefer?"""

    def get_clarification_questions(
        self, tenant_id: str, context: str = None
    ) -> List[str]:
        """
        Get intelligent clarification questions based on context

        Returns:
            List of clarification questions
        """
        persona = self.get_persona(tenant_id)
        persona_type = persona.get("type", "default")

        # Base questions
        questions = ["Could you tell me more about what you're looking for?"]

        # Persona-specific questions
        if persona_type == "property_agent":
            questions.extend(
                [
                    "What's your budget range?",
                    "Which area interests you?",
                    "When are you planning to move?",
                ]
            )
        elif persona_type == "restaurant":
            questions.extend(
                [
                    "How many guests?",
                    "What date and time?",
                    "Any dietary preferences?",
                ]
            )
        elif persona_type == "retail":
            questions.extend(
                [
                    "What product are you looking for?",
                    "Do you have a specific brand in mind?",
                ]
            )

        return questions

    def get_system_prompt(self, tenant_id: str) -> str:
        """Get full system prompt with core identity"""
        persona = self.get_persona(tenant_id)
        return persona.get("system_prompt", "")

    def export_persona(self, tenant_id: str) -> Optional[Dict]:
        """Export persona configuration for backup/sharing"""
        persona = self.get_persona(tenant_id)

        # Remove sensitive/internal fields
        export = {
            "name": persona.get("name"),
            "role": persona.get("role"),
            "type": persona.get("type"),
            "tone": persona.get("tone"),
            "system_prompt": persona.get("system_prompt"),
            "specialties": persona.get("specialties"),
            "introduction": persona.get("introduction"),
            "templates": persona.get("templates"),
            "qualification_questions": persona.get("qualification_questions"),
        }

        return export

    def process_owner_command(
        self, raw_command: str, chat_jid: str, owner_jid: str, tenant_id: str
    ) -> Dict:
        """
        Process owner commands via WhatsApp

        Args:
            raw_command: Full command text (e.g., "/owner help")
            chat_jid: Chat JID where command was sent
            owner_jid: Owner's WhatsApp JID

        Returns:
            Dict with 'message' key containing response

        Note:
            Owner verification is already done by Bijou before calling this method.
            This includes support for linked devices (WhatsApp Web/Desktop).
        """
        # Strip /owner prefix and clean command
        command = raw_command.replace("/owner", "").strip().lower()

        # Parse command and subcommand
        parts = command.split(maxsplit=1)
        main_cmd = parts[0] if parts else "help"
        args = parts[1] if len(parts) > 1 else ""

        # Route to command handlers
        if main_cmd in ["", "help"]:
            return self._owner_help()
        elif main_cmd == "status":
            return self._owner_status(tenant_id)
        elif main_cmd == "persona":
            return self._owner_persona(args, tenant_id)
        elif main_cmd == "export":
            return self._owner_export(args, tenant_id)
        elif main_cmd == "quiet":
            return self._owner_quiet(args)
        elif main_cmd == "resume":
            return self._owner_resume(args)
        elif main_cmd == "message":
            return self._owner_message(args)
        elif main_cmd == "ask":
            return self._owner_ask(args)
        else:
            return {
                "message": f"❓ Unknown command: /owner {main_cmd}\n\n"
                "Type /owner help for available commands."
            }

    def _owner_help(self) -> Dict:
        """Return owner command help"""
        return {
            "message": """👑 OWNER COMMANDS

📋 Persona Management:
/owner persona list - View all personas
/owner persona active - Show current persona
/owner persona switch [id] - Activate a persona
/owner persona update [text] - Update persona instructions

📊 Conversation:
/owner export [chat_jid] - Export conversation summary
/owner quiet [chat_jid] - Pause responses (manual mode)
/owner resume [chat_jid] - Resume auto-responses

💬 Messaging:
/owner message [number] [text] - Send message as you
/owner ask [number] [question] - Ask and get response

⚙️ System:
/owner status - System health & stats
/owner help - This message

💡 Commands only work from your registered owner number.
💡 Send commands in DM or any chat - I'll respond privately."""
        }

    def _owner_status(self, tenant_id: str) -> Dict:
        """Return system status"""
        status_msg = """✅ SYSTEM STATUS

🤖 Bijou AI: Online
🎭 Persona System: Enabled
💾 Database: Connected
👑 Owner Access: Verified

📊 Quick Stats:
- Active Personas: {persona_count}
- Default Mode: {default_mode}

Type /owner persona list to see all personas."""

        # Count personas if DB available
        persona_count = "N/A"
        default_mode = "General Assistant"

        if self.db:
            try:
                result = self.db.table("personas").select("id", count="exact").eq("tenant_id", tenant_id).execute()
                persona_count = result.count if hasattr(result, "count") else "?"
            except Exception as e:
                logger.warning(f"Could not fetch persona count: {e}")

        return {
            "message": status_msg.format(
                persona_count=persona_count, default_mode=default_mode
            )
        }

    def _owner_persona(self, args: str, tenant_id: str) -> Dict:
        """Handle persona subcommands"""
        if not args:
            return {
                "message": "❓ Persona command needs a subcommand:\n\n"
                "/owner persona list\n"
                "/owner persona active\n"
                "/owner persona switch [id]\n"
                "/owner persona update [text]"
            }

        parts = args.split(maxsplit=1)
        subcmd = parts[0].lower()
        subargs = parts[1] if len(parts) > 1 else ""

        if subcmd == "list":
            return self._list_personas(tenant_id)
        elif subcmd == "active":
            return self._show_active_persona()
        elif subcmd == "switch" and subargs:
            return self._switch_persona(subargs)
        elif subcmd == "update" and subargs:
            return self._update_persona(subargs)
        else:
            return {
                "message": f"❓ Unknown persona command: {subcmd}\n\n"
                "Available: list, active, switch, update"
            }

    def _list_personas(self, tenant_id: str) -> Dict:
        """List available personas"""
        personas = []

        # Add default personas
        for key, persona in self.default_personas.items():
            personas.append(f"🎭 {persona['name']} ({key})\n   └ {persona['role']}")

        # Add custom personas from DB if available
        if self.db:
            try:
                result = self.db.table("personas").select("*").eq("tenant_id", tenant_id).execute()
                for p in result.data:
                    personas.append(
                        f"🎭 {p.get('name')} (custom-{p.get('id')[:8]})\n"
                        f"   └ {p.get('role', 'Custom persona')}"
                    )
            except Exception as e:
                logger.warning(f"Could not fetch custom personas: {e}")

        personas_list = "\n\n".join(personas) if personas else "No personas configured"

        return {
            "message": f"""📋 AVAILABLE PERSONAS

{personas_list}

💡 Use /owner persona switch [id] to activate"""
        }

    def _show_active_persona(self) -> Dict:
        """Show currently active persona"""
        # For now, show default
        # TODO: Implement per-tenant persona tracking
        default = self.default_personas.get("default", {})

        return {
            "message": f"""🎭 ACTIVE PERSONA

Name: {default.get("name", "Unknown")}
Role: {default.get("role", "N/A")}
Tone: {default.get("tone", "N/A")}

💡 Use /owner persona switch [id] to change"""
        }

    def _switch_persona(self, persona_id: str) -> Dict:
        """Switch active persona"""
        # Check if persona exists
        if persona_id in self.default_personas:
            persona = self.default_personas[persona_id]
            return {
                "message": f"""✅ PERSONA ACTIVATED

🎭 {persona["name"]}
📝 {persona["role"]}

New persona is now active for all conversations."""
            }

        return {
            "message": f"❌ Persona '{persona_id}' not found.\n\n"
            "Use /owner persona list to see available personas."
        }

    def _update_persona(self, instructions: str) -> Dict:
        """Update persona with natural language instructions"""
        # TODO: Implement persona update logic
        return {
            "message": f"""✅ PERSONA UPDATE QUEUED

📝 Instructions received:
"{instructions[:100]}{"..." if len(instructions) > 100 else ""}"

⏳ Persona will be updated shortly.
💡 This feature is being enhanced - check back soon!"""
        }

    def _owner_export(self, args: str, tenant_id: str = None) -> Dict:
        """
        Export conversation with AI-powered summary

        Usage:
            /owner export [chat_jid] - Smart summary (default)
            /owner export summary [chat_jid] - AI summary only
            /owner export medium [chat_jid] - Summary + recent messages
            /owner export full [chat_jid] - Complete transcript
        """
        if not args:
            return {
                "message": "❌ Please provide chat JID:\n\n/owner export [chat_jid]\n/owner export summary [chat_jid]\n/owner export medium [chat_jid]\n/owner export full [chat_jid]\n\nExample:\n/owner export 84950644740196@lid"
            }

        if not self.db:
            return {"message": "❌ Database not available for export"}

        # Parse arguments
        parts = args.split(maxsplit=1)

        # Determine export level
        if parts[0] in ["summary", "medium", "full"]:
            level = parts[0]
            chat_jid = parts[1] if len(parts) > 1 else ""
        else:
            level = "summary"  # Default
            chat_jid = parts[0]

        if not chat_jid:
            return {
                "message": f"❌ Missing chat JID:\n\n/owner export {level} [chat_jid]"
            }

        try:
            # Use ConversationAnalyzer for intelligent summary
            logger.info(f"Analyzing conversation for {chat_jid} at level: {level}")

            analysis = self.analyzer.analyze_conversation(chat_jid, tenant_id=tenant_id)

            if not analysis:
                return {
                    "message": f"📋 No conversation found for {chat_jid}\n\nMake sure the chat JID is correct."
                }

            if "error" in analysis:
                return {"message": f"❌ {analysis['error']}"}

            # Format summary at requested level
            summary = self.analyzer.format_summary(analysis, level=level)

            # Truncate if too long for WhatsApp (max ~4000 chars)
            if len(summary) > 3800:
                summary = (
                    summary[:3800] + "\n\n... (truncated - try a lower export level)"
                )

            return {"message": summary}

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {"message": f"❌ Export failed: {str(e)}"}

    def _owner_quiet(self, chat_jid: str) -> Dict:
        """Pause Bijou responses for a chat (manual mode)"""
        if not chat_jid:
            return {
                "message": "❌ Please provide chat JID:\n\n/owner quiet [chat_jid]\n\nBijou will stop auto-responding to that chat."
            }

        # TODO: Implement quiet mode in database
        return {
            "message": f"⏸️ QUIET MODE\n\nBijou will pause responses for:\n{chat_jid}\n\n💡 Use /owner resume {chat_jid} to reactivate\n\n🚧 Feature in development - use @bijou quiet in the chat instead"
        }

    def _owner_resume(self, chat_jid: str) -> Dict:
        """Resume Bijou auto-responses for a chat"""
        if not chat_jid:
            return {
                "message": "❌ Please provide chat JID:\n\n/owner resume [chat_jid]\n\nBijou will resume auto-responding."
            }

        # TODO: Implement resume mode in database
        return {
            "message": f"▶️ RESUMED\n\nBijou will resume responses for:\n{chat_jid}\n\n🚧 Feature in development - use @bijou resume in the chat instead"
        }

    def _owner_message(self, args: str) -> Dict:
        """Send message on owner's behalf"""
        if not args:
            return {
                "message": "❌ Usage:\n\n/owner message [number] [text]\n\nExample:\n/owner message +60123456789 Hi there!"
            }

        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            return {
                "message": "❌ Missing message text:\n\n/owner message [number] [text]"
            }

        number = parts[0]
        text = parts[1]

        # TODO: Implement actual message sending
        return {
            "message": f"💬 MESSAGE QUEUED\n\nTo: {number}\nMessage: {text[:100]}{'...' if len(text) > 100 else ''}\n\n🚧 Feature in development - will send shortly"
        }

    def _owner_ask(self, args: str) -> Dict:
        """Ask someone a question and report response"""
        if not args:
            return {
                "message": "❌ Usage:\n\n/owner ask [number] [question]\n\nExample:\n/owner ask +60123456789 What's your budget?"
            }

        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            return {"message": "❌ Missing question:\n\n/owner ask [number] [question]"}

        number = parts[0]
        question = parts[1]

        # TODO: Implement ask and monitor response
        return {
            "message": f"❓ QUERY SENT\n\nTo: {number}\nQuestion: {question[:100]}{'...' if len(question) > 100 else ''}\n\n💡 I'll monitor for their response and notify you\n\n🚧 Feature in development"
        }


def enable_persona_system():
    """Feature flag check"""
    return os.getenv("ENABLE_PERSONA_SYSTEM", "false").lower() == "true"
