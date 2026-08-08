"""Canonical action namespace: maps agent-facing action names to backends + policy."""
from __future__ import annotations
from .base import Action, Policy

# Composio slugs verified 2026-07-22 against the live catalog (composio 0.18.0)
# via tools.get_raw_composio_tools(toolkits=[...]). See docs/COMPOSIO_CONNECTOR_LAYER_DESIGN.md §17.
_SHEETS_APPEND_SLUG = "GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND"
_CALENDAR_CREATE_SLUG = "GOOGLECALENDAR_CREATE_EVENT"


def build_registry(orchestrator=None) -> dict[str, Action]:
    def _calendar_native(tenant_id, args):
        if orchestrator is None:
            raise RuntimeError("calendar native tool not wired")
        return orchestrator.execute_calendar_command(args, tenant_id=tenant_id)

    def _email_native(tenant_id, args):
        if orchestrator is None:
            raise RuntimeError("gmail native tool not wired")
        return orchestrator.execute_gmail_command(args)

    return {
        "email.send": Action(
            description="Send an email on the tenant's behalf",
            input_schema={"type": "object", "properties": {
                "to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
                "required": ["to", "subject", "body"]},
            native=_email_native, composio_slug=None, policy=Policy.NATIVE_ONLY),
        "calendar.book_slot": Action(
            description="Book a calendar appointment for the customer",
            input_schema={"type": "object", "properties": {
                "title": {"type": "string"}, "start_time": {"type": "string"}},
                "required": ["title", "start_time"]},
            native=_calendar_native, composio_slug=_CALENDAR_CREATE_SLUG, policy=Policy.NATIVE_FIRST),
        "sheets.append_row": Action(
            description="Append a row of values to the tenant's Google Sheet",
            input_schema={"type": "object", "properties": {
                "spreadsheet_id": {"type": "string"},
                "values": {"type": "array", "items": {"type": "string"}}},
                "required": ["spreadsheet_id", "values"]},
            native=None, composio_slug=_SHEETS_APPEND_SLUG, policy=Policy.COMPOSIO_ONLY,
            degrade_message="Aiyo boss, cannot update the sheet right now — I noted it down first, will settle later ya."),
    }
