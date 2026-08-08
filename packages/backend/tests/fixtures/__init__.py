"""
Test Fixtures
=============

Synthetic test data for automated testing.

Fixtures:
- test_tenants.py - 4 business type tenants with realistic data

Usage:
    from tests.fixtures.test_tenants import get_test_tenants

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Date: 2026-02-07
"""

from tests.fixtures.test_tenants import (
    get_all_knowledge,
    get_dental_knowledge,
    get_dental_tenant,
    get_fnb_knowledge,
    get_fnb_tenant,
    get_gaming_knowledge,
    get_gaming_tenant,
    get_knowledge_by_type,
    get_property_knowledge,
    get_property_tenant,
    get_tenant_by_type,
    get_test_tenants,
)

__all__ = [
    "get_test_tenants",
    "get_property_tenant",
    "get_gaming_tenant",
    "get_dental_tenant",
    "get_fnb_tenant",
    "get_property_knowledge",
    "get_gaming_knowledge",
    "get_dental_knowledge",
    "get_fnb_knowledge",
    "get_all_knowledge",
    "get_tenant_by_type",
    "get_knowledge_by_type",
]
