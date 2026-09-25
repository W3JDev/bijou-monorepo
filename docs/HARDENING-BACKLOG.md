# Hardening backlog

What is left after the 2026-09-05/06 audit, ordered. Effort is calendar time for
one engineer who knows this codebase.

Detail and evidence: `docs/AUDIT-2026-09-06.md`. What was already fixed:
`docs/FIXLOG-2026-09-06.md`.

## Status at 2026-09-06 end of session

Done since the audit opened:

| | |
|---|---|
| Baseline schema | **DONE.** 154 tables / 1797 columns / 521 indexes extracted from the live project and verified by rebuilding an empty database. Was item #2. |
| Login poisoning the service-role client | **DONE.** Broke login entirely under service-role-only RLS. |
| Webhook authentication | **DONE.** Shared secret + GOWA HMAC. Still fail-open until an operator sets the variable — see #3b. |
| `/api/onboarding/v2/*` auth | **DONE.** Was the last open P0 in code. |
| Wrong bridge shipped | **DONE.** GOWA, not `packages/bridge`. The QR now works end to end. |
| Per-tenant LLM budget | **DONE.** One tenant could stop AI for all others. |
| Secret scanning | **DONE.** Tracked hook + gitleaks CI + 19-case self-test. |
| Onboarding routing after login | **DONE.** New tenants reach the QR step. |
| `/api/proactive/status` 500 | **DONE.** Attribute typo, not a missing dependency. |
| i18n gaps | **DONE.** ms/zh/ta were rendering raw keys on the pricing page. |
| Unit test suite | 183 failed → 127 failed, 557 → 673 passed. All remaining failures are integration/e2e, needing a live server. |

Still open and **only you can do**: rotate the Coolify token (#1), apply the
SECURITY DEFINER revoke (#3a), push the branch, unblock Actions billing (#5).

---

## Do now — before the Dokploy cutover

### 1. Rotate the Coolify API token and everything it could read — **1 hour, owner only**
A live token is in three tracked files and in pushed history, still matching
`.env`. It reads every service's environment variables, so treat
`SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`, `STRIPE_SECRET_KEY` and
`ADMIN_API_KEY` as compromised too. Revoke first, then rotate, then audit logs,
then scrub history. Ordered runbook:
`docs/SECURITY_ALERT_2026-09-06_coolify_token.md`.

Redacting the files (done) protects nothing on its own — any clone taken since
2026-08-29 still has the token.

### 2. ~~Commit a baseline schema migration~~ — **DONE (`743e778`)**
`packages/backend/migrations-py/0000_baseline.sql`, extracted from the live
project and verified by rebuilding an empty database: 154 tables, 1797 columns,
521 indexes — exact matches to production. The local stack now boots on it and
completes signup, email confirmation, login and onboarding routing.

Original description kept below for context.

<details><summary>was</summary>
79 tables queried, 13 created by any `.sql` in the repo. The production schema
exists only as live state in one Supabase project. Until this lands there is no
disaster recovery, no staging, no schema review, and no new environment.

```bash
supabase db dump --db-url "$SUPABASE_DB_URL" --schema public \
  -f packages/backend/migrations-py/0000_baseline.sql
```

Then verify it actually reconstructs: run it against the local stack and check
all 79 tables appear. This also unblocks every end-to-end flow below.
</details>

### 3a. Apply the SECURITY DEFINER revoke — **5 minutes, owner only**
14 functions in `public` are EXECUTE-able by `anon` — the public browser key —
and SECURITY DEFINER bypasses RLS. Confirmed against production: the table read
returns `[]` (RLS works) but the RPC returns data. `search_knowledge` returns
knowledge-base CONTENT cross-tenant; three others DELETE rows.

The migration is written, committed and safe (nothing calls them with anon):

```bash
psql "$SUPABASE_DB_URL" -f packages/backend/migrations-py/add_revoke_anon_security_definer.sql
```

I could not apply it — writing DDL to production is blocked by a permission
guard on my side, not by Supabase.

### 3b. Set `BIJOU_WEBHOOK_SECRET` on any running deployment — **5 minutes**
The webhook auth added this session is fail-open when that variable is unset,
so upgrading does not drop inbound WhatsApp mid-flight. Until it is set, those
endpoints are still open. `openssl rand -hex 32`, same value on backend and
bridge. Grep production logs for `UNAUTHENTICATED WEBHOOK` to find instances
still in that state.

### 3. Authenticate the unauthenticated write endpoints — **partly done (`2d4b732`)**

**Done — the two webhooks.** Shared secret (`BIJOU_WEBHOOK_SECRET`), constant-time
compare, sent by the bridge, required in both compose files. Verified end to end:
401 without a credential and with a wrong one, past the gate with the right one.

Two things an operator must still do:
- **Set `BIJOU_WEBHOOK_SECRET` on any existing deployment.** The check is
  fail-open when unset (and logs CRITICAL) so upgrading does not take inbound
  WhatsApp down mid-flight. Until it is set, those endpoints are still open.
  `openssl rand -hex 32`, same value on backend and bridge.
- Grep production logs for `UNAUTHENTICATED WEBHOOK` to find instances still in
  that state.

**Still open — `/api/onboarding/v2/*`** (`src/saas/onboarding_complete.py`).
`tenant_id` comes from the URL path, the module contains zero `Depends`, and
writes use the service-role client. Not fixed here for two reasons: the caller
is an end user mid-signup, so the bridge secret is the wrong credential; and the
flow cannot be exercised until #2 lands, so a fix could not be tested.

Design when you do it: `/signup` stays public (it creates the tenant), and every
`/{tenant_id}` route requires the `tenants.signup_token` the magic-link flow
already issues — compare it constant-time, the same shape as
`_verify_webhook_secret`. Do it **with** #2, not before.

### 4. ~~Add secret scanning~~ — **DONE (`ce52a02`)**
Tracked guard at `ops/githooks/` (was `.git/hooks/`, which git never tracks, so
it protected only the machine it was written on), gitleaks over full history in
CI, and a 19-case self-test pinning both known regressions. Install with
`./ops/githooks/install.sh`.

Two things still outstanding from it:
- The CI workflow has **never run** — GitHub Actions is billing-locked. Do not
  read it as passing.
- Everyone with a clone must run the installer once; a tracked hook is not an
  installed hook.

### 5. Make CI actually gate — **halfa day (blocked on billing)**
`pytest` never runs in CI; `ruff` and `mypy` end in `|| echo`. Only
`py_compile` and `node --check` can fail a build. GitHub Actions is billing-
locked, so this is blocked on that, but the workflow change can land now.

Land it with the baseline pinned at the real number so it cannot regress:

```
182 failed, 527 passed, 28 skipped, 15 errors
```

---

## Next sprint

### 6. Root-cause the 182 failing tests — **3–5 days**
Nobody knew about these because CI does not run pytest and the documented
command silently truncates. Cluster them and fix the cause, never the assertion.

The two dominant signatures, already diagnosed:

- **`400 Missing tenant_id for dashboard access`** (shared_context,
  outreach_consent, and others). `verify_session` is **correct** — it fails
  closed and `DASHBOARD_MODE` defaults to `strict`. These are **stale tests**
  that predate that default. Fix the tests' setup, do not touch the dependency.
- **`assert 401 == 400`** in `test_outreach_api` (19 tests). Auth now runs before
  validation, so the status changed. Decide which order is intended, then align
  the tests to it.

Largest clusters: `test_outreach_api` 19, `test_integration` 18,
`test_call_flow` 15, `test_call_functionality` 14, `test_dashboard_complete` 14,
`test_postman_collection` 12 (that one just wants a file at
`docs/bijou-api.postman_collection.json`), `test_api_endpoints` 12.

### 7. Fix the `pytest` capture crash — **halfa day**
Without `-s` the run dies with `ValueError: I/O operation on closed file` after
collecting 248 of 731. Something closes `sys.stdout`/`stderr` or a file
descriptor during teardown. Find it — a suite that looks green because it
truncated is worse than a red one.

### 8. Drop the unused ML stack from `requirements.txt` — **2 hours**
`torch`, `torchaudio`, `chatterbox-tts` are installed by `Dockerfile.backend`
and imported by nothing under `src/`. The stripped image is 1.36 GB. The
`sed`-based strip in `ops/dokploy/Dockerfile.backend.dokploy` is a workaround;
the real fix is to move them to an optional extra, or delete them if TTS is not
coming back.

### 9. Reconcile the four `requirements` files — **halfa day**
`requirements.txt`, `requirements-dev.txt`, `requirements.optimized.txt`, plus
the derived local/dokploy variants. `requirements-dev.txt` cannot even run the
app (no `google-genai`, `langfuse`, `PyPDF2`, `tiktoken`). Decide on one base
plus extras.

### 10. Verify RLS on tables whose migrations do not enable it — **1 day**
`add_tenant_integrations.sql` and `add_whatsapp_device_mapping.sql` contain no
`ENABLE ROW LEVEL SECURITY` and no `CREATE POLICY`. Whether the **live** tables
have RLS is unverified — this audit had no database access. Check first; adding
RLS blindly could lock the app out of its own tables.

### 11. Fix `/api/proactive/status` returning 500 — **2 hours**
The only 500 across 103 unauthenticated GET probes.

### 11b. Drop the git stash holding a service-role key — **10 minutes**
`refs/stash` → `b9000833` carries `ops/coolify/.envs-backup.json`, which
contains a `service_role` JWT. Never pushed and the file is gitignored, so this
is a local landmine rather than a leak — but `git push --all` or handing over
the repo directory would expose unrestricted read/write on all tenant data.

```bash
git stash list                    # identify the entry
git stash drop stash@{N}
git reflog expire --expire-unreachable=now --all && git gc --prune=now
```

### 11c. Purge real user emails from the repo — **fold into the P0-1 history rewrite**
46 distinct addresses in tracked docs/tests on `origin/main`, 8 of them consumer
mailboxes, alongside expired signup tokens (`DB_FIX_RESULTS.md` and siblings).
The tokens are dead; the personal data is the problem, for a product shipping
`docs/compliance/DATA_SUBJECT_RIGHTS.md`. A deletion request cannot be honoured
against git history. Do it in the same `filter-repo` pass as item #1 rather than
rewriting history twice.

### 12. Move the production-mutating scratch scripts out of the tree — **2 hours**
`ops/_fix_rls_v6.js` and nine siblings hold a live Supabase Management PAT in
plaintext and **drop RLS policies on the production database**. Untracked and
gitignored (verified), so not a repo leak — but a loaded gun in the working
directory. Rotate the PAT, move them to a secured runbook.

---

## Nice to have

### 13. Retire `@app.on_event("startup")` — **2 hours**
Deprecated in FastAPI, and it is why the app has 41 routes at import and 222
after startup — which surprises every new reader and breaks naive test setups.
Move to a `lifespan` context manager.

### 14. Split the landing bundle — **halfa day**
One 1,009 KB chunk (302 KB gzipped), no code splitting. Vite already warns.

### 15. Delete or fix the root `Dockerfile` — **1 hour**
`Dockerfile:36` has `COPY packages/backend/scripts /app/scripts 2>/dev/null || true`
— shell redirection is not valid COPY syntax. `Dockerfile.backend` documents and
fixes this; the root file still carries it. Nothing references it. Left alone
because deleting a file someone may be using is not a mechanical call.

### 16. Correct `/status` — **1 hour**
Reports `"database":"sqlite"`, `"ai_model":"gemini-1.5-flash"` and a hardcoded
`"environment":"production"`. The real stack is Supabase and the `ai://` gateway
aliases.

### 17. Clean `ops/` — **halfa day**
~82 untracked scratch files: `_probe_*.js`, `_linter_*.js`, `push*.out/.err`,
`fly-*.out/.err`, `ss*.out/.err`, screenshots. Also `.git.broken` and
`.git.broken2` at the repo root. The new `.dockerignore` keeps them out of
images; they still make the tree hard to read.

### 18. Reconcile the stale docs — **halfa day**
`CLAUDE.md` says 439 tests (731), and its `LOGIN_URL` bug-class section is out of
date — `auth_api.py` has had a correct `_public_base_url()` fallback since
2026-08-17. `AGENTS.md` references directories that do not exist. `README.md`
and `AGENTS.md` claim 5 locales; there are 4.

### 19. Verify Nango against the real API — **1 day**
`src/connectors/nango_*.py` is unit-tested with mocks only. Per `CLAUDE.md`
nobody has hit `POST /api/nango/session` against a running instance, and the
dashboard Connect UI is not wired up.

### 20. Load-test the Dokploy resource settings — **halfa day**
`WEB_CONCURRENCY=2` and `2G` replace the old `4` and `1G`. Reasoned from "each
worker imports the whole app and builds its own `BijouAI`", not measured.

---

## Leads not personally reproduced

The audit's finder agents produced **138 findings** (15 P0, 42 P1, 48 P2, 33 P3
by their own labelling). The adversarial panel did not complete — 399 of 428
agents failed on an org spend limit — so most were never independently checked.
Items 1–20 above are the ones I confirmed myself by running a command or reading
the exact code path.

The rest are leads, not facts, and the raw set is worth a second pass once the
items above are done. Themes that recurred and look worth chasing first:

- input validation on file-upload routes (`kb_import_api`, `knowledge_upload`,
  `media_api`) — size and type checks
- SSRF in routes that fetch a user-supplied URL (`knowledge_sync`, `kb_import`)
- `packages/landing/api/chat.js` importing `../backend/ai-router.cjs`, a path
  that reportedly does not exist
- `WaitlistStrip.tsx` reportedly posting `name:""` to `/api/leads`, which rejects
  it with 400 while the UI shows success
- unauthenticated `/api/data-request/access` reportedly returning the signed
  download token inline

Re-running the panel is `Workflow({scriptPath, resumeFromRunId})` — completed
agents replay from cache, so only the failed verifiers re-run.
