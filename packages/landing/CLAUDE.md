# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

The marketing/landing site for **Bijou AI** — a WhatsApp + Telegram AI sales agent SaaS for Malaysian/SE-Asian SMEs. Despite the README calling it a "static frontend," it is actually a **React SPA plus a Vercel serverless API layer** (`api/*.js`). The core product (the multi-tenant WhatsApp backend, dashboard, RAG, billing) lives in a *separate* repo (`w3j-bijou-enterprise` / `bijou-production.fly.dev`); this repo only contains the public site, a demo chat, and lead-capture endpoints.

## Commands

```bash
npm run dev          # Vite dev server on port 3000 (host 0.0.0.0)
npm run build        # Production build → dist/
npm run preview      # Serve the production build locally
npx tsc --noEmit     # Type-check (the ONLY automated check — see below)
```

There is **no test framework and no linter/formatter**. `tsc --noEmit` is the only gate; verify changes manually in the dev server.

> Important: `tsc` only checks the frontend. `tsconfig.json` deliberately **excludes `api/**` and `backend/**`** because those run in Node (Vercel functions) and Deno (Supabase edge functions), not the browser. Editing an `api/*.js` file will not be type-checked — validate those by exercising the endpoint.

## Architecture

### Two runtimes in one repo
- **Browser (Vite/React):** `App.tsx`, `index.tsx`, `components/`, `services/`, `utils/`, `i18n.ts`. Bundled by Vite, aliased `@/*` → repo root.
- **Serverless (Node, Vercel):** `api/*.js` — plain ESM handlers exporting `default async function handler(req, res)`. These hold all secrets; the browser never sees API keys (`vite.config.ts` intentionally injects almost nothing into `process.env`).
- **Edge (Deno, Supabase):** `backend/supabase/functions/{create-link,redirect}/index.ts` — a link-shortener. `backend/*.sql` is the Postgres schema.

### Frontend composition (no router)
`App.tsx` is a single scroll page that stacks section components (`Hero`, `PainSection`, `Pricing`, `DemoChat`, `FAQ`, `FinalCTA`, …). "Navigation" is anchor-scroll + a single shared modal (`OnboardingModal`) driven by one `modalState` in `App.tsx`, opened via an `openModal(mode, source)` callback drilled into children as props. There is no global store — state is local (`useState`) and passed down. Follow this prop-drilling pattern; don't introduce Redux/Zustand.

### The demo chat → serverless proxy pattern
`components/DemoChat.tsx` calls `services/gemini.ts` → `fetch('/api/chat')` → `api/chat.js`, which calls Google GenAI (`gemini-flash-lite-latest`) server-side. **The entire Manglish persona/system prompt lives inline in `api/chat.js`** — that is where you edit Bijou's voice, pricing knowledge, and competitor comparisons, not in any frontend file. `services/tools.ts` is a *mock* tool orchestrator (console-logs, no real send) used only for the demo.

### Lead capture & email
`api/leads.js`, `api/slide-deck.js`, `api/voice-waitlist.js`, `api/onboarding/signup.js` persist to **Supabase** and send transactional email via **Resend**. `api/spots.js` reads a **Stripe** counter for the "early adopter spots remaining" badge.

### i18n
`i18n.ts` (~85KB) holds all translation resources inline for **4 languages** (EN, MS = formal Bahasa Melayu, ZH, TA). Manglish is rendered inline by the LLM via the system prompt in `api/chat.js`, not from the i18n catalog. It is initialized once via `import './i18n'` in `index.tsx`; components consume it with `react-i18next` hooks (`LanguageSwitcher.tsx` toggles). When adding user-facing copy, add keys to `i18n.ts` rather than hardcoding strings.

### Styling
Tailwind is loaded via **CDN in `index.html`** (config block is inline there), not a build-time PostCSS pipeline — so there is no `tailwind.config.js` to edit; change the `tailwind.config = {…}` script in `index.html`. Design language: dark theme, emerald (`#10b981`) / deep-green / gold, glassmorphism (`.glass-panel-3d`), Framer Motion spring animations. It's a PWA (`public/sw.js`, `public/manifest.json`, `PWAInstallPrompt.tsx`).

## Environment variables (server-side only, set in Vercel)

Never expose these to the client. Consumed inside `api/*.js`:
- `VITE_GEMINI_API_KEY` — Google GenAI (demo chat)
- `SUPABASE_URL` / `VITE_SUPABASE_URL`, `SUPABASE_SERVICE_KEY` / `SUPABASE_SERVICE_ROLE_KEY`
- `RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_NOTIFY`, `FOUNDER_EMAIL`
- `STRIPE_SECRET_KEY`

## Deployment

Vercel, auto-deploy from `main`. `vercel.json` rewrites everything except `/brand/*` to `index.html` (SPA), long-caches `/assets/*`, and sets security headers. Build command is `npm install && npm run build`.

## Conventions

- Functional components with typed props: `export const X: React.FC<XProps>`. Named exports everywhere except `App.tsx` (default). Components `PascalCase.tsx`; services/utils `camelCase.ts`.
- User-facing error strings use **Manglish** deliberately (e.g. "Aiyo, server having hiccup boss") — this is a product voice choice, keep it.
- `api/*.js` handlers should catch errors and still return HTTP 200 with a friendly Manglish `response` (see `api/chat.js`) so the demo never hard-fails in the UI.

## Related agent context

`AGENTS.md` holds an overlapping (and partly dated) style guide. `.opencode/` contains an OpenCode multi-agent setup (`agents/`, `commands/`, `JEWEL_PROFILE.md`, `MASTER_CONTEXT.md`) for a different tool — not required for working in this repo, but useful business/founder context if a task needs it.
