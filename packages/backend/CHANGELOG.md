# Changelog — Bijou AI Enterprise

All notable changes are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) · Versioning: [SemVer](https://semver.org/spec/v2.0.0.html)

---

## [3.7.0] - 2026-03-10 (commits `43b3650`, `542b5bb`, `89964e2`, `eeac319`)

### Added

#### 🔐 Auth — Inline Password Change

- `POST /api/auth/change-password` — authenticated endpoint in `src/saas/auth_api.py`
  - Accepts `{new_password: str}` (min 8 chars) with `Authorization: Bearer <token>` header
  - Uses Supabase `auth.set_session(token) + auth.update_user({"password": ...})` — no email round-trip needed
- `GET /api/auth/me` — returns `{email, id}` for the current JWT holder

#### 🖥️ Settings > My Account — Email Display + Password Form

- Email is now resolved from: `JWT.email → JWT.sub → localStorage("tenant_email") → businessProfile.owner_email`
  - Magic-link users (who had no JWT email) now see their signup email from the DB profile
- Replaced single "Send Password Reset Email" button with a `<details>` accordion:
  - **Change Password** form (two password fields, client-side length + match validation, calls `/api/auth/change-password`)
  - **Send Password Reset Email Instead** as secondary option below
  - Uses `<details>/<summary>` HTML — no React hooks needed inside the IIFE renderer

#### 🧪 Test Infrastructure

- `tests/unit/test_payment_webhook_endpoint.py` — 4 new endpoint-level tests for `POST /api/payment/webhook`:
  - Missing `Stripe-Signature` header → 400 `{success: false}`
  - Invalid signature (service returns `None`) → 400 `{success: false}`
  - Valid signature → 200 `{success: true, received: true, event_id: "..."}`
  - Background processing error → still 200 (Stripe retry safety)
- `tests/unit/test_outreach_api.py` — expanded to **50 tests** covering all outreach endpoints end-to-end
- `tests/unit/test_call_handler.py` — **36 tests** covering `is_missed_call()` and `build_missed_call_context()` helpers

### Changed

#### 💳 Payment Webhook — Refactored for Testability

- `src/saas/payment_api.py` — extracted `StripeService` class with:
  - `verify_webhook_event(payload, sig_header) → dict | None` — signature check; dev-mode passthrough when `STRIPE_WEBHOOK_SECRET` unset
  - `process_webhook_event(event) → bool` — all Supabase DB updates for 4 Stripe event types
- `get_stripe_service() → StripeService` factory function (monkeypatched in tests)
- `stripe_webhook` endpoint now: reads sig header → calls service → returns `{success, received, event_id}` (was `{received: True}` — tests required the new format)
- Removed ~60 lines of inline dead code left over from prior refactor

### Fixed

- `test_payment_webhook_endpoint.py` import failed — `supabase` stub was missing `Client` attribute required by `dashboard_api_simple.py`
- Settings email field showed `"—"` for tenants who logged in via magic link (no email in JWT) — now falls back to `businessProfile.owner_email` from DB

### CI

- Removed `--ignore=tests/unit/test_payment_webhook_endpoint.py` from `.github/workflows/test-suite.yml`
  - Total covered tests in CI: **228 collected** (36 call_handler + 50 outreach + 4 payment webhook + rest)

---

## [3.6.0] - 2026-03-10 (commits `089a316`, `001c4f3`)

### Added

#### 🔔 Escalation Notification Bell (Dashboard)

- **Topbar bell icon** in `App()` component — live "new escalation" counter with red badge
- 30-second polling via `checkEscalationAlerts()` → `GET /api/dashboard/escalations?status=open`
- **Web Audio chirp** (880 Hz → 440 Hz sine wave) fires on new escalation arrival
- Bell renders in topbar next to hamburger menu on mobile; hidden if no alerts
- Badge count auto-clears when Escalations module is opened

#### 💰 Pricing Page (`/pricing`)

- `static/pricing.html` — **new full pricing page** (205 lines):
  - PRO tier: RM299/month (RM251/month billed yearly)
  - GROWTH tier: RM499/month (RM419/month billed yearly) — "Contact Sales" flow
  - Monthly / yearly toggle with calculated savings display
  - Stripe checkout via `POST /api/payment/checkout` — redirects to `data.url`
  - Tenant resolved from URL `?tenant_id=` or `localStorage`; JWT/Bearer auth headers sent
  - 14-day trial note; FPX/DuitNow mentioned
- `src/core/bijou.py` — `GET /pricing` route added after `/callback` route:
  ```python
  @app.get("/pricing", response_class=HTMLResponse)
  async def pricing_page():
      p = Path(__file__).parent.parent.parent / "static" / "pricing.html"
      if p.exists():
          return p.read_text()
      return RedirectResponse(url="/dashboard")
  ```

#### 📞 Missed Call Webhook Handler

- `src/core/bijou.py` — handles `event_type in ("call", "call.missed", "call.received", "call.rejected")` before the "skip non-message events" guard
- Synthesizes a `📞 MISSED_CALL` message and routes it into the existing AI missed-call follow-up logic
- No new DB tables or API endpoints needed — reuses the existing conversation pipeline

### Fixed

#### 🐛 422 Outreach Campaign Create

- **Root cause:** `createCampaign()` in `static/outreach.html` sent wrong field names (`campaign_name`, `message_template`, `daily_limit_per_contact`) — Pydantic raised 422 because required field `name` was absent.
- **Fix:** Rewrote payload to match `CampaignCreateRequest` model exactly:
  - `name` (was `campaign_name`)
  - `description` (was `message_template`)
  - `daily_limit` clamped to `ge=5, le=200` (was `daily_limit_per_contact: 1`)
  - `min_delay_seconds` with `ge=30`, `max_delay_seconds` with `ge=60`
  - `send_window_start: "09:00"`, `send_window_end: "21:00"` added

### Changed

#### 🎨 Settings UX Redesign

- **Layout:** 2-column grid → single column (`space-y-3`) for better readability on all screen sizes
- **Email Notifications card removed** — redundant; merged into the Email Configuration card below
- **Test email button** moved into "Email Configuration" card (was a standalone card)
- **"Tenant Info" card** renamed to **"My Account"**:
  - Email displayed from JWT decode (`atob(token.split('.')[1])`)
  - Name field shown from same JWT payload
  - **Password Reset button** added → calls Supabase Auth password reset flow

---

## [Unreleased] — Future Roadmap

### Planned

- `@bijou` operator command dispatch — async fix in `bijou.py:2130` (currently commented out, needs `ENABLE_BIJOU_COMMANDS=true` + async call site fix)
- Facebook / Google / LinkedIn Ads integrations (Phase 5)
- HubSpot / Slack / Google Sheets deep connectors
- Real-time analytics dashboard
- Automated monthly reporting engine
- Stripe billing portal embedded in dashboard
- Multi-language AI responses (BM, Tamil, Chinese per tenant)
- Telegram channel parity with WhatsApp feature set

---

## [3.5.0] - 2025-07-31

### Added

#### 💬 Live Chat Widget (help.html)

- `src/api/help_chat.py` — NEW: Bijou AI powered live chat backend:
  - `POST /api/help-chat/verify` — validates tenant email against `tenants.email`, returns `{verified, tenant_id, tenant_name, plan}`
  - `POST /api/help-chat/message` — Gemini 2.5 Flash REST, public system prompt (W3J/Bijou Q&A only) or tenant-aware prompt with full conversation history
  - `POST /api/help-chat/ticket` — saves escalations to `web_support_tickets` with `issue_type='chat-escalation'` and full chat transcript
- `static/help.html` — replaced floating WhatsApp button with purple "💬 Chat with Bijou" chat panel:
  - Welcome screen → Public or Tenant mode selector
  - Tenant: email verification flow → account-aware help
  - After 3 messages: "Still stuck? Create a support ticket →" CTA
  - Ticket form: pre-fills email/name for verified tenants, includes full chat transcript
- `src/core/bijou.py` — `help_chat_router` wired after `kb_import_router`

#### 📄 Document OCR — Gemini Multimodal (All File Types)

- `src/core/bijou.py` — entire document analysis block replaced with Gemini 2.5 Flash multimodal pipeline:
  - `application/pdf` + all image mimes → `gtypes.Part.from_bytes` inline → Gemini reads natively (works on scanned PDFs, photos of invoices, etc.)
  - DOCX → python-docx text extraction (fallback for Word files)
  - XLSX → openpyxl (reads up to 3 sheets × 50 rows each)
  - TXT/CSV/MD → direct UTF-8 decode
  - Unknown types → friendly "I can read PDFs, images, Word, Excel, text files" response

### Fixed

- `fly.production.toml` — added `strategy = "immediate"` to `[deploy]` — eliminates lease deadlock on single machine + volume deploys permanently
- `fly.staging.toml` — same `strategy = "immediate"` fix applied
- `src/saas/kb_import_api.py` — model corrected: `gemini-1.5-flash` → `gemini-2.5-flash`
- `database/migrations/030_add_chat_escalation_issue_type.sql` — new migration adds `'chat-escalation'` to `web_support_tickets.issue_type` CHECK constraint (was missing from migration 029, causing silent ticket failures)

---

## [3.4.0] - 2026-03-06

### Added

#### 🏠 PropertyGuru & Listing Importer

- `src/saas/kb_import_api.py` — new router (`/api/kb`) with two endpoints:
  - `POST /api/kb/import-listing` — scrape any property listing URL, extract visible text via stdlib html.parser, Gemini AI formats into structured KB article, inserts into `knowledge_documents` table
  - `POST /api/kb/import-text` — paste listing text directly; Gemini extracts and formats; inserts to `knowledge_documents`
  - Returns `needs_paste: true` when scrape is blocked (JS pages), triggering paste mode fallback in frontend
- `src/core/bijou.py` — `kb_import_router` wired after `support_router`
- `static/dashboard.html` — "🏠 Import Listing" tab added to `KnowledgeModule`:
  - New state: `importUrl`, `importText`, `importNote`, `importLoading`, `importResult`, `importNeedsPaste`
  - `importListing()` and `importListingText()` async functions
  - URL input panel with optional agent note field
  - Auto-switches to paste mode panel on `needs_paste` response
  - Yellow warning banner in paste mode with "Try URL Again" back button

#### 🆘 Help & Support System

- `static/help.html` — "🏠 Property Agents: Import Listings to Your AI" section (3 accordions):
  - URL method guide (6 step-guide cards)
  - Paste mode guide (4 step-guide cards)
  - Tips for best results (bullet list)
- `static/help.html` — Inline support form (accordion + submit to `/api/support/ticket`)
- `static/help.html` — Fixed accordion arrow rotation CSS bug; replaced placeholder screenshots with step-guide card layout
- `src/api/support.py` — `POST /api/support/ticket` → stores to `web_support_tickets` Supabase table
- `database/029_web_support_tickets.sql` — migration applied to production

#### 💳 Billing Portal

- `src/saas/payment_api.py` — `/api/payment/tenant/usage` now returns `has_subscription: bool(stripe_customer_id)`
- `static/dashboard.html` — billing section conditionally shows "Subscribe to a Plan →" (no Stripe customer) or "Manage Subscription →" (existing subscriber)

#### 🔐 Auth System (Phase 4.3 — already deployed v137)

- `src/saas/auth_api.py` — email/password signup, login, logout, refresh token endpoints
- `static/login.html`, `static/signup.html` — professional auth pages
- `static/dashboard.html` — reads JWT from localStorage, auto-logout on 401 → `/login`
- `src/core/dashboard_api_simple.py` — `verify_session()` supports both JWT Bearer and legacy magic-link token
- `database/019_tenant_users_auth.sql` — `tenant_users` table, RLS policies

---

## [3.3.0] - 2026-03-05

### Fixed — Bug Audit Batch (v158–v164)

**Dashboard (` static/dashboard.html`)**

- Fixed React error #31: `customer_context` JSONB guard (parse crash on escalations page)
- Fixed mobile footer cut-off on iOS: `height: calc(60px + env(safe-area-inset-bottom))` for bottom nav bar; `more-drawer bottom` and main scroll `padding-bottom` updated with safe-area offsets
- Fixed conversations `ORDER BY` column (`timestamp` → `created_at` — column did not exist, caused 400 errors)
- **Fixed `[IMPORTANT:]` / `[INSTRUCTION:]` internal AI injection messages leaking into dashboard chat view and conversation list previews** — messages starting with these prefixes are now filtered from the chat render and replaced with `🎤 Voice message` in the preview strip

**Backend (`src/core/bijou.py`)**

- Removed broken `pg_extension_exists` RPC check (returned 404 on every startup, caused log noise)
- Fixed `_signal_handler` double-shutdown: removed `sys.exit(0)` call that caused "Task exception was never retrieved" asyncio errors
- Added `_bg()` wrapper for fire-and-forget async tasks to suppress `CancelledError` gracefully on shutdown
- Fixed `_wa_keepalive_monitor` to catch `CancelledError` at `asyncio.sleep` (was causing unhandled exception on shutdown)

**Bridge keepalive (`src/core/bijou.py`)**

- Removed auth headers from `/health` keepalive requests (bridge returns 400 when auth sent to health endpoint — was triggering false alarm reconnect loop)

**Webhook logging (`src/core/bijou.py`)**

- Downgraded webhook parse error log level from `ERROR` to `WARNING` (not actionable, was flooding error logs)

**Auth & Onboarding (`src/saas/auth_api.py`)**

- Added `client_config` auto-creation step in signup endpoint — new tenants now get a default config row on registration instead of missing it silently

**Escalation (`src/saas/handover_system.py`, `src/saas/ai_handover_detector.py`)**

- Removed `rights`, `legal`, `court` from legal keywords — too broad for real estate context ("Airbnb rights", "court yard", etc.)
- Legal keywords now limited to: `lawsuit`, `sue`, `lawyer`, `attorney`, `court order`, `legal action`
- Raised complex multi-part message threshold: 500 chars + 3 questions → 900 chars + 6 questions (was triggering false escalations on normal multi-part enquiries)
- Removed `"talk to someone"` and `"talk to a person"` from `_ESCALATION_PHRASES` (fired on `"Can I talk to someone about the apartment?"`)

---

## [3.1.0] - 2026-02-26

### Added — Operator WhatsApp Command Interface

**`@bijou` owner commands** (sent from the owner's own WhatsApp — `src/saas/command_handler.py`):
| Command | Description |
|---|---|
| `@bijou bookings` | Lists today's call bookings for the tenant |
| `@bijou crm <name or phone>` | Looks up a contact in the tenant's CRM |
| `@bijou send <phone/name> > <message>` | Sends a WhatsApp message to any contact via bridge |
| `@bijou confirm <booking-id>` | Marks a booking as in_progress by short-ID prefix |
| `@bijou help` | Full command reference |
| `@bijou pause` | Pauses Bijou for the tenant (existing) |
| `@bijou resume` | Resumes Bijou |

- All commands are **owner-only** (JID matched against `owner_whatsapp_jid`)
- `CommandHandler` now receives `db_conn`, `bridge_url`, `bridge_user`, `bridge_password` at init
- `bijou.py` passes `db_conn=self.db_conn` to `CommandHandler` at instantiation

### Fixed — Multi-Tenant Isolation in Command Handler

- **Removed `_get_tenant_id()` method** — the reverse-lookup (owner JID → tenants table → return first match) was a cross-tenant data leak risk in multi-tenant deployment
- `handle_command(message, chat_jid, sender, tenant_id: str = "")` — `tenant_id` now flows in from the call chain (resolved per-message from `whatsapp_devices` table)
- `_handle_bijou_command(cmd, tenant_id: str = "")` — same
- All `_cmd_*` methods: accept `tenant_id` as explicit param; validate non-empty before any DB query; every query has `.eq("tenant_id", tenant_id)` as mandatory filter; return safe error if `tenant_id` is empty
- **Rule enforced**: no method inside `CommandHandler` may derive or lookup `tenant_id` itself

**Known gap**: `@bijou` dispatch in `bijou.py:2130` is still commented out — `process_message` is synchronous. Requires async fix before commands activate in production. Tracked in roadmap.

---

## [3.0.5] - 2026-02-25 (commits `7af0106`, `0a65cca`)

### Added — Editable Call Settings Panel

**`static/dashboard.html` — Availability tab settings:**

- Call settings panel is now **editable** (was static display-only)
- Added `editingSettings`, `settingsDraft`, `savingSettings` Vue state
- Added `saveSettings()` async function → `PUT /api/call-booking/availability/settings`
- Edit/Cancel/Save toggle buttons in panel header
- Editable fields: `buffer_minutes` (int), `max_calls_per_day` (int), `max_calls_per_hour` (int), `advance_booking_days` (int), `allow_same_day_booking` (select yes/no), `timezone` (text)
- Backend (`call_booking_api.py` line 729) was already complete — only UI was missing

### Added — CRM Editable Contact Names + Enriched Inbox

**CRM / Contacts (LeadsModule in dashboard.html):**

- Contact names are now **editable inline** — `editName` state, name input in edit form, `saveEdit()` sends `name` in `PATCH /api/contacts/{jid}` body
- `ContactUpdate` model in `contacts_api.py` already accepted `name` field

**Inbox enrichment:**

- `GET /api/dashboard/conversations` (`dashboard_api_simple.py`) now queries the `contacts` table after building the conversation list
- Enriches each conversation with `contact_name` (overrides phone-derived display name if a saved name exists) and `contact_tag`
- Best-effort enrichment — wrapped in try/except, non-fatal if contacts table unavailable

**Chat header tag badge:**

- Active conversation now shows `sel.contact_tag` as a coloured pill badge in the chat header
- `TAG_COLORS` map promoted to global scope (before `// Auth` block) — was previously only accessible inside LeadsModule

---

## [3.0.4] - 2026-02-24 (commit `6ec3df7`)

### Added

- `DELETE /api/knowledge/{id}` endpoint — was returning 404 (endpoint was missing, only `GET`/`POST` existed)

### Fixed

- All `alert()` calls across `dashboard.html` replaced with a non-blocking **Toast notification system**
  - `showToast(message, type)` function with auto-dismiss (3 s)
  - Types: `success` (green), `error` (red), `info` (blue)
  - Toast container positioned top-right, CSS animated fade in/out

---

## [3.0.3] - 2026-02-23 (commit `022ed96`)

### Added — Knowledge Module Enhancements

- **Expanded file type support**: PDF, TXT, DOCX, CSV, XLSX, PNG, JPG, JPEG, GIF, WEBP, MP3, MP4, MOV (was PDF + TXT only)
- **Increased upload limit**: 10 MB per file (was 5 MB)
- **Note/trigger field**: each knowledge item can have a `note` and `trigger_phrase` for contextual injection
- **Owner WhatsApp notification on upload**: when any knowledge file is uploaded/updated, the tenant `owner_whatsapp_jid` receives a WA message confirming the update

### Added — Media Library Module

- `SEND_FILE` token support in AI response pipeline — Bijou can now send files to customers
- `MediaModule` in dashboard: upload, list, delete media assets
- `PATCH /api/media/{id}` keyword tagging — associate trigger keywords with media items
- New UI section: Media Library tab in dashboard

### Fixed

- Image icon rendering in chat (was showing broken icon for image messages)

---

## [3.0.2] - 2026-02-22 (commit `8911a4b`)

### Added — Mobile UX + PWA

- **WhatsApp-style inbox layout** — conversation list on left, chat pane on right (responsive)
- **Bottom navigation bar** on mobile — Inbox, Contacts, Escalations, Settings as tab bar
- **PWA install fix** — `manifest.json` `start_url` corrected to `/`, install prompt shown on mobile
- Collapsible sidebar for tablet breakpoints

---

## [3.0.1] - 2026-02-20 (commits `524a62a`, `ba55d92`)

### Fixed — Production Bugs

- `[BREAK]` token incorrectly sent as literal text to customers — resolved, break is now silent
- WhatsApp disconnect/reconnect sync — bridge status updates dashboard correctly
- Keepalive monitor — prevents cold-start disconnects on Fly.io

### Added

- QR auto-refresh every 25 s with countdown timer (for device pairing screen)
- Root folder enforcement: `scripts/static_audit.py` CI check blocks files placed outside their correct folders

---

## [3.0.0] - 2026-02-18 (commits `05aa260`, `66c551f`)

### Added — Full Contacts CRM

- `database/migrations/026_contacts_crm_table.sql` — `contacts` table with `tenant_id`, `jid`, `name`, `phone`, `tag` (lead/customer/vip/cold), `notes`, `created_at`, `updated_at`
- `src/saas/contacts_api.py` — full CRUD: `GET`, `POST`, `PATCH /{jid}`, `DELETE /{jid}`, bulk tag update
- `ContactUpdate` Pydantic model supports partial updates (all fields optional)
- Dashboard Contacts tab: searchable, filterable table, tag colour badges, inline edit, delete

---

## [2.2.3] - 2026-02-14 (commits `1b3f3f4`, `99b959e`, `90f6d69`)

### Added

- Document, location, and vCard message handlers — Bijou acknowledges/processes all WhatsApp message types
- Auto-save contacts from incoming messages — any new JID auto-creates a contact record
- CI health check timeout extended: 10 s → 30 s for Fly.io cold starts

### Fixed

- Re-applied 3 lost hotfixes (circuit_breaker, gemini_timeout, chat_jid)
- Un-skipped 3 regression tests

---

## [2.2.2] - 2026-02-12 (commit `4fbfb29`)

### Changed

- `PUBLIC_URL` updated to `app.mybijou.xyz` in production config
- Hardened WhatsApp JID lookup for multi-device sessions
- GOWA v8.x webhook schema support
- Bridge authentication — Basic Auth + `X-Device-Id` header

---

## [2.2.1] - 2026-02-07

### Added - Phase 4.5: Automated Testing Suite

- **Test Infrastructure:**
  - 21 comprehensive E2E tests covering all major APIs
  - `tests/test_e2e_full_suite.py` with 100% pass rate
  - `tests/conftest.py` with async support and fixtures
  - `tests/fixtures/test_tenants.py` with 4 synthetic business tenants
  - `tests/mocks/whatsapp_mock.py` for WhatsApp bridge simulation

- **CI/CD Automation:**
  - `.github/workflows/test-suite.yml` for automated testing
  - Multi-Python version testing (3.10, 3.11, 3.12)
  - Coverage reporting (Codecov integration)
  - Linting integration (Ruff, Black, isort)

- **Test Runners:**
  - `run_tests.bat` for Windows one-command testing
  - `run_tests.sh` for Unix one-command testing
  - `install_test_deps.ps1` for dependency installation
  - `pytest.ini` for test configuration

- **Documentation:**
  - `START_HERE.md` - Single source of truth for project status
  - `DEPLOYMENT.md` - Comprehensive deployment guide
  - `CHANGELOG.md` - This file
  - `PROJECT_TRACKER.md` - Master status tracker (353 lines)
  - `CLEANUP_REPORT.md` - Documentation consolidation plan (382 lines)
  - `PHASE_4.5_DEPLOYMENT_SUMMARY.md` - Complete phase summary
  - `docs/archive/README.md` - Archive disclaimer
  - Updated `BIJOU_PRODUCT_BIBLE` to v2.2.1

### Changed

- **Test Coverage:** Established 19% baseline coverage
  - Settings API: 68%
  - Onboarding API: 47%
  - Knowledge Upload: 46%
  - Knowledge API: 44%
  - Proactive API: 42%
  - Message Filter: 36%

- **Documentation Consolidation:**
  - Reduced from 27+ files to 12 core documents (-56%)
  - Deleted 2 duplicate status files
  - Archived 44 outdated documentation files

### Fixed

- Async test support with pytest-asyncio and event loop fixtures
- Supabase mock chaining for `table().select().eq().execute()` patterns
- Field name mismatches between uploader and API (`file_size_kb` vs `content_length`)
- Zed config JSON syntax (trailing commas, tasks.json array structure)
- PyPDF2/pytesseract optional dependencies handling in tests

### Deployment

- ✅ Deployed to staging: `bijou-staging.fly.dev`
- ✅ Machine ID: `080e091f05d6e8`
- ✅ Region: Singapore (sin)
- ✅ Health check: PASSING

---

## [2.2.0] - 2026-02-05

### Added - Phase 4: Marketing & Analytics

- **Analytics Infrastructure:**
  - `analytics_events` table in Supabase
  - Event tracking for lead captures, escalations, messages
  - Tenant-specific analytics isolation

- **Proactive Messaging API:**
  - `src/saas/proactive_api.py` for scheduled campaigns
  - Bulk message scheduling
  - Campaign management endpoints

- **Settings API:**
  - `src/saas/settings_api.py` for tenant configuration
  - Testing mode toggle (restrict to test numbers)
  - Ignore list management (block spam numbers)
  - Business hours configuration

- **Knowledge Management:**
  - `src/saas/knowledge_api.py` for knowledge base operations
  - PDF/TXT upload support
  - Combined knowledge retrieval
  - Synthetic training data generation

### Changed

- Updated Product Bible to v2.2.0
- Enhanced multi-tenant routing logic
- Improved persona management system

---

## [2.1.0] - 2026-01-31

### Added - Phase 3: SaaS Infrastructure

- **Multi-Tenancy:**
  - `src/saas/tenant_router.py` for message routing by WhatsApp JID
  - Tenant isolation in database queries
  - Per-tenant configuration and settings

- **Onboarding API:**
  - `src/saas/onboarding_api.py` with self-service signup
  - QR code generation for WhatsApp connection
  - Tenant creation and validation
  - Onboarding status tracking

- **Persona Management:**
  - `src/saas/persona_manager.py` for multi-persona support
  - Owner commands (`/owner help`, `/owner status`, `/owner stats`)
  - Dynamic persona switching based on context

- **Command Handler:**
  - `src/saas/command_handler.py` for `@bijou` commands
  - Pause/resume functionality
  - Manual mode support

### Fixed

- App startup crash (NameError in bijou.py)
- Missing media handler in deployment
- Missing tool orchestrator in deployment
- Port configuration for Fly.io (default to 8080)
- Bridge URL initialization sequence
- Type annotation forward reference errors

### Deployment

- Fixed offline issue on bijou-staging
- Successfully deployed to https://bijou-staging.fly.dev
- Verified all systems operational

---

## [2.0.0] - 2026-01-28

### Added - Phase 2: Channels & Adapters

- **WhatsApp Integration:**
  - Real-time webhook message processing
  - Media handling (images, audio, voice notes, documents)
  - Message status tracking (sent, delivered, read)
  - Group message support

- **WhatsApp Bridge:**
  - Separate Go service for WhatsApp API connection
  - QR code pairing for new sessions
  - Session persistence and recovery
  - Multi-device support

- **Telegram Support (Future):**
  - Placeholder for Telegram bot integration
  - Unified message format across channels

### Changed

- Migrated from polling to webhook-driven architecture
- Improved message queue handling
- Enhanced error recovery for network issues

---

## [1.5.0] - 2026-01-20

### Added - Phase 1: Core Intelligence

- **AI Engine:**
  - Gemini 2.5 Flash integration for fast responses
  - Multi-language support (English, Malay, Chinese, Tamil)
  - Manglish detection and processing
  - Context retention across conversations

- **TRACE Framework:**
  - Trust-building through empathy
  - Rapport establishment
  - Active listening signals
  - Contextual responses
  - Empathetic closing

- **Tool Orchestration:**
  - `src/core/tool_orchestrator.py` for dynamic tool execution
  - Lead capture tool with quality scoring
  - Appointment booking tool (skeleton)
  - Knowledge retrieval tool

- **Database Layer:**
  - Supabase integration for persistence
  - Conversation history storage
  - Message threading and context
  - Tenant data isolation

### Changed

- Switched from OpenAI to Gemini for cost optimization
- Improved conversation memory management
- Enhanced language detection accuracy

---

## [1.0.0] - 2025-11-15

### Added - Initial Release

- **Core Application:**
  - `src/core/bijou.py` - Main FastAPI application
  - Basic message handling
  - Simple AI responses
  - WhatsApp polling (legacy approach)

- **Infrastructure:**
  - Dockerfile for containerization
  - Fly.io deployment configuration
  - Supabase database setup
  - Environment variable management

- **Documentation:**
  - Initial README
  - Basic deployment instructions

### Known Issues

- Polling creates latency (fixed in v2.0.0)
- No multi-tenant support (fixed in v2.1.0)
- Limited language support (fixed in v1.5.0)

---

## Version History Summary

| Version   | Date       | Focus                 | Status      |
| --------- | ---------- | --------------------- | ----------- |
| **2.2.1** | 2026-02-07 | Automated Testing     | ✅ Current  |
| 2.2.0     | 2026-02-05 | Marketing & Analytics | ✅ Complete |
| 2.1.0     | 2026-01-31 | SaaS Infrastructure   | ✅ Complete |
| 2.0.0     | 2026-01-28 | Channels & Adapters   | ✅ Complete |
| 1.5.0     | 2026-01-20 | Core Intelligence     | ✅ Complete |
| 1.0.0     | 2025-11-15 | Initial Release       | ✅ Complete |

---

## Deprecation Notices

### Deprecated in 2.2.0

- **Polling mode:** Removed in favor of webhooks (use `WEBHOOK_MODE=true`)
- **Single-tenant mode:** Deprecated in favor of multi-tenant (use `ENABLE_MULTI_TENANT=true`)

### Planned Deprecations

- **Legacy anon keys:** Will be replaced by publishable keys in v3.0.0
- **Synchronous message handling:** Will be fully async in v3.0.0

---

## Migration Guides

### Upgrading from 2.2.0 to 2.2.1

No breaking changes. Simply redeploy:

```bash
C:\Users\w3jbt\.fly\bin\flyctl.exe deploy --app bijou-staging --config fly.staging.toml
```

### Upgrading from 2.1.0 to 2.2.0

1. Run new database migrations (analytics_events table)
2. Add new environment variables: `ENABLE_ANALYTICS=true`
3. Deploy updated code

### Upgrading from 2.0.0 to 2.1.0

1. Run database migrations (tenants, tenant_users tables)
2. Add environment variable: `ENABLE_MULTI_TENANT=true`
3. Update WhatsApp bridge to support multi-session
4. Deploy updated code

---

## Contributors

- **W3J Bijou AI Team** - Core development
- **AI Assistants** - Code generation and testing support

---

## License

Proprietary - All rights reserved

---

**Maintained by:** W3J Bijou AI
**Last Updated:** 2026-02-07
**Format Version:** 1.0.0 (Keep a Changelog)
