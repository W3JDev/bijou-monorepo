# FIXES-AUTH.md

Ranked fixes for the auth / onboarding / agent-output hardening pass.
**Date:** 2026-09-21 · **Branch:** `audit/hardening-pass`
Companion to `DIAGNOSIS-AUTH.md` (which has the full file:line evidence per finding).

**Nothing here is deployed.** CI is billing-locked and Fly is billing-locked
(per `CLAUDE.md`); these land in the working tree on `audit/hardening-pass`.
Deploy is the operator's Dokploy UI step — see `ops/DOKPLOY_DEPLOY.md`.

**Verification level, stated honestly:** all fixes are verified at the
**unit / import / compile** layer (commands + output below). **None** has been
exercised through a running app against real Supabase / a real browser flow —
that requires a deploy this pass does not do. Where a fix can only be proven
end-to-end, it is marked **NOT VERIFIED (e2e)**.

---

## The 8 ranked fixes (sign-up / sign-in pipeline — Job 2)

Ranked by severity. ✅ = implemented this pass. 📝 = documented recommendation
(deliberately not implemented — rationale given).

### 1. ✅ D-AUTH-1 — Google sign-up now provisions a tenant · CRITICAL
New Google users hitting "Sign up with Google" got a `404 "Please sign up first"`
because `oauth_session` only *resolved* a tenant, never created one.
**Fix:** `src/saas/auth_api.py` — new `_provision_oauth_tenant(db, user_id, email)`
mirrors `signup()`'s tenant + `tenant_users` creation (same column shape, same
rollback cascade); `oauth_session` calls it when `_resolve_or_link_tenant` returns
`None`, then falls through to the normal JWT + onboarding-redirect response.
Does not create a Supabase auth user (already made client-side by
`signInWithOAuth`). Existing-tenant callers unchanged.
**EVIDENCE:** `tests/unit/test_oauth_session_onboarding_routing.py` →
`test_oauth_session_provisions_tenant_for_new_google_user`,
`test_oauth_session_existing_tenant_does_not_provision` — 4 passed.
**NOT VERIFIED (e2e):** real `signInWithOAuth` → `auth-callback.html` → live backend.

### 2. ✅ D-CORS-1 — CORS wildcard + credentials removed · HIGH
`allow_origins=["*"]` with `allow_credentials=True` let any site make credentialed
calls; the real dashboard origin wasn't even listed.
**Fix:** `src/core/bijou.py:481-490` — dropped `"*"`, added
`https://app.mybijou.xyz`, and a comment forbidding re-adding `"*"`.
**EVIDENCE:** import smoke shows middleware loads; explicit origins only.

### 3. ✅ D-AUTH-2 — broken custom Google callback neutralized · HIGH
`google_oauth.py`'s callback inserts non-existent `tenant_users` columns
(`email`, `is_main_contact`) and omits `user_id NOT NULL` → 500, and never makes
an `auth.users` row. It is an orphaned second implementation.
**Fix:** un-mounted the router at `src/core/bijou.py` (the former
`app.include_router(google_oauth_router)` block), with a comment pointing here.
The live Supabase-native path (`oauth_session`, now fix #1) handles Google fully.
File left in place for reference; revive only after schema reconciliation.

### 4. ✅ D-AUTH-3 — Google connection-pool anti-pattern removed from the live path · HIGH
`google_oauth.get_supabase()` did `create_client()` per call (no HTTP/1.1 forcing),
re-opening the `ConnectionTerminated`/HTTP-2 pattern `get_auth_client()` exists to
avoid. Resolved by the same un-mount as #3 — the anti-pattern code is no longer
reachable from any mounted route.

### 5. ✅ D-AUTH-4 — only one Google implementation is mounted now · MEDIUM
Two divergent Google impls were mounted at once; a stray link to
`/api/auth/google/login` walked users into the broken Path B. The un-mount (#3)
leaves exactly one Google path — the working native one.

### 6. 📝 D-AUTH-5 — magic-link ships a long-lived dashboard token in a URL · MEDIUM
`auth_api.py:1150-1156` emails `?token={signup_token}`, and `signup_token` is the
same value `verify_session` accepts as a dashboard credential — not a true,
expiring OTP.
**Recommended (not done):** replace the homemade link with Supabase's real OTP
(`auth.sign_in_with_otp`) so the link is single-use and time-boxed. Deferred
because it changes an email-delivery behavior that can only be validated with a
real mailer + browser round-trip, which this pass can't exercise.

### 7. 📝 D-AUTH-6 — `oauth_session` returns a dead `refresh_token` · LOW
`auth_api.py:920` — `db.auth.get_user(token)` yields no session, so the returned
`refresh_token` is almost always `""`. Masked today by `auth-callback.html`
falling back to the client session's refresh token.
**Recommended (not done):** either stop returning the field or source it from the
actual token exchange, and document the contract. Low impact, no user-facing break.

### 8. Context — the 12 prior-audit bugs (commit `3b4784f`) remain correctly fixed
Signup `identities==[]` vs `session=None`, tenant+`tenant_users` creation with
rollback, per-IP signup rate limit, canonical `_public_base_url()`, logout/
change-password shared-session hazards, and `verify_session` tenant isolation were
re-verified sound (`DIAGNOSIS-AUTH.md §2`). No regressions introduced —
193 auth/tenant unit tests + 9 security tests pass (below).

---

## Agent onboarding (Job 3)

### ✅ D-ONB-1 — onboarding vertical choice now configures the agent · HIGH
The onboard business-type dropdown wrote only `business_profiles.business_type`,
but `vertical_loader` reads `tenant_verticals` — so the choice never reached the
agent prompt.
**Fix:** `src/saas/business_profile_api.py` — `_map_business_type_to_vertical()`
maps the dropdown value to a valid vertical key (`restaurant→fnb`,
`realestate/property→property`, `healthcare/dental/clinic→dental`; unknown → skip),
and an additive idempotent upsert into `tenant_verticals` (same column shape as
`auth_api.py:510`). Does **not** change the `ENABLE_VERTICAL_TEMPLATES=false`
default (ops decision) — noted in-code.
**EVIDENCE:** `tests/unit/test_business_profile_vertical.py` — 4 passed
(3 known types upsert; unknown writes nothing).
**NOT VERIFIED (e2e):** requires `ENABLE_VERTICAL_TEMPLATES=true` + a live DB.

### 📝 Not done this pass (scoped out — larger features, honest incompleteness)
- **D-ONB-2 — KB seeding during onboarding is missing.** The live flow has no KB
  step; the only upload endpoint is on the dead v2 router with extraction commented
  out. Building a real KB-seeding step is a feature, not a fix — recommend a
  dedicated task.
- **D-ONB-3 — `BusinessTemplateSeeder` is built but never invoked.** Wiring
  auto-seeding by business type is a feature; recommend pairing it with D-ONB-1's
  mapping so type selection seeds both vertical and templates.
- **D-ONB-4 — no persona/tone step in onboarding.** Job 4 delivers the *mechanism*
  (per-tenant `client_configs.tone`); adding an onboarding UI step to set it is a
  follow-up. The dashboard is the current place to set tone.
- **Dead duplicated surface** (`onboarding_api_v3.py`, `onboarding_complete.py` +
  `onboarding.html`, split completion-state schema): recommend deleting the dead
  routers in a separate cleanup PR so this hardening diff stays reviewable.

---

## Agent output style (Job 4)

### ✅ Default tone + per-tenant override
**Fix:** `src/core/bijou.py` — module-level `DEFAULT_AGENT_TONE`
(`"warm, friendly, and professional"`) + `_build_tone_instruction(client_config)`,
called in the prompt-assembly chain right after the Manglish block. Per-tenant
override reads `client_configs.tone` (already loaded — **no migration, no new
query, no schema change**); falls back to the default. Known tones get specific
guidance; unknown tones are still injected; blank falls back.
**EVIDENCE:** `tests/unit/test_agent_tone.py` — 7 passed.

### ✅ D-STYLE-1 — dashboard Manglish toggle now reaches the prompt · HIGH
The toggle wrote `tenants.manglish_mode` but the prompt read `client_config`
(from `client_configs`, which has no such column) → the toggle was a no-op.
**Fix:** `src/saas/tenant_router.py::get_client_config()` — the one chokepoint all
readers pass through — now merges `tenants.manglish_mode` into the returned config.
One PK-keyed single-column select per load (marked with an upgrade note).
**EVIDENCE:** 193 auth/tenant unit tests + 9 `test_call_security.py` pass (no
regression from the added key).

---

## Verification (commands + output)

```bash
# from packages/backend/
$ ./.venv/Scripts/python.exe -m py_compile src/core/bijou.py \
    src/saas/tenant_router.py src/saas/auth_api.py src/saas/business_profile_api.py
PY_COMPILE_OK

$ ./.venv/Scripts/python.exe -c "import src.core.bijou"   # module-level app + includes
IMPORT_OK   # Google Path B no longer in the include logs (unmount confirmed)

$ ./.venv/Scripts/python.exe -m pytest tests/unit/test_agent_tone.py \
    tests/unit/test_oauth_session_onboarding_routing.py \
    tests/unit/test_business_profile_vertical.py -q -p no:cacheprovider -s
15 passed

$ ./.venv/Scripts/python.exe -m pytest tests/unit/ -q -p no:cacheprovider -s \
    -k "auth or signup or session or oauth or tenant or cors"
193 passed, 452 deselected

$ ./.venv/Scripts/python.exe -m pytest tests/security/test_call_security.py -q -p no:cacheprovider -s
9 passed

# production untouched, still healthy:
$ curl -sS https://bijou-production.fly.dev/health
{"status":"healthy","version":"2.2.0","database":"supabase"}   HTTP 200
```

## Files changed (this pass only)
```
M  packages/backend/src/core/bijou.py            # CORS, unmount Google Path B, tone layer
M  packages/backend/src/saas/auth_api.py         # D-AUTH-1 Google signup provisioning
M  packages/backend/src/saas/business_profile_api.py  # D-ONB-1 vertical connect
M  packages/backend/src/saas/tenant_router.py    # D-STYLE-1 manglish merge
A  packages/backend/tests/unit/test_agent_tone.py
A  packages/backend/tests/unit/test_business_profile_vertical.py
M  packages/backend/tests/unit/test_oauth_session_onboarding_routing.py
A  DIAGNOSIS-AUTH.md
A  FIXES-AUTH.md
```
> The `packages/landing/*` modifications in the working tree are **NOT part of this
> pass** (a marketing repositioning present before these fixes). Excluded from any
> commit here.
