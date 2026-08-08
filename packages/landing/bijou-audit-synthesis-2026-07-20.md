# Bijou AI — Audit Synthesis (2026-07-20)

**One-page exec summary tying together three independent audit reports.**

This synthesis is the entry point. Read this first, then drill into the linked report(s) for the specific evidence.

## The three reports

| # | Report | File | Size | Angle |
|---|--------|------|------|-------|
| 1 | **Senior fullstack audit** | [`audit-report.md`](./audit-report.md) | 49 KB | Architecture, code quality, deps, build/deploy, i18n, repo hygiene, 40 numbered findings, 5-row risk register, 30/60/90 day plan. **Plus 4 re-runnable Python audit scripts in `scripts/`.** |
| 2 | **Adversarial review** | [`adversarial-review.md`](./adversarial-review.md) | 34 KB | Hostile-eye attack on `api/*.js`, silent failures, prompt injection, phishing surfaces, CLAUDE.md lies, hostile-user scenarios. |
| 3 | **Cross-repo relation analysis** | [`cross-repo-analysis.md`](./cross-repo-analysis.md) | 22 KB | Same product, deliberately split into 2 repos; pricing/voice/schema drift, shared-package recommendation, quick wins. |

All three agents worked from the same starting evidence (the working tree) and converged on the same top findings. Where they disagreed, the disagreement is itself informative.

## TL;DR

> **The Bijou AI landing site is the public-facing half of a two-repo product. Today it is in worse shape than its own CLAUDE.md admits, and it is bleeding trust in three concrete ways: (1) live production secrets are in the working tree; (2) the lead-capture and voice-waitlist endpoints return HTTP 200 even when every backing service has failed, silently dropping customer leads; (3) two unauthenticated, CORS-`*` endpoints (`/api/send` and the `create-link` edge function) make the brand's primary domain an open relay for WhatsApp phishing. The cross-repo coupling with `w3j-bijou-enterprise/` is a hand-maintained proxy contract with three different pricing realities, two divergent Bijou voices, and triplicated schema — which means even after the immediate fixes, drift will re-introduce the same problems unless a shared `w3j-bijou-shared/` package is introduced.**

**Verdict (overlapping across all 3 reports):** do not ship to a paying customer today. Three blockers must be fixed first (rotate secrets, stop swallowing errors in lead endpoints, gate the open proxies). Then 30-day hardening. Then 90-day structural cleanup.

## The top 7 blockers (consensus across the 3 reports)

These are the items that appeared in all three reports' top-tier findings. They are the things to do this week.

| # | Blocker | Where it lives | Why it matters | All 3 reports flag it? |
|---|---------|----------------|----------------|------------------------|
| 1 | **`.env` + `.env.local` checked in with live secrets** (Supabase service-role JWT, Vercel OIDC, Discord bot tokens, Cloudflare tunnel, Fly.io bearer, 4 Resend keys, Cal.com OAuth secret) | `.env:1-115`, `.env.local:1-3` | One `git log -p .env` exposes all of it. Service-role key bypasses every RLS policy on the Supabase project. | **Yes** |
| 2 | **`/api/send` is an unauthenticated, CORS-`*` proxy to production WhatsApp** | `api/send.js:5, 25-32` | Anyone on the internet can send arbitrary WhatsApp messages to any number through the brand's production system. Phishing primitive + MY CMA 1998 / PDPA exposure. | **Yes** |
| 3 | **`create-link` + `redirect` edge functions are an unauthenticated link shortener on `mybijou.xyz`** | `backend/supabase/functions/{create-link,redirect}/index.ts` | Anyone can publish `https://mybijou.xyz/l/abc12` that opens WhatsApp with attacker-controlled text on the brand's primary domain. | **Yes** |
| 4 | **Lead-capture endpoints return 200 on total backend failure** (Supabase + Resend + WhatsApp all down → user still sees "Check your email" with a fake `temp-<timestamp>` leadId) | `api/leads.js:117-130`, `api/voice-waitlist.js:50-55`, `api/slide-deck.js:130-133` | Customer thinks the founder is ignoring them; founder has no DLQ/alert; the "24h follow-up" promise is a lie in the failure path. | **Yes** |
| 5 | **No rate limiting on any endpoint** (Resend quota exhaustable in minutes; Supabase writes unbounded) | all `api/*.js` | Cost-amplification attack is trivial — 100k requests = ~200k Resend emails + 100k WhatsApp messages + Supabase bill. | **Yes** |
| 6 | **No CSP, HSTS, Permissions-Policy, Referrer-Policy**; `X-XSS-Protection` is set but deprecated | `vercel.json:17-30` | Latent XSS / clickjacking surface; brand-impersonation defense missing. | **Yes** |
| 7 | **`schema.sql` enables RLS on `leads` with zero policies defined** | `backend/schema.sql:69-76` | Currently masked only by the service-role bypass; one env-var typo away from total compromise. | **Yes** |

## Cross-cutting issues (where the 3 reports disagreed — and what that tells you)

The three agents agreed on the top blockers. They diverged on the *second tier*. The divergence is itself a signal — the issues that are "P1 in one report, P2 in another" are the structural/drift problems that will keep re-appearing.

### Drift the audit caught (3rd report, structural)

- **Three different "live" pricing tables** in three files: `i18n.ts` (RM299 PRO single tier), `w3j-bijou-enterprise/static/pricing.html` (PRO RM299 + GROWTH RM499), `w3j-bijou-enterprise/src/saas/pricing_engine.py` (FREEMIUM/STARTER $29/PRO $99/ENTERPRISE USD). The senior audit's P1 "30-day vs 14-day money-back" mismatch is a *symptom* of this — the same product, three pricing realities. Until there's a single source of truth, copy contradictions will keep happening.
- **Two divergent Bijou voices**: landing demo (`api/chat.js:22-131`) is a 6-step lead-capture Manglish script; production (`bijou_system_prompt.txt` + 5 TRACE agents) is a property-agent lead-handoff system. A customer who chats with the landing demo and then messages the production bot on WhatsApp will get two different personalities. The senior audit's P1 "`DemoChat.tsx:20` opening violates the system's own Manglish rules" is a symptom of this — the landing prompt is hand-tuned, the production prompt is a different file entirely.
- **Triplicated schema**: `Repo A/backend/*.sql` (3 files), `Repo B/w3j-bijou-enterprise/database/00X_*.sql` (30+ migrations), `Repo B/supabase/migrations/00X_*.sql` (3 files with different numbering). The senior audit's RLS-gaps and the adversarial review's "which SQL file is canonical?" are *symptoms* of this — the schema is split across 3 places and nobody can tell which is live.
- **Hard-coded Fly.io URLs** in `api/send.js:34` and `api/onboarding/signup.js:43`. The cross-repo report flagged this; the senior audit didn't because it was scoped to Repo A. But it's the **reason** the open proxy problem is so dangerous — it's not a server you can take down, it's a relay to a production system you don't control from this repo.

### What the senior audit caught that the adversarial missed

- **PWA icons 404 in production** (`index.html:38, 53, 86-104` references `/icons/icon-192x192.png` which doesn't exist). The adversarial skim didn't open `index.html`; the senior audit walked the deploy surface.
- **52.8 MB of `public/brand/{1..12}.png` committed and never referenced anywhere** (Repo A `public/brand/`).
- **`dist/` committed at 53.75 MB** (gitignored in spirit, not in fact). Bloats the repo.
- **The "30-day vs 14-day money-back" copy contradiction** in 3 user-facing surfaces.
- **`HowItWorks.tsx:100` "4-Agent Empathy Pipeline · 41% lift"** — the CHANGELOG walked it back to a single-LLM architecture, but the marketing copy still says 4 agents.
- **`i18n` is a façade: 28/37 components don't use `useTranslation`** — the setup is there but most components hardcode English. The adversarial review confirmed the i18n *catalog* is well-built; the senior audit pointed out it isn't actually *used*.

### What the adversarial caught that the senior missed

- **`/api/spots.js` fabricated scarcity counter** — returns a hardcoded `{total: 3, remaining: 7}` on any Stripe error; the front-end renders it without flagging. The senior audit caught the *number*; the adversarial caught the *lie*.
- **The service worker caches POST responses** — a successful `POST /api/leads` is cached and served to the *next* user, who gets the first visitor's `leadId` back. Subtle data-leakage bug.
- **Email regex rejects `+`-aliases** (both JS regex and SQL constraint miss the `+` in the local-part char class). Legitimate `john+test@gmail.com` fails both layers. Cross-cutting because it affects all 3 lead endpoints.
- **Slide-deck endpoint is broken** — `.upsert({onConflict: "email"})` requires a unique index on `email`; the schema doesn't have one. The endpoint will throw on first call.
- **Founder's contact info is in the system prompt** — extractable via prompt injection. The senior audit noted the demo chat pattern; the adversarial walked the full "what does a hostile user do" tree.
- **The "voice-waitlist" endpoint has no Supabase call at all** — only Resend. The CLAUDE.md says "all four persist to Supabase." Adversarial caught the false-advertising.

### What the cross-repo caught that the other two couldn't have

- **Same product, two repos, no shared contract.** The senior audit and adversarial both stayed inside Repo A; the cross-repo analysis was the only one that could see the `bijou-production.fly.dev` hard-codes, the pricing drift, the voice drift, and the schema triplication.
- **The `bijou-landing/v0-cliste-website-navigation/` empty directory in Repo B** that 5 stale docs still describe as a Next.js project. Future agents will be misled.
- **The orphaned `w3j-bijou-ai-main\src\saas\orchestration.py` at Repo B root** that hardcodes a different Supabase project (`jryalnbmsxfxihurfwmc.supabase.co`). Dead code that will eventually be mistaken for canonical.

## Combined risk register

| # | Risk | Likelihood | Impact | Owners |
|---|------|-----------|--------|--------|
| 1 | Open WhatsApp proxy (`/api/send`) → mass harassment, Fly.io suspension, brand damage | High | Critical | Repo A (gate the proxy) + Repo B (move auth into the upstream endpoint) |
| 2 | Open-redirect shortener (`create-link`/`redirect`) → phishing on `mybijou.xyz` | High | High | Repo A (validate destination + add auth) |
| 3 | Live secrets in `.env` + `.env.local` → service-role key compromise, full Supabase read/write | Medium (latent — already in working tree, only high if repo was pushed) | Critical | Repo A (rotate today, gitignore, push protection) |
| 4 | RLS enabled with zero policies → one env-var typo from total compromise | Medium | Critical | Repo A (add policies in a new migration) |
| 5 | Lead funnel silently drops data (always-200) → customer trust erosion, lost revenue | High (every Stripe/Supabase/Resend outage) | High | Repo A (return 5xx on backend failure, add DLQ + admin alert) |
| 6 | Resend quota DoS via `/api/leads` flood → bill shock, brand-as-spammer | High | High | Repo A (rate limit + CAPTCHA + drop self-call) |
| 7 | Three pricing realities + two Bijou voices + triplicated schema → copy contradictions, broken customer expectations | High (every release) | High | Both repos (introduce `w3j-bijou-shared/`) |
| 8 | Founder's contact info in system prompt + landing chat → prompt-extraction → harassment | Medium | Medium | Repo A (move contact out of prompt, add a `contact_human` tool the LLM must call) |
| 9 | 30-day vs 14-day money-back copy → consumer-protection exposure in MY | Medium | Medium | Repo A (single source of truth) |
| 10 | Hand-rolled PWA + service worker caching POSTs → user A gets user B's leadId | Medium | Medium | Repo A (switch to `vite-plugin-pwa` + Workbox, never cache POST) |

## 30-day plan (the urgent ones, ordered by ROI)

### Day 0 (today) — secrets + open proxies

1. **Rotate every secret in `.env` + `.env.local`.** Then `git rm --cached` both, update `.gitignore`, force-push, and trigger any Vercel deploy to invalidate cached env. (Highest priority; one-time fix.)
2. **Gate `api/send.js` and `api/onboarding/signup.js`.** Add a `process.env.INTERNAL_PROXY_TOKEN` check; restrict CORS to `https://mybijou.xyz` and `https://app.mybijou.xyz`; whitelist the `to` number prefix (`+60` only).
3. **Gate `create-link` + `redirect` edge functions.** Add an allowlist of phone prefixes; require a founder-signed JWT to create a link; validate `destination_url` is `https://wa.me/...` only.
4. **Replace hard-coded `bijou-production.fly.dev` URLs** with `process.env.BIJOU_PRODUCTION_URL` (and `BIJOU_STAGING_URL` for previews).

### Day 1-3 — lead funnel + rate limiting + schema

5. **Stop swallowing errors in `api/leads.js`, `api/voice-waitlist.js`, `api/slide-deck.js`.** Return 5xx on Supabase/Resend failure; add a fallback inbox (or a simple DLQ table) and an admin alert.
6. **Add a unique index on `leads.email`** (fixes the slide-deck upsert that was broken) and a basic RLS policy in a new migration `000_leads_policies.sql`.
7. **Add rate limiting + Cloudflare Turnstile** to public lead forms. At minimum: per-IP 5 req/min on `/api/leads`, `/api/voice-waitlist`, `/api/slide-deck`, `/api/onboarding/signup`.
8. **Move founder contact info out of the system prompt** and into a `contact_human` tool the LLM must call.

### Day 4-7 — security headers + PWA + copy

9. **Replace `vercel.json` security headers** with a full CSP, HSTS, Referrer-Policy, Permissions-Policy, COOP, COEP. Remove the deprecated `X-XSS-Protection`.
10. **Fix PWA icons** — generate real 192/512/180 PNGs, remove the broken `/icons/icon-192x192.png` references from `index.html`, generate a real `og-image.svg`.
11. **Pick one trial-length copy and apply everywhere** (resolve the 30-day vs 14-day contradiction).
12. **Update `HowItWorks.tsx:100`** to match the actual single-LLM architecture (drop the "4-Agent · 41% lift" headline).
13. **Fix `DemoChat.tsx:20` opening** (drop "boleh tahu" — the system prompt forbids it).
14. **Fix the `CUSTOME_API_ENDOINT` typo** in both `.env` and `api/chat.js:103` in the same commit.
15. **Fix `CalBooking.tsx:18`** `process.env` → `import.meta.env`.

### Day 8-14 — repo hygiene + i18n cleanup

16. **`git rm -r dist`** and ensure it's in `.gitignore`.
17. **Delete the 52.8 MB of unreferenced brand PNGs** in `public/brand/`.
18. **Update `CLAUDE.md`**: 5 → 4 languages, note the edge functions, note the open-proxy work that's been done.
19. **Update `AGENTS.md`** — it's stale and overlapping with CLAUDE.md.
20. **Move to a real PWA setup**: `vite-plugin-pwa` + Workbox, with proper precache manifest and hashed asset names.
21. **Fix the email regex + SQL constraint** to allow `+` in the local part (`[A-Za-z0-9._%+-]+@...`).
22. **Fix the service worker's POST caching** — only cache GET responses; for non-idempotent endpoints, never cache the response.

### Day 15-30 — drift prevention (cross-repo)

23. **Create `w3j-bijou-shared/`** as a third repo (or a sub-folder in either side, mirrored by a sync script). Hold `pricing.json`, `voice.md`, `brand/`, generated `openapi-client.{ts,py}`, canonical `env.example`.
24. **Pick one pricing reality** and delete the other two. The fastest path: keep `i18n.ts` (RM299 PRO) as marketing truth; make `w3j-bijou-enterprise/static/pricing.html` mirror it; rewrite `src/saas/pricing_engine.py` to accept a JSON config loaded at startup.
25. **Write a one-page `CONTRACTS.md`** in each repo listing every URL, env var, table name, and lead-schema field that the other repo depends on.
26. **Delete the orphaned `src/saas/orchestration.py` at Repo B root** (the byte-similar duplicate pointing at a different Supabase project).
27. **Add a CI check** that fails the build if any Vercel handler returns 200 on a non-success path.

## Re-runnable audit scripts (Repo A `scripts/`)

The senior fullstack audit left four Python scripts in `scripts/` that re-verify the findings. Run them after fixes.

| Script | What it checks |
|--------|----------------|
| `scripts/i18n_audit.py` | 4 langs × 238 keys; finds duplicates, missing translations, orphaned keys |
| `scripts/i18n_unused.py` | Lists keys defined in `i18n.ts` but never referenced in `components/` |
| `scripts/i18n_usage.py` | Lists components NOT using `useTranslation` (i18n façade check) |
| `scripts/dep_audit.py` | Inspects `package.json` for outdated majors + known-vulnerable transitive deps |

```bash
# from the repo root
python scripts/i18n_audit.py
python scripts/i18n_unused.py
python scripts/i18n_usage.py
python scripts/dep_audit.py
```

## What the site does well (don't tear it all down)

It's worth keeping in mind that the audit also found genuinely good things, and not everything needs to change:

- **The i18n catalog** is genuinely well-built (4 langs × 238 keys, 0 dupes, 0 missing translations). It's the *usage* that's a façade, not the catalog.
- **`vite.config.ts` is properly hardened** — no secret leakage via the bundler today.
- **The AI gateway fallback chain** (`auto/best-fast` → `gemini-2.5-flash` → `claude-haiku-4-5` → direct Gemini) is clever and actually degrades gracefully.
- **The honest-copy CHANGELOG discipline** (v5.0.0) is exemplary — the authors do walk back claims.
- **Component composition is clean** — shallow prop-drilling, no global store, plain `useState`. The "no router, single scroll page" architecture CLAUDE.md describes is actually how the code is laid out.
- **PWA service worker is correctly scoped** (network-first for `/api/*`, cache-first for static, prod-only registration) — it just has the POST-caching bug and the version-decoupling bug.

## The bottom line

Three concrete P0 blockers (secrets in tree, open WhatsApp proxy, open link shortener) and a structural drift problem (two repos with no shared contract). The P0s are a 1-2 day fix; the structural problem is a 30-60 day program. The good news: the cross-repo recommendation (introduce `w3j-bijou-shared/`) is low-effort and high-leverage — it makes the existing drift visible and prevents the next 10 drift bugs from happening.

The site isn't broken. It's *trust-broken*: a paying customer will get a worse experience than the landing page promises, and the brand's primary domain is an open relay. Fix the trust first; everything else is incremental.
