# Landing Pivot — 2026-09-21

Pivoted the Bijou AI landing page from a Malaysia/SE-Asia self-serve WhatsApp SaaS
to a **US/EU done-for-you managed AI service**.

## Locked decisions applied
- **Pricing:** `$2,500` one-time setup **+** `$499/month` managed. Enterprise = **"Custom"**.
  All `RM` amounts removed / converted to USD.
- **Primary CTA:** "Book a Free Strategy Call" (existing `onOpenModal`/modal wiring unchanged — label text only).
- **Positioning:** "Done-for-you AI agents for US & EU businesses — we build, deploy, and manage them for you."
- **Voice:** clear, professional US English (no Manglish).
- **Compliance framing:** PDPA → GDPR & CCPA.

## Files changed

### `i18n.ts` (en block only — ms/zh/ta intentionally untouched)
- `hero.*` — new done-for-you subtitle/positioning, CTA → "Book a Free Strategy Call",
  badge (no RM0/WABA), trustFooter, `hero.trust.pdpa` → "GDPR & CCPA Ready",
  chatDemo bubbles rewritten to US English, roiCard amount RM2,700+ → $3,000+.
- `pricing.pro.*` — name → "DONE-FOR-YOU", price → "499", yearlyPrice repurposed to "2,500"
  (one-time setup), yearlySaving → "Build, deployment & full onboarding included",
  description + features reworded (no WABA/Manglish/BM/Tamil).
- `pricing.title` → "One Plan. Fully Managed.", `pricing.cta.trial` → "Book a Free Strategy Call".
- `pricing.ea.b1/b2` → $499 lock / "New customers pay more".
- `waitlist.*` — headline $499/mo, social → "Built for US & EU businesses.", "Live in days".
- `comparison.disclaimer` + `comparison.cta.body` + `comparison.cta.wa` — done-for-you USD framing.
- `features.wa/tg/trace/manglish/security.*` — WABA/Meta/Manglish/PDPA/Singapore → managed,
  brand voice, multilingual, GDPR/CCPA, US & EU regions. `features.stats.langs.sub` → "English + multilingual".
- `cases.realEstate.*` — repurposed to **Confidential US Client** case study with placeholders
  (`[RESULT — pending]`, `[METRIC — pending]`).
- Stale pricing code-comment updated.

### `components/Pricing.tsx` (hardcoded, i18n doesn't cover)
- `getUrgencyMessage()` RM399/RM299 → $599/$499.
- `addOns` array `+RMxx` → `+$xx`.
- Price prefix `RM` → `$`; **Annual Plan block repurposed to "One-Time Setup" ($2,500 / one-time)**.
- "Zero hidden fees" list: "WABA application fee" → "DIY setup work on your end".
- Enterprise card: `RM999`/month → **"Custom"**; features "Official WABA" → "Official WhatsApp Business API",
  "Custom Manglish persona" → "Custom AI persona per brand"; removed Malay cap-note line.
- Comparison table: subtitle "Manglish AI agent" → "Done-for-you AI agent", price "RM 299/mo" → "$499/mo",
  lang row → "English + multilingual", pdpa row label → GDPR/CCPA, both "Why Bijou costs…" paragraphs reframed.

### `components/Features.tsx` (hardcoded feature list — NOT driven by i18n)
- WhatsApp/Telegram/TRACE descriptions: WABA/Meta/RM/Manglish → managed / brand voice / $499+$2,500.
- "Manglish Engine" → "Multilingual Engine" (title/subtitle/desc/bullets).
- "PDPA-Ready Security" → "Enterprise-Grade Security" (GDPR/CCPA, US & EU regions).
- `ManglishDialWidget` sample responses + slider label "Full Manglish" → "Casual" (component name kept — no rename).
- Trust chip "PDPA Ready" → "GDPR Ready".

### `components/CaseStudies.tsx`
- Added `<!-- TODO: real Confidential US Client figures before deploy -->` comment near the Confidential US Client case.

### `api/chat.js` (prompt TEXT only — no logic/handler changes)
- Persona: "Malaysian businesses" → "done-for-you AI agent service for US & EU businesses".
- Mandatory-Manglish directive → "Reply in clear, friendly, professional US English by default."
- Pricing facts → "$2,500 one-time setup + $499/month managed; Enterprise: custom" (removed "NO setup fee").
- Competitor section converted from RM/WABA/Meta to generic USD done-for-you framing.
- Knowledge base / greeting / never-do / response-format sections de-Manglished; kept greet→qualify→close flow.
- Verified with `node --check api/chat.js` → OK.

### Other funnel components (visible RM + prominent Malaysia/Manglish/WABA)
- `FinalCTA.tsx` — RM0/RM299/RM2,990/WABA → managed USD; button "Start Free Trial" → "Book a Free Strategy Call".
- `RevenueCalculator.tsx` — `bijouCost` 299→499; RM savings/ROI + Malay line → USD managed framing.
- `ComparisonTable.tsx` — RM prices → USD; "WABA Required" → "DIY Setup Required";
  "WhatsApp (no WABA)" → "(fully managed)"; "Manglish / Malaysian AI" → "Brand-voice AI persona";
  "English + BM + 中文 + தமிழ்" → "English + multilingual".
- `FAQ.tsx` — RM pricing, WABA/Meta answers, "Malaysian Market" category (→ "Languages & Reach",
  incl. the 3 style-map keys), Singapore servers, Manglish examples → US-English done-for-you.
- `PainSection.tsx` — RM299/RM5,000/WABA/Manglish/"real Malaysian businesses" → USD managed / generic.
- `Story2amProperty.tsx` — Manglish + Malay translation block + "No WABA"/"Manglish native" chips → brand voice / managed.
- `Playbooks.tsx` — RM3.5k/RM50 + Manglish demo bubbles (property/dental/gaming/F&B) → USD + US English.
- `ViralPillars.tsx` — "Merdeka Promo (RM2k…)" Manglish bubble → USD US-English.
- `VoiceComingSoon.tsx` — "In Manglish" + Malay paragraph + "Malaysian SMEs" + RM299 → brand voice / US & EU / $499.
- `Changelog.tsx` — RM values → USD; Manglish/"Malaysian SMEs" historical entries neutralized.
- `DemoChat.tsx` — Manglish opener + "Manglish difference" hint → US English / "done-for-you difference".
- `InfoModal.tsx` (Footer About/Careers/Terms modal) — Kuala Lumpur/Malaysia, RM300k, RM299/RM2,990 → US & EU / USD.
- `PartnershipForm.tsx` (Footer modal) — RM commissions/values + "First Manglish AI Agent" → USD / done-for-you.
- `OnboardingModal.tsx` — "Malaysian SME" copy, "500+ Malaysian SMEs", "PDPA Compliant",
  "Malaysian team", and phone validation message → US/EU + GDPR/CCPA.
- `Footer.tsx` — "Operations: Kuala Lumpur, Malaysia" → "Serving US & EU businesses".
- `WhatsAppCTA.tsx` — "Malaysian team… 🇲🇾" → "our team… 💬".
- `HowItWorks.tsx` — "slang (Manglish)" → "tone across languages".
- `LeadCaptureForm.tsx` — "Malaysian SMEs" → "growing businesses"; "PDPA compliant" → "GDPR & CCPA compliant".
- `PWAInstallPrompt.tsx` — "Manglish digital employee" → "AI digital employee".

## Verification
- `npx tsc --noEmit` → **PASS** (exit 0, no errors).
- `npm run build` (Vite) → **PASS** (exit 0, "✓ built in 26.30s").
  Note: had to install `@rollup/rollup-win32-x64-msvc` (`npm install … --no-save` at repo root)
  to work around the known npm optional-deps bug (npm/cli#4828) — unrelated to these edits.
- Dev server for browser check: `cd packages/landing && npm run dev` → http://localhost:3000
- **NOT browser-verified by me** — typecheck + production build pass; page not loaded in a browser this session.

## Known remaining / TODO
- **Confidential US Client metrics are placeholders** (`[RESULT — pending]`, `[METRIC — pending]`) — replace with
  real figures before deploy (HTML TODO comment added in `CaseStudies.tsx`).
- **`ms`/`zh`/`ta` i18n blocks still contain RM/Manglish/Malaysia copy** — intentionally left per task
  scope (US/EU visitors get English via `fallbackLng: "en"` + LanguageDetector). The `LanguageSwitcher`
  still offers 🇲🇾/🇨🇳/🇮🇳 locales.
- **`OnboardingModal` phone normalization logic** still assumes Malaysian format (`0…` → `60…`,
  min length 10) — this is code logic, left unchanged per "no logic changes" constraint. The user-facing
  message was updated, but US/EU numbers may still be rejected. Flag for a follow-up logic fix.
- **Not rendered in `App.tsx`, so left as-is:** `Roadmap.tsx` (Manglish/Bahasa/Tagalog/Thai),
  `CalBooking.tsx` (Manglish demo + "PDPA compliant"). Fix if they become reachable.
- **`api/*.js` email templates** (`leads.js`, `voice-waitlist.js`, `agents.js`, `slide-deck.js`) may still
  contain Malaysia-specific copy — not visible on the page, not exercised this pass.
- Code comments referencing "Malaysian SME" (e.g. `Pricing.tsx` competitor-table comment, `WaitlistStrip.tsx`,
  `Footer.tsx` PDPA comment) left in place — not user-visible.
- Pre-existing FAQ "15-minute setup / scan QR" steps still describe self-serve mechanics; contradicts the
  done-for-you model but contains no RM/Malaysia — left for a copy pass.
