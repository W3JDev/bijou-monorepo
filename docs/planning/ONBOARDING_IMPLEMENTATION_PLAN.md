# BIJOU AI ONBOARDING PORTAL - 5-DAY IMPLEMENTATION PLAN

**Project:** Automated Self-Serve Onboarding System  
**Timeline:** 5 working days (40 hours)  
**Team:** Solo developer (Muhammad Nurunnabi / Jewel)  
**Target:** Staging deployment with full onboarding flow  

---

## 📊 SPRINT OVERVIEW

| Day | Focus Area | Deliverables | Status Check |
|-----|-----------|-------------|--------------|
| **1** | Database & Backend Foundation | Migrations, RLS policies, core API endpoints | Run pytest + manual SQL tests |
| **2** | WhatsApp Integration | QR flow, device provisioning, status polling | Test with real WhatsApp number |
| **3** | Knowledge & CRM Features | File upload, embedding generation, contact import | Upload 5 test PDFs |
| **4** | Frontend Wizard | React components, wizard flow, API integration | Complete onboarding test run |
| **5** | Integration & Polish | Stripe billing, testing, deployment to staging | Health checks pass |

---

## DAY 1: DATABASE & BACKEND FOUNDATION (8 hours)

### Morning (4 hours): Database Migrations

**Tasks:**
1. ✅ **Create migration files** (1 hour)
   - [ ] `001_crm_contacts.sql`
   - [ ] `002_integrations.sql`
   - [ ] `003_billing_subscriptions.sql`
   - [ ] `004_audit_logs.sql`
   - [ ] `005_onboarding_progress.sql`
   - [ ] `006_update_existing_tables.sql`
   - [ ] `007_analytics_views.sql`

2. ✅ **Apply migrations to Supabase** (1 hour)
   ```bash
   # From project root
   cd database/migrations
   
   # Apply each migration via Supabase dashboard SQL editor
   # OR use Supabase CLI:
   supabase db push
   ```

3. ✅ **Test RLS policies** (1 hour)
   - Create test tenant in Supabase dashboard
   - Try to access data without `tenant_id` filter (should fail)
   - Verify service role bypass works
   - Test cascade deletes (tenant → contacts → escalations)

4. ✅ **Create helper functions** (1 hour)
   - `update_updated_at_column()` trigger function
   - `is_service_role()` auth check
   - `current_tenant_id()` context getter
   - `cleanup_old_audit_logs()` retention policy

**Validation:**
```sql
-- Check all tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Verify RLS enabled
SELECT tablename, rowsecurity FROM pg_tables 
WHERE schemaname = 'public';

-- Test tenant isolation
SET app.current_tenant_id = 'test-tenant-id';
SELECT * FROM crm_contacts; -- Should only return test tenant data
```

### Afternoon (4 hours): Backend API Endpoints

**Tasks:**
1. ✅ **Create `onboarding_api_v2.py`** (2 hours)
   - Implement all Pydantic models (SignupRequest, AIPersonaConfig, etc.)
   - Write POST /api/onboarding/v2/signup endpoint
   - Write GET /api/onboarding/v2/status/{token} endpoint
   - Add proper error handling and logging

2. ✅ **Implement helper functions** (1 hour)
   - `log_audit_event()` for GDPR compliance
   - `generate_system_prompt()` for persona config
   - `provision_whatsapp_device()` background task
   - `send_welcome_email()` placeholder

3. ✅ **Register routes in `bijou.py`** (30 min)
   ```python
   from src.saas.onboarding_api_v2 import router as onboarding_v2_router
   app.include_router(onboarding_v2_router)
   ```

4. ✅ **Write unit tests** (30 min)
   ```bash
   # Create test file
   touch tests/unit/test_onboarding_api_v2.py
   
   # Run tests
   pytest tests/unit/test_onboarding_api_v2.py -v
   ```

**Validation:**
```bash
# Start local server
cd w3j-bijou-enterprise
python src/core/bijou.py

# Test signup endpoint
curl -X POST http://localhost:8080/api/onboarding/v2/signup \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Test Business",
    "email": "test@example.com",
    "phone": "+60123456789",
    "owner_name": "Test Owner"
  }'

# Check response contains signup_token and onboarding_url
```

**Blockers:**
- ⚠️ Supabase service key must be configured in `.env`
- ⚠️ Ensure `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set

**End-of-Day Deliverables:**
- ✅ 7 migration files applied to Supabase
- ✅ `onboarding_api_v2.py` with signup + status endpoints
- ✅ Unit tests passing (at least signup flow)
- ✅ Audit logs recording tenant creation

---

## DAY 2: WHATSAPP INTEGRATION (8 hours)

### Morning (4 hours): Bridge Device Provisioning

**Tasks:**
1. ✅ **Review existing `whatsapp_bridge_client.py`** (30 min)
   - Verify `create_device()` method exists
   - Check `get_qr_code()` implementation
   - Test `initialize_session()` works

2. ✅ **Implement QR endpoint** (1.5 hours)
   - Write GET /api/onboarding/v2/whatsapp/qr/{token}
   - Handle QR refresh logic (60s expiry)
   - Update `whatsapp_devices` table with status changes
   - Return QR image URL from bridge

3. ✅ **Background device provisioning** (1 hour)
   - Complete `provision_whatsapp_device()` function
   - Call bridge API to create device
   - Store device_id in `whatsapp_devices` table
   - Handle errors gracefully (log + update status)

4. ✅ **Status polling mechanism** (1 hour)
   - Add GET /api/onboarding/v2/whatsapp/status/{token}
   - Return connection status (provisioning → qr_ready → connected)
   - Update `tenants.whatsapp_connected_at` on success
   - Mark onboarding step as completed

**Validation:**
```bash
# Test device provisioning
curl -X POST http://localhost:8080/api/onboarding/v2/signup \
  -H "Content-Type: application/json" \
  -d '{"business_name": "QR Test", "email": "qr@test.com", "phone": "+60123456789", "owner_name": "Test"}'

# Get signup_token from response
TOKEN="<signup_token>"

# Poll for QR code (should return qr_ready after ~5s)
curl http://localhost:8080/api/onboarding/v2/whatsapp/qr/$TOKEN

# Scan QR with real WhatsApp (use test number)
# Poll again (should return connected)
curl http://localhost:8080/api/onboarding/v2/whatsapp/qr/$TOKEN
```

### Afternoon (4 hours): Webhook Integration

**Tasks:**
1. ✅ **Test bridge webhook flow** (1 hour)
   - Verify bridge sends POST /api/webhook on message receive
   - Check existing webhook handler in `bijou.py`
   - Ensure device_id → tenant_id mapping works
   - Test with ngrok if local testing needed

2. ✅ **Add QR connection webhook** (1 hour)
   - Bridge should notify when QR is scanned
   - Update `whatsapp_devices.status` = 'connected'
   - Store `whatsapp_jid` from bridge
   - Trigger onboarding progress update

3. ✅ **Error handling** (1 hour)
   - Handle QR expiry (refresh automatically)
   - Handle bridge downtime (retry provisioning)
   - Log all bridge API errors
   - Update `connection_errors` JSONB field

4. ✅ **Write integration tests** (1 hour)
   ```bash
   # Create test file
   touch tests/integration/test_whatsapp_provisioning.py
   
   # Test full flow: signup → provision → QR → connect
   pytest tests/integration/test_whatsapp_provisioning.py -v
   ```

**Validation:**
- [ ] Real WhatsApp number can scan QR and connect
- [ ] `whatsapp_devices` table shows status = 'connected'
- [ ] `tenants.whatsapp_jid` populated with correct JID
- [ ] Onboarding progress shows `step_whatsapp_completed = true`

**Blockers:**
- ⚠️ Requires GOWA bridge running and accessible
- ⚠️ Bridge must have POST /api/device endpoint
- ⚠️ Need real WhatsApp number for testing (cannot use same number twice)

**End-of-Day Deliverables:**
- ✅ WhatsApp QR endpoint returning valid QR codes
- ✅ Device provisioning working end-to-end
- ✅ Status polling shows real-time connection updates
- ✅ At least 1 successful WhatsApp connection test

---

## DAY 3: KNOWLEDGE BASE & CRM (8 hours)

### Morning (4 hours): Knowledge Base Upload

**Tasks:**
1. ✅ **Implement file upload endpoint** (1.5 hours)
   - Write POST /api/onboarding/v2/knowledge/upload/{token}
   - Accept multipart/form-data with files
   - Validate file types (PDF, DOCX, TXT, CSV, XLSX)
   - Enforce 10MB per file, 50 files max limits
   - Store file metadata in `knowledge_documents` table

2. ✅ **Text extraction logic** (1.5 hours)
   - Review existing `knowledge_engine.py`
   - Implement `extract_text()` for each file type:
     - PDF: PyPDF2 or pdfplumber
     - DOCX: python-docx
     - TXT: direct read
     - CSV/XLSX: pandas (extract as text)
   - Handle extraction errors gracefully

3. ✅ **Background processing task** (1 hour)
   - Complete `process_knowledge_file()` function
   - Extract text from uploaded file
   - Chunk text (1000 tokens using tiktoken)
   - Generate embeddings (OpenAI ada-002 or Gemini)
   - Store in `knowledge_bases` table with VECTOR type

**Validation:**
```bash
# Upload test PDF
curl -X POST http://localhost:8080/api/onboarding/v2/knowledge/upload/$TOKEN \
  -F "files=@test_document.pdf" \
  -F "category=faq" \
  -F "tags=onboarding,test"

# Check database
SELECT id, filename, file_size_kb FROM knowledge_documents 
WHERE tenant_id = '<tenant_id>';

# Verify embedding generated (wait 30s for background task)
SELECT id, title, content FROM knowledge_bases 
WHERE tenant_id = '<tenant_id>' 
LIMIT 5;
```

### Afternoon (4 hours): CRM Contact Import

**Tasks:**
1. ✅ **Implement CRM import endpoint** (1.5 hours)
   - Write POST /api/onboarding/v2/crm/import/{token}
   - Accept JSON array of contacts
   - Validate phone numbers (E.164 format)
   - Validate emails (RFC 5322)
   - Check for duplicates if `skip_duplicates = true`

2. ✅ **Bulk insert logic** (1 hour)
   - Batch insert contacts (100 at a time)
   - Handle duplicate errors (skip or upsert)
   - Apply tags (merge with `tag_all_with`)
   - Set default `lead_source = 'import'`

3. ✅ **CSV parsing helper** (1 hour)
   - Create frontend CSV parser (papaparse library)
   - Map CSV columns to contact fields
   - Validate CSV format (name, phone, email required)
   - Preview import (show first 10 rows)

4. ✅ **Write tests** (30 min)
   ```python
   # tests/unit/test_crm_import.py
   def test_import_contacts_bulk():
       contacts = [
           {"name": "John Doe", "email": "john@example.com"},
           {"name": "Jane Smith", "phone": "+60123456789"}
       ]
       response = client.post(f"/api/onboarding/v2/crm/import/{token}", json={
           "contacts": contacts,
           "skip_duplicates": True
       })
       assert response.status_code == 200
       assert response.json()["imported_count"] == 2
   ```

**Validation:**
```bash
# Import test contacts
curl -X POST http://localhost:8080/api/onboarding/v2/crm/import/$TOKEN \
  -H "Content-Type: application/json" \
  -d '{
    "contacts": [
      {"name": "Test Contact 1", "email": "test1@example.com", "tags": ["test"]},
      {"name": "Test Contact 2", "phone": "+60123456789"}
    ],
    "skip_duplicates": true
  }'

# Check database
SELECT name, email, phone, tags FROM crm_contacts 
WHERE tenant_id = '<tenant_id>';
```

**Blockers:**
- ⚠️ Requires embedding API key (OpenAI or Gemini)
- ⚠️ Large file uploads may timeout (need to optimize)
- ⚠️ CSV parsing needs frontend library (papaparse)

**End-of-Day Deliverables:**
- ✅ File upload endpoint accepting PDF/DOCX/TXT
- ✅ Text extraction working for at least PDF + TXT
- ✅ Embeddings generated and stored in database
- ✅ CRM import handling 100+ contacts without errors

---

## DAY 4: FRONTEND WIZARD (8 hours)

### Morning (4 hours): React Setup & Core Components

**Tasks:**
1. ✅ **Initialize Vite + React project** (30 min)
   ```bash
   cd w3j-bijou-enterprise/frontend
   npm create vite@latest onboarding -- --template react-ts
   cd onboarding
   npm install
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```

2. ✅ **Install shadcn/ui** (30 min)
   ```bash
   npx shadcn-ui@latest init
   npx shadcn-ui@latest add button input card form progress label select textarea
   ```

3. ✅ **Setup TanStack Query** (30 min)
   ```bash
   npm install @tanstack/react-query axios zustand react-hook-form zod
   ```

4. ✅ **Create API client** (1 hour)
   - Write `src/lib/api.ts` with axios instance
   - Implement error handling (HTTPException → toast notifications)
   - Add request interceptors (auth headers if needed)
   - Create type-safe API functions

5. ✅ **Build wizard layout** (1.5 hours)
   - Create `ProgressBar.tsx` component (7 steps)
   - Create `StepNavigation.tsx` (Next, Back buttons)
   - Create `WizardLayout.tsx` (sidebar + main content)
   - Implement Zustand store for wizard state

**Validation:**
```bash
npm run dev
# Visit http://localhost:5173
# Should see wizard layout with progress bar
```

### Afternoon (4 hours): Wizard Step Components

**Tasks:**
1. ✅ **SignupStep.tsx** (45 min)
   - Form with business_name, email, phone, owner_name
   - React Hook Form + Zod validation
   - Submit to POST /api/onboarding/v2/signup
   - Store signup_token in Zustand store
   - Auto-navigate to WhatsApp step

2. ✅ **WhatsAppQRStep.tsx** (1 hour)
   - Display QR code image from API
   - Poll GET /api/onboarding/v2/whatsapp/qr/{token} every 3s
   - Show connection status (provisioning → qr_ready → connected)
   - Add "Refresh QR" button (sets `?refresh=true`)
   - Auto-proceed when status = 'connected'

3. ✅ **KnowledgeUploadStep.tsx** (45 min)
   - React Dropzone for file drag-drop
   - Show file list with size + type
   - Upload to POST /api/onboarding/v2/knowledge/upload/{token}
   - Display upload progress (use axios onUploadProgress)
   - Show processing status message

4. ✅ **PersonaConfigStep.tsx** (45 min)
   - Form with tone selector (radio buttons)
   - Personality traits (multi-select checkboxes)
   - Response length slider
   - Manglish toggle switch
   - Preview system prompt (read-only textarea)

5. ✅ **CRMImportStep.tsx** (45 min)
   - CSV file upload (papaparse)
   - Preview table (first 10 rows)
   - Column mapping UI (if needed)
   - Submit to POST /api/onboarding/v2/crm/import/{token}
   - Show import summary (imported, skipped, errors)

**Validation:**
- [ ] Signup form validates email format
- [ ] WhatsApp QR appears within 5 seconds
- [ ] File upload shows progress bar
- [ ] Persona config preview updates in real-time
- [ ] CRM import shows error messages for invalid rows

**Blockers:**
- ⚠️ Need API running on localhost:8080 for testing
- ⚠️ CORS must allow http://localhost:5173 origin

**End-of-Day Deliverables:**
- ✅ React app running with all 7 wizard steps
- ✅ API integration working for signup + WhatsApp QR
- ✅ File upload functional (at least for TXT files)
- ✅ Navigation between steps working (Next, Back buttons)

---

## DAY 5: BILLING, TESTING & DEPLOYMENT (8 hours)

### Morning (4 hours): Stripe Integration & Final Steps

**Tasks:**
1. ✅ **IntegrationsStep.tsx** (1 hour)
   - Google Calendar integration (calendar_id input)
   - Webhook URL input + test button
   - Submit to POST /api/onboarding/v2/integrations/setup/{token}
   - Show connection test results

2. ✅ **BillingStep.tsx** (1.5 hours)
   - Plan selection cards (Free, Pro $49, Enterprise $199)
   - Feature comparison table
   - Stripe Elements integration (payment form)
   - Submit to POST /api/onboarding/v2/billing/checkout/{token}
   - Redirect to Stripe Checkout

3. ✅ **Stripe webhook handler** (1 hour)
   - Implement POST /api/webhooks/stripe endpoint
   - Verify webhook signature (STRIPE_WEBHOOK_SECRET)
   - Handle `checkout.session.completed` event
   - Update `billing_subscriptions` table
   - Mark onboarding as completed
   - Send confirmation email

4. ✅ **Success page** (30 min)
   - Create `OnboardingComplete.tsx` component
   - Show success message + next steps
   - Link to dashboard (or placeholder)
   - Confetti animation (react-confetti)

**Validation:**
```bash
# Test Stripe checkout (use test mode)
# Visit wizard, complete all steps
# Select Pro plan
# Enter test card: 4242 4242 4242 4242
# Verify redirect to success page

# Check database
SELECT * FROM billing_subscriptions WHERE tenant_id = '<tenant_id>';
SELECT onboarding_completed FROM onboarding_progress WHERE tenant_id = '<tenant_id>';
```

### Afternoon (4 hours): Testing & Deployment

**Tasks:**
1. ✅ **End-to-end testing** (1.5 hours)
   - Create `tests/e2e/test_onboarding_flow.py`
   - Test full flow: signup → WhatsApp → knowledge → persona → CRM → billing
   - Use Playwright or Selenium for browser automation
   - Verify all database records created correctly

2. ✅ **Manual testing checklist** (1 hour)
   - [ ] Signup with valid email works
   - [ ] Signup with duplicate email fails (409 error)
   - [ ] WhatsApp QR appears and refreshes every 60s
   - [ ] File upload accepts PDF, rejects .exe
   - [ ] Persona config saves to database
   - [ ] CRM import handles 100 contacts
   - [ ] Stripe checkout redirects correctly
   - [ ] Free plan activates without payment
   - [ ] Mobile responsive (test at 375px width)
   - [ ] Accessibility (keyboard navigation works)

3. ✅ **Build frontend for production** (30 min)
   ```bash
   cd frontend/onboarding
   npm run build
   # Copy dist/ to backend static files
   cp -r dist/* ../../src/static/
   ```

4. ✅ **Deploy to staging** (1 hour)
   ```powershell
   cd w3j-bijou-enterprise
   
   # Deploy to Fly.io
   C:\Users\w3jbt\.fly\bin\flyctl.exe deploy --app bijou-staging --config fly.staging.toml
   
   # Wait for deployment
   timeout /t 30
   
   # Run health checks
   python tests\e2e_health_check.py --env staging
   
   # Test onboarding flow on staging
   # Visit: https://bijou-staging.fly.dev/onboard
   ```

5. ✅ **Documentation** (30 min)
   - Update README.md with onboarding instructions
   - Document environment variables needed
   - Create admin guide for reviewing signups
   - Add troubleshooting section

**Validation:**
```bash
# Staging health checks
curl https://bijou-staging.fly.dev/health
# Should return {"status": "healthy"}

# Test signup on staging
curl -X POST https://bijou-staging.fly.dev/api/onboarding/v2/signup \
  -H "Content-Type: application/json" \
  -d '{"business_name": "Staging Test", "email": "staging@test.com", "phone": "+60123456789", "owner_name": "Test"}'

# Complete full wizard flow manually
```

**Blockers:**
- ⚠️ Requires Stripe test API keys configured in Fly.io secrets
- ⚠️ Bridge must be accessible from staging environment
- ⚠️ Email sending needs SMTP credentials or SendGrid API key

**End-of-Day Deliverables:**
- ✅ Stripe billing integration working
- ✅ All 7 wizard steps functional on staging
- ✅ E2E test covering full onboarding flow
- ✅ Staging deployment passing health checks
- ✅ Documentation updated with onboarding guide

---

## 🚨 CRITICAL PATH & DEPENDENCIES

### Dependency Graph
```
Day 1: Database Migrations
   ↓
Day 2: WhatsApp Integration (depends on Day 1)
   ↓
Day 3: Knowledge & CRM (depends on Day 1)
   ↓
Day 4: Frontend Wizard (depends on Days 1-3 APIs)
   ↓
Day 5: Billing & Deployment (depends on Day 4 UI)
```

### Parallel Work Opportunities
- **Day 1 Afternoon + Day 2 Morning:** Can work in parallel (backend APIs vs bridge)
- **Day 3:** Knowledge upload and CRM import can be developed independently
- **Day 4:** Frontend components can be stubbed with mock data while APIs finalize

---

## 📋 TESTING CHECKLIST

### Unit Tests (pytest)
- [ ] `test_signup_endpoint()` - Valid signup creates tenant
- [ ] `test_signup_duplicate_email()` - Returns 409 error
- [ ] `test_qr_status_polling()` - Returns correct status
- [ ] `test_knowledge_upload_validation()` - Rejects invalid files
- [ ] `test_crm_import_duplicates()` - Skips duplicates correctly
- [ ] `test_persona_config_save()` - Updates tenant settings
- [ ] `test_stripe_webhook_verification()` - Validates signature

### Integration Tests (pytest)
- [ ] `test_full_signup_to_whatsapp()` - Signup → device provisioned
- [ ] `test_file_upload_to_embedding()` - Upload → text extracted → embedding stored
- [ ] `test_crm_import_to_database()` - Import → contacts in DB
- [ ] `test_stripe_checkout_to_activation()` - Checkout → subscription created

### E2E Tests (Playwright or manual)
- [ ] Complete full wizard in < 5 minutes
- [ ] WhatsApp QR connects successfully
- [ ] Upload 5 PDFs (20MB total) without timeout
- [ ] Import 100 contacts via CSV
- [ ] Stripe checkout completes (test mode)
- [ ] Free plan activates without payment
- [ ] Onboarding completion triggers welcome email

### Performance Tests
- [ ] API latency < 200ms p95 (dashboard endpoints)
- [ ] File upload handles 10MB in < 10s
- [ ] CRM import processes 1000 contacts in < 30s
- [ ] Database query response < 100ms (with indexes)

### Security Tests
- [ ] RLS prevents cross-tenant data access
- [ ] Signup with SQL injection fails safely
- [ ] File upload rejects executable files (.exe, .sh)
- [ ] Stripe webhook rejects invalid signatures
- [ ] Audit logs capture all tenant actions

---

## 🚀 DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] All migrations applied to Supabase production
- [ ] Environment variables configured in Fly.io secrets
- [ ] Stripe webhook endpoint configured (production URL)
- [ ] Bridge URL updated to production instance
- [ ] CORS origins include production domain
- [ ] Email SMTP credentials configured

### Deployment Steps
```powershell
# 1. Run tests locally
pytest tests/ -v --cov=src

# 2. Build frontend
cd frontend/onboarding
npm run build
cp -r dist/* ../../src/static/

# 3. Deploy to staging
cd w3j-bijou-enterprise
C:\Users\w3jbt\.fly\bin\flyctl.exe deploy --app bijou-staging

# 4. Run health checks
timeout /t 30
python tests\e2e_health_check.py --env staging

# 5. Manual smoke test
# - Visit https://bijou-staging.fly.dev/onboard
# - Complete full wizard
# - Verify database records created

# 6. Deploy to production (if staging passes)
C:\Users\w3jbt\.fly\bin\flyctl.exe deploy --app bijou-production
```

### Post-Deployment
- [ ] Monitor Fly.io logs for errors (first 30 minutes)
- [ ] Check Sentry for exceptions
- [ ] Verify first real tenant can sign up
- [ ] Test Stripe webhook with real event
- [ ] Confirm email sending works
- [ ] Review audit logs for suspicious activity

---

## 🛠️ TROUBLESHOOTING GUIDE

### Common Issues

**1. WhatsApp QR not appearing**
- Check bridge is running: `curl https://<bridge-url>/health`
- Verify `BRIDGE_URL` in environment variables
- Check `whatsapp_devices` table for errors
- Review bridge logs for device creation failures

**2. File upload timeout**
- Increase FastAPI timeout: `app = FastAPI(timeout=300)`
- Use chunked upload for files > 5MB
- Check Supabase storage limits
- Verify background task is processing files

**3. CRM import fails**
- Validate CSV format (UTF-8 encoding)
- Check for duplicate phone/email conflicts
- Verify RLS policies allow insert
- Review error logs for SQL exceptions

**4. Stripe webhook not triggering**
- Verify webhook URL in Stripe dashboard
- Check webhook secret matches environment variable
- Test with Stripe CLI: `stripe listen --forward-to localhost:8080/api/webhooks/stripe`
- Review Stripe dashboard webhook logs

**5. Onboarding progress not updating**
- Check trigger function `update_onboarding_current_step()`
- Verify step completion flags set correctly
- Review database trigger logs
- Manually update step if needed (SQL update)

---

## 📊 SUCCESS METRICS

### Onboarding Metrics (Track Daily)
| Metric | Target | Tracking Method |
|--------|--------|-----------------|
| Signup to WhatsApp time | < 3 min | `TIMESTAMPDIFF(signup_at, whatsapp_at)` |
| Drop-off rate per step | < 20% | `COUNT(current_step) / COUNT(total_signups)` |
| QR scan failure rate | < 5% | `COUNT(status='error') / COUNT(status='qr_ready')` |
| File upload success rate | > 95% | `COUNT(processing_failed=false) / COUNT(total_uploads)` |
| Onboarding completion rate | > 70% | `COUNT(onboarding_completed=true) / COUNT(signups)` |

### Platform Metrics (Monitor in Dashboard)
- Message processing latency (p50, p95, p99)
- WhatsApp device uptime (% connected)
- Knowledge base search accuracy (relevance score)
- API availability (uptime %)
- Database query performance (slow query log)

---

## 📦 DELIVERABLES SUMMARY

### Code Deliverables
1. ✅ **Database Migrations** (7 SQL files)
2. ✅ **Backend API** (`onboarding_api_v2.py` - 400+ lines)
3. ✅ **Frontend Wizard** (React app with 7 step components)
4. ✅ **Integration Tests** (pytest suite covering critical paths)
5. ✅ **Deployment Scripts** (PowerShell/Bash for staging deploy)

### Documentation Deliverables
1. ✅ **Implementation Plan** (this document)
2. ✅ **API Documentation** (OpenAPI/Swagger at /docs)
3. ✅ **Frontend README** (setup + development guide)
4. ✅ **Troubleshooting Guide** (common issues + fixes)
5. ✅ **Admin Guide** (reviewing signups, managing tenants)

### Testing Deliverables
1. ✅ **Unit Tests** (80%+ coverage target)
2. ✅ **Integration Tests** (key flows end-to-end)
3. ✅ **E2E Test Suite** (automated browser testing)
4. ✅ **Manual Test Checklist** (pre-deployment validation)
5. ✅ **Performance Benchmarks** (API latency, DB query speed)

---

## 🎯 DEFINITION OF DONE

**Feature is considered complete when:**
1. ✅ All 7 wizard steps functional on staging
2. ✅ User can complete onboarding in < 5 minutes
3. ✅ All automated tests passing (unit + integration)
4. ✅ Manual smoke test completed successfully
5. ✅ RLS policies prevent cross-tenant data leaks
6. ✅ Staging deployment passing health checks
7. ✅ Documentation updated with onboarding guide
8. ✅ Zero critical bugs in Sentry (first 24 hours)
9. ✅ At least 1 real tenant successfully onboarded
10. ✅ Audit logs capturing all tenant actions

---

## 🚧 FUTURE ENHANCEMENTS (Post-MVP)

### Phase 2 (Week 2-3)
- [ ] Email verification with confirmation link
- [ ] Google OAuth login (existing credentials configured)
- [ ] Team member invitations during onboarding
- [ ] Advanced AI persona testing (preview mode with sample conversations)
- [ ] Website crawler for knowledge base (auto-scrape FAQ pages)

### Phase 3 (Month 2)
- [ ] Analytics dashboard (real-time charts)
- [ ] Automated billing reminders (80% usage notification)
- [ ] GDPR data export (one-click download)
- [ ] Multi-language onboarding (Malay, Mandarin)
- [ ] White-label branding for enterprise tier

### Phase 4 (Month 3)
- [ ] Integration marketplace (Zapier, Make, custom webhooks)
- [ ] AI training data upload (fine-tuning on business corpus)
- [ ] Voice onboarding (voice notes instead of text)
- [ ] Mobile app (React Native) for on-the-go management
- [ ] API playground (test endpoints without wizard)

---

## 📞 ESCALATION CONTACTS

| Issue Type | Contact | Response Time |
|------------|---------|---------------|
| Supabase outage | Support ticket | < 1 hour |
| Fly.io deployment failure | Community forum | < 30 min |
| Bridge connection issues | Check GOWA logs | Immediate |
| Stripe webhook errors | Stripe dashboard | < 2 hours |
| Critical bug blocking signups | Create GitHub issue | Immediate fix |

---

## 📝 NOTES & ASSUMPTIONS

### Assumptions
- Solo developer has full access to all systems (Supabase, Fly.io, Stripe)
- Existing WhatsApp bridge (GOWA) is running and accessible
- Staging environment mirrors production (same database schema)
- Budget allows for Supabase Pro plan (needed for large file storage)
- Test WhatsApp numbers available (cannot reuse same number)

### Known Limitations
- Free tier limited to 100 messages/month (may need adjustment)
- File uploads capped at 10MB (chunked upload not implemented)
- No real-time collaboration (only one user can edit settings)
- Email sending requires external service (SendGrid or SMTP)
- Voice responses not included in onboarding (manual setup later)

### Risk Mitigation
- **Risk:** WhatsApp bridge downtime during onboarding
  - **Mitigation:** Add retry logic with exponential backoff, show user-friendly error
- **Risk:** Large file uploads timeout
  - **Mitigation:** Use chunked uploads, show progress bar, allow resume
- **Risk:** Stripe webhook failures
  - **Mitigation:** Implement retry queue, manual activation fallback
- **Risk:** Database migration breaks existing tenants
  - **Mitigation:** Test on staging first, have rollback plan, backup database

---

**END OF IMPLEMENTATION PLAN**

**Next Step:** Begin Day 1 - Database Migrations  
**Owner:** @db-admin (assisted by @backend)  
**ETA:** 8 hours from start

**Questions? Escalate to:** @architect
