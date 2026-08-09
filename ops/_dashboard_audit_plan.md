# Bijou Dashboard Audit Plan

## Confirmed bugs (severity ordered)

### CRITICAL — public PII leak
- `GET /api/admin/tenants` returns full tenant list (id, business_name, phone, status) with **NO authentication**. Anyone hitting `app.mybijou.xyz/api/admin/tenants` gets the whole customer database.

### HIGH — help.html `escHtml` broken
- `escHtml()` only escapes `&<>\\n`. Used in two unsafe contexts:
  - `onclick="BijouChat.submitTicket('${escHtml(transcript)}')"` — JS syntax error if transcript contains `'` (any user message with an apostrophe). Ticket submit button breaks for any tenant who typed "I'm" or "don't" in chat.
  - `value="${escHtml(...)}"` for tenant name/email/msg — no `"` escape → potential XSS via tenant name (a tenant whose business name contains `"` can break out of the attribute).

### HIGH — admin.html renders tenant data with no escaping + inline onclick with business_name
- Line 319: `<td><strong>${tenant.business_name}</strong></td>` — direct unescaped insertion
- Line 320: `<td>${tenant.email}</td>` — direct unescaped insertion
- Line 334: `onclick="generateQR('${tenant.id}', '${tenant.business_name}')"` — XSS via business_name
- Line 353: `modalSubtitle.innerHTML = 'Tenant ID: <code>${tenantId}</code>'` — XSS if user types a value with HTML
- Line 382: `qrContainer.innerHTML = '<div class="error">❌ ${error.message}</div>'` — `error.message` from server may contain user-controlled text

### MEDIUM — kb-wizard.html `escHtml` is also broken
- Same problem; less surface area (FAQ preview is innerHTML only, `<` is escaped so script tags can't be injected, but the function still lies about its name).

### LOW — `/api-docs` and `/changelog` 404
- Routes exist but `docs/api-docs.html` and `docs/CHANGELOG.md` are missing. Not a code bug per se — content is missing.

## Fix plan (focused commits)
1. **fix(security): add X-Admin-Key gate to /api/admin/* endpoints** (admin_api.py)
2. **fix(security): admin.html — escape tenant data, no inline onclick with user input** (admin.html)
3. **fix(security): help.html — fix escHtml to escape quotes; rebuild ticket submit button without inline onclick** (help.html)
4. **fix(security): kb-wizard.html — fix escHtml to escape quotes** (kb-wizard.html)

## Skipped (lower priority or out of scope)
- Pydantic v2 `.dict()` deprecations (warning only, not a bug)
- Dead `dashboard_api.py` not mounted (cleanup, not a bug)
- `api()` helper magic-link edge case (no JWT + only `?tenant_id=` → sends fake `?token=<UUID>`)
- `/api-docs` and `/changelog` 404 (content missing, not code)
