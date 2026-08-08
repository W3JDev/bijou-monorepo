# Bijou AI — Cross-Repo Relation Analysis (Repo A vs Repo B)

**Audit date:** 2026-07-20 (Mon, 07:34 MYT)
**Author:** automated audit agent
**Target repos:**
- **Repo A (current workspace):** `C:\Users\W3jde\local-projects\Bijou-AI---Digital-Employee-main\Bijou-AI---Digital-Employee-main` — Vite/React + Vercel-serverless marketing/landing site
- **Repo B:** `C:\Users\W3jde\local-projects\w3j-bijou-ai-main\w3j-bijou-ai-main` — workspace wrapper; the real product is `w3j-bijou-enterprise/` (FastAPI + Supabase multi-tenant SaaS, Fly.io). Also has `gowa-bridge/`, `whatsapp-bridge/`, `bijou-landing/`.

---

## Verdict (1 line)

**Same product, deliberately split into two repos by design** — Repo A is the public marketing/landing site (Vercel, `mybijou.xyz`); Repo B's `w3j-bijou-enterprise/` is the production multi-tenant FastAPI SaaS (Fly.io, `app.mybijou.xyz` + `bijou-production.fly.dev`). They are loosely coupled by a hand-maintained API contract (two Vercel proxy functions in Repo A call Fly.io endpoints) but share no code, no schema, no env, and no pricing source of truth. **Drift is already visible in pricing, voice, and schema.**

---

## Inventory map (concern vs file vs file vs in-sync?)

| Concern | Repo A file | Repo B file | In sync? |
|---|---|---|---|
| Top-level orientation | `CLAUDE.md:7` — "core product lives in a *separate* repo (`w3j-bijou-enterprise` / `bijou-production.fly.dev`)" | `CLAUDE.md:7-14` — `w3j-bijou-enterprise/` is "SOURCE OF TRUTH" | **Yes** — both name the other side |
| Marketing landing site | `App.tsx`, `components/*` (35 files), `i18n.ts` (85KB), `dist/` | `w3j-bijou-enterprise/static/dashboard.html` etc. (dashboard, **not** landing) | **No** — different site, different purpose |
| Public Bijou voice (demo) | `api/chat.js` (10KB) — 6-step lead-capture Manglish persona, hard-coded pricing/competitors/contacts | `w3j-bijou-enterprise/src/core/bijou_system_prompt.txt` (20KB) + `src/agents/{asi,humanizer,ers,cae,srp}.py` — TRACE empathy pipeline | **No** — divergent voices |
| Production Bijou voice | n/a | `src/agents/humanizer.py` (5KB) strips robotic prefixes, simulates typing, tracks intro frequency | n/a |
| Lead-capture DB | `backend/schema.sql` (4.6KB) + `backend/leads-table-only.sql` + `backend/leads-table-SAFE.sql` (separate, public-only) | n/a (production has its own `tenants`, `contacts`, `escalations` tables) | **No** — landing leads are not the production `contacts` |
| Production multi-tenant DB | n/a | `w3j-bijou-enterprise/database/002_onboarding_schema.sql` … `035_customer_memory.sql` (30+ numbered migrations) | n/a |
| Alternative Supabase migrations | n/a | `supabase/migrations/004_phase2_multi_tenant.sql`, `005_google_oauth_onboarding.sql`, `006_dashboard_token_support.sql` (3 files, smaller set) | **No — triplicate schema risk** |
| Pricing — landing public | `i18n.ts:45-84` — single PRO RM299, 3,000 msg/mo, ENTERPRISE RM999 "Q3 2026" | n/a | — |
| Pricing — in-app dashboard | n/a | `w3j-bijou-enterprise/static/pricing.html:188-339` — **PRO RM299 + GROWTH RM499** (two tiers, year toggle) | **No** |
| Pricing — backend engine | n/a | `w3j-bijou-enterprise/src/saas/pricing_engine.py:65-127` — **FREEMIUM / STARTER $29 / PRO $99 / ENTERPRISE** (USD, 4 tiers, 100–5000 msg/mo) | **No — three different pricing realities** |
| Stripe config | `api/spots.js` (reads `STRIPE_SECRET_KEY`, only counts active subscriptions) | `src/saas/stripe_service.py` (18.8KB) + `payment_api.py` (19.6KB); `.env.example` defines `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_GROWTH_*` | **No** — Repo A's pricing check has no equivalent of Repo B's Stripe price IDs |
| Email service — Resend | `api/leads.js`, `api/slide-deck.js`, `api/voice-waitlist.js` (single `RESEND_API_KEY`; landing-only HTML templates hardcoded) | `src/saas/email_service.py` (36.8KB, **multi-domain rotation** across 4 keys/domains) + `src/integrations/email_service.py` (18.2KB) | **No** — different domains, different templates, different reliability model |
| Cross-repo proxy | `api/send.js:34` → `https://bijou-production.fly.dev/api/send`<br>`api/onboarding/signup.js:43` → `https://bijou-production.fly.dev/api/onboarding/signup`<br>`api/leads.js:349` → `${VERCEL_URL}/api/send` (chains the proxy) | These endpoints presumably exist in `src/saas/payment_api.py`, `src/saas/onboarding_api.py` | **Partly** — URLs are hardcoded strings; no schema/version check |
| Env vars — Supabase | `.env` (committed!) + `api/*.js`: `SUPABASE_URL`, `VITE_SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | `.env.example:18-22`: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`; CLAUDE.md warns: *"preflight in bijou.py requires SUPABASE_KEY, not SUPABASE_SERVICE_KEY"* | **No** — Repo B's CLAUDE.md itself flags this naming conflict |
| Env var — AI demo | `CUSTOME_API_ENDOINT` (typo, missing 'P'), `CUSTOME_API_KEY`, `GEMINI_API_KEY_3`, `GEMINI_API_KEY_4`, `VITE_GEMINI_API_KEY` | `GEMINI_API_KEY` only (per `.env.example` + `src/agents/asi.py:70`) | **No** — landing has its own AI gateway layer, completely different |
| Brand assets / logo | `dist/bijou-logo.svg` (61KB), `public/brand/*` | `static/bijou-logo.png` (1.1MB), `static/bijou-logo-transparent.png` (3.7MB), `static/bijou-logo.svg` (3.1MB) | **Likely out of sync** (different file sizes, different content) — unverified, manual check needed |
| i18n copy | `i18n.ts` 85KB — 4 langs (en/ms/zh/ta), hard-codes all marketing copy | n/a (no public surface) | n/a |
| Stripe "early-adopter" counter | `api/spots.js` (`TOTAL_EARLY_ADOPTER_SPOTS = 10`) | n/a | n/a |
| Marketing system prompt (TRACE) | `api/chat.js:25-130`: ASI/Humanizer/ERS/Routing labels in `Features.tsx` (per CHANGELOG v5.0.0) | `src/agents/{asi,cae,ers,humanizer,srp}.py` — actual production agents | **Partial** — names match, behavior doesn't (landing labels use different ordering per `Features.tsx` "Emotion→ASI, Cause→Humanizer, Plan→ERS, Respond→Routing" but production TRACE is `ASI→CAE→SRP→ERS`) |
| Versioning scheme | CHANGELOG semver `1.0.0 → 5.0.0` (last entry 2026-05-15) | CHANGELOG (root) + `w3j-bijou-enterprise/CHANGELOG.md` use `v300 / v301 / 3.6.0 / 3.7.0` | **No** — independent schemes |
| `package.json` | `bijou-ai---digital-employee` v0.0.0, React 19, Vite 6, Supabase, Resend, Stripe | `w3j-bijou-enterprise/package.json` (531B) — Playwright only; Python is the real manifest in `requirements*.txt` | n/a |
| Bridge (Go WhatsApp) | n/a (just proxies) | `gowa-bridge/` (source) + `whatsapp-bridge/` (deployed instance) | n/a |
| Onboarding (production signup) | `api/onboarding/signup.js` — **thin proxy to fly.dev** | `src/saas/onboarding_api.py` (24KB) + `onboarding_api_v3.py` (17KB) | Coupling exists, but undocumented |
| Cross-doc references to the other repo | `CLAUDE.md`, `README.md`, `scripts/i18n_audit.py` (hard-coded local path) | `docs/brand-docs/BijouAi_brand_guide_doc.md:66`; `w3j-bijou-enterprise/docs/PAYMENT_ROLLOUT_COMPLETION.md:110/299/307`; `w3j-bijou-enterprise/docs/LANDING_TO_PAYMENT_FLOW.md:4`; `w3j-bijou-enterprise/database/yesterday.md:5118/5161/5194` | **Yes** — both sides name the other |
| `bijou-landing/v0-cliste-website-navigation/` (Repo B) | n/a | Empty dir (0 files); **many** Repo B docs still reference files inside it (e.g. `app/dashboard/whatsapp/page.tsx`, `tests/screenshots/`, `tests/e2e/dashboard-e2e.spec.ts`) — all stale | **Stale references** |
| Top-level `src/saas/orchestration.py` (Repo B root) | n/a | 2.6KB duplicate of `w3j-bijou-enterprise/src/saas/orchestration.py` (2.6KB) — points at `jryalnbmsxfxihurfwmc.supabase.co` (a different project than the one in `.env`/landing) | **No** — orphan duplicate |
| Git history | "your current branch 'main' does not have any commits yet" / "not a git repository" | Same | **No versioning pin possible** |

---

## Divergence log (concrete, evidence-backed)

1. **Three different "live" pricing tables in three files:**
   - `i18n.ts` (Repo A): single PRO RM299, 3,000 msg/mo, ENTERPRISE RM999 "Q3 2026"
   - `w3j-bijou-enterprise/static/pricing.html` (Repo B in-app): PRO RM299 (RM251/yr) + GROWTH RM499 (RM419/yr)
   - `w3j-bijou-enterprise/src/saas/pricing_engine.py` (Repo B engine): FREEMIUM 100 msg / STARTER $29/1000 / PRO $99/5000 / ENTERPRISE custom
   - **Risk:** if marketing runs an "early adopter RM299" promo against the backend's $99 PRO limit, the production `pricing_engine` will silently allow >3,000 messages, or a customer paying RM299 will hit limits designed for $99.

2. **Landing's i18n.ts still carries the dead 3-tier model** (`pricing.starter.*`, `pricing.professional.*`, `pricing.enterprise.*` keys at `i18n.ts:101-128`) even though `CHANGELOG.md` v4.0.0 (2026-03-04) claims "Removed ~190 lines of leftover 3-tier JSX from `Pricing.tsx`." The English translation file was not cleaned; the keys are orphaned but reachable.

3. **Bijou's voice has bifurcated.** The landing demo (`api/chat.js:22-131`) is a 6-step lead-capture script in Manglish with hard-coded `jewel@mybijou.xyz` / `support@mybijou.xyz` / `hello@mybijou.xyz` / `+60 17-410 6981` / `https://app.mybijou.xyz/signup`. The production system (`src/core/bijou_system_prompt.txt`) is an entirely different prompt for property-agent lead handoff, with different contact info (`w3j.btc@gmail.com`, Jewel in Subang Jaya), different domain example URLs, and a "[BREAK]" token formatting rule the landing copy does not use. Customers who chat with the landing demo and then message the production bot on WhatsApp will get two different personalities.

4. **TRACE component labelling has drifted.** Repo A's `CHANGELOG.md` v5.0.0 (2026-05-15) renames TRACE for the Features widget to "Emotion→ASI, Cause→Humanizer, Plan→ERS, Respond→Routing", but the production `asi.py / cae.py / ers.py / humanizer.py / srp.py` pipeline actually runs in the order **ASI → CAE → SRP → ERS → LLM → Humanizer** (per `w3j-bijou-enterprise/CHANGELOG.md` v301, 2026-05-15). The marketing diagram does not match the runtime order.

5. **Two Vercel proxy endpoints hard-code the Fly.io URL.** `api/send.js:34` and `api/onboarding/signup.js:43` both call `https://bijou-production.fly.dev/api/send` and `/api/onboarding/signup` respectively. There is no environment-variable override; the staging URL is unreachable from the landing site without a code change.

6. **Schema is triplicated.** `Repo A/backend/{schema.sql, leads-table-only.sql, leads-table-SAFE.sql}` define a public-only `leads` table. `Repo B/w3j-bijou-enterprise/database/` holds 30+ production migrations (`002_…` through `035_…`). `Repo B/supabase/migrations/` holds a third, smaller set (`004_phase2_multi_tenant.sql`, `005_google_oauth_onboarding.sql`, `006_dashboard_token_support.sql`). The two Repo B locations share **none** of the migration numbers — they are independent, and a fresh `supabase db push` from either location will produce a different schema state.

7. **Env-var naming conflicts even inside Repo B.** `w3j-bijou-enterprise/.env.example` defines both `SUPABASE_KEY` and `SUPABASE_SERVICE_KEY`, and CLAUDE.md explicitly warns: *"preflight in bijou.py requires SUPABASE_KEY, not SUPABASE_SERVICE_KEY"*. `OWNER_WHATSAPP_JID` is defined twice in the same file (`+601160600963@s.whatsapp.net` and `60174106981@s.whatsapp.net`). `WHATSAPP_OWNER=+601160600963` and `BIJOU_OWNER_WA=601121113249` — three different owner WhatsApp numbers exist. The landing site also uses two Supabase URL env-var names (`SUPABASE_URL` and `VITE_SUPABASE_URL`).

8. **Repo A's `.env` is committed to the working tree** (`.env`, 7.9KB). It contains live secrets: `RESEND_API_KEY` (4 domains), `SUPABASE_SERVICE_ROLE_KEY`, `CAL_API_KEY`, `CAL_0AUTH_CLIENT_ID`, `VITE_GEMINI_API_KEY` + 2 rotation keys, a Fly.io V1 API token, `SUPABASE_ACCESS_TOKEN`, an `AGENTMAIL` API key, and 5 domain-specific `IMPROVMX_*` keys. The `.gitignore` should have excluded it; either the file was added before the rule, or the rule is incomplete. The Vercel `OIDC_TOKEN` is in `.env.local` (also committed). **High risk.**

9. **Typo in the AI gateway env var is propagated to code.** The committed `.env` line is `CUSTOME_API_ENDOINT=https://ai-gateway-…` (missing the 'P' in ENDPOINT). `api/chat.js:103` reads `process.env.CUSTOME_API_ENDOINT` directly — the typo is now part of the public code path. Renaming the env var in Vercel will silently break the demo.

10. **A duplicate "orchestration" module is orphaned at the Repo B root.** `w3j-bijou-ai-main\src\saas\orchestration.py` (2.6KB) and `w3j-bijou-ai-main\w3j-bijou-enterprise\src\saas\orchestration.py` (2.6KB) are byte-similar duplicates; the root-level one hard-codes a different Supabase project (`jryalnbmsxfxihurfwmc.supabase.co`) and exposes only `find_available_bridge()` / `increment_bridge_device_count()`. Nothing imports it — it is dead code that the founder will eventually believe is canonical.

11. **The `bijou-landing/v0-cliste-website-navigation/` directory is empty but heavily referenced.** Five Repo B docs (`CONTINUATION_SUMMARY.md`, `E2E_TEST_RESULTS.md`, `PROJECT_OVERVIEW.md`, `PROJECT_STATUS.md`, `docs/brand-docs/BijouAi_brand_guide_doc.md`) still describe it as a Next.js project with `app/dashboard/whatsapp/page.tsx`, Playwright tests, and a `tests/screenshots/` folder. None of those files exist. The directory was created 2026-07-18 and contains 0 files. Any future agent reading the docs will think there is a third landing repo.

12. **A Telegram add-on + inclusion contradiction in the same file.** `i18n.ts:59` says PRO includes "Telegram AI Agent — same brain, same Manglish"; `components/Pricing.tsx:25` lists `{ name: "Extra Telegram bot", when: "Q2 2026", price: "+RM60/mo" }`. Both files claim to describe the same product. The CHANGELOG v4.0.0 entry (2026-03-04) explicitly says "Telegram now included in PRO (was a paid add-on at +RM60/mo)" but the add-on is still in the array.

13. **`services/gemini.ts` is not Gemini.** The file is a thin `fetch('/api/chat')` proxy to the Vercel handler, which in turn uses OmniRoute (Claude Haiku / Gemini Flash via `CUSTOME_API_KEY`). The `services/tools.ts` "Tool Orchestrator" only `console.log`s — no real email send. Anyone reading the file names will assume a Gemini direct integration that does not exist.

---

## Shared schema / contract candidates

These are the surfaces where drift will silently break the customer experience. Each should be a generated/shared artifact.

| Candidate | Current state | What it should be |
|---|---|---|
| Pricing tier table | Hard-coded strings in 3 places (`i18n.ts`, `pricing.html`, `pricing_engine.py`) | A single TypeScript-typed `pricing.ts` in Repo A and a generated `pricing_pb2.py` (or Pydantic model) in Repo B, both from one source |
| Lead-capture request schema | `api/leads.js` accepts `{name,email,phone,company,industry,source,marketing_consent}`; production has no matching endpoint — the leads live in Repo A's Supabase only | Either a typed Zod schema shared via npm package, or a real `POST /api/contacts` proxy in Repo B that writes into the production `contacts` table |
| Proxy endpoint contract | Hard-coded `https://bijou-production.fly.dev/api/send` and `/api/onboarding/signup` | An OpenAPI client generated from `w3j-bijou-enterprise/openapi.json` (110KB) consumed by Repo A's `api/*.js` |
| Bijou voice | Two divergent `systemInstruction` strings (landing demo vs production) | One canonical persona + pricing + competitor-comparison + contact-info document, with landing- and production-specific deltas declared in a manifest |
| Brand assets | Two sets of `bijou-logo.*` and `brand/*` with different sizes/encodings | A single `brand-kit/` (or a `packages/brand` workspace package) consumed by both repos; today sizes already differ (61KB svg in Repo A vs 3.1MB svg in Repo B) |
| Resend sender map | Landing uses 1 key; production uses 4-domain rotation pool | A typed `email-senders.ts` / `email_senders.py` with the 4-domain list, shared |
| Stripe price IDs | `.env.example` defines `STRIPE_PRICE_STARTER/PRO/GROWTH_*`; landing `api/spots.js` only counts customers | A `stripe-prices.ts` consumer file; the landing's "early-adopter spots remaining" badge should read from a single `STRIPE_PRICE_PRO_*` config |
| Owner/operator contacts | Three different WhatsApp JIDs across Repo B's `.env.example`; landing has one | A `contacts.yaml` listing `founder_whatsapp`, `support_whatsapp`, `notify_email`, `from_email`, `domain` |
| i18n keys for pricing | Repo A's i18n has the dead 3-tier keys; the same brand string ("Telegram included") appears in two contradictory forms in Repo A alone | A typed `i18n-keys.ts` with `as const` keys, plus a CI check that any removed key has no React references |

---

## Monorepo vs polyrepo recommendation

**Recommendation: Keep polyrepo, but add a small shared package (option b) — not (a), not (c).**

Reasoning:

- **(a) Monorepo is the wrong move.** Repo A is Vite/React/Vercel (ESM, Node-edge runtime, no `node_modules` outside Vite's); Repo B is FastAPI/Python/Fly.io (uv, requirements files, Deno edge functions). Folding them together would mean either two build systems fighting in one `package.json`/`pyproject.toml`, or a pnpm/turbo setup that adds 5x the complexity for a 1-person team. The founder's "Refactor reality" note in Repo B's CLAUDE.md (`bijou.py` is 7,300 lines, `dashboard_api_simple.py` 3,500) shows the back-end already has its hands full. Adding a third concern (a build orchestrator) is the wrong thing to do first.
- **(c) Fully independent would also be wrong.** The two are **demonstrably coupled**: Vercel `api/send.js` and `api/onboarding/signup.js` call Fly.io URLs, the landing site embeds `app.mybijou.xyz` URLs in 30+ components, the production email/help_chat copy references `mybijou.xyz`, the brand guide in `docs/brand-docs/` names the landing repo explicitly, and `database/yesterday.md` is full of cross-repo workflows ("Update landing CTAs in `C:\Users\w3jbt\PROJECTS\Bijou-AI---Digital-Employee`"). Pretending they're independent is what got the pricing/voice drift in the first place.
- **(b) Shared package is the right level.** A single repo (or sub-folder in either repo, mirrored by a sync script) holding:
  - `pricing.json` — one source of truth for tiers, prices, currency, limits
  - `voice.md` — canonical Bijou persona + Manglish rules + pricing/contact snippets
  - `brand/` — logos, fonts, color tokens
  - `openapi-client.{ts,py}` — generated from `w3j-bijou-enterprise/openapi.json`
  - `env.example` — single canonical env-var list with notes on which side consumes which

  This gives both repos a "lockdown surface" without a monorepo migration. The contracts become versioned (semver) and the diff between releases is visible.

  Concrete shape:
  ```
  w3j-bijou-shared/   ← third repo, or a sub-folder in either side
  ├── pricing.json
  ├── voice.md
  ├── brand/...
  ├── openapi.json   ← exported from w3j-bijou-enterprise's openapi.json
  ├── env.example
  └── CHANGELOG.md
  ```
  Repo A consumes via npm git dep or subtree; Repo B via pip git dep or `path` reference. **Both repos reference the same `@bijou/shared` version in their respective changelogs** so the implicit version contract is explicit.

---

## Quick wins (this week)

1. **Rotate every secret in Repo A's `.env` and `.env.local`**, then `git rm --cached` both and update `.gitignore`. The committed `.env` contains a Fly.io V1 API token, a Supabase service-role key, a `SUPABASE_ACCESS_TOKEN`, four Resend keys, and a Cal.com OAuth client secret — any of these are now public. This is the single highest-priority fix.
2. **Pick one pricing reality and delete the other two.** The fastest path: keep the landing-site `i18n.ts` prices (RM299 PRO) as marketing truth, make `w3j-bijou-enterprise/static/pricing.html` mirror it, and rewrite `src/saas/pricing_engine.py` so the engine accepts a JSON config loaded at startup. Twenty lines of code, one config file, zero drift.
3. **Replace the two hard-coded Fly.io URLs** in `api/send.js:34` and `api/onboarding/signup.js:43` with `process.env.BIJOU_PRODUCTION_URL` (and a `BIJOU_STAGING_URL` for previews). Add both to Vercel env vars. This unlocks the staging path for the landing site.
4. **Add a one-page `CONTRACTS.md` to the root of each repo** that lists, in one table, every URL, env var, table name, and lead-schema field that the other repo depends on. The current truth is scattered across `yesterday.md` (537KB), `CLAUDE.md` × 2, and `docs/PAYMENT_ROLLOUT_COMPLETION.md`. A single indexable document turns cross-repo changes from archaeology into a checklist.
5. **Fix the typo `CUSTOME_API_ENDOINT` → `CUSTOM_API_ENDPOINT` in both `.env` and `api/chat.js:103`.** While you're in there, also fix the email-template contradiction (`i18n.ts:59` "Telegram included" vs `Pricing.tsx:25` "+RM60 add-on") and the orphaned 3-tier keys still living in `i18n.ts:101-128`. These are mechanical edits; they only matter because they survive the auto-formatter and ship.

---

## Unverified — manual check needed

- **Git remotes / branches / tags.** Neither checkout has a `.git` history, so the report cannot confirm which GitHub org/branch the live sites deploy from. **Manual check needed.**
- **Brand assets parity.** Sizes differ wildly between `dist/bijou-logo.svg` (61KB in Repo A) and `static/bijou-logo.svg` (3.1MB in Repo B) and the PNGs (none in A, 1.1MB / 3.7MB in B). **Manual check needed** to confirm whether the logos are the same artwork at different sizes/encodings, or have drifted.
- **Whether `bijou-production.fly.dev/api/send` and `/api/onboarding/signup` still exist** in the deployed build of `w3j-bijou-enterprise`. The proxy code in `api/send.js:34` and `api/onboarding/signup.js:43` assumes they do; the CHANGELOG references in Repo B's `dashboard_api.py` evolution (multiple refactors) suggest the surface may have changed.
- **The actual production `openapi.json` ↔ landing `api/*.js` contract.** `w3j-bijou-enterprise/openapi.json` is 110KB but was not diffed against the four Vercel endpoints.
