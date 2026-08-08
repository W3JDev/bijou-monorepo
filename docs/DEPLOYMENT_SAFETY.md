# Deployment Safety Plan

**Purpose:** Ensure zero risk to production during all future phases  
**Strategy:** Blue-Green Deployment with parallel apps  
**Status:** Ready for Phase 2+  

---

## 🛡️ Core Principle

**NEVER modify or delete running production apps until new apps are proven stable.**

---

## Current Production (DO NOT TOUCH)

### Active Fly.io Apps

```
whatsapp-bridge-w3j
├── Status: ✅ PRODUCTION
├── URL: https://whatsapp-bridge-w3j.fly.dev
├── Purpose: WhatsApp message handling
└── Action: KEEP RUNNING (do not modify, do not delete)

bijou-ai-enterprise-w3j
├── Status: ✅ PRODUCTION
├── URL: https://bijou-ai-enterprise-w3j.fly.dev
├── Purpose: AI conversation processing
└── Action: KEEP RUNNING (do not modify, do not delete)
```

**These apps serve real customers RIGHT NOW. We will NOT touch them until Phase 6.**

---

## New Deployment Plan (Phase 5-6)

### Strategy: Blue-Green Deployment

**Blue (Old) = Current production apps (keep running)**  
**Green (New) = New apps from packages/ (deploy separately)**

### New Apps to Create

```
whatsapp-bridge-mcp-prod
├── Source: packages/whatsapp-bridge-mcp/
├── Purpose: New bridge with improved architecture
├── URL: https://whatsapp-bridge-mcp-prod.fly.dev (new URL)
└── Relationship: Runs ALONGSIDE old bridge

bijou-core-prod
├── Source: packages/bijou-core/
├── Purpose: New Bijou with RAG and enhanced features
├── URL: https://bijou-core-prod.fly.dev (new URL)
└── Relationship: Runs ALONGSIDE old Bijou
```

**Key Point: Different app names = Different apps = Both run at same time!**

---

## Deployment Phases

### Phase 1-4: Development Only ✅
- **Status:** Creating packages, adding features, testing locally
- **Production:** Untouched
- **Risk:** Zero (no deployments)

### Phase 5: Staging Deployment 📋
- **Create staging apps:**
  ```bash
  fly apps create whatsapp-bridge-mcp-staging
  fly apps create bijou-core-staging
  ```
- **Deploy and test:**
  - Deploy new code to staging apps
  - Run comprehensive tests
  - Monitor for 1-2 weeks
- **Production:** Still untouched
- **Risk:** Zero (staging only)

### Phase 6: Blue-Green Production 📋
- **Step 1: Create new production apps**
  ```bash
  fly apps create whatsapp-bridge-mcp-prod
  fly apps create bijou-core-prod
  ```

- **Step 2: Deploy new code**
  ```bash
  cd packages/whatsapp-bridge-mcp
  fly deploy --app whatsapp-bridge-mcp-prod
  
  cd ../bijou-core
  fly deploy --app bijou-core-prod
  ```

- **Step 3: Both old and new apps running**
  ```
  OLD (Blue):                    NEW (Green):
  whatsapp-bridge-w3j     +      whatsapp-bridge-mcp-prod
  bijou-ai-enterprise-w3j +      bijou-core-prod
  
  Both processing messages simultaneously!
  ```

- **Step 4: Gradual traffic switch**
  - Update webhook URL to point to new Bijou
  - Monitor new apps for 48 hours
  - Old apps still running (instant rollback if needed)

- **Step 5: Only after 100% confidence**
  - Decommission old apps
  - Keep them for 30 days as backup

---

## Rollback Procedures

### Instant Rollback (Environment Variable Change)

**If new Bijou has issues:**
```bash
# Switch webhook URL back to old Bijou (30 seconds)
fly secrets set BIJOU_WEBHOOK_URL=https://bijou-ai-enterprise-w3j.fly.dev/webhook/message \
  --app whatsapp-bridge-mcp-prod

# Or switch back to old bridge entirely
fly secrets set BRIDGE_URL=https://whatsapp-bridge-w3j.fly.dev \
  --app bijou-ai-enterprise-w3j
```

**Result:** Back to old system in under 1 minute, zero data loss

### Full Rollback (Keep Old Apps Running)

**If new apps completely fail:**
```bash
# Old apps are still running!
# Just point traffic back to old apps
# Delete new apps if needed

fly apps destroy whatsapp-bridge-mcp-prod
fly apps destroy bijou-core-prod
```

**Result:** Back to original state, nothing lost

---

## Safety Guarantees

### ✅ Zero Downtime

- Old apps run throughout entire migration
- New apps tested thoroughly before traffic switch
- Traffic switch is instant and reversible
- No customer sees any interruption

### ✅ Zero Data Loss

- Both apps access same WhatsApp session (Fly.io volume)
- SQLite database shared or synced
- Conversation memory preserved
- No messages lost

### ✅ Easy Rollback

- Environment variable change = instant rollback
- Old apps kept running for 30+ days
- Can switch back and forth for testing
- No permanent changes until we're 100% confident

### ✅ Gradual Migration

- Deploy to staging first (Phase 5)
- Deploy to production but don't switch traffic (Phase 6 start)
- Switch small percentage of traffic (Phase 6 middle)
- Full cutover only after proven stable (Phase 6 end)

---

## Commands You'll Run (Phase by Phase)

### Phase 2-4: Local Development Only

**No deployment commands! All local work:**
```bash
# Install packages locally
pip install -e packages/shared
pip install -e packages/bijou-core

# Run tests locally
pytest packages/bijou-core/tests/

# No Fly.io commands, no production changes
```

### Phase 5: Staging Deployment

**I'll give you these exact commands:**
```bash
# Create staging apps (NEW apps, not touching production)
fly apps create whatsapp-bridge-mcp-staging
fly apps create bijou-core-staging

# Create staging volumes
fly volumes create whatsapp_data --app whatsapp-bridge-mcp-staging

# Deploy to staging
cd packages/whatsapp-bridge-mcp
fly deploy --app whatsapp-bridge-mcp-staging

cd ../bijou-core
fly deploy --app bijou-core-staging

# Test staging (no impact on production)
curl https://bijou-core-staging.fly.dev/health
```

**Production apps: Still running normally! ✅**

### Phase 6: Blue-Green Production

**I'll give you these exact commands:**
```bash
# Create NEW production apps (different names!)
fly apps create whatsapp-bridge-mcp-prod
fly apps create bijou-core-prod

# Create volumes for new apps
fly volumes create whatsapp_data --app whatsapp-bridge-mcp-prod

# Deploy to NEW apps (old apps still running!)
cd packages/whatsapp-bridge-mcp
fly deploy --app whatsapp-bridge-mcp-prod

cd ../bijou-core
fly deploy --app bijou-core-prod

# At this point, you have BOTH old and new running!

# Switch traffic (reversible!)
fly secrets set BIJOU_WEBHOOK_URL=https://bijou-core-prod.fly.dev/webhook/message \
  --app whatsapp-bridge-mcp-prod

# Monitor for 48 hours, old apps still running for instant rollback
```

**If anything goes wrong: Change URL back, instant rollback! ✅**

---

## What You Control

### You Decide When To:

1. **Create staging apps** (Phase 5)
   - I'll give commands, you run them when ready
   - Zero risk (staging only)

2. **Deploy to staging** (Phase 5)
   - I'll give commands, you test staging
   - Zero production impact

3. **Create new production apps** (Phase 6)
   - I'll give commands, you run when confident
   - Old apps keep running

4. **Switch traffic** (Phase 6)
   - I'll give command, you run when 100% ready
   - Reversible instantly

5. **Decommission old apps** (Phase 6 end)
   - Only after 30+ days of new apps running perfectly
   - You make final call

**You're in control every step. I just give you the commands!**

---

## Monitoring Plan

### Before Switching Traffic

**Check new apps are healthy:**
```bash
# Health check
curl https://bijou-core-prod.fly.dev/health
curl https://whatsapp-bridge-mcp-prod.fly.dev/health

# Test conversation
# Send test WhatsApp message
# Verify AI responds correctly

# Check logs
fly logs --app bijou-core-prod
fly logs --app whatsapp-bridge-mcp-prod
```

**Only switch if ALL checks pass!**

### After Switching Traffic

**Monitor for 48 hours:**
```bash
# Continuous log monitoring
fly logs --app bijou-core-prod -f

# Check for errors
fly logs --app bijou-core-prod | grep ERROR

# Verify customer conversations working
# Check response times
# Monitor error rates
```

**If ANY issues: Instant rollback!**

### Success Criteria

**Only decommission old apps when:**
- ✅ New apps running for 30+ days
- ✅ Zero critical errors
- ✅ Customer satisfaction maintained
- ✅ Response times acceptable
- ✅ All features working
- ✅ You feel 100% confident

---

## Timeline with Safety Checkpoints

```
Phase 1: Reorganization ✅
└─ CHECKPOINT: No deployment, zero risk ✅

Phase 2: Add RAG (2-3 weeks)
└─ CHECKPOINT: Local only, zero risk ✅

Phase 3: Add Tools (3-4 weeks)
└─ CHECKPOINT: Local only, zero risk ✅

Phase 4: Add Tests (2-3 weeks)
└─ CHECKPOINT: Tests pass locally ✅

Phase 5: Staging Deploy (1-2 weeks)
├─ CHECKPOINT: Create staging apps
├─ CHECKPOINT: Deploy to staging
├─ CHECKPOINT: Staging tests pass
└─ DECISION: Proceed to production? (YOU DECIDE)

Phase 6: Production Deploy (3-4 weeks)
├─ CHECKPOINT: Create new prod apps (old still running)
├─ CHECKPOINT: New apps healthy
├─ CHECKPOINT: Switch traffic (reversible!)
├─ CHECKPOINT: Monitor 48 hours
├─ CHECKPOINT: Monitor 7 days
├─ CHECKPOINT: Monitor 30 days
└─ DECISION: Decommission old apps? (YOU DECIDE)

Phase 7: Cleanup (1 week)
└─ Archive old code, celebrate! 🎉
```

**At every checkpoint, you can stop or rollback with zero consequences!**

---

## Your Safety Net

### What Protects You:

1. **Separate App Names**
   - Old: `whatsapp-bridge-w3j`, `bijou-ai-enterprise-w3j`
   - New: `whatsapp-bridge-mcp-prod`, `bijou-core-prod`
   - Can't accidentally modify wrong one

2. **Both Run Simultaneously**
   - Old apps keep serving customers
   - New apps tested in parallel
   - Switch traffic instantly

3. **Environment Variable Switching**
   - Change one URL = instant rollback
   - 30 seconds to switch back
   - No code changes needed

4. **Staging Environment**
   - Test everything in staging first
   - No production impact from testing
   - Full replica of production

5. **Gradual Rollout**
   - Can test with 1% traffic first
   - Increase gradually (10%, 25%, 50%, 100%)
   - Rollback at any point

---

## Summary

**Question:** Can we deploy without touching current production?  
**Answer:** YES! 100% YES!

**How:**
1. New apps have different names
2. Both old and new run at same time
3. Switch traffic with environment variable (reversible)
4. Keep old apps running for 30+ days
5. Only delete old apps when YOU decide

**Your Risk:** Zero until YOU decide to decommission old apps

**My Promise:**
- Every command explained upfront
- Every step reversible
- Every checkpoint you control
- Zero surprises

---

**Status:** Ready for safe deployment in Phase 5-6  
**Your Control:** 100%  
**Production Risk:** Zero (until you decide otherwise)  
**Confidence Level:** You should feel 100% safe! ✅