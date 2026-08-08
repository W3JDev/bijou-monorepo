# src/saas/orchestration.py

import logging
import os
from typing import Optional

import supabase
from fastapi import HTTPException
from supabase import Client, PostgrestAPIResponse

logger = logging.getLogger(__name__)

# --- Configuration ---
# Using environment variables is best practice.
BI_SUPABASE_URL = os.environ.get("BI_SUPABASE_URL", "https://jryalnbmsxfxihurfwmc.supabase.co")
BI_SUPABASE_KEY = os.environ.get("BI_SUPABASE_SERVICE_KEY") # Ensure this is set in your environment

if not BI_SUPABASE_KEY:
    logger.fatal("BI_SUPABASE_SERVICE_KEY environment variable not set.")
    bi_db_client = None
else:
    try:
        bi_db_client: Client = supabase.create_client(BI_SUPABASE_URL, BI_SUPABASE_KEY)
    except Exception as e:
        logger.fatal(f"Could not initialize BI Supabase client: {e}")
        bi_db_client = None

# --- Database Interaction Functions for BI Database ---

def find_available_bridge() -> Optional[str]:
    """
    Connects to the W3J-BI database, queries the bridge_pool table,
    and returns the URL of the most available bridge.

    Returns:
        The URL of the bridge with the lowest device_count, or None if none are active.
    """
    if not bi_db_client:
        raise HTTPException(status_code=500, detail="BI Database client not initialized.")

    try:
        response: PostgrestAPIResponse = bi_db_client.table("bridge_pool") \
            .select("bridge_url") \
            .eq("status", "active") \
            .order("device_count", desc=False) \
            .limit(1) \
            .execute()

        if response.data:
            return response.data[0]['bridge_url']
        else:
            return None
    except Exception as e:
        logger.error(f"Could not query bridge_pool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query bridge pool: {e}")


def increment_bridge_device_count(bridge_url: str) -> bool:
    """
    Increments the device_count for a given bridge in the BI database via RPC.

    Args:
        bridge_url: The URL of the bridge to update.

    Returns:
        True if successful, False otherwise.
    """
    if not bi_db_client:
        raise HTTPException(status_code=500, detail="BI Database client not initialized.")

    try:
        response = bi_db_client.rpc('increment_device_count', {'url': bridge_url}).execute()

        if response.error:
             raise Exception(response.error.message)

        logger.info(f"Successfully incremented device count for {bridge_url}")
        return True

    except Exception as e:
        logger.error(f"Could not increment device count for {bridge_url}: {e}")
        return False
