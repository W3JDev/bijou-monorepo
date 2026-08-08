# QUICK START GUIDE - BIJOU AI ONBOARDING PORTAL

**⏱️ Time to implement:** 5 days (40 hours)  
**👤 Developer:** Solo (you!)  
**🎯 Goal:** Production-ready automated onboarding system

---

## 🚀 START HERE (Day 1 Morning - First 2 Hours)

### Step 1: Review Architecture (30 minutes)
```bash
# Read these files in order:
1. docs/architecture/ONBOARDING_PORTAL_ARCHITECTURE.md  # THIS FILE (Overview)
2. docs/planning/ONBOARDING_IMPLEMENTATION_PLAN.md      # Day-by-day tasks
3. Database migrations (skim through the 8 SQL files)
```

### Step 2: Apply Database Migrations (1 hour)
```sql
-- Go to: https://supabase.com/dashboard/project/lrwzlujomukzjykafmic/sql

-- 1. Copy & paste this first (REQUIRED):
-- File: database/migrations/000_helper_functions.sql

-- 2. Then apply these migrations in order:
-- (Each SQL file is already written and ready to execute)

-- ✅ 001_crm_contacts.sql        (CRM table + RLS)
-- ✅ 002_integrations.sql        (OAuth tokens)
-- ✅ 003_billing_subscriptions.sql  (Stripe data)
-- ✅ 004_audit_logs.sql          (GDPR compliance)
-- ✅ 005_onboarding_progress.sql (Wizard tracking)
-- ✅ 006_update_existing_tables.sql  (Add columns)
-- ✅ 007_analytics_views.sql     (Materialized views)

-- 3. Verify migrations applied:
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- You should see: crm_contacts, integrations, billing_subscriptions, 
--                 audit_logs, onboarding_progress, etc.
```

### Step 3: Create Backend API File (30 minutes)
```bash
# Navigate to project root
cd w3j-bijou-enterprise

# The file src/saas/onboarding_api_v2.py is ALREADY WRITTEN
# (See Part 3 of ONBOARDING_PORTAL_ARCHITECTURE.md)

# You need to:
# 1. Copy the complete code from the architecture doc
# 2. Create the file at: src/saas/onboarding_api_v2.py
# 3. Register routes in src/core/bijou.py

# Edit bijou.py and add this import:
from src.saas.onboarding_api_v2 import router as onboarding_v2_router

# Then add this line after other routers:
app.include_router(onboarding_v2_router)
```

---

## 📋 FILES ALREADY CREATED FOR YOU

### ✅ Database Migrations (8 files)
All migration SQL is complete and ready to execute in Supabase:
- `000_helper_functions.sql` - Created ✅
- `001_crm_contacts.sql` - See Part 1 of architecture doc
- `002_integrations.sql` - See Part 1 of architecture doc
- `003_billing_subscriptions.sql` - See Part 1 of architecture doc
- `004_audit_logs.sql` - See Part 1 of architecture doc
- `005_onboarding_progress.sql` - See Part 1 of architecture doc
- `006_update_existing_tables.sql` - See Part 1 of architecture doc
- `007_analytics_views.sql` - See Part 1 of architecture doc

### ✅ Backend API Code
- `src/saas/onboarding_api_v2.py` - Complete FastAPI endpoints (~800 lines)
  - Located in Part 3 of `ONBOARDING_PORTAL_ARCHITECTURE.md`
  - Just copy-paste into your project!

### ✅ Frontend Scaffolds
- `frontend/onboarding/README.md` - Setup guide ✅
- `frontend/onboarding/src/lib/types.ts` - TypeScript types ✅
- Component templates documented (build in Day 4)

### ✅ Documentation
- `docs/architecture/ONBOARDING_PORTAL_ARCHITECTURE.md` - Full architecture ✅
- `docs/planning/ONBOARDING_IMPLEMENTATION_PLAN.md` - 5-day sprint plan ✅
- `docs/QUICK_START.md` - This file! ✅

---

## 🔥 PRIORITY TASKS (Do These First)

### Day 1 Priority (Complete Today)
```bash
# Morning (4 hours):
☐ Apply all 8 database migrations to Supabase
☐ Create src/saas/onboarding_api_v2.py file
☐ Register routes in bijou.py
☐ Start local server: python src/core/bijou.py

# Test signup endpoint:
curl -X POST http://localhost:8080/api/onboarding/v2/signup \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Test Business",
    "email": "test@example.com",
    "phone": "+60123456789",
    "owner_name": "Test Owner"
  }'

# Expected response:
{
  "tenant_id": "uuid...",
  "signup_token": "uuid...",
  "onboarding_url": "http://localhost:8080/onboard/uuid...",
  "status": "pending"
}

# Afternoon (4 hours):
☐ Write unit test for signup endpoint
☐ Implement status endpoint (GET /api/onboarding/v2/status/{token})
☐ Test status endpoint returns onboarding progress
☐ Commit code to git: git commit -m "feat: onboarding API v2 - signup + status"
```

### Day 2 Priority (WhatsApp Integration)
```bash
☐ Implement GET /api/onboarding/v2/whatsapp/qr/{token}
☐ Test with real WhatsApp number (scan QR code)
☐ Verify whatsapp_devices table updates status to 'connected'
☐ Mark onboarding_progress step_whatsapp_completed = true
```

### Day 3 Priority (File Upload + CRM)
```bash
☐ Implement POST /api/onboarding/v2/knowledge/upload/{token}
☐ Test uploading PDF file (extract text)
☐ Implement POST /api/onboarding/v2/crm/import/{token}
☐ Test importing 100 contacts via JSON
```

### Day 4 Priority (Frontend Wizard)
```bash
☐ Initialize Vite + React project
☐ Install shadcn/ui components
☐ Build SignupStep.tsx component
☐ Build WhatsAppQRStep.tsx component
☐ Test signup → QR flow end-to-end in browser
```

### Day 5 Priority (Billing + Deploy)
```bash
☐ Implement POST /api/onboarding/v2/billing/checkout/{token}
☐ Test Stripe checkout session (test mode)
☐ Build frontend for production: npm run build
☐ Deploy to staging: flyctl deploy --app bijou-staging
☐ Run health checks: python tests/e2e_health_check.py --env staging
```

---

## 🧪 TESTING AS YOU GO

### After Each Endpoint Implementation
```bash
# 1. Write unit test in tests/unit/test_onboarding_api_v2.py
# 2. Run test: pytest tests/unit/test_onboarding_api_v2.py -v
# 3. Test with curl/Postman manually
# 4. Check database to verify records created
# 5. Review logs for errors
```

### Manual Testing Checklist
```bash
☐ Signup with valid email works
☐ Signup with duplicate email returns 409 error
☐ Status endpoint shows current_step correctly
☐ WhatsApp QR appears within 5 seconds
☐ QR scan connects real WhatsApp device
☐ File upload accepts PDF, rejects .exe
☐ CRM import handles 100 contacts
☐ Stripe checkout redirects correctly
☐ Free plan activates without payment
```

---

## ⚠️ CRITICAL BLOCKERS TO WATCH

### 1. WhatsApp Bridge Must Be Running
```bash
# Check bridge health:
curl https://<bridge-url>/health

# If down, start bridge:
flyctl ssh console --app gowa-bridge
# (or check bridge logs for errors)
```

### 2. Supabase Service Key Required
```bash
# Verify .env file contains:
SUPABASE_URL=https://lrwzlujomukzjykafmic.supabase.co
SUPABASE_SERVICE_KEY=<your-service-role-key>

# Test connection:
python -c "from supabase import create_client; import os; client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY')); print('✅ Connected')"
```

### 3. RLS Policies Must Allow Service Role
```sql
-- If you get permission errors, check RLS policies:
SELECT tablename, policyname FROM pg_policies WHERE schemaname = 'public';

-- Service role should bypass all RLS:
CREATE POLICY "Service role full access"
    ON <table_name>
    USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');
```

### 4. CORS Must Allow Frontend
```python
# In src/core/bijou.py, ensure CORS allows frontend:
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://bijou-staging.fly.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📞 WHERE TO GET HELP

### Issue Types & Solutions
| Problem | First Check | Solution |
|---------|-------------|----------|
| Database error | Supabase logs | Check RLS policies, verify migration applied |
| API 500 error | FastAPI logs | Check `.env` variables, verify imports |
| File upload timeout | File size | Reduce to < 5MB, check background task |
| WhatsApp QR not showing | Bridge logs | Restart bridge, check device provisioning |
| Stripe webhook fails | Stripe dashboard | Verify webhook secret, check signature |

### External Resources
- **Supabase Issues:** https://supabase.com/dashboard (check logs)
- **Fly.io Logs:** `flyctl logs --app bijou-staging`
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **React Query:** https://tanstack.com/query/latest

---

## ✅ SUCCESS CRITERIA

**You're done when:**
1. ✅ User can sign up and get a signup_token
2. ✅ WhatsApp QR connects a real device
3. ✅ Knowledge base files upload and process
4. ✅ CRM contacts import successfully
5. ✅ Stripe checkout creates subscription
6. ✅ Staging deployment passes health checks
7. ✅ At least 1 complete onboarding test run

---

## 🎯 YOUR FIRST ACTION RIGHT NOW

**Copy-paste this into your terminal:**

```bash
# Navigate to project
cd w3j-bijou-enterprise

# Open Supabase SQL editor in browser
start https://supabase.com/dashboard/project/lrwzlujomukzjykafmic/sql

# While that loads, open architecture doc:
start docs/architecture/ONBOARDING_PORTAL_ARCHITECTURE.md

# Copy the helper functions SQL:
code database/migrations/000_helper_functions.sql

# Paste into Supabase SQL editor and run ▶️
```

**Then scroll to Part 1 of the architecture doc and copy each migration SQL into Supabase one by one.**

---

## 📊 PROGRESS TRACKER

Use this to track your daily progress:

### Day 1: Database & Backend Foundation
- [ ] Helper functions migration applied
- [ ] All 7 migrations applied
- [ ] RLS policies tested
- [ ] `onboarding_api_v2.py` created
- [ ] Signup endpoint working
- [ ] Status endpoint working
- [ ] Unit tests passing

### Day 2: WhatsApp Integration
- [ ] QR endpoint implemented
- [ ] Device provisioning working
- [ ] Status polling functional
- [ ] Real WhatsApp connected
- [ ] Integration tests written

### Day 3: Knowledge & CRM
- [ ] File upload endpoint done
- [ ] Text extraction working
- [ ] Embeddings generated
- [ ] CRM import endpoint done
- [ ] 100 contacts imported successfully

### Day 4: Frontend Wizard
- [ ] React project initialized
- [ ] shadcn/ui installed
- [ ] Signup step component
- [ ] WhatsApp QR step component
- [ ] Knowledge upload step component
- [ ] All 7 steps navigable

### Day 5: Billing & Deployment
- [ ] Stripe checkout endpoint
- [ ] Frontend built for production
- [ ] Deployed to staging
- [ ] Health checks passing
- [ ] Manual test completed
- [ ] Documentation updated

---

## 🏁 FINISH LINE

**When you complete Day 5, you will have:**
- ✅ A fully functional onboarding portal
- ✅ 8 database tables with proper RLS
- ✅ 8 FastAPI endpoints with validation
- ✅ React wizard with 7 steps
- ✅ WhatsApp QR integration working
- ✅ Stripe billing automated
- ✅ Production-ready deployment

**You can then:**
- Launch to real customers
- Collect feedback
- Iterate on UI/UX
- Add advanced features (analytics dashboard, etc.)

---

**🎉 Ready to start? Open Supabase and apply the first migration!**

**Questions? Everything is documented. Check:**
1. This file (QUICK_START.md)
2. Implementation plan (ONBOARDING_IMPLEMENTATION_PLAN.md)
3. Architecture doc (ONBOARDING_PORTAL_ARCHITECTURE.md)

**Good luck! You've got this! 💪**

---

_Generated by @architect | February 17, 2026_
