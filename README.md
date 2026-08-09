# Bijou AI â€” Monorepo

[![Landing CI](https://github.com/W3JDev/bijou-monorepo/actions/workflows/landing.yml/badge.svg)](https://github.com/W3JDev/bijou-monorepo/actions/workflows/landing.yml)
[![Backend CI](https://github.com/W3JDev/bijou-monorepo/actions/workflows/backend.yml/badge.svg)](https://github.com/W3JDev/bijou-monorepo/actions/workflows/backend.yml)
[![Bridge CI](https://github.com/W3JDev/bijou-monorepo/actions/workflows/bridge.yml/badge.svg)](https://github.com/W3JDev/bijou-monorepo/actions/workflows/bridge.yml)

**The whole product in one repo.** Marketing site + dashboard + AI backend + WhatsApp bridge, deployable as 3 independent services (Vercel + Fly.io + Fly.io).

Bijou is a WhatsApp/Telegram AI agent that answers customer messages 24/7 for Malaysian SMEs (clinics, F&B, property agents, salons). Replies in **Manglish** â€” the cultural moat.

- ðŸŒ Landing: <https://mybijou.xyz>
- ðŸ› ï¸ Dashboard: <https://app.mybijou.xyz>
- ðŸ“¡ API: <https://bijou-production.fly.dev>
- ðŸ¦ Status: `curl -fsS https://app.mybijou.xyz/health` â†’ `{"status":"ok",...}`

---

## The 3 packages

| Package | Stack | Deploys to | Purpose |
|---|---|---|---|
| [`packages/landing/`](./packages/landing/) | React 19 + Vite + Tailwind (CDN) + 5-locale i18n | **Vercel** | Marketing site + demo AI chat + lead capture + Vercel serverless API (`api/*.js`) |
| [`packages/backend/`](./packages/backend/) | Python (FastAPI) + Node.js lead pipeline (Supabase) | **Fly.io** (`bijou-production`) | Multi-tenant SaaS engine + Supabase migrations + AI lead-gen pipeline |
| [`packages/bridge/`](./packages/bridge/) | Go (main.go 55KB) + SQLite | **Fly.io** | WhatsApp Web bridge â€” connects tenant phone, syncs messages, runs on tenant's behalf |

Plus [`ops/`](./ops/) (22 deploy/monitor scripts) and [`docs/`](./docs/) (architecture + strategy + 29 historical handoffs).

---

## Quick start

```bash
# 1. Install JS deps (workspaces)
npm install

# 2. Run the landing in dev mode
npm run dev:landing          # http://localhost:3000

# 3. Type-check the landing
npm run typecheck:landing

# 4. Run the lead pipeline (needs Supabase creds in packages/backend/.env)
npm run lead:overpass        # scout Klang Valley prospects from OpenStreetMap
npm run lead:scorer          # score them with AI
npm run lead:outreach        # draft Manglish outreach for top fits
```

For backend (Python) and bridge (Go) â€” see their per-package README + AGENTS.md.

---

## The agent team

This monorepo is designed to be worked on by a swarm of specialist agents (the **MiniMax Code team**), not just one human. Each agent has a narrow role and a narrow scope:

| Agent | Scope | Tools |
|---|---|---|
| `bijou-frontend` | `packages/landing/` only | React, Vite, Tailwind, i18n |
| `bijou-backend` | `packages/backend/app/*.py` | FastAPI, Supabase, pricing engine |
| `bijou-pipeline` | `packages/backend/app/*.cjs` | Lead pipeline, ai-router, overpass |
| `bijou-bridge` | `packages/bridge/` | Go, SQLite, Fly.io, WhatsApp Web |
| `bijou-devops` | CI/CD, `ops/`, `fly.*.toml`, `vercel.json` | GitHub Actions, Vercel, Fly.io |
| `bijou-qa` | Tests, type-check, lint, e2e | tsc, pytest, go test, playwright |
| `bijou-reviewer` | PR review | adversarial-reviewer skill |

The root **Mavis** (this session) is the orchestrator: receives TODOs, dispatches branch sessions, watches CI, escalates to human only on irreversible decisions.

See [`AGENTS.md`](./AGENTS.md) for the full playbook.

---

## Deploys

| Service | URL | Trigger |
|---|---|---|
| Landing | <https://mybijou.xyz> | Push to `main` â†’ Vercel auto-deploy |
| Dashboard/API | <https://app.mybijou.xyz> / <https://bijou-production.fly.dev> | Push to `main` â†’ Fly.io auto-deploy (via `fly.production.toml`) |
| Bridge | per-tenant via Fly.io | Push to `main` â†’ Fly.io auto-deploy (via `fly.bridge-production.toml`) |

Status (last 30 ticks): see `bijou-prod-health-state.md` in agent memory topics.

---

## Documentation

- [`AGENTS.md`](./AGENTS.md) â€” **read this first**. The master playbook: what's in each package, who owns what, how to ship a change, the agent team, the autonomous loop.
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) â€” system architecture
- [`docs/SWARM_ARCHITECTURE.md`](./docs/SWARM_ARCHITECTURE.md) â€” the agent team design
- [`docs/PROJECT_EXECUTION_PLAN.md`](./docs/PROJECT_EXECUTION_PLAN.md) â€” the original 1-2 day plan
- [`docs/QUICK_START.md`](./docs/QUICK_START.md) â€” fast dev environment setup
- [`docs/handoffs-and-audits/`](./docs/handoffs-and-audits/) â€” 29 historical reports, decisions, and fixes (read these before you refactor anything that might have been touched before)

---

## Per-package docs

- [`packages/landing/AGENTS.md`](./packages/landing/AGENTS.md) â€” frontend coding guidelines, i18n rules, Vercel serverless patterns
- [`packages/backend/AGENTS.md`](./packages/backend/AGENTS.md) â€” Python backend, lead pipeline, Supabase schema
- [`packages/bridge/AGENT.md`](./packages/bridge/AGENT.md) â€” Go bridge, WhatsApp Web sync, history logic
- [`ops/README.md`](./ops/README.md) â€” deploy/monitor scripts

---

## Legacy

[`legacy/`](./legacy/) contains the original 2 repos (`Bijou-AI---Digital-Employee-main.original/` and `w3j-bijou-ai-main.original/`) untouched. **Don't `git rm` it â€” it's a safety net.** The whole repo's git history will be fresh (we re-init in this monorepo), so legacy stays as a reference but isn't tracked.

<!-- CI trigger: 2026-08-09 05:33:41 MYT -->


<!-- CI smoke test: 2026-08-09 21:09:05 -->

