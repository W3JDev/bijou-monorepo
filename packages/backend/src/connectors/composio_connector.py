"""Composio connector — wraps composio.tools.execute (credentials vaulted at Composio)."""
from __future__ import annotations
import os
from .base import Action, Connector, Health, ToolResult


class ComposioConnector(Connector):
    name = "composio"

    def __init__(self, client=None, api_key: str | None = None, health_state: Health = Health.OK,
                 tool_version: str | None = None):
        self._client = client
        self._api_key = api_key or os.getenv("COMPOSIO_API_KEY")
        self._health_state = health_state
        # Composio requires a toolkit version for manual execution. If a version is
        # pinned (via arg or COMPOSIO_TOOL_VERSION), pass it; otherwise skip the
        # version check so calls use the current version. Verified 2026-07-22:
        # tools.execute rejects version="latest" but accepts dangerously_skip_version_check.
        self._tool_version = tool_version or os.getenv("COMPOSIO_TOOL_VERSION")

    def _get_client(self):
        if self._client is None:
            from composio import Composio  # lazy import; only needed for live calls
            self._client = Composio(api_key=self._api_key)
        return self._client

    def supports(self, action: Action) -> bool:
        return action.composio_slug is not None

    async def health(self) -> Health:
        return self._health_state

    async def execute(self, tenant_id: str, action: Action, args: dict) -> ToolResult:
        try:
            client = self._get_client()
            version_kwargs = ({"version": self._tool_version} if self._tool_version
                              else {"dangerously_skip_version_check": True})
            raw = client.tools.execute(action.composio_slug, user_id=tenant_id,
                                       arguments=args, **version_kwargs)
            if isinstance(raw, dict):
                successful, data, error = raw.get("successful"), raw.get("data"), raw.get("error")
            else:
                successful = getattr(raw, "successful", False)
                data = getattr(raw, "data", None)
                error = getattr(raw, "error", None)
            return ToolResult(success=bool(successful), data=data, error=error, backend="composio")
        except Exception as e:  # never raise into the agent loop
            return ToolResult(success=False, error=str(e), backend="composio")

    # --- per-tenant OAuth connection lifecycle -------------------------------
    def initiate_connection(self, tenant_id: str, auth_config_id: str,
                            callback_url: str | None = None) -> dict:
        """Start a per-tenant OAuth connection for one toolkit.

        Returns {connection_id, redirect_url, status} — redirect the customer to
        redirect_url and persist connection_id against the tenant. On error returns
        {error: ...} (never raises).
        """
        try:
            client = self._get_client()
            req = client.connected_accounts.initiate(
                tenant_id, auth_config_id, callback_url=callback_url)
            return {"connection_id": req.id, "redirect_url": req.redirect_url, "status": req.status}
        except Exception as e:
            return {"error": str(e)}

    def connection_status(self, connection_id: str) -> str:
        """Return the connected-account status (e.g. ACTIVE/INITIATED/FAILED),
        'UNKNOWN' if the field is absent, or 'ERROR' on failure. Never raises."""
        try:
            client = self._get_client()
            resp = client.connected_accounts.get(connection_id)
            status = resp.get("status") if isinstance(resp, dict) else getattr(resp, "status", None)
            return status or "UNKNOWN"
        except Exception:
            return "ERROR"
