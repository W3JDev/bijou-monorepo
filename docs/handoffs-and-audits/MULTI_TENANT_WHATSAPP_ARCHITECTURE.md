# Multi-Tenant WhatsApp Architecture - Complete Explanation

## 🚨 CRITICAL FINDINGS

### Current Status: **SINGLE-TENANT MODE**
- ✅ Database schema supports multi-tenancy
- ✅ Code supports multi-tenancy
- ❌ **ONLY 1 WhatsApp bridge deployed** (shared by all tenants)
- ❌ **device_sessions table is EMPTY** (no tenant-to-device mapping)
- ❌ **Dashboard shows THE SAME QR code for all tenants**

---

## 🏗️ The Three Multi-Tenant Architecture Options

### **Option 1: Shared Bridge + Device Isolation** (CURRENT INTENDED DESIGN)
**How it works:**
- 1 bridge handles multiple devices (up to 5)
- Each tenant gets their own `device_id` on the same bridge
- Tenants scan different QR codes for different devices
- Bridge routes messages based on `device_id` → `tenant_id` mapping

**Database Flow:**
```
1. Tenant signs up → Creates record in `tenants` table
2. System creates device on bridge → Stores in `device_sessions` table:
   - device_id (from bridge)
   - tenant_id (link to tenant)
   - qr_code_url (unique per tenant)
   - whatsapp_jid (after scanning)

3. Message arrives → Bridge sends webhook with device_id
4. Bijou looks up: device_id → tenant_id → process message
```

**Pros:**
- Cost-effective (1 bridge for all tenants)
- Easy to manage
- Up to 5 tenants max

**Cons:**
- Limited to 5 tenants (GOWA bridge limit)
- If bridge crashes, ALL tenants affected
- No true isolation (all on same server)

**Cost:** ~$5/month (1 Fly.io app)

---

### **Option 2: Dedicated Bridge Per Tenant** (TRUE ISOLATION)
**How it works:**
- Each tenant gets their own bridge app
- Each tenant has isolated WhatsApp connection
- No shared resources

**Deployment:**
```bash
# For Tenant A
fly apps create bijou-bridge-tenant-a
fly deploy --app bijou-bridge-tenant-a --config fly.tenant.toml

# For Tenant B  
fly apps create bijou-bridge-tenant-b
fly deploy --app bijou-bridge-tenant-b --config fly.tenant.toml
```

**Database:**
```sql
tenants table:
- id: tenant_id
- bridge_url: https://bijou-bridge-tenant-a.fly.dev
- bridge_device_id: unique per tenant
- whatsapp_jid: their connected WhatsApp
```

**Pros:**
- True isolation (1 crash doesn't affect others)
- Unlimited tenants
- Better security
- Can customize per tenant

**Cons:**
- Expensive ($5-10/month per tenant)
- Complex management (100 tenants = 100 apps)
- DevOps overhead

**Cost:** $5/tenant/month (if 100 tenants = $500/month)

---

### **Option 3: Multi-Bridge Pools** (HYBRID - RECOMMENDED FOR SCALE)
**How it works:**
- Deploy bridges in pools of 5 tenants each
- Load balance across pools
- Auto-scale as needed

**Architecture:**
```
Pool 1: bijou-bridge-pool-1.fly.dev (5 tenants)
Pool 2: bijou-bridge-pool-2.fly.dev (5 tenants)
Pool 3: bijou-bridge-pool-3.fly.dev (5 tenants)
...
Pool N: bijou-bridge-pool-N.fly.dev (5 tenants)
```

**Assignment Logic:**
```python
def assign_tenant_to_bridge(tenant_id):
    # Find bridge with < 5 devices
    bridges = get_bridges_with_capacity()
    if not bridges:
        # Create new bridge pool
        new_bridge = create_bridge_pool(pool_num=next_pool_number)
        return new_bridge
    return bridges[0]
```

**Pros:**
- Cost-effective ($5 per 5 tenants = $1/tenant)
- Scalable (auto-create new pools)
- Fault-tolerant (1 pool failure affects max 5 tenants)

**Cons:**
- More complex than Option 1
- Still requires pool management

**Cost:** $1/tenant/month (if 100 tenants = $100/month for 20 pools)

---

## 🔍 Current Implementation Status

### What EXISTS in Code:
```python
# src/saas/session_manager.py
class DeviceSessionManager:
    async def create_session(self, tenant_id: UUID, device_id: str, ...)
    async def get_session_by_device_id(self, device_id: str)
    async def get_tenant_id_by_device_id(self, device_id: str)
```

### What's MISSING:
1. ❌ **No device creation during tenant onboarding**
2. ❌ **No QR code generation per tenant**
3. ❌ **No device_id assignment logic**
4. ❌ **Dashboard shows shared QR code (wrong!)**

---

## 📊 Database Schema (Already Correct!)

### `tenants` table
```sql
id              UUID (PRIMARY KEY)
name            TEXT
business_name   TEXT
whatsapp_jid    TEXT  -- Their WhatsApp number after connecting
whatsapp_number TEXT  -- For lookup
device_id       TEXT  -- ⚠️ SHOULD be in device_sessions, not here
status          TEXT  -- active, suspended, etc.
```

### `device_sessions` table (CURRENTLY EMPTY!)
```sql
id              UUID (PRIMARY KEY)
tenant_id       UUID (FOREIGN KEY → tenants.id)
device_id       TEXT (UNIQUE) -- From GOWA bridge
whatsapp_jid    TEXT           -- After scanning QR
qr_code_url     TEXT           -- Unique QR per tenant
status          TEXT           -- pending, active, disconnected
connected_at    TIMESTAMP
last_seen       TIMESTAMP
```

### `conversations` / `messages` tables
```sql
tenant_id       UUID (FOREIGN KEY) -- Ensures data isolation
chat_jid        TEXT               -- Customer WhatsApp
...
```

---

## 🔧 How to FIX Current Implementation

### Step 1: Choose Architecture
**Recommendation:** Start with **Option 1** (Shared Bridge), migrate to **Option 3** (Pools) when > 5 tenants.

### Step 2: Implement Device Creation

**File:** `src/saas/onboarding_api.py`

```python
async def complete_onboarding(tenant_id: UUID):
    # 1. Create tenant record (already done)
    tenant = await create_tenant(...)
    
    # 2. Create device on bridge (NEW!)
    bridge_url = os.getenv("BRIDGE_URL")
    device_response = requests.post(
        f"{bridge_url}/devices",
        auth=(os.getenv("BRIDGE_USER"), os.getenv("BRIDGE_PASSWORD")),
        json={
            "display_name": tenant.business_name,
            "external_id": str(tenant_id)  # Map device to tenant
        }
    )
    device_data = device_response.json()
    device_id = device_data["results"]["device_id"]
    
    # 3. Store in device_sessions (NEW!)
    session_manager = DeviceSessionManager(supabase)
    await session_manager.create_session(
        tenant_id=tenant_id,
        device_id=device_id,
        status="pending"  # Waiting for QR scan
    )
    
    # 4. Generate QR code (NEW!)
    qr_response = requests.get(
        f"{bridge_url}/devices/{device_id}/qr",
        auth=(os.getenv("BRIDGE_USER"), os.getenv("BRIDGE_PASSWORD"))
    )
    qr_data = qr_response.json()
    
    # 5. Update session with QR (NEW!)
    await session_manager.update_session(
        device_id=device_id,
        qr_code_url=qr_data["results"]["qr_url"],
        qr_expires_at=qr_data["results"]["expires_at"]
    )
    
    return {
        "tenant_id": tenant_id,
        "device_id": device_id,
        "qr_code_url": qr_data["results"]["qr_url"]
    }
```

### Step 3: Update Dashboard to Show Tenant-Specific QR

**File:** `appscript/production/Dashboard.gs`

```javascript
function getConnectionStatus() {
  const tenantId = getTenantIdFromSession(); // Get from user session
  
  // Call Bijou API to get THIS tenant's device status
  const response = UrlFetchApp.fetch(
    `${BIJOU_API_URL}/api/tenant/${tenantId}/device/status`,
    {
      headers: { "Authorization": `Bearer ${getApiKey()}` }
    }
  );
  
  const data = JSON.parse(response.getContentText());
  
  return {
    connected: data.status === "active",
    qrCode: data.qr_code_url,  // Tenant-specific QR!
    deviceId: data.device_id,
    expiresAt: data.qr_expires_at
  };
}
```

### Step 4: Webhook Routing by Device ID

**File:** `src/core/bijou.py` (already implemented!)

```python
@app.post("/webhook/message")
async def webhook_message(request: Request):
    data = await request.json()
    device_id = data.get("device_id")  # From GOWA webhook
    
    # Look up tenant by device_id
    session_mgr = DeviceSessionManager(supabase)
    tenant_id = await session_mgr.get_tenant_id_by_device_id(device_id)
    
    # Process message for THIS tenant only
    await process_message(tenant_id, message_data)
```

---

## 🎯 Multi-Device vs Multi-Tenant Confusion

### "Up to 5 devices" - What It Means:

**GOWA Bridge Perspective:**
- 1 bridge can manage up to 5 **separate WhatsApp accounts**
- Each account is a "device" in GOWA terminology
- Example:
  ```
  Device 1: Tenant A's WhatsApp (601234567890)
  Device 2: Tenant B's WhatsApp (601987654321)
  Device 3: Tenant C's WhatsApp (603112233445)
  Device 4: Tenant D's WhatsApp (604556677889)
  Device 5: Tenant E's WhatsApp (605998877665)
  ```

**WhatsApp Multi-Device (Companion Mode):**
- 1 WhatsApp account on up to 4 linked devices
- Example: Phone + Web + Desktop + Tablet
- This is DIFFERENT from GOWA's "5 devices"
- Each GOWA device can ALSO use WhatsApp's companion mode

**Total Capacity:**
- 5 GOWA devices × 4 WhatsApp companions = 20 connected devices
- But still only 5 **separate businesses/tenants**

---

## 🔐 Data Isolation & Security

### How Isolation Works:

**1. Database Level (RLS):**
```sql
-- All queries automatically filter by tenant_id
CREATE POLICY tenant_isolation ON messages
  FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

**2. Application Level:**
```python
# Webhook arrives with device_id
device_id = webhook_data["device_id"]

# Lookup tenant
tenant_id = await get_tenant_by_device(device_id)

# ALL subsequent queries use this tenant_id
messages = await get_messages(tenant_id=tenant_id, chat_jid=customer)
kb = await get_knowledge_base(tenant_id=tenant_id)
settings = await get_settings(tenant_id=tenant_id)
```

**3. Bridge Level:**
- Each device has isolated message queue
- GOWA automatically routes by device_id
- Messages for Device 1 never go to Device 2

---

## 📞 Handover Feature in Multi-Tenant

### How Handover Works:

**Scenario:** Customer escalates to human

**Current Flow:**
```python
# 1. ERS detects escalation needed
escalation = await create_escalation(
    tenant_id=tenant_id,
    chat_jid=customer_jid,
    reason="billing_inquiry"
)

# 2. Notify tenant owner
owner_whatsapp = await get_tenant_owner_whatsapp(tenant_id)
await send_notification(
    to=owner_whatsapp,
    device_id=tenant_device_id,  # ⚠️ Uses TENANT's device!
    message=f"Escalation from {customer_name}: {reason}"
)

# 3. Owner replies directly in WhatsApp
# Message goes through bridge → routed by device_id → correct tenant
```

**Key Point:** Each tenant has their own `device_id`, so notifications go to the correct owner's WhatsApp!

---

## 🎨 Dashboard iframe Issue

### Current Problem:
```html
<iframe src="https://bijou-bridge-staging-v2.fly.dev/"></iframe>
```
- Shows ALL devices on the bridge
- Tenant A can see Tenant B's devices! ❌
- No authentication separation

### Solution 1: Tenant-Specific Device View
```html
<iframe src="https://bijou-bridge-staging-v2.fly.dev/devices/{TENANT_DEVICE_ID}"></iframe>
```
- Show ONLY this tenant's device
- Requires GOWA to support device-specific views (check documentation)

### Solution 2: Proxy Through Bijou API
```html
<!-- Don't embed bridge directly -->
<!-- Instead, show Bijou's device management UI -->
<div id="deviceManager">
  <img id="qrCode" src="/api/tenant/{{TENANT_ID}}/qr">
  <div id="status">{{device_status}}</div>
  <button onclick="reconnect()">Reconnect</button>
</div>

<script>
// Call Bijou API, NOT bridge directly
async function getDeviceStatus() {
  const response = await fetch('/api/tenant/{{TENANT_ID}}/device/status');
  const data = await response.json();
  updateUI(data);
}
</script>
```

### Solution 3: Remove iframe, Use API Integration (RECOMMENDED)
- Don't embed bridge UI at all
- Build custom UI that calls Bijou API
- Bijou API calls bridge on behalf of tenant
- Complete isolation guaranteed

---

## 📈 Scaling Plan

### Phase 1: 1-5 Tenants (Current)
- Use 1 shared bridge
- Implement device_id mapping
- Cost: $5/month

### Phase 2: 6-25 Tenants
- Deploy 5 bridge pools
- Auto-assign tenants to pools
- Cost: $25/month (5 pools × $5)

### Phase 3: 26-100 Tenants
- Deploy 20 bridge pools
- Implement auto-scaling
- Add load balancer
- Cost: $100/month (20 pools × $5)

### Phase 4: 100+ Tenants (Enterprise)
- Offer dedicated bridges for premium tenants
- Shared pools for standard tenants
- Tiered pricing:
  - Free: Shared pool (1-5 tenants)
  - Pro: Priority pool (better SLA)
  - Enterprise: Dedicated bridge

---

## 🚀 Immediate Action Items

1. ✅ **Understand current architecture** (this document)
2. ⏳ **Implement device creation during onboarding**
3. ⏳ **Update Dashboard to show tenant-specific QR**
4. ⏳ **Test with 2 tenants to verify isolation**
5. ⏳ **Document tenant onboarding flow**
6. ⏳ **Remove bridge iframe or restrict to device view**

---

## ❓ FAQ

**Q: Can we use 1 bridge for all tenants forever?**
A: No. GOWA limit is 5 devices = max 5 tenants per bridge.

**Q: What happens if we exceed 5 tenants?**
A: Need to deploy another bridge (Pool 2) and assign new tenants there.

**Q: Is data actually isolated right now?**
A: YES - database RLS is working. But device routing is NOT (no device_sessions).

**Q: Can tenants see each other's WhatsApp messages?**
A: NO - RLS prevents this at database level. But iframe shows all devices (fix needed).

**Q: How do we test multi-tenancy?**
A: Create 2 tenants, assign different device_ids, verify messages route correctly.

---

**Author:** OpenCode Analysis
**Date:** 2026-02-17
**Status:** Architecture Documentation
