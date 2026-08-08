# Risk Mitigation & Contingency Plan - Google Sheets Dashboard
**Project:** Bijou AI - Google Sheets Integration  
**Version:** 1.0.0  
**Created:** 2026-02-15  

---

## 🎯 RISK ASSESSMENT MATRIX

| # | Risk | Probability | Impact | Risk Score | Priority |
|---|------|-------------|--------|------------|----------|
| 1 | Google API quota exceeded | Medium (40%) | High | 32 | P0 |
| 2 | AppScript deployment fails | Low (20%) | High | 16 | P1 |
| 3 | Database schema changes break sync | Medium (30%) | Medium | 15 | P1 |
| 4 | Service account credentials compromised | Very Low (5%) | Critical | 20 | P0 |
| 5 | Webhook authentication bypass | Low (15%) | High | 12 | P2 |
| 6 | Sync performance degradation (>1000 rows) | Medium (35%) | Medium | 14 | P1 |
| 7 | Timezone mismatches in data | High (50%) | Low | 10 | P2 |
| 8 | AppScript execution timeout (6min limit) | Low (20%) | Medium | 8 | P3 |
| 9 | Tenant isolation breach | Very Low (3%) | Critical | 15 | P0 |
| 10 | Manual sheet edits cause data inconsistency | Medium (40%) | Low | 8 | P3 |

**Risk Score Formula:** `Probability (%) × Impact (1-5 scale) / 5`

---

## DETAILED RISK ANALYSIS

### RISK #1: Google API Quota Exceeded
**Probability:** 40% (Medium)  
**Impact:** High (Sync stops working, users lose real-time data)  
**Risk Score:** 32

#### Symptoms
- AppScript logs show `Exception: Service invoked too many times for one day: urlfetch.`
- Sync functions fail silently
- Logs sheet shows repeated quota errors

#### Root Causes
- Too many tenants syncing simultaneously
- Sync frequency too high (every 2 minutes)
- Inefficient API calls (N+1 queries)

#### Mitigation Strategies

**Prevention:**
1. **Implement exponential backoff**
   ```javascript
   function fetchWithRetry(url, options, maxRetries = 3) {
     for (let i = 0; i < maxRetries; i++) {
       try {
         return UrlFetchApp.fetch(url, options);
       } catch (e) {
         if (e.message.includes('quota') && i < maxRetries - 1) {
           Utilities.sleep(Math.pow(2, i) * 1000);  // 1s, 2s, 4s
         } else {
           throw e;
         }
       }
     }
   }
   ```

2. **Cache API responses** (Redis or AppScript Cache Service)
   ```javascript
   function getCachedConversations() {
     const cache = CacheService.getScriptCache();
     let data = cache.get('conversations');
     
     if (!data) {
       data = JSON.stringify(fetchConversationsFromAPI());
       cache.put('conversations', data, 300);  // Cache for 5 minutes
     }
     
     return JSON.parse(data);
   }
   ```

3. **Batch API requests** (fetch 100 rows at once, not 1 by 1)
   ```python
   # Bijou backend: Add pagination
   GET /api/conversations/{tenant_id}?limit=100&offset=0
   ```

4. **Monitor quota usage**
   ```javascript
   function logQuotaUsage() {
     const quotaUsed = UrlFetchApp.getQuotaRemaining();
     Logger.log(`Quota remaining: ${quotaUsed}`);
     
     if (quotaUsed < 100) {
       sendAlertToOwner('⚠️ Google API quota low');
     }
   }
   ```

**Detection:**
- Monitor Logs sheet for quota errors
- Set up alert trigger (GAS email notification)
- Track quota in Google Cloud Console

**Recovery:**
1. **Immediate:** Disable automatic sync, enable manual sync only
2. **Short-term:** Increase sync interval (5min → 10min)
3. **Long-term:** Upgrade to Google Workspace Enterprise ($18/user/month for unlimited quota)

**Fallback Options:**
- **Option A:** Switch to webhook-only mode (no polling)
- **Option B:** Use Google Cloud Tasks for scheduled syncs (higher quota)
- **Option C:** Implement differential sync (only fetch new data, not full table)

---

### RISK #2: AppScript Deployment Fails
**Probability:** 20% (Low)  
**Impact:** High (Manual deployment required, delays launch)  
**Risk Score:** 16

#### Symptoms
- `clasp push` fails with syntax error
- `clasp deploy` succeeds but functions don't run
- Script Properties not carried over

#### Root Causes
- Syntax errors in .gs files (JavaScript)
- Missing dependencies (though AppScript has no npm)
- Permission scope changes not approved by user

#### Mitigation Strategies

**Prevention:**
1. **Use clasp for version control**
   ```bash
   npm install -g @google/clasp
   clasp login
   clasp create --title "Bijou AI Dashboard" --type sheets
   clasp push
   clasp deploy --description "v1.0.0"
   ```

2. **Implement local testing** (before deployment)
   ```javascript
   // Run in Apps Script Editor (Test > Run > testAllFunctions)
   function testAllFunctions() {
     try {
       testSyncConversations();
       testSyncEscalations();
       testUpdateStats();
       testOnEdit();
       Logger.log('✅ All tests passed');
     } catch (e) {
       Logger.log(`❌ Test failed: ${e.message}`);
       throw e;
     }
   }
   ```

3. **Use staging spreadsheet** (test deployment before production)

**Detection:**
- Run `clasp deployments` to verify deployment succeeded
- Check Apps Script Editor → Executions for errors

**Recovery:**
1. **Immediate:** Rollback to previous deployment
   ```bash
   clasp deployments  # Get deployment ID
   clasp undeploy <deployment_id>
   clasp deploy --deploymentId <previous_deployment_id>
   ```

2. **Alternative:** Manual deployment via Apps Script Editor
   - Copy Code.gs content
   - Paste into Editor
   - Click Deploy → New Deployment

**Fallback:** Provide tenant owner with deployment instructions (manual setup)

---

### RISK #3: Database Schema Changes Break Sync
**Probability:** 30% (Medium)  
**Impact:** Medium (Stale data, requires code update)  
**Risk Score:** 15

#### Symptoms
- AppScript logs show `Cannot read property 'lead_status' of undefined`
- Conversations sheet missing columns
- Webhook returns 422 Unprocessable Entity

#### Root Causes
- Bijou backend adds new column (e.g., `voice_language`)
- Column renamed (e.g., `detected_language` → `language`)
- Column type changed (e.g., TEXT → JSON)

#### Mitigation Strategies

**Prevention:**
1. **Version API contracts** (breaking changes require v2 endpoint)
   ```python
   # Bijou backend
   @router.get("/api/v1/conversations/{tenant_id}")  # Stable
   @router.get("/api/v2/conversations/{tenant_id}")  # New schema
   ```

2. **Implement schema validation** in AppScript
   ```javascript
   function validateConversationSchema(data) {
     const requiredFields = ['id', 'chat_jid', 'message_content', 'timestamp'];
     const missing = requiredFields.filter(field => !(field in data[0]));
     
     if (missing.length > 0) {
       throw new Error(`Missing fields: ${missing.join(', ')}`);
     }
   }
   ```

3. **Graceful degradation** (use default values for missing fields)
   ```javascript
   const row = [
     conv.timestamp,
     conv.chat_jid,
     conv.message_content,
     conv.ai_response,
     conv.detected_language || 'unknown',  // ← Default value
     conv.lead_status || 'cold',           // ← Default value
     conv.sentiment || 'neutral'           // ← Default value
   ];
   ```

**Detection:**
- Monitor Logs sheet for schema errors
- Run automated tests after each backend deployment

**Recovery:**
1. **Immediate:** Display error in Logs sheet, continue syncing other data
2. **Short-term:** Update AppScript to handle new schema
3. **Long-term:** Implement schema versioning

**Fallback:** Manual data export → CSV → Google Sheets import

---

### RISK #4: Service Account Credentials Compromised
**Probability:** 5% (Very Low)  
**Impact:** Critical (Unauthorized access to all tenant spreadsheets)  
**Risk Score:** 20

#### Symptoms
- Unauthorized API calls in Google Cloud audit logs
- Spreadsheets accessed from unknown IPs
- Data exfiltration detected

#### Root Causes
- Credentials leaked in Git repository
- Credentials logged to stdout
- Phishing attack on developer

#### Mitigation Strategies

**Prevention:**
1. **Never commit credentials.json to Git**
   ```bash
   # .gitignore
   credentials.json
   service-account-key.json
   ```

2. **Store in Fly.io secrets** (encrypted at rest)
   ```powershell
   C:\Users\w3jbt\.fly\bin\flyctl.exe secrets set \
     GOOGLE_SERVICE_ACCOUNT_JSON="$(cat credentials.json)" \
     --app bijou-staging
   ```

3. **Rotate keys monthly**
   ```bash
   # Google Cloud Console → IAM → Service Accounts
   # Create new key, update Fly.io secrets, delete old key
   ```

4. **Implement IP whitelist** (if possible with Google Workspace)

5. **Enable audit logging**
   ```bash
   # Google Cloud Console → Logging → Audit Logs
   # Alert on anomalous access patterns
   ```

**Detection:**
- Monitor Google Cloud audit logs
- Set up alerts for unusual API activity
- Use git-secrets to scan commits

**Recovery:**
1. **IMMEDIATE ACTIONS (within 5 minutes):**
   - Revoke compromised service account
   - Create new service account
   - Update Fly.io secrets with new credentials
   - Deploy updated credentials

2. **FOLLOW-UP ACTIONS (within 1 hour):**
   - Audit all spreadsheets for unauthorized changes
   - Notify affected tenant owners
   - Review access logs for data exfiltration
   - Change all API keys

3. **POST-INCIDENT (within 24 hours):**
   - Conduct security review
   - Update security procedures
   - Implement additional monitoring
   - Document lessons learned

**Fallback:** Temporarily disable Google Sheets integration until credentials secured

---

### RISK #5: Webhook Authentication Bypass
**Probability:** 15% (Low)  
**Impact:** High (Unauthorized data modification)  
**Risk Score:** 12

#### Symptoms
- Database shows updates from unknown sources
- Escalations marked as resolved without authorization
- Audit logs show webhook calls without valid API key

#### Root Causes
- API key validation not enforced
- HMAC signature missing
- Replay attack (old webhook reused)

#### Mitigation Strategies

**Prevention:**
1. **Validate API key** on every webhook call
   ```python
   @router.post("/api/v1/webhooks/sheets")
   async def sheets_webhook(
       payload: SheetsWebhookPayload,
       x_api_key: str = Header(..., alias="X-API-Key")
   ):
       if not await validate_api_key(x_api_key, payload.tenant_id):
           raise HTTPException(status_code=401, detail="Invalid API key")
   ```

2. **Implement HMAC signature** (recommended for production)
   ```python
   import hmac
   import hashlib
   
   def verify_webhook_signature(payload_body: bytes, signature: str, secret: str) -> bool:
       expected = hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
       return hmac.compare_digest(expected, signature)
   
   @router.post("/api/v1/webhooks/sheets")
   async def sheets_webhook(
       request: Request,
       x_signature: str = Header(...)
   ):
       body = await request.body()
       if not verify_webhook_signature(body, x_signature, WEBHOOK_SECRET):
           raise HTTPException(status_code=401)
   ```

3. **Add timestamp validation** (prevent replay attacks)
   ```python
   from datetime import datetime, timedelta
   
   def validate_timestamp(timestamp: str) -> bool:
       request_time = datetime.fromisoformat(timestamp)
       now = datetime.now()
       return abs((now - request_time).total_seconds()) < 300  # 5 minutes
   ```

4. **Rate limiting** (prevent brute-force attacks)
   ```python
   from slowapi import Limiter
   
   limiter = Limiter(key_func=lambda: request.client.host)
   
   @app.post("/api/v1/webhooks/sheets")
   @limiter.limit("10/minute")  # Max 10 requests per minute per IP
   async def sheets_webhook(...):
       ...
   ```

**Detection:**
- Monitor failed authentication attempts (log to notification_logs)
- Alert on unusual webhook patterns (e.g., 100 calls in 1 minute)

**Recovery:**
1. **Immediate:** Disable webhook endpoint (`WEBHOOKS_ENABLED=false`)
2. **Short-term:** Investigate source of unauthorized calls
3. **Long-term:** Implement HMAC signatures

---

### RISK #6: Sync Performance Degradation (>1000 rows)
**Probability:** 35% (Medium)  
**Impact:** Medium (Slow sync, timeout errors)  
**Risk Score:** 14

#### Symptoms
- Sync takes >5 minutes (approaches 6-minute AppScript limit)
- Timeout errors in Logs sheet
- Google Sheets UI becomes sluggish

#### Mitigation Strategies

**Prevention:**
1. **Implement pagination**
   ```javascript
   async function syncConversationsInBatches() {
     const BATCH_SIZE = 100;
     let offset = 0;
     let allData = [];
     
     while (true) {
       const batch = await fetchConversations(offset, BATCH_SIZE);
       if (batch.length === 0) break;
       
       allData = allData.concat(batch);
       offset += BATCH_SIZE;
     }
     
     writeToSheet(allData);
   }
   ```

2. **Use `setValues()` instead of `setValue()`** (100x faster)
   ```javascript
   // BAD - O(n²) complexity
   for (let i = 0; i < data.length; i++) {
     sheet.getRange(i+2, 1).setValue(data[i].timestamp);
     sheet.getRange(i+2, 2).setValue(data[i].chat_jid);
     // ...
   }
   
   // GOOD - O(n) complexity
   const rows = data.map(conv => [
     conv.timestamp,
     conv.chat_jid,
     conv.message_content,
     conv.ai_response,
     conv.detected_language,
     conv.lead_status,
     conv.sentiment
   ]);
   sheet.getRange(2, 1, rows.length, 7).setValues(rows);
   ```

3. **Archive old data** (only sync last 30 days)
   ```python
   # Bijou backend
   @router.get("/api/conversations/{tenant_id}")
   async def get_conversations(tenant_id: str, days: int = 30):
       cutoff = datetime.now() - timedelta(days=days)
       return await supabase.table("conversations") \
           .select("*") \
           .eq("tenant_id", tenant_id) \
           .gte("timestamp", cutoff.isoformat()) \
           .execute()
   ```

**Detection:**
- Monitor Apps Script execution logs
- Alert if sync duration >4 minutes (approaching 6-min limit)

**Recovery:**
1. **Immediate:** Reduce batch size
2. **Short-term:** Implement differential sync (only new data)
3. **Long-term:** Move to BigQuery for large datasets

---

### RISK #7: Timezone Mismatches
**Probability:** 50% (High)  
**Impact:** Low (Confusing timestamps, not critical)  
**Risk Score:** 10

#### Symptoms
- Timestamps off by several hours
- "Today" filter shows yesterday's data

#### Mitigation Strategies

**Prevention:**
1. **Store all timestamps in UTC** (database and API)
2. **Convert to local timezone** in Google Sheets
   ```javascript
   function formatTimestamp(utcTimestamp) {
     const date = new Date(utcTimestamp);
     return Utilities.formatDate(date, "Asia/Kuala_Lumpur", "yyyy-MM-dd HH:mm:ss");
   }
   ```

3. **Document timezone in Settings sheet**

---

### RISK #9: Tenant Isolation Breach
**Probability:** 3% (Very Low)  
**Impact:** Critical (Data leak, GDPR violation)  
**Risk Score:** 15

#### Symptoms
- Tenant A sees Tenant B's conversations
- API returns data from wrong tenant
- Audit logs show cross-tenant queries

#### Mitigation Strategies

**Prevention:**
1. **ALWAYS filter by tenant_id** in every query
   ```python
   # ✅ CORRECT
   conversations = await supabase.table("conversations") \
       .select("*") \
       .eq("tenant_id", tenant_id) \
       .execute()
   
   # ❌ WRONG - data leak!
   conversations = await supabase.table("conversations") \
       .select("*") \
       .execute()
   ```

2. **Enable Row-Level Security** in Supabase
   ```sql
   ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
   
   CREATE POLICY "Tenants can only access their own data"
   ON conversations
   FOR ALL
   USING (tenant_id = auth.uid());
   ```

3. **Add integration tests** for tenant isolation
   ```python
   @pytest.mark.integration
   async def test_tenant_isolation():
       # Tenant A tries to access Tenant B's data
       response = await client.get(
           f"/api/conversations/{tenant_b_id}",
           headers={"X-API-Key": tenant_a_api_key}
       )
       
       assert response.status_code == 403  # Forbidden
   ```

**Detection:**
- Audit all database queries
- Monitor for `SELECT * FROM` without `WHERE tenant_id =`

**Recovery:**
1. **Immediate:** Take affected tables offline
2. **Investigation:** Audit logs to identify scope of breach
3. **Notification:** Inform affected tenants (GDPR requirement)
4. **Remediation:** Implement RLS, add tests

---

## 📋 CONTINGENCY PLAYBOOKS

### PLAYBOOK 1: Total System Failure
**Trigger:** All syncs failing for >30 minutes

**Actions:**
1. Switch to manual mode (disable all triggers)
2. Notify tenant owners via email
3. Provide CSV export option
4. Investigate root cause
5. Deploy fix to staging first
6. Re-enable syncs incrementally (1 tenant at a time)

### PLAYBOOK 2: Data Corruption Detected
**Trigger:** Spreadsheet shows incorrect/missing data

**Actions:**
1. Immediately stop all syncs
2. Create backup of spreadsheet (File → Make a copy)
3. Compare spreadsheet data vs database
4. Identify source of corruption (AppScript bug? Database migration?)
5. Restore from backup
6. Fix root cause
7. Re-run sync with validation

### PLAYBOOK 3: Security Breach Confirmed
**Trigger:** Unauthorized access detected in audit logs

**Actions:**
1. Revoke all service account keys
2. Disable webhook endpoints
3. Rotate all API keys
4. Audit all tenants for unauthorized changes
5. Notify affected tenants within 72 hours (GDPR)
6. Conduct post-mortem
7. Implement additional security measures

---

## 🎯 SUCCESS CRITERIA (Risk Management)

### Pre-Launch Checklist
- [ ] All P0 and P1 risks have mitigation strategies
- [ ] Security audit passed (no critical vulnerabilities)
- [ ] Backup and recovery procedures tested
- [ ] Monitoring alerts configured
- [ ] Incident response team identified

### Post-Launch Monitoring (First 30 Days)
- [ ] Monitor error rate daily
- [ ] Review audit logs weekly
- [ ] Rotate service account keys (monthly)
- [ ] Conduct security review (monthly)
- [ ] Update risk register based on incidents

---

**Document Version:** 1.0.0  
**Created:** 2026-02-15  
**Status:** Production-Ready  
**Review Cycle:** After every incident or quarterly  
**Owner:** @security (primary), @architect (secondary)
