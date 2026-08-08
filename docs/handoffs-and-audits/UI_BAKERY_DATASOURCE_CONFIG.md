# UI Bakery Datasource Configuration - Bijou AI Backend

## 📋 Ready to Copy-Paste Configuration

---

## SETTINGS

### Data Source name
```
Bijou AI Backend
```

**Description (if available):**
```
Bijou AI WhatsApp Enterprise API - Multi-tenant SaaS platform
```

---

## CONNECTION SETTINGS

### ✅ Enable environments
**Toggle:** ON (Checked)

### Base URL
```
https://bijou-staging.fly.dev
```

**Alternative (Production - when available):**
```
https://bijou-production.fly.dev
```

**Alternative (Local Testing):**
```
http://localhost:8080
```

---

### Headers (Add these rows)

| Header Name | Header Value |
|-------------|--------------|
| `Content-Type` | `application/json` |
| `X-Tenant-ID` | `00000000-0000-0000-0000-000000000001` |

**Optional - If using authentication:**

| Header Name | Header Value |
|-------------|--------------|
| `Authorization` | `Bearer REDACTED_SERVICE_ROLE_KEY_ROTATE_IN_SUPABASE` |

**Copy-Paste Format for UI:**
```
Header 1:
  Name: Content-Type
  Value: application/json

Header 2:
  Name: X-Tenant-ID
  Value: 00000000-0000-0000-0000-000000000001
```

---

### Query Params (Default - Usually empty)

**Leave empty** or add these if needed globally:

| Parameter Name | Parameter Value |
|----------------|-----------------|
| `tenant_id` | `00000000-0000-0000-0000-000000000001` |

**Copy-Paste Format:**
```
Query Param 1:
  Name: tenant_id
  Value: 00000000-0000-0000-0000-000000000001
```

---

## AUTHENTICATION SETTINGS

### Authentication Type
**Select:** `None`

**Alternatives if you want authentication:**

#### Option 1: Bearer Token
```
Type: Bearer Token
Token: REDACTED_SERVICE_ROLE_KEY_ROTATE_IN_SUPABASE
```

#### Option 2: API Key (in header)
```
Type: API Key
Header Name: Authorization
Header Value: Bearer {token}
```

---

### ☑️ Allow anonymous users
**Toggle:** ON (Checked)

**Explanation:** Allows dashboard users to make API calls without individual authentication

---

## 🧪 TEST CONFIGURATION

After setting up, test with these endpoints:

### Test 1: Health Check
```
Method: GET
Path: /health
Expected Response: {"status": "healthy", "service": "bijou-ai-enterprise"}
```

### Test 2: Tenant Device Status
```
Method: GET
Path: /api/tenant/00000000-0000-0000-0000-000000000001/device/status
Expected Response: {
  "tenant_id": "...",
  "device_id": "...",
  "status": "active",
  "bridge_status": {...}
}
```

### Test 3: Dashboard Stats
```
Method: GET
Path: /api/dashboard/stats
Query Params: tenant_id=00000000-0000-0000-0000-000000000001
Expected Response: {
  "total_conversations": 150,
  "active_conversations": 12,
  ...
}
```

---

## 📝 COMPLETE CONFIGURATION SUMMARY

**Copy this entire block if UI supports JSON import:**

```json
{
  "name": "Bijou AI Backend",
  "type": "http",
  "baseUrl": "https://bijou-staging.fly.dev",
  "headers": [
    {
      "name": "Content-Type",
      "value": "application/json"
    },
    {
      "name": "X-Tenant-ID",
      "value": "00000000-0000-0000-0000-000000000001"
    }
  ],
  "queryParams": [],
  "authentication": {
    "type": "none",
    "allowAnonymous": true
  },
  "environments": {
    "staging": {
      "baseUrl": "https://bijou-staging.fly.dev"
    },
    "production": {
      "baseUrl": "https://bijou-production.fly.dev"
    },
    "local": {
      "baseUrl": "http://localhost:8080"
    }
  }
}
```

---

## 🎯 ENVIRONMENT-SPECIFIC CONFIGURATIONS

### Staging Environment
```
Base URL: https://bijou-staging.fly.dev
Tenant ID: 00000000-0000-0000-0000-000000000001
Status: Active, tested
```

### Production Environment (Future)
```
Base URL: https://bijou-production.fly.dev
Tenant ID: (Use production tenant ID)
Status: Not yet deployed
```

### Local Development
```
Base URL: http://localhost:8080
Tenant ID: 00000000-0000-0000-0000-000000000001
Status: For local testing only
```

---

## 🔐 TENANT IDs FOR DIFFERENT USE CASES

### Default Testing Tenant
```
00000000-0000-0000-0000-000000000001
Name: W3J Consulting
WhatsApp: Connected (601160600963@s.whatsapp.net)
Device ID: 0d1bc10a-1775-497f-a159-55ebb959d221
```

### Alternative Testing Tenants

**W3J LLC:**
```
607690ec-4ff7-4ef4-b98e-bfb00442fe95
WhatsApp: 60174106981@s.whatsapp.net
```

**Jewel W3J Admin:**
```
87dcc712-1eb3-4772-a682-d74f67d13f92
Email: jewel@w3j.my
WhatsApp: +601121113249@s.whatsapp.net
```

**D&D Real Estate:**
```
2012067f-5a48-43d9-8e39-af8864b74ecc
Email: shawny.loh.dndream@gmail.com
```

---

## 📊 COMMON API ENDPOINTS TO USE

Once datasource is configured, use these paths:

### Device & Connection Status
```
GET /api/tenant/{tenant_id}/device/status
GET /api/dashboard/whatsapp/status?tenant_id={id}
GET /bridge/health
```

### Dashboard Data
```
GET /api/dashboard/stats?tenant_id={id}
GET /api/dashboard/conversations?tenant_id={id}
GET /api/dashboard/conversation/{customer_jid}?tenant_id={id}
```

### Messaging
```
POST /api/dashboard/send-message
POST /api/dashboard/takeover
POST /api/dashboard/return-to-ai/{customer_jid}
```

### Knowledge Base
```
GET /api/knowledge/list?tenant_id={id}
POST /api/knowledge/upload
DELETE /api/knowledge/{document_id}
```

---

## ⚙️ STEP-BY-STEP FILLING GUIDE

### Step 1: Basic Settings
1. Click "Add Data Source" or "Create Data Source"
2. Select "HTTP API" or "REST API"
3. Enter name: `Bijou AI Backend`
4. Click "Enable environments" checkbox

### Step 2: Connection Settings
1. In "Base URL" field, paste:
   ```
   https://bijou-staging.fly.dev
   ```

2. Click "+ Add Header" button
   - First header:
     - Name: `Content-Type`
     - Value: `application/json`
   
   - Click "+ Add Header" again
   - Second header:
     - Name: `X-Tenant-ID`
     - Value: `00000000-0000-0000-0000-000000000001`

3. Leave "Query Params" empty (or add `tenant_id` if UI requires it)

### Step 3: Authentication
1. Select "None" from dropdown
2. Check "Allow anonymous users" checkbox

### Step 4: Test Connection
1. Click "Test Connection" or "Test" button
2. If successful, you should see:
   ```
   ✅ Connection successful
   Status: 200 OK
   ```

### Step 5: Save
1. Click "Save" or "Create" button
2. Datasource is now ready to use!

---

## 🚨 TROUBLESHOOTING

### If connection test fails:

**Error: CORS or Network Error**
- Check Base URL has no trailing slash
- Verify URL is `https://bijou-staging.fly.dev` (no `/` at end)

**Error: 404 Not Found**
- Test with `/health` endpoint first
- Full URL should be: `https://bijou-staging.fly.dev/health`

**Error: 401 Unauthorized**
- Remove Authorization header if present
- Set Authentication to "None"
- Enable "Allow anonymous users"

**Error: 500 Internal Server Error**
- Check tenant_id is valid UUID format
- Try default tenant: `00000000-0000-0000-0000-000000000001`

---

## 🎨 VISUAL REFERENCE (Text Format)

```
┌─────────────────────────────────────────────────┐
│ SETTINGS                                        │
├─────────────────────────────────────────────────┤
│ Data Source name                                │
│ ┌─────────────────────────────────────────────┐ │
│ │ Bijou AI Backend                            │ │
│ └─────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────┤
│ CONNECTION SETTINGS                             │
├─────────────────────────────────────────────────┤
│ ☑ Enable environments                          │
│                                                 │
│ Base URL                                        │
│ ┌─────────────────────────────────────────────┐ │
│ │ https://bijou-staging.fly.dev               │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ Headers                                         │
│ ┌─────────────────────┬─────────────────────┐   │
│ │ Content-Type        │ application/json    │   │
│ ├─────────────────────┼─────────────────────┤   │
│ │ X-Tenant-ID         │ 00000000-0000-...   │   │
│ └─────────────────────┴─────────────────────┘   │
│                                                 │
│ Query Params                                    │
│ ┌─────────────────────┬─────────────────────┐   │
│ │ (empty)             │ (empty)             │   │
│ └─────────────────────┴─────────────────────┘   │
├─────────────────────────────────────────────────┤
│ AUTHENTICATION SETTINGS                         │
├─────────────────────────────────────────────────┤
│ Type: ▼ None                                    │
│ ☑ Allow anonymous users                        │
├─────────────────────────────────────────────────┤
│          [Test Connection]  [Save]              │
└─────────────────────────────────────────────────┘
```

---

## 📞 SUPPORT INFORMATION

**Backend Status:** https://bijou-staging.fly.dev/status  
**Health Check:** https://bijou-staging.fly.dev/health  
**API Docs:** https://bijou-staging.fly.dev/docs  
**Bridge Health:** https://bijou-staging.fly.dev/bridge/health

**Quick Test CURL:**
```bash
curl https://bijou-staging.fly.dev/health

# Expected:
# {"status":"healthy","service":"bijou-ai-enterprise","version":"2.2.0"}
```

---

**Configuration Complete!** ✅  
You're ready to build your dashboard with Bijou AI Backend datasource.

**Last Updated:** 2026-02-17  
**Version:** 1.0
