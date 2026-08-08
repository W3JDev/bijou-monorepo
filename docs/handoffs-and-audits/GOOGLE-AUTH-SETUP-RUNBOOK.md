# Google Sign-In + Workspace — Setup Runbook

**Created:** 2026-07-23 · **Repo:** `w3j-bijou-enterprise` (product), Supabase project `lrwzlujomukzjykafmic`

> **The "Sign in with Google" code is complete and deployed.** The only blockers are
> console configuration (Supabase Auth + Google Cloud) and a secret rotation. This
> runbook is those steps. Code evidence: `static/login.html:408-496`,
> `static/auth-callback.html`, `src/saas/auth_api.py:271-304` (`/api/auth/oauth-session`),
> routers registered at `src/core/bijou.py:560` and `:643`.

---

## Part A — Rotate the exposed secrets (DO FIRST; console-only)

Two live secrets were sitting in plaintext docs/scripts (now redacted, 2026-07-23).
Redaction does **not** make them safe — rotate to invalidate the old values.

1. **Supabase `service_role` key**
   - Dashboard → project `lrwzlujomukzjykafmic` → **Settings → API → rotate the `service_role` key**.
   - ⚠️ If you rotate the underlying JWT secret, the **anon** key changes too — you must then
     update the anon key in `static/login.html:478` and `static/auth-callback.html:58`.
   - Update the new service key everywhere it's set: Fly.io secrets (`SUPABASE_SERVICE_KEY` /
     `SUPABASE_KEY`), Vercel env, and any local `.env`.

2. **Google OAuth `client_secret`** (`GOCSPX-…`, was in `PHASE_1_COMPLETION_REPORT.md`)
   - Google Cloud Console → **APIs & Services → Credentials →** the OAuth client → **Reset secret**.
   - Update wherever consumed (`GOOGLE_CLIENT_SECRET` in Fly secrets / `src/saas/google_oauth.py` config).

---

## Part B — Enable "Sign in with Google" (the actual sign-in blocker)

1. **Supabase → Authentication → Providers → Google → Enable.** Paste the OAuth **Client ID**
   and the **rotated Client Secret**.
2. **Google Cloud Console → the OAuth client → Authorized redirect URIs**, add exactly:
   ```
   https://lrwzlujomukzjykafmic.supabase.co/auth/v1/callback
   ```
   and add your app origins to **Authorized JavaScript origins** (e.g.
   `https://app.mybijou.xyz`, `https://bijou-production.fly.dev`).
   *(Current credentials only allow `http://localhost:3000/oauth2callback` — that is the blocker.)*
3. **OAuth consent screen → Publish** (or add test users) — otherwise external users are blocked.
4. **Verify the DB** has the tables the flow needs (else login succeeds then 404s at `oauth-session`):
   ```sql
   select to_regclass('public.tenant_users'),
          to_regclass('public.onboarding_sessions'),
          (select count(*) from information_schema.columns
           where table_name='tenants' and column_name='google_access_token');
   ```
   If `tenant_users` is null, apply migration `supabase/migrations/005_google_oauth_onboarding.sql`
   and the `tenant_users` migration.
5. **Test:** open `/login` → "Sign in with Google" → should land on `/dashboard`.

### Known limitation (not a bug — a gap to decide on)
`oauth-session` (`auth_api.py:285-290`) only links a Google user **if their email already owns a
tenant**. A brand-new Google user with no tenant gets `404 "No tenant is registered to this
Google account's email."` Signup is currently email/password only. If you want Google *signup*
(not just login), the signup flow needs a Google path that creates the tenant. Decide before launch.

---

## Part C — Google Workspace / Sheets (SEPARATE from sign-in — NOT yet done)

Enabling Google login does **not** unblock this. It's a different flow (`google_oauth_router`,
`src/saas/google_oauth.py`) using its own GCP credential. Open blockers per
`PHASE_1_COMPLETION_REPORT.md`:

- [ ] **Redirect URI is localhost-only** → add a production redirect, or switch to a **service
      account** (the report's Phase-2 recommendation, lines 388-403).
- [ ] **`customer_phone` shows `DEVICE_XXX`** — webhook handler in `src/core/bijou.py` (~line 3640)
      doesn't extract the phone from the `from` field (report lines 309-328). Blocks correct Sheets export.
- [ ] **Missing Sheets/Drive scopes** on the credential (report lines 62-69):
      `spreadsheets`, `drive.file`.
- [ ] Service-account JSON must live in Fly.io secrets, never committed.

**Status: NOT STARTED.** This is a multi-file change in a large FastAPI codebase — recommend a
fresh session (see summary).
