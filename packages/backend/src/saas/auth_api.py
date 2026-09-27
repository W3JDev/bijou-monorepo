import logging
import os
import secrets as _secrets
import threading
import time
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Dict, Optional
from pydantic import BaseModel, EmailStr
from src.core.dashboard_api_simple import get_supabase
from src.saas.email_service import get_email_service
from src.saas.tenant_manager import TenantManager
from uuid import uuid4

# Specific exception types from the auth/Supabase stack. Catching the broad
# `Exception` below was masking the real error from `db.auth.sign_up` and
# turning every Supabase auth failure (signups disabled, network blip, weak
# password, etc.) into a generic 500 with no actionable detail. 2026-08-09.
try:
    from supabase_auth.errors import AuthApiError  # type: ignore
except ImportError:  # pragma: no cover — older supabase-py
    AuthApiError = Exception  # type: ignore
try:
    import httpx  # used for the welcome-WhatsApp block AND surfaced here
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Dedicated Supabase client for user-scoped auth operations.
#
# get_supabase() returns a PROCESS-WIDE singleton built with the service-role
# key, and every .table(...) call in the backend shares it. RLS was hardened so
# service_role is the only role that can read or write (ops/_fix_rls_v6.js), so
# that credential is load-bearing for the entire application.
#
# supabase-py's Client._listen_to_auth_events rewrites
# options.headers["Authorization"] and drops the cached PostgREST client on
# SIGNED_IN / TOKEN_REFRESHED / SIGNED_OUT. Running sign_in_with_password(),
# set_session() or refresh_session() on the shared client therefore replaced
# the service-role credential with one user's JWT for the whole worker process,
# and nothing put it back. Measured before this fix:
#
#     login   before: Bearer SERVICE-ROLE-KEY-AAA
#     login   after : Bearer eyJhbGciOiAiSFMyNTYiL...   <- the user's JWT
#
# Every later request that worker handled — other tenants' dashboards, the
# WhatsApp webhook, the schedulers — then authorized as that user.
#
# Keeping a SECOND singleton (rather than a fresh client per request) preserves
# the reason the first one exists: get_supabase()'s docstring records that
# create_client per call opened a new httpx pool and caused ConnectionTerminated
# errors under load. Auth sessions still churn on this client between users, but
# nothing here relies on its ambient session — every handler passes the caller's
# token explicitly — and crucially it is never used for data access.
# ---------------------------------------------------------------------------
_auth_supabase_client = None
_auth_client_lock = __import__("threading").Lock()


def get_auth_client():
    """Supabase client for user-scoped auth calls only. Never use for .table()."""
    global _auth_supabase_client
    with _auth_client_lock:
        if _auth_supabase_client is None:
            supabase_url = os.getenv("SUPABASE_URL") or os.getenv(
                "NEXT_PUBLIC_SUPABASE_URL", ""
            ).strip('"')
            supabase_key = (
                os.getenv("SUPABASE_SERVICE_KEY")
                or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip('"')
                or os.getenv("SUPABASE_KEY")
            )
            if not supabase_url or not supabase_key:
                raise HTTPException(
                    status_code=500, detail="Missing Supabase configuration"
                )

            import httpx as _httpx
            from supabase import create_client as _create_client
            from supabase import ClientOptions as _SBCO  # type: ignore

            # Match get_supabase(): force HTTP/1.1 (PostgREST HTTP/2 drops
            # certain tables).
            opts = _SBCO(httpx_client=_httpx.Client(http2=False, timeout=30.0))
            _auth_supabase_client = _create_client(supabase_url, supabase_key, options=opts)
        return _auth_supabase_client

# Canonical public origin. Everything user-facing (emails, WhatsApp links,
# magic links, password resets) must be built on this — NEVER on
# request.base_url.
#
# 2026-08-17 BUG: the welcome WhatsApp message and the password-reset email
# both used `os.getenv("APP_URL", "https://bijou-production.fly.dev")` as
# their fallback. Behind Fly's proxy, `bijou-production.fly.dev` is the
# internal container host — a different browser origin from app.mybijou.xyz.
# Result: the password-reset email and the welcome-WhatsApp message linked
# to the Fly machine URL, and the user's browser either showed a
# Fly-default-cert warning or, on the bare Fly host, the dashboard found
# no JWT in localStorage (origin-scoped) and bounced them to /login.
# Mirrors `_public_base_url()` in google_oauth.py:54 and every other
# canonical-URL site in this monorepo (onboarding_api.py:191, etc.).
CANONICAL_PUBLIC_URL = "https://app.mybijou.xyz"


def _public_base_url() -> str:
    """Public origin for user-facing redirects + email links. Never derived
    from the request. Caller should rstrip('/') if appending a path."""
    return (os.getenv("PUBLIC_URL") or os.getenv("APP_URL") or CANONICAL_PUBLIC_URL).rstrip("/")

# Request/Response Models
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    business_name: str
    phone: str
    plan: str = "free"
    vertical: Optional[str] = None  # 'property' | 'dental' | 'fnb' | 'w3j'

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    # This project has email confirmation ON (GoTrue mailer_autoconfirm=false),
    # so a *successful* signup legitimately has no session yet — the tokens
    # only exist after the user clicks the verification link. Tokens must
    # therefore be optional, otherwise "created, awaiting verification" is not
    # representable and the endpoint is forced to report success as an error.
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: dict
    tenant_id: str
    email_confirmation_required: bool = False
    # 2026-08-17 FIX: also expose `email` and `business_name` at the top
    # level so the static login.html (and any other consumer) can do
    # `data.email` / `data.business_name` without reaching into
    # `data.user.email` (which doesn't exist in the same shape for
    # `business_name` at all). Previously, `localStorage.setItem("email",
    # data.email)` stored the literal string "undefined" and the dashboard's
    # identity fell back to JWT-only or "—", which is what the user
    # experienced as "login is not working". Mirrors what `oauth_session()`
    # already returns for the Google sign-in path.
    email: Optional[str] = None
    business_name: Optional[str] = None
    # Where the client should go next. None => /dashboard. Set to an
    # /onboard/{token} URL when this tenant still has to connect WhatsApp, so
    # email/password login behaves like the Google path instead of dumping a
    # brand-new user on an empty dashboard.
    next_url: Optional[str] = None

class RefreshRequest(BaseModel):
    refresh_token: str

class MagicLinkRequest(BaseModel):
    email: str


@router.post("/api/auth/refresh")
async def refresh_access_token(request: RefreshRequest):
    """
    Exchange a valid refresh_token for a new access_token.
    Called automatically by the dashboard when the access_token expires (401).
    Keeps users logged in without forcing a manual re-login.
    """
    db = get_supabase()
    try:
        # Auth client, not the shared data client: refresh_session fires
        # TOKEN_REFRESHED, which would rewrite the data client's credential.
        result = get_auth_client().auth.refresh_session(request.refresh_token)
        if not result or not result.session:
            raise HTTPException(status_code=401, detail="Refresh token invalid or expired. Please log in again.")

        # Resolve tenant_id for the refreshed user
        tenant_id = None
        try:
            link = db.table("tenant_users") \
                .select("tenant_id") \
                .eq("user_id", str(result.user.id)) \
                .maybe_single() \
                .execute()
            ld = getattr(link, "data", None) if link else None
            tenant_id = ld.get("tenant_id") if isinstance(ld, dict) else None
        except Exception:
            pass

        logging.info(f"✅ Token refreshed for user {result.user.email}")
        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "tenant_id": tenant_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")


# ---------------------------------------------------------------------------
# Per-IP rate limit on /api/auth/signup. Before this, nothing throttled the
# endpoint at our own edge — only Supabase's own project-wide signup limit
# (signup.html's own comment cites "~4 per IP per hour"), which meant an
# attacker probing candidate emails (see the anti-enumeration fix above) or
# just spamming signups paid no cost until THAT tripped, at which point the
# user got Supabase's raw 429 rather than a controlled response.
#
# Same token-bucket algorithm as _webhook_take_token in src/core/bijou.py
# (kept as a separate, self-contained copy rather than a shared import: this
# module is imported from bijou.py inside _include_routers(), so importing
# bijou.py's helper back from here for one small function would add a real
# circular-import risk for very little gain).
# ---------------------------------------------------------------------------
_SIGNUP_RATE_LOCK = threading.Lock()
_SIGNUP_RATE_BUCKETS: Dict[str, list] = {}  # ip -> [tokens, last_refill_monotonic]
_SIGNUP_RATE_BUCKET_MAX_KEYS = 10000


def _reset_signup_rate_limit() -> None:
    """Empty every bucket. For tests: this state is process-global, so a
    flood in one test would otherwise 429 an unrelated later test."""
    with _SIGNUP_RATE_LOCK:
        _SIGNUP_RATE_BUCKETS.clear()


def _signup_client_ip(http_request: Optional[Request]) -> str:
    if http_request is None:
        return "unknown"
    forwarded = http_request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return http_request.client.host if http_request.client else "unknown"


def _check_signup_rate_limit(http_request: Optional[Request]) -> None:
    """Raise HTTPException(429) if this IP has exceeded its signup budget.

    Env-tunable, same convention as the webhook limiter: capacity <= 0
    disables it entirely.
    """
    try:
        capacity = float(os.getenv("SIGNUP_RATE_CAPACITY", "5"))
    except ValueError:
        capacity = 5.0
    if capacity <= 0:
        return
    try:
        refill_per_sec = float(os.getenv("SIGNUP_RATE_REFILL_PER_SEC", str(5.0 / 3600)))
    except ValueError:
        refill_per_sec = 5.0 / 3600

    key = _signup_client_ip(http_request)
    now = time.monotonic()
    with _SIGNUP_RATE_LOCK:
        bucket = _SIGNUP_RATE_BUCKETS.get(key)
        if bucket is None:
            if len(_SIGNUP_RATE_BUCKETS) >= _SIGNUP_RATE_BUCKET_MAX_KEYS:
                cutoff = now - 3600
                for k in [k for k, v in _SIGNUP_RATE_BUCKETS.items() if v[1] < cutoff]:
                    del _SIGNUP_RATE_BUCKETS[k]
                if len(_SIGNUP_RATE_BUCKETS) >= _SIGNUP_RATE_BUCKET_MAX_KEYS:
                    # Saturated: shed load rather than grow unbounded.
                    raise HTTPException(
                        status_code=429,
                        detail="Too many sign-up attempts. Please wait a minute and try again.",
                    )
            bucket = [capacity, now]
            _SIGNUP_RATE_BUCKETS[key] = bucket

        tokens, last = bucket
        tokens = min(capacity, tokens + (now - last) * refill_per_sec)
        bucket[1] = now

        if tokens < 1.0:
            bucket[0] = tokens
            logger.warning("🚦 signup rate limit hit for %s: shedding load", key)
            raise HTTPException(
                status_code=429,
                detail="Too many sign-up attempts. Please wait a minute and try again.",
            )
        bucket[0] = tokens - 1.0


@router.post("/api/auth/signup", response_model=AuthResponse)
async def signup(request: SignupRequest, http_request: Request = None):
    """
    Professional signup with email/password authentication.
    Creates Supabase auth user + tenant + tenant_user link.

    The supabase-py client is sync, so a hung Supabase request will block
    the event loop. We compensate with comprehensive exception mapping in
    the outer `except` below (AuthApiError.status, httpx errors, etc.)
    so a failure surfaces as a real 4xx/5xx with a JSON body instead of
    a silent Fly-edge 500 with no body.  2026-08-09.
    """
    _check_signup_rate_limit(http_request)
    db = get_supabase()

    user_id = None
    try:
        # 1. Create Supabase Auth user
        # 2026-08-09: AuthApiError is raised for "email already registered",
        # "signups not allowed", "rate limit exceeded", "weak password", and
        # most other Supabase auth failures. Letting it bubble to the broad
        # `except Exception` below (instead of the cascade at step 2+) means
        # we don't create an orphan tenant for a user that was never
        # actually provisioned, and the dashboard sees the real 4xx/5xx
        # instead of a misleading 500.
        try:
            # email_redirect_to: every OTHER user-facing auth email in this
            # file (reset_password below) builds its link on
            # _public_base_url() explicitly, precisely because this project
            # was bitten twice by a link defaulting to the wrong domain
            # (Fly's internal host, or a stale Supabase dashboard Site URL)
            # instead of app.mybijou.xyz. The confirmation email sign_up()
            # sends was the one link in this file still relying on that
            # dashboard-configured default — make it explicit too.
            auth_response = get_auth_client().auth.sign_up({
                "email": request.email,
                "password": request.password,
                "options": {"email_redirect_to": f"{_public_base_url()}/login"},
            })
        except AuthApiError as auth_err:
            # Let the outer `except` mapper translate it to a 4xx/5xx with
            # a useful message. We don't re-raise as HTTPException here
            # because the outer handler has richer context (it knows the
            # email, request shape, and full Supabase error payload).
            logger.warning(
                "Supabase auth.sign_up rejected signup for %s (status=%s, code=%s): %s",
                request.email,
                getattr(auth_err, "status", None),
                getattr(auth_err, "code", None),
                auth_err,
            )
            raise

        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Failed to create user account")

        user_id = auth_response.user.id

        # 1a. Detect the "email already exists" case EARLY.
        # The supabase-py library (v2.x) has a known bug: when sign_up is
        # called with an email that already exists in auth.users, it
        # returns a User object with a *phantom* UUID (a freshly-generated
        # uuid4 that is NOT in auth.users) and session=None — instead of
        # either returning the existing user or raising AuthApiError.
        # We catch this here so the dashboard gets a clean 409 instead
        # of cascading into a 23503 FK violation on tenant_users.
        # 2026-08-10 FIX: `session is None` is NOT a valid signal for this.
        # With email confirmation enabled (this project: GoTrue
        # mailer_autoconfirm=false), a brand-new, perfectly successful signup
        # ALSO returns session=None — the session only appears after the user
        # clicks the verification link. The old check therefore rejected 100%
        # of new registrations with "account already exists", and left an
        # orphaned auth.users row with no tenant, so the user could neither
        # register nor log in. Both directions dead-ended.
        #
        # The correct discriminator is GoTrue's obfuscated-response contract:
        # for an email that already exists it returns identities == [], while
        # a genuinely new user gets exactly one identity. Only treat an
        # explicitly EMPTY list as "already exists" — if the attribute is
        # missing on some client version, fall through and let the signup
        # proceed rather than re-introducing a block-everyone failure.
        identities = getattr(auth_response.user, "identities", None)
        if isinstance(identities, list) and len(identities) == 0:
            logger.info(
                "Signup for %s returned a user with no identities — email "
                "already exists in auth.users; sending a password-reset "
                "email and responding as if this were a normal pending "
                "signup (anti-enumeration).",
                request.email,
            )
            # 2026-09-18 FIX: this used to raise 409 with "An account with
            # this email already exists" — a textbook email-enumeration
            # oracle (POST candidate emails, 409 vs 200 tells you which are
            # registered), and inconsistent with reset_password's own
            # "always return success, don't reveal if email exists" policy
            # a few lines below. Instead: help the actual account owner (they
            # may have forgotten they have one) via the same password-reset
            # email that endpoint sends, and respond with the EXACT shape a
            # genuine new signup gets while awaiting email confirmation
            # (see the `email_confirmation_required=True` branch below) so
            # the two cases are indistinguishable from the response alone.
            # `user_id` here is GoTrue's own phantom UUID for this case (see
            # the comment above) — already random and never in auth.users,
            # which is exactly what an anti-enumeration placeholder needs.
            # `tenant_id` has no real backing row here (we must NOT create a
            # tenant for someone else's existing account), so a fresh UUID
            # fills the same `tenant_id: str` field the real branch always
            # populates, without persisting anything.
            try:
                get_auth_client().auth.reset_password_email(
                    email=request.email,
                    options={"redirect_to": f"{_public_base_url()}/reset-password"},
                )
            except Exception as reset_err:
                logger.warning(
                    "Could not send password-reset email during signup "
                    "collision for %s: %s", request.email, reset_err,
                )
            return AuthResponse(
                access_token=None,
                refresh_token=None,
                user={"id": user_id, "email": request.email},
                tenant_id=str(uuid4()),
                email_confirmation_required=True,
                email=request.email,
                business_name=request.business_name,
            )

        # 2. Create tenant record
        tenant_manager = TenantManager(db)
        try:
            tenant_id = tenant_manager.create_tenant(
                business_name=request.business_name,
                whatsapp_number=request.phone,
                owner_email=request.email,
                subscription_tier=request.plan,
            )
        except Exception as tenant_err:
            # The Supabase auth user was created above. If the tenant
            # insert fails, leave them dangling and the user can never
            # sign in. Best-effort cleanup so they can retry with the
            # same email. service-role client needed to admin-delete.
            logger.exception(
                "Tenant creation failed for %s; rolling back auth user %s: %s",
                request.email, user_id, tenant_err,
            )
            try:
                db.auth.admin.delete_user(user_id)
            except Exception as cleanup_err:
                logger.warning(
                    "Could not roll back auth user %s after tenant failure: %s",
                    user_id, cleanup_err,
                )
            raise HTTPException(
                status_code=500,
                detail="Failed to create workspace. Please try again or contact support.",
            )

        if not tenant_id:
            try:
                db.auth.admin.delete_user(user_id)
            except Exception as cleanup_err:
                logger.warning(
                    "Could not roll back auth user %s: %s", user_id, cleanup_err,
                )
            raise HTTPException(
                status_code=500,
                detail="Failed to create workspace. Please try again or contact support.",
            )

        # 3. Link user to tenant in tenant_users table.
        # NOTE (2026-08-06): wrap in try/except — the `tenant_users` table
        # has a foreign key to `public.users(id)`, and if the auth.users
        # row we just created isn't mirrored in public.users (no sync
        # trigger, race condition, or migration drift), the insert raises
        # APIError 23503. Without this try/except the entire signup 500s
        # AND leaves an orphaned tenant + auth user. We now roll back
        # both so the user can retry with the same email cleanly.
        try:
            db.table("tenant_users").insert({
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "user_id": user_id,
                "role": "owner",
            }).execute()
        except Exception as link_err:
            logger.exception(
                "tenant_users insert failed for user %s tenant %s; rolling back: %s",
                user_id, tenant_id, link_err,
            )
            # Roll back the tenant we just created
            try:
                db.table("tenants").delete().eq("id", tenant_id).execute()
            except Exception as tenant_rollback_err:
                logger.warning(
                    "Could not roll back tenant %s after tenant_users failure: %s",
                    tenant_id, tenant_rollback_err,
                )
            # Roll back the auth user
            try:
                db.auth.admin.delete_user(user_id)
            except Exception as auth_rollback_err:
                logger.warning(
                    "Could not roll back auth user %s after tenant_users failure: %s",
                    user_id, auth_rollback_err,
                )
            # Map FK violation to a clearer message than a generic 500
            err_str = str(link_err).lower()
            if "foreign key" in err_str or "violates" in err_str:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Account provisioning failed: the auth user was created "
                        "but the tenant linkage row could not be written. "
                        "Please try again — if it keeps happening, contact support."
                    ),
                )
            raise HTTPException(
                status_code=500,
                detail="Failed to link account to workspace. Please try again.",
            )

        # 4a. Assign vertical template if selected at signup
        if request.vertical:
            try:
                db.table("tenant_verticals").insert({
                    "tenant_id": tenant_id,
                    "vertical_id": request.vertical,
                    "enabled": True,
                }).execute()
                logging.info(f"✅ Assigned vertical '{request.vertical}' to tenant {tenant_id}")
            except Exception as vert_err:
                # Non-fatal: vertical can be assigned later from dashboard
                logging.warning(f"⚠️ Could not assign vertical: {vert_err}")

        # 4b. Auto-create client_config so AI persona works from day 1
        try:
            from datetime import datetime
            db.table("client_configs").insert({
                "tenant_id": tenant_id,
                "client_type": "general",
                "manglish_level": "medium",
                "tone": "professional",
                "enabled_tools": [],
                "system_prompt_vars": {
                    "business_name": request.business_name,
                    "business_type": "Business Services",
                    "owner_phone": request.phone,
                },
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }).execute()
            logging.info(f"✅ Auto-created client_config for new tenant {tenant_id}")
        except Exception as cfg_err:
            # Non-fatal: will be auto-created on WhatsApp connection
            logging.warning(f"⚠️ Could not pre-create client_config: {cfg_err}")

        # 5. Send WhatsApp welcome message via support device (non-fatal)
        try:
            import httpx
            import re as _re
            import base64 as _b64
            bridge_url = os.getenv("BRIDGE_URL", "").rstrip("/")
            bridge_user = os.getenv("BRIDGE_USER", "")
            bridge_pass = os.getenv("BRIDGE_PASSWORD", "")
            support_device = os.getenv("SUPPORT_WA_DEVICE_ID", "")
            if bridge_url and bridge_user and support_device and request.phone:
                clean_phone = _re.sub(r"\D", "", request.phone)
                if clean_phone:
                    jid = f"{clean_phone}@s.whatsapp.net"
                    app_url = _public_base_url()
                    welcome_msg = (
                        f"\U0001f44b Hi {request.business_name}!\n\n"
                        f"Welcome to *Bijou AI* \U0001f389\n\n"
                        f"I'm your Bijou Support bot. Here's how to get started:\n\n"
                        f"1\ufe0f\u20e3 *Connect WhatsApp* \u2014 Dashboard \u2192 Settings \u2192 WhatsApp \u2192 Scan QR\n"
                        f"2\ufe0f\u20e3 *Watch your AI work* \u2014 Dashboard \u2192 Inbox\n"
                        f"3\ufe0f\u20e3 *Help & guides* \u2014 {app_url}/static/help.html\n\n"
                        f"Reply here anytime you need support \U0001f64c\n\n"
                        f"_Bijou Support Team_"
                    )
                    auth_header = _b64.b64encode(
                        f"{bridge_user}:{bridge_pass}".encode()
                    ).decode()
                    async with httpx.AsyncClient(timeout=10.0) as _client:
                        await _client.post(
                            f"{bridge_url}/send/message",
                            json={"device_id": support_device, "jid": jid, "text": welcome_msg},
                            headers={"Authorization": f"Basic {auth_header}"},
                        )
                    logging.info(f"✅ Welcome WhatsApp sent to {clean_phone}")
        except Exception as wa_err:
            logging.warning(f"⚠️ Could not send welcome WhatsApp (non-fatal): {wa_err}")

        # 6. Return JWT tokens
        # NOTE (2026-08-06): handle the case where Supabase returns a
        # user but no session. This happens when (a) the email already
        # exists in auth.users (Supabase returns the existing user
        # without a session), or (b) email confirmation is required and
        # the user hasn't confirmed yet. In both cases we previously
        # crashed with `'NoneType' object has no attribute
        # 'access_token'` and turned a real UX signal into a 500. We
        # now roll back the dangling tenant we just created and surface
        # an honest 409/403.
        # 2026-08-10 FIX: a missing session here means "email confirmation
        # pending", NOT "email already exists" — the already-exists case was
        # ruled out at step 1a via the identities check. The old code deleted
        # the auth user AND the tenant we just created and returned 409, which
        # destroyed every legitimate signup.
        #
        # Keep both rows. The user verifies by email, then logs in normally
        # and _resolve_or_link_tenant finds the tenant we persisted here.
        session = getattr(auth_response, "session", None)
        if not session or not getattr(session, "access_token", None):
            logger.info(
                "Signup for %s created tenant %s; awaiting email confirmation "
                "(no session issued yet).",
                request.email, tenant_id,
            )
            return AuthResponse(
                access_token=None,
                refresh_token=None,
                user={"id": user_id, "email": request.email},
                tenant_id=tenant_id,
                email_confirmation_required=True,
                # 2026-08-17: include the same top-level identity fields
                # login() returns. The static signup.html doesn't read them
                # today, but the dashboard does, and a missing `business_name`
                # would surface as "undefined" / "Bijou" the first time a
                # freshly-signed-up user lands anywhere that shows it.
                email=request.email,
                business_name=request.business_name,
            )

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user={"id": user_id, "email": request.email},
            tenant_id=tenant_id,
            email_confirmation_required=False,
            # 2026-08-17: same top-level identity fields as login(). Keeps
            # the contract identical across both endpoints so consumers
            # (static HTML + the dashboard) can rely on a single shape.
            email=request.email,
            business_name=request.business_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Map common Supabase Auth errors to honest HTTP status codes
        # so the dashboard can show the right message and we stop
        # returning 500 for "user already registered" / "rate limit" /
        # "signups not allowed" / network blips.  2026-08-09: expanded
        # coverage after the dashboard signup was returning 500 (no body)
        # on every retry — Fly edge timeout on a hung supabase-py call.
        msg = str(e).lower()
        # Prefer AuthApiError.status when the supabase lib gives us one
        # — it's the most reliable signal of what really went wrong.
        auth_status = getattr(e, "status", None) if isinstance(e, AuthApiError) else None
        auth_code = getattr(e, "code", None) if isinstance(e, AuthApiError) else None
        # GoTrue error codes are more precise than status: weak_password is
        # ALSO a 422 (and supabase-py raises it as AuthWeakPasswordError, not
        # AuthApiError, so it fell through to a 500), and
        # over_email_send_rate_limit is the PROJECT-WIDE confirmation-email
        # cap, not this user going too fast — "wait a minute" was untrue.
        # Measured on production 2026-09-28: first-ever signup attempt from
        # a fresh IP got that 429.
        any_code = getattr(e, "code", None)
        if any_code == "weak_password":
            raise HTTPException(
                status_code=400,
                detail="That password is too weak. Please use at least 8 characters with a mix of letters and numbers.",
            )
        if any_code == "over_email_send_rate_limit":
            logger.error("Supabase email send rate limit hit during signup for %s", request.email)
            raise HTTPException(
                status_code=503,
                detail="We couldn't send your verification email right now. Please try again in about an hour, or contact support and we'll set you up.",
                headers={"Retry-After": "3600"},
            )

        if auth_status == 422 or "already registered" in msg or "already been registered" in msg:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Try signing in instead.",
            )
        if auth_status == 429 or "rate limit" in msg or "too many requests" in msg:
            raise HTTPException(
                status_code=429,
                detail="Too many sign-up attempts. Please wait a minute and try again.",
            )
        if auth_status == 403 or "signups not allowed" in msg or "signups disabled" in msg:
            raise HTTPException(
                status_code=403,
                detail="New signups are temporarily disabled. Please try again later or contact support.",
            )
        if auth_status == 400 or "weak password" in msg or ("invalid" in msg and "password" in msg):
            raise HTTPException(
                status_code=400,
                detail="That password is too weak. Please use at least 8 characters with a mix of letters and numbers.",
            )
        if "invalid" in msg and "email" in msg:
            raise HTTPException(
                status_code=400,
                detail="That email address was rejected by the auth provider. Please use a different one.",
            )
        if auth_status == 401 and ("email" in msg and "confirm" in msg or "verified" in msg):
            raise HTTPException(
                status_code=403,
                detail="Please confirm your email address before signing in. Check your inbox for the verification link.",
            )
        # Network / transport failures — Supabase or Fly edge unreachable.
        # NOTE: the welcome-WhatsApp block below does a local `import httpx`
        # in a try, which makes `httpx` a local variable in this function and
        # shadows the module-level one. Look the class up via the real
        # module (sys.modules) instead so the `isinstance` check works
        # regardless of which path raised.
        try:
            import sys as _sys
            _httpx_mod = _sys.modules.get("httpx")
        except Exception:
            _httpx_mod = None
        if _httpx_mod is not None and isinstance(e, _httpx_mod.HTTPError):
            logging.error("Signup network error: %s", e, exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="The auth service is temporarily unreachable. Please try again in a moment.",
            )
        logging.error("Signup error (status=%s, code=%s): %s",
                      auth_status, auth_code, e, exc_info=True)
        # Surface a useful hint in the detail (sanitized — no raw stack) so
        # the dashboard can show a non-vague message AND we have something
        # to grep for in Fly logs.
        safe_hint = (msg[:200] if msg else type(e).__name__).strip() or type(e).__name__
        raise HTTPException(
            status_code=500,
            detail=(
                "Signup failed. Please try again or contact support if it keeps happening. "
                f"(ref: {type(e).__name__})"
            ),
        )

def _onboarding_redirect_for(db, tenant_id: str) -> Optional[str]:
    """Where a just-logged-in tenant should land: onboarding, or nowhere.

    Returns an absolute /onboard/{token} URL when this tenant still needs to
    connect WhatsApp, or None when it should go to the dashboard as usual.

    Why this exists: static/login.html sent EVERY successful login to
    /dashboard, so a brand-new tenant landed on an empty dashboard with no QR
    prompt and no route to the connect flow. The Google sign-in path already
    got this right (src/saas/google_oauth.py:210) — it checks
    whatsapp_connected_at and redirects to /onboard/{signup_token}. The two
    sign-in methods disagreed. Putting the decision here means one rule serves
    both instead of it being duplicated in JavaScript.

    This must never turn a good login into a failed one, so every failure path
    returns None and the user simply lands on /dashboard.
    """
    try:
        resp = (
            db.table("tenants")
            .select("whatsapp_connected_at, onboarding_completed, signup_token")
            .eq("id", tenant_id)
            .maybe_single()
            .execute()
        )
        row = getattr(resp, "data", None)
        if not row:
            return None

        # Either signal counts as done. whatsapp_connected_at is the one the
        # Google path uses; onboarding_completed covers tenants that finished
        # before that column was populated.
        if row.get("whatsapp_connected_at") or row.get("onboarding_completed"):
            return None

        token = row.get("signup_token")
        if not token:
            # Predates signup_token, or the backfill missed it. Mint one rather
            # than stranding the user with no way into onboarding.
            token = _secrets.token_urlsafe(32)
            db.table("tenants").update({"signup_token": token}).eq("id", tenant_id).execute()

        return f"{_public_base_url()}/onboard/{token}"
    except Exception as e:  # noqa: BLE001 - routing is a nicety, login is not
        logger.warning(f"⚠️ Onboarding routing check failed for {tenant_id}: {e}")
        return None


def _resolve_or_link_tenant(db, user_id: str, email: Optional[str]) -> Optional[str]:
    """Return the user's tenant_id from tenant_users; if there is no link yet,
    auto-link by matching a tenant this email owns. Self-heals existing owners for
    BOTH password and Google login. Uses the service-role client, so the insert
    bypasses RLS. Returns None only if the email owns no tenant."""
    # order() for the same reason as dashboard_api_simple.py::verify_session:
    # a user in >1 tenant must get a deterministic pick (oldest membership),
    # not whatever order Postgres happens to return with no ORDER BY.
    link = (
        db.table("tenant_users")
        .select("tenant_id")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    if link.data:
        return link.data[0]["tenant_id"]
    if not email:
        return None
    owned = (
        db.table("tenants")
        .select("id")
        .or_(f"owner_email.eq.{email},email.eq.{email}")
        .limit(1)
        .execute()
    )
    if not owned.data:
        return None
    tenant_id = owned.data[0]["id"]
    try:
        db.table("tenant_users").insert(
            {"tenant_id": tenant_id, "user_id": user_id, "role": "owner"}
        ).execute()
        logging.info(f"Auto-linked user {user_id} -> tenant {tenant_id} by email {email}")
    except Exception as e:
        logging.warning(f"Auto-link insert skipped ({e})")
    return tenant_id


@router.post("/api/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Professional login with email/password.
    Returns JWT tokens for authenticated access.
    """
    db = get_supabase()

    try:
        # 1. Authenticate with Supabase Auth
        # Auth client, not the shared data client: a successful sign-in fires
        # SIGNED_IN and would replace the service-role credential process-wide.
        auth_response = get_auth_client().auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
        })

        if not auth_response.user or not auth_response.session:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_id = auth_response.user.id

        # 2. Resolve tenant (auto-links existing owners by email on first login)
        tenant_id = _resolve_or_link_tenant(db, user_id, request.email)
        if not tenant_id:
            raise HTTPException(status_code=404, detail="No tenant found for this user")

        # 3. Look up business_name for the resolved tenant.
        # 2026-08-17: the static login.html reads `data.business_name` from
        # the top level of this response and stores it in localStorage. If
        # we don't populate it here, the dashboard falls back to "Bijou" for
        # the shell and shows "undefined" anywhere else. We use maybe_single()
        # so a missing tenant row returns None instead of a 500.
        business_name: Optional[str] = None
        try:
            t_row = (
                db.table("tenants")
                .select("business_name")
                .eq("id", tenant_id)
                .maybe_single()
                .execute()
            )
            t_data = getattr(t_row, "data", None) if t_row else None
            if isinstance(t_data, dict):
                business_name = t_data.get("business_name")
        except Exception as biz_err:
            # Non-fatal: login itself succeeded, just no business_name
            # available. The dashboard has fallbacks (BUSINESS_NAME || "Bijou")
            # so the user still gets a usable shell.
            logger.warning("Could not load business_name for tenant %s: %s", tenant_id, biz_err)

        # 4. Decide where to send them. A tenant that has never connected
        #    WhatsApp goes to the QR flow, matching what google_oauth.py:210
        #    already does — otherwise email/password users land on an empty
        #    dashboard with no prompt and no route into onboarding.
        next_url = _onboarding_redirect_for(db, tenant_id)

        # 5. Return JWT tokens + identity fields the dashboard expects
        return AuthResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            user={"id": user_id, "email": request.email},
            tenant_id=tenant_id,
            email=request.email,
            business_name=business_name,
            next_url=next_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Supabase raises AuthApiError for bad creds, email-not-confirmed,
        # rate-limit, etc. — surface those as honest 4xx codes instead of
        # a generic 500. The raw message goes to logs for diagnosis.
        msg = str(e).lower()
        if "invalid login credentials" in msg or "invalid email or password" in msg:
            logger.info("Login rejected for %s: bad credentials", request.email)
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if "email not confirmed" in msg:
            raise HTTPException(
                status_code=403,
                detail="Please confirm your email before signing in. Check your inbox for the verification link.",
            )
        if "rate limit" in msg:
            raise HTTPException(
                status_code=429,
                detail="Too many sign-in attempts. Please wait a minute and try again.",
            )
        logger.error("Login error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Login failed. Please try again or contact support if it keeps happening.",
        )

def _provision_oauth_tenant(db, user_id: str, email: Optional[str]) -> str:
    """Create a tenant + tenant_users owner row for a first-time OAuth user.

    signInWithOAuth already created the auth.users row client-side, so this
    provisions ONLY the workspace — mirroring signup()'s tenant creation +
    tenant_users insert (same TenantManager helper, same id/tenant_id/user_id/
    role column shape) and its rollback cascade, minus the auth-user
    creation/cleanup. On any failure it rolls the tenant back rather than
    leaving a partial workspace, and raises a clean 500. The real business
    name is collected later during onboarding, so we seed a placeholder from
    the email local-part."""
    business_name = (email.split("@", 1)[0] if email else "").strip() or "My Business"
    tenant_manager = TenantManager(db)
    try:
        tenant_id = tenant_manager.create_tenant(
            business_name=business_name,
            whatsapp_number="",
            owner_email=email,
            subscription_tier="freemium",
        )
    except Exception as tenant_err:
        logger.exception("OAuth tenant creation failed for %s: %s", email, tenant_err)
        raise HTTPException(
            status_code=500,
            detail="Failed to create workspace. Please try again or contact support.",
        )
    if not tenant_id:
        raise HTTPException(
            status_code=500,
            detail="Failed to create workspace. Please try again or contact support.",
        )
    try:
        db.table("tenant_users").insert({
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "role": "owner",
        }).execute()
    except Exception as link_err:
        logger.exception(
            "tenant_users insert failed for oauth user %s tenant %s; rolling back: %s",
            user_id, tenant_id, link_err,
        )
        try:
            db.table("tenants").delete().eq("id", tenant_id).execute()
        except Exception as rollback_err:
            logger.warning(
                "Could not roll back tenant %s after tenant_users failure: %s",
                tenant_id, rollback_err,
            )
        raise HTTPException(
            status_code=500,
            detail="Failed to link account to workspace. Please try again.",
        )
    logger.info(
        "Provisioned tenant %s for first-time OAuth user %s (%s)",
        tenant_id, user_id, email,
    )
    return tenant_id


@router.post("/api/auth/oauth-session")
async def oauth_session(authorization: Optional[str] = Header(None)):
    """Complete a Supabase OAuth (e.g. Google) sign-in. The client obtains a
    Supabase session via signInWithOAuth, then POSTs the access_token here; we
    resolve/auto-link the tenant and return the same shape the dashboard expects."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    db = get_supabase()
    try:
        user_resp = db.auth.get_user(token)
        user = getattr(user_resp, "user", None)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session")
        tenant_id = _resolve_or_link_tenant(db, user.id, user.email)
        if not tenant_id:
            # First-time Google user (D-AUTH-1). signInWithOAuth already
            # created the auth.users row client-side, so — unlike signup() —
            # we provision ONLY the workspace (tenant + tenant_users), then
            # fall through to the normal onboarding-redirect response, exactly
            # like a fresh email signup. Without this, Google was sign-in-only
            # and every new Google user got a 404.
            tenant_id = _provision_oauth_tenant(db, user.id, user.email)
        biz = (
            db.table("tenants").select("business_name").eq("id", tenant_id).limit(1).execute()
        )
        # 2026-08-17 FIX: also surface the refresh_token so the static
        # auth-callback.html can store it in localStorage the same way the
        # email/password login path does. Without this, the dashboard's
        # session-refresh-on-401 has no refresh token to fall back on and
        # the user gets signed out 60 min later instead of being silently
        # refreshed. Falls back to the access token if the Supabase client
        # can't surface one (older supabase-py).
        refresh_token = getattr(getattr(user_resp, "session", None), "refresh_token", None) or ""
        # Same onboarding-routing decision /api/auth/login makes (see
        # _onboarding_redirect_for) — without it, a brand-new tenant signing
        # in with Google lands on an empty dashboard with no QR prompt,
        # because auth-callback.html unconditionally redirects to /dashboard
        # unless this endpoint tells it otherwise.
        next_url = _onboarding_redirect_for(db, tenant_id)
        return {
            "access_token": token,
            "refresh_token": refresh_token,
            "tenant_id": tenant_id,
            "email": user.email,
            "business_name": (biz.data[0]["business_name"] if biz.data else None),
            "next_url": next_url,
        }
    except HTTPException:
        raise
    except Exception as e:
        # Map common Supabase Auth errors to honest codes instead of 500.
        msg = str(e).lower()
        if "session" in msg or "token" in msg:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        logging.error(f"OAuth session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="OAuth session failed")


@router.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """
    Revoke the caller's own session via Supabase Auth.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ", 1)[1]
    try:
        # admin.sign_out(jwt, scope) revokes exactly the token passed in, via
        # a one-off request. The plain `.auth.sign_out()` used before acted on
        # whatever session happened to be cached on get_auth_client()'s
        # process-wide shared client (see its docstring) — not the caller's
        # token. That meant logout could silently no-op, or revoke a
        # different concurrent user's session instead of the caller's.
        get_auth_client().auth.admin.sign_out(token, "global")
    except AuthApiError:
        # Token already invalid/expired — still a successful logout from the
        # caller's point of view.
        pass
    except Exception as e:
        logger.error("Logout error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Logout failed")

    return {"message": "Logged out successfully"}

@router.post("/api/auth/reset-password")
async def reset_password(request: MagicLinkRequest):
    """
    Send password reset email to user.
    Uses Supabase Auth's built-in password recovery.
    """
    db = get_supabase()

    if not request.email or not request.email.strip():
        raise HTTPException(status_code=400, detail="Email address is required")

    try:
        # Get the app URL for the password-reset link. 2026-08-17 FIX:
        # use the canonical public URL (not request.base_url, not the Fly
        # internal host) so the email links to the user-facing domain and
        # the user lands back on the dashboard, not on a raw Fly machine
        # URL with a cert warning. Matches the helper in google_oauth.py.
        redirect_url = f"{_public_base_url()}/reset-password"

        # Send password recovery email via Supabase Auth
        db.auth.reset_password_email(
            email=request.email,
            options={"redirect_to": redirect_url}
        )

        # Always return success (don't reveal if email exists - security best practice)
        return {
            "message": "If an account exists with this email, you will receive a password reset link shortly."
        }

    except Exception as e:
        logging.error(f"Password reset error: {e}", exc_info=True)
        # Still return success message (security best practice)
        return {
            "message": "If an account exists with this email, you will receive a password reset link shortly."
        }


class ChangePasswordRequest(BaseModel):
    new_password: str


@router.post("/api/auth/change-password")
async def change_password(
    request: ChangePasswordRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Change the authenticated user's password using their JWT.
    Requires Authorization: Bearer <access_token> header.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    token = authorization.split(" ", 1)[1]
    db = get_supabase()
    try:
        # Resolve the caller's user id from their token with get_user(jwt=...),
        # which — like get_current_user() above — makes a stateless request and
        # never touches session storage. Then update via admin.update_user_by_id
        # (service-role, same pattern as the admin.delete_user calls elsewhere
        # in this file), instead of the previous set_session()+update_user(),
        # which mutated get_auth_client()'s process-wide shared session on
        # every call — the same hazard documented on that client and on
        # /api/auth/logout above.
        user_result = db.auth.get_user(token)
        if not user_result or not user_result.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        result = db.auth.admin.update_user_by_id(
            str(user_result.user.id), {"password": request.new_password}
        )
        if not result.user:
            raise HTTPException(status_code=400, detail="Failed to update password")
        return {"success": True, "message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        # Map Supabase AuthApiError to honest status codes instead of 500.
        msg = str(e).lower()
        if "different from the old" in msg or "same as" in msg:
            raise HTTPException(
                status_code=400,
                detail="New password must be different from the current password.",
            )
        if "rate limit" in msg:
            raise HTTPException(
                status_code=429,
                detail="Too many password change attempts. Please wait a minute and try again.",
            )
        if "weak" in msg or "short" in msg or "characters" in msg:
            raise HTTPException(
                status_code=400,
                detail=str(e)[:200],
            )
        if "session" in msg or "token" in msg or "unauthorized" in msg:
            raise HTTPException(
                status_code=401,
                detail="Your session expired. Please sign in again and retry.",
            )
        logging.error(f"Change password error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update password")


@router.get("/api/auth/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Return the authenticated user's email and id from their JWT.
    Used by the dashboard to display the account email.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ", 1)[1]
    db = get_supabase()
    try:
        result = db.auth.get_user(token)
        if not result or not result.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"email": result.user.email, "id": str(result.user.id)}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Get current user error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/api/auth/magic-link")
async def send_magic_link(request: MagicLinkRequest):
    """
    Endpoint to send magic link to user's email for login.

    Always returns the same generic success message regardless of whether the
    email is registered — matching /api/auth/reset-password's "don't reveal if
    email exists" policy below. This endpoint used to return 404 "No account
    found with that email" whenever the lookup failed, which let anyone probe
    arbitrary emails against it to find out which ones have a Bijou account.
    """
    db = get_supabase()
    generic_response = {
        "message": "If an account exists with this email, you will receive a login link shortly."
    }

    # Validate email is not empty
    if not request.email or not request.email.strip():
        raise HTTPException(status_code=400, detail="Email address is required.")

    # Query the tenant database to find the tenant by email
    try:
        tenant = db.table("tenants").select("id, signup_token, name") \
            .eq("email", request.email).maybe_single().execute()
    except Exception as e:
        # If tenant not found, Supabase throws an exception
        logging.warning(f"No tenant found for email: {request.email}")
        return generic_response

    # Double-check if tenant data exists
    tdata = getattr(tenant, "data", None) if tenant else None
    if not tdata:
        return generic_response

    # Construct Magic Link URL. 2026-08-17 FIX: prefer the canonical public
    # base via `_public_base_url()` so the link lands on app.mybijou.xyz
    # (or whatever PUBLIC_URL is set to), not on the Fly internal host.
    # LOGIN_URL is honored first so tests/overrides can point at a
    # different path without touching env defaults.
    login_url = os.getenv("LOGIN_URL")
    if not login_url:
        login_url = f"{_public_base_url()}/static/login.html"

    # NOTE (2026-08-06): use the validated `tdata` guard variable rather
    # than raw `tenant.data[...]` — if the tenant is missing or the column
    # is null, the line 582 check already returned 404, but a future
    # refactor could remove that check and the unguarded `tenant.data[]`
    # access would 500.
    token = tdata.get("signup_token")
    tenant_id = tdata.get("id")
    business_name = tdata.get("name", "") or ""
    if not token or not tenant_id:
        logging.warning(f"Magic link requested for {request.email} but tenant row is missing signup_token or id")
        return generic_response
    magic_link_url = f"{login_url}?token={token}&tenant_id={tenant_id}"

    # Send branded magic link email via EmailService template
    email_service = get_email_service()
    try:
        email_sent = email_service.send_login_magic_link(
            to=request.email,
            business_name=business_name,
            magic_link_url=magic_link_url,
        )
        if not email_sent:
            logging.error(f"Failed to send magic link email to {request.email}")
    except Exception as e:
        logging.error(f"Unexpected error sending magic link: {e}", exc_info=True)

    # Same response whether the send above succeeded, failed, or the email
    # simply wasn't registered — see docstring.
    return generic_response
