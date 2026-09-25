# Blueprint — Bijou "Big Features" (grounded audit + build plan)

_Authored 2026-09-21. Based on a read-only audit of `packages/backend` (3 parallel
mappers). Every "state" claim below cites `file:line`. This is the source of truth
for the build; it is deliberately biased toward **enable / fix / wire / verify**
over greenfield, because the audit shows most of this already exists._

---

## TL;DR — what's actually left

| # | Feature | Real state (evidenced) | Work class | Effort |
|---|---------|------------------------|------------|--------|
| 1 | Dashboard → WhatsApp reply | **Built end-to-end** (`dashboard_api_simple.py:1005`, `dashboard.html:1121`) | **Verify only** | XS |
| 2 | CRM (contacts) | **Built + live** (`contacts_api.py:86-312`, `dashboard.html:3068`, auto-populate `bijou.py:4487`) | Verify + optional enrich | S |
| 3 | Stop-texting a contact | Hard-block built (`blocked_numbers`, `bijou.py:2791`); no soft "AI-off" | Small add | S |
| 4 | Scheduled messages | API exists (`/api/proactive/schedule`) but **not durable** (schema bug) | Fix + UI | M |
| 5 | Proactive / automations | **Running** (2 asyncio loops, `bijou.py:1105-1121`); 2 dormant/broken bits | Fix + wire | M |
| 6 | Long memory | Table + `embedding vector(768)` exist, wired but **naive & dark** (`bijou.py:5097/5522`) | Wire semantics + enable | M |
| 7 | PA vertical | Base persona hard-wired to SME-sales; PersonaManager **dead code** (`bijou.py:4909`) | Make persona selectable | M |
| 8 | WhatsApp onboarding → dashboard | Owner-command surface exists; intake is a **`# TODO` no-op** (`persona_manager.py:324`) | Wire to existing upsert | M |

**Cross-cutting bugs the audit surfaced (fix regardless of features):**
- **B1 — `scheduled_messages` data-loss:** `_save_scheduled_message` (`proactive_messaging.py:886`) writes columns that don't match the live cron-shaped table (`0000_baseline.sql:1771`); inserts fail and are swallowed → scheduled/campaign sends live **in process memory only** and vanish on restart.
- **B2 — `@bijou` operator commands crash:** helpers called without `tenant_id` (`command_handler.py:272-312`) → `TypeError` when `ENABLE_BIJOU_COMMANDS=true` (masked today by `CommandHandler.enabled=false`).
- **B3 — device-routing inconsistency:** dashboard send doesn't use the `bijou-{tenant_id}` fallback that `bijou.py:660` does; errors instead when `whatsapp_devices` is empty.
- **B4 — dead scaffolding:** `LeadConverter.schedule_follow_up()` (`lead_converter.py:413`) is never called; `follow_ups` loop is a no-op.
- **B5 — scale caveat (not a bug yet):** two in-memory 60s/30s loops with no distributed lock → running 2 backend replicas double-sends. Document before scaling out.

---

## Feature detail (state → build → seams → verify)

### 1. Dashboard → WhatsApp reply — VERIFY ONLY
- **State:** `POST /api/dashboard/send-message` → `send_message_as_agent()` (`dashboard_api_simple.py:1005`) proxies to GOWA `/send/message` (`:1100`), resolves tenant→device (`:1108`), persists outbound to `messages` (`:1242`). Inbox reply box wired (`dashboard.html:1121`). Human takeover + co-pilot present.
- **Build:** nothing. Optionally fix **B3** (device fallback).
- **Verify:** log in → open Inbox → send to the connected test number → confirm (a) bridge 200, (b) message arrives on the phone, (c) `messages` row `sent_by="dashboard"`.

### 2. CRM — VERIFY + OPTIONAL ENRICH
- **State:** `contacts` table rich schema (`0000_baseline.sql:694`), full CRUD (`contacts_api.py:86-312`), auto-populated per inbound (`bijou.py:4487`), dashboard UI (`dashboard.html:3068`).
- **Build (optional, ranked):** (a) per-contact **activity timeline** — new `contact_events` table + write a row at the `bijou.py:4487` upsert + `GET /api/contacts/{jid}/events` + UI panel; (b) **deal stages** — `stage` column + `PATCH .../stage`; (c) **custom fields** — `custom_fields jsonb`.
- **Verify:** create/tag/note/delete a contact via UI; confirm a WhatsApp inbound creates a contact row; timeline shows events.

### 3. Stop-texting a contact (soft "AI off") — SMALL ADD
- **State:** hard block (`blocked_numbers` + `_is_number_blacklisted` `bijou.py:2791`, CRUD `dashboard_api_simple.py:2794-2904`) *drops* messages; escalation pause implies a human is handling. No "AI stops replying but I still receive" flag.
- **Build:** add `ai_paused boolean` to `contacts` (table already exists); `_is_ai_paused(tenant_id, chat_jid)` helper mirroring `_is_number_blacklisted`; gate in the shared guard block (`bijou.py:2954-2972`) **and** `process_message` (`:3468`) so both inbound paths honor it (still save the inbound); clone the blacklist CRUD trio into `/api/dashboard/contact/{jid}/ai` + a UI toggle in the Inbox/CRM row.
- **Verify:** toggle AI-off for a contact; send from that number; confirm message is saved but no AI reply; toggle back; confirm replies resume.

### 4. Scheduled messages — FIX + UI
- **State:** `POST /api/proactive/schedule` (`proactive_api.py:112`) + 60s loop send, but persistence is **B1**-broken (in-memory only).
- **Build:** route one-off scheduled sends through the **durable** `outbound_queue` (`0000_baseline.sql:1550`) drained by `OutreachScheduler` (`outreach_scheduler.py:120`) — it already has `scheduled_at`, retry/backoff, anti-spam, opt-out. Add absolute-timestamp param. Tweak the `campaigns!inner` join (`:130`) to allow a null-campaign standalone row. Add a dashboard "schedule message" UI (date/time picker → endpoint).
- **Verify:** schedule a message for +2 min; restart the backend; confirm it still fires after restart (proves durability); confirm cancel works.

### 5. Proactive / automations — FIX + WIRE
- **State:** `ProactiveMessagingSystem` (60s, `proactive_messaging.py:124`) + `OutreachScheduler` (30s, `outreach_scheduler.py:108`) both launched (`bijou.py:1105-1121`), `ENABLE_PROACTIVE_MESSAGING` default true. Call reminders live. REST surface at `/api/proactive`.
- **Build:** fix **B1** (persistence); make lead follow-ups live by calling `LeadConverter.schedule_follow_up()` from the handover-trigger path (`bijou.py:4337-4362`) — fixes **B4**. Decide keep-or-delete the cron-shaped `scheduled_messages` table.
- **Verify:** a warm-lead inbound schedules a follow-up row; the loop sends it when due; anti-spam gates (business hours, daily cap, stop-on-reply) observed in logs.

### 6. Long memory — WIRE SEMANTICS + ENABLE
- **State:** `customer_memory` (`0000_baseline.sql:795`) with `embedding vector(768)`; `MemoryStore` read (`bijou.py:5097`) + write (`:5522`). But summary is naive 1500-char concat, `key_facts` never populated, embedding **never written/queried**, gated **off** (`ENABLE_AGENT_MEMORY`).
- **Build:** on write, (a) extract `key_facts` via `llm.complete("ai://extract", …)`, (b) produce a real rolling summary (LLM, not concat), (c) write the embedding using the existing `vector_search.create_embedding` (`vector_search.py:54`); add a `match_customer_memory` pgvector RPC mirroring `vector_search.py:406`; on read, inject top-K semantically-recalled facts. Enable the flag in prod after verify.
- **Verify:** two-session test — mention a fact (e.g. "my shop is in Ipoh, I sell batik") in session 1; in session 2 ask something that requires it; confirm the reply uses the remembered fact and a `customer_memory` row has non-null `embedding` + populated `key_facts`.

### 7. Personal-Assistant vertical — MAKE PERSONA SELECTABLE
- **State:** base prompt is the unconditional SME-sales `bijou_system_prompt.txt` (`bijou.py:4907`); Manglish forced; `PersonaManager`/`personas` table are **dead for replies** (bypass at `bijou.py:4909`); vertical loader only *appends* a domain block, gated `ENABLE_VERTICAL_TEMPLATES` (off).
- **Build (chosen path — branch the base prompt):** (a) new `bijou_personal_assistant_prompt.txt` (PA/partner persona, Manglish optional, no lead-capture funnel); (b) in `_get_default_system_prompt` (`bijou.py:5701`) accept a `variant` and, at the call site (`:4907`), select it when the tenant's vertical is `personal_assistant`; (c) insert a `vertical_templates` row `vertical_id='personal_assistant'`; (d) add mapping `"personal assistant" → personal_assistant` in `business_profile_api.py:72` + onboarding dropdown; (e) gate Manglish (`:4933`) on the vertical. _(Alt path: revive `PersonaManager` by removing the `:4909` bypass — heavier, deferred.)_
- **Verify:** set a tenant's vertical to `personal_assistant`; send "remind me to call the bank tomorrow" — confirm PA-style reply (no RM299 upsell, no "capture lead" funnel), and an SME tenant still gets the sales persona.

### 8. WhatsApp onboarding → dashboard — WIRE TO EXISTING UPSERT
- **State:** owner surface exists (`/owner` `persona_manager.py:530`, `@bijou` `command_handler.py:137`), but `update_persona_from_instructions` is a `# TODO` no-op (`persona_manager.py:324`) and **nothing** from WhatsApp writes `business_profiles`/`client_configs`/`tenant_verticals`.
- **Build:** extract the dashboard write logic `upsert_business_profile()` (`business_profile_api.py:216`) into a shared service; add `/owner setup` (or a guided intake) that runs `ai://extract` over the owner's messages and calls that shared upsert; fix **B2** (`tenant_id` in `@bijou` helpers) before enabling `ENABLE_BIJOU_COMMANDS`.
- **Verify:** as owner over WhatsApp, "set up my business: Kedai Kopi Aman, cafe, opens 8-6, in Ipoh" → confirm `business_profiles`/`tenant_verticals` rows written and the dashboard business-profile page reflects them.

---

## Execution strategy — "in a go, without getting stuck"

**Three gates (we are here at the end of gate 1):**
1. **AUDIT** ✅ done (this doc).
2. **BUILD** — one `Workflow` orchestration, **one feature per pipeline item**, each item = `implement → self-test → adversarial verify`. Isolation: features touching disjoint files run in parallel; the three that all edit `bijou.py` (#3, #6, #7) are serialized to avoid edit conflicts (or run in worktrees).
3. **VERIFY** — after each feature's code lands, a live end-to-end check against the local Docker stack (the "Verify" row above) before it's marked done. Merge to `main` only after the whole batch is green.

**Anti-stuck mechanisms (why this won't spin):**
- **Everything ships dark behind a feature flag**, enabled only after live verify — a half-built feature can't break prod.
- **Per-feature atomic commit** on `audit/hardening-pass`; a failed feature is reverted in isolation, never blocking the others.
- **Bugs B1–B4 are prerequisites**, done first (they're small and unblock #4/#5/#8).
- **Adversarial verify per finding** — each feature's "done" is challenged by an independent check, not self-attested.
- **Hard scope line:** CRM enrich (#2b/c), memory decay, and the PersonaManager-revival alt-path are explicitly **out of this batch** (logged, not built) to keep it finishable.

**Recommended build order (dependency-sorted):**
`B1,B2,B3,B4 (fixes)` → `#3 stop-texting` → `#4 scheduled` → `#5 proactive wiring` → `#6 memory` → `#7 PA vertical` → `#8 WA-onboarding` → `#1/#2 live-verify pass`.

**Rollback:** every change is flag-gated and per-feature-committed; disabling the flag or reverting the one commit restores prior behavior. No schema change is destructive (all additive columns/tables).

---

## Open decisions for the owner (blockers to starting the build)
- **D1 — AI key:** the rotator is shipped but needs at least one live key (`MINIMAX_API_KEY` / `AI_GATEWAY_API_KEY` / fresh `GEMINI_API_KEY`) or memory/PA verifies can't run end-to-end (they need real generations).
- **D2 — scope:** confirm the batch = features #3–#8 + fixes B1–B4, with #1/#2 as verify-only, and the enrich/alt-paths deferred.
- **D3 — PA persona content:** the PA persona voice (tone, Manglish on/off, what it should/shouldn't do) — provide a short brief or let me draft one for approval.
