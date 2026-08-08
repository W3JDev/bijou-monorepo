# Google Sheets Dashboard - Detailed Execution Plan
**Project:** Bijou AI WhatsApp Customer Management System  
**Feature:** Google Sheets + AppScript Dashboard (ZERO Manual Setup)  
**Timeline:** 2-4 hours (with parallel execution)  
**Cost:** $0 (free Google services only)  

---

## 🎯 PROJECT OBJECTIVES

### Business Goals
- **Enable self-service dashboard access** for clients without coding
- **Zero manual setup required** (automated spreadsheet creation)
- **Real-time data sync** between Bijou backend and Google Sheets
- **Cost-efficient solution** using free Google Workspace APIs

### Technical Goals
- **Automated spreadsheet generation** via Google Sheets API
- **Bidirectional data flow** (Sheets ↔ Bijou backend)
- **Secure OAuth 2.0 authentication** with service accounts
- **Enterprise-level error handling** and logging

---

## 📊 PHASE BREAKDOWN

```
Phase 1: Analysis (30 min)
├── @backend: API endpoint inventory
├── @db-admin: Schema documentation
└── @google-workspace: OAuth credential verification

Phase 2: Sheets Setup (45 min)
├── @google-workspace: Spreadsheet creation script
├── @db-admin: Data validation rules
└── @qa-engineer: Acceptance criteria

Phase 3: AppScript Backend (60 min)
├── @fullstack: AppScript functions
├── @backend: API integration contracts
└── @security: Credential storage audit

Phase 4: Web Interfaces (45 min)
├── @fullstack: Dashboard HTML/CSS/JS
└── @qa-engineer: UI testing strategy

Phase 5: Backend Integration (60 min)
├── @backend: Webhook sender implementation
├── @devops: Environment variables
└── @security: Webhook authentication

Phase 6: Testing & Deployment (30 min)
└── @qa-engineer: E2E tests with all agents
```

**Total Time:** 270 minutes (4.5 hours)  
**With Parallel Execution:** 150 minutes (2.5 hours)

---

## PHASE 1: ANALYSIS (30 MINUTES)

### Objective
Understand current system architecture and identify integration points.

### Tasks

#### TASK 1.1: Locate API Endpoints
**Owner:** @backend  
**Duration:** 15 minutes  
**Parallel:** Yes (with 1.2, 1.3)

**Deliverables:**
1. Document: `docs/sheets/bijou_api_inventory.md`
2. List all FastAPI endpoints in `src/core/bijou.py`
3. Document request/response formats (Pydantic models)
4. Identify authentication mechanism (API key, OAuth, etc.)

**Verification Commands:**
```bash
# List all FastAPI routes
python -c "from src.core.bijou import app; print('\n'.join([f'{r.path} [{r.methods}]' for r in app.routes]))"

# Verify API documentation
curl http://localhost:8080/docs -o api_docs.html
```

**Expected Output:**
```markdown
# Bijou AI API Inventory

## Dashboard Endpoints
- GET /api/dashboard/stats/{tenant_id}
  - Auth: X-API-Key header
  - Response: { conversations: int, escalations: int, ... }

## Conversations Endpoints
- GET /api/conversations/{tenant_id}
  - Query params: limit, offset, chat_jid
  - Response: [ { id, chat_jid, message_content, ... } ]

## Escalations Endpoints
- GET /api/escalations/{tenant_id}
  - Query params: status (pending, resolved)
  - Response: [ { id, chat_jid, priority, status, ... } ]
```

---

#### TASK 1.2: Extract Supabase Schema
**Owner:** @db-admin  
**Duration:** 15 minutes  
**Parallel:** Yes (with 1.1, 1.3)

**Deliverables:**
1. Document: `docs/sheets/database_schema.md`
2. List all tables relevant to dashboard
3. Document column types and constraints
4. Identify relationships (foreign keys)

**Verification Commands:**
```sql
-- Get table schemas
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('conversations', 'escalations', 'notification_logs', 'tenants')
ORDER BY table_name, ordinal_position;

-- Get foreign key relationships
SELECT
    tc.table_name, 
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public';
```

**Expected Output:**
```markdown
# Database Schema

## conversations table
- id: UUID (primary key)
- tenant_id: UUID (foreign key → tenants.id)
- chat_jid: TEXT (customer WhatsApp ID)
- message_content: TEXT
- ai_response: TEXT
- detected_language: TEXT (en, ms, zh, ta, manglish)
- timestamp: TIMESTAMP

## escalations table
- id: UUID (primary key)
- tenant_id: UUID (foreign key → tenants.id)
- chat_jid: TEXT
- status: TEXT (pending, in_progress, resolved)
- priority: TEXT (low, normal, high, urgent)
- created_at: TIMESTAMP
```

---

#### TASK 1.3: Locate OAuth Credentials
**Owner:** @google-workspace  
**Duration:** 10 minutes  
**Parallel:** Yes (with 1.1, 1.2)

**Deliverables:**
1. Confirm Google Cloud Project exists
2. Verify service account credentials
3. Document OAuth 2.0 scopes required
4. Check API quotas and limits

**Verification Commands:**
```bash
# Check if credentials file exists
ls -la credentials.json

# Verify service account JSON structure
python -c "import json; creds = json.load(open('credentials.json')); print(f'Service Account: {creds['client_email']}')"

# Test Google Sheets API access
python scripts/test_google_api_access.py
```

**Expected Output:**
```markdown
# Google Workspace Configuration

## Service Account
- Email: bijou-ai@bijou-sheets-integration.iam.gserviceaccount.com
- Project ID: bijou-sheets-integration
- Key ID: abc123...

## Required Scopes
- https://www.googleapis.com/auth/spreadsheets (read/write sheets)
- https://www.googleapis.com/auth/drive.file (create spreadsheets)
- https://www.googleapis.com/auth/script.projects (deploy AppScript)

## API Quotas (Free Tier)
- Sheets API: 100 requests/100 seconds/user
- Drive API: 1000 requests/100 seconds/user
- AppScript Executions: 20,000/day
```

---

### Phase 1 Exit Criteria
- [ ] All API endpoints documented with authentication methods
- [ ] Database schema exported with relationships mapped
- [ ] Google Cloud credentials verified and tested
- [ ] No blockers identified for Phase 2

---

## PHASE 2: SHEETS SETUP (45 MINUTES)

### Objective
Create automated spreadsheet generation script with proper schema.

### Tasks

#### TASK 2.1: Create Spreadsheet Programmatically
**Owner:** @google-workspace  
**Duration:** 30 minutes  
**Parallel:** Partially (with 2.2)

**Deliverables:**
1. Script: `scripts/create_dashboard_spreadsheet.py`
2. Function to create spreadsheet via Google Sheets API
3. Function to configure 5 sheets (Conversations, Escalations, Stats, Logs, Settings)
4. Function to apply formatting (headers, data validation, protected ranges)

**Implementation:**
```python
# scripts/create_dashboard_spreadsheet.py

from googleapiclient.discovery import build
from google.oauth2 import service_account
import os

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
          'https://www.googleapis.com/auth/drive.file']

def create_dashboard_spreadsheet(tenant_id: str, tenant_name: str) -> dict:
    """
    Create a new Google Sheets dashboard for a tenant.
    
    Args:
        tenant_id: UUID of the tenant
        tenant_name: Business name
        
    Returns:
        {
            'spreadsheet_id': 'abc123...',
            'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/...',
            'sheets': {
                'conversations': 0,
                'escalations': 1,
                'stats': 2,
                'logs': 3,
                'settings': 4
            }
        }
    """
    # Authenticate
    creds = service_account.Credentials.from_service_account_file(
        'credentials.json', scopes=SCOPES
    )
    service = build('sheets', 'v4', credentials=creds)
    
    # Create spreadsheet
    spreadsheet = {
        'properties': {
            'title': f'{tenant_name} - Bijou AI Dashboard'
        },
        'sheets': [
            {'properties': {'title': 'Conversations', 'gridProperties': {'frozenRowCount': 1}}},
            {'properties': {'title': 'Escalations', 'gridProperties': {'frozenRowCount': 1}}},
            {'properties': {'title': 'Stats', 'gridProperties': {'frozenRowCount': 0}}},
            {'properties': {'title': 'Logs', 'gridProperties': {'frozenRowCount': 1}}},
            {'properties': {'title': 'Settings', 'gridProperties': {'frozenRowCount': 0}}}
        ]
    }
    
    result = service.spreadsheets().create(body=spreadsheet).execute()
    spreadsheet_id = result['spreadsheetId']
    
    # Configure each sheet
    configure_conversations_sheet(service, spreadsheet_id)
    configure_escalations_sheet(service, spreadsheet_id)
    configure_stats_sheet(service, spreadsheet_id)
    configure_logs_sheet(service, spreadsheet_id)
    configure_settings_sheet(service, spreadsheet_id)
    
    # Store spreadsheet_id in database
    from src.saas.tenant_manager import TenantManager
    tenant_mgr = TenantManager()
    tenant_mgr.update_tenant_settings(
        tenant_id, 
        {'dashboard_spreadsheet_id': spreadsheet_id}
    )
    
    return {
        'spreadsheet_id': spreadsheet_id,
        'spreadsheet_url': f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}',
        'sheets': {
            'conversations': 0,
            'escalations': 1,
            'stats': 2,
            'logs': 3,
            'settings': 4
        }
    }

def configure_conversations_sheet(service, spreadsheet_id):
    """Configure Conversations sheet with headers and formatting."""
    headers = [
        ['Timestamp', 'Customer Phone', 'Message', 'AI Response', 'Language', 'Lead Status', 'Sentiment']
    ]
    
    # Write headers
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Conversations!A1:G1',
        valueInputOption='RAW',
        body={'values': headers}
    ).execute()
    
    # Format headers (bold, background color)
    requests = [{
        'repeatCell': {
            'range': {
                'sheetId': 0,  # Conversations sheet
                'startRowIndex': 0,
                'endRowIndex': 1
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
                    'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                }
            },
            'fields': 'userEnteredFormat(backgroundColor,textFormat)'
        }
    }]
    
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': requests}
    ).execute()

# Similar functions for other sheets...
```

**Verification:**
```bash
# Run script
python scripts/create_dashboard_spreadsheet.py --tenant_id "607690ec-..." --tenant_name "Test Tenant"

# Check output
# Expected: Spreadsheet URL printed, database updated
```

---

#### TASK 2.2: Design Data Validation Rules
**Owner:** @db-admin  
**Duration:** 20 minutes  
**Parallel:** Yes (with 2.1)

**Deliverables:**
1. Document: `docs/sheets/validation_rules.md`
2. List data validation rules that mirror DB constraints
3. Define dropdowns for enum fields (status, priority, language)

**Example Rules:**
```markdown
# Validation Rules

## Conversations Sheet
- Timestamp: Date/Time format (YYYY-MM-DD HH:MM:SS)
- Customer Phone: Text (regex: \+\d{10,15})
- Language: Dropdown (en, ms, zh, ta, manglish)
- Lead Status: Dropdown (cold, warm, hot, qualified)
- Sentiment: Dropdown (positive, neutral, negative, frustrated)

## Escalations Sheet
- Status: Dropdown (pending, in_progress, resolved)
- Priority: Dropdown (low, normal, high, urgent)
- Assigned To: Text (employee name or "Unassigned")
```

---

#### TASK 2.3: Define Acceptance Criteria
**Owner:** @qa-engineer  
**Duration:** 15 minutes  
**Parallel:** Yes (with 2.1, 2.2)

**Deliverables:**
1. Document: `docs/sheets/acceptance_criteria.md`
2. List testable success criteria for spreadsheet creation

**Acceptance Criteria:**
```markdown
# Spreadsheet Creation Acceptance Criteria

## Functional Requirements
- [ ] Spreadsheet created with tenant name in title
- [ ] All 5 sheets present (Conversations, Escalations, Stats, Logs, Settings)
- [ ] Headers formatted (bold, colored background)
- [ ] Data validation applied to all enum columns
- [ ] Spreadsheet ID stored in database (tenants.settings.dashboard_spreadsheet_id)

## Performance Requirements
- [ ] Spreadsheet creation completes in <5 seconds
- [ ] Can handle 1000+ rows without performance degradation

## Security Requirements
- [ ] Only service account has edit access
- [ ] Tenant owner has view-only access (shared via email)
- [ ] No PII logged in creation process

## Error Handling
- [ ] If creation fails, no partial spreadsheet left
- [ ] Database rolled back if spreadsheet creation fails
- [ ] Clear error message returned to user
```

---

### Phase 2 Exit Criteria
- [ ] Spreadsheet creation script working end-to-end
- [ ] All validation rules documented and implemented
- [ ] Acceptance criteria approved by @architect
- [ ] Manual test completed (1 test spreadsheet created)

---

## PHASE 3: APPSCRIPT BACKEND (60 MINUTES)

### Objective
Implement Google Apps Script functions for data sync and automation.

### Tasks

#### TASK 3.1: Implement AppScript Functions
**Owner:** @fullstack  
**Duration:** 45 minutes  
**Parallel:** Partially (with 3.2)

**Deliverables:**
1. File: `appscript/Code.gs` (Google Apps Script)
2. Functions:
   - `syncConversations()` - Fetch from Bijou API, update sheet
   - `syncEscalations()` - Fetch escalations, update sheet
   - `updateStats()` - Calculate real-time stats
   - `onEdit(e)` - Trigger webhook on manual sheet edit
   - `setupTriggers()` - Install time-based and event triggers

**Implementation:**
```javascript
// appscript/Code.gs

/**
 * Global configuration - set these in Script Properties
 */
const CONFIG = {
  BIJOU_API_URL: PropertiesService.getScriptProperties().getProperty('BIJOU_API_URL'),
  BIJOU_API_KEY: PropertiesService.getScriptProperties().getProperty('BIJOU_API_KEY'),
  TENANT_ID: PropertiesService.getScriptProperties().getProperty('TENANT_ID')
};

/**
 * Sync conversations from Bijou API to Conversations sheet
 */
function syncConversations() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Conversations');
  
  // Fetch data from Bijou API
  const url = `${CONFIG.BIJOU_API_URL}/api/conversations/${CONFIG.TENANT_ID}?limit=100`;
  const options = {
    'method': 'get',
    'headers': {
      'X-API-Key': CONFIG.BIJOU_API_KEY
    },
    'muteHttpExceptions': true
  };
  
  try {
    const response = UrlFetchApp.fetch(url, options);
    const data = JSON.parse(response.getContentText());
    
    if (response.getResponseCode() !== 200) {
      throw new Error(`API Error: ${data.detail || 'Unknown error'}`);
    }
    
    // Clear existing data (keep headers)
    const lastRow = sheet.getLastRow();
    if (lastRow > 1) {
      sheet.getRange(2, 1, lastRow - 1, 7).clearContent();
    }
    
    // Write new data
    const rows = data.map(conv => [
      new Date(conv.timestamp),
      conv.chat_jid.replace('@s.whatsapp.net', ''),
      conv.message_content,
      conv.ai_response,
      conv.detected_language || 'en',
      conv.lead_status || 'cold',
      conv.sentiment || 'neutral'
    ]);
    
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, 7).setValues(rows);
    }
    
    // Update last sync time
    PropertiesService.getScriptProperties().setProperty(
      'LAST_SYNC_CONVERSATIONS', 
      new Date().toISOString()
    );
    
    Logger.log(`✅ Synced ${rows.length} conversations`);
    
  } catch (error) {
    Logger.log(`❌ Sync failed: ${error.message}`);
    
    // Log error to Logs sheet
    logError('syncConversations', error.message);
    
    // Send notification (optional)
    sendErrorNotification(error);
  }
}

/**
 * Sync escalations from Bijou API
 */
function syncEscalations() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Escalations');
  
  const url = `${CONFIG.BIJOU_API_URL}/api/escalations/${CONFIG.TENANT_ID}`;
  const options = {
    'method': 'get',
    'headers': {
      'X-API-Key': CONFIG.BIJOU_API_KEY
    },
    'muteHttpExceptions': true
  };
  
  try {
    const response = UrlFetchApp.fetch(url, options);
    const data = JSON.parse(response.getContentText());
    
    if (response.getResponseCode() !== 200) {
      throw new Error(`API Error: ${data.detail}`);
    }
    
    // Clear existing data
    const lastRow = sheet.getLastRow();
    if (lastRow > 1) {
      sheet.getRange(2, 1, lastRow - 1, 6).clearContent();
    }
    
    // Write new data
    const rows = data.map(esc => [
      new Date(esc.created_at),
      esc.chat_jid.replace('@s.whatsapp.net', ''),
      esc.reason || 'Unknown',
      esc.priority,
      esc.status,
      esc.assigned_to || 'Unassigned'
    ]);
    
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, 6).setValues(rows);
    }
    
    Logger.log(`✅ Synced ${rows.length} escalations`);
    
  } catch (error) {
    Logger.log(`❌ Escalations sync failed: ${error.message}`);
    logError('syncEscalations', error.message);
  }
}

/**
 * Calculate and update stats
 */
function updateStats() {
  const conversationsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Conversations');
  const escalationsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Escalations');
  const statsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Stats');
  
  // Count conversations
  const totalConversations = conversationsSheet.getLastRow() - 1;
  
  // Count escalations
  const totalEscalations = escalationsSheet.getLastRow() - 1;
  
  // Count pending escalations
  const escalationData = escalationsSheet.getRange(2, 5, escalationsSheet.getLastRow() - 1, 1).getValues();
  const pendingEscalations = escalationData.filter(row => row[0] === 'pending').length;
  
  // Update stats sheet
  statsSheet.clear();
  statsSheet.getRange('A1:B1').setValues([['Metric', 'Value']]).setFontWeight('bold');
  statsSheet.getRange('A2:B5').setValues([
    ['Total Conversations', totalConversations],
    ['Total Escalations', totalEscalations],
    ['Pending Escalations', pendingEscalations],
    ['Last Updated', new Date()]
  ]);
  
  Logger.log(`✅ Stats updated`);
}

/**
 * Webhook sender - called when sheet is manually edited
 */
function onEdit(e) {
  const sheet = e.source.getActiveSheet();
  const sheetName = sheet.getName();
  
  // Only trigger for Escalations sheet
  if (sheetName !== 'Escalations') {
    return;
  }
  
  const range = e.range;
  const row = range.getRow();
  const col = range.getColumn();
  
  // Column 5 = Status, Column 6 = Assigned To
  if (col !== 5 && col !== 6) {
    return;
  }
  
  // Get escalation ID (column A)
  const escalationId = sheet.getRange(row, 1).getValue();
  const newValue = range.getValue();
  
  // Send update to Bijou backend
  const url = `${CONFIG.BIJOU_API_URL}/api/v1/webhooks/sheets`;
  const payload = {
    'tenant_id': CONFIG.TENANT_ID,
    'action': 'update_escalation',
    'data': {
      'escalation_id': escalationId,
      'field': col === 5 ? 'status' : 'assigned_to',
      'value': newValue
    }
  };
  
  const options = {
    'method': 'post',
    'contentType': 'application/json',
    'headers': {
      'X-API-Key': CONFIG.BIJOU_API_KEY
    },
    'payload': JSON.stringify(payload),
    'muteHttpExceptions': true
  };
  
  try {
    const response = UrlFetchApp.fetch(url, options);
    Logger.log(`✅ Webhook sent: ${response.getContentText()}`);
  } catch (error) {
    Logger.log(`❌ Webhook failed: ${error.message}`);
    logError('onEdit', error.message);
  }
}

/**
 * Setup time-based triggers
 */
function setupTriggers() {
  // Delete existing triggers
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => ScriptApp.deleteTrigger(trigger));
  
  // Sync conversations every 5 minutes
  ScriptApp.newTrigger('syncConversations')
    .timeBased()
    .everyMinutes(5)
    .create();
  
  // Sync escalations every 2 minutes
  ScriptApp.newTrigger('syncEscalations')
    .timeBased()
    .everyMinutes(2)
    .create();
  
  // Update stats every 10 minutes
  ScriptApp.newTrigger('updateStats')
    .timeBased()
    .everyMinutes(10)
    .create();
  
  Logger.log('✅ Triggers installed');
}

/**
 * Log error to Logs sheet
 */
function logError(functionName, errorMessage) {
  const logsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Logs');
  logsSheet.appendRow([new Date(), functionName, 'ERROR', errorMessage]);
}

/**
 * Send error notification (optional - via email or webhook)
 */
function sendErrorNotification(error) {
  // Could send email to tenant owner or post to Slack/Discord
  // For now, just log
  Logger.log(`Error notification: ${error.message}`);
}
```

**Verification:**
1. Deploy AppScript to test spreadsheet
2. Set script properties (BIJOU_API_URL, BIJOU_API_KEY, TENANT_ID)
3. Run `syncConversations()` manually
4. Check Conversations sheet populated
5. Run `setupTriggers()` and verify triggers installed

---

#### TASK 3.2: Design API Integration Contracts
**Owner:** @backend  
**Duration:** 30 minutes  
**Parallel:** Yes (with 3.1)

**Deliverables:**
1. Document: `docs/sheets/api_contracts.md`
2. Define request/response schemas for all AppScript → Bijou calls
3. Define webhook payload schema for Bijou → AppScript calls

**API Contracts:**
```markdown
# API Contracts

## AppScript → Bijou (Data Fetch)

### GET /api/conversations/{tenant_id}
**Request:**
```http
GET /api/conversations/607690ec-4ff7-4ef4-b98e-bfb00442fe95?limit=100&offset=0
X-API-Key: bijou_api_key_123
```

**Response (200 OK):**
```json
[
  {
    "id": "uuid-1",
    "tenant_id": "607690ec-...",
    "chat_jid": "+60123456789@s.whatsapp.net",
    "message_content": "I want to buy a condo",
    "ai_response": "Great! What's your budget?",
    "detected_language": "en",
    "lead_status": "hot",
    "sentiment": "positive",
    "timestamp": "2026-02-15T10:30:00Z"
  }
]
```

## Bijou → AppScript (Webhook on Data Change)

### POST /api/v1/webhooks/sheets
**Request:**
```http
POST /api/v1/webhooks/sheets
X-API-Key: bijou_api_key_123
Content-Type: application/json

{
  "tenant_id": "607690ec-...",
  "action": "update_escalation",
  "data": {
    "escalation_id": "uuid-2",
    "field": "status",
    "value": "resolved"
  }
}
```

**Response (200 OK):**
```json
{
  "status": "processed",
  "updated_at": "2026-02-15T10:31:00Z"
}
```
```

---

#### TASK 3.3: Security Audit
**Owner:** @security  
**Duration:** 30 minutes  
**Depends on:** 3.1, 3.2

**Deliverables:**
1. Document: `docs/sheets/security_audit.md`
2. Review credential storage (Script Properties vs hardcoded)
3. Review API key transmission (HTTPS only)
4. Review webhook authentication (HMAC signature validation)

**Security Checklist:**
```markdown
# Security Audit

## Credential Storage
- [ ] ✅ API keys stored in Script Properties (NOT hardcoded in .gs files)
- [ ] ✅ Service account JSON never exposed in client-side code
- [ ] ✅ Spreadsheet ID not hardcoded (fetched from database)

## Authentication
- [ ] ✅ All API calls use X-API-Key header
- [ ] ✅ HTTPS enforced (no HTTP fallback)
- [ ] ⚠️ MISSING: Webhook HMAC signature validation (RECOMMENDATION)

## Data Exposure
- [ ] ✅ No PII logged to Apps Script Logger
- [ ] ✅ Error messages don't leak sensitive info
- [ ] ✅ Spreadsheet shared only with tenant owner (view-only)

## Recommendations
1. Add HMAC signature to webhook payloads
2. Implement rate limiting on /api/v1/webhooks/sheets
3. Add IP whitelist for AppScript execution (if possible)
```

---

### Phase 3 Exit Criteria
- [ ] AppScript functions deployed and working
- [ ] API contracts documented and approved
- [ ] Security audit passed (or recommendations documented)
- [ ] Manual test: Sync runs successfully

---

## PHASE 4: WEB INTERFACES (45 MINUTES)

### Objective
Build HTML/CSS/JS dashboard interface (optional - for enhanced UX).

### Tasks

#### TASK 4.1: Build Dashboard UI
**Owner:** @fullstack  
**Duration:** 45 minutes

**Deliverables:**
1. File: `appscript/Dashboard.html` (embedded in AppScript)
2. Dashboard with:
   - Stats cards (conversations, escalations, leads)
   - Real-time charts (conversation trends, sentiment distribution)
   - Filters (date range, language, status)
   - Manual sync button

**Implementation:**
```html
<!-- appscript/Dashboard.html -->
<!DOCTYPE html>
<html>
  <head>
    <base target="_top">
    <style>
      body {
        font-family: 'Roboto', sans-serif;
        margin: 20px;
        background: #f5f5f5;
      }
      .header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
      }
      .stats-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-bottom: 20px;
      }
      .stat-card {
        background: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      }
      .stat-value {
        font-size: 32px;
        font-weight: bold;
        color: #667eea;
      }
      .stat-label {
        color: #666;
        margin-top: 8px;
      }
      .sync-button {
        background: #667eea;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 16px;
      }
      .sync-button:hover {
        background: #5568d3;
      }
      .sync-button:disabled {
        background: #ccc;
        cursor: not-allowed;
      }
    </style>
  </head>
  <body>
    <div class="header">
      <h1>Bijou AI Dashboard</h1>
      <p>Real-time WhatsApp customer analytics</p>
    </div>
    
    <div class="stats-container">
      <div class="stat-card">
        <div class="stat-value" id="total-conversations">0</div>
        <div class="stat-label">Total Conversations</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="total-escalations">0</div>
        <div class="stat-label">Total Escalations</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="pending-escalations">0</div>
        <div class="stat-label">Pending Escalations</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="hot-leads">0</div>
        <div class="stat-label">Hot Leads</div>
      </div>
    </div>
    
    <button class="sync-button" onclick="syncNow()">🔄 Sync Now</button>
    <p id="status-message"></p>
    
    <script>
      // Load stats on page load
      google.script.run
        .withSuccessHandler(displayStats)
        .withFailureHandler(handleError)
        .getStats();
      
      function displayStats(stats) {
        document.getElementById('total-conversations').textContent = stats.total_conversations;
        document.getElementById('total-escalations').textContent = stats.total_escalations;
        document.getElementById('pending-escalations').textContent = stats.pending_escalations;
        document.getElementById('hot-leads').textContent = stats.hot_leads;
      }
      
      function syncNow() {
        document.getElementById('status-message').textContent = '🔄 Syncing...';
        document.querySelector('.sync-button').disabled = true;
        
        google.script.run
          .withSuccessHandler(() => {
            document.getElementById('status-message').textContent = '✅ Sync complete!';
            document.querySelector('.sync-button').disabled = false;
            
            // Reload stats
            google.script.run.withSuccessHandler(displayStats).getStats();
          })
          .withFailureHandler((error) => {
            document.getElementById('status-message').textContent = `❌ Error: ${error.message}`;
            document.querySelector('.sync-button').disabled = false;
          })
          .syncAll();
      }
      
      function handleError(error) {
        alert(`Error loading stats: ${error.message}`);
      }
    </script>
  </body>
</html>
```

**Verification:**
1. Deploy dashboard HTML via AppScript Editor
2. Add menu item to show dashboard
3. Test stats loading
4. Test manual sync button

---

### Phase 4 Exit Criteria
- [ ] Dashboard UI renders correctly
- [ ] Stats load from spreadsheet
- [ ] Manual sync button works
- [ ] Mobile-responsive (optional)

---

## PHASE 5: BACKEND INTEGRATION (60 MINUTES)

### Objective
Implement webhook endpoints in Bijou backend for bidirectional sync.

### Tasks

#### TASK 5.1: Webhook Receiver Endpoint
**Owner:** @backend  
**Duration:** 45 minutes

**Deliverables:**
1. File: `src/integrations/google_sheets_webhook.py`
2. FastAPI POST endpoint: `/api/v1/webhooks/sheets`
3. Pydantic models for validation
4. Unit tests

**Implementation:**
```python
# src/integrations/google_sheets_webhook.py

import logging
from typing import Dict, Any, Literal
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from supabase import create_client, Client
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# Initialize Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

class SheetsWebhookPayload(BaseModel):
    """Webhook payload from Google Sheets AppScript."""
    tenant_id: str = Field(..., description="UUID of tenant")
    action: Literal["update_escalation", "update_conversation", "create_note"]
    data: Dict[str, Any] = Field(..., description="Action-specific data")

@router.post("/sheets")
async def sheets_webhook(
    payload: SheetsWebhookPayload,
    x_api_key: str = Header(..., alias="X-API-Key")
) -> Dict[str, Any]:
    """
    Receive updates from Google Sheets AppScript.
    
    Args:
        payload: Webhook payload with action and data
        x_api_key: API key for authentication
        
    Returns:
        {"status": "processed", "updated_at": "..."}
        
    Raises:
        HTTPException 401: Invalid API key
        HTTPException 404: Tenant or resource not found
        HTTPException 422: Invalid payload
    """
    try:
        # Validate API key
        tenant = await validate_api_key(x_api_key, payload.tenant_id)
        if not tenant:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Route to appropriate handler
        if payload.action == "update_escalation":
            result = await update_escalation(payload.tenant_id, payload.data)
        elif payload.action == "update_conversation":
            result = await update_conversation(payload.tenant_id, payload.data)
        elif payload.action == "create_note":
            result = await create_note(payload.tenant_id, payload.data)
        else:
            raise HTTPException(status_code=422, detail=f"Unknown action: {payload.action}")
        
        logger.info(f"✅ Sheets webhook processed: {payload.action} (tenant={payload.tenant_id})")
        
        return {
            "status": "processed",
            "updated_at": result["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Sheets webhook failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def update_escalation(tenant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update escalation status or assignment.
    
    Args:
        tenant_id: UUID of tenant
        data: { "escalation_id": "uuid", "field": "status", "value": "resolved" }
        
    Returns:
        { "updated_at": "2026-02-15T10:31:00Z" }
    """
    escalation_id = data.get("escalation_id")
    field = data.get("field")
    value = data.get("value")
    
    if not escalation_id or not field or not value:
        raise HTTPException(status_code=422, detail="Missing required fields")
    
    # Validate field
    allowed_fields = ["status", "assigned_to", "priority"]
    if field not in allowed_fields:
        raise HTTPException(status_code=422, detail=f"Invalid field: {field}")
    
    # Update database (with tenant_id filter for security)
    response = await supabase.table("escalations") \
        .update({field: value}) \
        .eq("id", escalation_id) \
        .eq("tenant_id", tenant_id) \
        .execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Escalation not found")
    
    return {"updated_at": response.data[0]["updated_at"]}

async def validate_api_key(api_key: str, tenant_id: str) -> Dict[str, Any]:
    """Validate API key belongs to tenant."""
    # Implementation: Check against tenants.api_key column
    response = await supabase.table("tenants") \
        .select("*") \
        .eq("id", tenant_id) \
        .eq("api_key", api_key) \
        .execute()
    
    return response.data[0] if response.data else None

# Add router to main app
# In src/core/bijou.py:
# from src.integrations.google_sheets_webhook import router as sheets_router
# app.include_router(sheets_router)
```

**Unit Tests:**
```python
# tests/unit/test_sheets_webhook.py

import pytest
from fastapi.testclient import TestClient
from src.core.bijou import app

client = TestClient(app)

@pytest.mark.unit
def test_sheets_webhook_valid_payload():
    """Test valid escalation update."""
    payload = {
        "tenant_id": "607690ec-4ff7-4ef4-b98e-bfb00442fe95",
        "action": "update_escalation",
        "data": {
            "escalation_id": "uuid-123",
            "field": "status",
            "value": "resolved"
        }
    }
    
    response = client.post(
        "/api/v1/webhooks/sheets",
        json=payload,
        headers={"X-API-Key": "test_api_key"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "processed"

@pytest.mark.unit
def test_sheets_webhook_invalid_api_key():
    """Test invalid API key returns 401."""
    payload = {
        "tenant_id": "607690ec-...",
        "action": "update_escalation",
        "data": {}
    }
    
    response = client.post(
        "/api/v1/webhooks/sheets",
        json=payload,
        headers={"X-API-Key": "invalid_key"}
    )
    
    assert response.status_code == 401

@pytest.mark.unit
def test_sheets_webhook_tenant_isolation():
    """Test tenant isolation enforced."""
    # Tenant A tries to update Tenant B's escalation
    payload = {
        "tenant_id": "tenant-a-uuid",
        "action": "update_escalation",
        "data": {
            "escalation_id": "escalation-from-tenant-b",
            "field": "status",
            "value": "resolved"
        }
    }
    
    response = client.post(
        "/api/v1/webhooks/sheets",
        json=payload,
        headers={"X-API-Key": "tenant_a_api_key"}
    )
    
    # Should return 404 (not found) not 200 (prevents data leak)
    assert response.status_code == 404
```

**Verification:**
```bash
# Run unit tests
pytest tests/unit/test_sheets_webhook.py -v

# Start local server
python src/core/bijou.py

# Test endpoint manually
curl -X POST http://localhost:8080/api/v1/webhooks/sheets \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test_key" \
  -d '{"tenant_id":"607690ec-...","action":"update_escalation","data":{"escalation_id":"uuid","field":"status","value":"resolved"}}'
```

---

#### TASK 5.2: Environment Variables
**Owner:** @devops  
**Duration:** 15 minutes  
**Parallel:** Yes (with 5.1)

**Deliverables:**
1. Add Google API credentials to Fly.io secrets
2. Update `.env.example` with new variables
3. Document in ENVIRONMENTS.md

**Required Secrets:**
```bash
# Add to Fly.io
C:\Users\w3jbt\.fly\bin\flyctl.exe secrets set \
  GOOGLE_SERVICE_ACCOUNT_JSON="$(cat credentials.json)" \
  GOOGLE_SHEETS_ENABLED=true \
  --app bijou-staging

# Add to .env.example
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GOOGLE_SHEETS_ENABLED=true
```

---

### Phase 5 Exit Criteria
- [ ] Webhook endpoint deployed to staging
- [ ] All unit tests passing
- [ ] Integration test with AppScript
- [ ] Secrets configured in Fly.io

---

## PHASE 6: TESTING & DEPLOYMENT (30 MINUTES)

### Objective
Comprehensive E2E testing and production deployment.

### Tasks

#### TASK 6.1: End-to-End Testing
**Owner:** @qa-engineer (with ALL agents participating)  
**Duration:** 30 minutes

**Test Scenarios:**

**Scenario 1: New Tenant Onboarding**
```bash
# 1. Create new tenant
curl -X POST http://localhost:8080/api/onboarding/signup \
  -d '{"business_name":"Test Business","email":"test@example.com"}'

# Expected: Tenant created, API key returned

# 2. Trigger spreadsheet creation
curl -X POST http://localhost:8080/api/sheets/create \
  -H "X-API-Key: <returned_api_key>" \
  -d '{"tenant_id":"<tenant_id>"}'

# Expected: 
# - Spreadsheet created
# - spreadsheet_id stored in database
# - AppScript deployed
# - Triggers installed

# 3. Verify spreadsheet
# Open returned spreadsheet_url
# Verify all 5 sheets present
# Verify headers formatted
```

**Scenario 2: Data Sync (Bijou → Sheets)**
```bash
# 1. Create test conversation in Bijou
curl -X POST http://localhost:8080/webhook/message \
  -d '{"from":"+60123456789@s.whatsapp.net","body":"Test message"}'

# 2. Wait 5 minutes (AppScript sync trigger)

# 3. Check Conversations sheet
# Expected: New row added with conversation data
```

**Scenario 3: Manual Edit (Sheets → Bijou)**
```bash
# 1. Open Escalations sheet
# 2. Change status from "pending" to "resolved"
# 3. Check Bijou database

# Expected:
# - escalations table updated
# - notification_logs entry created
# - Owner notified via WhatsApp
```

**Automated E2E Test:**
```python
# tests/e2e/test_sheets_integration.py

import pytest
import time

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_sheets_integration():
    """Test complete workflow: Tenant signup → Spreadsheet → Sync → Webhook."""
    
    # 1. Create tenant
    tenant = await create_test_tenant()
    
    # 2. Create spreadsheet
    spreadsheet = await create_dashboard_spreadsheet(tenant["id"], tenant["name"])
    assert "spreadsheet_id" in spreadsheet
    
    # 3. Verify database
    tenant_updated = await get_tenant(tenant["id"])
    assert tenant_updated["settings"]["dashboard_spreadsheet_id"] == spreadsheet["spreadsheet_id"]
    
    # 4. Trigger conversation
    await simulate_whatsapp_message(tenant["id"], "+60123456789@s.whatsapp.net", "Test")
    
    # 5. Wait for AppScript sync (mock timer)
    time.sleep(10)  # In real test, use mock
    
    # 6. Verify sheet updated
    sheet_data = await read_conversations_sheet(spreadsheet["spreadsheet_id"])
    assert len(sheet_data) > 0
    assert sheet_data[0]["message_content"] == "Test"
    
    # 7. Update sheet manually
    await update_sheet_cell(spreadsheet["spreadsheet_id"], "Escalations", "B2", "resolved")
    
    # 8. Verify webhook triggered
    time.sleep(5)
    escalation = await get_escalation_by_chat_jid(tenant["id"], "+60123456789@s.whatsapp.net")
    assert escalation["status"] == "resolved"
    
    # Cleanup
    await delete_test_tenant(tenant["id"])
    await delete_spreadsheet(spreadsheet["spreadsheet_id"])
```

---

#### TASK 6.2: Deployment to Staging
**Owner:** @devops  
**Duration:** 15 minutes  
**Depends on:** All tests passing

**Deployment Steps:**
```powershell
# 1. Commit all changes
git add .
git commit -m "feat: Add Google Sheets dashboard integration"

# 2. Deploy to staging
cd w3j-bijou-enterprise
C:\Users\w3jbt\.fly\bin\flyctl.exe deploy --app bijou-staging --config fly.staging.toml

# 3. Wait for deployment
timeout /t 30

# 4. Run health checks
python tests\e2e_health_check.py --env staging

# 5. Test sheets endpoint
curl https://bijou-staging.fly.dev/api/v1/webhooks/sheets -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test_key" \
  -d '{"tenant_id":"test","action":"update_escalation","data":{}}'

# Expected: 200 OK (or 401 if API key validation working)
```

**Rollback Plan:**
```powershell
# If health checks fail
C:\Users\w3jbt\.fly\bin\flyctl.exe releases rollback <previous_version> --app bijou-staging
```

---

### Phase 6 Exit Criteria
- [ ] All E2E tests passing
- [ ] Deployed to staging successfully
- [ ] Health checks passing
- [ ] Manual smoke test completed
- [ ] Performance benchmarks met (<2s response time)

---

## 🎯 SUCCESS CRITERIA (OVERALL)

### Functional Requirements
- [ ] Spreadsheet auto-created on tenant signup
- [ ] Data syncs Bijou → Sheets every 5 minutes
- [ ] Manual edits sync Sheets → Bijou immediately
- [ ] All 5 sheets present and formatted correctly
- [ ] Dashboard shows real-time stats

### Performance Requirements
- [ ] Spreadsheet creation <5 seconds
- [ ] Data sync <10 seconds for 100 rows
- [ ] Webhook response time <500ms
- [ ] Handles 1000+ rows without lag

### Security Requirements
- [ ] API keys never exposed in logs
- [ ] Service account credentials secured in Fly.io secrets
- [ ] Tenant isolation enforced (no cross-tenant data access)
- [ ] Webhooks validate API key

### Quality Requirements
- [ ] Unit test coverage >80%
- [ ] All integration tests passing
- [ ] E2E test passing
- [ ] Code review approved by @architect
- [ ] Security audit approved by @security

---

## 📊 TIMELINE & PARALLEL EXECUTION

### Sequential (Old Way): 4.5 hours
```
Phase 1 (30m) → Phase 2 (45m) → Phase 3 (60m) → Phase 4 (45m) → Phase 5 (60m) → Phase 6 (30m)
```

### Parallel (Swarm): 2.5 hours
```
Phase 1 (30m)
├── @backend: API inventory (15m)
├── @db-admin: Schema docs (15m) } PARALLEL
└── @google-ws: OAuth check (10m)

Phase 2 (45m)
├── @google-ws: Spreadsheet script (30m)
├── @db-admin: Validation rules (20m) } PARALLEL
└── @qa: Acceptance criteria (15m)

Phase 3 (60m)
├── @fullstack: AppScript (45m)
├── @backend: API contracts (30m) } PARALLEL
└── @security: Audit (30m) ─── DEPENDS ON ── @fullstack, @backend

Phase 4 (45m)
└── @fullstack: Dashboard UI (45m)

Phase 5 (60m)
├── @backend: Webhook endpoint (45m)
└── @devops: Environment setup (15m) } PARALLEL

Phase 6 (30m)
└── @qa + ALL: E2E tests & deployment (30m)
```

**Critical Path:** Phase 1 → Phase 2 → Phase 3 (@fullstack) → Phase 5 (@backend) → Phase 6  
**Total Time on Critical Path:** 2.5 hours

---

## 🚨 RISK MITIGATION PLAN

### Risk 1: Google API Quota Exceeded
**Probability:** Medium  
**Impact:** High (sync stops working)

**Mitigation:**
- Use exponential backoff on API calls
- Cache spreadsheet data locally (Redis)
- Implement rate limiting in AppScript
- Monitor quota usage via Google Cloud Console

**Fallback:**
- Upgrade to paid Google Workspace plan (if needed)
- Reduce sync frequency (5min → 10min)

---

### Risk 2: AppScript Deployment Fails
**Probability:** Low  
**Impact:** High (manual deployment required)

**Mitigation:**
- Test deployment in sandbox first
- Use clasp CLI for automated deployment
- Keep backup of previous AppScript version

**Fallback:**
- Manual deployment via Apps Script Editor
- Provide user with deployment instructions

---

### Risk 3: Database Schema Changes Break Sync
**Probability:** Medium  
**Impact:** Medium (stale data in sheets)

**Mitigation:**
- Version API contracts
- Add schema validation in webhook handler
- Implement graceful degradation

**Fallback:**
- Display error message in Logs sheet
- Notify tenant owner
- Manual data sync via CSV export

---

### Risk 4: Service Account Credentials Compromised
**Probability:** Very Low  
**Impact:** Critical (security breach)

**Mitigation:**
- Store credentials in Fly.io secrets (encrypted)
- Rotate service account keys monthly
- Monitor Google Cloud audit logs
- Implement IP whitelist

**Fallback:**
- Immediate key rotation
- Revoke compromised service account
- Notify all affected tenants

---

## 📝 ROLLBACK PROCEDURES

### Rollback Scenario 1: Deployment Breaks Production
**Trigger:** Health checks fail after deployment

**Steps:**
```powershell
# 1. Identify last working version
C:\Users\w3jbt\.fly\bin\flyctl.exe releases --app bijou-staging

# 2. Rollback
C:\Users\w3jbt\.fly\bin\flyctl.exe releases rollback v<number> --app bijou-staging

# 3. Verify rollback
python tests\e2e_health_check.py --env staging

# 4. Investigate issue
C:\Users\w3jbt\.fly\bin\flyctl.exe logs --app bijou-staging --limit 100
```

---

### Rollback Scenario 2: Database Migration Fails
**Trigger:** Migration script errors out

**Steps:**
```sql
-- 1. Check migration status
SELECT * FROM schema_migrations ORDER BY version DESC LIMIT 5;

-- 2. Rollback migration (if migration has rollback script)
-- Run: database/migrations/010_sheets_integration_ROLLBACK.sql

-- 3. Verify schema restored
DESCRIBE conversations;

-- 4. Re-run deployment with fixed migration
```

---

### Rollback Scenario 3: Spreadsheet Creation Broken
**Trigger:** All spreadsheet creations fail

**Steps:**
1. Disable spreadsheet feature flag: `GOOGLE_SHEETS_ENABLED=false`
2. Deploy with flag disabled
3. Investigate root cause (check Google Cloud logs)
4. Fix issue
5. Re-enable feature: `GOOGLE_SHEETS_ENABLED=true`

---

## 🎓 LESSONS LEARNED (TO BE FILLED POST-IMPLEMENTATION)

### What Went Well
- (To be filled after implementation)

### What Went Wrong
- (To be filled after implementation)

### What to Improve
- (To be filled after implementation)

---

**Document Version:** 1.0.0  
**Created:** 2026-02-15  
**Status:** Ready for Execution  
**Estimated Completion:** 2.5 hours (parallel) / 4.5 hours (sequential)  
**Owner:** @architect  
**Reviewers:** @backend, @google-workspace, @fullstack, @security, @qa-engineer, @devops
