"""
JID Utility Functions
=====================

Helper functions for normalizing and interpreting WhatsApp JIDs (Jabber IDs).

WhatsApp JID formats:
  - Standard phone:   60174106981@s.whatsapp.net
  - Device suffix:    60174106981:2@s.whatsapp.net   (same account, different device)
  - Linked device:    88304745713870@lid              (privacy-preserving ID — no phone)
  - Group:            120363XXXXXXXXXX@g.us

Author: W3J Bijou AI Backend Team
"""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def normalize_device_jid(jid: str) -> str:
    """
    Strip the device-suffix (`:N`) from a WhatsApp business JID.

    The old bridge sends `business_jid` in the form:
        60174106981:2@s.whatsapp.net
    The canonical form (used in whatsapp_devices.whatsapp_jid) is:
        60174106981@s.whatsapp.net

    Args:
        jid: Raw JID string, possibly containing a `:N` device suffix.

    Returns:
        Normalized JID with device suffix removed.

    Examples:
        >>> normalize_device_jid("60174106981:2@s.whatsapp.net")
        '60174106981@s.whatsapp.net'
        >>> normalize_device_jid("60174106981@s.whatsapp.net")
        '60174106981@s.whatsapp.net'
        >>> normalize_device_jid("88304745713870@lid")
        '88304745713870@lid'
    """
    if not jid:
        return jid
    # Match "localpart:N@domain" and return "localpart@domain"
    normalized = re.sub(r":(\d+)@", "@", jid)
    return normalized


def is_lid_jid(jid: str) -> bool:
    """
    Return True if the JID is a linked-device (LID) identifier.

    LID JIDs end with `@lid` and do NOT contain a phone number.
    They are assigned by WhatsApp for privacy-preserving contact references.

    Args:
        jid: WhatsApp JID string.

    Returns:
        True if the JID ends with `@lid`, False otherwise.

    Examples:
        >>> is_lid_jid("88304745713870@lid")
        True
        >>> is_lid_jid("60174106981@s.whatsapp.net")
        False
    """
    if not jid:
        return False
    return jid.endswith("@lid")


def extract_phone(jid: str) -> Optional[str]:
    """
    Extract the phone number portion from a standard WhatsApp JID.

    Returns None for LID JIDs (which have no phone number) and group JIDs.

    Args:
        jid: WhatsApp JID string.

    Returns:
        Phone number string (digits only, no + prefix), or None.

    Examples:
        >>> extract_phone("60174106981@s.whatsapp.net")
        '60174106981'
        >>> extract_phone("60174106981:2@s.whatsapp.net")
        '60174106981'
        >>> extract_phone("88304745713870@lid")
        None
        >>> extract_phone("120363000000000000@g.us")
        None
    """
    if not jid:
        return None
    if is_lid_jid(jid):
        return None
    if jid.endswith("@g.us"):
        return None
    # Strip device suffix then domain
    local = re.sub(r":(\d+)@", "@", jid).split("@")[0]
    # Return only if it looks like a phone number (all digits)
    return local if local.isdigit() else None


def conversation_key(device_jid: str, chat_jid: str) -> str:
    """
    Build a deterministic composite key that uniquely identifies a
    conversation between a specific business device and a customer JID.

    Used to detect the same thread across messages and avoid cross-device
    collisions when two devices share a phone number.

    Args:
        device_jid: Normalized business device JID (no `:N` suffix).
        chat_jid:   Customer or group JID.

    Returns:
        A `::` separated composite string, e.g.
        `60174106981@s.whatsapp.net::88304745713870@lid`

    Examples:
        >>> conversation_key("60174106981@s.whatsapp.net", "88304745713870@lid")
        '60174106981@s.whatsapp.net::88304745713870@lid'
    """
    device = device_jid or ""
    chat = chat_jid or ""
    return f"{device}::{chat}"


def build_conversation_key(tenant_id: str, device_jid: str, chat_jid: str) -> str:
    """
    Build a deterministic composite key scoped to a tenant.

    Extends `conversation_key` by prepending the tenant UUID, ensuring
    there are no collisions across tenants even if they share device JIDs
    (e.g. two tenants on the same WhatsApp number during migration).

    Args:
        tenant_id:  UUID of the tenant (may be None — falls back to empty string).
        device_jid: Normalized business device JID (no `:N` suffix).
        chat_jid:   Customer or group JID.

    Returns:
        A `::` separated composite string, e.g.
        `29d48db4-075f-45ee-8c00-a57f8fd3016a::60174106981@s.whatsapp.net::88304745713870@lid`

    Examples:
        >>> build_conversation_key(
        ...     "29d48db4-075f-45ee-8c00-a57f8fd3016a",
        ...     "60174106981@s.whatsapp.net",
        ...     "88304745713870@lid",
        ... )
        '29d48db4-075f-45ee-8c00-a57f8fd3016a::60174106981@s.whatsapp.net::88304745713870@lid'
        >>> build_conversation_key(None, None, "60174106981@s.whatsapp.net")
        '::::60174106981@s.whatsapp.net'
    """
    tid = tenant_id or ""
    device = device_jid or ""
    chat = chat_jid or ""
    return f"{tid}::{device}::{chat}"


def is_group_chat(chat_jid: str) -> bool:
    """
    Detect if JID is a group chat.
    
    WhatsApp JID formats:
    - Direct:     60123456789@s.whatsapp.net
    - Direct (lid): 84950644740196@lid (linked device)
    - Group:      120363XXXXXXXXXX@g.us
    - Broadcast:  status@broadcast
    - Newsletter: newsletter@newsletter
    
    Args:
        chat_jid: WhatsApp JID string
        
    Returns:
        True if group/broadcast, False if direct message
        
    Examples:
        >>> is_group_chat("60123456789@s.whatsapp.net")
        False
        >>> is_group_chat("84950644740196@lid")
        False
        >>> is_group_chat("120363123456789@g.us")
        True
        >>> is_group_chat("status@broadcast")
        True
        >>> is_group_chat(None)
        False
    """
    if not chat_jid:
        return False
    
    # Group chats end with @g.us
    if chat_jid.endswith("@g.us"):
        return True
    
    # Broadcast lists (status updates, newsletters)
    if chat_jid.endswith("@broadcast") or chat_jid.endswith("@newsletter"):
        return True
    
    # Direct messages (including linked devices)
    return False


async def resolve_phone_jid(
    supabase_client: Any,
    chat_jid: str,
    tenant_id: str,
) -> Optional[str]:
    """
    Resolve a linked-device (LID) JID to its canonical phone JID.

    Queries the `jid_mappings` table for a previously stored mapping of
    ``lid_jid → phone_jid``.  Returns ``None`` (gracefully) on any error
    so callers can proceed without a resolved phone JID.

    This function is a **no-op** for non-LID JIDs: it returns ``None``
    immediately without hitting the database.

    Args:
        supabase_client: An initialised Supabase client instance
                         (``supabase_py`` or ``supabase-py`` v2 client).
        chat_jid:        The JID to look up.  If it does not end with
                         ``@lid`` this function returns ``None`` instantly.
        tenant_id:       UUID of the tenant — used to scope the lookup so
                         that LID mappings from one tenant cannot bleed into
                         another.

    Returns:
        The ``phone_jid`` string if a mapping exists, otherwise ``None``.

    Examples:
        >>> # Non-LID JID — no DB call made
        >>> await resolve_phone_jid(client, "60174106981@s.whatsapp.net", tid)
        None
        >>> # LID JID with existing mapping
        >>> await resolve_phone_jid(client, "88304745713870@lid", tid)
        '60174106981@s.whatsapp.net'
        >>> # LID JID with no mapping yet
        >>> await resolve_phone_jid(client, "99999999999999@lid", tid)
        None
    """
    # Fast-path: skip DB call entirely for non-LID JIDs
    if not is_lid_jid(chat_jid):
        return None

    if not supabase_client:
        logger.debug("resolve_phone_jid: no supabase client, skipping lookup")
        return None

    try:
        response = (
            supabase_client
            .table("jid_mappings")
            .select("phone_jid")
            .eq("tenant_id", tenant_id)
            .eq("lid_jid", chat_jid)
            .limit(1)
            .execute()
        )
        if response.data:
            phone_jid = response.data[0].get("phone_jid")
            logger.debug(
                f"resolve_phone_jid: {chat_jid} → {phone_jid} (tenant={tenant_id})"
            )
            return phone_jid
        return None
    except Exception as exc:
        logger.warning(
            f"resolve_phone_jid: failed to query jid_mappings for {chat_jid}: {exc}"
        )
        return None
