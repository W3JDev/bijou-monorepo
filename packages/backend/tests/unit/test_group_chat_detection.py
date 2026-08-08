"""
Unit tests for group chat detection functionality.

Tests the is_group_chat() function in src/core/jid_utils.py
to ensure proper detection of different WhatsApp JID formats.
"""

import pytest
from src.core.jid_utils import is_group_chat


class TestGroupChatDetection:
    """Test suite for group chat detection"""

    def test_detect_direct_message_standard(self):
        """Test detection of standard direct message JID"""
        assert is_group_chat("60123456789@s.whatsapp.net") == False

    def test_detect_direct_message_with_device_suffix(self):
        """Test detection of direct message JID with device suffix"""
        assert is_group_chat("60123456789:2@s.whatsapp.net") == False

    def test_detect_direct_message_lid(self):
        """Test detection of linked device (LID) JID"""
        assert is_group_chat("84950644740196@lid") == False

    def test_detect_group_chat(self):
        """Test detection of group chat JID"""
        assert is_group_chat("120363123456789@g.us") == True

    def test_detect_group_chat_short_id(self):
        """Test detection of group chat with short ID"""
        assert is_group_chat("120363000000000000@g.us") == True

    def test_detect_broadcast_status(self):
        """Test detection of status broadcast JID"""
        assert is_group_chat("status@broadcast") == True

    def test_detect_newsletter(self):
        """Test detection of newsletter JID"""
        assert is_group_chat("newsletter@newsletter") == True

    def test_handle_none_jid(self):
        """Test handling of None JID"""
        assert is_group_chat(None) == False

    def test_handle_empty_jid(self):
        """Test handling of empty string JID"""
        assert is_group_chat("") == False

    def test_handle_whitespace_jid(self):
        """Test handling of whitespace-only JID"""
        assert is_group_chat("   ") == False

    def test_malformed_jid_no_at_symbol(self):
        """Test handling of malformed JID without @ symbol"""
        assert is_group_chat("60123456789") == False

    def test_malformed_jid_incomplete(self):
        """Test handling of incomplete JID"""
        assert is_group_chat("60123456789@") == False

    def test_real_world_group_jid(self):
        """Test with real-world group chat JID format"""
        # Real group JIDs follow pattern: 120363 + timestamp + checksum
        assert is_group_chat("120363044893881949@g.us") == True

    def test_real_world_direct_jid_malaysia(self):
        """Test with real-world Malaysian phone number JID"""
        assert is_group_chat("60174106981@s.whatsapp.net") == False

    def test_real_world_direct_jid_singapore(self):
        """Test with real-world Singapore phone number JID"""
        assert is_group_chat("6581234567@s.whatsapp.net") == False


@pytest.mark.parametrize(
    "jid,expected",
    [
        # Direct messages
        ("60123456789@s.whatsapp.net", False),
        ("60123456789:2@s.whatsapp.net", False),
        ("84950644740196@lid", False),
        ("1234567890@s.whatsapp.net", False),
        # Group chats
        ("120363123456789@g.us", True),
        ("120363000000000000@g.us", True),
        ("120363044893881949@g.us", True),
        # Broadcasts
        ("status@broadcast", True),
        ("newsletter@newsletter", True),
        # Edge cases
        (None, False),
        ("", False),
        ("   ", False),
        ("invalid", False),
    ],
)
def test_group_chat_detection_parametrized(jid, expected):
    """Parametrized test for various JID formats"""
    assert is_group_chat(jid) == expected


if __name__ == "__main__":
    # Run tests with: pytest tests/unit/test_group_chat_detection.py -v
    pytest.main([__file__, "-v"])
