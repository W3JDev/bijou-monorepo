# PostHog Setup — Bijou AI Landing

Installed 2026-07-30 across the full stack. All three layers (landing, backend, database) now fire into a single PostHog project so you can see the funnel end-to-end.

- Project: US Cloud (`https://us.posthog.com`)
- Project ID: `534283`
- Project token: `phc_REDACTED`
- Personal API key: `phx_REDACTED` (server-only)

## What's wired

| Layer | File | What it does |
|---|---|---|
| Frontend | `services/posthog.ts` | Lazy init, typed `EventName` union, `track/identify/reset` helpers |
| Frontend init | `index.tsx` | Calls `initPostHog()` before React mounts |
| Frontend events | `App.tsx`, `Navbar.tsx`, `Hero.tsx`, `Pricing.tsx`, `FinalCTA.tsx`, `LeadCaptureForm.tsx`, `OnboardingModal.tsx`, `DemoChat.tsx`, `WhatsAppCTA.tsx` | `landing_pageview`, `signup_modal_opened/completed`, `lead_captured`, `demo_chat_*`, `pricing_plan_clicked`, `whatsapp_cta_clicked`, `slide_deck_opened`, etc. |
| GA4 compat | `utils/analytics.ts` | `trackTrialSignup` / `trackDemoBooking` / `trackFormSubmission` / `trackPlanSelection` now fire to BOTH GA4 and PostHog |
| Server | `lib/posthog-server.js` | `captureServer`, `identifyServer`, `distinctIdFromReq` |
| Server events | `api/leads.js`, `api/chat.js`, `api/send.js`, `api/spots.js`, `api/voice-waitlist.js`, `api/slide-deck.js`, `api/demo.js` | `lead_captured`, `demo_booked`, `voice_waitlist_joined`, `slide_deck_downloaded`, `spot_count_fetched`, `chat_error`, `api_error` |
| Database bridge | `api/posthog-bridge.js` | Receives Supabase Database Webhooks → forwards to PostHog as `lead_db_change` / `user_db_change` / `voice_waitlist_db_change` |

## Env vars (already set in local `.env`)

- `VITE_POSTHOG_PROJECT_KEY=phc_…` (browser-safe)
- `VITE_POSTHOG_HOST=https://us.i.posthog.com`
- `POSTHOG_PROJECT_KEY=phc_…` (server-side)
- `POSTHOG_HOST=https://us.i.posthog.com`
- `POSTHOG_PERSONAL_API_KEY=phx_…` (server-only)

**Vercel env** must also have all five set on the project's Production environment — local dev has them, prod does not until you copy.

## CSP

`vercel.json` now allows:
- `script-src` → `https://us-assets.i.posthog.com`
- `connect-src` → `https://us.i.posthog.com https://us-assets.i.posthog.com`

(GA4 stays as-is.)

## Supabase Database Webhooks (one-time, ~5 min)

The landing page itself fires PostHog from the browser, and `api/leads.js` fires server-side. But for **DB-side** events (a lead updated in Supabase, a user deleted, a new voice-waitlist row from somewhere else), wire a Supabase Database Webhook to `api/posthog-bridge.js`:

1. Supabase dashboard → **Database → Webhooks → Create new webhook**
2. **Name:** `posthog-bridge-leads`
3. **Table:** `leads`
4. **Events:** INSERT, UPDATE, DELETE
5. **Type:** HTTP Request
6. **URL:** `https://mybijou.xyz/api/posthog-bridge`
7. **Method:** POST
8. **HTTP Headers:**
   - `Content-Type: application/json`
   - `X-Internal-Token: <paste your INTERNAL_API_TOKEN value>`
9. Repeat for `onboarding_users` and `voice_waitlist` tables.

That's it — Supabase will POST the row to the bridge on every change and it'll show up in PostHog as `lead_db_change` etc.

## Where to look in PostHog

After the Vercel deploy + Supabase webhook setup:

- **Activity tab** → live event stream. Filter by event name (`landing_pageview`, `lead_captured`, `demo_booked`) to see real-time traffic.
- **Persons tab** → identified users (`email:*` distinctIds). Each lead shows up with their full event timeline.
- **Insights → Trends** → build a funnel: `landing_pageview` → `signup_modal_opened` → `signup_modal_completed` → `demo_booked`.
- **Insights → Funnels** → the visual conversion map.
- **Insights → Dashboards** → add the standard "Bijou Landing" dashboard with the events above.

## Funnel events reference

Frontend (browser-side, with autocapture context):
- `landing_pageview` — first page load (with UTM params + referrer)
- `language_change` — i18n switcher
- `hero_cta_clicked` — top "Start Free Trial" / "Get Early Access"
- `nav_signup_clicked` — Navbar "Get Early Access"
- `signup_modal_opened` / `signup_modal_completed` / `signup_modal_failed`
- `demo_modal_opened` / `demo_chat_message_sent` / `demo_chat_response_received`
- `waitlist_modal_opened`
- `lead_capture_form_submitted` / `lead_capture_form_failed`
- `pricing_plan_clicked` (`plan_name`: pro / enterprise / enterprise_contact)
- `whatsapp_cta_clicked`
- `cal_booking_opened`
- `slide_deck_opened` / `slide_deck_downloaded`

Backend (server-side, with request meta):
- `lead_captured` — successful Supabase insert in `/api/leads`
- `demo_booked` — successful demo notify in `/api/demo`
- `voice_waitlist_joined` — `/api/voice-waitlist`
- `slide_deck_downloaded` — `/api/slide-deck`
- `spot_count_fetched` — `/api/spots` (any refresh, with total/remaining)
- `whatsapp_relay_sent` — `/api/send`
- `chat_error` — Gemini/gateway failure in `/api/chat`
- `api_error` — generic server error, with `endpoint` + `kind` properties

DB bridge (Supabase webhook → bridge):
- `lead_db_change` — INSERT/UPDATE/DELETE on `leads`
- `user_db_change` — INSERT/UPDATE/DELETE on `onboarding_users`
- `voice_waitlist_db_change` — INSERT/UPDATE/DELETE on `voice_waitlist`

## Kill switch

Set `POSTHOG_ENABLED=0` on Vercel → server-side PostHog stops capturing. Frontend PostHog stops capturing when `VITE_POSTHOG_PROJECT_KEY` is unset (rebuild + redeploy required).

## Verifying after deploy

1. Open `https://mybijou.xyz` in incognito (clear cookies)
2. PostHog Activity tab should show a `$pageview` within 2 sec
3. Click "Get Early Access" → expect `nav_signup_clicked` + `signup_modal_opened`
4. Fill the form → expect `signup_modal_completed` + (server-side) `lead_captured`
5. Try the demo chat → expect `demo_chat_message_sent` + `demo_chat_response_received`

If events don't show up: open DevTools → Network → filter `posthog` → check for 200s on `/e/` (browser) and `/batch/` (server).
