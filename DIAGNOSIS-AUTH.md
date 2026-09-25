# DIAGNOSIS-AUTH.md

Auth / onboarding / agent-output hardening pass — diagnosis.
**Date:** 2026-09-21 · **Branch:** `audit/hardening-pass`

Scope: diagnose the current state of the sign-up/sign-in pipeline, the agent
onboarding flow, and the agent output-style controls, with `file:line` citations.
This is a *diagnosis* — fixes are tracked in `FIXES-AUTH.md`.

> **Prior art:** commit `3b4784f` (2026-09-18) already fixed 12 signup/signin/
> onboarding bugs. This pass reports what **remains**, not what that audit fixed.

---

## 0. Pre-flight (verified)

| Check | Result | Evidence |
|---|---|---|
| Production health | ✅ 200 | `curl https://bijou-production.fly.dev/health` → `{"status":"healthy","version":"2.2.0","database":"supabase"}` |
| Route count (startup completed) | ✅ 182 paths | `curl .../openapi.json` → 182 (floor for "startup failed" is ~41) |
| `app.mybijou.xyz` == Fly prod | ✅ same | both serve v2.2.0 / 182 paths |
| Deploy artifacts present | ✅ | `ops/DOKPLOY_DEPLOY.md`, `ops/dokploy/Dockerfile.backend.dokploy`, `docker-compose.dokploy.yml` |

Doc drift (non-blocking): `ops/DOKPLOY_DEPLOY.md:265` and the app-gotcha in
`CLAUDE.md` say a healthy instance serves "~222 paths"; the live count is **182**.
Not a fault — startup completes — but the number should be corrected.

---

## 1. Confirmed defects (verified directly, independent of code-map explorers)

### D-CORS-1 — wildcard origin + credentials  · **HIGH** · security
`packages/backend/src/core/bijou.py:481-490`
```python
allow_origins=[ ..., "https://mybijou.xyz", "https://www.mybijou.xyz",
    "*",  # Allow all origins temporarily for testing
],
allow_credentials=True,
```
`"*"` together with `allow_credentials=True` makes Starlette's `CORSMiddleware`
reflect **any** request origin and return `Access-Control-Allow-Credentials: true`.
That lets any website make credentialed cross-origin requests to the API.
Also note `app.mybijou.xyz` (the real dashboard origin) is **not** in the explicit
list — it works today only because of the `"*"`. Root cause: a "temporary for
testing" wildcard left in production.

---

## 2. Sign-up / sign-in pipeline

Commit `3b4784f` landed correctly: shared-client session hazards (logout,
change-password, login, refresh), `identities==[]` vs `session=None`
discrimination, canonical-URL usage, and anti-enumeration are all present and
correct. Email/password signup, login, logout, change-password, reset-password,
and `verify_session` tenant isolation are **sound** and re-verified. Remaining
live defects, all in the **Google OAuth** area:

### D-AUTH-1 — Google sign-up is impossible for new users · **CRITICAL** · correctness
`src/saas/auth_api.py:904-909` — `POST /api/auth/oauth-session` calls
`_resolve_or_link_tenant`, and on `None` raises
`404 "…Please sign up first."` But **both** `static/login.html:491` and
`static/signup.html:545` funnel Google through this same endpoint, and **no code
path provisions a tenant for a first-time Google user**. Google is effectively
sign-in-only; a brand-new user clicking "Sign up with Google" gets a 404.
Root cause: `oauth_session` resolves a tenant but never creates one, unlike
`signup()`.

### D-AUTH-2 — Custom Google callback (`google_oauth.py`) cannot complete · **HIGH** · correctness
`src/saas/google_oauth.py:306-314` inserts into `tenant_users` with
`{tenant_id, email, role, is_main_contact, created_at}` — but the table requires
`user_id NOT NULL` and has **no** `email`/`is_main_contact` columns
(`migrations-py/0000_baseline.sql:2014-2021`). Insert fails → `except` at
`:319-321` raises 500. It also never creates an `auth.users` row, so even a
successful insert yields a user who can never log in. Mounted at `bijou.py:857`
but unreferenced by any static page. Root cause: predates the Supabase-native
path, never reconciled with the schema.

### D-AUTH-3 — `google_oauth.get_supabase()` reintroduces the connection-pool anti-pattern · **HIGH** · reliability
`src/saas/google_oauth.py:79-87` calls `create_client()` per invocation with no
`ClientOptions`/HTTP-1.1 forcing — the exact "new httpx pool per call →
ConnectionTerminated / HTTP/2 GOAWAY" pattern that `auth_api.py:52-56` +
`get_auth_client` exist to avoid. Only bites if the (broken) Path B runs.

### D-AUTH-4 — two divergent Google implementations mounted at once · **MEDIUM** · dead-code/footgun
`bijou.py:693` (native, via `oauth_session`) and `bijou.py:857` (custom, broken).
Any link to `/api/auth/google/login` walks a user into the broken Path B.

### D-AUTH-5 — magic-link ships a long-lived bearer token in a URL · **MEDIUM** · security
`src/saas/auth_api.py:1150-1156` emails `?token={signup_token}`, and
`signup_token` is the same value `verify_session` accepts as a dashboard
credential (`dashboard_api_simple.py:408`). Not a true OTP, doesn't expire like
one. Root cause: homemade link reuses the onboarding/dashboard token.

### D-AUTH-6 — `oauth_session` server-returned `refresh_token` is effectively dead · **LOW** · contract
`src/saas/auth_api.py:920` — `db.auth.get_user(token)` yields no `session`, so
the returned `refresh_token` is almost always `""`. Masked today because
`auth-callback.html:120` falls back to the client Supabase session's
refresh_token, but the server contract is misleading and breaks any non-JS
consumer.

## 3. Agent onboarding flow

**Live flow = 3 steps**, served by `static/onboard-qr.html` at `/onboard/{token}`
(`bijou.py:6861-6876`) on top of `onboarding_api.py` (mounted `/api/onboarding`,
`bijou.py:623-625`) + `business_profile_api.py`:

1. Signup → `POST /api/auth/signup` → redirect to `/onboard/{token}`
   (`auth_api.py:709-751`).
2. Business-profile form (shown if `needs_business_info`) →
   `POST /api/business/profile` (`business_profile_api.py:188-331`).
3. WhatsApp QR connect → `GET /api/onboarding/qr/{token}` (`onboarding_api.py:558-729`)
   → on connect, `POST /api/onboarding/complete/{token}`
   (`onboarding_api.py:732-783`) sets `tenants.onboarding_completed` → dashboard.

**Working:** QR connect against the production **GOWA** bridge is correct — calls
`GET /app/login?device_id=…`, and on `404 DEVICE_NOT_FOUND` provisions via
`POST /devices` then retries (`onboarding_api.py:635-669`); QR bytes proxied
(`onboarding_api.py:521-555`). Business-profile capture is tenant-scoped and syncs
`phone`/`business_name` back to `tenants`. The 3b4784f `X-Onboarding-Token` fix is
real (`onboarding.html:448-456`) — but lives in a **dead** page (see below).

### Dead / duplicated surface (footgun, not a live break)
- `onboarding_complete.py` (`/api/onboarding/v2`, mounted `bijou.py:630-632`) is
  reachable only from `static/onboarding.html`, which is served nowhere except a
  `/signup` fallback that never fires (`signup.html` exists). **Dead in practice.**
- `onboarding_api_v3.py` — **never imported** anywhere in `src/`; would prefix-collide
  with the live router if mounted. Contains the *only* email-verification endpoints
  (`/verify-email`, `/resend-verification`, `onboarding_api_v3.py:225,317`) — so that
  variant is entirely unreachable.
- **Split completion-state schema:** live path sets `tenants.onboarding_completed`
  (`onboarding_api.py:763-769`); the dead v2 + webhook handlers
  (`bijou.py:7731-7748, 7975-8000, 8183-8193`) write `onboarding_progress.*` /
  `tenants.onboarding_step`, which the live status endpoint never reads.

### D-ONB-1 — the vertical the user picks in onboarding never configures the agent · **HIGH** · correctness
The onboard-page business-type dropdown (`onboard-qr.html:283-295`) is written to
`business_profiles.business_type` (`business_profile_api.py:255-262`), but
`vertical_loader.get_tenant_vertical_prompt` reads the **`tenant_verticals`** table
(`vertical_loader.py:81-85`). The only writer of `tenant_verticals` is a *separate*
hidden `vertical` field on `signup.html` (`auth_api.py:510`). Net: a business that
selects "Restaurant" during onboarding gets **no** vertical prompt. Also gated
behind `ENABLE_VERTICAL_TEMPLATES=false` by default (`vertical_loader.py:45`).

### D-ONB-2 — knowledge-base seeding is missing from the live flow · **MEDIUM** · gap
`onboard-qr.html` has no KB step. The only KB-upload endpoint lives on the dead v2
router (`onboarding_complete.py:513-577`) and even it stores a placeholder
`upload_url` with text-extraction commented out (`onboarding_complete.py:544,550-552`).
No onboarding path seeds a knowledge base.

### D-ONB-3 — `BusinessTemplateSeeder` built but never invoked · **MEDIUM** · dead-code
Constructed at `bijou.py:1995-1997`; neither `detect_and_seed_business_type`
(`business_template_seeder.py:616`) nor `seed_business_templates` (`:521`) is called
from anywhere live. Auto-template seeding by business type does not happen.

### D-ONB-4 — no persona/tone step in onboarding · **MEDIUM** · gap
No onboarding step/endpoint/field captures agent persona or tone anywhere in the live
flow. (Ties directly to §4 and Job 4.)

## 4. Agent output style / persona

**Assembly chain (live path is entirely `src/core/bijou.py`;
`agent_loop.py`/`gateway_agent.py` are unwired Phase-2 experiments):**

1. `_get_default_system_prompt()` reads `src/core/bijou_system_prompt.txt`
   (`bijou.py:5652-5664`).
2. Base assignment `bijou.py:4868-4870` — with comment *"TEMPORARY FIX: Always use
   file-based prompt (bypass persona manager)"* (`bijou.py:4866-4871`); the
   `personas` table is deliberately not consulted.
3. Append layers: vertical (`4876-4888`), **Manglish (`4893-4901`)**, TRACE (`4965`),
   media (`4996`).
4. Message array `bijou.py:5156-5166`; LLM call
   `_llm_gateway.complete("ai://reasoning", …)` `bijou.py:5284-5293`.
5. `client_config` comes from `tenant_router.get_client_config()` → `select("*")` on
   the **`client_configs`** table (`tenant_router.py:794-800`).

### Per-tenant tone override: schema EXISTS, code is DISCONNECTED
- `client_configs` **already has** `tone text DEFAULT 'professional'` and
  `manglish_level text DEFAULT 'medium'` (`baseline.sql:653-654`), and because
  `get_client_config` does `select("*")`, **`client_config["tone"]` is already in
  memory at the assembly point** — but **nothing reads it.** This is the closest
  existing override and it's completely unused.
- The `personas` table + `persona_manager.py` are a full parallel persona store
  (`baseline.sql:1687-1713`) but **bypassed** for reply rendering (`bijou.py:4866-4871`);
  only used for owner WhatsApp commands. Reviving it is *not* the small diff.

### D-STYLE-1 — dashboard Manglish toggle is a no-op on the live prompt · **HIGH** · correctness
Settings writes `manglish_mode` to the **`tenants`** table
(`settings_api.py:440-444`; column `baseline.sql:2089`), but the prompt reads
`client_config.get("manglish_mode")` (`bijou.py:4893`), and `client_config` comes
from **`client_configs`**, which has no `manglish_mode` column. So the dashboard
Manglish toggle never affects replies — the injection block at `bijou.py:4893` is
effectively dead for dashboard-driven config.

### Where the Manglish voice lives
Hardcoded in `src/core/bijou_system_prompt.txt:6-12` ("CRITICAL RULE — MANGLISH
ALWAYS"), NOT per-tenant. `packages/landing/api/chat.js` carries a byte-identical
copy (edit together). `.w3j-legacy*` variants are unused.

### Smallest-diff insertion point for Job 4 (default tone + per-tenant override)
`bijou.py:4891-4902` — the existing Manglish block, where `client_config` (with its
already-loaded `tone` column) is in scope. Add a module-level `DEFAULT_TONE` and an
append that reads `client_config.get("tone")`. Default handles the default; the
`client_configs.tone` column handles the per-tenant override — **no migration, no new
query, no schema change.** (Fixing D-STYLE-1 in the same spot: read the toggle from a
source that matches the read path, or write tone to `client_configs`.)

---

## 5. Fix priority (feeds `FIXES-AUTH.md`)

| ID | Severity | Job | One-line |
|---|---|---|---|
| D-AUTH-1 | CRITICAL | 2 | Google sign-up 404s for new users — no tenant provisioning |
| D-CORS-1 | HIGH | 2 | `"*"` origin + credentials; real dashboard origin missing |
| D-AUTH-2 | HIGH | 2 | Custom Google callback writes non-existent columns → 500 |
| D-STYLE-1 | HIGH | 4 | Dashboard Manglish toggle no-ops (wrong table) |
| D-ONB-1 | HIGH | 3 | Onboarding vertical choice never reaches the agent |
| D-AUTH-3 | HIGH | 2 | `google_oauth` per-call client → connection-pool anti-pattern |
| D-AUTH-4 | MED | 2 | Two Google impls mounted; broken Path B reachable |
| D-AUTH-5 | MED | 2 | Magic-link ships long-lived dashboard token in URL |
| D-ONB-2/3 | MED | 3 | KB seeding missing; template seeder dead |
| D-ONB-4 | MED | 3/4 | No persona/tone step in onboarding |
| D-AUTH-6 | LOW | 2 | `oauth_session` returns dead `refresh_token` |
