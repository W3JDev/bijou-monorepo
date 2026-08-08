# E2E Testing Strategy - Implementation Checklist

**Created:** 2026-02-14  
**Status:** Ready for Implementation  
**Author:** @architect

---

## 📋 Quick Summary

Comprehensive E2E testing strategy created for Bijou AI v301. Strategy covers:

- ✅ **53 test scenarios** across 6 categories
- ✅ **Priority levels** (P0 = blocking, P1 = important, P2 = monitor)
- ✅ **Security validation** (v301 tenant isolation patches)
- ✅ **WhatsApp connection verification** (addresses known "Disconnected" issue)
- ✅ **Automated deployment gates** (CI/CD integration)
- ✅ **Rollback criteria** (automatic + manual procedures)

---

## 🎯 Key Test Categories

### 1. Security & Tenant Isolation (10 tests)
**Priority:** P0 (5 tests), P1 (3 tests), P2 (2 tests)

**Critical Tests:**
- TC-SEC-001: Cross-tenant escalation leak (v301 Bug #1)
- TC-SEC-002: Tenant ID required for escalation (v301 Bug #2)
- TC-SEC-003: Dashboard API tenant isolation
- TC-SEC-004: Knowledge base access control
- TC-SEC-005: SQL injection prevention

**Why Critical:** Validates v301 security patches are working correctly.

---

### 2. WhatsApp Integration (9 tests)
**Priority:** P0 (4 tests), P1 (3 tests), P2 (2 tests)

**Critical Tests:**
- TC-WA-001: Bridge connection health ⚠️ **ADDRESSES KNOWN ISSUE**
- TC-WA-002: Message sending via bridge
- TC-WA-003: Incoming message webhook
- TC-WA-004: Connection status webhook
- TC-WA-005: Message deduplication

**Known Issue:** Dashboard shows "Disconnected" even when bridge is connected.  
**Test Coverage:** TC-WA-001 and TC-DASH-004 verify connection status accuracy.

---

### 3. Dashboard API (10 tests)
**Priority:** P0 (3 tests), P1 (4 tests), P2 (3 tests)

**Critical Tests:**
- TC-DASH-001: Conversations list with proper formatting
- TC-DASH-002: Stats dashboard calculations
- TC-DASH-003: Escalation queue sorting
- TC-DASH-004: WhatsApp connection status ⚠️ **KNOWN ISSUE TEST**

---

### 4. AI Response Generation (8 tests)
**Priority:** P0 (3 tests), P1 (2 tests), P2 (3 tests)

**Critical Tests:**
- TC-AI-001: Gemini API integration
- TC-AI-002: Multi-language detection (Malay, Mandarin, etc.)
- TC-AI-003: Knowledge base retrieval
- TC-AI-004: Escalation keyword detection

---

### 5. Database Operations (8 tests)
**Priority:** P0 (4 tests), P1 (2 tests), P2 (2 tests)

**Critical Tests:**
- TC-DB-001: Supabase connection health
- TC-DB-002: Conversation logging (data integrity)
- TC-DB-003: RLS policies enforced
- TC-DB-004: Query performance (<500ms p95)

---

### 6. Performance & Reliability (8 tests)
**Priority:** P0 (2 tests), P1 (3 tests), P2 (3 tests)

**Critical Tests:**
- TC-PERF-001: Health check response time (<2s)
- TC-PERF-002: Concurrent message handling (10 simultaneous)
- TC-PERF-003: Memory leak detection

---

## 🚨 Deployment Gates (BLOCKING)

### Pre-Deployment (Staging)

```bash
# Step 1: Run unit tests (100% pass required)
pytest tests/unit/ -v -m "not slow"

# Step 2: Run integration tests (95% pass required)
pytest tests/integration/ -v

# Step 3: Run v301 security tests (100% pass required)
pytest tests/unit/test_security_fixes_v301.py -v

# Step 4: Deploy to staging
flyctl deploy --app bijou-staging --config fly.staging.toml

# Step 5: Wait for stabilization
sleep 30

# Step 6: Health check (ALL 7 checks must pass)
python tests/e2e_health_check.py --env staging

# Step 7: E2E smoke tests (100% pass required)
pytest tests/e2e/ -m smoke -v
```

**If ANY step fails → DO NOT deploy to production**

---

### Post-Deployment (Production)

```bash
# Wait 30 seconds for deployment
sleep 30

# Run production health checks
python tests/e2e_health_check.py --env production

# Exit code 0 = Success ✅
# Exit code 1 = Failure → AUTOMATIC ROLLBACK 🚨
```

---

## 🔴 Automatic Rollback Triggers

Rollback is **automatically triggered** if:

1. **Health Check Failures**
   - Any of 7 health checks fail
   - WhatsApp bridge unreachable
   - Database connection failure

2. **Critical Errors**
   - HTTP 500 errors >5% of requests
   - Response time >10s (severe degradation)
   - Application crashes

3. **Security Violations**
   - Cross-tenant data leak detected
   - Tenant isolation bypass
   - Unauthorized access logged

4. **Data Integrity**
   - Conversations not saving
   - Message delivery failures >10%
   - AI responses failing >25%

---

## 📁 Test Files to Create

### Priority 1: Create These Files First

```
tests/e2e/
├── conftest.py (shared fixtures for E2E tests)
├── test_security_tenant_isolation.py (TC-SEC-001 to TC-SEC-005)
├── test_whatsapp_bridge.py (TC-WA-001 to TC-WA-005)
└── test_dashboard_api.py (TC-DASH-001 to TC-DASH-004)
```

### Priority 2: Create After P1 Tests Pass

```
tests/e2e/
├── test_ai_responses.py (TC-AI-001 to TC-AI-004)
├── test_database.py (TC-DB-001 to TC-DB-004)
└── test_performance.py (TC-PERF-001 to TC-PERF-003)
```

### Priority 3: Create for Full Coverage

```
tests/e2e/
├── test_full_journey.py (End-to-end user flows)
└── test_regression_v301.py (Security regression tests)
```

---

## 🛠️ Required Dependencies

```bash
# Install testing tools
pip install pytest pytest-asyncio pytest-cov httpx pytest-mock responses
```

---

## ⚠️ Known Issues to Address

### Issue 1: WhatsApp Connection Status "Disconnected"

**Symptom:** Dashboard shows "Disconnected" even when bridge is connected  
**Tests:** TC-DASH-004, TC-WA-004  
**Priority:** P0 (must fix before production)

**Action Required:**
1. Verify `/webhook/connection` receives status updates
2. Check `whatsapp_sessions` table has status column
3. Ensure dashboard queries correct endpoint

**Test to Verify Fix:**
```python
# TC-DASH-004
async def test_whatsapp_connection_status():
    response = await client.get(
        f"{BIJOU_URL}/api/dashboard/whatsapp-status?tenant_id=w3j"
    )
    assert response.json()["status"] == "connected"  # Should PASS after fix
```

---

### Issue 2: Slow Dashboard Queries

**Symptom:** Conversations list takes >1s to load  
**Tests:** TC-DB-004  
**Priority:** P2 (performance optimization)

**Fix Required:**
```sql
CREATE INDEX idx_conversations_tenant_created 
ON conversations(tenant_id, created_at DESC);
```

---

## 📊 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **Test Coverage** | 53 scenarios documented | ✅ Complete |
| **P0 Tests** | 21 critical tests | 📝 Need to implement |
| **P1 Tests** | 17 important tests | 📝 Need to implement |
| **P2 Tests** | 15 monitoring tests | 📝 Optional |
| **Deployment Gates** | 3 automated workflows | ✅ Documented |
| **Rollback Criteria** | 4 trigger categories | ✅ Defined |

---

## 🚀 Next Steps (Priority Order)

### Immediate (Before Production Deployment)

1. **Create conftest.py** with shared fixtures
2. **Implement TC-SEC-001** (cross-tenant escalation leak test)
3. **Implement TC-SEC-002** (tenant ID required test)
4. **Implement TC-WA-001** (bridge connection test)
5. **Implement TC-DASH-004** (WhatsApp status test) ⚠️ **FIX KNOWN ISSUE**
6. **Run pre-deployment workflow** on staging
7. **Fix WhatsApp "Disconnected" issue** if tests fail
8. **Deploy to production** once all P0 tests pass

---

### Short-Term (Week 1-2)

9. **Implement remaining P0 tests** (21 total)
10. **Create automation scripts** (pre_deployment_tests.sh)
11. **Set up CI/CD integration** with GitHub Actions
12. **Document test failures** and create bug tickets
13. **Implement P1 tests** (17 total)

---

### Long-Term (Month 1)

14. **Implement P2 tests** (15 total)
15. **Add load testing** with Locust
16. **Create performance baselines**
17. **Set up monitoring dashboards**
18. **Automate rollback procedures**

---

## 📞 Support

**Owner:** @architect  
**Team:** W3J Consulting  
**On-Call:** Muhammad Nurunnabi (Jewel)  
**Contact:** +60 14 385 6929

**Escalation:**
1. Check test logs
2. Review health checks
3. Contact @architect for blockers
4. Emergency rollback if needed

---

## 📖 Full Documentation

See **tests/e2e/TEST_STRATEGY.md** for:
- Complete test scenarios (53 total)
- Detailed test code examples
- CI/CD pipeline diagrams
- Rollback procedures
- Test data fixtures
- Known issues and workarounds

---

**Status:** ✅ Strategy Complete - Ready for Implementation  
**Last Updated:** 2026-02-14  
**Version:** v1.0
