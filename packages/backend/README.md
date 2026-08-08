# Bijou AI Enterprise — WhatsApp AI Sales & Support Platform

**Version:** 3.6.0 | **Updated:** 2026-03-10 | **Status:** Production Live

## What's New in v3.6.0

| Feature                          | Detail                                                                                                                                                  |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Escalation notification bell** | Live alert bell in dashboard topbar: red badge, 30-second polling, Web Audio chirp (880→440 Hz) on new escalation arrival.                              |
| **`/pricing` page**              | Full public pricing page — PRO RM299/mo, GROWTH RM499/mo, monthly/yearly toggle, Stripe checkout. Route: `GET /pricing`.                                |
| **Missed call webhook handler**  | `event_type=call.*` now synthesizes `📞 MISSED_CALL` and routes it through the AI follow-up pipeline instead of being silently discarded.               |
| **Settings UX redesign**         | Single-column layout, merged email cards, "My Account" card with JWT-decoded email/name, Password Reset button.                                         |
| **422 campaign create fix**      | `createCampaign()` payload corrected to match `CampaignCreateRequest` Pydantic model (`name`, `daily_limit`, `min/max_delay_seconds`, `send_window_*`). |

## What's New in v3.5.0

| Feature                            | Detail                                                                                                                      |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Live Chat Widget (help.html)**   | Bijou AI powered chat panel: public + tenant modes, email verification, auto-escalation to support ticket after 3 messages. |
| **Gemini Multimodal Document OCR** | PDF/image/DOCX/XLSX/CSV/MD — all processed by Gemini 2.5 Flash natively (including scanned PDFs, invoice photos).           |

## What's New in v3.2.0

| Feature                             | Detail                                                                                                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`@bijou` WA commands live**       | Owner can now send `@bijou status`, `@bijou help`, etc. directly from WhatsApp. Async dispatch fixed in `bijou.py`. `ENABLE_BIJOU_COMMANDS` defaults `true`. |
| **Contact CSV Export**              | `GET /api/contacts/export.csv` — one-click download of all CRM contacts as CSV (name, phone, JID, tag, notes, status).                                       |
| **Contact CSV Import**              | `POST /api/contacts/import` — bulk-upsert contacts from a CSV file. Supports Excel BOM, deduplicates on `tenant_id + jid`.                                   |
| **Dashboard Export/Import buttons** | `↓ Export CSV` and `↑ Import CSV` buttons live in the Contacts CRM toolbar.                                                                                  |

> A multi-tenant SaaS AI agent that fully automates WhatsApp customer engagement for SMEs — handling sales enquiries, booking calls, managing leads, escalating to humans, and giving operators a WhatsApp-native command interface to run the business from their phone.

---

## Problem We Solve

Small and medium businesses in Malaysia (and SE Asia broadly) run their entire customer pipeline on WhatsApp. They have:

- **No time** to reply instantly 24/7
- **No budget** for a call centre
- **No system** to capture leads, follow up, or book calls
- **No visibility** into what customers are asking

Bijou AI plugs directly into their existing WhatsApp number and becomes their always-on sales agent — replying in Manglish, Malaysian English, BM, Chinese, or Tamil — learning their product catalogue, booking appointments, escalating to the human when needed, and giving the operator a live command panel via their own WhatsApp.

---

## Live Deployments

| Environment         | URL                                          | Status |
| ------------------- | -------------------------------------------- | ------ |
| Production App      | `https://bijou-production.fly.dev`           | Live   |
| Staging App         | `https://bijou-staging.fly.dev`              | Live   |
| Dashboard           | `https://app.mybijou.xyz`                    | Live   |
| WA Bridge (Prod)    | `https://bijou-bridge-production-v2.fly.dev` | Live   |
| WA Bridge (Staging) | `https://bijou-bridge-staging-v2.fly.dev`    | Live   |
| Database            | Supabase `lrwzlujomukzjykafmic`              | Live   |

---

## Tech Stack

| Layer                   | Technology                                         |
| ----------------------- | -------------------------------------------------- |
| **AI Model**            | Google Gemini 2.5 Flash (`google-genai >= 1.56.0`) |
| **Web Framework**       | FastAPI + Uvicorn (Python 3.11)                    |
| **Database**            | Supabase (PostgreSQL + pgvector)                   |
| **WhatsApp Bridge**     | GOWA v8.x (Go service, Fly.io)                     |
| **Frontend Dashboard**  | Single-file Vue 3 (CDN, no build step)             |
| **Deployment**          | Fly.io (Docker, Singapore region `sin`)            |
| **CI/CD**               | GitHub Actions + Fly.io hooks                      |
| **Payments**            | Stripe (subscription billing)                      |
| **Auth**                | Supabase JWT + Magic Link                          |
| **Storage**             | Supabase Storage (knowledge files, media)          |
| **Vector Search**       | pgvector (`vector_search.py`)                      |
| **Telegram (optional)** | python-telegram-bot >= 22.0                        |

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                  Customer (WhatsApp)                       │
└───────────────────────┬────────────────────────────────────┘
                        │ WhatsApp Cloud API
                        ▼
         ┌─────────────────────────────────┐
         │         GOWA Bridge (Go)        │
         │  bijou-bridge-production.fly.dev│
         │  • Multi-device WA sessions     │
         │  • QR pairing + reconnect       │
         │  • Forwards webhooks to Bijou   │
         │  • Sends messages for Bijou     │
         └────────────────┬────────────────┘
                          │ HTTP Webhook
                          ▼
┌──────────────────────────────────────────────────────────────┐
│               Bijou AI (FastAPI)  bijou-production.fly.dev   │
│                                                              │
│  Tenant Router (device → tenant_id)                         │
│       │                                                      │
│  Message Filter → ASI → TRACE Prompt → Gemini 2.5 Flash     │
│       │                     │               │               │
│  [Guardrails]     [Social Intel]    [Tool Orchestrator]      │
│  [Anti-scam]      [Manglish]        [Knowledge Engine]       │
│  [Spam filter]    [ERS Escalate]    [Lead Capture]           │
│       │                                                      │
│  Humanizer → Send via Bridge                                 │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │          Supabase (PostgreSQL + pgvector)            │    │
│  │ messages · tenants · contacts · call_bookings        │    │
│  │ knowledge_items · media_library · escalations        │    │
│  │ whatsapp_devices · notification_groups               │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
             Dashboard (app.mybijou.xyz)
             Vue 3 SPA — Operator / Admin UI
```

---

## Features

### AI & Conversation

- **Gemini 2.5 Flash** — fast, low-cost inference; key rotation via `cost_optimizer.py`
- **TRACE Framework** — structured sales/support conversation embedded in system prompt
- **Manglish mode** (per tenant) — `lah`, `kan`, `boleh` injected for authentic MY tone
- **Multi-language** — English, BM, Chinese (Mandarin), Tamil; detected per message
- **Context memory** — last N messages from DB per conversation thread
- **Hallucination control** — responses checked against KB facts (`hallucination_control.py`)
- **Guardrails** — blocks harmful, out-of-scope, competitor, scam content
- **Anti-scam guard** — detects inbound scam patterns (`security/anti_scam_guardrail.py`)

### Lead & Sales Automation

- **Lead capture** — AI extracts name, phone, intent, quality score → `contacts` table
- **CRM** — contacts with tags (Lead / Customer / VIP / Cold), editable names, notes
- **Inbox enrichment** — conversation list shows saved names + tag badges from CRM
- **Live learning** — operator WA corrections stored to `learning_logs`; Bijou improves
- **Proactive messaging** — schedule campaigns to contact lists

### Call Booking

- Full booking flow via WhatsApp conversation
- Availability settings (editable from dashboard): buffer, max calls/day, max/hour, advance days, same-day toggle, timezone
- Google Calendar event creation on confirmed booking
- Automated WA reminders to customers
- `@bijou confirm <ID>` — operator marks booking from WhatsApp

### Escalation System

- ERS detects: anger, complexity, explicit human request
- Handover — Bijou goes silent, human takes over
- Notification groups — multiple operators notified per tenant
- Stale escalation cleanup via background job

### Knowledge Base

- Upload: PDF, TXT, DOCX, CSV, XLSX, PNG, JPG, GIF, WEBP, MP3, MP4, MOV (≤10 MB)
- pgvector semantic search for relevant KB articles per query
- Note + trigger phrase per KB item for contextual injection
- Owner WA notification on every upload

### Media Library

- Upload, tag, delete media assets
- `SEND_FILE` token — Bijou sends the file directly to the customer in-conversation
- Keyword tagging via `PATCH /api/media/{id}`

### Operator WhatsApp Commands (`@bijou`)

| Command                        | What it does                     |
| ------------------------------ | -------------------------------- |
| `@bijou bookings`              | Today's bookings for your tenant |
| `@bijou crm <query>`           | Search contacts by name or phone |
| `@bijou send <target> > <msg>` | Send a WA message to any contact |
| `@bijou confirm <id>`          | Mark booking as in_progress      |
| `@bijou pause`                 | Pause Bijou                      |
| `@bijou resume`                | Resume Bijou                     |
| `@bijou help`                  | Full help                        |

> **Note:** Dispatch is currently commented out at `bijou.py:2130` (sync→async fix needed). Tracked in roadmap.

### Dashboard (app.mybijou.xyz)

- **Inbox** — WhatsApp-style layout, enriched contact names, tag badges
- **Contacts CRM** — searchable table, tag filter, inline name edit, delete, CSV import/export
- **Escalations** — live queue, claim/close; topbar bell with audio chirp on new escalation
- **Knowledge Base** — upload, list, delete; note + trigger phrase per item; PropertyGuru URL import
- **Media Library** — upload, tag, delete
- **Call Booking** — calendar, booking list, fully editable settings
- **Outreach** — campaign builder, segment manager; corrected Pydantic payload (v3.6.0 fix)
- **Settings** — single-column UX, "My Account" with JWT-decoded profile, password reset, email config + test-email, Manglish toggle, ignore list, business hours
- **Billing** — Subscribe vs Manage button based on Stripe customer status; link to `/pricing` page
- **PWA** — installable, bottom nav on mobile (iOS/Android)

### Multi-Tenancy

- Strict isolation: every DB query has `.eq("tenant_id", tenant_id)` — no exceptions
- Device routing: `whatsapp_devices` table maps device JID → `tenant_id` per message
- Per-tenant AI persona, prompt, KB, business hours, Manglish mode
- Free vs Pro limits via `plan_manager.py`
- Self-service onboarding: Stripe checkout → QR pairing → live

---

## Repository Structure

```
w3j-bijou-enterprise/
├── src/
│   ├── core/           ← App entry, pipeline, LLM, tools, memory
│   ├── agents/         ← ASI, Humanizer, ERS sub-agents
│   ├── saas/           ← Business logic, multi-tenancy, all SaaS APIs
│   ├── integrations/   ← Call booking, webhooks, Google Sheets
│   ├── channels/       ← Bridge adapter (WA), Telegram adapter
│   └── security/       ← Anti-scam guardrail
├── static/
│   └── dashboard.html  ← Full dashboard (Vue 3, single file ~3500 lines)
├── database/migrations/ ← 026 numbered SQL migrations
├── tests/              ← e2e / functional / integration
├── scripts/            ← 60+ utility scripts
├── docs/               ← All documentation
├── .github/workflows/  ← CI/CD
├── Dockerfile
├── fly.production.toml
├── fly.staging.toml
└── Makefile
```

---

## Quick Start (Local Dev)

```bash
# Dev deps only — NOT the full 3GB ML stack
make setup

make audit      # lint + root cleanliness check
make test       # full test suite
make test-fast  # unit tests only
```

### Key `.env` Variables

```env
SUPABASE_URL=https://lrwzlujomukzjykafmic.supabase.co
SUPABASE_KEY=<anon key>
GEMINI_API_KEY=<key>
BRIDGE_URL=https://bijou-bridge-staging-v2.fly.dev
BRIDGE_USER=bijou
BRIDGE_PASSWORD=<password>
OWNER_WHATSAPP_JID=60xxxxxxxxx@s.whatsapp.net
ENABLE_BIJOU_COMMANDS=true
```

---

## Deployment

```bash
# Staging
C:\Users\w3jbt\.fly\bin\flyctl.exe deploy --app bijou-staging --config fly.staging.toml

# Production — via VS Code task: "Push to production"
git push --no-verify origin main:production
```

---

## CI/CD Pipeline

```
Push to main
 ├── GitHub Actions: lint → static audit → pytest (3.10 / 3.11 / 3.12)
 └── Fly.io: auto-deploy to staging (manual gate for production)
```

---

## Known Issues

| Issue                                                                         | Status             |
| ----------------------------------------------------------------------------- | ------------------ |
| `@bijou` commands disabled — `bijou.py:2130` commented out (sync/async)       | Roadmap            |
| `process_message` is synchronous                                              | REFACTOR-3 tracked |
| `dashboard_api_simple_backup.py` exists in src/core                           | Cleanup pending    |
| Outreach campaign `description` used as message body — no dedicated DB column | Roadmap            |

---

## Documentation

| Doc                                          | Purpose                               |
| -------------------------------------------- | ------------------------------------- |
| [CHANGELOG.md](CHANGELOG.md)                 | Full version history                  |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Deep architecture + flowcharts        |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md)     | Operator guide (EN + Manglish)        |
| [docs/ROADMAP.md](docs/ROADMAP.md)           | Future features                       |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)     | Deploy step-by-step                   |
| [AGENTS.md](AGENTS.md)                       | Codebase compass for devs + AI agents |

---

## License

Proprietary — All rights reserved. W3J Bijou AI, 2026.
