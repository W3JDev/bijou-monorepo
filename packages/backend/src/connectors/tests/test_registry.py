from src.connectors.base import Policy
from src.connectors.registry import build_registry


def test_sheets_append_row_is_composio_only():
    reg = build_registry()
    a = reg["sheets.append_row"]
    assert a.policy is Policy.COMPOSIO_ONLY
    assert a.composio_slug and a.native is None
    assert a.degrade_message


def test_email_send_is_native_only():
    reg = build_registry()
    assert reg["email.send"].policy is Policy.NATIVE_ONLY


def test_calendar_is_native_first_with_both_backends():
    reg = build_registry()
    a = reg["calendar.book_slot"]
    assert a.policy is Policy.NATIVE_FIRST and a.composio_slug
