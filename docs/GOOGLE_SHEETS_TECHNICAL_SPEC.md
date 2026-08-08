# Google Sheets Dashboard - Technical Specification
**Project:** Bijou AI WhatsApp Management  
**Feature:** Automated Google Sheets Dashboard  
**Version:** 1.0.0  

---

## 1. GOOGLE SHEETS SCHEMA

### Sheet 1: Conversations
| Column | Type | Source | Validation |
|--------|------|--------|------------|
| Timestamp | DateTime | conversations.timestamp | Format: YYYY-MM-DD HH:MM:SS |
| Customer Phone | Text | conversations.chat_jid | Remove @s.whatsapp.net suffix |
| Message | Text | conversations.message_content | Max 4096 chars |
| AI Response | Text | conversations.ai_response | Max 4096 chars |
| Language | Dropdown | conversations.detected_language | [en, ms, zh, ta, manglish] |
| Lead Status | Dropdown | via lead_converter | [cold, warm, hot, qualified] |
| Sentiment | Dropdown | via ASI analysis | [positive, neutral, negative, frustrated] |

**Formula Examples:**
```
# Count hot leads
=COUNTIF(F:F,"hot")

# Average response time (calculated field)
=AVERAGE(A2:A-B2:B)
```

---

### Sheet 2: Escalations
| Column | Type | Source | Validation |
|--------|------|--------|------------|
| Created At | DateTime | escalations.created_at | |
| Customer Phone | Text | escalations.chat_jid | |
| Reason | Text | escalations.reason | |
| Priority | Dropdown | escalations.priority | [low, normal, high, urgent] |
| Status | Dropdown | escalations.status | [pending, in_progress, resolved] |
| Assigned To | Text | escalations.assigned_to | Editable, triggers webhook |

**Protected Ranges:**
- Columns A-D: Read-only (sync from database)
- Columns E-F: Editable (triggers webhook on change)

**Conditional Formatting:**
- Priority "urgent": Red background
- Status "resolved": Green text
- Status "pending": Orange background

---

### Sheet 3: Stats (Real-time Dashboard)
| Metric | Formula | Description |
|--------|---------|-------------|
| Total Conversations | `=COUNTA(Conversations!A:A)-1` | Row count minus header |
| Hot Leads | `=COUNTIF(Conversations!F:F,"hot")` | Lead status = hot |
| Total Escalations | `=COUNTA(Escalations!A:A)-1` | |
| Pending Escalations | `=COUNTIFS(Escalations!E:E,"pending")` | |
| Avg Response Time | `=AVERAGE(...)` | Calculated from timestamps |
| Sentiment Distribution | Pie chart | positive vs neutral vs negative |

**Charts:**
1. **Conversation Trends (Line Chart)**
   - X-axis: Date (grouped by day)
   - Y-axis: Count of conversations
   - Data range: Conversations!A:A

2. **Lead Funnel (Funnel Chart)**
   - cold → warm → hot → qualified
   - Data: `=COUNTIF(Conversations!F:F,status)`

3. **Escalation Priority (Pie Chart)**
   - Data: Escalations!D:D
   - Colors: Low=Green, Normal=Blue, High=Orange, Urgent=Red

---

### Sheet 4: Logs
| Column | Type | Purpose |
|--------|------|---------|
| Timestamp | DateTime | When error/event occurred |
| Function | Text | AppScript function name |
| Level | Text | INFO, WARNING, ERROR |
| Message | Text | Error message or event description |

**Auto-cleanup:**
```javascript
// Delete logs older than 30 days
function cleanupOldLogs() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Logs');
  const data = sheet.getDataRange().getValues();
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - 30);
  
  for (let i = data.length - 1; i >= 1; i--) {
    if (data[i][0] < cutoffDate) {
      sheet.deleteRow(i + 1);
    }
  }
}
```

---

### Sheet 5: Settings
| Setting | Value | Description |
|---------|-------|-------------|
| Tenant ID | UUID | Auto-populated from script properties |
| Bijou API URL | URL | https://bijou-staging.fly.dev |
| Last Sync | DateTime | Updated by sync functions |
| Sync Frequency | Dropdown | [2 min, 5 min, 10 min, 30 min] |
| Auto-sync Enabled | Checkbox | Toggle time-based triggers |

**Config Management:**
```javascript
function getConfig() {
  const settingsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Settings');
  return {
    tenantId: settingsSheet.getRange('B1').getValue(),
    apiUrl: settingsSheet.getRange('B2').getValue(),
    syncFrequency: settingsSheet.getRange('B4').getValue()
  };
}
```

---

## 2. APPSCRIPT API REQUIREMENTS

### Required Libraries
- None (uses built-in UrlFetchApp, SpreadsheetApp)

### Script Properties (Secret Storage)
```javascript
// Set via Apps Script Editor → Project Settings → Script Properties
Properties:
  BIJOU_API_KEY: "sk_bijou_..."
  TENANT_ID: "607690ec-4ff7-4ef4-b98e-bfb00442fe95"
  BIJOU_API_URL: "https://bijou-staging.fly.dev"
```

### Functions to Implement

#### Core Sync Functions
```javascript
function syncConversations() // Fetch conversations from Bijou API
function syncEscalations()   // Fetch escalations from Bijou API
function updateStats()       // Calculate real-time stats
```

#### Trigger Management
```javascript
function setupTriggers()     // Install time-based triggers
function removeTriggers()    // Uninstall all triggers
```

#### Event Handlers
```javascript
function onEdit(e)           // Triggered when user edits sheet
function onOpen(e)           // Add custom menu on open
```

#### Utilities
```javascript
function logError(fn, msg)   // Log to Logs sheet
function getConfig()         // Read Settings sheet
function testConnection()    // Verify API connectivity
```

---

## 3. BIJOU BACKEND INTEGRATION POINTS

### New Endpoints to Create

#### 3.1 Webhook Receiver
```python
POST /api/v1/webhooks/sheets
Headers:
  X-API-Key: <tenant_api_key>
  Content-Type: application/json

Body:
{
  "tenant_id": "uuid",
  "action": "update_escalation" | "update_conversation" | "create_note",
  "data": {
    "escalation_id": "uuid",
    "field": "status" | "assigned_to",
    "value": "resolved"
  }
}

Response (200 OK):
{
  "status": "processed",
  "updated_at": "2026-02-15T10:31:00Z"
}
```

#### 3.2 Spreadsheet Creation Endpoint
```python
POST /api/sheets/create
Headers:
  X-API-Key: <tenant_api_key>
  
Body:
{
  "tenant_id": "uuid"
}

Response (200 OK):
{
  "spreadsheet_id": "abc123...",
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/...",
  "appscript_deployment_id": "xyz789..."
}
```

#### 3.3 Existing Endpoints (No Changes)
- GET /api/conversations/{tenant_id}
- GET /api/escalations/{tenant_id}
- GET /api/dashboard/stats/{tenant_id}

---

## 4. SECURITY & AUTHENTICATION FLOW

### Authentication Model

```
┌─────────────────────┐
│  Google AppScript   │
│  (Server-side JS)   │
└──────────┬──────────┘
           │
           │ 1. Fetch data
           │ Headers: X-API-Key
           ▼
┌─────────────────────┐
│   Bijou Backend     │
│   (FastAPI)         │
│                     │
│ 2. Validate API key │
│ 3. Check tenant_id  │
│ 4. Return data      │
└──────────┬──────────┘
           │
           │ 5. Query database
           ▼
┌─────────────────────┐
│   Supabase          │
│   (PostgreSQL)      │
│                     │
│ RLS enforces        │
│ tenant isolation    │
└─────────────────────┘
```

### Credential Storage

**❌ NEVER DO:**
```javascript
// BAD - Hardcoded in script
const API_KEY = "sk_bijou_abc123";
```

**✅ ALWAYS DO:**
```javascript
// GOOD - Stored in Script Properties
const API_KEY = PropertiesService.getScriptProperties().getProperty('BIJOU_API_KEY');
```

### API Key Validation (Bijou Backend)
```python
async def validate_api_key(api_key: str, tenant_id: str) -> bool:
    """Validate API key belongs to tenant."""
    response = await supabase.table("tenants") \
        .select("id") \
        .eq("id", tenant_id) \
        .eq("api_key", api_key) \
        .execute()
    
    return len(response.data) > 0
```

---

## 5. TESTING STRATEGY

### Unit Tests (AppScript)
**Challenge:** Apps Script doesn't have built-in testing framework

**Solution:** Use [GasT](https://github.com/huan/gast) or manual testing

```javascript
function testSyncConversations() {
  const result = syncConversations();
  if (result.status !== 'success') {
    throw new Error('Sync failed');
  }
  Logger.log('✅ testSyncConversations passed');
}

function runAllTests() {
  try {
    testSyncConversations();
    testSyncEscalations();
    testUpdateStats();
    Logger.log('✅ All tests passed');
  } catch (error) {
    Logger.log(`❌ Test failed: ${error.message}`);
  }
}
```

### Integration Tests (Python)
```python
# tests/integration/test_sheets_integration.py

@pytest.mark.integration
async def test_appscript_to_bijou_webhook():
    """Test AppScript can send webhook to Bijou."""
    # 1. Simulate AppScript webhook call
    payload = {
        "tenant_id": TEST_TENANT_ID,
        "action": "update_escalation",
        "data": {
            "escalation_id": "test-uuid",
            "field": "status",
            "value": "resolved"
        }
    }
    
    # 2. Send to webhook endpoint
    response = await client.post(
        "/api/v1/webhooks/sheets",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    # 3. Verify response
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    
    # 4. Verify database updated
    escalation = await get_escalation("test-uuid")
    assert escalation["status"] == "resolved"
```

### E2E Tests
```python
@pytest.mark.e2e
async def test_full_sheets_workflow():
    """Test complete workflow: Create spreadsheet → Sync → Edit → Webhook."""
    # 1. Create tenant
    tenant = await create_test_tenant()
    
    # 2. Create spreadsheet
    spreadsheet = await create_dashboard_spreadsheet(tenant["id"])
    
    # 3. Trigger conversation in Bijou
    await simulate_whatsapp_message(tenant["id"], "Test message")
    
    # 4. Wait for AppScript sync
    await asyncio.sleep(300)  # 5 minutes
    
    # 5. Verify sheet updated
    sheet_data = await read_conversations_sheet(spreadsheet["spreadsheet_id"])
    assert "Test message" in [row["message"] for row in sheet_data]
    
    # 6. Edit sheet (change escalation status)
    await update_sheet_cell(
        spreadsheet["spreadsheet_id"],
        "Escalations",
        "E2",  # Status column
        "resolved"
    )
    
    # 7. Verify webhook triggered
    await asyncio.sleep(5)
    escalation = await get_latest_escalation(tenant["id"])
    assert escalation["status"] == "resolved"
```

---

## 6. PERFORMANCE BENCHMARKS

### Target Metrics
| Operation | Target | Rationale |
|-----------|--------|-----------|
| Spreadsheet creation | <5s | User waits during onboarding |
| Sync 100 conversations | <10s | AppScript execution limit: 6min |
| Sync 10 escalations | <3s | Critical data |
| Webhook response | <500ms | Real-time updates |
| Sheet rendering (1000 rows) | <2s | Google Sheets handles this |

### Optimization Strategies
1. **Batch API calls** - Fetch all data in single request
2. **Use `setValues()` instead of `setValue()`** - 100x faster
3. **Cache spreadsheet references** - Don't call `getSheetByName()` repeatedly
4. **Limit data to last 30 days** - Add `WHERE timestamp > NOW() - INTERVAL '30 days'`

---

## 7. DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] E2E test passing
- [ ] Security audit approved
- [ ] Performance benchmarks met
- [ ] Code review by @architect
- [ ] Documentation updated

### Deployment Steps
1. **Deploy Bijou backend changes**
   ```powershell
   cd w3j-bijou-enterprise
   C:\Users\w3jbt\.fly\bin\flyctl.exe deploy --app bijou-staging
   ```

2. **Deploy AppScript**
   ```bash
   # Using clasp CLI
   clasp push
   clasp deploy --description "Sheets integration v1.0.0"
   ```

3. **Configure Script Properties**
   - Open Apps Script Editor
   - Project Settings → Script Properties
   - Add: BIJOU_API_KEY, TENANT_ID, BIJOU_API_URL

4. **Run Initial Setup**
   ```javascript
   // In Apps Script Editor
   setupTriggers();  // Install time-based triggers
   syncConversations();  // Initial data load
   syncEscalations();
   updateStats();
   ```

5. **Health Checks**
   ```powershell
   # Verify backend endpoint
   curl https://bijou-staging.fly.dev/api/v1/webhooks/sheets -X POST \
     -H "X-API-Key: test" \
     -d '{"tenant_id":"test","action":"update_escalation","data":{}}'
   
   # Expected: 200 OK or 401 Unauthorized (auth working)
   ```

### Post-Deployment
- [ ] Monitor logs for 30 minutes
- [ ] Verify sync triggers running every 5 minutes
- [ ] Test manual edit → webhook flow
- [ ] Check error rate <1%
- [ ] Notify tenant owner of new dashboard

---

## 8. KNOWN LIMITATIONS

### Google API Quotas (Free Tier)
- **Sheets API:** 100 requests/100 seconds/user
- **AppScript Executions:** 20,000/day
- **Script Runtime:** 6 minutes max per execution

**Mitigation:**
- Implement exponential backoff
- Cache data in script properties (up to 500KB)
- Reduce sync frequency if quota hit

### Data Freshness
- **Delay:** 2-5 minutes (time-based triggers)
- **Trade-off:** Real-time updates would exceed quota

**Mitigation:**
- Add manual "Sync Now" button
- Push critical updates via webhook

### AppScript Limitations
- **No async/await** - Must use synchronous UrlFetchApp
- **No npm packages** - Pure JavaScript only
- **6-minute execution limit** - Batch processing required

---

## 9. FUTURE ENHANCEMENTS

### Phase 2 Features (Post-MVP)
1. **Advanced Charts**
   - Conversation trends by language
   - Lead conversion funnel
   - Sentiment analysis over time

2. **Custom Filters**
   - Filter by date range
   - Filter by customer phone
   - Search messages

3. **Export Functionality**
   - Export to CSV
   - Email daily reports
   - Schedule automated backups

4. **Multi-User Collaboration**
   - Role-based access (admin, viewer, agent)
   - Comment threads on escalations
   - Task assignment

---

**Document Version:** 1.0.0  
**Created:** 2026-02-15  
**Status:** Production-Ready Specification  
**Owner:** @architect  
**Reviewers:** @backend, @fullstack, @google-workspace, @security
