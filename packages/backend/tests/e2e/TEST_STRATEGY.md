# Bijou AI v301 - End-to-End Testing Strategy

**Version:** v301  
**Created:** 2026-02-14  
**Status:** Production Ready  
**Owner:** @architect

---

## 🎯 Executive Summary

This document defines the comprehensive E2E testing strategy for Bijou AI v301 before production deployment. It covers critical user flows, security validation (v301 security patches), integration points, and automated health checks.

### Testing Goals

1. **Verify Production Readiness** - All critical paths operational
2. **Validate Security Patches** - v301 tenant isolation fixes verified
3. **Test Integration Points** - WhatsApp Bridge, Supabase, Dashboard, Gemini API
4. **Ensure Zero Downtime** - Rollback criteria clearly defined
5. **Automate Deployment Gates** - CI/CD integration for safety

### Key Metrics

| Metric | Target | Blocking? |
|--------|--------|-----------|
| **P0 Tests Pass Rate** | 100% | ✅ Yes - blocks deployment |
| **P1 Tests Pass Rate** | ≥95% | ✅ Yes - requires review |
| **P2 Tests Pass Rate** | ≥80% | ⚠️ No - log for investigation |
| **Response Time** | <2s (health check) | ✅ Yes - performance critical |
| **WhatsApp Bridge** | Connected | ✅ Yes - core functionality |
| **Database Queries** | <500ms (p95) | ⚠️ No - monitor only |

---

## 📊 Test Coverage Matrix

### Priority Levels

- **P0** = Must pass (deployment blocking)
- **P1** = Should pass (requires investigation if fails)
- **P2** = Nice to have (log failures for future improvement)

### Coverage Areas

| Area | P0 | P1 | P2 | Total |
|------|----|----|----|----|
| **Security & Tenant Isolation** | 5 | 3 | 2 | 10 |
| **WhatsApp Integration** | 4 | 3 | 2 | 9 |
| **Dashboard API** | 3 | 4 | 3 | 10 |
| **AI Response Generation** | 3 | 2 | 3 | 8 |
| **Database Operations** | 4 | 2 | 2 | 8 |
| **Performance & Reliability** | 2 | 3 | 3 | 8 |
| **TOTAL** | **21** | **17** | **15** | **53** |

---

## 🧪 Test Scenarios Matrix

### 1. Security & Tenant Isolation (P0 Priority)

#### TC-SEC-001: Cross-Tenant Escalation Leak (P0)
**Bug Reference:** v301 Bug #1 (handover_system.py:128)

```python
# File: tests/e2e/test_security_tenant_isolation.py
# Test: should_escalate() filters by tenant_id

def test_cross_tenant_escalation_leak():
    """
    GIVEN: Two tenants (A and B) with same customer chat_jid
    WHEN: Tenant A checks for recent escalations
    THEN: Only Tenant A's escalations should be returned
    AND: Tenant B's escalations should be isolated
    """
    # Setup: Create escalation for Tenant B
    # Action: Query escalations for Tenant A
    # Assert: No leak from Tenant B
```

**Expected Result:** Query includes `.eq("tenant_id", tenant_id)` filter  
**Rollback Trigger:** If tenant isolation is bypassed  
**Priority:** P0 (BLOCKING)

---

#### TC-SEC-002: Tenant ID Required for Escalation (P0)
**Bug Reference:** v301 Bug #2 (handover_system.py:267)

```python
# Test: escalate() rejects None tenant_id

def test_escalate_requires_tenant_id():
    """
    GIVEN: Escalation request with tenant_id=None
    WHEN: escalate() is called
    THEN: Request should be rejected
    AND: Security error should be logged
    AND: No database query should execute
    """
```

**Expected Result:** Returns `None`, logs "SECURITY: tenant_id is required"  
**Rollback Trigger:** If escalation created without tenant_id  
**Priority:** P0 (BLOCKING)

---

#### TC-SEC-003: Dashboard API Tenant Isolation (P0)

```python
# File: tests/e2e/test_dashboard_tenant_isolation.py

@pytest.mark.e2e
@pytest.mark.security
async def test_conversations_filtered_by_tenant():
    """
    GIVEN: Conversations exist for multiple tenants
    WHEN: GET /api/dashboard/conversations?tenant_id=w3j
    THEN: Only w3j tenant's conversations returned
    AND: No data from other tenants leaked
    """
    # Setup: Create conversations for 3 tenants
    # Action: Query with tenant_id header
    # Assert: Only matching tenant's data returned
```

**Expected Result:** 100% tenant isolation in API responses  
**Rollback Trigger:** If cross-tenant data leak detected  
**Priority:** P0 (BLOCKING)

---

#### TC-SEC-004: Knowledge Base Access Control (P1)

```python
# File: tests/e2e/test_knowledge_security.py

async def test_knowledge_documents_tenant_isolated():
    """
    GIVEN: Knowledge documents uploaded by different tenants
    WHEN: Tenant A retrieves combined knowledge
    THEN: Only Tenant A's documents should be included
    """
```

**Expected Result:** Knowledge retrieval scoped to tenant  
**Rollback Trigger:** N/A (P1 - log for investigation)  
**Priority:** P1

---

#### TC-SEC-005: SQL Injection Prevention (P1)

```python
# File: tests/e2e/test_security_sql_injection.py

async def test_dashboard_api_sql_injection_prevention():
    """
    GIVEN: Malicious input in query parameters
    WHEN: Input contains SQL injection patterns
    THEN: Input should be sanitized
    AND: Query should fail safely
    """
    # Test cases:
    # - customer_jid="'; DROP TABLE conversations; --"
    # - tenant_id="1' OR '1'='1"
```

**Expected Result:** All inputs sanitized via Supabase client  
**Rollback Trigger:** N/A (existing library protection)  
**Priority:** P1

---

### 2. WhatsApp Integration (P0 Priority)

#### TC-WA-001: Bridge Connection Health (P0)

```python
# File: tests/e2e/test_whatsapp_bridge.py

@pytest.mark.smoke
@pytest.mark.e2e
async def test_whatsapp_bridge_connected():
    """
    GIVEN: WhatsApp bridge is deployed
    WHEN: Health check endpoint is called
    THEN: Bridge should be connected
    AND: Active sessions should be reported
    """
    response = await httpx.get(f"{BRIDGE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "active_sessions" in data
```

**Expected Result:** Bridge returns `is_connected=true`  
**Rollback Trigger:** If bridge disconnected OR unreachable  
**Priority:** P0 (BLOCKING)

---

#### TC-WA-002: Message Sending (P0)

```python
async def test_send_message_via_bridge():
    """
    GIVEN: WhatsApp bridge is connected
    WHEN: POST /api/dashboard/send-message is called
    THEN: Message should be queued successfully
    AND: Bridge should accept the request
    """
    payload = {
        "customer_jid": "60143856929@s.whatsapp.net",
        "message": "Test message from Bijou AI E2E",
        "agent_name": "E2E Test Suite"
    }
    response = await client.post(
        f"{BIJOU_URL}/api/dashboard/send-message",
        json=payload,
        headers={"X-Tenant-ID": "w3j"}
    )
    assert response.status_code in [200, 202]  # Accepted
```

**Expected Result:** HTTP 200/202, bridge confirms receipt  
**Rollback Trigger:** If message fails to send (400/500)  
**Priority:** P0 (BLOCKING)

---

#### TC-WA-003: Incoming Message Webhook (P0)

```python
async def test_incoming_message_webhook():
    """
    GIVEN: Customer sends message to WhatsApp number
    WHEN: Bridge posts to /webhook/message
    THEN: Message should be processed
    AND: AI response should be generated
    AND: Response sent back to customer
    """
    webhook_payload = {
        "session_id": "w3j-session",
        "chat_jid": "60100000001@s.whatsapp.net",
        "message": "What are your business hours?",
        "timestamp": "2026-02-14T10:30:00Z"
    }
    response = await client.post(
        f"{BIJOU_URL}/webhook/message",
        json=webhook_payload
    )
    assert response.status_code == 200
```

**Expected Result:** Webhook processed, AI response generated  
**Rollback Trigger:** If webhook returns 500 or times out  
**Priority:** P0 (BLOCKING)

---

#### TC-WA-004: Connection Status Webhook (P1)

```python
async def test_connection_status_webhook():
    """
    GIVEN: WhatsApp connection state changes
    WHEN: Bridge posts to /webhook/connection
    THEN: Status should be updated in database
    """
    webhook_payload = {
        "session_id": "w3j-session",
        "status": "connected",
        "device_info": {
            "phone": "+60143856929",
            "platform": "android"
        }
    }
    response = await client.post(
        f"{BIJOU_URL}/webhook/connection",
        json=webhook_payload
    )
    assert response.status_code == 200
```

**Expected Result:** Connection status updated  
**Rollback Trigger:** N/A (P1)  
**Priority:** P1

---

#### TC-WA-005: Message Deduplication (P1)

```python
async def test_duplicate_message_prevention():
    """
    GIVEN: Same message received twice (webhook retry)
    WHEN: Duplicate webhook is posted
    THEN: Message should only be processed once
    AND: Redis cache should prevent duplicate
    """
    message_id = "msg-12345-unique"
    # Send message twice
    # Assert: Only one conversation entry created
```

**Expected Result:** Duplicate messages ignored  
**Rollback Trigger:** N/A (P1)  
**Priority:** P1

---

### 3. Dashboard API (P0 Priority)

#### TC-DASH-001: Conversations List (P0)

```python
# File: tests/e2e/test_dashboard_api.py

@pytest.mark.e2e
async def test_get_conversations():
    """
    GIVEN: Sample conversations exist in database
    WHEN: GET /api/dashboard/conversations?tenant_id=w3j
    THEN: Conversations should be returned
    AND: Response should include: customer_jid, last_message, timestamp
    AND: Phone numbers should be formatted correctly
    """
    response = await client.get(
        f"{BIJOU_URL}/api/dashboard/conversations",
        headers={"X-Tenant-ID": "w3j"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data
    assert len(data["conversations"]) > 0
    
    # Verify phone formatting
    for conv in data["conversations"]:
        assert conv["customer_phone"].startswith("+60")  # Malaysian format
```

**Expected Result:** Conversations returned with correct formatting  
**Rollback Trigger:** If endpoint returns 500 or incorrect data  
**Priority:** P0 (BLOCKING)

---

#### TC-DASH-002: Stats Dashboard (P0)

```python
async def test_dashboard_stats():
    """
    GIVEN: Activity data exists for tenant
    WHEN: GET /api/dashboard/stats?tenant_id=w3j
    THEN: Stats should include:
         - total_conversations
         - active_conversations
         - messages_today
         - avg_response_time
    """
    response = await client.get(
        f"{BIJOU_URL}/api/dashboard/stats",
        headers={"X-Tenant-ID": "w3j"}
    )
    assert response.status_code == 200
    stats = response.json()
    assert "total_conversations" in stats
    assert isinstance(stats["total_conversations"], int)
```

**Expected Result:** Stats calculated correctly  
**Rollback Trigger:** If stats calculation fails  
**Priority:** P0 (BLOCKING)

---

#### TC-DASH-003: Escalation Queue (P1)

```python
async def test_get_escalation_queue():
    """
    GIVEN: Pending escalations exist
    WHEN: GET /api/dashboard/escalations?tenant_id=w3j
    THEN: Escalations should be returned
    AND: Sorted by priority (urgent first)
    """
    response = await client.get(
        f"{BIJOU_URL}/api/dashboard/escalations",
        headers={"X-Tenant-ID": "w3j"}
    )
    assert response.status_code == 200
    escalations = response.json()["escalations"]
    
    # Verify sorting (urgent > high > normal > low)
    priorities = [e["priority"] for e in escalations]
    assert priorities == sorted(priorities, key=lambda p: {
        "urgent": 0, "high": 1, "normal": 2, "low": 3
    }.get(p, 4))
```

**Expected Result:** Escalations sorted correctly  
**Rollback Trigger:** N/A (P1)  
**Priority:** P1

---

#### TC-DASH-004: WhatsApp Connection Status (P0)

```python
async def test_whatsapp_connection_status():
    """
    GIVEN: Dashboard UI queries connection status
    WHEN: GET /api/dashboard/whatsapp-status?tenant_id=w3j
    THEN: Current connection status should be returned
    AND: Status should be one of: connected, disconnected, connecting
    """
    response = await client.get(
        f"{BIJOU_URL}/api/dashboard/whatsapp-status",
        headers={"X-Tenant-ID": "w3j"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["connected", "disconnected", "connecting"]
```

**Expected Result:** Connection status accurate  
**Rollback Trigger:** If always shows "disconnected" (KNOWN ISSUE)  
**Priority:** P0 (BLOCKING)

---

### 4. AI Response Generation (P0 Priority)

#### TC-AI-001: Gemini API Integration (P0)

```python
# File: tests/e2e/test_ai_responses.py

@pytest.mark.e2e
async def test_gemini_api_response():
    """
    GIVEN: Customer message received
    WHEN: AI processes message
    THEN: Gemini API should generate response
    AND: Response should be contextually relevant
    """
    from src.core.tool_orchestrator import ToolOrchestrator
    
    orchestrator = ToolOrchestrator(tenant_id="w3j")
    response = await orchestrator.process_message(
        message="What time do you open?",
        chat_jid="60100000001@s.whatsapp.net"
    )
    
    assert response is not None
    assert len(response) > 10  # Meaningful response
    assert "business hours" in response.lower() or "open" in response.lower()
```

**Expected Result:** AI generates relevant response  
**Rollback Trigger:** If Gemini API fails (500/503)  
**Priority:** P0 (BLOCKING)

---

#### TC-AI-002: Multi-Language Detection (P1)

```python
async def test_language_detection():
    """
    GIVEN: Customer sends message in Malay
    WHEN: ASI analyzes message
    THEN: Language should be detected correctly
    AND: Response should be in same language
    """
    from src.agents.asi import ArtificialSocialIntelligence
    
    asi = ArtificialSocialIntelligence(tenant_id="w3j")
    result = await asi.analyze_message(
        message="Apa harga rumah 2 bilik?",
        chat_jid="60100000001@s.whatsapp.net"
    )
    
    assert result["detected_language"] == "malay"
```

**Expected Result:** Language detected correctly  
**Rollback Trigger:** N/A (P1)  
**Priority:** P1

---

#### TC-AI-003: Knowledge Base Integration (P1)

```python
async def test_knowledge_base_retrieval():
    """
    GIVEN: Tenant has uploaded knowledge documents
    WHEN: Customer asks about business info
    THEN: AI should retrieve relevant knowledge
    AND: Include it in response
    """
    # Upload test knowledge
    # Ask question about uploaded content
    # Verify response includes knowledge
```

**Expected Result:** Knowledge correctly retrieved  
**Rollback Trigger:** N/A (P1)  
**Priority:** P1

---

#### TC-AI-004: Escalation Detection (P0)

```python
async def test_escalation_keyword_detection():
    """
    GIVEN: Customer says "I want to speak to a human"
    WHEN: ERS analyzes message
    THEN: Escalation should be triggered
    AND: Owner should be notified
    """
    from src.agents.ers import EscalationRoutingSystem
    
    ers = EscalationRoutingSystem(tenant_id="w3j")
    should_escalate, reason = await ers.check_escalation(
        message="This AI is useless, I want to talk to a real person NOW!",
        chat_jid="60100000001@s.whatsapp.net"
    )
    
    assert should_escalate == True
    assert "human request" in reason.lower() or "escalation" in reason.lower()
```

**Expected Result:** Escalation triggered correctly  
**Rollback Trigger:** If escalations not detected  
**Priority:** P0 (BLOCKING)

---

### 5. Database Operations (P0 Priority)

#### TC-DB-001: Supabase Connection (P0)

```python
# File: tests/e2e/test_database.py

@pytest.mark.smoke
@pytest.mark.e2e
async def test_supabase_connection():
    """
    GIVEN: Supabase credentials configured
    WHEN: Application starts
    THEN: Connection should be established
    AND: Health check should pass
    """
    from src.core.bijou import get_supabase
    
    supabase = get_supabase()
    response = supabase.table("tenants").select("id").limit(1).execute()
    assert response.data is not None
```

**Expected Result:** Connection successful  
**Rollback Trigger:** If Supabase unreachable  
**Priority:** P0 (BLOCKING)

---

#### TC-DB-002: Conversation Logging (P0)

```python
async def test_conversation_persisted():
    """
    GIVEN: Message received and processed
    WHEN: AI generates response
    THEN: Conversation should be saved to database
    AND: Include: tenant_id, chat_jid, message, ai_response, timestamp
    """
    # Send message via webhook
    # Query conversations table
    # Verify entry exists
```

**Expected Result:** All conversations logged  
**Rollback Trigger:** If logging fails (data loss)  
**Priority:** P0 (BLOCKING)

---

#### TC-DB-003: RLS Policies Enforced (P1)

```python
async def test_row_level_security():
    """
    GIVEN: RLS policies are enabled
    WHEN: Query uses anon key (not service role)
    THEN: Only authorized data should be accessible
    """
    # Use NEXT_PUBLIC_SUPABASE_ANON_KEY (not service role)
    # Attempt to query conversations without tenant filter
    # Verify RLS blocks unauthorized access
```

**Expected Result:** RLS blocks unauthorized queries  
**Rollback Trigger:** N/A (P1)  
**Priority:** P1

---

#### TC-DB-004: Query Performance (P2)

```python
async def test_conversation_query_performance():
    """
    GIVEN: 1000+ conversations in database
    WHEN: Dashboard queries conversations
    THEN: Response time should be <500ms (p95)
    """
    import time
    
    start = time.time()
    response = await client.get(
        f"{BIJOU_URL}/api/dashboard/conversations?limit=50",
        headers={"X-Tenant-ID": "w3j"}
    )
    duration = (time.time() - start) * 1000  # ms
    
    assert duration < 500  # 500ms p95 threshold
```

**Expected Result:** Queries under 500ms  
**Rollback Trigger:** N/A (P2 - monitor only)  
**Priority:** P2

---

### 6. Performance & Reliability (P1 Priority)

#### TC-PERF-001: Health Check Response Time (P0)

```python
# File: tests/e2e/test_performance.py

@pytest.mark.smoke
async def test_health_check_response_time():
    """
    GIVEN: Application is running
    WHEN: GET /health is called
    THEN: Response time should be <2 seconds
    """
    import time
    
    start = time.time()
    response = await client.get(f"{BIJOU_URL}/health")
    duration = (time.time() - start) * 1000  # ms
    
    assert response.status_code == 200
    assert duration < 2000  # 2 seconds
```

**Expected Result:** Health check <2s  
**Rollback Trigger:** If >5s (severely degraded)  
**Priority:** P0 (BLOCKING)

---

#### TC-PERF-002: Concurrent Message Handling (P1)

```python
async def test_concurrent_messages():
    """
    GIVEN: Multiple messages arrive simultaneously
    WHEN: 10 webhooks posted concurrently
    THEN: All should be processed without errors
    AND: No deadlocks or race conditions
    """
    import asyncio
    
    async def send_message(i):
        return await client.post(
            f"{BIJOU_URL}/webhook/message",
            json={
                "session_id": "w3j-session",
                "chat_jid": f"6010000000{i}@s.whatsapp.net",
                "message": f"Test message {i}"
            }
        )
    
    results = await asyncio.gather(*[send_message(i) for i in range(10)])
    assert all(r.status_code == 200 for r in results)
```

**Expected Result:** All messages processed  
**Rollback Trigger:** N/A (P1)  
**Priority:** P1

---

#### TC-PERF-003: Memory Leak Detection (P2)

```python
async def test_no_memory_leaks():
    """
    GIVEN: Application runs for extended period
    WHEN: 1000 messages are processed
    THEN: Memory usage should stabilize
    AND: No continuous memory growth
    """
    # Monitor /health memory metrics
    # Process 1000 messages
    # Verify memory returns to baseline
```

**Expected Result:** Memory stable  
**Rollback Trigger:** N/A (P2 - monitor only)  
**Priority:** P2

---

## 📁 Test File Structure

```
tests/
├── e2e/
│   ├── __init__.py
│   ├── TEST_STRATEGY.md (this file)
│   ├── conftest.py (shared fixtures)
│   │
│   ├── test_security_tenant_isolation.py (TC-SEC-001 to TC-SEC-005)
│   ├── test_whatsapp_bridge.py (TC-WA-001 to TC-WA-005)
│   ├── test_dashboard_api.py (TC-DASH-001 to TC-DASH-004)
│   ├── test_ai_responses.py (TC-AI-001 to TC-AI-004)
│   ├── test_database.py (TC-DB-001 to TC-DB-004)
│   ├── test_performance.py (TC-PERF-001 to TC-PERF-003)
│   │
│   ├── test_full_journey.py (End-to-end user flows)
│   └── test_regression_v301.py (Security bug regression tests)
│
├── integration/
│   ├── test_supabase_integration.py
│   └── test_gemini_integration.py
│
├── unit/
│   ├── test_tenant_manager.py
│   ├── test_message_filter.py
│   └── test_security_fixes_v301.py (EXISTING)
│
├── regression/
│   └── test_v299_regressions.py (EXISTING)
│
├── fixtures/
│   ├── test_tenants.py (Synthetic tenant data)
│   └── sample_conversations.json
│
├── mocks/
│   ├── whatsapp_mock.py (Mock WhatsApp Bridge)
│   └── gemini_mock.py (Mock Gemini API)
│
├── e2e_health_check.py (EXISTING - deployment gate)
├── test_e2e_full_suite.py (EXISTING - comprehensive E2E)
└── conftest.py (Global fixtures)
```

---

## 🛠️ Required Tools & Dependencies

### Python Packages

```bash
# Core testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-timeout>=2.1.0
pytest-xdist>=3.3.0  # Parallel execution

# HTTP testing
httpx>=0.25.0
requests>=2.31.0

# Mocking
pytest-mock>=3.11.0
responses>=0.23.0

# Test data
faker>=19.0.0  # Generate test data

# Performance testing
locust>=2.15.0  # Load testing (optional)
```

### Installation

```bash
cd w3j-bijou-enterprise
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx pytest-mock
```

---

## 🤖 Automation Strategy

### CI/CD Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                     DEPLOYMENT PIPELINE                         │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────┐
  │ Code Commit  │
  └──────┬───────┘
         │
         v
  ┌──────────────────┐
  │  Unit Tests (P0) │ ◄─── pytest tests/unit/ -m "not slow"
  │  ~50 tests       │      Exit Code 0 required
  └──────┬───────────┘
         │ PASS
         v
  ┌──────────────────────┐
  │ Integration Tests    │ ◄─── pytest tests/integration/ -v
  │ (P0 + P1)            │      95% pass rate required
  │ ~30 tests            │
  └──────┬───────────────┘
         │ PASS
         v
  ┌──────────────────────┐
  │ Deploy to STAGING    │ ◄─── flyctl deploy --app bijou-staging
  └──────┬───────────────┘
         │
         v
  ┌──────────────────────┐
  │ E2E Health Check     │ ◄─── python tests/e2e_health_check.py --env staging
  │ (7 critical checks)  │      ALL must pass
  └──────┬───────────────┘
         │ PASS
         v
  ┌──────────────────────┐
  │ E2E Test Suite (P0)  │ ◄─── pytest tests/e2e/ -m smoke -v
  │ ~20 smoke tests      │      100% pass rate required
  └──────┬───────────────┘
         │ PASS
         v
  ┌──────────────────────┐
  │ Security Tests       │ ◄─── pytest tests/unit/test_security_fixes_v301.py -v
  │ (v301 patches)       │      ALL must pass
  └──────┬───────────────┘
         │ PASS
         v
  ┌──────────────────────┐
  │ Manual Approval      │ ◄─── Human review required
  │ (Production Gate)    │      @architect approves
  └──────┬───────────────┘
         │ APPROVED
         v
  ┌──────────────────────┐
  │ Deploy to PRODUCTION │ ◄─── flyctl deploy --app bijou-production
  └──────┬───────────────┘
         │
         v
  ┌──────────────────────┐
  │ Post-Deploy Health   │ ◄─── python tests/e2e_health_check.py --env production
  │ Check (Production)   │      Wait 30s → Run checks
  └──────┬───────────────┘
         │
         ├─ PASS ──────────────────────────────┐
         │                                      v
         │                           ┌──────────────────┐
         │                           │ Deployment       │
         │                           │ SUCCESSFUL ✅    │
         │                           │ Notify team      │
         │                           └──────────────────┘
         │
         └─ FAIL ──────────────────────────────┐
                                                v
                                     ┌──────────────────┐
                                     │ AUTOMATIC        │
                                     │ ROLLBACK 🚨      │
                                     │ Revert to prev   │
                                     │ Notify on-call   │
                                     └──────────────────┘
```

---

## 🚀 Test Execution Workflows

### Workflow 1: Pre-Deployment (Staging)

```bash
#!/bin/bash
# File: scripts/pre_deployment_tests.sh

echo "🧪 Running Pre-Deployment Test Suite..."

# Step 1: Unit Tests (Fast)
echo "\n[1/5] Running Unit Tests..."
pytest tests/unit/ -v --tb=short -m "not slow" || exit 1

# Step 2: Integration Tests
echo "\n[2/5] Running Integration Tests..."
pytest tests/integration/ -v --tb=short || exit 1

# Step 3: Security Regression Tests (v301)
echo "\n[3/5] Running Security Tests..."
pytest tests/unit/test_security_fixes_v301.py -v || exit 1

# Step 4: Deploy to Staging
echo "\n[4/5] Deploying to Staging..."
flyctl deploy --app bijou-staging --config fly.staging.toml || exit 1

# Step 5: Wait for deployment
echo "\n[5/5] Waiting for deployment to stabilize..."
sleep 30

# Step 6: Health Check
echo "\n[6/6] Running Health Checks..."
python tests/e2e_health_check.py --env staging || {
    echo "❌ Health checks FAILED - Rolling back staging"
    flyctl releases rollback --app bijou-staging
    exit 1
}

echo "\n✅ All Pre-Deployment Tests PASSED"
```

---

### Workflow 2: Post-Deployment (Production)

```bash
#!/bin/bash
# File: scripts/post_deployment_tests.sh

echo "🏥 Running Post-Deployment Health Checks..."

# Wait for production to stabilize
echo "⏳ Waiting 30 seconds for deployment to complete..."
sleep 30

# Run comprehensive health checks
python tests/e2e_health_check.py --env production

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "\n✅ Production Deployment SUCCESSFUL"
    echo "🎉 Bijou AI v301 is live!"
    
    # Optional: Run smoke tests against production
    echo "\n🧪 Running Production Smoke Tests..."
    pytest tests/e2e/ -m smoke --env production -v
else
    echo "\n❌ Production Health Checks FAILED"
    echo "🚨 INITIATING AUTOMATIC ROLLBACK"
    
    # Rollback to previous version
    flyctl releases rollback --app bijou-production
    
    # Notify team
    echo "📧 Notifying on-call engineer..."
    # (Add notification logic here)
    
    exit 1
fi
```

---

### Workflow 3: Smoke Tests Only (Quick Validation)

```bash
#!/bin/bash
# File: scripts/smoke_tests.sh

echo "💨 Running Smoke Tests (Critical Paths Only)..."

pytest tests/e2e/ -m smoke -v --tb=short --maxfail=1

if [ $? -eq 0 ]; then
    echo "\n✅ All Smoke Tests PASSED"
else
    echo "\n❌ Smoke Tests FAILED - Do NOT deploy"
    exit 1
fi
```

---

## 📈 Success Metrics

### Deployment Gate Criteria

| Metric | Staging | Production | Blocking? |
|--------|---------|------------|-----------|
| **Unit Tests** | 100% pass | N/A | ✅ Yes |
| **Integration Tests** | ≥95% pass | N/A | ✅ Yes |
| **E2E Smoke Tests** | 100% pass | N/A | ✅ Yes |
| **Health Check** | All 7 pass | All 7 pass | ✅ Yes |
| **Security Tests** | 100% pass | N/A | ✅ Yes |
| **Response Time** | <2s | <2s | ✅ Yes |
| **WhatsApp Connected** | Yes | Yes | ✅ Yes |
| **Database Latency** | <500ms | <500ms | ⚠️ Monitor |
| **Memory Usage** | <512MB | <512MB | ⚠️ Monitor |

---

## 🔴 Rollback Criteria

### Automatic Rollback Triggers

Rollback is **automatically triggered** if any of the following occur:

1. **Health Check Failures**
   - Any of the 7 health checks fail after deployment
   - Bridge unreachable or disconnected
   - Database connection failure

2. **Critical Errors**
   - HTTP 500 errors exceed 5% of requests
   - Response time >10s (severe degradation)
   - Application crashes (process exits)

3. **Security Violations**
   - Cross-tenant data leak detected
   - Tenant isolation bypass observed
   - Unauthorized access logged

4. **Data Integrity**
   - Conversations not being saved
   - Message delivery failures >10%
   - AI responses failing >25%

---

### Manual Rollback Procedure

```powershell
# 1. List recent releases
C:\Users\w3jbt\.fly\bin\flyctl.exe releases list --app bijou-production

# Output example:
# VERSION  STATUS   DEPLOY_TIME             REASON
# v15      deployed 2026-02-14 10:30:00     deploy v301
# v14      deployed 2026-02-13 15:20:00     deploy v2.2.1

# 2. Rollback to previous version
C:\Users\w3jbt\.fly\bin\flyctl.exe releases rollback v14 --app bijou-production

# 3. Verify rollback health
python tests\e2e_health_check.py --env production

# 4. Notify team
echo "🚨 PRODUCTION ROLLED BACK to v14"
```

---

## 🧩 Test Data Requirements

### Sample Tenants (Fixtures)

```python
# tests/fixtures/test_tenants.py

SAMPLE_TENANTS = [
    {
        "id": "w3j-test-tenant",
        "name": "W3J Consulting",
        "email": "test@w3j.consulting",
        "phone": "+60143856929",
        "plan_tier": "pro",
        "whatsapp_jid": "60143856929@s.whatsapp.net",
        "testing_mode": True,
        "test_numbers": ["+60100000001", "+60100000002"]
    },
    {
        "id": "harmoni-test-tenant",
        "name": "Harmoni Residence",
        "email": "shawny@harmoni.com",
        "phone": "+60123456789",
        "plan_tier": "free",
        "whatsapp_jid": "60123456789@s.whatsapp.net",
        "testing_mode": True,
        "test_numbers": ["+60100000003"]
    }
]
```

### Sample Conversations

```json
// tests/fixtures/sample_conversations.json
[
  {
    "id": "conv-001",
    "tenant_id": "w3j-test-tenant",
    "chat_jid": "60100000001@s.whatsapp.net",
    "customer_phone": "+60 10 000 0001",
    "message_content": "What are your business hours?",
    "ai_response": "We're open Monday to Friday, 9 AM - 6 PM (MYT). How can I help you today?",
    "detected_language": "english",
    "timestamp": "2026-02-14T10:00:00Z"
  },
  {
    "id": "conv-002",
    "tenant_id": "w3j-test-tenant",
    "chat_jid": "60100000002@s.whatsapp.net",
    "customer_phone": "+60 10 000 0002",
    "message_content": "Berapa harga servis anda?",
    "ai_response": "Harga bermula dari RM 500 sebulan. Boleh saya tahu lebih lanjut tentang keperluan anda?",
    "detected_language": "malay",
    "timestamp": "2026-02-14T10:15:00Z"
  }
]
```

---

## 🐛 Known Issues & Workarounds

### Issue 1: WhatsApp Connection Status "Disconnected"

**Symptom:** Dashboard shows "Disconnected" even when bridge is connected  
**Root Cause:** Connection status webhook not firing OR database not updating  
**Test:** TC-DASH-004, TC-WA-004  
**Workaround:** Manually query bridge `/health` endpoint  
**Priority:** P0 (must fix before production)

**Fix Required:**
1. Verify `/webhook/connection` is receiving status updates
2. Check database `whatsapp_sessions` table for status column
3. Ensure dashboard queries correct endpoint

---

### Issue 2: Slow Dashboard Queries (>1s)

**Symptom:** Dashboard conversations list slow to load  
**Root Cause:** Missing database indexes on `tenant_id`, `created_at`  
**Test:** TC-DB-004  
**Workaround:** Limit query to last 50 conversations  
**Priority:** P2 (performance optimization)

**Fix Required:**
```sql
-- Create indexes for performance
CREATE INDEX idx_conversations_tenant_created 
ON conversations(tenant_id, created_at DESC);

CREATE INDEX idx_escalations_tenant_priority
ON escalations(tenant_id, priority, created_at DESC);
```

---

## 📝 Test Execution Logs

### Example Test Run Output

```bash
$ pytest tests/e2e/ -v -m smoke

======================== test session starts =========================
platform win32 -- Python 3.11.5, pytest-7.4.0
rootdir: C:\...\w3j-bijou-enterprise
plugins: asyncio-0.21.0, cov-4.1.0
collected 53 items / 33 deselected / 20 selected

tests/e2e/test_security_tenant_isolation.py::test_cross_tenant_escalation_leak PASSED [5%]
tests/e2e/test_security_tenant_isolation.py::test_escalate_requires_tenant_id PASSED [10%]
tests/e2e/test_whatsapp_bridge.py::test_whatsapp_bridge_connected PASSED [15%]
tests/e2e/test_whatsapp_bridge.py::test_send_message_via_bridge PASSED [20%]
tests/e2e/test_whatsapp_bridge.py::test_incoming_message_webhook PASSED [25%]
tests/e2e/test_dashboard_api.py::test_get_conversations PASSED [30%]
tests/e2e/test_dashboard_api.py::test_dashboard_stats PASSED [35%]
tests/e2e/test_dashboard_api.py::test_whatsapp_connection_status FAILED [40%] ⚠️
tests/e2e/test_ai_responses.py::test_gemini_api_response PASSED [45%]
tests/e2e/test_ai_responses.py::test_escalation_keyword_detection PASSED [50%]
tests/e2e/test_database.py::test_supabase_connection PASSED [55%]
tests/e2e/test_database.py::test_conversation_persisted PASSED [60%]
tests/e2e/test_performance.py::test_health_check_response_time PASSED [65%]

===================== 18 passed, 1 failed in 45.2s ======================

FAILED tests/e2e/test_dashboard_api.py::test_whatsapp_connection_status
AssertionError: Expected status='connected', got status='disconnected'
```

**Action:** Investigate failing test before production deployment

---

## 🎓 Test Development Guidelines

### Writing Good E2E Tests

```python
# ✅ GOOD: Clear, isolated, descriptive
@pytest.mark.e2e
@pytest.mark.smoke
async def test_dashboard_returns_tenant_conversations():
    """
    GIVEN: 5 conversations exist for tenant w3j
    WHEN: GET /api/dashboard/conversations?tenant_id=w3j
    THEN: Exactly 5 conversations should be returned
    AND: All conversations belong to tenant w3j
    AND: Response time < 1 second
    """
    # Arrange
    tenant_id = "w3j"
    
    # Act
    start = time.time()
    response = await client.get(
        f"{BIJOU_URL}/api/dashboard/conversations",
        headers={"X-Tenant-ID": tenant_id}
    )
    duration = time.time() - start
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["conversations"]) == 5
    assert all(c["tenant_id"] == tenant_id for c in data["conversations"])
    assert duration < 1.0


# ❌ BAD: Unclear, multiple responsibilities, no documentation
async def test_dashboard():
    response = await client.get("/api/dashboard/conversations")
    assert response.status_code == 200
    # What is this testing? What's the expected result?
```

---

### Test Naming Convention

```
test_{feature}_{scenario}_{expected_result}

Examples:
- test_escalation_requires_tenant_id_returns_none()
- test_whatsapp_bridge_connected_returns_true()
- test_conversations_filtered_by_tenant_no_leak()
```

---

## 📞 Support & Contact

**Owner:** @architect  
**Team:** W3J Consulting  
**On-Call Engineer:** Muhammad Nurunnabi (Jewel)  
**Contact:** +60 14 385 6929

**Escalation Path:**
1. Check test logs: `pytest tests/e2e/ -v --tb=short`
2. Review health check: `python tests/e2e_health_check.py --env staging`
3. Contact @architect for deployment blockers
4. Emergency rollback: Follow manual rollback procedure above

---

## 🔄 Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| v1.0 | 2026-02-14 | @architect | Initial E2E testing strategy |
| v1.1 | TBD | TBD | Add performance benchmarks |
| v1.2 | TBD | TBD | Add load testing scenarios |

---

**End of Document** ✅  
**Status:** Ready for Implementation  
**Next Steps:** Create test files, run staging validation, deploy to production
