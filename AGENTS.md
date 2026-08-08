# AGENTS.md — Bijou AI Monorepo (Master Playbook)

> **Read this first.** This is the master playbook for the **MiniMax Code agent team**
> working on the Bijou AI monorepo. Per-package coding guidelines live in
> `packages/<name>/AGENTS.md` — this file is the strategic + cross-cutting layer.

---

## 0. What this is

Bijou AI is a **WhatsApp/Telegram AI agent** for Malaysian SMEs. The product
has 3 deployable surfaces (landing / backend / bridge) and a multi-tenant
SaaS engine behind them. This monorepo is the **single source of truth** for
all of it.

| Surface | Stack | Lives in | Deploys to |
|---|---|---|---|
| **Landing** (mybijou.xyz) | React 19 + Vite + i18n (5 locales) + Vercel serverless API | `packages/landing/` | Vercel |
| **Backend** (app.mybijou.xyz) | Python (FastAPI) + Node lead pipeline + Supabase | `packages/backend/` | Fly.io |
| **Bridge** (per-tenant) | Go (main.go) + SQLite | `packages/bridge/` | Fly.io |
| **Ops** | PowerShell / bash deploy scripts | `ops/` | local |
| **Docs** | Strategy + 29 historical handoffs | `docs/` | this repo |

Live URLs (last verified: see `topics/bijou-prod-health-state.md` in agent memory):
- <https://mybijou.xyz> — landing (200/307)
- <https://app.mybijou.xyz/health> — dashboard API (200)
- <https://bijou-production.fly.dev/health> — backend (200, version 2.2.0, db: supabase)

---

## 1. The 3 rules for any agent (or human) touching this repo

### Rule 1 — Don't break prod. Verify, then claim.

- Run `npx tsc --noEmit` in the package you touched. If you change `api/*.js`, exercise the endpoint with `curl` (see "verify after change" below).
- **Never claim "fixed" unless you hit the live URL for the exact port + process the user is running.** A parallel uvicorn on port 8081 is NOT proof the live port-8000 service is fixed. (Lesson: this rule exists because of an actual 4-time repeat failure.)
- Read `memory/MEMORY.md` "PR body claim vs reality" before writing any PR or commit message that claims live behavior.

### Rule 2 — The right agent for the right file.

| If you touch... | You are | Read |
|---|---|---|
| `packages/landing/**` | `bijou-frontend` | `packages/landing/AGENTS.md` |
| `packages/backend/app/*.py` | `bijou-backend` | `packages/backend/AGENTS.md` |
| `packages/backend/app/*.cjs` (lead pipeline) | `bijou-pipeline` | `packages/backend/AGENTS.md` § Lead Pipeline |
| `packages/bridge/**` | `bijou-bridge` | `packages/bridge/AGENT.md` |
| `ops/**`, `fly.*.toml`, `vercel.json`, `.github/workflows/**` | `bijou-devops` | this file § 6 |
| Tests, type-check, lint | `bijou-qa` | this file § 7 |
| Any PR diff | `bijou-reviewer` | `adversarial-reviewer` skill |

If your change spans 2 packages, you need a coordinating branch session, not
a single agent. The root Mavis dispatches.

### Rule 3 — Document what you did, in the place future-you will look.

- If you changed a deploy config, update `docs/DEPLOYMENT_SAFETY.md`.
- If you fixed a bug with non-obvious cause, drop a 1-line note in `docs/handoffs-and-audits/` (filename: `<TOPIC>-<DATE>.md`).
- If you changed an env var, update `.env.example` at root.
- If you learned something durable, write it to agent memory (via the `memory` tool, target=main or topic). High-signal only — not every observation.

---

## 2. The autonomous build loop (the "no human in the loop" part)

This is the **5-bottleneck framework**. Solve these 5, you have a hackathon-winner setup.

```
TODO filed (by you OR auto-detected from logs/code)
    ↓
[1] Orchestrator (root Mavis) reads TODO + AGENTS.md + relevant code
    ↓
[2] Dispatches branch session with right specialist (bijou-frontend, etc.)
    ↓
[3] Specialist: implement → test → review-self → commit → push
    ↓
[4] CI runs: lint → typecheck → unit → integration → build → deploy
    ↓  (each step writes STATUS.json)
[5] If green → reviewer agent (adversarial-reviewer)
    ↓
[6] If approved → merge to main → auto-deploy
    ↓
[7] Smoke test in prod (curl /health) → mark done
    ↓
[8] If anything fails twice → self-heal → if still fails, escalate to root
```

**Self-heal rule** (memory-enforced): max **2 retries on the same error**.
After 2 fails, escalate. Don't burn tokens retrying the same broken approach.

**Human escalation triggers** (everything else is autonomous):
- Initial scope ("what's done?")
- Major architecture pivots
- Production deploy button (one human click)
- Anything costing money (DIDs, infra spend, paid APIs)
- A decision needs your authority ("should we kill this old endpoint?")

---

## 3. The agent team

| Agent | Scope | When triggered |
|---|---|---|
| `bijou-architect` | cross-package, specs, ADRs | New feature, refactor request |
| `bijou-frontend` | `packages/landing/` | UI/UX issues, i18n, Vercel api/ |
| `bijou-backend` | `packages/backend/app/*.py` | FastAPI, pricing engine, Supabase schema |
| `bijou-pipeline` | `packages/backend/app/*.cjs` | Lead-gen pipeline (overpass, scorer, outreach) |
| `bijou-bridge` | `packages/bridge/` | WhatsApp Web bridge, history sync |
| `bijou-devops` | CI/CD, `ops/`, deploy configs | Infra issues, secrets, deploys |
| `bijou-qa` | Tests, type-check, lint, e2e | Every PR |
| `bijou-reviewer` | Adversarial review | Every PR pre-merge |
| `bijou-incident` | PagerDuty-style self-heal | Prod health-check fail |

Each agent runs in a **branch session** via the `task` tool. They don't pollute
the root context. They get one job, ship the PR, return.

**Root Mavis (this session) is the orchestrator** — it reads TODOs, dispatches
agents, watches CI, decides when to escalate. Root never writes code directly
unless it's a one-line hotfix that doesn't justify a branch session.

---

## 4. Local + remote sync (the "always-on brain" pattern)

You have 2 places this monorepo lives:
- **Local** (Windows + WSL on your ZBook)
- **Remote** (Contabo VPS, when provisioned)

**The pattern:**
- **Code sync** = git (free, trivial)
- **CI sync** = GitHub Actions is the single source of truth (both local + remote watch it)
- **State sync** = Supabase (the multi-tenant DB) — no per-machine state
- **Cron sync** = same `cron list` on both, **remote (Contabo) is primary** because it never sleeps
- **Agent sync** = same Mavis config on both, same agent roster

**Failure modes:**
- Local down → Contabo keeps the swarm running, picks up next TODO from the queue
- Contabo down → local takes over, same queue, same crons
- Both down → TODO queue persists in Supabase, picks up when one is back

This is the **only way** to get a truly autonomous 24/7 dev loop without paying for always-on CI minutes.

---

## 5. The 1-2 day plan (the one that wins the hackathon)

**Day 1 — foundation (this session + 1 follow-up)**
1. ✅ Survey (done)
2. ✅ Create monorepo + move files (done in this session)
3. ✅ Write master AGENTS.md + .env.example + package.json + .gitignore + README.md (done)
4. ⏳ git init + first commit
5. ⏳ Verify: `npx tsc --noEmit` + `go build` + `python -c "import app"`
6. ⏳ Per-package AGENTS.md updates (pointers to this master)

**Day 2 — agent team + first end-to-end build**
1. ⏳ `mavis agent create` × 6 specialists
2. ⏳ Add 3 GitHub Actions workflows (landing.yml, backend.yml, bridge.yml)
3. ⏳ Add i18n-drift.yml (daily cron for pricing-drift)
4. ⏳ Wire `cron self` for daily cost watchdog + drift + lead pipeline
5. ⏳ First end-to-end build: fix the **9-day i18n.ts pricing drift** (per `topics/bijou-pricing-drift-state.md` — 1 line per string, 4 locales)
6. ⏳ `ship-gate` audit + `adversarial-reviewer` pass
7. ⏳ Production deploy button
8. ⏳ Set up Contabo as remote brain

After Day 2, the swarm runs itself. You get pinged only for the 4 things in §2.

---

## 6. CI/CD — the 4 gates every change goes through

Per package, before merge to `main`:

| Step | Landing | Backend | Bridge |
|---|---|---|---|
| Lint | `npx tsc --noEmit` | `ruff check app/` | `go vet ./...` |
| Type-check | `npx tsc --noEmit` | `mypy app/` (when py.typed added) | `go build ./...` |
| Unit test | (none yet — add in Day 2) | `pytest tests/` (when tests added) | `go test ./...` (when added) |
| Build | `npm run build` | `pip install -r requirements.txt && python -c "import app"` | `go build -o bridge .` |
| Deploy | Vercel auto on main | Fly.io auto on main | Fly.io auto on main |

**Deployment status badges** (add to README once workflows are in):
- ![Landing CI](https://github.com/W3J-Dev/bijou-monorepo/actions/workflows/landing.yml/badge.svg)
- ![Backend CI](.../backend.yml/badge.svg)
- ![Bridge CI](.../bridge.yml/badge.svg)

**Status file**: each CI step writes to a `STATUS.json` artifact that the
orchestrator reads. If a step is red, the orchestrator routes the failure
to the right specialist for self-heal.

---

## 7. Verify after change (the 2-check rule)

For ANY change, before claiming "fixed":

1. **Local check**: run the package's type-check / build / test command locally. Get green.
2. **Live check** (for changes that hit prod): curl the live URL with the exact same path + method + auth as a real user would.

**The 2-check rule exists because of a real failure pattern:**
- Smoke against a parallel uvicorn (port 8081) ≠ smoke against the live port-8000 service
- A unit test that asserts the wrong expected value will pass and still be wrong
- The git "fix" branch can be 3 commits behind `main` and the diff you tested is gone

See `memory/MEMORY.md` "PR body claim vs reality" for the full case study.

**The local commands:**

```bash
# Landing
cd packages/landing && npx tsc --noEmit
cd packages/landing && npm run build

# Backend (Python) — needs venv
cd packages/backend && python -c "import sys; sys.path.insert(0, 'app'); import ai_router"  # adjust per file

# Bridge (Go)
cd packages/bridge && go build -o bridge_test .
cd packages/bridge && go vet ./...
```

---

## 8. Emergency procedures

### "Prod is down"
1. Check `topics/bijou-prod-health-state.md` (last tick state)
2. `curl -fsS https://app.mybijou.xyz/health` — if red, backend is down
3. `curl -fsS https://mybijou.xyz/` — if red, landing is down
4. Spin up `bijou-incident` agent (don't try to fix manually)
5. If the user is the only one with deploy access, escalate with: which service, what the logs say, what you tried

### "I made a change and CI is red"
1. Read the actual error, not the summary
2. Check if `main` is ahead of your branch (rebase first)
3. Self-heal ONCE with the obvious fix
4. If still red, escalate to root with: branch name, error, what you tried

### "I don't know which package a file belongs to"
1. The path tells you: `packages/<name>/` = that package
2. Files at monorepo root = cross-cutting (AGENTS.md, README.md, .env.example, .gitignore, package.json)
3. Files in `docs/` = strategy + history, never edit without good reason
4. Files in `legacy/` = **DO NOT TOUCH** — it's a safety net

### "I want to make a change that doesn't fit the package model"
- Open an ADR: `docs/architecture/ADR-<NNN>-<topic>.md`
- Use the `senior-architect` skill to draft
- Get human sign-off before coding

---

## 9. The don't list (lessons paid for in blood)

These are real mistakes from the project's history (in `topics/` + memory). Don't repeat them.

- ❌ Don't change env var names in prod without fall-back. The `MINIMAX_API_KEY` → `minimax no API key` chain failure on 2026-08-05 was a CRLF `.env` parser bug; never change parsers in deployed code without testing both LF and CRLF inputs.
- ❌ Don't trust cron reports about "548 inserted" when the actual DB count is 0. The Overpass scout was silently failing for 7+ days because `ignoreDuplicates: true` returned `data: []` with no error. Always check the actual count, not the script's own log.
- ❌ Don't use the same `i18n.ts` string for both pricing and features blocks. The KB doc count has been a 1-line fix for 9+ days because the same file says "200 documents" in one place and "50 FAQs + 2 documents" in another.
- ❌ Don't `git reset --hard origin/master` after a squash merge. The squash bundles everything into one commit on `origin/master`; your local feature branch tip is NOT in that commit. Recovery: `git checkout <old-sha> -- <files>`, then commit.
- ❌ Don't claim "fixed" without hitting the live URL. See §7.
- ❌ Don't autodeploy without a smoke test. The "all green CI, prod is broken" pattern is real.

---

## 10. Where to look first

| Question | Look here |
|---|---|
| What's deployed right now? | `topics/bijou-prod-health-state.md` |
| What's broken in the lead pipeline? | `topics/bijou-daily-pipeline-state.md` |
| What's the i18n drift? | `topics/bijou-pricing-drift-state.md` |
| What's my LLM costing? | `topics/bijou-cost-watchdog-state.md` |
| What changed in the codebase? | `git log --oneline -20` |
| What did past humans/agents do? | `docs/handoffs-and-audits/` (29 files) |
| What was the original plan? | `docs/PROJECT_EXECUTION_PLAN.md`, `docs/SWARM_ARCHITECTURE.md` |
| How do I deploy X? | `ops/README.md` + per-package AGENTS.md |
| Why is Y the way it is? | grep the original PR or handoff doc |

---

## 11. The vibe

This codebase serves **Malaysian SMEs**. The product replies in **Manglish**.
The team is autonomous, the loop is tight, the safety nets are real.

When in doubt:
- Run `npx tsc --noEmit` (catches most things)
- Read the existing code in the file you're changing (the answer is usually there)
- Don't add new patterns when an existing one works
- Don't over-engineer — ship, learn, refactor
- The user is building a business, not a portfolio. Bias toward "this works in prod" over "this is theoretically elegant."

Welcome to the swarm. 🚀
