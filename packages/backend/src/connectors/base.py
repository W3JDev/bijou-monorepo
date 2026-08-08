"""Core types for the provider-agnostic connector layer."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class Health(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class Policy(str, Enum):
    NATIVE_ONLY = "native_only"
    NATIVE_FIRST = "native_first"
    COMPOSIO_FIRST = "composio_first"
    COMPOSIO_ONLY = "composio_only"


@dataclass
class ToolSpec:
    action: str
    description: str
    input_schema: dict


@dataclass
class ToolResult:
    success: bool
    data: Any | None = None
    error: str | None = None
    backend: str | None = None
    user_message: str | None = None


@dataclass
class Action:
    description: str
    input_schema: dict
    native: Optional[Callable[..., Any]] = None
    composio_slug: Optional[str] = None
    policy: Policy = Policy.NATIVE_ONLY
    degrade_message: Optional[str] = None


class Connector(ABC):
    name: str

    @abstractmethod
    async def execute(self, tenant_id: str, action: Action, args: dict) -> ToolResult: ...

    @abstractmethod
    async def health(self) -> Health: ...

    @abstractmethod
    def supports(self, action: Action) -> bool: ...
