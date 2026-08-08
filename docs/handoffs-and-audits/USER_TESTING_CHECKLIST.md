# Bijou AI - User Testing Checklist

**Date:** 2026-02-14  
**System:** Bijou AI Dashboard - W3J Tenant  
**Status:** ✅ READY FOR TESTING  
**Database Fixes:** 8/8 Successful  
**Verification Grade:** B+ (88%)

---

## Pre-Testing Verification

Before starting manual tests, verify the following:

- [ ] Read `EXECUTIVE_SUMMARY.md` for overview of fixes applied
- [ ] Read `DB_FIX_RESULTS.md` for database change details  
- [ ] Read `VERIFICATION_AUDIT_RESULTS.md` for automated test results
- [ ] Confirm database backup exists: `tenants_backup_20260214` table
- [ ] Confirm W3J tenant ID: `607690ec-4ff7-4ef4-b98e-bfb00442fe95`

**Expected State:**
- W3J tenant has `whatsapp_number`: `+60174106981` ✅
- W3J tenant has `whatsapp_jid`: `60174106981@s.whatsapp.net` ✅
- W3J tenant has `whatsapp_connected`: `true` ✅
- W3J tenant has `device_id`: `0d1bc10a-1775-497f-a159-55ebb959d221` ✅

---

## Dashboard Access

**Dashboard URL:** https://v0-cliste-website-navigation-sigma-ruby.vercel.app/dashboard?tenant=w3j  
**Login Email:** w3jdev@gmail.com  
**Login Password:** *(Use your existing credentials)*  
**Tenant ID:** 607690ec-4ff7-4ef4-b98e-bfb00442fe95  
**Business Phone:** +60174106981

---

## Test 1: WhatsApp Connection Page

**Navigate to:**  
`https://v0-cliste-website-navigation-sigma-ruby.vercel.app/dashboard/whatsapp?tenant=w3j`

### Expected Results

Check the following elements on the WhatsApp connection page:

- [ ] **Connection Status Badge:** Shows "Connected" (green) or similar positive indicator
- [ ] **Phone Number Display:** Shows "+60174106981" (NOT "Unknown Number")
- [ ] **Device Status:** Shows active/connected state
- [ ] **Last Activity:** Shows recent timestamp (today's date)
- [ ] **QR Code:** Either hidden (already connected) or shows "Already connected" message
- [ ] **No Error Messages:** No "disconnected" warnings or error banners

### If Status Shows "Disconnected"

**This may be a cache issue. Try the following:**

```bash
# Restart Bijou Staging app
C:\Users\w3jbt\.fly\bin\flyctl.exe restart --app bijou-staging

# Wait 30 seconds for app to fully restart
# Then refresh dashboard in browser (Ctrl+F5 for hard refresh)
```

### Test Result

**Status:** ⬜ PASS / ⬜ FAIL  
**Notes:**
```
[Enter any issues, screenshots, or observations here]
```

---

## Test 2: Conversations List

**Navigate to:**  
`https://v0-cliste-website-navigation-sigma-ruby.vercel.app/dashboard?tenant=w3j`

### Expected Results

- [ ] **Conversations Load:** Page loads without errors (not blank/404)
- [ ] **Conversation Count:** Shows at least 2 conversations (from verification tests)
- [ ] **Customer Names:** Shows phone numbers or names (NOT "Unknown")
- [ ] **Chat JIDs:** Shows valid WhatsApp JIDs (e.g., `173053107535911@lid`)
- [ ] **Status Indicators:** Shows "AI handled" or conversation status
- [ ] **Timestamps:** Shows recent activity (today's date: 2026-02-14)

### Test Result

**Status:** ⬜ PASS / ⬜ FAIL  
**Notes:**
```
Number of conversations shown: _______
Any missing/incorrect data: _______
```

---

## Test 3: Analytics Page

**Navigate to:**  
`https://v0-cliste-website-navigation-sigma-ruby.vercel.app/dashboard/analytics?tenant=w3j`

### Expected Results

- [ ] **Active Conversations:** Shows 2 (or current count, NOT 0)
- [ ] **Messages Today:** Shows 22 (or current count, NOT 0)
- [ ] **AI Handled:** Shows percentage or count (NOT 0%)
- [ ] **Response Time:** Shows "< 1s" or actual time (NOT "N/A")
- [ ] **Charts/Graphs:** Render correctly (if present)
- [ ] **No Zero Metrics:** At least some metrics should have real data

### Test Result

**Status:** ⬜ PASS / ⬜ FAIL  
**Notes:**
```
Active conversations: _______
Messages today: _______
Any metrics showing 0: _______
```

---

## Test 4: Escalations Page

**Navigate to:**  
`https://v0-cliste-website-navigation-sigma-ruby.vercel.app/dashboard/escalations?tenant=w3j`

### Expected Results

- [ ] **Page Loads:** No errors or 404
- [ ] **Empty State:** Shows "No escalations" or empty list (expected - 0 escalations currently)
- [ ] **No Error Messages:** No API errors or broken elements
- [ ] **UI Functional:** Filters/search work (if present)

### Test Result

**Status:** ⬜ PASS / ⬜ FAIL  
**Notes:**
```
[Note if page is functional even if empty]
```

---

## Test 5: Agents Page

**Navigate to:**  
`https://v0-cliste-website-navigation-sigma-ruby.vercel.app/dashboard/agents?tenant=w3j`

### Expected Results

- [ ] **Page Loads:** No errors
- [ ] **Agents Listed:** Shows AI agents (ASI, CAE, ERS, etc.)
- [ ] **Agent Status:** Shows active/enabled state
- [ ] **No Configuration Errors:** No missing settings warnings

### Test Result

**Status:** ⬜ PASS / ⬜ FAIL  
**Notes:**
```
Number of agents shown: _______
Any configuration issues: _______
```

---

## Test 6: Send Test WhatsApp Message

**Action:** Send a test message to the W3J business WhatsApp number.

**Test Message:**
```
Hi Bijou, this is a test message sent on 2026-02-14 at [current time]. 
Please respond to confirm you're receiving messages correctly.
```

**Send to:** +60174106981 (W3J business WhatsApp number)

### Expected Results

- [ ] **Message Sent:** Successfully delivered via WhatsApp
- [ ] **AI Response:** Receive automated reply within 10 seconds
- [ ] **Response Quality:** Reply is contextual and relevant (not error message)
- [ ] **Dashboard Update:** New conversation appears in dashboard conversations list
- [ ] **Message Count:** Dashboard stats increment (messages_today +1)

### Test Result

**Status:** ⬜ PASS / ⬜ FAIL  
**AI Response Received:**
```
[Paste the AI response here]
```

**Response Time:** _______ seconds  
**Notes:**
```
[Any issues with message delivery or AI response]
```

---

## Test 7: Browser Console Check

**Action:** Open browser developer console (F12) while on dashboard.

### Expected Results

- [ ] **No JavaScript Errors:** Console should be mostly clean (warnings OK, no red errors)
- [ ] **API Calls Succeed:** Network tab shows 200 OK responses for API calls
- [ ] **No 404 Errors:** No missing resources or broken endpoints
- [ ] **No CORS Errors:** API requests complete successfully

### Errors Found

**Console Errors:**
```
[Paste any error messages here]
```

### Test Result

**Status:** ⬜ PASS / ⬜ FAIL

---

## Test 8: API Verification (Optional - Technical Users)

### 8a. WhatsApp Status Check

**Command:**
```bash
curl -s -H "X-Tenant-ID: 607690ec-4ff7-4ef4-b98e-bfb00442fe95" \
  https://bijou-staging.fly.dev/api/dashboard/whatsapp/status
```

**Expected:** `{"connected": true, "status": "connected"}`  
**Known Issue:** May show `{"connected": false}` due to cache (see EXECUTIVE_SUMMARY.md)

- [ ] API returns 200 OK (even if status shows "disconnected")

---

### 8b. Conversations API

**Command:**
```bash
curl -s -H "X-Tenant-ID: 607690ec-4ff7-4ef4-b98e-bfb00442fe95" \
  https://bijou-staging.fly.dev/api/dashboard/conversations
```

**Expected:** Array of conversations with proper structure

- [ ] Returns non-empty array with at least 2 conversations

---

### 8c. Dashboard Stats API

**Command:**
```bash
curl -s -H "X-Tenant-ID: 607690ec-4ff7-4ef4-b98e-bfb00442fe95" \
  https://bijou-staging.fly.dev/api/dashboard/stats
```

**Expected:** Real metrics (NOT all zeros)

- [ ] Returns `active_conversations > 0` and `messages_today > 0`

---

## Issues Encountered

If you encounter any issues during testing, document them here:

### Issue 1
**Test:** ____________________  
**Expected:** ____________________  
**Actual:** ____________________  
**Severity:** ⬜ Critical / ⬜ High / ⬜ Medium / ⬜ Low  
**Screenshot/Error:**
```
[Paste error message or attach screenshot]
```

### Issue 2
**Test:** ____________________  
**Expected:** ____________________  
**Actual:** ____________________  
**Severity:** ⬜ Critical / ⬜ High / ⬜ Medium / ⬜ Low  
**Screenshot/Error:**
```
[Paste error message or attach screenshot]
```

### Issue 3
**Test:** ____________________  
**Expected:** ____________________  
**Actual:** ____________________  
**Severity:** ⬜ Critical / ⬜ High / ⬜ Medium / ⬜ Low  
**Screenshot/Error:**
```
[Paste error message or attach screenshot]
```

---

## Final Sign-Off

**Testing Completed By:** ____________________  
**Date:** ____________________  
**Time:** ____________________

### Overall Result

- ⬜ **ALL TESTS PASSED** - System is fully functional, ready for production
- ⬜ **MINOR ISSUES** - System mostly works, minor bugs/cosmetic issues found
- ⬜ **MAJOR ISSUES** - Critical functionality broken, needs immediate attention

### Ready for Production?

- ⬜ **YES** - Approve deployment to production
- ⬜ **NO** - Requires fixes before production deployment  
- ⬜ **NEEDS REVIEW** - Engineering team should review findings first

### Additional Notes

```
[Any additional observations, recommendations, or concerns]
```

---

## Escalation

### If Critical Issues Found

**Contact:** w3jdev@gmail.com  
**Subject:** `[URGENT] Bijou AI Dashboard Testing Issues - W3J Tenant`

**Include in Report:**
1. This completed checklist
2. Screenshots of any errors
3. Browser console logs (if applicable)
4. API response samples (if technical issue)

### Reference Documents

- **EXECUTIVE_SUMMARY.md** - Overview of fixes applied
- **DB_FIX_RESULTS.md** - Database changes made
- **VERIFICATION_AUDIT_RESULTS.md** - Automated test results
- **FIX_REPORT.md** - Original issue analysis

### Rollback Available

If testing reveals critical issues that require reverting changes:

**Backup Location:** `tenants_backup_20260214` table in Supabase  
**Retention:** 30 days (until 2026-03-14)  
**Instructions:** See `DB_FIX_RESULTS.md` section "Rollback Instructions"

---

## Testing Tips

### Dashboard Not Loading?
- Clear browser cache (Ctrl+Shift+Delete)
- Try incognito/private browsing mode
- Check internet connection
- Verify URL has `?tenant=w3j` parameter

### WhatsApp Shows Disconnected?
- Wait 1 minute and refresh page
- Restart Bijou Staging app (see Test 1 instructions)
- Send test message anyway - may still work despite status display

### API Errors?
- Check if you're using correct tenant ID header
- Verify staging app is running: `https://bijou-staging.fly.dev/health`
- Check app logs: `C:\Users\w3jbt\.fly\bin\flyctl.exe logs --app bijou-staging`

### No Conversations Showing?
- Verify at least 2 conversations exist in database (see VERIFICATION_AUDIT_RESULTS.md)
- Check browser console for API errors
- Try refreshing page
- Send test WhatsApp message to create new conversation

---

## Success Criteria Summary

For testing to be considered successful, **minimum requirements:**

✅ **MUST PASS (Critical):**
- Test 1: WhatsApp page loads without errors
- Test 2: Conversations list shows data
- Test 6: Can send/receive WhatsApp messages

✅ **SHOULD PASS (Important):**
- Test 3: Analytics shows real metrics
- Test 4: Escalations page loads
- Test 7: No critical console errors

⚠️ **NICE TO HAVE (Optional):**
- Test 1: Status shows "Connected" (may show "Disconnected" due to cache)
- Test 5: Agents page functional
- Test 8: All APIs return expected data

---

**END OF CHECKLIST**

📋 **Total Tests:** 8 main tests + 3 optional API tests  
⏱️ **Estimated Time:** 15-20 minutes  
🎯 **Success Threshold:** 6/8 main tests passing  

**Good luck with testing! 🚀**
