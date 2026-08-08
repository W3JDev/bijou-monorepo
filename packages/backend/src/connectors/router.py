"""Backend router: per-action policy, circuit breaker, graceful degradation."""
from __future__ import annotations
from typing import Callable
from .base import Action, Connector, Health, Policy, ToolResult
from .circuit_breaker import CircuitBreaker

_ORDER = {
    Policy.NATIVE_ONLY: ["native"],
    Policy.NATIVE_FIRST: ["native", "composio"],
    Policy.COMPOSIO_FIRST: ["composio", "native"],
    Policy.COMPOSIO_ONLY: ["composio"],
}

_DEFAULT_DEGRADE = "Aiyo boss, cannot do that one right now — I noted it down, will follow up ya."


class ConnectorRouter:
    def __init__(self, connectors: dict[str, Connector],
                 breaker_factory: Callable[[], CircuitBreaker] = CircuitBreaker,
                 default_degrade: str = _DEFAULT_DEGRADE):
        self.connectors = connectors
        self.breakers = {name: breaker_factory() for name in connectors}
        self.default_degrade = default_degrade

    async def execute(self, tenant_id: str, action_name: str, args: dict,
                      registry: dict[str, Action]) -> ToolResult:
        action = registry.get(action_name)
        if action is None:
            return ToolResult(success=False, error=f"unknown action: {action_name}",
                              user_message=self.default_degrade)
        last_error = None
        for name in _ORDER[action.policy]:
            conn = self.connectors.get(name)
            if conn is None or not conn.supports(action):
                continue
            breaker = self.breakers[name]
            if breaker.is_open():
                continue
            if await conn.health() is Health.DOWN:
                breaker.record_failure()
                continue
            result = await conn.execute(tenant_id, action, args)
            if result.success:
                breaker.record_success()
                return result
            breaker.record_failure()
            last_error = result.error
        return ToolResult(success=False, error=last_error,
                          user_message=action.degrade_message or self.default_degrade)
