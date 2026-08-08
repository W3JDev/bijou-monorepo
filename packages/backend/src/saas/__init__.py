"""
Bijou AI - SaaS Platform Module
================================

Multi-tenant SaaS features for Bijou AI WhatsApp platform.

This module contains all SaaS-specific functionality:
- Multi-tenant management and isolation
- Usage tracking and pricing enforcement
- @bijou in-chat commands
- / command discovery
- Auto-reporting system
- Human handover queue
- Function calling orchestration
- Client onboarding

All features are feature-flagged and can be enabled/disabled via environment variables.

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Version: 1.0.0
"""

from .command_handler import CommandHandler
from .function_caller import FunctionCaller
from .handover_system import EscalationPriority, EscalationStatus, HandoverSystem
from .lead_converter import LeadConverter
from .persona_manager import PersonaManager
from .pricing_engine import PricingEngine, SubscriptionTier
from .reporting_engine import ReportingEngine
from .tenant_manager import TenantManager

__all__ = [
    "CommandHandler",
    "LeadConverter",
    "PersonaManager",
    "PricingEngine",
    "SubscriptionTier",
    "TenantManager",
    "ReportingEngine",
    "FunctionCaller",
    "HandoverSystem",
    "EscalationPriority",
    "EscalationStatus",
]

__version__ = "1.0.0"
