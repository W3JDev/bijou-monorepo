# Bijou AI Dashboard Configuration - Complete Answer Sheet

**Date:** 2026-02-17  
**Purpose:** Configuration values for testing WhatsApp connection dashboard

---

## 🎯 Your Question: Dashboard Configuration

You asked for configuration values for this dashboard:
```
1. Update Backend URL
2. Auth Token
3. Backend API Requirements
```

---

## ✅ COMPLETE ANSWERS

### 1. Backend URL

```typescript
const BACKEND_URL = 'https://bijou-staging.fly.dev';
```

**Alternative (Local Testing):**
```typescript
const BACKEND_URL = 'http://localhost:8080';
```

---

### 2. Auth Token

**Current Status:** Bijou uses **Supabase JWT authentication**, not simple token auth.

**For Quick Testing (No Auth - Recommended):**
```typescript
const AUTH_TOKEN = '';  // Leave empty
```

**For Full Access (Service Role Key):**
```typescript
const AUTH_TOKEN = 'REDACTED_SERVICE_ROLE_KEY_ROTATE_IN_SUPABASE';
```

⚠️ **Note:** Service key has FULL database access - use only for testing, not production!

---

### 3. Active Tenant IDs (From Database)

You have **10 active tenants** in the system. Here are the main ones:

#### ✅ **Best for Testing - W3J Consulting** (Has device_id!)
```typescript
const TENANT_ID = '00000000-0000-0000-0000-000000000001';
```
- **Name:** W3J Consulting
- **WhatsApp:** 601160600963@s.whatsapp.net
- **Device ID:** `0d1bc10a-1775-497f-a159-55ebb959d221` ✅
- **Status:** Connected & Active
- **Created:** Default tenant

#### ✅ **Alternative - W3J LLC**
```typescript
const TENANT_ID = '607690ec-4ff7-4ef4-b98e-bfb00442fe95';
```
- **Name:** W3J LLC
- **WhatsApp:** 60174106981@s.whatsapp.net
- **Device ID:** `0d1bc10a-1775-497f-a159-55ebb959d221` ✅
- **Status:** Connected & Active

#### Other Active Tenants (No device_id yet)

**Jewel W3J Admin:**
```
ID: 87dcc712-1eb3-4772-a682-d74f67d13f92
WhatsApp: +601121113249@s.whatsapp.net
Email: jewel@w3j.my
```

**D&D Real Estate:**
```
ID: 2012067f-5a48-43d9-8e39-af8864b74ecc
Email: shawny.loh.dndream@gmail.com
WhatsApp: Not connected
```

**MN Jewel:**
```
ID: 23976770-7e79-450d-b342-96928a985796
Email: mnj3wl@gmail.com
WhatsApp: Not connected
```

**Mamak Restaurant:**
```
ID: 200ab38a-8fd1-4540-a54b-297b255329f9
WhatsApp: +60123456789@s.whatsapp.net
```

---

## 🔧 Missing Endpoint Issue

**Problem:** The dashboard expects `/api/dashboard/data` which doesn't exist yet.

**Solution Options:**

### Option A: Use Existing Endpoint (Quick Fix)

Instead of calling `/api/dashboard/data`, modify your code to use:

```typescript
// In your dashboard code, replace:
// const response = await fetch(`${BACKEND_URL}/api/dashboard/data`);

// With this:
const TENANT_ID = '00000000-0000-0000-0000-000000000001';

const response = await fetch(
  `${BACKEND_URL}/api/tenant/${TENANT_ID}/device/status`
);

const data = await response.json();

// Map the response to expected format:
const dashboardData = {
  tenant: {
    id: data.tenant_id,
    name: "W3J Consulting",  // You'd fetch this separately
    email: "contact@w3j.my"
  },
  device_session: {
    device_id: data.device_id,
    bridge_url: "https://bijou-bridge-staging-v2.fly.dev",
    status: data.status,
    qr_code: data.qr_code_url,
    last_connected: data.connected_at,
    tenant_id: data.tenant_id
  }
};
```

### Option B: Create the Missing Endpoint (I can do this!)

Want me to create `GET /api/dashboard/data` that matches your frontend's expected format?

---

## 📊 Current System Status

### Device Sessions Table Status
- **Status:** ❌ **EMPTY** (critical issue we're fixing)
- **Expected:** Each tenant should have a row with device_id
- **Actual:** Only `tenants` table has device_id (wrong architecture)

### Tenants with WhatsApp Connected
```
✅ W3J Consulting         (device_id: 0d1bc10a-1775-497f-a159-55ebb959d221)
✅ W3J LLC                (device_id: 0d1bc10a-1775-497f-a159-55ebb959d221)
✅ Jewel W3J Admin        (whatsapp_jid: +601121113249@s.whatsapp.net)
✅ Mamak Restaurant       (whatsapp_jid: +60123456789@s.whatsapp.net)
✅ Paradise Properties KL (whatsapp_jid: +60123456789@s.whatsapp.net)
✅ Prime Properties       (whatsapp_jid: +60198765432@s.whatsapp.net)
```

**Issue:** Most tenants share the same device_id (`0d1bc10a-1775-497f-a159-55ebb959d221`)
- This is the single-tenant architecture we're migrating away from
- New signups will get unique device IDs (from our Phase 1 implementation)

---

## 🚀 Complete Configuration Code

**Copy-paste ready for your dashboard:**

```typescript
// app/app.tsx or config.ts

// ===== CONFIGURATION =====
const BACKEND_URL = 'https://bijou-staging.fly.dev';
const TENANT_ID = '00000000-0000-0000-0000-000000000001';  // W3J Consulting (best for testing)
const AUTH_TOKEN = '';  // Empty for now (or use service key above)

// ===== API CALL EXAMPLE =====
async function fetchDeviceStatus() {
  try {
    const response = await fetch(
      `${BACKEND_URL}/api/tenant/${TENANT_ID}/device/status`,
      {
        headers: {
          'Content-Type': 'application/json',
          // Uncomment if using auth token:
          // 'Authorization': `Bearer ${AUTH_TOKEN}`,
        }
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    
    return {
      tenant: {
        id: data.tenant_id,
        name: "W3J Consulting",
        email: "contact@w3j.my"
      },
      device_session: {
        device_id: data.device_id,
        bridge_url: "https://bijou-bridge-staging-v2.fly.dev",
        status: data.status,  // 'pending', 'active', 'disconnected'
        qr_code: data.qr_code_url,
        last_connected: data.connected_at,
        tenant_id: data.tenant_id,
        is_connected: data.bridge_status?.is_connected || false,
        is_logged_in: data.bridge_status?.is_logged_in || false
      }
    };
  } catch (error) {
    console.error('Failed to fetch device status:', error);
    return null;
  }
}

// ===== USAGE =====
const dashboardData = await fetchDeviceStatus();

if (dashboardData) {
  console.log('Device ID:', dashboardData.device_session.device_id);
  console.log('Status:', dashboardData.device_session.status);
  console.log('Connected:', dashboardData.device_session.is_connected);
  console.log('QR Code:', dashboardData.device_session.qr_code);
}
```

---

## 🔐 Database Credentials (For Reference)

**Supabase URL:**
```
https://lrwzlujomukzjykafmic.supabase.co
```

**Supabase Anon Key (Public):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxyd3psdWpvbXVremp5a2FmbWljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkwNzA2ODMsImV4cCI6MjA4NDY0NjY4M30.ZJSvmh0Oa_51rfr0TrTSjS4OdszrUCe5Fmsnfk9X-6U
```

**Supabase Service Role Key (Full Access):**
```
REDACTED_SERVICE_ROLE_KEY_ROTATE_IN_SUPABASE
```

---

## 🎨 Expected API Response Format

When you call `GET /api/tenant/{tenant_id}/device/status`, you'll get:

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "device_id": "0d1bc10a-1775-497f-a159-55ebb959d221",
  "status": "active",
  "qr_code_url": "https://bijou-bridge-staging-v2.fly.dev/devices/0d1bc10a-1775-497f-a159-55ebb959d221/qr",
  "qr_expires_at": null,
  "whatsapp_jid": "601160600963@s.whatsapp.net",
  "connected_at": "2026-02-07T08:00:00Z",
  "last_seen": "2026-02-17T10:30:00Z",
  "bridge_status": {
    "is_connected": true,
    "is_logged_in": true,
    "display_name": "Bijou"
  }
}
```

---

## 🛠️ Troubleshooting

### If you get 404 Not Found
- Check the tenant_id is correct (copy from list above)
- Try using W3J Consulting tenant: `00000000-0000-0000-0000-000000000001`

### If you get "No device configured"
- This tenant doesn't have a device session yet
- Only new tenants (after our Phase 1 implementation) will have device sessions
- Use one of the tenants with device_id (W3J Consulting or W3J LLC)

### If you get CORS errors
- Bijou staging should allow CORS from all origins
- Check browser console for exact error
- May need to add your domain to allowed origins

### If QR code doesn't load
- The QR code URL is a proxy through the bridge
- Try accessing it directly: `https://bijou-bridge-staging-v2.fly.dev/devices/{device_id}/qr`
- Bridge may require basic auth: `bijou:Ik7vOKhkH99a2deLtbW8eJGOudNDJVbn`

---

## 📝 Summary - Copy This!

**Minimum Configuration:**
```typescript
const BACKEND_URL = 'https://bijou-staging.fly.dev';
const TENANT_ID = '00000000-0000-0000-0000-000000000001';
const AUTH_TOKEN = '';
```

**API Endpoint to Use:**
```
GET https://bijou-staging.fly.dev/api/tenant/00000000-0000-0000-0000-000000000001/device/status
```

**Expected Response Fields:**
- `device_id` - Unique device identifier
- `status` - 'pending', 'active', or 'disconnected'
- `qr_code_url` - URL to QR code image
- `bridge_status.is_connected` - Boolean connection status
- `whatsapp_jid` - Connected WhatsApp number

---

## ✅ All Your Questions Answered

### Q1: "Which folder has API documentation?"
**A:** `w3j-bijou-enterprise/API_ENDPOINTS_REFERENCE.md` (just created!)

### Q2: "Give me active tenant"
**A:** Best one is `00000000-0000-0000-0000-000000000001` (W3J Consulting)

### Q3: "Give me existing tenant"
**A:** You have 10 active tenants (see list above)

### Q4: "What should I input in dashboard config?"
**A:** See "Complete Configuration Code" section above

### Q5: "Backend URL?"
**A:** `https://bijou-staging.fly.dev`

### Q6: "Auth Token?"
**A:** Empty string for now (Bijou uses Supabase JWT, not simple tokens)

### Q7: "Backend API Requirements?"
**A:** Endpoint exists at `/api/tenant/{tenant_id}/device/status` (not `/api/dashboard/data`)

---

**Need Help?**
- Test the endpoint: `curl https://bijou-staging.fly.dev/api/tenant/00000000-0000-0000-0000-000000000001/device/status`
- View interactive docs: `https://bijou-staging.fly.dev/docs`
- Want me to create the missing `/api/dashboard/data` endpoint? Just ask!

**Last Updated:** 2026-02-17  
**Status:** Ready for testing ✅
