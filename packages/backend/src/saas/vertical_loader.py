"""
Vertical Template Loader
=========================

Loads domain-specific AI instructions from vertical_templates table and injects
them into the AI's system prompt based on tenant's assigned vertical.

Verticals:
- property: Real estate (sales & rentals) with calendar booking instructions
- dental: Dental clinics with appointment booking
- fnb: Food & beverage with reservation system
- w3j: W3J Consulting (tech recruiting, AI automation)

Author: W3J Consulting
Date: 2026-03-04
"""

import logging
import os
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class VerticalTemplateLoader:
    """
    Loads and caches vertical templates from database.

    Flow:
    1. Check if vertical templates enabled (ENABLE_VERTICAL_TEMPLATES)
    2. Load tenant's assigned vertical from tenant_verticals table
    3. Fetch domain_prompt from vertical_templates table
    4. Inject into AI's system prompt
    """

    def __init__(self, supabase_client=None):
        """
        Initialize vertical template loader.

        Args:
            supabase_client: Supabase client instance
        """
        self.db = supabase_client
        self.enabled = os.getenv("ENABLE_VERTICAL_TEMPLATES", "false").lower() == "true"

        # Cache templates to avoid repeated DB calls
        self._template_cache: Dict[str, Dict] = {}
        self._cache_timestamp: Dict[str, datetime] = {}
        self._cache_ttl_seconds = 300  # 5 minutes

        if self.enabled:
            logger.info("✅ Vertical Template Loader initialized (enabled=true)")
        else:
            logger.info("✅ Vertical Template Loader initialized (enabled=false)")

    def get_tenant_vertical_prompt(self, tenant_id: str) -> Optional[str]:
        """
        Get domain-specific prompt for tenant's assigned vertical.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Domain prompt string or None if not found
        """
        if not self.enabled:
            logger.debug("Vertical templates disabled (ENABLE_VERTICAL_TEMPLATES=false)")
            return None

        if not self.db:
            logger.warning("No database client available for vertical template loading")
            return None

        if not tenant_id:
            logger.warning("No tenant_id provided for vertical template loading")
            return None

        try:
            # Step 1: Get tenant's assigned vertical
            vertical_mapping = self.db.table("tenant_verticals")\
                .select("vertical_id, enabled, custom_overrides")\
                .eq("tenant_id", tenant_id)\
                .eq("enabled", True)\
                .execute()

            if not vertical_mapping.data:
                logger.debug(f"No vertical assigned to tenant {tenant_id}")
                return None

            vertical_id = vertical_mapping.data[0]["vertical_id"]
            custom_overrides = vertical_mapping.data[0].get("custom_overrides", {})

            logger.info(f"📋 Tenant {tenant_id[:8]}... assigned to vertical: {vertical_id}")

            # Step 2: Load vertical template (use cache if fresh)
            domain_prompt = self._get_vertical_template(vertical_id)

            if not domain_prompt:
                logger.warning(f"No domain prompt found for vertical: {vertical_id}")
                return None

            # Step 3: Apply custom overrides (if any)
            if custom_overrides:
                logger.debug(f"Applying custom overrides for tenant {tenant_id[:8]}...")
                # Future: support custom_overrides to modify parts of domain_prompt
                # For now, just return the base template

            logger.info(f"✅ Loaded vertical prompt for {vertical_id} ({len(domain_prompt)} chars)")
            return domain_prompt

        except Exception as e:
            logger.error(f"Error loading vertical template for tenant {tenant_id}: {e}")
            return None

    def _get_vertical_template(self, vertical_id: str) -> Optional[str]:
        """
        Get vertical template from cache or database.

        Args:
            vertical_id: Vertical identifier (property, dental, fnb, w3j)

        Returns:
            Domain prompt string or None
        """
        # Check cache
        if vertical_id in self._template_cache:
            cache_age = (datetime.now() - self._cache_timestamp.get(vertical_id, datetime.min)).total_seconds()
            if cache_age < self._cache_ttl_seconds:
                logger.debug(f"Using cached template for {vertical_id} (age: {cache_age:.0f}s)")
                return self._template_cache[vertical_id].get("domain_prompt")

        # Load from database
        try:
            result = self.db.table("vertical_templates")\
                .select("vertical_id, vertical_name, domain_prompt")\
                .eq("vertical_id", vertical_id)\
                .execute()

            if not result.data:
                logger.warning(f"Vertical template not found: {vertical_id}")
                return None

            template_data = result.data[0]

            # Cache it
            self._template_cache[vertical_id] = template_data
            self._cache_timestamp[vertical_id] = datetime.now()

            logger.debug(f"Loaded and cached template for {vertical_id}")
            return template_data.get("domain_prompt")

        except Exception as e:
            logger.error(f"Database error loading vertical template {vertical_id}: {e}")
            return None

    def get_available_verticals(self) -> list:
        """
        Get list of all available vertical templates.

        Returns:
            List of dicts with vertical_id and vertical_name
        """
        if not self.enabled or not self.db:
            return []

        try:
            result = self.db.table("vertical_templates")\
                .select("vertical_id, vertical_name")\
                .execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Error fetching available verticals: {e}")
            return []

    def clear_cache(self):
        """Clear the template cache (useful after template updates)."""
        self._template_cache.clear()
        self._cache_timestamp.clear()
        logger.info("Vertical template cache cleared")


# ============================================================================
# Convenience function
# ============================================================================

def create_vertical_loader(supabase_client=None) -> VerticalTemplateLoader:
    """
    Factory function to create VerticalTemplateLoader instance.

    Args:
        supabase_client: Supabase client instance

    Returns:
        VerticalTemplateLoader instance
    """
    return VerticalTemplateLoader(supabase_client=supabase_client)
