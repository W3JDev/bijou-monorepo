"""
Unit Tests — Tenant Isolation Fixes
=====================================

Tests for the JID routing and multi-tenant message persistence fixes
introduced in this sprint (migrations 018–020).

Covers:
  1. build_conversation_key()          — tenant-scoped key construction
  2. normalize_device_jid()            — device suffix stripping
  3. resolve_phone_jid() — fast-path   — no DB call for non-LID JIDs
  4. resolve_phone_jid() — LID mapping — returns phone_jid from DB row
  5. resolve_phone_jid() — DB error    — returns None gracefully
  6. _save_message() new columns       — device_jid / chat_type / conversation_key
                                         written to Supabase INSERT payload

Author: W3J Bijou AI Backend Team
Marker: pytest -m unit
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

W3J_TENANT_ID = "29d48db4-075f-45ee-8c00-a57f8fd3016a"
DEVICE_JID    = "60174106981@s.whatsapp.net"
DEVICE_RAW    = "60174106981:2@s.whatsapp.net"   # with :2 device suffix
CHAT_JID      = "60123456789@s.whatsapp.net"
LID_JID       = "88304745713870@lid"
GROUP_JID     = "120363000000000001@g.us"


# ─────────────────────────────────────────────────────────────────────────────
# Test Case 1 — build_conversation_key()
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestBuildConversationKey:
    """Tenant-scoped composite key construction."""

    def test_happy_path_returns_three_part_key(self):
        """
        GIVEN: valid tenant_id, device_jid, chat_jid
        WHEN:  build_conversation_key() is called
        THEN:  returns "<tenant_id>::<device_jid>::<chat_jid>"
        """
        from src.core.jid_utils import build_conversation_key

        result = build_conversation_key(W3J_TENANT_ID, DEVICE_JID, CHAT_JID)

        assert result == f"{W3J_TENANT_ID}::{DEVICE_JID}::{CHAT_JID}"

    def test_lid_chat_jid_included_verbatim(self):
        """LID JIDs must be stored verbatim — no normalization at key level."""
        from src.core.jid_utils import build_conversation_key

        result = build_conversation_key(W3J_TENANT_ID, DEVICE_JID, LID_JID)

        assert result.endswith(f"::{LID_JID}")
        assert result.startswith(W3J_TENANT_ID)

    def test_none_tenant_id_falls_back_to_empty_string(self):
        """
        GIVEN: tenant_id is None (routing failed)
        WHEN:  build_conversation_key() is called
        THEN:  tenant segment is empty string (no crash)
        """
        from src.core.jid_utils import build_conversation_key

        result = build_conversation_key(None, DEVICE_JID, CHAT_JID)

        # Key is still valid, just missing tenant prefix
        assert result == f"::{DEVICE_JID}::{CHAT_JID}"

    def test_none_device_jid_falls_back_to_empty_string(self):
        """device_jid None → empty string segment (bridge didn't send business_jid)."""
        from src.core.jid_utils import build_conversation_key

        result = build_conversation_key(W3J_TENANT_ID, None, CHAT_JID)

        assert result == f"{W3J_TENANT_ID}::::{CHAT_JID}"

    def test_all_none_returns_two_separators(self):
        """All None args → "::::::" — ugly but never raises."""
        from src.core.jid_utils import build_conversation_key

        result = build_conversation_key(None, None, None)

        assert result == "::::"

    def test_different_tenants_produce_different_keys_for_same_chat(self):
        """
        Two tenants who share a device_jid MUST get different conversation keys
        to prevent cross-tenant data bleed.
        """
        from src.core.jid_utils import build_conversation_key

        tenant_a = "aaaaaaaa-0000-0000-0000-000000000001"
        tenant_b = "bbbbbbbb-0000-0000-0000-000000000002"

        key_a = build_conversation_key(tenant_a, DEVICE_JID, CHAT_JID)
        key_b = build_conversation_key(tenant_b, DEVICE_JID, CHAT_JID)

        assert key_a != key_b, "Two tenants must never share the same conversation key"


# ─────────────────────────────────────────────────────────────────────────────
# Test Case 2 — normalize_device_jid()
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestNormalizeDeviceJid:
    """Device suffix (:N) stripping from WhatsApp business JIDs."""

    def test_strips_device_suffix(self):
        """
        GIVEN: JID with :2 device suffix (e.g. "60174106981:2@s.whatsapp.net")
        WHEN:  normalize_device_jid() is called
        THEN:  returns JID without device suffix
        """
        from src.core.jid_utils import normalize_device_jid

        result = normalize_device_jid(DEVICE_RAW)

        assert result == DEVICE_JID

    def test_idempotent_on_already_normalized_jid(self):
        """Calling twice on an already-normalized JID returns same value."""
        from src.core.jid_utils import normalize_device_jid

        result = normalize_device_jid(DEVICE_JID)

        assert result == DEVICE_JID

    def test_lid_jid_not_modified(self):
        """LID JIDs have no device suffix — must be returned unchanged."""
        from src.core.jid_utils import normalize_device_jid

        result = normalize_device_jid(LID_JID)

        assert result == LID_JID

    def test_group_jid_not_modified(self):
        """Group JIDs contain no :N suffix — must be returned unchanged."""
        from src.core.jid_utils import normalize_device_jid

        result = normalize_device_jid(GROUP_JID)

        assert result == GROUP_JID

    def test_empty_string_returns_empty_string(self):
        """Empty input → empty output (no crash)."""
        from src.core.jid_utils import normalize_device_jid

        result = normalize_device_jid("")

        assert result == ""

    def test_high_device_number(self):
        """Device suffix can be multi-digit (e.g. :12)."""
        from src.core.jid_utils import normalize_device_jid

        raw    = "60174106981:12@s.whatsapp.net"
        result = normalize_device_jid(raw)

        assert result == DEVICE_JID


# ─────────────────────────────────────────────────────────────────────────────
# Test Case 3 — resolve_phone_jid() fast-path (non-LID JID)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestResolvePhoneJidFastPath:
    """
    resolve_phone_jid() must return None immediately for non-LID JIDs
    WITHOUT making any database call.
    """

    @pytest.mark.asyncio
    async def test_standard_jid_returns_none_without_db_call(self):
        """
        GIVEN: chat_jid is a standard phone JID (not @lid)
        WHEN:  resolve_phone_jid() is called
        THEN:  returns None immediately; supabase.table() is NEVER called
        """
        from src.core.jid_utils import resolve_phone_jid

        mock_supabase = MagicMock()

        result = await resolve_phone_jid(mock_supabase, CHAT_JID, W3J_TENANT_ID)

        assert result is None
        mock_supabase.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_group_jid_returns_none_without_db_call(self):
        """Group JIDs are not @lid — must also fast-path."""
        from src.core.jid_utils import resolve_phone_jid

        mock_supabase = MagicMock()

        result = await resolve_phone_jid(mock_supabase, GROUP_JID, W3J_TENANT_ID)

        assert result is None
        mock_supabase.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_supabase_client_returns_none(self):
        """If supabase client is None, must return None gracefully (no AttributeError)."""
        from src.core.jid_utils import resolve_phone_jid

        result = await resolve_phone_jid(None, LID_JID, W3J_TENANT_ID)

        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Test Case 4 — resolve_phone_jid() LID → phone_jid mapping found
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestResolvePhoneJidMapping:
    """resolve_phone_jid() with a LID JID that has a known mapping in jid_mappings."""

    @pytest.mark.asyncio
    async def test_returns_phone_jid_from_db(self):
        """
        GIVEN: chat_jid ends with @lid AND jid_mappings has a matching row
        WHEN:  resolve_phone_jid() is called
        THEN:  returns the phone_jid from the DB row
        """
        from src.core.jid_utils import resolve_phone_jid

        # Build mock Supabase query chain
        mock_execute = MagicMock()
        mock_execute.data = [{"phone_jid": CHAT_JID}]

        mock_table = MagicMock()
        mock_table.select.return_value  = mock_table
        mock_table.eq.return_value      = mock_table
        mock_table.limit.return_value   = mock_table
        mock_table.execute.return_value = mock_execute

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        result = await resolve_phone_jid(mock_supabase, LID_JID, W3J_TENANT_ID)

        assert result == CHAT_JID

    @pytest.mark.asyncio
    async def test_queries_correct_table_and_filters(self):
        """
        The query must filter by BOTH tenant_id AND lid_jid for tenant isolation.
        """
        from src.core.jid_utils import resolve_phone_jid

        mock_execute = MagicMock()
        mock_execute.data = []   # no mapping — but we care about the call args

        mock_table = MagicMock()
        mock_table.select.return_value  = mock_table
        mock_table.eq.return_value      = mock_table
        mock_table.limit.return_value   = mock_table
        mock_table.execute.return_value = mock_execute

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        await resolve_phone_jid(mock_supabase, LID_JID, W3J_TENANT_ID)

        # Verify table name
        mock_supabase.table.assert_called_once_with("jid_mappings")

        # Verify both tenant_id and lid_jid filters were applied
        eq_calls = mock_table.eq.call_args_list
        eq_keys  = [c[0][0] for c in eq_calls]  # first positional arg of each .eq()
        assert "tenant_id" in eq_keys, "Query must filter by tenant_id"
        assert "lid_jid"   in eq_keys, "Query must filter by lid_jid"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_mapping_row(self):
        """
        GIVEN: chat_jid is @lid BUT jid_mappings has no matching row
        WHEN:  resolve_phone_jid() is called
        THEN:  returns None (mapping not yet learned)
        """
        from src.core.jid_utils import resolve_phone_jid

        mock_execute = MagicMock()
        mock_execute.data = []  # no row

        mock_table = MagicMock()
        mock_table.select.return_value  = mock_table
        mock_table.eq.return_value      = mock_table
        mock_table.limit.return_value   = mock_table
        mock_table.execute.return_value = mock_execute

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        result = await resolve_phone_jid(mock_supabase, LID_JID, W3J_TENANT_ID)

        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Test Case 5 — resolve_phone_jid() DB error → graceful None
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestResolvePhoneJidDbError:
    """resolve_phone_jid() must swallow DB exceptions and return None."""

    @pytest.mark.asyncio
    async def test_db_exception_returns_none(self):
        """
        GIVEN: The Supabase query raises an exception (network, RLS, etc.)
        WHEN:  resolve_phone_jid() is called
        THEN:  returns None — does NOT propagate the exception
        """
        from src.core.jid_utils import resolve_phone_jid

        mock_table = MagicMock()
        mock_table.select.return_value  = mock_table
        mock_table.eq.return_value      = mock_table
        mock_table.limit.return_value   = mock_table
        mock_table.execute.side_effect  = Exception("Supabase connection refused")

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Should NOT raise — must return None
        result = await resolve_phone_jid(mock_supabase, LID_JID, W3J_TENANT_ID)

        assert result is None

    @pytest.mark.asyncio
    async def test_rls_error_returns_none(self):
        """Simulate an RLS permission error — same graceful behavior expected."""
        from src.core.jid_utils import resolve_phone_jid

        mock_table = MagicMock()
        mock_table.select.return_value  = mock_table
        mock_table.eq.return_value      = mock_table
        mock_table.limit.return_value   = mock_table
        mock_table.execute.side_effect  = PermissionError("RLS policy violation")

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        result = await resolve_phone_jid(mock_supabase, LID_JID, W3J_TENANT_ID)

        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Test Case 6 — _save_message() new columns written to Supabase INSERT
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestSaveMessageNewColumns:
    """
    _save_message() must write device_jid, phone_jid, chat_type,
    conversation_key, and is_system_event to the Supabase INSERT payload.
    """

    def _make_bijou_instance(self, mock_supabase):
        """
        Build a minimal Bijou instance with the required attributes for
        _save_message() to run without needing the full FastAPI app.
        """
        # Import the class — full app startup is NOT triggered; we only need
        # the method.  We patch out the supabase client directly.
        from src.core.bijou import BijouAI  # noqa: F401 (imported for patching)

        with patch("src.core.bijou.BijouAI.__init__", return_value=None):
            import src.core.bijou as bijou_module
            obj = bijou_module.BijouAI.__new__(bijou_module.BijouAI)

        # Wire up only what _save_message() reads
        obj.db_conn      = mock_supabase
        obj.db_type      = "supabase"   # must be "supabase" to reach the INSERT branch
        obj.logger       = MagicMock()
        # Stub out helper methods that do string parsing — keep them simple
        obj._extract_phone_number  = lambda jid: jid.split("@")[0] if jid else ""
        obj._extract_customer_name = lambda jid: None
        # conversation_history and async helpers not needed for this test
        return obj

    @pytest.mark.asyncio
    async def test_individual_message_writes_new_columns(self):
        """
        GIVEN: _save_message() called with device_jid and chat_type="individual"
        WHEN:  Supabase INSERT is executed
        THEN:  payload contains device_jid, chat_type, conversation_key,
               is_system_event=False, and phone_jid=None (non-LID chat_jid)
        """
        captured_payload = {}

        # Build mock Supabase that captures the INSERT dict
        mock_insert_result = MagicMock()
        mock_insert_result.execute.return_value = MagicMock(data=[{"id": "abc"}])

        mock_table = MagicMock()
        mock_table.insert.side_effect = lambda payload: (
            captured_payload.update(payload) or mock_insert_result
        )

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Patch resolve_phone_jid to avoid real DB call
        with patch(
            "src.core.bijou.resolve_phone_jid",
            new=AsyncMock(return_value=None),
        ), patch(
            "src.core.bijou.build_conversation_key",
            return_value=f"{W3J_TENANT_ID}::{DEVICE_JID}::{CHAT_JID}",
        ):
            obj = self._make_bijou_instance(mock_supabase)
            await obj._save_message(
                chat_jid   = CHAT_JID,
                tenant_id  = W3J_TENANT_ID,
                role       = "user",
                content    = "Hello Bijou",
                device_jid = DEVICE_JID,
                chat_type  = "individual",
            )

        # Verify the five new columns are present in the INSERT payload
        assert "device_jid"       in captured_payload, "device_jid missing from INSERT"
        assert "chat_type"        in captured_payload, "chat_type missing from INSERT"
        assert "conversation_key" in captured_payload, "conversation_key missing from INSERT"
        assert "is_system_event"  in captured_payload, "is_system_event missing from INSERT"
        assert "phone_jid"        in captured_payload, "phone_jid missing from INSERT"

        # Verify values
        assert captured_payload["device_jid"]       == DEVICE_JID
        assert captured_payload["chat_type"]         == "individual"
        assert captured_payload["is_system_event"]   == False  # noqa: E712
        assert captured_payload["phone_jid"]         is None   # CHAT_JID is not @lid
        assert W3J_TENANT_ID in captured_payload["conversation_key"]
        assert DEVICE_JID    in captured_payload["conversation_key"]
        assert CHAT_JID      in captured_payload["conversation_key"]

    @pytest.mark.asyncio
    async def test_group_message_sets_chat_type_group(self):
        """
        GIVEN: chat_jid ends with @g.us
        WHEN:  _save_message() is called with chat_type="group"
        THEN:  INSERT payload has chat_type == "group"
        """
        captured_payload = {}

        mock_insert_result = MagicMock()
        mock_insert_result.execute.return_value = MagicMock(data=[{"id": "xyz"}])

        mock_table = MagicMock()
        mock_table.insert.side_effect = lambda payload: (
            captured_payload.update(payload) or mock_insert_result
        )

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        with patch(
            "src.core.bijou.resolve_phone_jid",
            new=AsyncMock(return_value=None),
        ), patch(
            "src.core.bijou.build_conversation_key",
            return_value=f"{W3J_TENANT_ID}::{DEVICE_JID}::{GROUP_JID}",
        ):
            obj = self._make_bijou_instance(mock_supabase)
            await obj._save_message(
                chat_jid   = GROUP_JID,
                tenant_id  = W3J_TENANT_ID,
                role       = "assistant",
                content    = "Welcome to the group!",
                device_jid = DEVICE_JID,
                chat_type  = "group",
            )

        assert captured_payload.get("chat_type") == "group"

    @pytest.mark.asyncio
    async def test_lid_message_triggers_phone_jid_resolution(self):
        """
        GIVEN: chat_jid ends with @lid
        WHEN:  _save_message() is called
        THEN:  resolve_phone_jid() is awaited exactly once and the returned
               phone_jid is stored in the INSERT payload
        """
        captured_payload = {}

        mock_insert_result = MagicMock()
        mock_insert_result.execute.return_value = MagicMock(data=[{"id": "lid-test"}])

        mock_table = MagicMock()
        mock_table.insert.side_effect = lambda payload: (
            captured_payload.update(payload) or mock_insert_result
        )

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        resolved_phone = CHAT_JID  # the "known" phone JID for this LID

        mock_resolve = AsyncMock(return_value=resolved_phone)

        with patch("src.core.bijou.resolve_phone_jid", new=mock_resolve), patch(
            "src.core.bijou.build_conversation_key",
            return_value=f"{W3J_TENANT_ID}::{DEVICE_JID}::{LID_JID}",
        ):
            obj = self._make_bijou_instance(mock_supabase)
            await obj._save_message(
                chat_jid   = LID_JID,
                tenant_id  = W3J_TENANT_ID,
                role       = "user",
                content    = "Hey from @lid",
                device_jid = DEVICE_JID,
                chat_type  = "individual",
            )

        # resolve_phone_jid must have been called once
        mock_resolve.assert_awaited_once()

        # The resolved phone JID must appear in the INSERT payload
        assert captured_payload.get("phone_jid") == resolved_phone

    @pytest.mark.asyncio
    async def test_none_device_jid_does_not_crash(self):
        """
        GIVEN: device_jid is None (bridge didn't send business_jid)
        WHEN:  _save_message() is called
        THEN:  INSERT succeeds; device_jid=None; conversation_key computed safely
        """
        captured_payload = {}

        mock_insert_result = MagicMock()
        mock_insert_result.execute.return_value = MagicMock(data=[{"id": "no-dev"}])

        mock_table = MagicMock()
        mock_table.insert.side_effect = lambda payload: (
            captured_payload.update(payload) or mock_insert_result
        )

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        with patch(
            "src.core.bijou.resolve_phone_jid",
            new=AsyncMock(return_value=None),
        ), patch(
            "src.core.bijou.build_conversation_key",
            return_value=f"{W3J_TENANT_ID}::::{CHAT_JID}",
        ):
            obj = self._make_bijou_instance(mock_supabase)
            # Should not raise even with device_jid=None
            await obj._save_message(
                chat_jid   = CHAT_JID,
                tenant_id  = W3J_TENANT_ID,
                role       = "user",
                content    = "No device JID test",
                device_jid = None,      # <── the case under test
                chat_type  = "individual",
            )

        # conversation_key is computed — it should still appear in payload
        assert "conversation_key" in captured_payload


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "unit"])
