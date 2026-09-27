"""
Bijou LLM Gateway v2 — data-driven, alias-based, with cross-provider fallback.

Author: W3J Bijou Enterprise
Architecture: docs/AI_GATEWAY.md
Public surface:
    await llm.complete("ai://fast", messages, **opts) -> CompletionResult

What this module guarantees:

1. NO callsite names a provider directly. They all use `ai://<alias>`.
2. Each alias has a YAML-defined policy (primary, fallbacks, budget, privacy).
3. Cross-provider fallback: 429/500/502/503/504 from primary -> next fallback.
4. Two daily USD budgets, both enforced: a platform-wide per-alias cap and a
   per-tenant cap within it. Exceeding either returns 429 BudgetExceeded.
5. Privacy level ("strict" vs "standard") — strict aliases never fall back to
   multi-tenant aggregators (OpenRouter).
6. Structured logging — provider, model, alias, latency, token usage, cost,
   fallback reason. Persisted to public.llm_usage.
7. Backwards compatible — the existing RoundRobinRotator (in llm_gateway.py) is
   still used for per-provider KEY-level rotation. v2 adds the alias/fallback
   layer on top of it.

This is intentionally NOT LiteLLM. The user asked for a gateway pattern, not
a third-party proxy. The infra is a single FastAPI process; no Redis, no
separate gateway server. All state is in-process + Supabase for usage logs.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx  # already in requirements.txt
import yaml  # already installed in .venv

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Config loading — single source of truth is llm_gateway.yaml next to this file.
# -----------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "llm_gateway.yaml"

# Provider-side HTTP failure codes, used by the provider ADAPTERS below to
# classify an error response. The cross-provider fallback DECISION lives in
# complete() and is broader than this set: it falls through on ANY provider-side
# failure (these codes, plus no-key / transport errors) and stops ONLY on a
# client-side 400. See the except-block in complete() for the authoritative rule.
# (Kept as a named set because both openai_compatible and gemini adapters test
# membership when building their ProviderError messages.)
FALLBACK_STATUS_CODES = {401, 403, 404, 429, 500, 502, 503, 504}

# Share of an alias's platform-wide cap a single tenant may spend when the alias
# declares no explicit per_tenant_daily_budget_usd. Absent means "derive", not
# "unlimited" — a newly added alias must be noisy-neighbour-safe before anyone
# remembers to tune it. Override in llm_gateway.yaml under
# budget_defaults.per_tenant_fraction.
DEFAULT_PER_TENANT_BUDGET_FRACTION = 0.2

# Providers that are allowed when privacy=strict. They are direct, paid,
# first-party APIs we control. OpenRouter / free pools are NOT in this list.
STRICT_PRIVACY_PROVIDERS = {"gemini", "openai_compatible"}


@dataclass
class CompletionResult:
    """Result of an llm.complete() call.

    Attributes:
        text: The model's text reply (or empty if a function_call was returned
            — call .function_calls instead).
        provider: Provider that ultimately answered ("gemini", "openrouter",
            "openai_compatible").
        model: Model name as reported by the provider.
        alias: The ai://... alias the caller used.
        fallback_reason: None if primary answered, else the class of failure
            that triggered the fallback ("429", "502", "timeout", etc).
        prompt_tokens / completion_tokens: Token usage if reported.
        cost_usd: Estimated cost in USD for this request.
        latency_ms: Wall-clock time spent in llm.complete().
        function_calls: List of {name, args} tool calls requested by the model
            (only for providers that support tool calling). Empty otherwise.
        raw: Full provider response (for debugging — not for production logic).
    """

    text: str
    provider: str
    model: str
    alias: str
    fallback_reason: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    function_calls: List[Dict[str, Any]] = field(default_factory=list)
    raw: Any = None


class BudgetExceeded(Exception):
    """Raised when a daily USD budget is exceeded.

    The API layer turns this into HTTP 429 with a Retry-After header.

    Two different caps raise this, and they are very different pages for
    whoever is on call:

        scope="tenant" — one customer burned through its own allowance. Every
            other tenant is still being served. Talk to that customer.
        scope="alias"  — the platform-wide cap for the alias is gone, so every
            tenant is degraded. Raise the cap or find what is spending.
    """

    def __init__(
        self,
        alias: str,
        spent: float,
        cap: float,
        scope: str = "alias",
        tenant_id: Optional[str] = None,
    ):
        self.alias = alias
        self.spent = spent
        self.cap = cap
        self.scope = scope
        self.tenant_id = tenant_id
        if scope == "tenant":
            msg = (
                f"Tenant {tenant_id!r} daily budget for alias {alias!r} exceeded: "
                f"spent ${spent:.4f} of ${cap:.4f} — other tenants unaffected"
            )
        else:
            msg = (
                f"Platform-wide daily budget for alias {alias!r} exceeded: "
                f"spent ${spent:.4f} of ${cap:.4f} — ALL tenants affected"
            )
        super().__init__(msg)


class NoProviderAvailable(Exception):
    """Raised when no provider in the chain has a usable key (or the alias
    is unknown). This is a config error, not a transient failure.
    """


# -----------------------------------------------------------------------------
# Usage tracker — in-memory daily spend counter, optionally persisted to
# public.llm_usage. Thread-safe.
# -----------------------------------------------------------------------------


class _UsageTracker:
    """Daily USD spend counters — per alias, and per (alias, tenant).

    Backed by an in-process dict (fast). On .flush_to_db() it bulk-inserts the
    day's usage into public.llm_usage so the dashboard can chart it. This is
    called by a cron / on shutdown / after every N requests — pick one.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # alias -> (date_iso, spent_usd, calls)
        self._day: Dict[str, Tuple[str, float, int]] = {}
        # alias -> {tenant_id: spent_usd} for the day named by _tenant_stamp
        self._tenant_day: Dict[str, Dict[str, float]] = {}
        self._tenant_stamp: str = self._today()
        # buffered rows for the next flush_to_db
        self._buffer: List[Dict[str, Any]] = []

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _roll_tenant_day(self, today: str) -> None:
        """Drop yesterday's tenant buckets. Caller must hold the lock.

        Unlike the per-alias dict (bounded by the handful of aliases) this one
        grows with the tenant count, so it is cleared wholesale at the UTC day
        boundary rather than left to accumulate a row per tenant per day.
        """
        if self._tenant_stamp != today:
            self._tenant_day.clear()
            self._tenant_stamp = today

    def record(
        self,
        alias: str,
        cost_usd: float,
        provider: str,
        model: str,
        latency_ms: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        fallback_reason: Optional[str] = None,
        error_class: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> None:
        with self._lock:
            today = self._today()
            spent, calls = self._day.get(alias, (today, 0.0, 0))[1:]
            if self._day.get(alias, (today, 0.0, 0))[0] != today:
                # New day — reset.
                spent, calls = 0.0, 0
            spent += float(cost_usd or 0.0)
            calls += 1
            self._day[alias] = (today, spent, calls)

            if tenant_id:
                self._roll_tenant_day(today)
                bucket = self._tenant_day.setdefault(alias, {})
                bucket[tenant_id] = bucket.get(tenant_id, 0.0) + float(cost_usd or 0.0)

            self._buffer.append(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "alias": alias,
                    "provider": provider,
                    "model": model,
                    "cost_usd": float(cost_usd or 0.0),
                    "latency_ms": int(latency_ms or 0),
                    "prompt_tokens": int(prompt_tokens or 0),
                    "completion_tokens": int(completion_tokens or 0),
                    "fallback_reason": fallback_reason,
                    "error_class": error_class,
                    "tenant_id": tenant_id,
                }
            )

    def spent_today(self, alias: str) -> float:
        with self._lock:
            entry = self._day.get(alias)
            if not entry or entry[0] != self._today():
                return 0.0
            return entry[1]

    def spent_today_tenant(self, alias: str, tenant_id: Optional[str]) -> float:
        if not tenant_id:
            return 0.0
        with self._lock:
            self._roll_tenant_day(self._today())
            return self._tenant_day.get(alias, {}).get(tenant_id, 0.0)

    def drain_buffer(self) -> List[Dict[str, Any]]:
        """Atomically returns + clears the pending usage rows."""
        with self._lock:
            rows, self._buffer = self._buffer, []
            return list(rows)


# -----------------------------------------------------------------------------
# Provider adapters — turn alias entries into actual HTTP calls.
#
# Each adapter takes (model: str, messages: list, opts: dict) and returns
# (text: str, raw: Any, prompt_tokens: int, completion_tokens: int, model_name: str).
# If the provider is unreachable / errors, it raises a ProviderError with a
# `status_code` so the gateway knows whether to fall back.
# -----------------------------------------------------------------------------


class ProviderError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _read_env_keys(env_keys_str: str) -> List[str]:
    """Read comma OR pipe-separated env var names. Returns the first non-empty."""
    keys: List[str] = []
    for raw in env_keys_str.split("|"):
        raw = raw.strip()
        if not raw:
            continue
        # GEMINI_API_KEYS is comma-separated; support that here too.
        if "," in raw:
            for sub in raw.split(","):
                sub = sub.strip()
                if sub:
                    keys.append(sub)
        else:
            keys.append(raw)
    out: List[str] = []
    for name in keys:
        val = os.getenv(name, "").strip()
        if val:
            out.append(val)
    return out


def _next_gemini_key() -> Optional[str]:
    """Reuse the existing key rotator if it's been initialised, else read env."""
    try:
        # Imported lazily to avoid circular imports at module load.
        from src.core.llm_gateway import RoundRobinRotator  # type: ignore

        rotator = getattr(RoundRobinRotator, "_shared", None)
        if rotator is None:
            rotator = RoundRobinRotator()
            setattr(RoundRobinRotator, "_shared", rotator)
        return rotator.get_next_key()
    except Exception:
        # Fallback: plain env read.
        return (
            os.getenv("GEMINI_API_KEYS", "").split(",")[0].strip()
            or os.getenv("GEMINI_API_KEY", "").strip()
            or os.getenv("GOOGLE_API_KEY", "").strip()
            or None
        )


# ---- Gemini ----------------------------------------------------------------


def _call_gemini(
    model: str,
    messages: List[Dict[str, str]],
    opts: Dict[str, Any],
) -> Tuple[str, Any, int, int, str]:
    """Synchronous Gemini REST call. Raises ProviderError on failure.

    We use the REST API (not the google-genai SDK) to keep the gateway
    dependency-light — httpx is the only HTTP client.
    """
    api_key = _next_gemini_key()
    if not api_key:
        raise ProviderError("No Gemini API key configured", status_code=None)

    # Convert OpenAI-style messages -> Gemini contents. Also supports the
    # OpenAI vision content list shape:
    #   {"role": "user", "content": [
    #       {"type": "text", "text": "..."},
    #       {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
    #   ]}
    system_parts: List[str] = []
    contents: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            # system content can be a string OR a list of text parts
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        system_parts.append(part.get("text", ""))
            else:
                system_parts.append(content or "")
            continue
        # Build the parts list for this message.
        parts: List[Dict[str, Any]] = []
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                ptype = part.get("type")
                if ptype == "text":
                    parts.append({"text": part.get("text", "")})
                elif ptype == "image_url":
                    url = (part.get("image_url") or {}).get("url", "")
                    # data:image/jpeg;base64,XXXX -> inline_data
                    if url.startswith("data:") and "," in url:
                        try:
                            import base64 as _b64
                            header, b64 = url.split(",", 1)
                            mime = "image/jpeg"
                            if ";" in header and header.startswith("data:"):
                                mime = header[5:].split(";", 1)[0] or mime
                            raw = _b64.b64decode(b64)
                            # Gemini's REST API expects base64 STRING (not raw bytes)
                            # for inline_data.data — JSON would otherwise choke.
                            parts.append(
                                {
                                    "inline_data": {
                                        "mime_type": mime,
                                        "data": _b64.b64encode(raw).decode("ascii"),
                                    }
                                }
                            )
                        except Exception as _e:
                            logger.warning("could not decode image_url: %s", _e)
        else:
            parts.append({"text": content or ""})
        if not parts:
            parts.append({"text": ""})
        if role == "assistant":
            contents.append({"role": "model", "parts": parts})
        else:
            contents.append({"role": "user", "parts": parts})
    if not contents:
        contents.append({"role": "user", "parts": [{"text": ""}]})

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": float(opts.get("temperature", 0.7)),
            "maxOutputTokens": int(opts.get("max_output_tokens", 1024)),
        },
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}

    # Tool / function calling. The gateway expects tools in OpenAI format:
    # [{"type": "function", "function": {"name": ..., "description": ...,
    # "parameters": ...}}, ...]. We translate to Gemini's
    # tools[0].function_declarations[...] shape.
    tools = opts.get("tools")
    if tools:
        decls = []
        for t in tools:
            if isinstance(t, dict) and t.get("type") == "function":
                fn = t.get("function", {}) or {}
                decls.append(
                    {
                        "name": fn.get("name", ""),
                        "description": fn.get("description", ""),
                        "parameters": fn.get("parameters", {"type": "object"}),
                    }
                )
            elif isinstance(t, dict) and "function_declarations" in t:
                # Already Gemini-shaped — pass through.
                payload.setdefault("tools", []).append(t)
                continue
        if decls:
            payload.setdefault("tools", []).append({"function_declarations": decls})

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(url, json=payload)
    except httpx.HTTPError as e:
        raise ProviderError(f"Gemini transport error: {e}", status_code=None) from e

    if r.status_code in FALLBACK_STATUS_CODES:
        # Mark the key rate-limited in the rotator so the next call skips it.
        try:
            from src.core.llm_gateway import RoundRobinRotator  # type: ignore

            getattr(RoundRobinRotator, "_shared", None)
        except Exception:
            pass
        raise ProviderError(
            f"Gemini {r.status_code}: {r.text[:200]}", status_code=r.status_code
        )

    if r.status_code >= 400:
        # Permanent (config / auth / not-found) — do NOT fall back.
        raise ProviderError(
            f"Gemini {r.status_code}: {r.text[:200]}", status_code=r.status_code
        )

    data = r.json()
    text = ""
    function_calls: List[Dict[str, Any]] = []
    try:
        parts = data["candidates"][0]["content"]["parts"]
        for part in parts:
            if "text" in part and part["text"]:
                text += part["text"]
            if "functionCall" in part and part["functionCall"]:
                fc = part["functionCall"]
                function_calls.append(
                    {
                        "name": fc.get("name", ""),
                        "args": fc.get("args", {}) or {},
                    }
                )
    except (KeyError, IndexError, TypeError):
        pass
    usage = data.get("usageMetadata", {}) or {}
    pt = int(usage.get("promptTokenCount", 0) or 0)
    ct = int(usage.get("candidatesTokenCount", 0) or 0)
    return (text or "").strip(), data, pt, ct, model


# ---- OpenAI-compatible (works for OpenAI + OpenRouter + any /v1 endpoint) -


def _call_openai_compatible(
    base_url: str,
    api_key: Optional[str],
    model: str,
    messages: List[Dict[str, str]],
    opts: Dict[str, Any],
) -> Tuple[str, Any, int, int, str]:
    """Generic OpenAI-compatible chat/completions call."""
    if not api_key:
        raise ProviderError(
            f"No API key for {base_url}", status_code=None
        )
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(opts.get("temperature", 0.7)),
        "max_tokens": int(opts.get("max_output_tokens", 1024)),
    }
    # Forward OpenAI-format tools. Without this, every non-Gemini provider was
    # silently tool-less, so ai://reasoning could not call a single tool once
    # Gemini died. Gemini-shaped entries ({"function_declarations": ...}) are
    # dropped — no OpenAI-compatible endpoint accepts them.
    tools = [
        t for t in (opts.get("tools") or [])
        if isinstance(t, dict) and t.get("type") == "function"
    ]
    if tools:
        payload["tools"] = tools
    # Per-entry YAML passthrough (MiniMax-M3 `thinking`). Entry-scoped, so a
    # fallback provider that would reject the field never receives it.
    if opts.get("thinking"):
        payload["thinking"] = opts["thinking"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as e:
        raise ProviderError(
            f"OpenAI-compat transport error ({base_url}): {e}", status_code=None
        ) from e

    if r.status_code in FALLBACK_STATUS_CODES:
        raise ProviderError(
            f"OpenAI-compat {r.status_code} ({base_url}): {r.text[:200]}",
            status_code=r.status_code,
        )
    if r.status_code >= 400:
        raise ProviderError(
            f"OpenAI-compat {r.status_code} ({base_url}): {r.text[:200]}",
            status_code=r.status_code,
        )
    data = r.json()
    try:
        text = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        text = ""
    # MiniMax M2.x reasoning models inline <think>...</think> in content; never
    # let that reach a customer (same strip as function_caller.call_with_openai_tools).
    text = re.sub(r"<think>.*?</think>\s*", "", text or "", flags=re.DOTALL)
    usage = data.get("usage", {}) or {}
    pt = int(usage.get("prompt_tokens", 0) or 0)
    ct = int(usage.get("completion_tokens", 0) or 0)
    return (text or "").strip(), data, pt, ct, model


# -----------------------------------------------------------------------------
# Gateway — the main public surface.
# -----------------------------------------------------------------------------


class LLMGateway:
    """Data-driven, alias-based, fallback-aware LLM gateway.

    Use:
        from src.core.llm_gateway_v2 import llm  # module-level singleton

        result = await llm.complete(
            "ai://fast",
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result.text)
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._config_path = config_path or _CONFIG_PATH
        self._lock = threading.Lock()
        self._config: Dict[str, Any] = {}
        self._usage = _UsageTracker()
        # Test seam — tests inject custom provider dispatch.
        self._dispatch_override: Optional[Dict[str, Any]] = None
        self.reload()

    # ---- config ----------------------------------------------------------

    def reload(self) -> None:
        """Re-read the YAML. Idempotent. Used by tests + on config change."""
        with self._lock:
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
            except FileNotFoundError:
                logger.warning(
                    "llm_gateway.yaml not found at %s — gateway will refuse every alias",
                    self._config_path,
                )
                self._config = {}
            except Exception as e:
                logger.error("Failed to load llm_gateway.yaml: %s", e)
                self._config = {}

    def _alias_cfg(self, alias: str) -> Dict[str, Any]:
        aliases = self._config.get("aliases") or {}
        cfg = aliases.get(alias)
        if not cfg:
            raise NoProviderAvailable(
                f"Unknown alias {alias!r}. Known: {sorted(aliases)}"
            )
        return cfg

    def _provider_cfg(self, name: str) -> Dict[str, Any]:
        providers = self._config.get("providers") or {}
        cfg = providers.get(name)
        if not cfg:
            raise NoProviderAvailable(
                f"Provider {name!r} not declared in llm_gateway.yaml"
            )
        return cfg

    def _cost_per_1k(self, model: str) -> Tuple[float, float]:
        costs = self._config.get("cost_per_1k") or {}
        for key, vals in costs.items():
            if key.endswith("/" + model) or key == model:
                return (
                    float(vals.get("input_usd", 0.0)),
                    float(vals.get("output_usd", 0.0)),
                )
        return (0.0, 0.0)

    def _resolve_per_tenant_budget(self, cfg: Dict[str, Any]) -> float:
        """Per-tenant daily cap for an alias config, in USD. 0.0 means unlimited.

        An explicit `per_tenant_daily_budget_usd: 0` is the documented opt-out
        and is honoured; only an *absent* key derives a cap from the
        platform-wide one.
        """
        declared = cfg.get("per_tenant_daily_budget_usd")
        if declared is not None:
            return float(declared or 0.0)

        platform = float(cfg.get("daily_budget_usd", 0.0) or 0.0)
        if platform <= 0:
            # Nothing sensible is a fraction of "unlimited" — an alias with no
            # platform cap has to name its per-tenant cap explicitly.
            return 0.0
        defaults = self._config.get("budget_defaults") or {}
        fraction = float(
            defaults.get("per_tenant_fraction", DEFAULT_PER_TENANT_BUDGET_FRACTION)
            or 0.0
        )
        if fraction <= 0:
            return 0.0
        return platform * fraction

    # ---- public ----------------------------------------------------------

    def list_aliases(self) -> List[Dict[str, Any]]:
        """Return a description of every configured alias. Used by /api/llm/aliases."""
        out: List[Dict[str, Any]] = []
        for name, cfg in (self._config.get("aliases") or {}).items():
            out.append(
                {
                    "alias": name,
                    "description": cfg.get("description", ""),
                    "primary": cfg.get("primary"),
                    "fallbacks": cfg.get("fallbacks", []),
                    "privacy": cfg.get("privacy", "standard"),
                    "daily_budget_usd": cfg.get("daily_budget_usd", 0.0),
                    "per_tenant_daily_budget_usd": self._resolve_per_tenant_budget(cfg),
                    "spent_today_usd": self._usage.spent_today(name),
                }
            )
        return out

    async def complete(
        self,
        alias: str,
        messages: List[Dict[str, str]],
        **opts: Any,
    ) -> CompletionResult:
        """Run the alias chain and return a CompletionResult.

        Args:
            alias: One of the configured ai://... aliases.
            messages: OpenAI-style list of {"role", "content"} dicts. The
                gateway translates to Gemini's format automatically.
            opts: Per-request overrides — max_output_tokens, temperature, tools,
                tenant_id (for usage tracking).

        Returns:
            CompletionResult on success.

        Raises:
            NoProviderAvailable: unknown alias or no provider has a key.
            BudgetExceeded: the calling tenant's daily cap (scope="tenant") or
                the platform-wide cap for the alias (scope="alias") is
                exhausted.
            ProviderError: every provider in the chain errored with a
                non-fallback status (rare — usually a config bug).
        """
        if not messages:
            raise ValueError("messages must be a non-empty list")

        cfg = self._alias_cfg(alias)
        privacy = cfg.get("privacy", "standard")
        budget = float(cfg.get("daily_budget_usd", 0.0) or 0.0)
        per_tenant_budget = self._resolve_per_tenant_budget(cfg)
        tenant_id = opts.get("tenant_id")

        # ---- budget checks (cheap) ----
        # Tenant cap first. A tenant that is over its own allowance has usually
        # also pushed the platform total up, and reporting that as a
        # platform-wide outage would hide the one customer actually causing it.
        # Calls with no tenant_id (cron, backfills, health probes) have no
        # tenant to charge and are only bounded by the platform cap below.
        if tenant_id and per_tenant_budget > 0:
            tenant_spent = self._usage.spent_today_tenant(alias, tenant_id)
            if tenant_spent >= per_tenant_budget:
                raise BudgetExceeded(
                    alias,
                    tenant_spent,
                    per_tenant_budget,
                    scope="tenant",
                    tenant_id=tenant_id,
                )

        spent = self._usage.spent_today(alias)
        if budget > 0 and spent >= budget:
            raise BudgetExceeded(alias, spent, budget)

        chain: List[Dict[str, Any]] = []
        primary = cfg.get("primary")
        if primary:
            chain.append(primary)
        for fb in cfg.get("fallbacks", []) or []:
            chain.append(fb)

        if not chain:
            raise NoProviderAvailable(f"Alias {alias!r} has no providers configured")

        last_err: Optional[Exception] = None
        last_fallback_reason: Optional[str] = None
        started = time.monotonic()
        # Langfuse: open one generation observation per complete() call, update as we
        # move through the provider chain. The observation records the alias, the
        # resolved provider+model, tokens, cost, and latency. PDPA-grade inputs
        # are masked inside trace_completion.
        from src.core.langfuse_tracing import trace_completion, flush as _lf_flush

        with trace_completion(
            alias=alias,
            model="chain",  # will be updated to the actual resolved model below
            provider="chain",
            messages=messages,
            tenant_id=tenant_id,
            session_id=opts.get("session_id"),
            user_id=opts.get("user_id"),
            metadata={
                "privacy": privacy,
                "daily_budget_usd": budget,
                "per_tenant_daily_budget_usd": per_tenant_budget,
                "chain_len": len(chain),
            },
            tags=[alias, privacy] if privacy else [alias],
        ) as _lf_obs:
            for idx, entry in enumerate(chain):
                provider_name = entry.get("provider")
                model = entry.get("model")
                entry_opts = dict(entry)
                entry_opts.update({k: v for k, v in opts.items() if k in ("temperature", "max_output_tokens", "tools")})

                # Privacy gate — strict aliases cannot use multi-tenant aggregators.
                if privacy == "strict" and provider_name not in STRICT_PRIVACY_PROVIDERS:
                    logger.info(
                        "🚫 alias=%s skipping provider=%s (privacy=strict)",
                        alias,
                        provider_name,
                    )
                    continue

                try:
                    text, raw, pt, ct, used_model, function_calls = self._dispatch(
                        provider_name, model, messages, entry_opts
                    )
                except ProviderError as e:
                    last_err = e
                    # Rotator semantics (2026-09-21): fall through to the NEXT
                    # provider on ANY provider error, full stop. We deliberately do
                    # NOT special-case status codes — providers disagree wildly:
                    # Google's OpenAI-compat endpoint returns 400 for a bad key,
                    # MiniMax returns 401, others 403; a missing key / transport
                    # error is status_code=None. Hard-stopping on any of these would
                    # abort the chain on a provider that a sibling could have
                    # served. If EVERY provider fails, the loop falls out below and
                    # raises last_err. A truly malformed request just costs a few
                    # extra attempts — cheap insurance vs. giving up while a working
                    # key still exists. THIS is "auto fall back to any working
                    # provider/env-var, instead of hitting the same dead API".
                    if e.status_code:
                        last_fallback_reason = f"http_{e.status_code}"
                    elif last_fallback_reason is None:
                        # No key / transport / unreachable: skip quietly and do NOT
                        # clobber a more informative earlier HTTP reason.
                        last_fallback_reason = "provider_unavailable"
                    logger.warning(
                        "⚠️ alias=%s provider=%s model=%s → %s (falling back)",
                        alias,
                        provider_name,
                        model,
                        f"http_{e.status_code}" if e.status_code else "unavailable/no-key",
                    )
                    continue

                # ---- success ----
                latency_ms = int((time.monotonic() - started) * 1000)
                cost = self._estimate_cost(model, pt, ct)
                self._usage.record(
                    alias=alias,
                    cost_usd=cost,
                    provider=provider_name,
                    model=used_model,
                    latency_ms=latency_ms,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    fallback_reason=last_fallback_reason if idx > 0 else None,
                    tenant_id=tenant_id,
                )
                # Langfuse: update the observation with the resolved provider/model,
                # the output, the token usage, and the cost.
                try:
                    _lf_obs.update(
                        model=used_model,
                        provider=provider_name,
                        output=text,
                        usage={"prompt_tokens": pt, "completion_tokens": ct},
                        cost_usd=cost,
                        metadata={
                            "fallback_reason": last_fallback_reason,
                            "latency_ms": latency_ms,
                        },
                    )
                except Exception as _lf_err:
                    logger.debug("Langfuse obs.update failed: %s", _lf_err)
                logger.info(
                    "✅ alias=%s provider=%s model=%s latency_ms=%d pt=%d ct=%d "
                    "cost_usd=%.5f fallback=%s",
                    alias,
                    provider_name,
                    used_model,
                    latency_ms,
                    pt,
                    ct,
                    cost,
                    last_fallback_reason or "primary",
                )
                return CompletionResult(
                    text=text,
                    provider=provider_name,
                    model=used_model,
                    alias=alias,
                    fallback_reason=last_fallback_reason if idx > 0 else None,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    function_calls=function_calls,
                    raw=raw,
                )

            # Every provider in the chain failed.
            latency_ms = int((time.monotonic() - started) * 1000)
            # Log the failure even though we didn't reach a result.
            self._usage.record(
                alias=alias,
                cost_usd=0.0,
                provider="(none)",
                model="(none)",
                latency_ms=latency_ms,
                fallback_reason=last_fallback_reason or "all_providers_failed",
                error_class=type(last_err).__name__ if last_err else "NoProviderAvailable",
                tenant_id=tenant_id,
            )
            err_msg = (
                f"all {len(chain)} providers failed"
                if last_err is None
                else f"{type(last_err).__name__}: {last_err}"
            )
            try:
                _lf_obs.fail(err_msg)
            except Exception:
                pass
            if last_err is not None:
                raise last_err
            raise NoProviderAvailable(
                f"Alias {alias!r}: no usable provider (all filtered or missing keys)"
            )

    # ---- internals -------------------------------------------------------

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        in_rate, out_rate = self._cost_per_1k(model)
        if in_rate == 0.0 and out_rate == 0.0:
            return 0.0
        return (prompt_tokens / 1000.0) * in_rate + (completion_tokens / 1000.0) * out_rate

    def _dispatch(
        self,
        provider_name: Optional[str],
        model: Optional[str],
        messages: List[Dict[str, str]],
        opts: Dict[str, Any],
    ) -> Tuple[str, Any, int, int, str, List[Dict[str, Any]]]:
        """Route a single call to the right adapter.

        Returns: (text, raw, prompt_tokens, completion_tokens, model_name, function_calls).
        function_calls is [] if the model returned plain text.

        Test override: if self._dispatch_override is set, it must be a dict
        keyed by provider name whose value is a callable matching the adapter
        signature. Used by tests to inject fakes.
        """
        if not provider_name or not model:
            raise ProviderError("provider and model are required", status_code=None)

        # Test seam.
        if self._dispatch_override and provider_name in self._dispatch_override:
            out = self._dispatch_override[provider_name](model, messages, opts)
            # Adapters in tests can return either 5-tuple or 6-tuple.
            if len(out) == 5:
                return out[0], out[1], out[2], out[3], out[4], []
            return out

        if provider_name == "gemini":
            text, raw, pt, ct, used_model = _call_gemini(model, messages, opts)
            # Re-extract function calls from the raw response — _call_gemini has
            # already collected them, but kept the legacy 5-tuple shape.
            function_calls = []
            try:
                for part in raw.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                    fc = part.get("functionCall") if isinstance(part, dict) else None
                    if fc:
                        function_calls.append(
                            {"name": fc.get("name", ""), "args": fc.get("args", {}) or {}}
                        )
            except (KeyError, IndexError, TypeError):
                pass
            return text, raw, pt, ct, used_model, function_calls

        # Data-driven: ANY provider whose YAML `type` is openai_compatible routes
        # through the OpenAI-compatible adapter. Adding MiniMax / Vercel AI Gateway
        # / Cloudflare Workers AI / OpenRouter / Google's OpenAI-compat endpoint /
        # any other free router is then a PURE-YAML change (base_url + env_keys) —
        # no edit here. base_url may embed ${ENV_VAR} (e.g. Cloudflare bakes the
        # account id into its path), expanded from the environment at call time.
        # (2026-09-21 — was a hardcoded name tuple, which silently blocked the
        # "add all the free router models" ask.)
        pcfg = (self._config.get("providers") or {}).get(provider_name) or {}
        if pcfg.get("type") == "openai_compatible":
            keys = _read_env_keys(pcfg.get("env_keys", ""))
            if not keys:
                raise ProviderError(
                    f"No API key set for provider {provider_name!r} "
                    f"(env_keys={pcfg.get('env_keys')!r})",
                    status_code=None,
                )
            base_url = os.path.expandvars(pcfg.get("base_url", ""))
            text, raw, pt, ct, used_model = _call_openai_compatible(
                base_url, keys[0], model, messages, opts
            )
            # OpenAI-compatible responses with tool_calls[].function.{name,arguments}.
            function_calls: List[Dict[str, Any]] = []
            try:
                msg = (raw.get("choices") or [{}])[0].get("message", {})
                for tc in msg.get("tool_calls") or []:
                    fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                    args = fn.get("arguments", "{}")
                    try:
                        import json as _json
                        parsed_args = _json.loads(args) if isinstance(args, str) else (args or {})
                    except Exception:
                        parsed_args = {}
                    function_calls.append(
                        {"name": fn.get("name", ""), "args": parsed_args}
                    )
            except (KeyError, IndexError, TypeError):
                pass
            return text, raw, pt, ct, used_model, function_calls

        raise ProviderError(f"Unknown provider {provider_name!r}", status_code=None)

    # ---- usage persistence (called by a cron / shutdown handler) --------

    def drain_usage(self) -> List[Dict[str, Any]]:
        """Pop buffered usage rows so the caller can INSERT them into Supabase.

        Idempotent — drains once per call. The gateway doesn't INSERT directly
        so callers can use their preferred Supabase client (sync vs async,
        service-role vs anon).
        """
        return self._usage.drain_buffer()

    def spent_today(self, alias: str) -> float:
        return self._usage.spent_today(alias)

    def spent_today_tenant(self, alias: str, tenant_id: Optional[str]) -> float:
        return self._usage.spent_today_tenant(alias, tenant_id)

    def per_tenant_budget(self, alias: str) -> float:
        """Resolved per-tenant daily cap for an alias, in USD. 0.0 = unlimited."""
        return self._resolve_per_tenant_budget(self._alias_cfg(alias))


# -----------------------------------------------------------------------------
# Module-level singleton — the public surface is `llm.complete(...)`.
# Tests can construct their own LLMGateway() and pass it around.
# -----------------------------------------------------------------------------

llm = LLMGateway()


class SyncTextModel:
    """Sync drop-in for the retired `genai.GenerativeModel(...)` objects.

    Legacy sync callers did `model.generate_content(prompt).text`; this keeps
    that shape but routes through the gateway alias, so no callsite names a
    provider. CompletionResult has `.text`. Async code should
    `await llm.complete(...)` instead.
    """

    def __init__(self, alias: str, **opts: Any) -> None:
        self.alias = alias
        self.opts = opts

    def generate_content(self, prompt: str) -> CompletionResult:
        coro = llm.complete(self.alias, [{"role": "user", "content": prompt}], **self.opts)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)  # plain sync / worker-thread caller
        # ponytail: sync caller INSIDE a running loop (e.g. owner commands in
        # process_message). Blocks the loop for the call, exactly as the old
        # sync genai SDK did; make the caller async to remove the block.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
