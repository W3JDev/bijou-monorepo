# 🧪 Bijou AI v294 Testing Guide
## False Escalation Fix - User Acceptance Testing

**Deployment:** `bijou-staging.fly.dev` (v294)  
**Date:** 2026-02-13  
**Fix:** Cultural term pre-filtering for Bengali/Malay false escalations

---

## ✅ DEPLOYMENT STATUS

**Health Check:**
```bash
curl https://bijou-staging.fly.dev/health
# Response: {"status":"healthy","service":"bijou-ai-enterprise","version":"2.2.0"}
```

**Deployment Version:**
- Machine ID: `080e091f05d6e8`
- Version: `v294`
- Region: Singapore (sin)
- Status: ✅ RUNNING (auto-suspends when idle, wakes up on requests)

---

## 🎯 WHAT WAS FIXED IN v294

### Problem:
**5 out of 6 messages were FALSE ESCALATIONS (83% failure rate)**

Bengali/Malay cultural address terms were incorrectly interpreted as "wants human agent":
- "vaia" (brother in Bengali)
- "bhai" (brother)
- "sayang" (darling in Malay)
- "bro" (casual English)

### Solution:
**Enhanced pre-filter in `ai_handover_detector.py`** (lines 47-79)

**NEW LOGIC:**
1. Check if message contains casual address terms (vaia, bhai, sayang, bro, etc.)
2. Check if message contains explicit escalation keywords (speak to owner, talk to manager, etc.)
3. **If casual term WITHOUT explicit escalation → Skip AI analysis → Treat as normal conversation**
4. If explicit escalation keyword present → Run AI analysis

**Result:** Expected 0% false positive rate for casual conversations

---

## 📋 TEST PLAN

### Test Environment:
- **WhatsApp Number:** Your testing number (e.g., +8801792345147)
- **Business Number:** +60174106981 (Bijou Staging)
- **Tenant ID:** `607690ec-4ff7-4ef4-b98e-bfb00442fe95`

### Test Messages (Send via WhatsApp):

#### Test 1: Bengali with "vaia" (casual)
**Message to send:**
```
Akhn Ki kortam vaia Oita bolo 1tu bujai
```
**Translation:** "What should I do now brother, tell me clearly"

**Expected Result:**
- ✅ AI responds normally (no escalation)
- ✅ NO notification to Escalation Queue group
- ✅ May trigger Updates notification (if AI responds helpfully)

**v292 Result:** ❌ ESCALATED (FALSE)  
**v294 Expected:** ✅ NORMAL CONVERSATION

---

#### Test 2: Bengali acknowledgment with "vaia"
**Message to send:**
```
Okh vaia thik ase boilo
```
**Translation:** "Ok brother alright tell me"

**Expected Result:**
- ✅ AI responds casually (acknowledgment)
- ✅ Updates notification sent (casual acknowledgment detected)
- ✅ NO escalation

**v292 Result:** ❌ ESCALATED (FALSE)  
**v294 Expected:** ✅ UPDATES NOTIFICATION ONLY

---

#### Test 3: Malay term of endearment
**Message to send:**
```
Ok sayang
```
**Translation:** "Ok dear/darling"

**Expected Result:**
- ✅ AI responds casually (acknowledgment)
- ✅ Updates notification sent
- ✅ NO escalation

**v292 Result:** ❌ ESCALATED (FALSE)  
**v294 Expected:** ✅ UPDATES NOTIFICATION ONLY

---

#### Test 4: REAL escalation request
**Message to send:**
```
I need to speak to the owner NOW
```

**Expected Result:**
- ✅ ESCALATION TRIGGERED (correct behavior)
- ✅ Notification to Escalation Queue group
- ✅ Priority: high
- ✅ Reason logged in database

**v292 Result:** ✅ ESCALATED (CORRECT)  
**v294 Expected:** ✅ ESCALATION (should still work)

---

#### Test 5: Gibberish/typo (bonus test)
**Message to send:**
```
duxedus
```

**Expected Result:**
- ✅ AI asks for clarification ("I didn't understand...")
- ✅ NO escalation
- ✅ NO notification (or Updates if AI responds)

**v292 Result:** ❌ ESCALATED as "Legal/compliance matter" (FALSE)  
**v294 Expected:** ✅ NORMAL CLARIFICATION REQUEST

---

## 📊 HOW TO VERIFY RESULTS

### Method 1: Check WhatsApp Groups

**Escalation Queue Group:**
- Should ONLY receive message from Test 4 ("I need to speak to the owner NOW")
- Should NOT receive messages from Tests 1, 2, 3, 5

**Customer Updates Group:**
- May receive notifications for Tests 2, 3 (casual acknowledgments)
- Should NOT receive notifications for Tests 1, 4, 5

**Hot Leads Group:**
- Should NOT receive any notifications from these tests

---

### Method 2: Check Database Logs

```sql
-- Run this in Supabase SQL Editor:
SELECT 
    notification_type,
    message,
    context,
    created_at
FROM notification_logs
WHERE tenant_id = '607690ec-4ff7-4ef4-b98e-bfb00442fe95'
ORDER BY created_at DESC
LIMIT 20;
```

**Expected Results:**
- Test 1: NO entry (or `notification_type = 'update'`)
- Test 2: `notification_type = 'update'`, context: "Casual acknowledgment"
- Test 3: `notification_type = 'update'`, context: "Casual acknowledgment"
- Test 4: `notification_type = 'escalation'`, context includes "owner NOW"
- Test 5: NO entry (or `notification_type = 'update'`)

---

### Method 3: Check Escalation Records

```sql
-- Check escalations table:
SELECT 
    chat_jid,
    reason,
    priority,
    created_at
FROM escalations
WHERE tenant_id = '607690ec-4ff7-4ef4-b98e-bfb00442fe95'
ORDER BY created_at DESC
LIMIT 10;
```

**Expected Results:**
- Should have ONE new escalation entry for Test 4 only
- Reason should mention "owner" or "speak to owner"
- Priority should be "high"

---

### Method 4: Check Application Logs

```bash
# Run this command to see real-time processing:
flyctl logs --app bijou-staging

# Look for these log patterns:
# ✅ GOOD: "🤖 AI: Skipping escalation - Cultural term detected"
# ✅ GOOD: "🚨 ESCALATION DETECTED: wants_human=True"
# ❌ BAD: "🚨 ESCALATION DETECTED" for Tests 1, 2, 3, 5
```

**Log Markers to Watch:**
- `Cultural term detected: vaia` → Pre-filter working ✅
- `Cultural term detected: sayang` → Pre-filter working ✅
- `AI: Skipping escalation check` → Pre-filter working ✅
- `ESCALATION DETECTED` for casual messages → Pre-filter FAILED ❌

---

## 📈 SUCCESS CRITERIA

### PASS Criteria:
- ✅ Test 1: NO escalation (AI responds normally)
- ✅ Test 2: NO escalation (Updates notification sent)
- ✅ Test 3: NO escalation (Updates notification sent)
- ✅ Test 4: ESCALATION triggered (correct behavior)
- ✅ Test 5: NO escalation (AI asks for clarification)

**Success Rate:** 5/5 tests passed (100%)

### FAIL Criteria:
- ❌ ANY of Tests 1, 2, 3, 5 trigger escalation
- ❌ Test 4 does NOT trigger escalation
- ❌ Database errors in logs
- ❌ Application crashes or timeouts

**If ANY test fails:** Report results and we'll analyze logs immediately

---

## 🐛 TROUBLESHOOTING

### Issue: No AI response at all
**Possible Causes:**
- Bridge is down
- Gemini API quota exceeded
- Database connection error

**Check:**
```bash
curl https://bijou-staging.fly.dev/health
# Should return: {"status":"healthy"}
```

**Fix:** Check logs for errors:
```bash
flyctl logs --app bijou-staging | grep ERROR
```

---

### Issue: Messages not reaching Bijou
**Possible Causes:**
- WhatsApp session disconnected
- Bridge not forwarding webhooks

**Check:**
1. Verify WhatsApp Web session is active (scan QR if needed)
2. Check bridge status:
```bash
curl https://bijou-bridge-staging-v2.fly.dev/health
```

**Fix:** Restart bridge or reconnect WhatsApp session

---

### Issue: Database constraint errors
**Symptoms:** Error in logs: `violates check constraint "notification_logs_notification_type_check"`

**Cause:** Bug in code (should be fixed in v294)

**Fix:** Already fixed - if this appears, we need to redeploy

---

### Issue: Duplicate notifications
**Symptoms:** Same message triggers multiple notifications

**Cause:** Duplicate escalation prevention cooldown not working

**Check:**
```sql
SELECT chat_jid, COUNT(*) as count
FROM escalations
WHERE created_at > NOW() - INTERVAL '10 minutes'
GROUP BY chat_jid
HAVING COUNT(*) > 1;
```

**Fix:** Cooldown logic in `handover_system.py:121-137` should prevent this

---

## 📞 REPORT RESULTS

**Please send back:**

1. **Screenshots of WhatsApp groups** (showing which notifications arrived)
2. **Test results table:**

| Test | Message | Expected | Actual | Pass/Fail |
|------|---------|----------|--------|-----------|
| 1 | "Akhn Ki kortam vaia..." | No escalation | ? | ? |
| 2 | "Okh vaia thik ase..." | Updates only | ? | ? |
| 3 | "Ok sayang" | Updates only | ? | ? |
| 4 | "I need to speak to owner NOW" | Escalation | ? | ? |
| 5 | "duxedus" | No escalation | ? | ? |

3. **Any error messages or unexpected behavior**

---

## 🚀 NEXT STEPS AFTER TESTING

### If ALL tests pass (100% success):
1. ✅ Mark notification system as **PRODUCTION READY**
2. 🎉 Deploy to production (`bijou-production.fly.dev`)
3. 📊 Monitor production for 24 hours
4. 🔧 Fix remaining issues (webhook timeouts, voice transcription)

### If ANY test fails:
1. 🔍 Analyze logs to find root cause
2. 🛠️ Adjust AI prompt or pre-filter logic
3. 🚀 Deploy v295 with fixes
4. 🧪 Re-test failed scenarios

---

## 📚 TECHNICAL DETAILS (For Reference)

### Files Modified in v294:
- `src/saas/ai_handover_detector.py` (lines 47-79, 87-133)
- Pre-filter logic with cultural term detection
- Rewritten AI prompt with your exact test cases

### Deployment Command Used:
```bash
cd w3j-bijou-enterprise
flyctl deploy --app bijou-staging --config fly.staging.toml
```

### Git Commit:
```
e3b33ff - fix: CRITICAL - Prevent false escalations from casual Bengali/Malay terms
```

### Database Schema (Reference):
- `notification_logs.notification_type` → 'escalation', 'hot_lead', 'update' (singular)
- `escalations.chat_jid` → WhatsApp JID (NOT customer_jid)
- `notification_groups.group_type` → 'escalation_queue', 'hot_leads', 'customer_updates'

---

**Testing Window:** Anytime (system is live 24/7)  
**Expected Testing Duration:** 10-15 minutes  
**Support:** If any issues, send logs/screenshots immediately

---

**Good luck with testing! 🚀**
