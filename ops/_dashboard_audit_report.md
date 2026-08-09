# Bijou Dashboard Audit Report

**Auditor:** general-purpose worker (Mavis)  
**Date:** 2026-08-10  
**Branch:** main  
**Scope:** `packages/backend/static/*.html` + `packages/backend/src/**/*.py` (dashboard routes/APIs only)

## Summary

| # | Bug | File | Severity | Status |
|---|-----|------|----------|--------|
| 1 | `/api/admin/tenants` returns all tenant PII with no auth | `saas/admin_api.py:110` | **CRITICAL** | Already fixed in commit `196f644` (pending deploy) |
| 2 | `escHtml` only escapes `&<>` — breaks inline `onclick` when transcript contains `'` | `static/help.html:3783` | HIGH | Fixed in `12cc45e` |
| 3 | Ticket form uses `onclick="...submitTicket('${transcript}')"` — JS syntax error + XSS | `static/help.html:3857` | HIGH | Fixed in `12cc45e` |
| 4 | `admin.html` renders tenant data with no escaping + inline `onclick` with `business_name` | `static/admin.html:319,334` | HIGH | Fixed in `cde204f` |
| 5 | `esc()` in `outreach.html` only escapes `<>` (and not `&`) | `static/outreach.html:1201` | MEDIUM | Fixed in `190623a` |
| 6 | `kb-wizard.html` `escHtml` only escapes `&<>\n` | `static/kb-wizard.html:1070` | MEDIUM | Fixed in `3060480` |
| 7 | `system-check.html` injects `error.message` into `innerHTML` unescaped | `static/system-check.html:545,569,594,620,649,676` | LOW | Fixed in `c76d772` |
| 8 | `dashboard.html` falls back `TOKEN` to `TENANT_ID` (UUID) when no `?token=` — sends bogus auth | `static/dashboard.html:334` | LOW | Fixed in `e27a80b` |
| 9 | `/api-docs` and `/changelog` return 404 (missing `docs/api-docs.html` + `docs/CHANGELOG.md`) | `core/bijou.py:6082,6091` | LOW | No fix (content missing, not code) |
| 10 | `body.dict()` in Pydantic v2 — deprecation warning only | `saas/contacts_api.py:285` | NIT | Not fixed (warning, not a bug) |
| 11 | `core/dashboard_api.py` is dead code (router never mounted) | `core/dashboard_api.py` | NIT | Not fixed (cleanup, not a bug) |

## Bug details

### 1 — CRITICAL: `/api/admin/tenants` leaks all tenant PII
- **Evidence:** `curl https://app.mybijou.xyz/api/admin/tenants` returns 200 with 20+ KB of `{id, business_name, email, phone, status, ...}` for every tenant in the database. No `Authorization` header, no API key, no session check.
- **Root cause:** `src/saas/admin_api.py` mounts an `APIRouter` with no auth dependency. The route at line 110 (`list_tenants`) reads straight from Supabase using the service key.
- **Existing fix:** Commit `196f644` ("fix(backend): route SRP error log through stdlib logger" — also contains the admin auth gate) added `Depends(_check_admin_key)` to every `/api/admin/*` route. The dependency reads `ADMIN_API_KEY` from env and matches it against the `X-Admin-Key` request header. If the env var is unset, endpoints return 503; otherwise 401 with no/wrong header.
- **Operator action:** The live server is still running the pre-fix code (verified via `curl` — endpoint still 200). Push deploy, then set `ADMIN_API_KEY` in production env and store the value in `localStorage.admin_api_key` on the operator's browser before opening `/admin`.

### 2 — HIGH: `help.html` `escHtml` doesn't escape quotes
- **File:** `packages/backend/static/help.html:3783` (original)
- **Code:**
  ```js
  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\n/g, "<br>");
  }
  ```
- **Why broken:** No `"` or `'` escape. Used in three unsafe contexts:
  1. `value="${escHtml(state.tenantName || "")}"` (form input) — a tenant whose business name contains `"` can break out of the attribute and inject arbitrary HTML attributes → XSS.
  2. `<textarea>${escHtml(state.pendingTicket || "")}</textarea>` — same shape, lower risk (no value attribute).
  3. `onclick="BijouChat.submitTicket('${escHtml(transcript)}')"` — any user message containing an apostrophe ("I'm", "don't") makes the inline JS handler throw a syntax error → **the ticket submit button silently fails for any user who has ever used an apostrophe in chat**. The `escHtml` function only matters in HTML-attribute context; in inline-JS the browser decodes `&#39;` back to `'` *before* the JS parser sees it, so just fixing the escape function is not enough for context #3.
- **Fix (commit `12cc45e`):**
  - Added `"` and `'` to `escHtml`.
  - Replaced the `onclick="BijouChat.submitTicket('${transcript}')"` pattern with a `data-transcript` attribute holding `JSON.stringify(transcript)` + a post-`appendHtml` `addEventListener` that parses the JSON and calls `BijouChat.submitTicket(...)`. No user input ever lands inside a JS string literal.

### 3 — HIGH: `admin.html` XSS via tenant data + inline `onclick`
- **File:** `packages/backend/static/admin.html:319,320,334,353`
- **Why broken:** `tenant.business_name`, `tenant.email`, and `tenant.phone` are user-controlled (signed up at signup time, never re-validated) and were dropped into `innerHTML` with no escape. Plus the "Generate QR" button used `onclick="generateQR('${tenant.id}', '${tenant.business_name}')"`. A tenant signing up with name `Acme" onmouseover="alert(1)` would get XSS on `/admin`.
- **Fix (commit `cde204f`):**
  - Added `escHtml()` helper (escapes `&<>"'`).
  - Escape every tenant field before interpolation; render `tenant.created_at` via `escHtml(new Date(...).toLocaleDateString())` for safety even though it's server-formatted.
  - Replaced inline `onclick` with a `data-tenant-id` / `data-tenant-name` attribute pair + `addEventListener` after `appendHtml`.
  - Replaced `modalSubtitle.innerHTML = '...<code>${tenantId}</code>'` with `textContent` + a `createElement('code')` + `appendChild`.
  - `loadTenants` and `generateQR` now attach an `X-Admin-Key` header from `localStorage.admin_api_key` so the new admin auth gate (bug #1) accepts the request.

### 4 — MEDIUM: `outreach.html` `esc()` skips `&` and quotes
- **File:** `packages/backend/static/outreach.html:1201`
- **Code:**
  ```js
  function esc(s) {
    return String(s || "")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
  ```
- **Why broken:** No `&` escape (so a campaign named `Acme & Co` renders with a literal `&` in the DOM, which most browsers tolerate but is invalid HTML), no `"` or `'` escape (latent if a future caller uses it in an attribute). Also unsafe `innerHTML` with `resp.sent_to` and `e.message` from server.
- **Fix (commits `190623a`, `4754940`):**
  - Added `&` and quotes to `esc()`.
  - Wrapped `resp.sent_to` and `e.message` interpolations in `esc()` in the `sendTestMessage` function.

### 5 — MEDIUM: `kb-wizard.html` `escHtml` doesn't escape quotes
- **File:** `packages/backend/static/kb-wizard.html:1070`
- Same broken escape as bug #2, but call sites are currently `innerHTML` only (no `value=` or `onclick=`), so the live impact is lower. The FAQ question/answer text is user-controlled though, so the missing `"`/`'` escape is a latent XSS if anyone ever changes the call site to use an attribute.
- **Fix (commit `3060480`):** Added `"` and `'` to `escHtml` so the function is actually safe by name.

### 6 — LOW: `system-check.html` interpolates `error.message` into `innerHTML`
- **File:** `packages/backend/static/system-check.html` (6 sites)
- **Why medium:** `error.message` is browser-side today, but FastAPI error responses include `detail` strings that can echo user input. The page is a self-serve diagnostic tool (not customer-facing), so the exploitability is low, but the pattern is the same as bugs #2 and #4.
- **Fix (commit `c76d772`):** Added an `esc()` helper and wrapped all 6 `error.message` interpolations.

### 7 — LOW: `dashboard.html` magic-link TOKEN falls back to TENANT_ID
- **File:** `packages/backend/static/dashboard.html:334`
- **Code (before):** `let TOKEN = params.get("token") || TENANT_ID;`
- **Why broken:** When a user lands on the dashboard with `?tenant_id=<UUID>` but no `?token=` param and no JWT in `localStorage`, the `api()` helper's `useMagicLink` becomes truthy and sends `?token=<UUID>`. The backend's `verify_session` then looks up `signup_token` and 401s. Edge case (the dashboard usually has either a JWT or a real `?token=`), but produces a confusing "log in again" loop.
- **Fix (commit `e27a80b`):** `let TOKEN = params.get("token") || "";` — no TENANT_ID fallback. If there's no real token, `useMagicLink` is false and the request goes out without `?token=…` at all. The backend will return 401 with the proper "log in" message instead of a malformed-token 401.

### 8 — NOT FIXED: `/api-docs` and `/changelog` 404
- **File:** `packages/backend/src/core/bijou.py:6082,6091`
- **Evidence:**
  - `GET /api-docs` → 404 `<h1>API Documentation Not Found</h1>`
  - `GET /changelog` → 404 `<h1>Changelog Not Found</h1>`
- **Root cause:** Both routes look for `docs/api-docs.html` and `docs/CHANGELOG.md` in the repo root. Neither file exists (`docs/` has `ARCHITECTURE.md`, `QUICK_START.md`, etc., but not these two).
- **Recommendation:** Generate the content and commit it, or remove the two routes. Decision needed — not a code bug, just missing content.

### 9 — NOT FIXED: `body.dict()` is Pydantic v2-deprecated
- **File:** `packages/backend/src/saas/contacts_api.py:285`
- **Note:** In Pydantic 2 the method is `model_dump()`. The old `.dict()` still works (with a DeprecationWarning). Not a bug, just noise in logs.

### 10 — NOT FIXED: `core/dashboard_api.py` is dead code
- **File:** `packages/backend/src/core/dashboard_api.py`
- **Note:** This file defines a `router = APIRouter(prefix="/api/dashboard")` but it's never included by `bijou.py`'s `_include_routers()`. The real dashboard routes come from `dashboard_api_simple.py`. Dead code that could cause future confusion (or a route shadowing bug if someone re-enables it). Cleanup, not a bug.

## Commits made

```
e27a80b  fix(dashboard): don't fall back to TENANT_ID when no real ?token= param present
c76d772  fix(security): system-check.html — escape error.message in innerHTML
4754940  fix(security): outreach.html — escape resp.sent_to and e.message in innerHTML
190623a  fix(security): outreach.html — fix esc() to escape & and quotes
3060480  fix(security): kb-wizard.html — escape quotes in escHtml
cde204f  fix(security): admin.html — escape tenant data, send X-Admin-Key, no inline onclick
12cc45e  fix(security): help.html — escape quotes in escHtml; rebuild ticket submit without inline onclick
```

Plus one pre-existing fix that was already committed:

```
196f644  fix(backend): route SRP error log through stdlib logger
                       (also adds _check_admin_key dependency to /api/admin/*)
```

## Live vs. local state

The live server at `app.mybijou.xyz` is running pre-`196f644` code. As of this audit:

- `GET /api/admin/tenants` → still **200 OK**, returns 20+ KB of tenant PII. **Critical: deploy pending.**
- `GET /help` → 200, still serves the broken `escHtml` and the broken `submitTicket` inline-onclick. Deploy pending.
- `GET /admin` → 200, still serves the XSS-vulnerable admin page. Deploy pending.
- `GET /outreach`, `/system-check` → 200, still serve the broken `esc()` / unescaped `error.message`. Deploy pending.

The seven local commits listed above are ready to push. Once deployed, also:
1. Set `ADMIN_API_KEY` in the prod env (a long random string).
2. In the operator's browser, set `localStorage.admin_api_key = "<the same value>"` before opening `/admin`.

## Bugs that need a separate decision

1. **Add `ADMIN_API_KEY` to the prod env and a runbook for setting `localStorage.admin_api_key` on the operator's browser.** The code is locked; the deployment isn't.
2. **Decide on `/api-docs` and `/changelog`:** either generate the missing docs content (preferred — they used to exist) or remove the routes and the static links.
3. **Decide whether to clean up `core/dashboard_api.py`** (delete it) so a future operator doesn't re-enable it and cause route shadowing with `dashboard_api_simple.py`.
4. **Add an `esc()` helper to `dashboard.html`** — the dashboard's `React.createElement` calls are mostly safe, but there are still a few `<a href={...}>` and `<button title={...}>` sites where user-controlled strings (e.g. conversation customer names, knowledge doc titles) get interpolated as React children, which is fine, but a future maintainer could easily break that. A shared helper would prevent regression.

## What I did NOT change

- `packages/backend/static/dashboard.html` "Signal Gem" / `volume-2` / `volume-x` icons and `replyListenTimer` — those are pre-existing in-progress feature work that was in the working tree before I started. Not a bug, not in scope.
- `packages/backend/static/manifest.json`, `packages/landing/components/DemoChat.tsx`, `packages/landing/scripts/i18n_audit.py` — same: pre-existing uncommitted work, not in scope.
- Any new untracked files in `ops/` (logs, screenshots, helper scripts from a previous session).
