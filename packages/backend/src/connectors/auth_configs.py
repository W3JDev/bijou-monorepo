"""Toolkit -> Composio auth-config-id resolution (from env / Fly secrets).

Auth-config IDs (`ac_...`) are created once per toolkit in the Composio dashboard
and shared across all tenants; each tenant then gets their own connected account.
Values come from env vars so they are never committed. Names mirror the
COMPOSIO_AUTH_ID_* keys documented in .env.composio.txt.
"""
from __future__ import annotations
import os

# canonical toolkit slug -> env var holding its auth_config_id
_ENV_BY_TOOLKIT = {
    "googlesheets": "COMPOSIO_AUTH_ID_GOOGLE_SHEETS",
    "googlecalendar": "COMPOSIO_AUTH_ID_GOOGLE_CALENDAR",
    "googledrive": "COMPOSIO_AUTH_ID_GOOGLE_DRIVE",
    "googledocs": "COMPOSIO_AUTH_ID_GOOGLE_DOCS",
    "googletasks": "COMPOSIO_AUTH_ID_GOOGLE_TASKS",
    "linkedin": "COMPOSIO_AUTH_ID_LINKEDIN",
    "instagram": "COMPOSIO_AUTH_ID_INSTAGRAM",
}


def auth_config_id(toolkit: str) -> str | None:
    """Return the configured auth_config_id for a toolkit, or None if unset."""
    env_key = _ENV_BY_TOOLKIT.get(toolkit.lower())
    return os.getenv(env_key) if env_key else None


def supported_toolkits() -> list[str]:
    """Toolkits that currently have an auth_config_id configured in the environment."""
    return [tk for tk in _ENV_BY_TOOLKIT if auth_config_id(tk)]
