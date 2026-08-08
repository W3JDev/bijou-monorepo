# packages/backend/AGENTS.md

> **Master playbook**: read `../../AGENTS.md` first. This file is the
> per-package detail for the backend.

## What this package is

The Bijou AI multi-tenant SaaS engine. Two sub-pieces:

1. **Python (FastAPI)** — the multi-tenant API, pricing engine, billing,
   tenant lifecycle, post-purchase automation. Will live in `app/` once
   organized (currently mixed with Node scripts).
2. **Node.js (lead-gen pipeline)** — the daily cron pipeline that scouts
   Klang Valley prospects from OpenStreetMap, scores them via AI, and
   drafts Manglish outreach. Files: `app/overpass_scout.cjs`,
   `app/run_scorer_now.cjs`, `app/run_outreach_topfit.cjs`,
   `app/research_scan.cjs`.

Plus Supabase migrations (`supabase/migrations/`) and the schema that
powers everything (`supabase/migrations/agent_fleet_schema.sql`).

## Folder layout

```
packages/backend/
├── app/                         # Python + Node source (mixed for now)
│   ├── *.py                     # FastAPI endpoints, pricing, billing
│   ├── *.cjs                    # Lead pipeline (overpass, scorer, outreach)
│   ├── agent_fleet_schema.sql   # The agent fleet DB schema
│   ├── migrations/              # Older SQL migrations
│   └── *.log                    # Debug logs (gitignored)
├── supabase/                    # Active Supabase config
│   ├── migrations/              # Current migrations
│   └── .env                     # Local Supabase creds (gitignored)
├── scripts/                     # DB utility scripts (check, list, probe)
├── fly.production.toml          # Fly.io deploy config (this package)
└── AGENTS.md                    # you are here
```

## Daily pipeline (cron)

Runs at 04:00 and 06:00 MYT every day. 3 steps:

1. **04:00** — `overpass_scout.cjs` → inserts 500+ new prospects (Klang Valley clinics + F&B)
2. **04:00** — `run_scorer_now.cjs 150` → scores up to 150 with AI
3. **04:00** — `run_outreach_topfit.cjs 60 15` → drafts Manglish for top 15 fit≥60
4. **06:00** — `research_scan.cjs` → Reddit + LLM-enriched digest

**Last run state**: see `topics/bijou-daily-pipeline-state.md` in agent memory.

**Known issues (from memory)**:
- `ai-router.cjs` env loader bug on CRLF `.env` (1-line fix: `split('\n')` → `split(/\r?\n/)`)
- `MiniMax-M3` provider ignores JSON schema → 0 fit scores for 3+ days
- `overpass_scout.cjs` reports "inserted" but `ignoreDuplicates: true` returns empty `data`
- Outreach LLM returns "Empty content" / "Unterminated string" frequently

**Do not auto-fix these without user sign-off** — they're in deployed scripts
and any change needs a re-run of the pipeline to verify.

## Lead pipeline scripts — when to touch

| Script | When | Why |
|---|---|---|
| `overpass_scout.cjs` | Adding new region or vertical | The query is hardcoded Klang Valley |
| `run_scorer_now.cjs` | Adding new scoring field | JSON schema needs an example in the system prompt |
| `run_outreach_topfit.cjs` | Changing Manglish style or template | Persona rules are inline |
| `research_scan.cjs` | Adding a new source | Reddit pacing needs `sleep(8000)` first |
| `ai-router.cjs` | Adding a new provider | Chain-fallback bug means new provider needs try/catch wrapping |

## Pricing engine

Files: `app/pricing_engine.py` (and any sibling `*_pricing*.py`).

Critical: this is the source of truth for what customers get charged.
**Any change to `TIER_PRICING`, `TIER_LIMITS`, or `get_tier_info()` requires:**
1. Update `packages/landing/i18n.ts` to match (5 locales)
2. Update `packages/landing/api/*.js` Stripe-related code
3. Add a migration in `supabase/migrations/` if the schema changes
4. Update `.env.example` at monorepo root

The pricing-drift cron (`bijou-pricing-drift-state.md` in memory) catches
3-way drift between landing/i18n.ts, in-app pricing.html, and this engine.
**A drift here = customer sees one price, gets charged another.** P0.

## Supabase schema

`supabase/migrations/` and the root `agent_fleet_schema.sql`.

Before adding a new table:
1. Check if `agent_fleet_schema.sql` already has a similar table (it's the
   pre-built fleet schema)
2. Use the naming convention: `bjx_<table_name>` (e.g., `bjx_prospects`,
   `bjx_review_queue`, `bjx_listener_opportunities`)
3. Add RLS policies (every table needs them, even internal ones)
4. Add a `created_at` and `updated_at` column
5. Add to the cron state topics so drift can be detected

## Environment

Read `.env` from `packages/backend/.env` (gitignored). The variables the
backend reads are documented in monorepo-root `.env.example` under the
"packages/backend/" section.

Critical: `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are mandatory. Without
them, every script fails with a connection error.

## Build / verify

```bash
# Python syntax check (no venv needed)
cd packages/backend
python -m py_compile app/*.py

# Run the lead pipeline (needs .env)
node app/overpass_scout.cjs          # inserts ~500 prospects
node app/run_scorer_now.cjs 5        # score 5 (test mode)
node app/run_outreach_topfit.cjs 60 1

# Fly.io deploy
fly deploy -c fly.production.toml
```

## Common patterns

- **Multi-tenant isolation**: every query should include `tenant_id`
- **Async everything**: FastAPI routes are async; use `await` on supabase calls
- **Pricing is data, not code**: TIER_PRICING is a dict, not if/else
- **Cron logs to .opencode/**: pipeline runs write `*.log` and `*.err.log` next to scripts
- **No auto-restart of ai-gateway sprite**: that's owned by the user, not the cron
