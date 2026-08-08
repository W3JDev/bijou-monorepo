"""
Bijou AI - Test Suite
======================

Automated E2E testing suite with mock WhatsApp and synthetic tenants.

Test organization:
- tests/test_e2e_full_suite.py - Complete E2E test suite (20 tests)
- tests/fixtures/ - Synthetic test data (4 business types)
- tests/mocks/ - WhatsApp bridge simulator
- tests/conftest.py - Pytest configuration & fixtures

Quick start:
    pytest tests/ -v              # Run all tests
    pytest tests/ -v -m smoke     # Run smoke tests only

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Date: 2026-02-07
"""

__version__ = "1.0.0"
