# Bijou Tenant Identity Persistence - Verification Results

**Date:** 2025-01-30
**Test Script:** `ops/verify_core_logic.py`
**Status:** ✅ **ALL TESTS PASSED**

---

## 🎯 Test Results

### [1] Tenant Router - Identity Lookup

#### WhatsApp Identifier Test
- **Input:** `+601160600963`
- **Expected:** `06e152aa-8090-419f-be07-7cb1f9cc409d`
- **Result:** ✅ **SUCCESS** - Found Jewel via WhatsApp!
- **Tenant ID:** `06e152aa-8090-419f-be07-7cb1f9cc409d`

#### Telegram Identifier Test
- **Input:** `mebijou`
- **Expected:** `06e152aa-8090-419f-be07-7cb1f9cc409d`
- **Result:** ✅ **SUCCESS** - Found Jewel via Telegram!
- **Tenant ID:** `06e152aa-8090-419f-be07-7cb1f9cc409d`

### [2] Client Config Load (Vibe Check)

- **Business Name:** W3J Live
- **Manglish Level:** heavy
- **Result:** ✅ **SUCCESS** - Loaded 'Heavy Manglish' setting!

---

## 🔧 Changes Implemented

### 1. TenantRouter Enhancements (`w3j-bijou-enterprise/src/saas/tenant_router.py`)

#### Auto-initialization of Supabase Client
```python
# Checks for env variables:
# - SUPABASE_URL or NEXT_PUBLIC_SUPABASE_URL
# - SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_ROLE_KEY
```

#### New Method: `get_tenant_id_by_identifier(identifier: str)`
- **Purpose:** Resolve tenant ID from WhatsApp phone or Telegram username
- **Logic:**
  - If identifier starts with `+` → WhatsApp lookup (`whatsapp_number` column)
  - Otherwise → Telegram lookup (`telegram_username` column)
- **Returns:** Tenant UUID or `None`

#### New Method: `get_client_config(tenant_id: str)`
- **Purpose:** Fetch client configuration from `client_configs` table
- **Features:**
  - Extracts `business_name` from `system_prompt_vars` JSON
  - Returns full config dict with manglish_level, tone, enabled_tools, etc.
- **Returns:** Config dict or `None`

### 2. Database Schema (Already Applied)

✅ Migration 005: Added `telegram_username` to `tenants` table
✅ Migration 006: Created `client_configs` table
✅ Migration 007: Created `messages` table
✅ Migration 008: Added UNIQUE constraint to `whatsapp_number`
✅ Migration 009: RLS policies and indexes

### 3. Seed Data (Already Inserted)

✅ Tenant "Jewel" created:
- WhatsApp: `+601160600963`
- Telegram: `mebijou`
- Tenant ID: `06e152aa-8090-419f-be07-7cb1f9cc409d`

✅ Client Config created:
- Business: W3J Live
- Type: gaming
- Manglish: heavy
- Tone: hype

---

## 🚀 Next Steps

### Immediate Actions

1. **Restart the Application**
   ```bash
   .\ops\stop-all.bat
   .\ops\start-all.bat
   ```

2. **Live Test**
   - Send "Hi" on **Telegram** (@mebijou)
   - Send "Hi" on **WhatsApp** (+601160600963)
   - **Expected:** Bijou should reply with "Eh Boss!" or your Hype vibe

### Integration Tasks

#### A. Wire Identity Resolution into Message Flow
**Location:** `w3j-bijou-enterprise/src/core/bijou.py` → `process_message()`

**Current Flow:**
```python
# Likely using phone number only for tenant lookup
```

**Required Change:**
```python
from src.saas.tenant_router import TenantRouter

# In process_message():
router = TenantRouter()

# For WhatsApp messages
if platform == "whatsapp":
    tenant_id = await router.get_tenant_id_by_identifier(f"+{phone}")

# For Telegram messages
if platform == "telegram":
    tenant_id = await router.get_tenant_id_by_identifier(username)

# Load tenant config
config = await router.get_client_config(tenant_id)
```

#### B. Update Conversation History Method
**Location:** `w3j-bijou-enterprise/src/core/bijou.py` → `_get_conversation_history()`

**Current Implementation:**
- Queries `conversations` table
- Format: `message_content`, `ai_response`, `timestamp`

**Question to Resolve:**
- Is `conversations` table deprecated in favor of `messages` table?
- Or do they serve different purposes?

**If messages table should be used:**
```python
# Update query to use messages table instead
resp = (
    self.db_conn.table("messages")
    .select("role, content, timestamp")
    .eq("chat_jid", chat_jid)
    .order("timestamp", desc=False)  # Chronological order
    .limit(limit)
    .execute()
)
```

#### C. Ensure Message Persistence
**Verify these locations save to correct table:**
- `_save_conversation()` method
- `_record_sent_message()` method

Should save to `messages` table with:
- `tenant_id`
- `chat_jid`
- `role` (user/assistant)
- `content`
- `timestamp`

---

## 🔍 Outstanding Questions

1. **Table Strategy:** Should we migrate from `conversations` → `messages`, or keep both?
   - `conversations`: Legacy format (message_content + ai_response per row)
   - `messages`: New format (one message per row, role-based)

2. **Multi-Platform JID Handling:**
   - WhatsApp: `phone@s.whatsapp.net`
   - Telegram: `username` or `user_id`
   - Do we need a unified `chat_jid` format?

3. **Tenant Context Isolation:**
   - Where is tenant_id currently set in the request context?
   - Is it passed through all layers (webhook → router → Bijou → tools)?

---

## 🛡️ Security & Performance Notes

### Already Addressed:
✅ RLS enabled on `client_configs` and `messages`
✅ Indexes added for foreign keys
✅ Unique constraints on identifiers

### Still Needed (From Advisor):
⚠️ Tighten RLS policies (replace `USING (true)` with tenant isolation)
⚠️ Add RLS policies for `api_keys` table
⚠️ Review auth RLS initplan warnings
⚠️ Set immutable search_path on custom functions

---

## 📊 Test Coverage

| Feature | Status | Notes |
|---------|--------|-------|
| WhatsApp Tenant Lookup | ✅ Pass | Via phone number |
| Telegram Tenant Lookup | ✅ Pass | Via username |
| Client Config Load | ✅ Pass | Manglish level verified |
| Conversation History | ⚠️ Pending | Need to verify table usage |
| Message Persistence | ⚠️ Pending | Need to verify write path |
| Live E2E Test | ⚠️ Pending | Requires app restart |

---

## 🎉 Summary

**The core identity resolution system is working perfectly!**

The verification proves that:
1. ✅ Tenant lookup works for both WhatsApp and Telegram
2. ✅ Client configuration loads correctly
3. ✅ Database connection is functional
4. ✅ The "Amnesia Bug" fix is ready for integration

**Next:** Wire these methods into the message processing flow and test live!

---

**Generated by:** Bijou Verification System
**Run Again:** `python ops/verify_core_logic.py`
