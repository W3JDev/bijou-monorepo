"""Native connector — wraps in-repo tools that own their own credentials."""
from __future__ import annotations
import inspect
from .base import Action, Connector, Health, ToolResult


class NativeConnector(Connector):
    name = "native"

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator

    def supports(self, action: Action) -> bool:
        return action.native is not None

    async def health(self) -> Health:
        return Health.OK

    async def execute(self, tenant_id: str, action: Action, args: dict) -> ToolResult:
        try:
            out = action.native(tenant_id, args)
            if inspect.isawaitable(out):
                out = await out
            if isinstance(out, ToolResult):
                out.backend = out.backend or "native"
                return out
            if isinstance(out, dict):
                return ToolResult(
                    success=bool(out.get("success")),
                    data=out,
                    error=out.get("error"),
                    backend="native",
                )
            return ToolResult(success=True, data=out, backend="native")
        except Exception as e:  # never raise into the agent loop
            return ToolResult(success=False, error=str(e), backend="native")
