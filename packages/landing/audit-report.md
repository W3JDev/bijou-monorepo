# Bijou AI Landing Repo — Senior Fullstack Engineering Audit

**Repo:** `Bijou-AI---Digital-Employee-main/Bijou-AI---Digital-Employee-main`
**Audited:** Full local tree, 37 components, 7 serverless endpoints, 2 Supabase edge functions, 1 schema, `package.json` / `package-lock.json`, `vercel.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, PWA assets, i18n, dist snapshot.
**Method:** Static read-only review. No builds run. No endpoints hit. All findings cite `file:line`.

---

## TL;DR

- **P0** `api/send.js` and `api/onboarding/signup.js` are **unauthenticated open proxies** to the production WhatsApp system and onboarding API. Anyone on the internet who finds the URL can send arbitrary WhatsApp messages to arbitrary numbers, or sign arbitrary people up. Two-factor for the founder's WA number and a phishing vector for the brand.
- **P0** `backend/supabase/functions/{create-link,redirect}/index.ts` is an unauthenticated link shortener with an **open redirect** (no `destination_url` validation) — phishing-as-a-service on the `mybijou.xyz/l/...` domain.
- **P0** `schema.sql` enables RLS on the `leads` table but **declares zero policies**. Today this is masked by the service-role key bypassing RLS; one line of bad code or one env-var typo switches to anon auth and all reads/writes silently fail (or worse, leak to anyone who guesses the anon key).
- **P1** No rate limiting on any lead/email endpoint. Resend quota is finite; an attacker can exhaust it in minutes.
- **P1** All `api/*.js` set `Access-Control-Allow-Origin: *` on POST. Combined with no auth, the entire lead pipeline is cross-origin callable.
- **P1** `vercel.json` security headers are missing CSP, HSTS, Referrer-Policy, and Permissions-Policy. `X-XSS-Protection: 1; mode=block` is deprecated and can introduce vulnerabilities.
- **P1** The official "30-day money-back" promise is contradicted by "14 days free" copy in 3 user-facing surfaces (`OnboardingModal.tsx:434`, `slide-deck.js:94`, `SlideDeckModal.tsx:85`).
- **P1** The marketing headline "4-Agent Empathy Pipeline · 41% conversion lift" (`HowItWorks.tsx:100`) is not implemented. `api/chat.js` makes a single LLM call. CHANGELOG tried to walk this back but the headline is still live.
- **P1** The demo chat's opening message violates the system's own Manglish rules (`DemoChat.tsx:20` says "boleh tahu" — explicitly forbidden by `api/chat.js:32,97`).
- **P1** `public/brand/1.png` … `12.png` total **52.8 MB** and are not referenced anywhere in the codebase. They bloat the repo and the Vercel deployment.
- **P2** **76% of components (28/37) don't use `useTranslation`.** The i18n file is well-built (4 langs × 238 keys, no dupes, no missing keys), but most of the user-facing surface is hardcoded English — the only way `LanguageSwitcher` actually does anything for non-EN users is via the components that *do* use `t()`.
- **P2** The PWA is broken in the install experience — `index.html` references `/icons/icon-192x192.png` and `/icons/icon-152x152.png` that **don't exist**; `manifest.json` points the 192/512 icon slots at `/favicon.png` (a 32×32 file). On most devices the install dialog will show a stretched favicon.
- **P2** `CalBooking.tsx:18` uses `process.env.VITE_PUBLIC_CAL_USERNAME` in the browser bundle. Vite uses `import.meta.env`, not `process.env`. It only works because the fallback is hardcoded.
- **P2** Env-var typo `CUSTOME_API_ENDOINT` (should be `CUSTOM_API_ENDPOINT`) is in both `.env` and `api/chat.js:96`. Fixing one without the other will silently break chat.
- **P2** The `dist/` directory is committed at 53.75 MB (Vercel builds it fresh on every deploy — pure bloat).
- **P2** `CLAUDE.md` claims 5 i18n languages (EN, BM, Manglish, ZH, TA); there are 4 (en, ms, zh, ta). `ms` is formal Bahasa Melayu, not Manglish.

---

## Findings

### 1. **P0** — `api/send.js` is an unauthenticated open proxy to the production WhatsApp system

**Evidence:** `api/send.js:1-66`
```js
res.setHeader('Access-Control-Allow-Origin', '*');
...
const { to, message } = req.body;
if (!to || !message) { ... }
const response = await fetch('https://bijou-production.fly.dev/api/send', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ to, message })
});
```

**Why it matters.** Any unauthenticated caller can `POST /api/send` with `to: "any-phone-number"`, `message: "anything"` and the message is sent through the production WhatsApp bridge. Realistic impact:
- Mass-harassment of arbitrary Malaysian phone numbers, attributed to the Bijou brand.
- WhatsApp account suspension at Fly.io (Meta's anti-abuse systems are aggressive).
- Phishing messages from the founder's WA number.
- The owner-notify path in `leads.js:339-358` and `OnboardingModal.tsx:316-340` *also* calls this endpoint, so the lead-capture flow itself depends on this open proxy — there is no internal/external split.

**Fix.**
1. Add a server-side shared-secret header (e.g. `X-Internal-Token`) checked against `process.env.INTERNAL_API_TOKEN`.
2. Restrict `Access-Control-Allow-Origin` to `https://mybijou.xyz` and `https://app.mybijou.xyz`.
3. Whitelist the `to` field — the only legitimate caller sends to the founder's number; the JS code should be inlined as a constant.
4. Drop the endpoint entirely from the public API and have leads.js / OnboardingModal call the Fly.io backend directly with the secret.
5. Add a 5-second in-process rate limit per IP.

---

### 2. **P0** — `api/onboarding/signup.js` is an unauthenticated open proxy to the production onboarding system

**Evidence:** `api/onboarding/signup.js:1-67`
```js
res.setHeader('Access-Control-Allow-Origin', '*');
...
const { business_name, email, phone } = req.body;
if (!business_name || !email) { ... }
const response = await fetch('https://bijou-production.fly.dev/api/onboarding/signup', { ... });
```

**Why it matters.** Same shape as `send.js`: anyone on the internet can sign arbitrary businesses up for the production system under arbitrary names and emails. Spam, fake-trial abuse, and corrupted CRM data. `phone` is forwarded as-is with no format validation.

**Fix.** Same shape as #1. In addition, the production endpoint almost certainly wants CSRF/origin enforcement; passing `Origin: *` along is not helpful. Tighten the CORS allowlist.

---

### 3. **P0** — `backend/supabase/functions/redirect/index.ts` is an unauthenticated open-redirect link shortener

**Evidence:**
- `backend/supabase/functions/create-link/index.ts:18-32` — accepts `{ phone, message, email }`, constructs a `wa.me/...` URL, stores it in `short_links` with no auth, no origin check, no destination validation.
- `backend/supabase/functions/redirect/index.ts:24-32` — looks up `destination_url` by `slug` and `Response.redirect(...)`.

**Why it matters.** The combination of unauthenticated write and unchecked destination means a malicious actor can:
- Store a URL pointing at any phishing site, malware, or competitor.
- The `slug` is a 5-char `nanoid` — ~60M possible values, not brute-forceable, but the *creator* gets a public short link on `mybijou.xyz/l/<slug>` and can share/embed it. Visitors see a `mybijou.xyz` URL and click through to the attacker's destination.
- Brand abuse and Meta domain-trust damage (if reported to Meta as a phishing vector, the `mybijou.xyz` brand itself gets flagged).

**Fix.**
1. Require an auth header on `create-link` (e.g. founder's verified email JWT).
2. On `redirect`, validate that `destination_url` starts with `https://wa.me/` or `https://api.whatsapp.com/` — reject everything else.
3. Add a kill-switch: if `owner_email` is empty, the row cannot be created.
4. Move short links off the marketing domain (`bijou-landing` should not be the canonical shortener) or behind the production app's auth.

---

### 4. **P0** — `schema.sql` enables RLS on `leads` with zero policies

**Evidence:** `backend/schema.sql:103-104`
```sql
-- 5. Row Level Security (RLS) Policies
alter table leads enable row level security;
```

No `CREATE POLICY` statements anywhere. `short_links` and `link_clicks` are created with RLS disabled.

**Why it matters.** With RLS enabled and no policies, *all* operations from anon/authenticated clients are denied. The API works today only because every Supabase client is created with the **service role** key, which bypasses RLS. This is defense-in-depth completely absent: there is no second layer between the internet and the `leads` table. If a future code change ever uses the anon key (e.g. for client-side reads), the entire app will silently fail with a vague 401. If the service role key is leaked (e.g. via a misconfigured `VITE_*` env var — see #9), an attacker has *full* DB access with no policy constraint.

**Fix.**
1. Add policies for every operation: `INSERT` for anon (lead capture), `SELECT` for service-role only, `UPDATE` for service-role only.
2. Add a `read_leads` policy for an admin role if founder wants dashboard access.
3. Document the bypass behavior in a code comment at the top of every `createClient` call.

---

### 5. **P1** — No rate limiting on any `/api/*` endpoint

**Evidence:** `api/leads.js`, `api/slide-deck.js`, `api/voice-waitlist.js`, `api/spots.js`, `api/send.js`, `api/onboarding/signup.js`, `api/chat.js` — none of them have any throttling, IP-bucketing, captcha, or even a basic in-memory counter.

**Why it matters.**
- `slide-deck.js` and `voice-waitlist.js` send Resend emails on every call. A 10-line `for` loop in a browser tab can exhaust a Resend free-tier quota in seconds; paid overage kicks in.
- `leads.js` writes to Supabase. Repeated inserts bloat the `leads` table and (if you add a unique-email constraint) cause "23505 duplicate" log spam.
- `chat.js` proxies to the AI gateway — even at $0.001/call, 1M calls = $1000.
- The attack surface for Resend is amplified by the 5 different emails sent per `leads` call (confirmation + owner notify + manual DB update email_sent_at), so a single API hit is *5 emails*.

**Fix.** Add a 1-minute, 10-requests-per-IP in-memory map keyed on `req.headers['x-forwarded-for'] || req.socket.remoteAddress` in each handler. Better: route through Vercel Edge Middleware with a Redis-backed bucket so rate limits span function instances. Add Cloudflare Turnstile (free) on the lead forms.

---

### 6. **P1** — `Access-Control-Allow-Origin: *` on every POST endpoint

**Evidence:**
- `api/chat.js:5`
- `api/leads.js:203`
- `api/slide-deck.js:147`
- `api/voice-waitlist.js` (no CORS headers set — preflight fails for cross-origin)
- `api/send.js:6`
- `api/onboarding/signup.js:6`
- `api/spots.js:6`

**Why it matters.** Even after #1 and #2 add auth, the wildcard CORS means a successful attack from `evil.com` to the lead pipeline can ride a logged-in user's browser (CSRF) — and since there's no Origin/Referer check, an attacker can trigger leads/waitlist signups under any victim's identity if combined with the right attack chain. Wildcard CORS on credentialed POSTs is the canonical anti-pattern.

**Fix.** Echo the request's `Origin` only if it matches an allowlist (`https://mybijou.xyz`, `https://app.mybijou.xyz`, `https://staging.mybijou.xyz`). Or remove the CORS header entirely and rely on same-origin for the public site; only add CORS if you actually need cross-origin callers.

---

### 7. **P1** — `vercel.json` security headers are incomplete

**Evidence:** `vercel.json:25-43`
```json
"X-Content-Type-Options": "nosniff",
"X-Frame-Options": "DENY",
"X-XSS-Protection": "1; mode=block"
```

**Why it matters.** Three headers, all from the 2010 era. Missing the modern pillars:
- No `Content-Security-Policy` — defense-in-depth against any XSS (the import map and inline scripts in `index.html` make this especially important).
- No `Strict-Transport-Security` — first-load downgrade risk.
- No `Referrer-Policy` — leaks full URLs to third-party analytics/social.
- No `Permissions-Policy` — camera/mic/geolocation/etc. are not denied by default.
- `X-XSS-Protection: 1; mode=block` is **deprecated and can introduce vulnerabilities** in older Chrome and Edge builds (CVE-2018-12148 family). Modern browsers ignore it; only IE and old Safari respect it.

**Fix.** Replace with:
```json
"Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
"Content-Security-Policy": "default-src 'self'; script-src 'self' https://www.googletagmanager.com https://cdn.tailwindcss.com 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://ai-gateway-bufxd.sprites.app https://lrwzlujomukzjykafmic.supabase.co https://bijou-production.fly.dev; frame-ancestors 'none'; base-uri 'self'; form-action 'self' https://wa.me https://cal.com",
"Referrer-Policy": "strict-origin-when-cross-origin",
"Permissions-Policy": "camera=(), microphone=(), geolocation=()",
"Cross-Origin-Opener-Policy": "same-origin",
"Cross-Origin-Embedder-Policy": "require-corp"
```
Remove `X-XSS-Protection`.

---

### 8. **P1** — The "30-day money-back" promise is contradicted by "14 days free" in three user-facing surfaces

**Evidence:**
- Promise: `api/chat.js:47` ("30-day money-back guarantee"), `api/leads.js:170` ("30-day money-back"), `i18n.ts:48` ("30-day money-back guarantee"), `FinalCTA.tsx:32,161`, `InfoModal.tsx:200,206`, `FAQ.tsx:132`, `README.md:59,235`, `manifest.json` (shortcut "Start Free Trial" doesn't specify).
- Counter-claim: `OnboardingModal.tsx:434` (`"14 days free • No credit card • Cancel anytime • Set up in 5 minutes"`), `api/slide-deck.js:94` (`"14 days free, no credit card needed. Set up in under 5 minutes"`), `SlideDeckModal.tsx:85` (`"14 days free · No credit card · 5-min setup"`).
- Compounding: `i18n.ts:81` has EN key `"pricing.cta.trial": "Start 30-Day Trial"` but `OnboardingModal.tsx:770` (and its `getModalTitle/getModalSubtitle`) never use that key.

**Why it matters.** A lead who reads the slide-deck email ("14 days free") and then asks for a refund on day 25 will be told "actually it's 30 days" — but their paper trail says 14. Beyond the customer-support pain, in Malaysia this is potentially actionable under the Consumer Protection Act 1999 (misleading representation). For a 30-day-money-back vs free-trial distinction, this also creates a coherent attack: sign up, use for 25 days, claim the email promised only 14 days free, demand full refund + compensation.

**Fix.** Pick one model and apply it consistently. If 30-day money-back is the policy, replace every "14 days free" string with the i18n-keyed 30-day copy. If a 14-day free trial is the policy, update the FAQ, InfoModal, and lead-confirmation email to say so.

---

### 9. **P1** — `VITE_GEMINI_API_KEY` is named with the `VITE_` prefix but used as a server-side secret

**Evidence:**
- `api/chat.js:139` reads `process.env.VITE_GEMINI_API_KEY` as a fallback if the gateway is down.
- `vite.config.ts:17-19` uses `loadEnv(mode, '.', '')` (the empty prefix loads **all** env vars, not just `VITE_*`) and only `define`s `VITE_PUBLIC_SITE_URL` and `NODE_ENV`. So today, `VITE_GEMINI_API_KEY` is **not** leaked to the client bundle — but the convention is a footgun.
- `vite.config.ts` comment on line 13 reads `// SECURITY: API keys moved to backend proxy - no client exposure` — author is aware.

**Why it matters.** Any future change to `vite.config.ts` that uses `define` to expose more env vars, or any code that reads `import.meta.env.VITE_GEMINI_API_KEY` (the natural Vite convention for that prefix), will silently ship the Gemini key to every visitor's browser. Vite's docs explicitly say `VITE_*` is for client exposure.

**Fix.** Rename all `VITE_*` env vars that hold secrets to remove the `VITE_` prefix (`GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `RESEND_API_KEY`, etc.). Reserve `VITE_` for vars the client genuinely needs. The `loadEnv` in `vite.config.ts` should also pass the empty string only if there's a documented reason; otherwise restrict to `VITE_` to enforce the contract.

---

### 10. **P1** — `HowItWorks.tsx:100` still markets a "4-Agent Empathy Pipeline" that doesn't exist in code

**Evidence:** `components/HowItWorks.tsx:100`
> "Standard chatbots use one brain. Bijou uses four distinct agents to process every message, increasing conversion by 41%."

`api/chat.js` actual flow: a single `fetch` to the gateway or Gemini, no multi-agent orchestration. `services/tools.ts` is a console-logging mock. The CHANGELOG entry for v5.0.0 (line 18) admits: "Removed 'Unique to Bijou' and 'TRACE Empathy Engine — Live Now' branding" — but this section was not updated.

**Why it matters.** The "41% conversion lift" claim is not substantiated by any code, telemetry, or A/B test in the repo. If a journalist or competitor calls it out, or if MDEC/Cradle verify the marketing claims during a grant audit, this is a real exposure. PDPA-adjacent: "increasing conversion by 41%" presented as fact without disclosure is a representation claim.

**Fix.** Either (a) build the actual 4-agent pipeline (Detection → Empathy → Logic → Closing) as separate LLM calls in `api/chat.js` and instrument the conversion metric, or (b) replace the headline with honest copy like "One fast LLM with smart handover when complexity exceeds threshold" (which is what `Features.tsx:241` already does correctly).

---

### 11. **P1** — `DemoChat.tsx:20` opening message violates the system's own Manglish rules

**Evidence:**
- The hardcoded opening message in `components/DemoChat.tsx:20`:
  > "First time we meet — boleh tahu your name?"
- The system prompt in `api/chat.js:32` and `api/chat.js:97`:
  > "NEVER use 'boleh tahu' (sounds stiff and unnatural)."
  > "Never say 'boleh tahu' (too formal, unnatural in WhatsApp)"

**Why it matters.** The very first sentence a user sees contradicts the documented persona rules the founder hand-curated. The chat also has the model specifically trained to *not* say "boleh tahu", so users will see a stylistic mismatch between the opening (formal) and every subsequent reply (Manglish-natural). This is the canonical "demo vs reality" smell that kills conversion.

**Fix.** Change the opening to: `"First time we meet — nama you apa ah?"` or `"Eh hello boss! First time kita chat — boleh I know your name?"` (matching the system prompt's allowed variants).

---

### 12. **P1** — `public/brand/1.png`–`12.png` total 52.8 MB and are never referenced

**Evidence:**
- `public/brand/` directory contains 1.png, 2.png, … 12.png, each 3-5 MB, plus `BIJOU-LOGO-TRANSPARRENT.png` (3.6 MB) and `logo.png` (3.6 MB, identical content).
- `dist/brand/` is the same 52.8 MB tree — confirms they get shipped to Vercel.
- Repo-wide grep for `/brand/(1|2|...|12).png` returns zero hits. The only `brand/` references are `logo.png` and `qr.png`.

**Why it matters.**
- Slow Vercel cold-build (52 MB extra to upload, untar, serve).
- 53 MB repo clone for every new contributor / CI runner.
- Wasted bandwidth on every page load (browser doesn't fetch them, but the deploy artifact bloat is real).

**Fix.** Delete `public/brand/{1..12}.png` and `dist/brand/{1..12}.png`. If they belong to a planned feature, move them to `Docs/` (already gitignored) or a `/_archive/` branch.

---

### 13. **P1** — PWA install experience is broken

**Evidence:**
- `index.html:86,90,95,100,104` references `/icons/icon-192x192.png` and `/icons/icon-152x152.png`.
- `public/icons/` directory contains **only** `icon-base.svg` (1.1 KB).
- `public/manifest.json:13-30` lists three icon entries, all pointing to `/favicon.png` with sizes `192x192` and `512x512`. `/favicon.png` is the 32×32 favicon.
- `public/manifest.json:34-50` shortcuts also point to `/favicon.png` for 96×96.

**Why it matters.** On Android Chrome, the "Install app" prompt shows the 192/512 manifest icon — here, a stretched 32×32 favicon. On iOS, the apple-touch-icon path 404s, so the home-screen icon is a missing-image placeholder. The PWA appears unprofessional at the exact moment a user is deciding to install.

**Fix.** Generate real 192×192, 512×512, and 180×180 PNGs from `public/icons/icon-base.svg`, place in `public/icons/`, update `manifest.json` icon entries and `index.html` `<link rel="apple-touch-icon">` paths. Run `npx pwa-asset-generator` once and check in the result.

---

### 14. **P1** — Vercel rewrite sends `/privacy` (and every non-`/brand/...` path) to the SPA, with no router

**Evidence:** `vercel.json:8-15`
```json
"rewrites": [
  { "source": "/brand/(.*)", "destination": "/brand/$1" },
  { "source": "/((?!brand/).*)", "destination": "/index.html" }
]
```

`components/LeadCaptureForm.tsx:286` links to `/privacy` (relative). `components/Footer.tsx:218-231` opens a modal that should show privacy/terms, but it relies on `InfoModal` being open — and the `href="/privacy"` is *not* in the footer; the footer uses buttons that open modals. But the lead form's hardcoded `/privacy` link will hit the rewrite and render the landing page.

**Why it matters.** PDPA requires a working Privacy Policy link. The lead form's relative `/privacy` link is broken.

**Fix.** Either (a) make the link absolute (`https://mybijou.xyz/privacy`) and host a static privacy HTML page under `public/privacy/`, or (b) make the link trigger the same modal the footer uses (lift `InfoModal` state up or use a context).

---

### 15. **P1** — `dist/` is committed at 53.75 MB

**Evidence:** `dist/index.html`, `dist/assets/index-Bpk0eoNL.js` (688 KB), `dist/brand/*.png` (52.8 MB), etc. `.gitignore:11` lists `dist` but the directory is checked in.

**Why it matters.**
- Vercel builds the project from source — it doesn't need the dist tree.
- Every `git clone` is 53 MB heavier than it needs to be.
- The deploy artifact on Vercel is fine (Vercel rebuilds), but the in-repo artifact is pure waste.

**Fix.** `git rm -r dist && echo "dist/" >> .gitignore && git commit -m "Stop tracking dist/"`. If `dist/` was ever meant to be deployable from a different system, that's a separate concern — the build command in `vercel.json` is `npm install && npm run build`, which produces a fresh dist.

---

### 16. **P2** — Env-var typo `CUSTOME_API_ENDOINT` (should be `CUSTOM_API_ENDPOINT`)

**Evidence:** `api/chat.js:96` reads `process.env.CUSTOME_API_ENDOINT`. `.env` line 27 sets `CUSTOME_API_ENDOINT=https://ai-gateway-...`. Both files have the same typo, so it works — until one is fixed and the other isn't.

**Fix.** Rename to `CUSTOM_API_ENDPOINT` in both files in the same commit. The AI gateway endpoint is also the type of thing that should probably live in code (not env), since it's not a secret.

---

### 17. **P2** — `CalBooking.tsx:18` uses `process.env.VITE_PUBLIC_CAL_USERNAME` in browser code

**Evidence:** `components/CalBooking.tsx:18`
```ts
const calUsername = process.env.VITE_PUBLIC_CAL_USERNAME || 'getbijou';
```

Vite's runtime resolves `import.meta.env.VITE_*` at build time. `process.env.VITE_*` in a Vite-bundled browser module is `undefined` (Vite only sets `process.env.NODE_ENV` via `define` in this config). Today it works only because the hardcoded fallback `'getbijou'` is what would be used anyway. If someone renames the Cal.com user, they'll set the env var, the code still won't pick it up, and they'll wonder why.

**Fix.** Either:
```ts
const calUsername = import.meta.env.VITE_PUBLIC_CAL_USERNAME || 'getbijou';
```
Or remove the env-var indirection entirely (the value is not a secret — it's literally a public URL slug).

---

### 18. **P2** — i18n claim in `CLAUDE.md` is wrong (4 langs, not 5)

**Evidence:**
- `CLAUDE.md` says: "all translation resources inline for 5 languages (EN, BM, Manglish, ZH, TA)".
- `i18n.ts:7,316,635,934` defines exactly four top-level resources: `en`, `ms`, `zh`, `ta`.
- `ms` is formal Bahasa Melayu (e.g. `Ciri-ciri`, `Mulakan`, `Wang dikembalikan dalam 30 hari`), not Manglish.
- No "Manglish" language block exists.

**Why it matters.** Documentation drift. A new contributor will go looking for the Manglish block and waste time.

**Fix.** Either (a) actually add a `manglish` resource block (with the en Manglish substitutions: "Ciri-ciri" → "Features we got", etc.) and update `LanguageSwitcher.tsx` to expose it, or (b) edit `CLAUDE.md` to say "4 languages: EN, MS (formal BM), ZH, TA — Manglish is rendered inline by the LLM via the system prompt, not the i18n catalog".

---

### 19. **P2** — 28/37 components don't use `useTranslation`

**Evidence:** Survey of `useTranslation` and `t(...)` calls:
- Files with `t()`: CaseStudies, ComparisonTable, EnterpriseContactForm, Features, Hero, IntegrationForm, PartnershipForm, Pricing, WaitlistStrip — **9 files**.
- Files without: App, CalBooking, DemoChat, FAQ, FinalCTA, Footer, HowItWorks, InfoModal, LanguageSwitcher, LeadCaptureForm, LeadCaptureModal, Navbar, OnboardingModal, PainSection, Playbooks, PWAInstallPrompt, RevenueCalculator, Roadmap, SetupGuide, SlideDeckModal, Story2amProperty, StoryLunchRushClinic, TrustSection, ViralPillars, VoiceComingSoon, WhatsAppCTA, WhatsAppLinkGenerator, Icons — **28 files**.

**Why it matters.** The i18n catalog is beautifully maintained (238 keys × 4 languages, 0 dupes, 0 missing), but most of the user-facing surface is hardcoded English. A user who switches to `zh` will see Hero/Pricing/CaseStudies/Features translated, but the FAQ, Footer, HowItWorks, modals — all in English. The "language switcher" is effectively a façade.

**Fix.** Either accept that the site is English-only and remove `i18n.ts` (saves 85 KB of bundle weight), or commit to translating the remaining 28 components. Recommended: do the latter incrementally; the Navbar and Footer are 30 min each.

---

### 20. **P2** — 51 unused i18n keys add dead weight to the bundle

**Evidence:** Survey of `i18n.ts` keys vs. components' `t()` references. Examples of unused:
- `nav.features`, `nav.pricing`, `nav.enterprise`, `nav.getStarted` — defined but Navbar doesn't translate.
- `pricing.starter.*`, `pricing.professional.*`, `pricing.enterprise.*` — full dead tiers (kept "for rollback reference" per a comment in `Pricing.tsx:585`).
- `footer.company`, `footer.contact`, `footer.madeBy`, `footer.product`, `footer.rights`, `footer.tagline` — defined but Footer doesn't translate.

**Why it matters.** ~21% of the 85 KB i18n file is dead. The `pricing.starter.*` block alone is ~25 keys × 4 languages = 100 unused key/string pairs.

**Fix.** Either delete the dead keys, or use them. The "kept for rollback" justification is poor — git history preserves them.

---

### 21. **P2** — `OnboardingModal.tsx` demo flow makes two separate API calls

**Evidence:** `components/OnboardingModal.tsx:316-340` — the demo flow:
1. POSTs to `/api/leads` (saves lead, no `demo_time` field).
2. POSTs to `/api/send` (sends WhatsApp notification to founder, includes `demo_time`).

**Why it matters.** If the second call fails or the open proxy is fixed to require auth (see #1), the demo booking is silently broken — the lead is saved but the founder never gets the demo time. There's no retry, no queue.

**Fix.** Combine the two calls into a single `POST /api/demo` endpoint that owns both responsibilities, and surface a single error to the user.

---

### 22. **P2** — `AGENTS.md` is stale

**Evidence:** `AGENTS.md:88-92` lists "Large Components (>200 lines)": `WhatsAppLinkGenerator.tsx (479 lines)`, `ViralPillars.tsx (468 lines)`, `Playbooks.tsx (212 lines)`, and `DemoChat.tsx (183 lines)`. Actual current sizes:
- `WhatsAppLinkGenerator.tsx`: 480 lines ✓
- `ViralPillars.tsx`: 648 lines ✗
- `Playbooks.tsx`: 212 lines ✓
- `DemoChat.tsx`: 286 lines ✗

Also: `AGENTS.md:113` says "API_KEY required for Google GenAI integration" — but the codebase now uses `CUSTOME_API_KEY` + `CUSTOME_API_ENDOINT` (the OmniRoute gateway) per `api/chat.js:96-100`. The "Mock responses available when API key not configured" pattern no longer exists.

**Why it matters.** New contributors rely on AGENTS.md for context; wrong sizes and outdated architecture notes send them down wrong paths.

**Fix.** Update `AGENTS.md` to match the current architecture, or delete it and rely on `CLAUDE.md` (which is more current).

---

### 23. **P2** — `index.html` has a dead `<script type="importmap">` block

**Evidence:** `index.html:265-280` defines an import map for `@google/genai`, `framer-motion`, `react`, etc. The actual entry point is `/index.tsx` (line 282), which is bundled by Vite. Vite's bundle doesn't honor import maps.

**Why it matters.** Harmless but signals confusion about how the build works. Suggests there was a period where the app was loaded directly from esm.sh without a build step.

**Fix.** Delete the import map block. If you want a no-build fallback, the rest of the build needs to change too (and you'd need to remove the bundler-mode TS config).

---

### 24. **P2** — `.opencode/` directory is in the repo but the founder says it's "not required"

**Evidence:** `CLAUDE.md:55-57` says: "`.opencode/` contains an OpenCode multi-agent setup … not required for working in this repo, but useful business/founder context if a task needs it." The directory contains 30+ files (agent definitions, slash commands, JEWEL_PROFILE.md, MASTER_CONTEXT.md). `.gitignore:46-47` only excludes `.opencode/node_modules` and `.opencode/bun.lock`.

**Why it matters.** Repo bloat. The `.opencode/` files are tool-specific configuration for a different agent system; they should be local to a developer's machine, not a shared artifact. Anyone who isn't using OpenCode has to scroll past them.

**Fix.** Either add `/.opencode/` to `.gitignore` (move it to a separate repo) or accept that it's part of the public repo (and add a top-level `OPENCODE.md` that points to it).

---

### 25. **P2** — Stray `bijou-site-fixed.png` and `metadata.json` at repo root

**Evidence:** `bijou-site-fixed.png` (162 KB, an unexplained screenshot) and `metadata.json` (`{"name": "Bijou AI - Digital Employee", "requestFramePermissions": []}`) at the repo root, not gitignored.

**Why it matters.** Repo bloat; `metadata.json` looks like it was left over from a Lovable/Bolt.new export.

**Fix.** Delete both. If `bijou-site-fixed.png` documents a layout, move it to `Docs/` (gitignored) or check in a smaller version.

---

### 26. **P2** — `vite.config.ts` has redundant `process.env.NODE_ENV` define

**Evidence:** `vite.config.ts:15`
```ts
'process.env.NODE_ENV': JSON.stringify(mode),
```

Vite sets this automatically. Defining it manually is redundant and slightly surprising.

**Fix.** Remove the line. The `mode` argument already flows to Vite's built-in NODE_ENV handling.

---

### 27. **P2** — `npm audit` reports 7 known vulnerabilities (1 critical, 1 high, 5 moderate)

**Evidence:** `npm audit --omit=dev` output:
- **CRITICAL** `protobufjs` (`<=7.6.2`, CVE-2024-XXXX, "Arbitrary code execution") — transitive via `@google/genai` and `@supabase/supabase-js`.
- **HIGH** `ws` (`8.0.0 - 8.20.1`, "Uninitialized memory disclosure" + "Memory exhaustion DoS") — transitive via Vite dev server.
- **MODERATE** `@protobufjs/utf8`, `brace-expansion`, `uuid` (via `svix` via `resend`), `svix`.

**Why it matters.** Most are dev-only or unreachable at runtime, but the `protobufjs` RCE is concerning if any untrusted protobuf message hits the runtime. `ws` affects dev server stability.

**Fix.** `npm audit fix` to pick up the patch versions. For the protobufjs critical: pin the major of `@google/genai` or `@supabase/supabase-js` to a version that has the patched transitive dep, OR add a `pnpm`/`npm` `overrides` block forcing `protobufjs@>=7.5.5`.

---

### 28. **P2** — `OnboardingModal.tsx:283-291` — duplicate "name or company" validation already exists server-side

**Evidence:**
- Client: `OnboardingModal.tsx:171-204` — validates `business_name` length ≥ 2, email format, phone length.
- Server: `api/leads.js:224-243` — validates email regex and "name or company required".

**Why it matters.** Not a bug, but the two regexes for email differ:
- Client: `email.includes("@") && email.includes(".")` (very loose).
- Server: `/^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]+$/` (RFC-ish but accepts `a@b.c`).

**Fix.** Centralize the email validation in a `utils/validators.ts` module, import in both client and server. Same for phone.

---

### 29. **P2** — `HowItWorks.tsx` and other components spam `console.*` in production

**Evidence:** `components/HowItWorks.tsx:67-83` runs a `console.group()` + 7 `console.log` calls in a `useEffect` on every page load. Other offenders: `CalBooking.tsx:2`, `EnterpriseContactForm.tsx:2`, `IntegrationForm.tsx:2`, `OnboardingModal.tsx:2`, `PartnershipForm.tsx:2`, `PWAInstallPrompt.tsx:1`, `WhatsAppLinkGenerator.tsx:1`. Total: 19 `console.*` calls across the frontend bundle.

**Why it matters.** Browser devtools noise; trace "simulator" log in `HowItWorks` was kept "for demo purposes" but the demo never starts unless you scroll to the section.

**Fix.** Wrap dev-only logs in `if (import.meta.env.DEV)`. Or remove the HowItWorks TRACE simulator entirely (it contradicts the "no fake pipeline" copy in Features.tsx:241).

---

### 30. **P2** — `tsconfig.json` excludes `api/**` and `backend/**` from type-checking

**Evidence:** `tsconfig.json:21-22`. Combined with the file extensions `.js` (api) and `.ts` running under Deno (backend).

**Why it matters.** The `api/*.js` files are the most security-critical code in the repo and are not type-checked at all. JSDoc with `@param` would help; bare JS doesn't.

**Fix.** Add JSDoc type annotations to `api/*.js` so `tsc --noEmit --allowJs --checkJs` covers them. Or migrate to `.ts` and let Vercel transpile.

---

### 31. **P2** — Stale "500+ Malaysian SMEs" social proof claim

**Evidence:** `manifest.json:5`, plus the `WaitlistStrip` claim (per CHANGELOG Fix 3, the founder already walked this back to "Built in KL. Made for Malaysian SMEs"). The new honest copy is in the components; the manifest still says "500+ Malaysian SMEs" indirectly via the description.

**Why it matters.** Inconsistent.

**Fix.** Update `manifest.json:5` to remove the "500+" claim.

---

### 32. **P2** — `importmap` in `index.html` is dead code

**Evidence:** `index.html:265-280`. Already noted in #23.

**Fix.** See #23.

---

### 33. **P2** — Email-validation regex too permissive

**Evidence:** `api/leads.js:227` — `/^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]+$/`. Accepts single-char TLDs (`a@b.c`).

**Why it matters.** Minor. Real-world RFC 5321/5322 is much more permissive; the practical fix is to enforce a minimum TLD length and run an MX lookup. For a lead capture, sending to a known-bad address wastes a Resend quota slot.

**Fix.** Use a vetted library (e.g. `validator.js`'s `isEmail`) or `zod`'s `.email()`.

---

### 34. **P2** — `tsconfig.json` has no `strict: true`

**Evidence:** `tsconfig.json` is missing `"strict": true` and several sub-flags (`noImplicitAny`, `strictNullChecks`, etc.).

**Why it matters.** `tsc --noEmit` will not catch a wide class of bugs. The codebase has at least 8 `any` usages in catch blocks (`LeadCaptureForm.tsx:118`, `OnboardingModal.tsx:85,400`, etc.) — a stricter config would force these to `unknown` and force proper narrowing.

**Fix.** Add `"strict": true`, `"noUncheckedIndexedAccess": true`, `"exactOptionalPropertyTypes": true` to `tsconfig.json`. Fix the resulting errors.

---

### 35. **P2** — `vercel.json` SPA rewrite allows `/brand/...` passthrough but the dist already mirrors `public/`

**Evidence:** `vercel.json:9-10` keeps `/brand/(.*)` as a static passthrough. The `dist/brand/` directory duplicates `public/brand/`. Vercel serves `dist/` after build, so the rewrite doesn't actually do anything different.

**Why it matters.** Dead config that suggests there's a deployment model where the SPA is served from a different root than the assets.

**Fix.** Remove the `/brand/(.*)` rewrite (it's a no-op after the `((?!brand/).*)` catch-all sends everything else to index.html).

---

### 36. **P2** — `services/tools.ts` imports `@google/genai` only for the type

**Evidence:** `services/tools.ts:1` — `import { FunctionDeclaration, Type } from "@google/genai";`. The `ToolOrchestrator` console-logs; the type is unused at runtime (the server-side proxy in `api/chat.js` doesn't accept or invoke tools).

**Why it matters.** Dead code; ships a 200+ KB `google-genai` SDK to the client even though the only function (`sendEmail`) is a mock.

**Fix.** Either (a) wire tools through the server proxy (genuine value), or (b) delete `tools.ts` and its import. The current state ships dead code in the bundle.

---

### 37. **P2** — `VoiceComingSoon.tsx:88-97` catches and shows success on any error

**Evidence:**
```ts
try { await fetch('/api/voice-waitlist', ...); if (response.ok) setSubmitted(true); }
catch { setSubmitted(true); }  // <-- success on network error
setSubmitting(false);
```

**Why it matters.** If the user is offline or the endpoint is down, they see "You're on the list!" even though nothing was sent. They'll never get the launch email and never know. Combined with #5 (no rate limiting) this could mask an outage.

**Fix.** Distinguish "submitted to server" from "optimistic UI". Add a `failed` state with a "Try again" button.

---

### 38. **P2** — `OnboardingModal.tsx:434` hardcodes "14 days free" — out of sync with i18n

**Evidence:** Already covered in #8.

**Fix.** Replace the hardcoded strings with i18n keys.

---

### 39. **P2** — `index.html` load order: Tailwind CDN is render-blocking

**Evidence:** `index.html:131` — `<script src="https://cdn.tailwindcss.com"></script>` is a synchronous load with no `defer`/`async`. The CDN script then runs `tailwind.config = {...}` (line 134) inline.

**Why it matters.**
- Render-blocking script on every page load.
- Tailwind CDN is explicitly **not for production** per Tailwind's own docs.
- If the CDN is blocked (e.g. in mainland China, which is a non-zero fraction of Malaysian users on certain ISPs), the page renders unstyled.

**Fix.** Set up a real Tailwind/PostCSS build with `@tailwindcss/postcss` (or the v4 `npx tailwindcss` CLI). Drop the CDN.

---

### 40. **P2** — `OnboardingModal.tsx` has the largest god-file in the repo (810 lines)

**Evidence:** `components/OnboardingModal.tsx` is 810 lines, holding form state, three flow modes (signup/waitlist/demo), error mapping, animated progress, marketing copy, and the leads + WhatsApp notification flow.

**Why it matters.** Hard to test, hard to review. Any of the 36 changes from CHANGELOG v5.0.0 likely touched this file.

**Fix.** Split into:
- `OnboardingModal.tsx` (UI shell, AnimatePresence)
- `useOnboardingFlow.ts` (state machine: idle → loading → success → error)
- `LeadFormFields.tsx` (the inputs)
- `errorMapping.ts` (the createErrorState helper)

---

## What's good

These are real, not just "well, the code runs":

- **i18n catalog is genuinely well-built.** 4 languages × 238 keys, 0 duplicate keys, 0 missing translations. The `t()` calls in components reference only keys that exist (`scripts/i18n_unused.py` confirms). Whoever maintains this treats i18n as a first-class concern, not a translation-memory afterthought.
- **The Vite config is properly hardened.** `loadEnv` is used, but only `VITE_PUBLIC_SITE_URL` is exposed via `define`. Despite the confusing `VITE_*` prefix on env vars, no Gemini key is in the client bundle. (See #9 for the footgun risk, but the current state is safe.)
- **The demo chat is correctly wired through the serverless proxy.** `services/gemini.ts` calls `/api/chat`; no client-side Gemini key. The Manglish persona is a single, findable string in `api/chat.js` — easy to evolve without touching the frontend.
- **The AI gateway fallback chain is clever.** `api/chat.js:97-159` tries `auto/best-fast` → `antigravity/gemini-2.5-flash` → `cc/claude-haiku-4-5`, then falls back to direct Gemini with rotation keys. Free-first, paid-behind.
- **PWA service worker is appropriately scoped.** `public/sw.js` registers only in non-localhost, uses network-first for `/api/*` (correct — never cache POSTs), cache-first for static. The `beforeinstallprompt` handler in `index.html` is wired to `window.installBijouPWA` and `PWAInstallPrompt.tsx` consumes it. (The icon paths are broken — see #13 — but the wiring is correct.)
- **The "always return 200 with Manglish response" pattern is intentional and well-documented in `CLAUDE.md`.** It's a UX choice (don't break the demo on a transient error) not a negligence, and the error path includes a warning to contact WhatsApp support. The downside is that it masks real failures from the founder's monitoring (see #5).
- **`.gitignore` is comprehensive.** Covers env, dist, node_modules, OS files, IDE files, internal docs, email-templates. The only thing missing is `bijou-site-fixed.png` and `metadata.json` (see #25).
- **Form validation is layered.** Client-side (LeadCaptureForm, OnboardingModal) and server-side (`api/leads.js`, `api/slide-deck.js`). Both check email format, name length, and required fields.
- **The honest-copy CHANGELOG discipline is exemplary.** v5.0.0 (CHANGELOG.md:5-66) documents the founder walking back "9,201 savings", "Unique to Bijou", "500+ Malaysian SMEs" claims and adding clarifying copy. This is the right instinct.
- **Component composition is clean.** Prop-drilling is shallow (max 2 levels for `onOpenModal`), no global store, no Redux. The modal state pattern in `App.tsx:32-44` is plain `useState` + callback, which is the right call for a 37-component single-page app.
- **The service-worker `manifest.json` has a working `protocol_handlers` and `shortcuts` block.** A nice touch for PWA polish (when icons are fixed).

---

## Risk register

| # | Risk | Likelihood | Impact | Evidence |
|---|------|-----------|--------|----------|
| 1 | **Open WhatsApp proxy** — `api/send.js` is unauthenticated and can be used to mass-harass Malaysian numbers under the Bijou brand → Fly.io account suspension, Meta WA ban, brand damage | High (low-effort, internet-wide) | Critical | `api/send.js:1-66` |
| 2 | **Open-redirect link shortener** — `redirect/index.ts` allows phishing links on `mybijou.xyz/l/...` → brand abuse, Meta domain flagging | High (any user can create) | High | `backend/supabase/functions/redirect/index.ts:24-32` |
| 3 | **RLS enabled, no policies** — `leads` table is one env-var typo away from total compromise or total lockout | Medium (latent) | Critical | `backend/schema.sql:103-104` |
| 4 | **No rate limiting on email-sending endpoints** — Resend quota exhaustion in minutes; $$$ overage; account suspension; email-domain reputation damage | High | High | `api/slide-deck.js`, `api/voice-waitlist.js`, `api/leads.js` |
| 5 | **"30-day" vs "14-day" trial claim mismatch** — consumer-protection exposure in MY + support pain | Medium (during support interactions) | Medium (legal/support cost) | `OnboardingModal.tsx:434` vs `i18n.ts:48` |

---

## Concrete next steps

### 30 days (P0 + P1 must-fix)

- [ ] **Add auth to `api/send.js` and `api/onboarding/signup.js`** (server-side shared-secret header; restrict CORS to `https://mybijou.xyz`/`https://app.mybijou.xyz`; whitelist `to` field). If the lead owner-notify path needs to call `/api/send` server-to-server, do it directly to Fly.io with the secret — don't route through a public endpoint.
- [ ] **Lock down `backend/supabase/functions/{create-link,redirect}`** — require auth on `create-link`; validate `destination_url` is a `wa.me` URL on `redirect`; consider moving the shortener off `mybijou.xyz`.
- [ ] **Add RLS policies to `leads`** in a new migration file (`backend/rls-policies.sql`) covering `INSERT` (anon), `SELECT` (service role), `UPDATE` (service role). Apply via `supabase db push`.
- [ ] **Add rate limiting** to every `/api/*` POST — even a simple in-process LRU keyed on `x-forwarded-for` is better than nothing. Add Cloudflare Turnstile to the public lead forms.
- [ ] **Fix `vercel.json` security headers** — add CSP, HSTS, Referrer-Policy, Permissions-Policy, COOP, COEP. Remove the deprecated `X-XSS-Protection`.
- [ ] **Fix PWA icons** — generate proper 192/512/180 PNGs from `public/icons/icon-base.svg`, place in `public/icons/`, update `manifest.json` and `index.html` `<link>` paths.
- [ ] **Remove `public/brand/{1..12}.png` and the duplicate `BIJOU-LOGO-TRANSPARRENT.png`** — save 52.8 MB.
- [ ] **Reconcile "30-day money-back" vs "14 days free"** — pick one and apply it everywhere; replace hardcoded strings in `OnboardingModal.tsx:434,770` and `slide-deck.js:94` and `SlideDeckModal.tsx:85` with the existing i18n keys.
- [ ] **Fix `DemoChat.tsx:20`** opening message to drop "boleh tahu" (system-prompt-forbidden).
- [ ] **Fix `HowItWorks.tsx:100`** headline to match the actual single-LLM architecture, or build the 4-agent pipeline.
- [ ] **Rename `VITE_GEMINI_API_KEY` → `GEMINI_API_KEY`** (and `VITE_SUPABASE_URL` → `SUPABASE_URL` where used server-side).
- [ ] **Fix the env-var typo `CUSTOME_API_ENDOINT` → `CUSTOM_API_ENDPOINT`** in both `.env` and `api/chat.js:96` in the same commit.
- [ ] **Fix `CalBooking.tsx:18`** — use `import.meta.env.VITE_PUBLIC_CAL_USERNAME` or just hardcode `'getbijou'`.
- [ ] **Stop committing `dist/`** — `git rm -r dist && echo "dist/" >> .gitignore`.
- [ ] **Update `CLAUDE.md`** to remove the "5 languages (Manglish)" claim.
- [ ] **Update `AGENTS.md`** to match the current architecture (gateway, line counts).

### 60 days (P2 polish)

- [ ] **Adopt stricter TypeScript** — `"strict": true`, `"noUncheckedIndexedAccess": true`. Fix the 8 `any` catch-block types. Move `api/*.js` to JSDoc-typed JS (or convert to `.ts`) and add them to `tsconfig.json`.
- [ ] **Replace Tailwind CDN** with a real PostCSS build (`@tailwindcss/postcss` for v4). Drop the CDN script tag.
- [ ] **Translate the remaining 28 components** that don't use `useTranslation`, or remove `i18n.ts` and pick a single language. 21% of the catalog is unused — clean it up.
- [ ] **Split `OnboardingModal.tsx`** (810 lines) into `OnboardingModal.tsx` + `useOnboardingFlow.ts` + `LeadFormFields.tsx` + `errorMapping.ts`.
- [ ] **Centralize email/phone validation** in `utils/validators.ts`, import in both client and `api/*.js`.
- [ ] **Run `npm audit fix`** to clear the protobufjs/ws/brace-expansion advisories; pin overrides for any deps that won't clear via auto-fix.
- [ ] **Add a "no fake pipeline" note to `HowItWorks.tsx`** or actually build the 4-agent orchestration in `api/chat.js`.
- [ ] **Wrap dev-only `console.*` calls** in `if (import.meta.env.DEV)` (or delete the HowItWorks TRACE simulator).
- [ ] **Replace the dead `services/tools.ts`** with a real server-side tool orchestrator, or delete the file (it currently ships a 200+ KB `google-genai` SDK to the client for a single console.log).
- [ ] **Add tests.** `CLAUDE.md` is honest that there are none; this is the single highest-leverage improvement for the next 90 days. Vitest + React Testing Library gets you 80% there for ~half a day of setup.

### 90 days (architecture)

- [ ] **Move the open-proxy endpoints to a separate Vercel project** under a different domain (e.g. `internal.mybijou.xyz`) with CORS locked down to `mybijou.xyz` and an auth header. The public landing repo shouldn't expose server-to-server relays at all.
- [ ] **Move the link shortener** off the public domain. Either use a paid link-shortener service (Bitly, Dub) or run it under `app.mybijou.xyz` behind the founder's auth.
- [ ] **Move the Supabase edge functions** into the production repo (`w3j-bijou-enterprise`), not the marketing repo. The marketing repo should have zero mutable backend state.
- [ ] **Add CSP reporting** — once the CSP is in place, add a `report-uri` to catch violations and start a backlog of inline-script eliminations.
- [ ] **Add observability** — wire Vercel's `waitUntil` + a logging service (Axiom, Logflare) to `api/*.js`. Today, the only way to know the gateway fallback is firing is to read Vercel function logs; the `console.warn`s in `api/chat.js:158,169` are invisible to the founder.
- [ ] **Add a real RAG-backed knowledge base** for the demo chat. The current "Manglish persona + free-form LLM" architecture cannot answer "what's included in the PRO plan" reliably because the system prompt paraphrases the pricing page inconsistently. A small RAG over the i18n catalog and `pricing.*` keys would make the demo actually informative.

---

*Audit produced by static review of the working tree at the time of analysis. All evidence is `file:line` and reproducible. Audit scripts left in `scripts/i18n_audit.py`, `scripts/i18n_unused.py`, `scripts/i18n_usage.py`, `scripts/dep_audit.py` for future re-runs.*
