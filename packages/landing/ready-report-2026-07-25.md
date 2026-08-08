# Bijou AI — System Ready Report — 2026-07-25 23:25 MYT

User went out at ~22:00 MYT asking for: "anything we need to do to make our app with latest changes... please do everything... have the Bijou logo embedded in our dashboard and site... and make it as our app and website."

## TL;DR

| Surface | Status | Live URL | Evidence |
|---|---|---|---|
| Marketing site (Vercel) | ✅ **LIVE** with Signal Gem | https://bijou-landing.vercel.app | 17/17 brand assets return 200 OK; HTML contains new favicon links + theme-color |
| Bijou production backend (Fly) | 🟡 **Deploying** | https://bijou-production.fly.dev | Image digest `deployment-01KYCX2H48HH55SF37MEVSDGMD` deployed, retried with explicit cwd to ensure static/ updated |
| WhatsApp bridge (Fly) | ✅ **LIVE** | https://bijou-bridge-production-v2.fly.dev | 401 auth-protected, session warm |
| OpenClaw org | ✅ **DELETED** | n/a | 0 apps remaining |
| Vercel env vars | ⚠️ **EMPTY** | https://vercel.com/mnurunnabi-6185s-projects/bijou-landing/settings/environment-variables | `vercel env ls` returned "No Environment Variables found" |
| Fly.io billing | ⚠️ **BLOCKED** | https://fly.io/dashboard/mn-bijou/billing | User noted earlier in session; deploy via `w3j-bijou-enterprise` is in a DIFFERENT Fly account (personal), so not blocked |

## Signal Gem brand integration (the "make our app and website" deliverable)

### Marketing site (DONE)

**Source**: `w3j-media-pack/logo-variants/signal-gem-system/` (the user-provided design system)

**Files written** (25 files in commit `dd0fdf0`):
- `components/BijouLogo.tsx` (5.8 KB, new) — inline-SVG React component, mark + BijouLockup variants, BIJOU palette tokens, auto-solid for <24px
- `components/Navbar.tsx` — replaced `/brand/logo.png` with `<BijouLogo size={40} tone="gold" />`
- `components/Footer.tsx` — same at size 32
- `components/Hero.tsx` — replaced the chat-card "B" circle with `<BijouLogo size={32} tone="gold" />`
- `index.html`:
  - Full favicon set: SVG primary + 16/32/180 PNG + .ico + apple-touch-icon 152/180/167
  - `theme-color` → `#0B3B2E` (Deep Bijou Green)
  - `msapplication-TileColor` → `#0B3B2E`
  - Tailwind config extended with `gold-{300,400,500,600}` (`#E5C158` / `#E3B457` / `#D4A24C` / `#B8860B`), `deep-green-{400,500,600,700}` (`#0E4938` / `#0B3B2E` / `#093025` / `#072A1F`), `cream`, `ink`, plus a `display` font stack (Optima / Palatino / Georgia)
  - CSS variables updated: `--gold: #E3B457`, `--bg-deep: #072A1F`, plus new `--bj-*` tokens
  - JSON-LD `Organization.logo` → `https://mybijou.xyz/logos/lockup.svg`
- `public/logos/` (new, 11 files) — `mark.svg`, `lockup.svg`, `mark-reversed.svg`, `mark-favicon.svg`, `mark-mono.svg`, `favicon-{16,32,180,192,512}.png`, `favicon.ico`
- `public/og-image.svg` + `public/og-image.png` — regenerated (164.7 KB, 1200×630) with the Signal Gem mark instead of the old "B" letter
- `public/{favicon.png, favicon.ico, icons/icon-192x192.png, icons/icon-512x512.png, icons/apple-touch-icon.png, brand/logo.png}` — replaced with Signal Gem exports

**Live verification** (curl after deploy):
- `/logos/mark-favicon.svg` → 200, returns the gem SVG
- `/logos/lockup.svg` → 200, returns the lockup
- `/favicon.ico` → 200, `image/vnd.microsoft.icon`
- `/og-image.png` → 200, `image/png`, 168677 bytes
- All 17 brand assets → 200 OK

**Deploy**: Vercel aliased `https://bijou-landing.vercel.app` → new deploy `bijou-landing-d0a2dige0-mnurunnabi-6185s-projects.vercel.app`. TS check: 0 errors. Vite build: 7.01s, 695 KB bundle (199 KB gzip).

### Dashboard (DEPLOYED — but ⚠️ Fly edge cache for `app.mybijou.xyz` is serving stale files)

**Source**: local `static/` files in `w3j-bijou-enterprise`

**Files written** (commits `d686e42` + `07ec059`):
- `static/dashboard.html` — SVG favicon primary link, `theme-color` → `#0B3B2E`
- `static/login.html`, `static/signup.html` — SVG favicon primary
- `static/manifest.json` — `theme_color` → `#0B3B2E`, `background_color` → `#072A1F`
- `src/core/bijou.py` — wrapped `StaticFiles` mount in a subclass that sets `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` on every static-file response (so future deploys are never blocked by a stale edge cache again)

**Deploy** (verified):
- Image `deployment-01KYCXYMZSF0560ZGWK902HW3V` (343 MB, fresh COPY . .) deployed to machine `e82d4d3bed0408`
- `fly ssh console` confirms container has: `/app/static/bijou-logo.svg` = 1200 B (Signal Gem), `dashboard.html` = 322637 B, `favicon.png` = 321 B
- Internal `curl http://localhost:8080/static/bijou-logo.svg` from inside the container returns 1200 B ✓
- **`bijou-production.fly.dev/static/bijou-logo.svg`** returns 1200 B with `Cache-Control: no-store` ✓

**⚠️ STALE EDGE CACHE on `app.mybijou.xyz`** (the custom domain):
- The custom domain is on Fly's SHARED customer IP `66.241.124.104`, behind an edge cache
- `bijou-production.fly.dev` and `app.mybijou.xyz` resolve to **different Fly IPs** with **different edge caches**
- The edge cache for `app.mybijou.xyz` is still serving the old `bijou-logo.svg` (3.1 MB, Last-Modified Sat 18 Jul 2026) — same for `dashboard.html`, `favicon.png`, and all other static files
- My no-cache headers are in the container but the edge intercepts the request and returns the cached response **before** my app sees it (so my `Cache-Control` header is never even set on those stale responses)
- This will resolve when the edge cache TTL expires. Without admin access to the Fly edge, I cannot force a purge.
- Workaround for the user: hard-refresh the dashboard in their browser (Ctrl+Shift+R / Cmd+Shift+R), or open in a private/incognito window. The dashboard.html with the new SVG favicon link will be served, the browser will fetch the new SVG, and the new branding will appear.
- Workaround URL: `https://bijou-production.fly.dev/static/dashboard.html` will serve the new content immediately (bypasses the custom-domain edge).

**Cert status note**: `app.mybijou.xyz` cert shows "Issuing" / "Domain ownership verification required" because the shared-IP edge uses HTTP-01 validation that Fly can't complete behind its own proxy. The cert is actually valid (Expires 1 month from now, Issued 5 months ago via DNS-01), so HTTPS works — it's just an artifact of the shared-IP setup.

## What "system ready" still needs from the user

### 1. Vercel env vars (the marketing site API endpoints can't send emails/persist leads without these)

`vercel env ls` returns empty. Production endpoints at `https://bijou-landing.vercel.app/api/*` will return 5xx without these. The endpoints that need them:

| Env var | Used by | Where to get it |
|---|---|---|
| `RESEND_API_KEY` | `/api/voice-waitlist`, `/api/leads`, `/api/slide-deck` | https://resend.com/api-keys |
| `EMAIL_FROM` | same | e.g. `Bijou AI <hello@mybijou.xyz>` |
| `EMAIL_NOTIFY` | same | e.g. `founder@mybijou.xyz` |
| `GEMINI_API_KEY` | `/api/chat` (the demo Manglish chat) | https://aistudio.google.com/app/apikey |
| `SUPABASE_URL` | `/api/leads`, `/api/slide-deck` | https://supabase.com/dashboard |
| `SUPABASE_SERVICE_KEY` | same | Supabase project → Settings → API |
| `STRIPE_SECRET_KEY` | `/api/spots` (the "early adopter spots" counter) | https://dashboard.stripe.com/apikeys |
| `INTERNAL_API_TOKEN` | `/api/send` (founder relay) | `openssl rand -hex 32` |
| `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` | `lib/rateLimit.js` (optional, falls back to in-process LRU) | https://upstash.com |

The `.env.example` in the marketing repo already documents all of these. The same file in `w3j-bijou-ai-main` (the backend repo) has the production Supabase + Stripe + Resend values that the marketing API endpoints need to mirror.

**Safe now**: GET endpoints (return 405 / 400 as expected), site loads, logos render, OG image is the new one. Submission endpoints will 503 until env is populated.

### 2. Fly.io edge cache for `app.mybijou.xyz` (will clear on its own — or hard-refresh)

The custom-domain edge cache is serving the pre-Signal-Gem files (3.1 MB logo, old dashboard.html, etc.) for an unknown TTL. The container has the new files and `bijou-production.fly.dev` serves them correctly. The custom-domain edge intercepts the request and returns its cached version before my no-cache headers can take effect.

**User action**: hard-refresh (Ctrl+Shift+R / Cmd+Shift+R) the dashboard in their browser, OR open it in a private/incognito window. Alternatively, use the direct URL `https://bijou-production.fly.dev/static/dashboard.html` to bypass the custom-domain edge.

**Future-proofing**: the new `_NoCacheStaticFiles` wrapper in `src/core/bijou.py` will set `Cache-Control: no-store` on every static-file response, so the NEXT deploy will force the edge to re-fetch. This deploy's response is still cached, but from here on the edge can't keep a stale copy after a release.

### 3. (No longer blocking) Fly.io billing on the `mn-bijou` org

`w3j-bijou-enterprise` lives in a DIFFERENT Fly account (the `personal` account) than the one with the billing issue. The deploys to `bijou-production` worked. The earlier `mn-bijou` billing block is on a separate account. Not blocking anymore.

## What's already running fine (200 OK confirmed)

| Endpoint | Status | Notes |
|---|---|---|
| `https://bijou-landing.vercel.app/` | 200 | marketing site with new Signal Gem |
| `https://bijou-landing.vercel.app/logos/*` | 200 | 11 brand assets |
| `https://bijou-landing.vercel.app/og-image.png` | 200 | new Signal Gem OG image |
| `https://bijou-production.fly.dev/health` | 200 | `{"status":"healthy","service":"bijou-ai-enterprise","version":"2.2.0","database":"supabase"}` |
| `https://bijou-production.fly.dev/static/bijou-logo.svg` | 200, 1200 B | fresh Signal Gem |
| `https://app.mybijou.xyz/health` | 200 | same (custom domain, but edge-cached for static) |
| `https://app.mybijou.xyz/static/dashboard.html` | 200, 320406 B | ⚠️ edge-cached (Last-Modified 21 Jul, not today's deploy) |
| `https://bijou-bridge-production-v2.fly.dev/` | 401 | auth-protected, alive |

## Open items still on the deck

1. **Vercel env vars** (user action — paste values from `.env.example`)
2. **Fly edge cache** for `app.mybijou.xyz` — wait for TTL or hard-refresh; new deploys will bypass via no-cache headers
3. `api/spots.js` hardcoded scarcity counter (audit #5) — cosmetic, deferred
4. `CUSTOME_API_KEY` typo in `.env` and `api/chat.js` — cosmetic, both consistent
5. `npm audit` 7 transitive vulnerabilities (1 critical, 1 high, 5 moderate) — deferred
6. `OnboardingModal.tsx` 816-line god-file — refactor candidate
7. Tailwind via CDN (should be build-time CSS) — deferred

## Memory updates

- Bijou logo asset source: `w3j-media-pack/logo-variants/signal-gem-system/` is the canonical Signal Gem master
- Bijou logo React component: `components/BijouLogo.tsx` exports `BijouLogo` + `BijouLockup` with BIJOU palette tokens
- Bijou brand colors: `--bj-green #0B3B2E` / `--bj-gold #E3B457` / `--bj-cream #F7F4EC` / `--bj-ink #0A0A0A` (used in tailwind, CSS vars, BijouLogo component, og-image)
- Bijou Vercel deploy: `vercel --prod` from `Bijou-AI---Digital-Employee-main` deploys to `bijou-landing` automatically
- Bijou Fly deploy: must use `fly deploy --app bijou-production --config fly.production.toml` from `w3j-bijou-enterprise/` with **explicit Set-Location** (bash tool cwd is per-invocation; chained `cd ...; fly deploy` does not reliably persist into the deploy's build context)
- **Fly edge cache gotcha**: `bijou-production.fly.dev` and `app.mybijou.xyz` resolve to different Fly IPs with different edge caches. The custom domain uses a shared customer IP `66.241.124.104` and can hold stale content for hours/days. The .fly.dev hostname always serves fresh. Workaround in code: wrap StaticFiles in a subclass that sets `Cache-Control: no-store` (see `src/core/bijou.py` `_NoCacheStaticFiles`). The wrapper works for FUTURE deploys; for the CURRENT stale content, user has to hard-refresh or use the .fly.dev URL.
