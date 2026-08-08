"""
Setup / Pre-Go-Live Sandbox API.

Exposes a DRY-RUN "Test Bijou" endpoint so a dashboard owner can chat with
their OWN tenant's AI before going live — without sending anything outbound
over the WhatsApp bridge and without persisting customer conversation records.

Tenant isolation is enforced by `verify_session` (imported from
`dashboard_api_simple`), which returns the authorized `tenant_id`. The handler
NEVER trusts a tenant_id from the request body.

Circular-import safety:
    - `verify_session` is imported at module top (dashboard_api_simple does NOT
      import this router, so there is no cycle).
    - `bijou_instance` (the live BijouAI singleton) is imported LAZILY inside the
      handler via `from src.core import bijou`, because bijou.py mounts this
      router at startup — importing it at module load would create a cycle.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

# Safe at module top: dashboard_api_simple imports none of the feature routers.
from src.core.dashboard_api_simple import verify_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/setup", tags=["setup"])


class TestMessageRequest(BaseModel):
    """Request body for the dry-run test chat."""

    message: str


class TestMessageResponse(BaseModel):
    """
    Stable response contract the dashboard frontend depends on.

    Always HTTP 200 — internal failures are surfaced via `ok=False` + `error`,
    never as a raised exception to the client.
    """

    reply: str
    ok: bool
    error: Optional[str] = None


# Minimal fallback config, mirroring the webhook path's fallback in
# bijou.py so the sandbox still works for a tenant whose client_config
# row is missing (e.g. mid-onboarding).
def _fallback_config(tenant_id: str) -> dict:
    return {
        "tenant_id": tenant_id,
        "business_name": "Business Assistant",
        "industry": "general",
        "persona_name": "Bijou",
        "tone": "friendly_professional",
        "language": "en",
        "timezone": "Asia/Kuala_Lumpur",
        "business_description": "A helpful AI assistant",
        "core_values": "helpful, professional, friendly",
        "response_style": "concise and clear",
    }


@router.post("/test-message", response_model=TestMessageResponse)
async def test_message(
    payload: TestMessageRequest,
    request: Request,
    tenant_id: str = Depends(verify_session),
) -> TestMessageResponse:
    """
    DRY-RUN: run the tenant's REAL generation engine against `message` and
    return the reply, without any outbound send or customer-data persistence.

    Dry-run guarantees:
      * We call `BijouAI._generate_response(...)` DIRECTLY. The WhatsApp bridge
        send and the `messages`/`conversations` inserts live in the webhook
        caller (`_process_message`), NOT in `_generate_response`, so none of
        those fire on this path.
      * `chat_jid` is prefixed `sandbox:` so any history lookups / conversation
        logs are isolated from real customer threads and clearly non-production.
      * `client_config["sandbox"] = True` makes `_generate_response` replace EVERY
        tool execution (escalation, calendar, gmail, payment, ...) with a harmless
        stub and skip ALL DB writes — so no consequential action can fire and a
        test writes nothing to the database. The guard is per-request (threaded
        through client_config), never a global toggle, so live traffic handled
        concurrently is completely unaffected.
    """
    try:
        # The live BijouAI singleton is stored on the shared FastAPI app.state
        # (bijou.py:805). app is one object across modules, so this works even
        # though bijou.py runs as __main__ and its module-global bijou_instance
        # lives in a different namespace than `src.core.bijou`. Module global is
        # a fallback for any launch path that didn't populate app.state.
        engine = getattr(getattr(request.app, "state", None), "bijou", None)
        if engine is None:
            from src.core import bijou  # lazy — avoids circular import at load
            engine = getattr(bijou, "bijou_instance", None)
        if engine is None:
            return TestMessageResponse(
                reply="", ok=False, error="AI engine not ready"
            )

        message = (payload.message or "").strip()
        if not message:
            return TestMessageResponse(
                reply="", ok=False, error="Message is empty"
            )

        # Load the tenant's REAL persona + knowledge config using the SAME
        # loader the webhook path uses: tenant_router.get_client_config().
        client_config = None
        try:
            tenant_router = getattr(engine, "tenant_router", None)
            if tenant_router is not None:
                client_config = await tenant_router.get_client_config(tenant_id)
        except Exception as cfg_err:  # noqa: BLE001 - never leak to client
            logger.warning(
                f"setup/test-message: config load failed for tenant "
                f"{tenant_id}: {cfg_err}"
            )
            client_config = None

        if client_config:
            # Persona/knowledge lookups downstream read tenant_id from config.
            client_config["tenant_id"] = tenant_id
        else:
            client_config = _fallback_config(tenant_id)

        # DRY-RUN flag: _generate_response honors client_config["sandbox"] to
        # (a) replace every tool execution with a harmless stub and (b) skip ALL
        # DB writes (conversation_logs / agent-memory / trajectory). This is the
        # airtight guarantee that no consequential action fires during a test.
        client_config["sandbox"] = True

        # Sandbox-prefixed JID isolates any history/log writes from real threads.
        sandbox_jid = f"sandbox:{tenant_id}"

        reply = await engine._generate_response(
            user_message=message,
            lang_context=None,
            chat_jid=sandbox_jid,
            client_config=client_config,
        )

        return TestMessageResponse(reply=reply or "", ok=True, error=None)

    except Exception as e:  # noqa: BLE001 - contract: never raise to client
        logger.error(f"setup/test-message error: {e}")
        return TestMessageResponse(reply="", ok=False, error=str(e))
