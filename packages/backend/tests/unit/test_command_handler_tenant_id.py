"""Regression test for B2: @bijou owner commands crashed with TypeError because
_handle_bijou_command called _cmd_bookings/_cmd_crm_lookup/_cmd_send_to_contact/
_cmd_confirm_booking WITHOUT the required tenant_id positional arg.

With db_conn=None and bridge_url="" every helper hits its own guard and returns a
string — the point is that the call path REACHES that guard instead of raising
TypeError before it. Before the fix these four commands raised TypeError the
moment ENABLE_BIJOU_COMMANDS=true.
"""
import asyncio

from src.saas.command_handler import CommandHandler


def _handler():
    return CommandHandler(owner_jid="60190000000@s.whatsapp.net", db_conn=None, bridge_url="")


def _run(handler, command, args):
    cmd = {
        "command": command,
        "args": args,
        "chat_jid": "60123456789@s.whatsapp.net",
        "is_owner": True,
    }
    return asyncio.run(handler._handle_bijou_command(cmd, tenant_id="tenant-123"))


def test_owner_operator_commands_pass_tenant_id_without_typeerror():
    h = _handler()
    for command, args in [
        ("bookings", ""),
        ("crm", "Ali Ahmad"),
        ("send", "60123456789 > hi there"),
        ("confirm", "abc123"),
    ]:
        out = _run(h, command, args)
        # A string came back → the tenant_id-requiring helper was called
        # successfully (it then hit its db/bridge guard). No TypeError.
        assert isinstance(out, str) and out, f"{command!r} returned {out!r}"
