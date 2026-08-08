# Changelog

All notable changes to Bijou AI Landing Page will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.0.0] - 2026-05-15

### 🎯 Honest + Viral Copy Redesign

Six targeted fixes to align marketing copy with verifiable claims and add viral social hooks.

### 💰 Fix 1 — Honest Savings Math (RevenueCalculator.tsx)

- Replaced old "RM9,201 savings · 335% ROI" hero card values with honest baseline
- Added savings callout: "Save **RM2,700+** every month vs part-time WhatsApp staff"
- ROI stated as **~900%** at RM299/mo — math verifiable against PayScale market rates
- MS: "Jimat RM2,700+ sebulan berbanding pekerja separuh masa. ROI ~900% pada harga RM299."
- i18n keys `hero.roiCard.amount` and `hero.roiCard.roi` remain in place for rollback

### 🧠 Fix 2 — TRACE Redesign to Real Component Names (Features.tsx)

- Removed "Unique to Bijou" and "TRACE Empathy Engine — Live Now" branding
- `TraceWidget` step labels updated: Emotion→**ASI**, Cause→**Humanizer**, Plan→**ERS**, Respond→**Routing**
- Feature card badge updated from "Unique to Bijou" to **"Production · v300"**
- New description (EN): "ASI reads the customer's intent. Humanizer turns the response into Manglish that doesn't sound like a robot. ERS decides if a human needs to step in. Routing sends it to the right WhatsApp."

### 👥 Fix 3 — Social Proof (WaitlistStrip.tsx)

- Source value was "500+ Malaysian SMEs" (no "00+" rendering bug found in current build)
- Replaced `t("waitlist.social")` with honest place-based proof: **"Built in KL. Made for Malaysian SMEs."**

### 🔒 Fix 4 — MDEC/Cradle HOLD Comment (Hero.tsx)

- Added HTML comment in trust section: `{/* HOLD: MDEC + Cradle status pending founder verification 2026-05-15 */}`
- No markup or rendering changes — comment only

### 🏢 Fix 5 — ENTERPRISE Tier (Pricing.tsx)

- Added ENTERPRISE card: **RM999/month**, marked "Coming Q3 2026 · Waitlist"
- Features: Official WABA, unlimited messages, multi-location, team accounts, priority support
- Added cap note: "Hit the 3,000/mo cap? Tell us — we'll upgrade you to ENTERPRISE early."
- MS: "Dah guna 3,000 perbulan? Beritahu kami — kami akan upgrade ke ENTERPRISE awal."

### 🎬 Fix 6 — Three Viral Hooks (New Components)

- **Hook A — "The 2am Viewing Inquiry"** (`components/Story2amProperty.tsx`):
  - Property vertical, Mont Kiara, 2:47am WhatsApp mock conversation
  - EN tagline: "The 2am Viewing Inquiry. Closed by morning."
  - MS: "Sabtu pagi dia dah datang viewing. Bijou yang uruskan semuanya."
- **Hook B — "The Lunch Rush Clinic"** (`components/StoryLunchRushClinic.tsx`):
  - Healthcare/dental vertical, child tooth pain triage at 12:14pm
  - EN tagline: "The Lunch Rush Clinic. Triaged. Booked. Done."
  - MS: "Masa rehat tengah hari pun Bijou boleh triage dan buat appointment."
- **Hook C — "Bijou speaks. In Manglish."** (`components/VoiceComingSoon.tsx`):
  - Voice AI teaser, phone call mock in Manglish, Q4 2026 target
  - Email capture form → `POST /api/voice-waitlist`
- **Stub endpoint** (`api/voice-waitlist.js`): Resend-powered (already in package.json) — notifies founder + confirms to user
- **App.tsx wiring**: Hooks A+B inserted after PainSection, Hook C after Pricing

### 🔧 Technical

- No new npm dependencies added — Resend `^6.9.2` already in `package.json`
- All components use existing Tailwind classes and Framer Motion patterns
- TypeScript types preserved; new components typed as `React.FC`
- Branch: `feature/honest-viral-copy-2026-05-15`

---

## [4.0.0] - 2026-03-04

### 💥 Pricing Architecture Change

- **BREAKING:** Retired 3-tier pricing model (Starter / Professional / Enterprise)
- Single **PRO** tier: **RM299/month** or **RM2,990/year** (save RM598)
- Annual savings updated: RM2,490 → RM2,990 | savings RM498 → RM598
- Telegram now **included** in PRO (was a paid add-on at +RM60/mo)
- Cal.com booking status promoted from Beta → **Live**
- Email booking confirmations and escalation alerts marked **Live**

### ✨ New Features

- **`PainSection` component** (`components/PainSection.tsx`):
  - 3 real competitor pain quotes (ChatDaddy, DahReply, Wati/WABA)
  - Red-tinted review cards with brand labels
  - Emerald divider → Bijou 3-column flip: Manglish tone / flat fees / 15-min setup
  - Inserted between Hero and Features in `App.tsx`
- **Early Adopter Price Lock badge** in Pricing card:
  - Pulsing Lock icon + gold progress bar at 70% ("7 of 10 spots remaining")
  - Price locked forever messaging for founding customers
- **"Zero hidden fees. Ever." strip** in Pricing card (left column, below CTA):
  - ✕ WhatsApp conversation markup
  - ✕ Per-message charges
  - ✕ WABA application fee
  - ✕ Annual lock-in
  - ✕ Bot-wall for support

### 📝 Copy Updates

- **Hero headline:** "Your WhatsApp goes offline at 10pm. Your competitors' doesn't."
- **Hero subtitle:** WhatsApp & Telegram mentioned explicitly; Cal.com appointments; "while you sleep" closer
- **Hero badge:** "RM0 to start — no credit card, no WABA needed"
- **Hero trust footer:** "30-day money-back · No WABA needed · Cancel anytime"
- **Hero CTA:** "Start Free — RM0"
- All 4 i18n languages (EN/MS/ZH/TA) updated with new pricing and feature list

### 🔧 Technical

- Removed ~190 lines of leftover 3-tier JSX from `Pricing.tsx` (was causing silent dead code)
- Removed empty `betaFeature` amber block (i18n value was empty string)
- `addOns` array: "Telegram channel" → "Extra Telegram bot" + "Email channel" → "Facebook Messenger"
- `Lock` icon added to Pricing.tsx imports; `AlertTriangle` removed
- Zero TypeScript errors post-migration (`npx tsc --noEmit`)

---

## [3.0.0] - 2026-02-24

### 🎨 Premium Branding Overhaul

- **BREAKING:** Complete visual rebrand from Emerald Green to Deep Green & Gold
- Updated color palette to Deep Green (#0d3d3d) + Gold (#D4AF37)
- Circuit board pattern background with gold grid lines
- All CTAs now use gold gradient styling
- Enhanced "AI" text visibility in footer logo

### ✨ New Features

- **Pricing Component:** Added comprehensive 3-tier pricing section
  - Starter: RM159/month (68% discount, first 100 customers)
  - Professional: RM299/month
  - Enterprise: Custom pricing
  - 335% ROI guarantee badge
- **Footer Enhancements:**
  - W3J LLC attribution with logo
  - Complete contact structure (hello@, mrj@, support@, jewel@mybijou.xyz)
  - Social media links (LinkedIn, Instagram, X/Twitter, GitHub)
  - Company location info (Wyoming, USA • KL, Malaysia)

### 🔧 Improvements

- Fixed ALL CTAs to trigger lead capture modals (no direct signup links)
- RevenueCalculator now opens modal instead of external link
- Updated RM159/month pricing throughout (was RM99)
- Enhanced ROI messaging: RM9,201/month savings highlighted
- Improved mobile responsiveness across all components
- Updated Hero section with launch pricing badge

### 🐛 Bug Fixes

- Fixed Footer "AI" text visibility (was too dark/fading)
- Corrected all email addresses to mybijou.xyz domain
- Fixed modal flow in FinalCTA component
- Updated case studies to use gold accents instead of emerald

### 🗑️ Cleanup

- Removed 7.7MB of duplicate logo files from /public
- Removed all screenshot files (500KB+)
- Cleaned up outdated project docs (MISSION_COMPLETE, PHASE docs, etc.)
- Enhanced .gitignore to exclude sensitive files

### 📚 Documentation

- Complete README.md overhaul with production info
- Added W3J LLC company information
- Updated tech stack documentation
- Added deployment instructions
- Included business metrics and target markets

### 🚀 Deployment

- Vercel auto-deployment configured
- Production build optimized (449KB, gzipped: 133KB)
- Live at mybijou.xyz

---

## [2.0.0] - 2026-02-23

### Added

- PWA functionality with offline support
- Lead capture modal with email collection
- Calendar booking integration (Cal.com)
- WhatsApp CTA floating button
- Waitlist strip component

### Changed

- Updated to React 19
- Migrated to Vite 6.4.1
- Enhanced Framer Motion animations
- Improved mobile navigation

---

## [1.0.0] - 2023-10-27

### Added

- **Tool Orchestrator:** Implemented `services/tools.ts` to simulate backend tool execution
- **Roadmap Voting:** Added interactivity with localStorage persistence
- **TRACE Logging:** Console logging for AI agent decision simulation
- **Security Animations:** Pulse and neon glow effects

### Changed

- **Hero UI:** Relocated floating ROI card to top-right corner
- **Navbar Behavior:** Enhanced sticky navigation with dynamic blur
- **Playbooks:** Implemented "Live Typing" simulation
- **Hero Animation:** Added staggered entrance animations

### Fixed

- **Syntax Error:** Fixed JSX syntax error in RevenueCalculator.tsx

### Initial Release

- Core landing page structure
- Revenue Calculator component
- Viral Pillars simulation (Stress Test, Speed Run, Night Dashboard)
- Basic Gemini AI integration for demo chat
- TRACE framework visualization

---

## Versioning Strategy

- **Major (X.0.0):** Breaking changes, major redesigns
- **Minor (0.X.0):** New features, non-breaking changes
- **Patch (0.0.X):** Bug fixes, minor improvements

---

**Repository:** [github.com/W3JDev/Bijou-AI---Digital-Employee](https://github.com/W3JDev/Bijou-AI---Digital-Employee)
**Maintainer:** W3J LLC | jewel@mybijou.xyz
