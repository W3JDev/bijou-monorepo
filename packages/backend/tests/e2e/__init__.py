"""
Bijou AI - End-to-End Test Suite
=================================

Comprehensive E2E tests for production deployment validation.

Test Organization:
- conftest.py: Shared fixtures and configuration
- test_security.py: Security and tenant isolation tests (P0)
- test_whatsapp.py: WhatsApp integration tests (P0)
- test_dashboard_api.py: Dashboard API tests (P0)

Priority Levels:
- P0: Must pass (deployment blocking)
- P1: Should pass (requires investigation if fails)
- P2: Nice to have (monitoring only)

Author: @qa-engineer
"""

__version__ = "1.0.0"
