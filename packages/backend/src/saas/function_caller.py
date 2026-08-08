"""
Bijou AI - Function Calling System
====================================

AI-driven automatic tool orchestration using Gemini 2.0 native function calling.

Automatically detects user intent and calls appropriate tools:
- Email: Send, search, draft emails via Gmail
- Calendar: Create, update, view events via Google Calendar
- Search: Query knowledge base
- Reminders: Set reminders for follow-ups

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class FunctionCaller:
    """
    Manages AI-driven function calling for automatic tool orchestration.

    Integrates with Gemini 2.0 function calling API to automatically
    detect intent and execute appropriate tools.
    """

    def __init__(
        self,
        tool_orchestrator=None,
        gemini_api_key: Optional[str] = None,
        enable_confirmations: bool = True,
        connector_router=None,
        connector_registry=None,
    ):
        """
        Initialize function caller.

        Args:
            tool_orchestrator: ToolOrchestrator instance
            gemini_api_key: Gemini API key
            enable_confirmations: Require confirmation for destructive actions
        """
        self.tool_orchestrator = tool_orchestrator
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.enable_confirmations = enable_confirmations

        # Feature flag
        self.enabled = os.getenv("ENABLE_FUNCTION_CALLING", "false").lower() == "true"

        # Track pending confirmations
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}

        # Multi-backend connector layer (native + Composio). Feature-flagged;
        # when ENABLE_COMPOSIO is off, none of the connector code paths run and
        # behavior is identical to before.
        self.composio_enabled = os.getenv("ENABLE_COMPOSIO", "false").lower() == "true"
        self._router = connector_router
        self._registry = connector_registry
        self._connector_fn_map: Dict[str, str] = {}
        if self._registry is not None:
            self._connector_fn_map = {a.replace(".", "_"): a for a in self._registry}

        # Initialize Gemini client
        if self.enabled and self.gemini_api_key:
            try:
                from google import genai

                self.genai_client = genai.Client(api_key=self.gemini_api_key)
                logger.info("✅ FunctionCaller initialized (enabled=true)")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.enabled = False
        else:
            logger.info("✅ FunctionCaller initialized (enabled=false)")

    def _ensure_connectors(self) -> None:
        """Lazily build the connector router + registry (idempotent)."""
        if self._router is not None and self._registry is not None:
            return
        from src.connectors.registry import build_registry
        from src.connectors.router import ConnectorRouter
        from src.connectors.native_connector import NativeConnector
        from src.connectors.composio_connector import ComposioConnector
        if self._registry is None:
            self._registry = build_registry(self.tool_orchestrator)
        if self._router is None:
            self._router = ConnectorRouter({
                "native": NativeConnector(self.tool_orchestrator),
                "composio": ComposioConnector(),  # api_key from COMPOSIO_API_KEY env
            })
        self._connector_fn_map = {a.replace(".", "_"): a for a in self._registry}

    def get_function_declarations(self) -> List[Dict[str, Any]]:
        """
        Get function declarations for Gemini function calling.

        Returns:
            List of function declaration dicts
        """
        functions = []

        # Email functions (if Gmail tool available)
        if self.tool_orchestrator and hasattr(self.tool_orchestrator, "gmail_tool"):
            functions.extend(
                [
                    {
                        "name": "send_email",
                        "description": "Send an email via Gmail",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "to": {
                                    "type": "string",
                                    "description": "Recipient email address",
                                },
                                "subject": {
                                    "type": "string",
                                    "description": "Email subject",
                                },
                                "body": {"type": "string", "description": "Email body"},
                            },
                            "required": ["to", "subject", "body"],
                        },
                    },
                    {
                        "name": "search_email",
                        "description": "Search emails in Gmail",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query (e.g., 'from:john@example.com')",
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Maximum number of results (default 10)",
                                },
                            },
                            "required": ["query"],
                        },
                    },
                ]
            )

        # Calendar functions (Multi-tenant calendar service)
        if self.tool_orchestrator and hasattr(self.tool_orchestrator, "tenant_calendar_service") and self.tool_orchestrator.tenant_calendar_service:
            functions.extend(
                [
                    {
                        "name": "check_availability",
                        "description": "Check available appointment slots on the calendar for a specific date. ALWAYS call this FIRST before booking.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "date_from": {
                                    "type": "string",
                                    "description": "Start date in ISO format (e.g., '2026-03-06')",
                                },
                                "date_to": {
                                    "type": "string",
                                    "description": "End date in ISO format (e.g., '2026-03-07'). Defaults to date_from + 1 day",
                                },
                            },
                            "required": ["date_from"],
                        },
                    },
                    {
                        "name": "book_appointment",
                        "description": "Book an appointment/viewing for customer using their Cal.com calendar. Only call this AFTER you have collected customer name, email, phone AND checked availability.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "customer_name": {
                                    "type": "string",
                                    "description": "Customer's full name",
                                },
                                "customer_email": {
                                    "type": "string",
                                    "description": "Customer's email address",
                                },
                                "customer_phone": {
                                    "type": "string",
                                    "description": "Customer's phone number (with country code)",
                                },
                                "start_time": {
                                    "type": "string",
                                    "description": "Appointment time in ISO format (e.g., '2026-03-05T14:00:00+08:00')",
                                },
                                "property_name": {
                                    "type": "string",
                                    "description": "Property name or description (optional)",
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Additional notes about the appointment (optional)",
                                },
                                "duration_minutes": {
                                    "type": "integer",
                                    "description": "Duration in minutes (default 30)",
                                },
                            },
                            "required": ["start_time"],
                        },
                    },
                ]
            )

        # Escalation/Handover functions
        functions.append(
            {
                "name": "escalate_to_human",
                "description": "Transfer conversation to human agent when customer needs personal assistance, has complex questions, or requests to speak with sales/support team",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Reason for escalation (e.g., 'Customer wants pricing negotiation', 'Complex technical question')",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "Escalation priority (default: medium)",
                        },
                        "customer_context": {
                            "type": "string",
                            "description": "Summary of conversation and customer's needs (optional)",
                        },
                    },
                    "required": ["reason"],
                },
            }
        )

        # Knowledge base search
        functions.append(
            {
                "name": "search_knowledge",
                "description": "Search the business knowledge base for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (default 5)",
                        },
                    },
                    "required": ["query"],
                },
            }
        )

        # Calculator function
        functions.append(
            {
                "name": "calculate",
                "description": "Evaluate a mathematical expression (e.g., '150 * 1.06')",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "The math expression to calculate",
                        }
                    },
                    "required": ["expression"],
                },
            }
        )

        # CRM functions
        functions.extend([
            {
                "name": "search_customer",
                "description": "Search for a customer or lead by name or phone",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Name or phone number to search"}
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "add_crm_lead",
                "description": "Add a new lead to the CRM",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Customer name"},
                        "phone": {"type": "string", "description": "Customer phone number"},
                        "details": {"type": "string", "description": "Additional details about the lead"}
                    },
                    "required": ["name", "phone"],
                },
            }
        ])

        # Long-tail actions served via the connector layer (Composio-backed).
        # Native/critical actions are already declared above; we only surface the
        # COMPOSIO_ONLY breadth here, using Gemini-safe names (dots -> underscores).
        if self.composio_enabled:
            self._ensure_connectors()
            from src.connectors.base import Policy
            existing = {f["name"] for f in functions}
            for gemini_name, canonical in self._connector_fn_map.items():
                action = self._registry[canonical]
                if action.policy is not Policy.COMPOSIO_ONLY:
                    continue
                if gemini_name in existing:
                    continue
                functions.append({
                    "name": gemini_name,
                    "description": action.description,
                    "parameters": action.input_schema,
                })

        return functions

    def is_destructive_action(self, function_name: str) -> bool:
        """
        Check if a function is destructive (requires confirmation).

        Args:
            function_name: Name of the function

        Returns:
            True if destructive
        """
        destructive_functions = [
            "send_email",
            "delete_email",
            "create_calendar_event",
            "delete_calendar_event",
            "update_calendar_event",
        ]
        return function_name in destructive_functions

    async def detect_and_execute(
        self, message: str, chat_jid: str, user_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if message requires function calling and execute.

        Args:
            message: User message
            chat_jid: Chat JID
            user_context: Optional user context

        Returns:
            Execution result dict or None if no function detected
        """
        if not self.enabled:
            return None

        try:
            from google.genai import types

            # Get function declarations
            functions = self.get_function_declarations()

            if not functions:
                logger.debug("No functions available for calling")
                return None

            # Create tools config
            tools = [types.Tool(function_declarations=functions)]

            # Call Gemini with function calling
            response = self.genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=message,
                config=types.GenerateContentConfig(
                    tools=tools,
                    temperature=0.3,  # Lower temperature for function calling
                ),
            )

            # Check if function was called
            if not response.candidates:
                return None

            candidate = response.candidates[0]
            if not hasattr(candidate, "function_calls") or not candidate.function_calls:
                return None

            # Execute function calls
            results = []
            for function_call in candidate.function_calls:
                result = await self._execute_function(
                    function_call, chat_jid, user_context
                )
                results.append(result)

            return {"function_calls": results, "requires_confirmation": False}

        except Exception as e:
            logger.error(f"Error in function calling: {e}")
            return None

    async def _execute_function(
        self,
        function_call: Any,
        chat_jid: str,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single function call.

        Args:
            function_call: Function call from Gemini
            chat_jid: Chat JID
            user_context: User context

        Returns:
            Execution result
        """
        function_name = function_call.name
        args = dict(function_call.args)

        logger.info(f"🔧 Executing function: {function_name} with args: {args}")

        # Check if destructive and needs confirmation
        if self.enable_confirmations and self.is_destructive_action(function_name):
            # Store pending confirmation
            confirmation_id = f"{chat_jid}_{datetime.now().timestamp()}"
            self.pending_confirmations[confirmation_id] = {
                "function_name": function_name,
                "args": args,
                "chat_jid": chat_jid,
                "timestamp": datetime.now().isoformat(),
            }

            return {
                "function": function_name,
                "args": args,
                "status": "pending_confirmation",
                "confirmation_id": confirmation_id,
                "message": self._get_confirmation_message(function_name, args),
            }

        # Execute function
        try:
            result = await self._call_function(function_name, args, user_context)
            return {
                "function": function_name,
                "args": args,
                "status": "success",
                "result": result,
            }
        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}")
            return {
                "function": function_name,
                "args": args,
                "status": "error",
                "error": str(e),
            }

    async def _call_function(
        self, function_name: str, args: Dict[str, Any], user_context: Optional[Dict]
    ) -> Any:
        """
        Actually call the function.

        Args:
            function_name: Name of function
            args: Function arguments
            user_context: User context

        Returns:
            Function result
        """
        # Connector-routed actions (multi-backend: native + Composio). Checked
        # first so new long-tail tools never collide with the native branches
        # below, and so a Composio outage degrades gracefully instead of raising.
        if self.composio_enabled:
            self._ensure_connectors()
            canonical = self._connector_fn_map.get(function_name)
            if canonical is not None:
                tenant_id = (user_context or {}).get("tenant_id")
                result = await self._router.execute(tenant_id, canonical, args, self._registry)
                return {
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "backend": result.backend,
                    "user_message": result.user_message,
                }

        # Email functions
        if function_name == "send_email":
            if not self.tool_orchestrator.gmail_tool:
                raise ValueError("Gmail tool not available")
            return self.tool_orchestrator.gmail_tool.send_email(
                to=args["to"], subject=args["subject"], body=args["body"]
            )

        elif function_name == "search_email":
            if not self.tool_orchestrator.gmail_tool:
                raise ValueError("Gmail tool not available")
            return self.tool_orchestrator.gmail_tool.search_emails(
                query=args["query"], max_results=args.get("max_results", 10)
            )

        # Calendar availability check (multi-tenant)
        elif function_name == "check_availability":
            if not self.tool_orchestrator.tenant_calendar_service:
                raise ValueError("Calendar service not available")

            tenant_id = user_context.get("tenant_id") if user_context else None
            if not tenant_id:
                raise ValueError("Tenant ID required for calendar check")

            # Get tenant's calendar config and check availability via Cal.com API
            config = self.tool_orchestrator.tenant_calendar_service.get_tenant_calendar_config(tenant_id)
            if not config:
                return {
                    "available": False,
                    "message": "Calendar not configured for this tenant. Please ask the customer to contact the office directly.",
                    "slots": []
                }

            try:
                from src.core.tools.calendar_tool import CalendarTool
                calendar = CalendarTool()
                calendar.api_key = config.get("cal_api_key")
                calendar.username = config.get("cal_username")
                calendar._initialized = True

                date_from = args["date_from"]
                date_to = args.get("date_to", date_from)
                slots = calendar.get_availability(date_from=date_from, date_to=date_to)
                return {
                    "available": bool(slots),
                    "slots": slots,
                    "message": f"Found {len(slots) if slots else 0} available slot(s)" if slots else "No available slots for this date"
                }
            except Exception as e:
                logger.error(f"Calendar availability check failed: {e}")
                return {
                    "available": False,
                    "error": str(e),
                    "message": "Could not check calendar availability. Please ask the customer to contact the office directly."
                }

        # Calendar booking (multi-tenant)
        elif function_name == "book_appointment":
            if not self.tool_orchestrator.tenant_calendar_service:
                raise ValueError("Calendar service not available")

            # Get tenant_id from user_context
            tenant_id = user_context.get("tenant_id") if user_context else None
            if not tenant_id:
                raise ValueError("Tenant ID required for calendar booking")

            return self.tool_orchestrator.tenant_calendar_service.create_booking(
                tenant_id=tenant_id,
                customer_name=args["customer_name"],
                customer_email=args["customer_email"],
                customer_phone=args["customer_phone"],
                start_time=args["start_time"],
                property_name=args.get("property_name"),
                notes=args.get("notes"),
                duration_minutes=args.get("duration_minutes", 30),
            )

        # Escalation/Handover
        elif function_name == "escalate_to_human":
            # Get user context
            chat_jid = user_context.get("chat_jid") if user_context else None
            tenant_id = user_context.get("tenant_id") if user_context else None

            if not chat_jid or not tenant_id:
                raise ValueError("Chat JID and Tenant ID required for escalation")

            # Create escalation via HandoverSystem
            try:
                if self.tool_orchestrator and hasattr(self.tool_orchestrator, 'handover_system') and self.tool_orchestrator.handover_system:
                    handover = self.tool_orchestrator.handover_system
                else:
                    from src.saas.handover_system import HandoverSystem
                    handover = HandoverSystem()

                escalation_id = await handover.create_escalation(
                    tenant_id=tenant_id,
                    chat_jid=chat_jid,
                    reason=args["reason"],
                    priority=args.get("priority", "medium"),
                    metadata={"customer_context": args.get("customer_context", "")},
                )

                return {
                    "success": True,
                    "escalation_id": escalation_id,
                    "message": "Escalated to human agent successfully",
                }
            except Exception as e:
                logger.error(f"Escalation failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                }

        # Knowledge base search
        elif function_name == "search_knowledge":
            # Placeholder - integrate with actual knowledge base
            return {
                "results": [
                    {
                        "title": "Knowledge result",
                        "content": "Search functionality coming soon",
                    }
                ]
            }

        # Calculator
        elif function_name == "calculate":
            if not self.tool_orchestrator.calculator_tool:
                raise ValueError("Calculator tool not available")
            return self.tool_orchestrator.calculator_tool.calculate(args["expression"])

        # CRM
        elif function_name == "search_customer":
            if not self.tool_orchestrator.crm_tool:
                raise ValueError("CRM tool not available")
            return self.tool_orchestrator.crm_tool.search_customer(args["query"])

        elif function_name == "add_crm_lead":
            if not self.tool_orchestrator.crm_tool:
                raise ValueError("CRM tool not available")
            return self.tool_orchestrator.crm_tool.add_lead(
                name=args["name"],
                phone=args["phone"],
                details=args.get("details")
            )

        # Reminder
        elif function_name == "set_reminder":
            # Placeholder - integrate with reminder system
            return {
                "status": "scheduled",
                "message": args["message"],
                "time": args["time"],
            }

        else:
            raise ValueError(f"Unknown function: {function_name}")

    def _get_confirmation_message(
        self, function_name: str, args: Dict[str, Any]
    ) -> str:
        """
        Generate confirmation message for destructive action.

        Args:
            function_name: Function name
            args: Function arguments

        Returns:
            Confirmation message
        """
        if function_name == "send_email":
            return (
                f"📧 **Confirm Email**\n\n"
                f"To: {args['to']}\n"
                f"Subject: {args['subject']}\n"
                f"Body: {args['body'][:100]}...\n\n"
                f"Reply 'yes' to send or 'no' to cancel."
            )

        elif function_name == "create_calendar_event":
            return (
                f"📅 **Confirm Calendar Event**\n\n"
                f"Title: {args['title']}\n"
                f"Start: {args['start_time']}\n"
                f"End: {args.get('end_time', 'Not specified')}\n\n"
                f"Reply 'yes' to create or 'no' to cancel."
            )

        else:
            return (
                f"⚠️ **Confirm Action**\n\n"
                f"Function: {function_name}\n"
                f"Arguments: {json.dumps(args, indent=2)}\n\n"
                f"Reply 'yes' to proceed or 'no' to cancel."
            )

    async def confirm_action(
        self, confirmation_id: str, confirmed: bool
    ) -> Dict[str, Any]:
        """
        Confirm or deny a pending action.

        Args:
            confirmation_id: Confirmation ID
            confirmed: True to confirm, False to cancel

        Returns:
            Execution result
        """
        if confirmation_id not in self.pending_confirmations:
            return {"status": "error", "error": "Confirmation not found or expired"}

        pending = self.pending_confirmations.pop(confirmation_id)

        if not confirmed:
            return {
                "status": "cancelled",
                "function": pending["function_name"],
                "message": "Action cancelled by user",
            }

        # Execute the function
        try:
            result = await self._call_function(
                pending["function_name"], pending["args"], None
            )
            return {
                "status": "success",
                "function": pending["function_name"],
                "result": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "function": pending["function_name"],
                "error": str(e),
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get function caller statistics"""
        return {
            "enabled": self.enabled,
            "confirmations_enabled": self.enable_confirmations,
            "pending_confirmations": len(self.pending_confirmations),
            "available_functions": len(self.get_function_declarations()),
        }
