# Bijou Enterprise Dashboard — Bug Report

## CRITICAL CAVEAT — Limitations of this audit

**This is an HTTP/HTML-level audit, not a full browser walkthrough.** The `control-in-app-browser` skill (`browser` tool) is referenced as available but is **not actually wired up in this session** — the MCP manifest at `C:\Users\W3jde\.minimax\mcp\manifest.json` shows only `cu`, `matrix`, and `trash` as active. `playwright` is in `mcp.json` but not registered. So:

- ❌ No real browser, no JS console output, no actual button clicks, no visual screenshots, no on-screen bug observation
- ✅ I could: fetch every HTML page, parse its structure, hit every referenced `/api/*` endpoint with curl using the test JWT, inspect server log errors, and verify route existence in source
- The file `static/_test_bootstrap.html` **does not exist** (the task description references it, but it isn't on disk and the dev server returns 404 for `/static/_test_bootstrap.html`)

If the user wants real browser-based screenshots/console-capture, this task must be re-run in a session where the Playwright MCP is actually registered.

Test credentials: `test-20260805194641@gmail.com` / `TestPass1234` — login works, returns a valid Supabase JWT and tenant_id `52be731a-5e70-48d9-bc84-84c98163ea3b`.

---

## P0 — Broken pages (5 of 9 listed URLs return 404)

These URLs are in the task spec but **don't have FastAPI route handlers** in `src/core/bijou.py`. The HTML files exist in `static/` but are unreachable via the URLs the user listed.

| Page | URL tested | HTTP | Where it actually lives |
|---|---|---|---|
| Admin | `/admin` | **404** | `/static/admin.html` (10.7 KB) |
| Integrations | `/integrations` | **404** | `/static/integrations.html` (6.9 KB) |
| System Check | `/system-check` | **404** | `/static/system-check.html` (24.7 KB) |
| User Guide | `/user-guide` | **404** | `/static/user-guide.html` (92.7 KB) |
| Sales Presentation | `/sales-presentation` | **404** | `/static/sales-presentation.html` (53.8 KB) |

**Impact:** If any nav link, footer link, or marketing email points to `/admin`, `/integrations`, `/system-check`, `/user-guide`, or `/sales-presentation`, the user gets a 404. These need either FastAPI routes in `bijou.py` (like the existing `@app.get("/help", ...)`) or the HTML files need to be deleted. Verified routes that DO work: `/login`, `/signup`, `/onboarding` (same page as `/signup`, see below), `/dashboard`, `/outreach`, `/kb-wizard`, `/help`, `/pricing`, `/reset-password`, `/callback`, `/api-docs`, `/changelog`.

---

## P0 — Backend wired up with no real keys (LLM, bridge, Stripe)

The dev server log shows multiple "configured with dummy" conditions that mean several features **will never work in this dev environment** even when the UI is correct:

```
ERROR:src.api.help_chat:❌ help-chat Gemini error: Client error '400 Bad Request' for url
  'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=dummy-local-key'
ERROR:src.core.dashboard_api_simple:❌ BRIDGE_PASSWORD environment variable is not set
{"detail":"Payment service not configured (STRIPE_SECRET_KEY missing)"} → HTTP 503
```

- **/help page AI assistant**: any user message returns `"I'm having trouble thinking right now 😅 Please try again in a moment, or email support@mybijou.xyz"` because `GEMINI_API_KEY` is `dummy-local-key`.
- **/api/payment/portal** returns **503 Payment service not configured (STRIPE_SECRET_KEY missing)** — the dashboard's "Manage Subscription" button will toast an error.
- **WhatsApp bridge** is not running → all WhatsApp features (`/api/dashboard/whatsapp/qr`, `send-message`, `whatsapp/disconnect`, take-over) fail with `"Bridge not configured"` / `"All connection attempts failed"`.

---

## P1 — Dashboard calls API endpoints with wrong HTTP method (multiple 405s)

The dashboard's `api()` helper has `method: "GET"` as default. The dashboard's source references several routes that **only exist as PUT/DELETE/POST**, so the page fires a 405 on load. Verified against `src/core/dashboard_api_simple.py`:

| Dashboard calls | Actual route | What happens |
|---|---|---|
| `GET /api/settings/auto-reply` (line `await api("/api/settings/auto-reply", ...)` in `api()/.catch()` for settings load) | **PUT only** (`@router.put("/auto-reply")` in `src/saas/settings_api.py:400`) | 405 Method Not Allowed |
| `GET /api/dashboard/knowledge/{id}` (called inside the Knowledge module) | **PUT + DELETE only** (`@router.put/...delete("/knowledge/{doc_id}")` at lines 1444, 1490) | 405 Method Not Allowed |
| `POST /api/dashboard/settings/email` (in test-email handler) | **PUT only** (`@router.put("/settings/email")` at line 3442) | 405 Method Not Allowed |
| `POST /api/dashboard/settings/calendar` | **PUT only** (`@router.put("/settings/calendar")` at line 3062) | 405 Method Not Allowed |
| `POST /api/dashboard/settings/vertical` | **PUT only** (`@router.put("/settings/vertical")` at line 3520) | 405 Method Not Allowed |
| `POST /api/dashboard/whatsapp/disconnect` | **DELETE only** (`@router.delete("/whatsapp/disconnect")` at line 3369) | 405 Method Not Allowed |

**What the user sees in the browser:** "Failed to ..." toasts in the settings panel, vertical picker silently fails, knowledge document fetch fails on detail-view, disconnect button is broken.

The dashboard DOES call these correctly with `method: "PUT"` / `method: "DELETE"` in *some* places (vertical save, knowledge delete, whatsapp disconnect) — but the *initial-load* `api(...).catch(() => null)` calls use the default GET and 405 out.

---

## P1 — Dashboard's `api()` helper fails to send the JWT when the localStorage is empty (the default case in the URL bar)

The `api()` helper in `static/dashboard.html` reads `getAccessToken()` from `localStorage`. On **direct URL navigation** (typing `/dashboard?tenant_id=...&token=...` in the address bar, or first load after a fresh tab), there's no localStorage → no `Authorization` header sent → every request returns **400 "Missing tenant_id for dashboard access"**.

The user has to actually log in first to populate localStorage, then the token sticks. But:
- The redirect from `/api/auth/login` to `/dashboard` does set localStorage correctly, so the normal login flow works.
- However, any hard refresh of the dashboard, magic-link email link, or PWA re-open in a new tab *without* localStorage will silently 400 every API call. There is no fallback to a server-side session cookie.

---

## P1 — `/onboarding` and `/signup` serve the EXACT SAME page

Both URLs return identical 17,607-byte HTML, same title `Create Account — Bijou AI`, same form fields. They aren't different flows — they're the same page aliased to two routes. If the user expects onboarding (post-signup wizard) to be different from signup (account creation), they aren't.

---

## P2 — API contract mismatches (the dashboard sends wrong field names)

The dashboard's `fetch()`/`api()` calls use field names that don't match the server's Pydantic models. Each one returns a 422 with the missing-fields list (a good error, but the dashboard's catch swallows it and the user just sees "nothing happened"):

| Dashboard sends | Server expects | Source |
|---|---|---|
| `POST /api/contacts {name, phone, email, tags}` | `{jid}` (required) plus optional `phone, name, tag, source, status, notes, property_interest` | `src/saas/contacts_api.py:63-71` |
| `POST /api/call-booking/book {customer_name, customer_phone, customer_email, booking_date, start_time, ...}` | `{customer_jid, scheduled_time, ...}` | the server returned: `"missing: customer_jid, scheduled_time"` |
| `POST /api/dashboard/send-message {to, message, channel}` | `{customer_jid, message}` | curl returns `"missing: customer_jid"` |
| `POST /api/business/profile {business_name, industry}` | `{tenant_id}` (then other fields) | curl returns `"missing: tenant_id"` (the dashboard reads tenant from X-Tenant-ID header, not body) |
| `POST /api/setup/test-message {phone, message}` | works with `to` not `phone` (server-side field name) | 422 when `phone` used |
| `POST /api/dashboard/takeover {customer_jid}` | works when customer exists in tenant — returns 403 "Customer not found in your account" when not |

**What the user sees:** click "Add contact" in the Leads page → 422 silently swallowed → no row added. Click "Send test message" → no message sent. The fields in the UI need to be relabeled and the JS bodies need to match the server's Pydantic schema.

---

## P2 — `GET /api/dashboard/whatsapp/qr` returns HTTP 200 with an error in the body

```
GET /api/dashboard/whatsapp/qr
→ 200 OK
→ {"status":"error","message":"404: No WhatsApp device configured for this tenant. Please contact support."}
```

The endpoint advertises success (200) but the body is a failure. Dashboard code reads `r.status` and will treat it as "got a QR" but `r.message` is an error string, so the QR image won't render. The endpoint should return 4xx for a real error, or the client should read `body.status === "error"` and toast.

---

## P2 — Knowledge upload accepts <50 chars but UI doesn't warn

`POST /api/kb/import-text {title, text, source}` returns 400 "Please paste more listing details (at least 50 characters)." but the form has no client-side length hint. Users who paste 30 chars get a confusing server error.

---

## P2 — KB templates listing returns 404

`GET /api/kb-templates/` (with trailing slash) returns 404. The dashboard calls `GET /api/kb-templates/industries` (works, returns 200 with 2 industries), and the kb-wizard HTML also references `/api/kb-templates/...` for sub-verticals. The base listing route isn't implemented.

```
GET /api/kb-templates/ → 404 Not Found
GET /api/kb-templates/industries → 200 OK (works)
```

---

## P2 — `require_auth` defaults to strict mode → all un-authed requests 400

`.env` does NOT set `REQUIRE_DASHBOARD_TOKEN=false` and `DASHBOARD_MODE=strict` is the server default. The test JWT is valid (3 segments, ES256), and the server's `verify_session()` works correctly. But if a test user doesn't have a row in `tenant_users` linking their `user.id` to a `tenant_id`, the JWT-auth branch falls through and the request 400s. The test user happens to have this link, so it works here, but any new signup that fails to create the `tenant_users` row will be silently 400'd on every dashboard call.

---

## P3 — Duplicate FastAPI Operation ID warning

```
UserWarning: Duplicate Operation ID external_webhook_api_webhook_post
  for function external_webhook at .../src/core/bijou.py
```

Two routes declare the same `operation_id`. This is a warning, not a break, but it means the OpenAPI schema at `/api-docs` will be ambiguous.

---

## P3 — Dashboard's `useMagicLink` token-rotation has a bug

In `static/dashboard.html`, the `api()` helper has:
```js
const useMagicLink = TOKEN && !currentToken;
```
where `TOKEN` is read from URL params (`params.get("token")`), and `currentToken` is the localStorage JWT. The variable name `TOKEN` is misleading — it's actually the URL `token` param (a magic-link token), not the JWT. If a user opens `/dashboard?tenant_id=X&token=Y` (magic link) **after** they've already logged in (have a localStorage JWT), `currentToken` is truthy → `useMagicLink` is false → the URL token is silently ignored. The dashboard's JWT is used, which is correct, but the code intent is confusing and could break in edge cases.

---

## Pages reachable via dashboard sidebar (NAV)

Source from `static/dashboard.html` `const NAV = [...]`:

```
home, inbox, escalations, updates, analytics, knowledge, test, media, leads, calls,
outreach (→ /outreach), ai_setup (→ /kb-wizard), settings, help (→ /help)
```

These are all **state-based tabs** in the SPA — they don't have their own URLs. The user can't deep-link to `/dashboard/inbox` etc. If the user refreshes the browser on a non-`home` tab, it resets to home. The user said "go through every page" — these tabs all live inside the same 323 KB `dashboard.html` and use the same `api()` helper, so they share the same P1 issues (wrong methods, JWT-must-be-in-localStorage).

---

## Per-page summary (HTTP-level only — no rendered UI observation possible)

| Page | URL | HTTP | Notes |
|---|---|---|---|
| Login | `/login` | 200 | Renders 4 buttons, 1 form, 4 inputs, 2 anchors. Form posts to `/api/auth/login` (works). |
| Root | `/` | 200 | Same 20.5 KB content as `/login`. |
| Signup | `/signup` | 200 | Identical 17.6 KB to `/onboarding`. |
| Onboarding | `/onboarding` | 200 | **Same page as /signup** — alias only. |
| Dashboard | `/dashboard` | 200 | 323 KB SPA, 92 buttons, 44 inputs, 78 api/fetch calls. Loads with broken tabs unless localStorage has JWT (P1). |
| Outreach | `/outreach` | 200 | 55.8 KB, 20 buttons, 17 api calls. 4 outreach endpoints tested — all 200. |
| KB Wizard | `/kb-wizard` | 200 | 36.7 KB, 7 buttons, 7 api calls. `/api/kb-templates/` 404 (P2). |
| Help | `/help` | 200 | 183.9 KB, 21 buttons, 1 form. AI assistant hardcoded to dummy Gemini key (P0). |
| Pricing | `/pricing` | 200 | 13.0 KB, 4 buttons, 3 api calls. `/api/payment/portal` returns 503 (P0). |
| Admin | `/admin` | **404** | File exists at `/static/admin.html` but no route (P0). |
| Integrations | `/integrations` | **404** | File at `/static/integrations.html` (P0). |
| System Check | `/system-check` | **404** | File at `/static/system-check.html` (P0). |
| User Guide | `/user-guide` | **404** | File at `/static/user-guide.html` (P0). |
| Sales Presentation | `/sales-presentation` | **404** | File at `/static/sales-presentation.html` (P0). |
| _test_bootstrap | `/_test_bootstrap.html` | **404** | Doesn't exist anywhere (P0). |

---

## Tested endpoints summary (curl with test JWT)

```
GET  /api/dashboard/stats                            200  {active:0, total:0, ...}
GET  /api/dashboard/conversations                    200  []
GET  /api/dashboard/escalations                      200  []
GET  /api/dashboard/escalations?status=pending       200  []
GET  /api/dashboard/knowledge/list                   200  {success, documents: [2 items]}
GET  /api/dashboard/knowledge/{id}                   405  No GET route — only PUT/DELETE
DELETE /api/dashboard/knowledge/{id}                 200  works
PUT   /api/dashboard/knowledge/{id}                  200  works
POST  /api/dashboard/knowledge                       ?    not exercised
GET  /api/dashboard/analytics/timeseries?days=7      200  {labels:[7], messages:[0,0,0,0,0,0,0], ...}
GET  /api/dashboard/whatsapp/status                  200  {connected:false, error:"Bridge not configured"}
GET  /api/dashboard/whatsapp/qr                      200  {status:"error", message:"404: No WhatsApp device..."}  ← should be 4xx
DELETE /api/dashboard/whatsapp/disconnect            200  works
GET  /api/dashboard/settings/email                   200  {configured:false}
PUT  /api/dashboard/settings/email                   500  Pydantic validation: expects `smtp_pass` not `smtp_password`
POST /api/dashboard/settings/email                   405  No POST route
GET  /api/dashboard/settings/calendar                200  {configured:false}
PUT  /api/dashboard/settings/calendar                500  expects `cal_username` + `cal_api_key`
POST /api/dashboard/settings/calendar                405
GET  /api/dashboard/settings/vertical                200  {vertical_id:null}
PUT  /api/dashboard/settings/vertical                200  works
GET  /api/dashboard/settings/verticals               200  [4 verticals]
POST /api/dashboard/settings/vertical                405
GET  /api/dashboard/blacklist                        200  [1 item]
POST /api/dashboard/blacklist                        200  works (added 60199999999)
DELETE /api/dashboard/blacklist/{id}                 ?
GET  /api/contacts                                   200  {contacts:[], total:0}
POST /api/contacts                                   422  expects `jid` not `name/phone`
GET  /api/media                                      200  {media:[], total:0}
POST /api/media/upload                               422  expects file in body
GET  /api/settings/current                           200  full settings doc
GET  /api/settings/auto-reply                        405  No GET route (PUT only)
PUT  /api/settings/auto-reply                        200  works (test: auto_reply_enabled=true toggled on)
GET  /api/business/profile?tenant_id=...             200  {success, profile:null}
POST /api/business/profile                           422  expects tenant_id in body (dashboard puts in X-Tenant-ID)
GET  /api/call-booking/list                          200  {bookings:[]}
GET  /api/call-booking/availability/default          405  No GET (POST)
POST /api/call-booking/availability/default          200  creates 5 slots Mon-Fri 9-5
GET  /api/call-booking/availability/schedule         200  [7 weekdays]
GET  /api/call-booking/availability/settings         200  full config
POST /api/call-booking/book                          409  slot not available (validation works)
GET  /api/payment/portal                             405  No GET (POST)
POST /api/payment/portal                             503  STRIPE_SECRET_KEY missing
GET  /api/payment/tenant/usage?tenant_id=...         200  {plan:free, usage:0, limit:3000}
GET  /api/tenant/{id}/device/status                  200  {status:unknown, error:"All connection attempts failed"}
GET  /api/outreach/campaigns                         200  [1 draft campaign]
GET  /api/outreach/segments                          200  []
GET  /api/outreach/queue/status                      200  {total:0, pending:0}
GET  /api/outreach/status                            200  {outreach_enabled:false, sent_today:0, ...}
GET  /api/kb-templates/                              404  base listing missing
GET  /api/kb-templates/industries                    200  [2 industries]
POST /api/kb/import-text                             400  "min 50 characters"
POST /api/help-chat/message (no auth)                200  LLM returns dummy-key error fallback
POST /api/support/ticket                             422  expects `name` + `issue_type`
POST /api/dashboard/send-message                     500  bridge down (correct error path)
POST /api/dashboard/takeover                         403  customer not in tenant
POST /api/auth/login                                 200  works
POST /api/auth/logout                                200  works
POST /api/auth/refresh                               ?    not exercised
POST /api/auth/signup                                422  expects `phone` field
```

---

## What I could not test (and why)

- **Visual UI rendering, layout breaks, blank sections, missing images, JS console errors during interaction** — no real browser available. The Playwright MCP is in `mcp.json` but not registered in the runtime's `manifest.json`, so the `browser` tool is not exposed in this session. The task description said "The session already has Browser available" — that appears to be a stale assumption; only `cu`, `matrix`, and `trash` are active.
- **Screenshots** — no screenshot tool wired up. `bug-report-screenshots/` directory was created at the project root but is empty.
- **Click-through every button** — without a browser, I can only know that a button exists in the HTML and that its referenced API endpoint is reachable. I cannot verify that the click handler is correctly bound, that the loading state appears, that the toast is shown, that modals open, etc.
- **Multi-step flows** (e.g. open Settings → edit email → save → verify) require actual UI state changes which need a browser.
- **Console errors during page load** — cannot capture. The static HTML parses fine, the JS may have runtime errors only visible in DevTools.

To complete the task as the user originally specified ("go through every onboarding, click every menu pages in dashboard, every button, every feature, must be working"), this needs to be re-run in a session where the `browser` tool / Playwright MCP is actually active, OR a human does it manually with DevTools open and captures the console + network errors.

---

## Files / locations referenced

- Dev server entry: `C:\Users\W3jde\local-projects\w3j-bijou-ai-main\w3j-bijou-ai-main\w3j-bijou-enterprise\run_dev_server.py`
- Main FastAPI app + routes: `src/core/bijou.py` (line 5840+ for HTML routes, 495-619 for API router includes)
- Dashboard API (where most `/api/dashboard/*` live): `src/core/dashboard_api_simple.py`
- Settings API (where `/api/settings/*` live): `src/saas/settings_api.py`
- Contacts API: `src/saas/contacts_api.py`
- Dashboard HTML (the SPA, 323 KB): `static/dashboard.html`
- Static pages with no route handlers: `static/admin.html`, `static/integrations.html`, `static/system-check.html`, `static/user-guide.html`, `static/sales-presentation.html`
- Dev server log: `w3j-bijou-enterprise/.devserver.err.log`
