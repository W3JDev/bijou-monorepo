# packages/landing/AGENTS.md — Bijou AI Landing (Vercel)

> **Master playbook**: read `../../AGENTS.md` first. This file is the
> per-package coding guidelines for the **landing** package (the React
> 19 + Vite SPA that lives on Vercel and serves mybijou.xyz).
>
> The master covers: agent team, autonomous loop, CI/CD, local+remote sync,
> emergency procedures. This file covers: how to code in this package.

---

This file contains essential information for coding agents working in the Bijou AI Digital Employee codebase.

> **Refreshed 2026-07-30 — PostHog added.** `posthog-js` + `posthog-node` are
> wired across the full stack: landing page, every `api/*.js` endpoint, and
> a Supabase-database-webhook bridge at `api/posthog-bridge.js`. Project is
> US Cloud, ID 534283. See `POSTHOG_SETUP.md` for the full env-var list,
> event reference, Supabase webhook setup, and the funnel to build in
> PostHog Insights.
>
> **Refreshed 2026-07-20.** Major drift from earlier version:
> - AI integration is now server-side via `api/chat.js` (gateway + direct
>   Gemini fallback), not a client-side GenAI call.
> - Line counts in the "Large Components" list are now accurate.
> - Env var list reflects the actual server-side contract.
> - See `audit-report.md` for the full list of issues this refresh addresses.

## 🏗️ Build Commands

### Development
```bash
npm run dev          # Start development server (Vite on port 3000)
npm run build        # Production build (output to dist/)
npm run preview      # Preview production build locally
```

### TypeScript
```bash
npx tsc --noEmit     # Type check without compilation (use this to validate TypeScript)
```

**Note:** This project has no testing framework configured. All testing must be done manually through the development server.

## 📁 Project Structure

```
├── components/           # React components (.tsx files)
├── services/            # API integration and business logic (gemini.ts, linkShortener.ts)
├── api/                 # Vercel serverless functions (.js, ESM)
├── backend/             # SQL schema, Supabase edge functions (Deno)
├── App.tsx              # Main application component
├── index.tsx           # Application entry point
├── vite.config.ts      # Build configuration
└── tsconfig.json       # TypeScript configuration
```

> **2026-07-20:** `dist/`, `node_modules/`, and `services/tools.ts` are
> gone. `public/brand/1.png`–`12.png` and the duplicate
> `BIJOU-LOGO-TRANSPARRENT.png` are gone. `bijou-site-fixed.png` and
> `metadata.json` at the repo root are gone. `public/icons/icon-base.svg`
> was restored with a minimal SVG (the original was lost in a prior
> mavis-trash operation).

## 🛠️ Technology Stack

- **Frontend:** React 19 + TypeScript + Vite
- **Styling:** Tailwind CSS (CDN) + Custom CSS
- **Animation:** Framer Motion 12.34.1
- **Icons:** Lucide React 0.574.0
- **AI Integration (server-side):** OmniRoute AI Gateway via `@google/genai`
  (direct Gemini as fallback)
- **Email:** Resend 6.9.2
- **DB:** Supabase (PostgreSQL)
- **Module System:** ESNext with bundler resolution

## 📝 Code Style Guidelines

### Import Organization
```typescript
// 1. React and external libraries first
import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, User, Bot } from 'lucide-react';

// 2. Local services and components
import { sendMessageToBijou } from '../services/gemini';
```

### Component Structure
**Always use functional components with TypeScript interfaces:**
```typescript
interface ComponentProps {
  onOpenModal: () => void;
  title?: string;
}

export const ComponentName: React.FC<ComponentProps> = ({ onOpenModal, title }) => {
  // Component logic
});
```

**Export Pattern:**
- Use named exports: `export const ComponentName: React.FC<Props>`
- Default export only for App.tsx: `export default function App()`

### TypeScript Guidelines
- **Always define interfaces** for component props
- Use strict typing - avoid `any` (use `unknown` + narrow in catch blocks)
- Leverage path aliases: `@/*` maps to root directory
- Target ES2022 with DOM libraries

### State Management
- Use `useState` hooks for local state
- Props drilling pattern for shared functionality (e.g. `onOpenModal` callbacks)
- No global state management (Redux/Zustand) - keep state local

### Animation Patterns (Framer Motion)
```typescript
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1, y: 0,
    transition: { type: "spring", stiffness: 100, damping: 10 },
  },
};
```

### Styling Conventions
- **Tailwind CSS** with custom utility classes
- **Glassmorphism:** Use `.glass-panel-3d` for consistent glass effects
- **Color Scheme:** Emerald green (#10b981) as primary, dark theme
- **Responsive:** Use `md:`, `lg:` breakpoints consistently

## 🚨 Error Handling

### API Integration Pattern
```typescript
// Client-side: services/gemini.ts only calls /api/chat — never holds a key.
// Server-side: api/*.js reads secrets from process.env.
try {
  const response = await fetch('/api/chat', { method: 'POST', ... });
} catch (error) {
  console.error("Error talking to Bijou:", error);
  return "Aiyo, server having hiccup. Give me a moment boss.";
}
```

### Error Message Style
- Use **Manglish** (Malaysian English) for user-facing errors
- Examples: "Aiyo, server having hiccup", "Walao, something went wrong boss"
- Maintain cultural authenticity with Malaysian context

## 🌏 Business Domain Context

This application serves the **Southeast Asian market** with specific cultural considerations:

### Manglish Integration
```typescript
const manglishKeywords = /walao|boss|can|settle|aiyo|fuyoh|best|swee|on|roger/i;
```

> The persona rules and forbidden phrases now live in the system prompt at
> `api/chat.js:32,97`. The client-side manglish detection in `DemoChat.tsx`
> is a visual-flourish only — the actual style enforcement happens
> server-side. See `audit-report.md` finding #11.

### Local Context
- Currency references in **RM (Malaysian Ringgit)**
- Location references: KLCC, Mont Kiara, Malaysia
- Malaysian flag color gradients in design

## 🔧 Development Notes

### Environment Variables (server-side only — never `VITE_*` prefix these)
- `CUSTOM_API_ENDPOINT`, `CUSTOME_API_KEY` — OmniRoute AI gateway
- `GEMINI_API_KEY_3/4` — direct Gemini fallback rotation
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` — server-side Supabase
- `RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_NOTIFY` — transactional email
- `STRIPE_SECRET_KEY` — early-adopter counter
- `INTERNAL_API_TOKEN` — shared secret for `api/send`, `api/onboarding/signup`, `api/demo`

> **2026-07-20:** The legacy typo `CUSTOME_API_ENDOINT` was renamed to
> `CUSTOM_API_ENDPOINT` in both `api/chat.js:96` and `.env`. Update any
> deploy environment that still has the old name. The `VITE_GEMINI_API_KEY`
> variable is gitignored but still exists in `.env`; Vite's `loadEnv` in
> `vite.config.ts` only exposes `VITE_PUBLIC_SITE_URL` via `define`, so no
> Gemini key is in the client bundle today. Rename to `GEMINI_API_KEY` in
> a follow-up to remove the footgun.

### File Naming
- Components: PascalCase (e.g. `WhatsAppLinkGenerator.tsx`)
- Services: camelCase (e.g. `gemini.ts`)
- Use `.tsx` for React components, `.ts` for utilities

### Performance Considerations
- Lazy load heavy components when possible
- Use Framer Motion's `AnimatePresence` for mount/unmount animations
- Optimize bundle size - current build uses Vite's tree shaking

## 🎯 Component Guidelines

### Large Components (>200 lines)
These components may need refactoring if modified:
- `OnboardingModal.tsx` (810 lines) — split into shell + flow hook + fields
- `Features.tsx` (708 lines)
- `ViralPillars.tsx` (648 lines)
- `Pricing.tsx` (552 lines)
- `WhatsAppLinkGenerator.tsx` (480 lines)
- `ComparisonTable.tsx` (468 lines)
- `FAQ.tsx` (422 lines)
- `LeadCaptureModal.tsx` (322 lines)
- `Footer.tsx` (318 lines)
- `SlideDeckModal.tsx` (315 lines)
- `LeadCaptureForm.tsx` (308 lines)
- `IntegrationForm.tsx` (307 lines)
- `InfoModal.tsx` (304 lines)
- `DemoChat.tsx` (286 lines) — Handle with care, contains main AI interaction logic
- `VoiceComingSoon.tsx` (263 lines)

## ⚠️ Important Notes

- **No testing framework** - Manual testing required
- **No linting/formatting** configured - Maintain existing code style manually
- **Single page application** - No routing, all navigation via state
- **Server-side env vars** must NEVER use the `VITE_` prefix (Vite would expose them)
- **Serverless API** at `api/*.js` (Vercel) is the trust boundary; treat all client input as hostile
- **`tsc --noEmit` does not check `api/*.js`** (those run in Node). Validate by exercising the endpoint.

## 🔍 Common Patterns

### Modal Pattern
```typescript
const [isModalOpen, setIsModalOpen] = useState(false);
const onOpenModal = () => setIsModalOpen(true);
// Pass onOpenModal to child components via props
```

### Loading States
Use Framer Motion's layout animations for smooth loading transitions:
```typescript
<AnimatePresence>
  {isLoading && (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      Loading...
    </motion.div>
  )}
</AnimatePresence>
```

Remember: This codebase prioritizes **user experience** and **cultural authenticity** for the Malaysian market. Maintain the established patterns for consistency and professional quality.
