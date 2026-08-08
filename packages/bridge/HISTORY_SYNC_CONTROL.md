# 🔧 WhatsApp Bridge: History Sync Control

**Created:** 2025-01-26  
**Status:** ACTIVE - History sync currently DISABLED  
**Priority:** CRITICAL  

---

## 📋 QUICK REFERENCE

### Current Status
```
✅ History sync is DISABLED by default
✅ Only LIVE messages are processed
✅ No old chat history pulled on connection
✅ Storage and AI costs protected
```

---

## 🎛️ CONTROL VIA ENVIRONMENT VARIABLE

### Disable History Sync (RECOMMENDED - Default)
```bash
ENABLE_HISTORY_SYNC=false
```

**What happens:**
- ✅ Bridge connects normally
- ✅ Live messages processed in real-time
- ❌ Old chat history NOT synced
- ✅ Storage stays minimal
- ✅ No AI processing costs for old messages

### Enable History Sync (USE WITH CAUTION)
```bash
ENABLE_HISTORY_SYNC=true
```

**What happens:**
- ⚠️ ALL chat history synced on connection
- ⚠️ Could pull months/years of old messages
- ⚠️ Storage grows rapidly
- ⚠️ Potential AI processing costs
- ⚠️ No incremental sync (full sync every time)

---

## 🚀 DEPLOYMENT CONFIGURATIONS

### Staging Bridge
**File:** `fly.staging.toml`
```toml
[env]
  ENVIRONMENT = "staging"
  WEBHOOK_URL = "https://bijou-staging.fly.dev/webhook/whatsapp"
  ENABLE_HISTORY_SYNC = "false"  # ✅ DISABLED
```

**Status:** ✅ History sync DISABLED

### Production Bridge
**File:** `fly.toml`
```toml
[env]
  BIJOU_WEBHOOK_URL = "https://bijou-ai-enterprise-w3j.fly.dev/webhook/message"
  ENABLE_HISTORY_SYNC = "false"  # ✅ DISABLED
```

**Status:** ✅ History sync DISABLED

---

## 📊 BEHAVIOR COMPARISON

| Scenario | History Sync OFF | History Sync ON |
|----------|------------------|-----------------|
| **Connection** | Connects normally | Connects + starts sync |
| **Old messages** | ❌ Not pulled | ✅ All pulled |
| **Live messages** | ✅ Processed | ✅ Processed |
| **Storage usage** | ~10-50 MB | ~500 MB - 5 GB+ |
| **AI processing** | Only new messages | All messages! |
| **Connection time** | Fast (~5 sec) | Slow (1-5 min) |

---

## 🔍 HOW TO VERIFY

### Check Logs (History Sync DISABLED)
```bash
fly logs -a whatsapp-bridge-staging-w3j
```

**Expected output:**
```
✅ History sync DISABLED - skipping 150 conversations 
   (set ENABLE_HISTORY_SYNC=true to enable)
```

### Check Logs (History Sync ENABLED)
```bash
fly logs -a whatsapp-bridge-staging-w3j
```

**Expected output:**
```
⚠️ History sync ENABLED via env var - processing 150 conversations
   Received history sync event with 150 conversations
   Stored message: [2025-12-15 11:20:23] ...
   (Many old messages being synced)
```

---

## ⚙️ HOW TO CHANGE SETTING

### For Staging Bridge

**Via Fly.io config file:**
```bash
# Edit fly.staging.toml
[env]
  ENABLE_HISTORY_SYNC = "true"  # or "false"

# Redeploy
fly deploy --config fly.staging.toml -a whatsapp-bridge-staging-w3j
```

**Via Fly.io secrets (runtime):**
```bash
# Disable
fly secrets set ENABLE_HISTORY_SYNC=false -a whatsapp-bridge-staging-w3j

# Enable
fly secrets set ENABLE_HISTORY_SYNC=true -a whatsapp-bridge-staging-w3j

# Restart to apply
fly apps restart whatsapp-bridge-staging-w3j
```

### For Production Bridge

**Via Fly.io config file:**
```bash
# Edit fly.toml
[env]
  ENABLE_HISTORY_SYNC = "true"  # or "false"

# Redeploy
fly deploy -a whatsapp-bridge-w3j
```

**Via Fly.io secrets (runtime):**
```bash
# Disable
fly secrets set ENABLE_HISTORY_SYNC=false -a whatsapp-bridge-w3j

# Enable (NOT RECOMMENDED without proper sync management)
fly secrets set ENABLE_HISTORY_SYNC=true -a whatsapp-bridge-w3j

# Restart to apply
fly apps restart whatsapp-bridge-w3j
```

---

## 🚨 WARNINGS

### ⚠️ Before Enabling History Sync

**DO NOT enable history sync until:**
1. Smart sync system is implemented (see `SYNC_FIX_PROPOSAL.md`)
2. Incremental sync is working
3. Message retention policy is active
4. Storage monitoring is in place
5. Deduplication is implemented

**Why?**
- Could fill entire 1GB volume in minutes
- Could trigger thousands of AI API calls
- Could cost hundreds of dollars in API fees
- No way to stop it once started (except restart)

### 💰 Cost Impact Example

**Scenario:** Connect with WhatsApp account that has 10,000 old messages

| Setting | Messages Synced | Storage Used | Potential AI Cost |
|---------|----------------|--------------|-------------------|
| **OFF** | 0 old messages | ~10 MB | $0 |
| **ON** | 10,000 messages | ~500 MB | $50-$500 |

---

## 🔧 CODE IMPLEMENTATION

### Location
**File:** `whatsapp-bridge/main.go`  
**Lines:** ~1065-1074

### Code Snippet
```go
case *events.HistorySync:
    // TEMPORARY: History sync disabled to prevent storage/cost issues
    // TODO: Implement smart sync with incremental updates and retention policy
    enableHistorySync := os.Getenv("ENABLE_HISTORY_SYNC")
    if enableHistorySync == "true" {
        logger.Infof("History sync ENABLED via env var - processing %d conversations", len(v.Data.Conversations))
        handleHistorySync(client, messageStore, v, logger)
    } else {
        logger.Infof("History sync DISABLED - skipping %d conversations (set ENABLE_HISTORY_SYNC=true to enable)", len(v.Data.Conversations))
    }
```

---

## 📝 TODO: PROPER IMPLEMENTATION

See `SYNC_FIX_PROPOSAL.md` for the complete professional solution.

**What needs to be implemented:**
1. ✅ Database schema for sync tracking
2. ✅ First-time sync: 7 days only
3. ✅ Incremental sync on reconnection
4. ✅ Message deduplication
5. ✅ Retention policy (30 days)
6. ✅ Auto cleanup scheduler
7. ✅ Storage monitoring
8. ✅ Configurable limits

**Timeline:**
- **Now:** History sync disabled (DONE ✅)
- **Phase 1:** Implement smart sync (2-3 hours)
- **Phase 2:** Test on staging (1 hour)
- **Phase 3:** Deploy to production (30 min)

---

## 🎯 RECOMMENDATIONS

### For Staging
```bash
✅ Keep ENABLE_HISTORY_SYNC=false
✅ Test with live messages only
✅ Monitor storage growth
✅ Implement proper sync before enabling
```

### For Production
```bash
✅ Keep ENABLE_HISTORY_SYNC=false
✅ Never enable without smart sync
✅ Monitor all metrics
✅ Have rollback plan ready
```

### For Development
```bash
✅ Keep ENABLE_HISTORY_SYNC=false
⚠️ Can enable for testing (use test account with minimal history)
✅ Delete database after testing
```

---

## 📊 MONITORING

### Check Current Setting
```bash
# Staging
fly ssh console -a whatsapp-bridge-staging-w3j -C "env | grep ENABLE_HISTORY_SYNC"

# Production
fly ssh console -a whatsapp-bridge-w3j -C "env | grep ENABLE_HISTORY_SYNC"
```

### Check Storage Usage
```bash
# Staging
fly ssh console -a whatsapp-bridge-staging-w3j -C "du -sh /app/store"

# Production
fly ssh console -a whatsapp-bridge-w3j -C "du -sh /data/store"
```

### Check Message Count
```bash
# Staging
fly ssh console -a whatsapp-bridge-staging-w3j -C "sqlite3 /app/store/messages.db 'SELECT COUNT(*) FROM messages'"

# Production
fly ssh console -a whatsapp-bridge-w3j -C "sqlite3 /data/store/messages.db 'SELECT COUNT(*) FROM messages'"
```

---

## 🆘 TROUBLESHOOTING

### Issue: Storage filling up despite history sync disabled
**Cause:** Live messages accumulating  
**Solution:** Implement retention policy or manual cleanup

### Issue: Old messages still appearing
**Cause:** History sync was enabled before, messages already stored  
**Solution:** Clear database or implement cleanup

### Issue: Want to clear all stored messages
**Solution:**
```bash
fly ssh console -a whatsapp-bridge-staging-w3j
rm /app/store/messages.db
exit
fly apps restart whatsapp-bridge-staging-w3j
```

---

## 📞 SUPPORT

**Questions?**
- See `SYNC_FIX_PROPOSAL.md` for complete solution
- Check logs for sync behavior
- Monitor storage metrics
- Contact dev team if issues

---

**Document Status:** ✅ ACTIVE  
**Last Updated:** 2025-01-26  
**Review Date:** After smart sync implementation  

---

**REMEMBER:** 
🚫 **DO NOT enable history sync without proper implementation**  
✅ **Current disabled state is SAFE and RECOMMENDED**  
📝 **Follow SYNC_FIX_PROPOSAL.md for proper solution**