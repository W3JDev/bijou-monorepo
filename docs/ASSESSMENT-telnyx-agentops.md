# Assessment — `agentops-platform` (Telnyx telephony) vs. Bijou absorption

**Date:** 2026-09-06
**Assessor:** Claude (assessment only — no code changed in either repo)
**Question asked:** can Bijou absorb this to sell one omnichannel suite (WhatsApp
Business, verified Facebook, SMS, voice, MMS, video/audio meetings, mass
inbound+outbound campaigns) alongside a connector layer?

**Answer in one line:** absorb the *voice core* (~4–6 weeks), rebuild the
*platform* around it, and do **not** promise the full omnichannel suite — that is
a 3–4 month project, and the three channels the pitch leans on hardest
(WhatsApp, MMS, opt-out-safe mass campaigns) are precisely the three that do not
exist in this codebase.

---

## 0. First finding: the path you gave me is empty

`C:\Users\W3jde\local-projects\w3j-projects\agentops-platform` is an empty
directory skeleton — 9 directories, **0 files, 0 bytes**:

```
$ find . -mindepth 1 | sort
./.github  ./.github/workflows  ./backend  ./backend/scripts
./backend/telnyx_mcp  ./backend/webhooks  ./docs  ./frontend  ./ops
=== files only: 0 ===
```

The real project is one level down, at:

```
/mnt/c/Users/W3jde/local-projects/w3j-projects/telnyx/agentops-platform
```

265 tracked files, git remote `https://github.com/mnjbold/agentops-platform.git`,
HEAD `4bc4ead`. Everything below refers to that repo. **Before anyone acts on
this, confirm which of these two paths the owner thinks is canonical** — an
empty look-alike sitting one directory up is exactly how a build gets
accidentally deleted.

---

## 1. What is real vs. scaffolded

### Real, and better-engineered than expected

| Signal | Evidence |
|---|---|
| **Size** | ~36k LOC tracked: `webhooks/` 14,957 · `frontend/src/` 8,264 · `tests/` 3,534 · `scripts/` 2,203 · `telnyx_mcp/` 1,410 · `appx/` 1,026 · `connectors/` 760 |
| **Tests genuinely pass** | `169 passed, 10 warnings in 36.57s` — 19 test files, 0 failures. (For contrast, Bijou's own current baseline is 183 failed / 557 passed.) |
| **CI actually runs them** | `.github/workflows/ci.yml:61` → `python -m pytest tests/ -v --tb=short`, plus a `secrets-scan` job at `:107`. Bijou's own CI never runs pytest. |
| **Low stub density** | 25 TODO/NotImplementedError markers in *tracked* code, and 21 are the four honestly-labelled email-provider stubs (`email_postmark.py`, `email_resend.py`, `email_sendgrid.py`, `email_ses.py`) |
| **137 live API routes** | measured from `/openapi.json` on a booted instance |
| **Honest failure reporting** | `webhooks/server.py:405-414` records failed router imports and `/health` returns `ok:false` — built *because* a broken module silently deleted Phase D from production once |

The code comments are unusually candid (`connectors/daily.py:11-14` announces its
own stub mode "loud in the logs so the operator notices the gap"). This is not a
vibe-coded shell.

### Aspirational — README claims that do not survive contact

`README.md:16` advertises an **"SMS / MMS inbox — threaded conversations,
scheduled sends, mass broadcasts."** Measured against the running app:

- **MMS: 0 routes.** `send_sms()` (`telnyx_mcp/clients/telnyx_client.py:406-420`)
  accepts only `from_`, `to`, `text`, `messaging_profile_id`, `webhook_url` —
  there is no `media_urls` parameter. Outbound MMS cannot be sent. "MMS" appears
  elsewhere only as a *number capability badge* in the Numbers tab.
- **The inbox is a demo stub.** `frontend/src/app.js:178`:
  `'/messages': () => mountStubScreen(main, { title: 'Messages', sub: 'SMS & WhatsApp threads' })`
  — served from a hardcoded `DEMO` object in `frontend/src/screens/stub.js:15-40`
  containing fake contacts ("Sarah Chen", "Acme Corp"). Five routes are stubs:
  `/` (Overview), `/calls`, `/messages`, `/contacts`, `/settings`
  (`app.js:175-185`). The two the README headlines — Overview and the
  SMS/WhatsApp inbox — are both fake.
- **The advertised live demo has a dead backend:**
  `https://agentops.getbijou.xyz` → `HTTP 200`;
  `https://bk-jr-api.aixlabs.fun/api/state` → **`HTTP 530`** (Cloudflare: origin
  unreachable). The demo frontend cannot load data.

### The half-built seam — and it is exactly where you want to build

`webhooks/server.py:453-461` imports three routers inside a `try/except`:

```python
try:
    from webhooks.whatsapp_api import router as whatsapp_router
    from webhooks.suppression_api import router as suppression_router
    from webhooks.sms_scheduler import router as sms_scheduler_router
    ...
except Exception as _exc:
    _record_mount_failure("phase_c_outbound", _exc)
```

**None of those three modules exist** — not tracked, not on disk. Boot evidence:

```
Router group 'phase_c_outbound' NOT mounted: No module named 'webhooks.whatsapp_api'

$ GET /health
{"ok": false, "failed_router_groups":
  {"phase_c_outbound": "ModuleNotFoundError: No module named 'webhooks.whatsapp_api'"}}
```

Route census on the running app confirms the hole:

```
whatsapp     0  []
suppress     0  []
mms          0  []
video        0  []
```

The **SQL tables and storage methods were written** — `storage.py:487`
`whatsapp_templates`, `:501` `whatsapp_messages`, `:517` `suppression_list`, and
`storage.py:2563-2577` `upsert_whatsapp_template()`. A source comment at
`storage.py:448` explains why: *"The other Phase C worker owns #22/23 (WhatsApp +
SMS blast)."* An agent worker was interrupted; the persistence layer landed and
the HTTP layer never did.

This is a **half-finished feature, not a missing one** — which is good news for
effort (the schema is designed) and bad news for trust (the repo has been
reporting `/health: ok=false` in this state since at least the last commit).

---

## 2. Telnyx capabilities genuinely wired

Derived by enumerating every SDK resource touched in
`telnyx_mcp/clients/telnyx_client.py` (line numbers are exact):

### Wired and real

| Capability | Where |
|---|---|
| **Numbers** — search, order, list, retrieve, update | `:145` `available_phone_numbers.list` · `:150` `number_orders.create` · `:156-178` `phone_numbers.*` |
| **Call Control** — dial, answer, transfer, hangup, reject | `:254` `calls.dial` · `:282-292` `calls.actions.{transfer,hangup,answer,reject}` |
| **Telnyx AI Assistants** — full CRUD + attach/detach to a live call | `:315-390` `ai.assistants.*` · `:308/:311` `calls.actions.{start,stop}_ai_assistant` |
| **Call Control Apps / Outbound Voice Profiles** | `:183-209`, `:214-224` |
| **SMS (text only)** + messaging profiles | `:420` `messages.create` · `:394-403` `messaging_profiles.*` |
| **Recordings** | `:424` `recordings.list`; recording started at `workflow_engine.py:406` `calls.actions.record_start` |
| **Voice clones / voice designs** | `:429`, `:432` |
| **TTS / STT** | `:474-476` `audio.speech.create` · `:521-523` `audio.transcriptions.create` |

Plus a real **workflow engine** (`webhooks/workflow_engine.py`, 770 LOC) with
four shipped JSON templates (`basic-ivr`, `ai-receptionist`, `after-hours`,
`queue`), and a genuine **contact-centre layer**: agent presence, skills-based
routing, call queue, and supervisor monitor/whisper/barge
(`webhooks/{presence,skills,queue,supervisor}.py`).

### Not wired — verified absent

| Capability | Status |
|---|---|
| **MMS (outbound)** | absent — no `media_urls` anywhere in the send path |
| **Verify / 2FA** | **zero hits** for `verify_profile`, `verifications` |
| **Video** | **not Telnyx.** Meetings use **Daily.co** — `connectors/daily.py`, `webhooks/meetings.py:27` `from connectors.daily import get_daily_client`. And it is *stub-first*: `daily.py:11-14` returns synthetic rooms whenever `DAILY_API_KEY` is unset |
| **Wireless / SIM** | **zero hits** |
| **10DLC / brand / campaign registration** | **zero hits** for `10DLC`, `brand_id`, `campaign_id_tcr`. Nothing registers A2P traffic |
| **Fax, porting, TeXML** | referenced in probe scripts only, not in the product path |

**The headline gap for your pitch:** of the seven channels in the omnichannel
story, **voice is production-shaped; SMS is text-only; meetings are a thin
Daily.co wrapper in stub mode; and WhatsApp, MMS, verified Facebook, and
campaign registration do not exist at all.**

---

## 3. Domain coupling — the absorb-vs-rebuild question

**This is the strongest finding in the assessment, and it contradicts the
premise of the request.**

A grep for recruiter/ATS vocabulary across all tracked `.py`/`.js`
(`recruit|candidate|applicant|ATS|resume|job_post|interview|hiring|vacancy`)
returns **24 hits, and every single one is a false positive**:

- `campaigns_extra.py:125` — `for candidate in (".mp3", ".wav")` (a loop variable)
- `dashboard_api.py:1610` — `@router.post("/campaigns/{campaign_id}/resume")` (the verb)
- `presence.py:252` — `recv_task` (substring match)
- `_probe_voices.py:15` — `candidates = [...]` (a list of TTS voices)

**There is no recruiter domain logic in this repository.** No candidate model, no
job model, no ATS integration, no pipeline stages. The telephony layer is not
"cleanly separable" — it is *already separate*. It is a generic multi-tenant
CPaaS/contact-centre platform.

The only recruiter trace I found is environmental, not code: booting the app
emitted `WARNING: Env file not found: D:\WORK\projects\recreuiter-telephony\.env.global`
— a stale absolute path baked into the local `.venv`, absent from every tracked
file. The "pointed at a recruiter dashboard" framing appears to describe a
*sibling deployment sharing an env file*, not this codebase.

**Consequence:** domain coupling is a non-issue. It is not the thing that decides
absorb-vs-rebuild. The thing that decides it is architecture (§4).

---

## 4. Architectural assumptions that clash with Bijou

Runtime is the good news; everything below it is the bad news.

| Dimension | agentops-platform | Bijou | Verdict |
|---|---|---|---|
| **Language / framework** | FastAPI, Python 3.12 (`requirements.txt`: `fastapi==0.141.1`) | FastAPI, Python 3.12 | ✅ **Compatible** — the one genuinely free win |
| **Database** | **SQLite, single file**, one `sqlite3` connection with `check_same_thread=False` and a `threading.Lock` serialising writes (`storage.py:24-31`). Uses **FTS5** for recordings search (`storage.py:36`) | Supabase / Postgres, multi-tenant, **RLS hardened to service-role-only** by `ops/_fix_rls_v6.js` | ❌ **Hard incompatibility** |
| **Second, half-present DB** | An **Appwrite** path also exists — `backend/appx/` (1,026 LOC), `appwrite==14.1.0`, repos for calls/campaigns/contacts/messages. Tests emit *"deprecated since 1.8.0, use tablesDB.create_row"* | none | ❌ Dead weight; do not port |
| **Auth** | Own JWT + bcrypt. **Tenant encoded in the email local-part** — `admin@default.local`, where the string between `@` and `.local` *is* the tenant id (`auth_api.py:48-56`). `tid` claim must match `X-Api-Key`/`X-Tenant-Id` | Supabase GoTrue, **email confirmation ON**, `tenants` + `tenant_users` tables | ❌ **Direct conflict** |
| **Tenancy** | `X-Tenant-Id` header + explicit `tenant_id` argument on every store method | RLS + service-role key | ❌ Different enforcement point |
| **Env contract** | **10 vars documented** in `.env.example`; **44 read in code** — undocumented: `APPWRITE_*`, `DAILY_API_KEY`, `STRIPE_*`, `TENANT_SECRET_KEY_FILE`, `BACKEND_DEV_PASSWORD`, `W3J_*`, `EMAIL_PROVIDER`, … | documented, with known aliases | ⚠️ 4.4× drift — a real onboarding tax |
| **Frontend** | Vanilla JS + Vite, **mid-migration** from a monolithic PWA (`frontend/index.html` + `campaigns.js` 1,178 LOC still the legacy source of truth per `stub.js:4-5`) | hand-written static HTML in `static/`, `dashboard.html` ~7.1k lines | ⚠️ Two migrations in flight; neither is React |
| **Deploy** | Coolify, 2 containers (FastAPI + nginx), **no DB server** (`README.md:27-29`) | Coolify primary | ✅ Compatible shape |

**The decisive number:** `webhooks/storage.py` is **3,904 lines** — the single
largest file in the repo — and it is 100% SQLite. Every router imports
`get_store()`. Porting persistence to Supabase is not a corner of the work; it
*is* the work, and it cannot be deferred, because SQLite-on-a-single-file
directly contradicts Bijou's multi-tenant Postgres + RLS model and will not
survive Coolify container restarts or horizontal scaling.

---

## 5. Secrets — clean, and better than Bijou's own record

Bijou has been bitten twice by committed credentials. This repo has **not**.

**Tracked files:** a pattern scan for `KEY…`, `sk-…`, `eyJ…`, `AKIA…`,
`sk_live_…`, `whsec_…`, `xox[baprs]-…`, `ghp_…`, `AC[32-hex]` across all 265
tracked files returned **zero hits**.

**Full history:** the same scan across **all 717 objects in all revisions**
returned zero hits. Method validated with a control (`git grep -lI 'TelnyxClient'
$(git rev-list --all)` correctly returned matches), so the empty result is a real
negative, not a broken command.

**`.gitignore` is unusually disciplined** — it anticipates the leading-dot trap
explicitly:

```
# .runtime-secrets/ holds live Telnyx + Fernet + webhook-HMAC values.
.runtime-secrets/
**/settings.json          # Appwrite credentials (real secret-bearing JSON)
**/sip_credentials.json   # SIP credentials
.tenant_master_key
.dev-password
```

**One real exposure, untracked and local-only:**

- `.runtime-secrets/coolify-secrets.txt` (446 bytes, untracked — `git ls-files`
  returns 0) holds live production values. Masked:
  ```
  # Generated 2026-0********:08:45 — Coolify production env
  WEBHOO********      (WEBHOOK_* HMAC secret)
  TENANT********      (TENANT_SECRET_* master key — Fernet root)
  TELNYX********      (TELNYX_* API key)
  ```
  **Not committed, correctly gitignored, but sitting in plaintext on disk** —
  the same posture CLAUDE.md already flags for the three telnyx/ SECURITY.md
  projects. Owner action: rotate and move to a secret manager. Note the
  `TENANT_SECRET_*` value is the **Fernet master key that decrypts every
  tenant's stored secrets** — it is the highest-value item in the file.

**One live-config weakness worth flagging:** the app boots with webhook signing
off and says so loudly —
`Webhook HMAC signing: DISABLED — WEBHOOK_HMAC_SECRET is not set. Anyone who can
reach /webhooks/telnyx can post events.` Correct behaviour (fail loud, not
silent), but it means a misconfigured deploy accepts forged Telnyx events.

**Verdict: secret hygiene here is better than Bijou's.** If anything, Bijou
should borrow this `.gitignore` and the CI `secrets-scan` job.

---

## 6. The two WhatsApp paths — complementary as product tiers, conflicting per number

This needs to be said plainly because it is a **product** decision that a merge
plan cannot paper over.

| | **GOWA bridge (Bijou today)** | **Telnyx WhatsApp (this repo)** |
|---|---|---|
| Mechanism | WhatsApp **Web**, QR-scanned, `whatsmeow`, one Go container per tenant | **Meta Business Cloud API** via Telnyx — `connectors/whatsapp.py:27` `https://api.telnyx.com/v2/whatsapp` |
| Onboarding | minutes — scan a QR | weeks — Meta Business Verification (SSM docs for MY), display-name approval, per-template approval |
| Verified badge | ❌ never | ✅ green badge available |
| Proactive/bulk messaging | practically limited; ban risk | supported, template-gated, per-message priced |
| ToS posture | unofficial; number-ban risk | official |
| Cost | free | per-conversation |

**They complement as tiers** — QR bridge for self-serve SME trials, WABA for
verified/high-volume clients. That is a genuinely good product ladder and a real
argument for absorption.

**They conflict per phone number.** A number registered to the WhatsApp Business
Cloud API cannot simultaneously run a WhatsApp Web session. Migrating a tenant
from GOWA to WABA is a one-way move that kills the existing bridge session and
its chat history. So this is a **per-tenant either/or requiring a channel-routing
abstraction** — which does not exist in either codebase today.

Also note what Telnyx WhatsApp here actually is: **69 lines**
(`connectors/whatsapp.py`), text-only, no template support, no media, and the
router that would expose it (`whatsapp_api.py`) **does not exist**. The template
table exists in SQL; nothing serves it. Treat this as a design sketch, not an
integration.

**On Composio:** zero references in any tracked `.py`/`.js` — it appears only in
two aspirational docs (`docs/w3j-bijou/ARCHITECTURE.md`, `SALES.md`). So there is
**no conflict** with Bijou's 2026-08-22 rejection of Composio, and nothing to
unwind. Bijou's Nango decision stands untouched. **Do not let the "alongside the
Composio connector layer" framing in the request re-open that** — this repo gives
you no reason to.

**On "verified Facebook":** no Meta Graph API, no Messenger, no Facebook code of
any kind exists in this repo. That channel is 100% greenfield.

---

## 7. RECOMMENDATION

### **Borrow-and-absorb the voice core. Rebuild the platform. Decline the full omnichannel suite as scoped.**

Concretely: take `telnyx_mcp/`, `agent_sdk/`, `compliance/`, and
`workflow_engine.py` into `packages/voice/`. Reimplement persistence against
Supabase. Leave `storage.py`, `auth_api.py`, `tenancy.py`, `appx/`, and the
entire frontend behind.

**Why this and not full absorption:** the valuable, portable, hard-to-rebuild
asset is the Telnyx integration knowledge — the SDK wrapper, the call-control
state machine, the workflow engine, the contact-centre primitives (presence,
queue, skills routing, supervisor barge). That is genuinely months of work and it
is tested. But it sits on a SQLite store, a bespoke JWT auth model, and a
half-dead Appwrite path, none of which can come along. You cannot merge the
platform; you can only harvest the layer that knows how to talk to Telnyx.

**Why not rebuild from scratch:** `telnyx_mcp/clients/telnyx_client.py` encodes
real, non-obvious Telnyx SDK v4 knowledge (the `.data` response-wrapper unwrap at
`:50-53`, the `audio.speech` vs `ai.audio.speech` mount drift at `:470-476`, org-key
vs scoped-JWT capability differences at `utils/env.py:1-13`). Rediscovering that
costs weeks and produces nothing better.

**Why not leave alone:** voice is already on Bijou's roadmap (issues #27/#28), the
A2A shared-context seam was built for exactly this (`shared_context` table,
`docs/superpowers/specs/2026-08-23-a2a-seam-protocol.md`), and the runtime match
(FastAPI/Python 3.12) is a real, rare advantage.

### The case against my own recommendation

Argue with me on these three points, because they are the strongest:

1. **The omnichannel pitch mostly does not exist here, so "absorb" may be
   overselling what you get.** WhatsApp router: missing. MMS: missing. Verified
   Facebook: missing. 10DLC: missing. Suppression/opt-out: missing. Video: a
   third-party (Daily.co) wrapper running in stub mode. If the business goal is
   the *suite*, this repo contributes roughly **one and a half channels** (voice,
   plus text-only SMS). A reasonable person could say: take the 558-line
   `telnyx_client.py` as a reference document, rebuild natively on Supabase, and
   skip the merge entirely. **If Bijou's near-term revenue does not depend on
   voice, that is the better call.**

2. **Bijou cannot currently deploy.** CLAUDE.md is explicit: GitHub Actions is
   billing-locked, Fly is billing-locked, Coolify is manual-only, and 29 commits
   sit unpushed. Bijou's own suite is at 183 failed / 557 passed. **Absorbing a
   second platform into a repo that cannot ship and whose tests are a third red
   is how you get two broken things instead of one.** Fix the deploy path and the
   baseline first; this work has no deadline that outranks that.

3. **The compliance module is built for the wrong country** (see §8). It may be a
   liability rather than an asset in the Malaysian market.

---

## 8. If you absorb: order, landing sites, effort

Effort is engineering time for one focused developer, and **excludes external
approval latency**, which is often the real critical path.

| # | Step | Lands at | Effort |
|---|---|---|---|
| 1 | Port `telnyx_mcp/` (client + `utils/env.py`) as-is; it has no store dependency | `packages/voice/telnyx/` | **3–5 days** |
| 2 | Reimplement call/campaign persistence against Supabase — replaces `storage.py` for voice tables only. **The dominant cost.** | `packages/backend/migrations-py/add_voice_*.sql` | **2–3 weeks** |
| 3 | Port the webhook receiver + `handlers/`, reusing Bijou's `verify_session`/tenant resolution instead of `tenancy.py` | `packages/backend/src/voice/` | **1–2 weeks** |
| 4 | Port `workflow_engine.py` + the 4 JSON templates | `packages/voice/workflows/` | **1 week** |
| 5 | Wire voice into the A2A `shared_context` seam (spec already exists) | `src/core/shared_context_api.py` | **3–5 days** |
| 6 | Contact-centre layer (presence, queue, skills, supervisor) — optional, only if selling to call centres | `src/voice/contact_center/` | **2 weeks** |
| 7 | **Build** SMS suppression / STOP-opt-out — does not exist, and is a legal prerequisite for step 8 | `src/voice/suppression.py` | **1–2 weeks** |
| 8 | **Build** mass campaign send with rate limiting + opt-out enforcement | `src/voice/campaigns.py` | **2 weeks** |
| 9 | **Build** WhatsApp channel abstraction (GOWA ↔ WABA routing, per-tenant) | `packages/bridge/` + `src/channels/` | **2–3 weeks** |
| 10 | **Build** MMS (add `media_urls`), meetings (Daily key + de-stub) | various | **1 week** |
| 11 | **Build** 10DLC/TCR registration — only if selling into the US | new | **3–4 weeks + weeks of external approval** |

**Voice core only (1–5): ~4–6 weeks.** This is the defensible scope.
**Full omnichannel suite (1–11): 3–4 months**, plus Meta and TCR approval
latency you do not control.

Do **not** port: `webhooks/storage.py`, `webhooks/auth_api.py`,
`webhooks/tenancy.py`, `backend/appx/**` (Appwrite), `frontend/**`,
`backend/scripts/_probe*.py`.

**Worth stealing immediately, independent of any merge:** the `.gitignore`
(§5), the CI `secrets-scan` job, and the `/health` failed-router-group pattern
(`server.py:405-414`) — Bijou has the exact silent-router-drop failure mode that
pattern was invented to catch.

---

## 9. Risks

### Regulatory

- **The compliance module is US-shaped, and Bijou sells to Malaysian SMEs.**
  `compliance/time_window.py:1-6` implements **TCPA** 8am–9pm using a
  *"area code → timezone for the top ~100 US area codes"* table.
  `compliance/dnc.py:44-51` ships a **seeded demo deny-list** of fake toll-free
  numbers, with real DNC wiring described as *"a one-line swap"* that has not
  been made. For a Malaysian customer base this is not merely unhelpful — it is
  **actively misleading**, because the dashboard will report "compliance checks
  passed" against rules that do not govern the jurisdiction. Either rewrite for
  MCMC/PDPA or remove it. Do not ship it as-is.

- **Call recording consent under Malaysian PDPA 2010 — a live gap.** Recording is
  started at `workflow_engine.py:406` (`calls.actions.record_start`). A grep for
  `consent` across every tracked `.py` returns **zero hits**. The project's own
  docs know this: `docs/w3j-bijou/API.md:290` carries an **unchecked** box —
  `- [ ] Recording consent announcement in every system prompt`. PDPA requires
  notice and consent for processing personal data; recording a call without a
  disclosure at call start is a compliance defect that ships by default. **Fix
  before any pilot call**, and note Bijou's own `docs/compliance/` framework is
  where the disclosure text should live.

- **10DLC (US A2P):** entirely absent. Unregistered A2P traffic is filtered or
  blocked by US carriers, and per-message fees apply. Relevant **only** if
  selling into the US — Malaysian SMEs texting Malaysian numbers do not need it.
  Malaysia has its own requirement: **MCMC sender-ID registration** for A2P SMS,
  also absent.

- **WhatsApp Business verification:** Meta Business Verification (SSM
  registration documents for a Malaysian entity), display-name approval, and
  per-template approval (typically 24–48h each) with quality-rating tiers that
  throttle sending. This is **weeks of calendar time you do not control**, and it
  gates the entire "verified WhatsApp" selling point.

### Technical / delivery

- **SQLite → Supabase is the whole job.** 3,904 lines of store code with every
  router depending on `get_store()`. Under-scoping this is the single most likely
  way the project overruns.
- **Two auth models** — bespoke JWT with tenant-in-email vs. Supabase GoTrue. If
  both survive the merge you will reproduce the *exact* session-loss/wrong-domain
  bug class CLAUDE.md documents twice already. Pick one (GoTrue) on day one.
- **Env drift** — 44 vars read, 10 documented. Expect misconfigured deploys until
  reconciled.
- **The repo is currently unhealthy in production**: `/health` returns
  `ok:false`, and the advertised API returns **530**. Do not treat the live demo
  as evidence of anything.
- **A second frontend migration** (monolithic PWA → Vite) is in flight and
  unfinished, in a project that already has an unfinished dashboard. Do not
  inherit it.

---

## 10. What I did not verify

Stated plainly, so nobody over-trusts this document:

- **No live Telnyx API call was made.** No valid Telnyx credential was used; I
  did not place a call, send an SMS, or exercise an AI assistant. Every Telnyx
  capability claim above is derived from **code inspection plus the local test
  suite**, which mocks the Telnyx client. "Wired" here means *the code path
  exists and is unit-tested*, **not** *observed working against Telnyx*.
- **I did not load the frontend in a browser.** `agentops.getbijou.xyz` returned
  HTTP 200 at the network layer only; I did not render it, read its console, or
  confirm what it displays. Given its API returns 530, I expect it renders an
  empty or erroring shell, but **I did not confirm that**.
- I **did** check whether the three missing routers survive in a sibling project
  (the commit log's "rescued from interrupted workers", `a00e9e8`, made this
  plausible). A filename search across **all** of `w3j-projects/` returned
  nothing:
  ```
  $ find . -maxdepth 6 \( -name 'whatsapp_api.py' -o -name 'suppression_api.py' \
        -o -name 'sms_scheduler.py' \) -not -path '*/.venv/*' -not -path '*/node_modules/*'
  (no results)
  ```
  They are **gone, not misplaced** — steps 7–9 in §8 are true greenfield work.
  I did not otherwise audit those sibling projects
  (`Connector-Hub`, `W3J-BIJOU PROJECT`, `Call Centre/contact-center-v0.2`,
  `agentops`) for reusable code.
- **I did not run the Bijou test suite** or change any file in the Bijou repo
  other than creating this document.
