# AGENT.MD - Bijou AI SaaS Platform Documentation

## =============================================================================
## Last Updated: 2026-01-30
## Purpose: Complete guide for SaaS features and multi-tenant architecture
## Location: packages/bijou-core/bijou_core/saas/
## =============================================================================

## 🎯 WHAT IS THIS?

**Bijou AI SaaS Module** provides multi-tenant capabilities for running Bijou as a SaaS platform.

This module adds:
1. Multi-tenant isolation (complete data separation between clients)
2. Subscription tiers (Freemium, Starter, Pro, Enterprise)
3. Usage tracking and limit enforcement
4. @bijou in-chat commands for better UX
5. / command discovery (slash commands)
6. Automated reporting (daily, weekly, monthly)
7. Pricing engine with tier management
8. Client onboarding workflow

```
┌─────────────────────────────────────────────────────────────┐
│                      Bijou SaaS Platform                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Tenant A              Tenant B              Tenant C        │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐    │
│  │ Freemium │         │ Starter  │         │    Pro   │    │
│  │ 100 msg  │         │ 1000 msg │         │ 5000 msg │    │
│  │ 5 cust   │         │ 50 cust  │         │ Unlimited│    │
│  │ No tools │         │ Tools ✓  │         │ All tools│    │
│  └──────────┘         └──────────┘         └──────────┘    │
│       ↓                     ↓                     ↓          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          Shared Bijou Core (Isolated Data)          │   │
│  │  • TRACE Framework  • Memory  • Tools               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 MODULE STRUCTURE

```
bijou_core/saas/
├── __init__.py                    # Module exports
├── AGENT.md                       # THIS FILE
├── command_handler.py             # @bijou and / commands
├── pricing_engine.py              # Subscription tiers & usage tracking
├── tenant_manager.py              # Multi-tenant isolation
├── reporting_engine.py            # Auto reports (daily/weekly/monthly)
├── function_caller.py             # AI-driven tool orchestration (some tools stubbed — see search_knowledge/set_reminder)
└── handover_system.py             # Human escalation queue
# NOTE: onboarding flows live in onboarding_api.py / onboarding_api_v3.py / onboarding_complete.py
# (there is no onboarding_wizard.py).
```

---

## 🚀 QUICK START

### Step 1: Enable SaaS Features

Set environment variables in Fly.io:

```bash
# Core SaaS features
fly secrets set ENABLE_BIJOU_COMMANDS=true -a bijou-staging
fly secrets set ENABLE_MULTI_TENANT=true -a bijou-staging
fly secrets set ENABLE_USAGE_LIMITS=true -a bijou-staging
fly secrets set ENABLE_AUTO_REPORTS=true -a bijou-staging

# Report settings
fly secrets set ENABLE_DAILY_REPORTS=true -a bijou-staging
fly secrets set ENABLE_WEEKLY_REPORTS=true -a bijou-staging
fly secrets set REPORT_HOUR=9 -a bijou-staging

# Default tenant (for testing)
fly secrets set DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000001 -a bijou-staging
```

### Step 2: Initialize in Your Code

```python
from bijou_core.saas import (
    CommandHandler,
    PricingEngine,
    TenantManager,
    ReportingEngine,
    SubscriptionTier
)

# Initialize SaaS components
tenant_manager = TenantManager(supabase_client=supabase)
pricing_engine = PricingEngine(supabase_client=supabase)
command_handler = CommandHandler(
    owner_jid=owner_jid,
    admin_controller=admin_controller,
    memory_system=memory_system
)
reporting_engine = ReportingEngine(
    memory_system=memory_system,
    supabase_client=supabase,
    pricing_engine=pricing_engine,
    send_message_callback=send_message
)
```

### Step 3: Use in Message Processing

```python
async def process_message(self, message: Dict[str, Any]):
    chat_jid = message.get("chat_jid")
    sender = message.get("sender")
    content = message.get("content", "")

    # 1. Get tenant from WhatsApp number
    tenant_id = self.tenant_manager.get_tenant_from_whatsapp(sender)

    # 2. Check if command
    if self.command_handler.is_command(content):
        response = await self.command_handler.handle_command(
            content, chat_jid, sender
        )
        if response:
            self.send_message(chat_jid, response)
            return

    # 3. Check if should respond (quiet mode check)
    if not self.command_handler.should_respond(content, chat_jid, sender):
        logger.info(f"Quiet mode active in {chat_jid}, not responding")
        return

    # 4. Check usage limits
    allowed, error_msg = self.pricing_engine.check_limit(
        tenant_id, "messages", increment=1
    )
    if not allowed:
        self.send_message(chat_jid, error_msg)
        return

    # 5. Process message normally
    response = await self._generate_response(content)
    self.send_message(chat_jid, response)

    # 6. Track usage
    self.pricing_engine.track_usage(
        tenant_id=tenant_id,
        message_count=1,
        customer_jid=chat_jid
    )
```

---

## 💎 SUBSCRIPTION TIERS

### FREEMIUM (Free Forever)

**Purpose:** Trial and low-volume users

**Limits:**
- 100 messages/month
- 5 active customers
- 0 tool calls (no image/audio/calendar/email)
- 10 knowledge documents max
- 30-day memory retention

**Features:**
- ✅ Basic AI responses
- ✅ Limited /admin commands (mode, quiet)
- ✅ Weekly reports (WhatsApp only)
- ✅ @bijou help
- ❌ No custom instructions
- ❌ No model switching
- ❌ No tools
- ❌ No human handover queue
- ❌ No dashboard

**Support:** Community only (Discord/forum)

---

### STARTER ($29/month)

**Purpose:** Small businesses, solopreneurs

**Limits:**
- 1,000 messages/month
- 50 active customers
- 100 tool calls/month (image + audio only)
- 50 knowledge documents
- 90-day memory retention

**Features:**
- ✅ All Freemium features
- ✅ Image analysis (Gemini Vision)
- ✅ Audio transcription (Whisper)
- ✅ Custom AI instructions
- ✅ Model switching (Gemini, GPT-4, Claude)
- ✅ Daily + weekly reports (WhatsApp)
- ✅ Basic human handover (manual routing)
- ❌ No calendar/email tools
- ❌ No API access
- ❌ No dashboard

**Support:** Email (48h response)

---

### PRO ($99/month)

**Purpose:** Growing businesses, teams

**Limits:**
- 5,000 messages/month
- Unlimited customers
- Unlimited tool calls
- 200 knowledge documents
- 1-year memory retention

**Features:**
- ✅ All Starter features
- ✅ Calendar integration (Google Calendar)
- ✅ Email integration (Gmail)
- ✅ Advanced human handover (queue + routing + analytics)
- ✅ API access + webhooks
- ✅ Analytics dashboard
- ✅ Daily + weekly + monthly reports (Dashboard + WhatsApp + Email)
- ✅ Custom integrations (Zapier)

**Support:** Priority email (24h response) + chat

---

### ENTERPRISE ($299+/month - Custom)

**Purpose:** Large organizations, agencies

**Limits:**
- 20,000+ messages/month (custom)
- Unlimited everything
- Custom data retention

**Features:**
- ✅ All Pro features
- ✅ White-label branding
- ✅ Multi-agent teams
- ✅ Custom model fine-tuning
- ✅ SSO/SAML authentication
- ✅ Custom SLA
- ✅ BI integration (Looker, Tableau)
- ✅ Dedicated infrastructure
- ✅ Custom integrations

**Support:** Dedicated Slack channel + phone + account manager

---

## 🎨 @BIJOU COMMANDS

### Everyone Can Use:

```
@bijou help              → Show available commands
@bijou quiet             → Stop responding in this chat (observe only)
@bijou resume            → Resume responding
@bijou status            → Check Bijou status
@bijou summarize         → Summarize this conversation
@bijou search [query]    → Search knowledge base
@bijou remind [time] [msg] → Set reminder (coming soon)
```

### Owner Only:

```
@bijou insights          → Get chat analytics
@bijou report            → Generate instant report
```

### How It Works:

**In Group Chats:**
```
Customer 1: Hey, what's the shipping time?
Bijou: We ship within 3-5 business days!

Owner (in same group): @bijou quiet
Bijou: 🤫 Quiet mode enabled. I'll observe but won't respond.

Customer 2: Is this still available?
[Bijou stays silent]

Owner: Yes, we have it in stock!

Owner: @bijou resume
Bijou: 👋 I'm back! I'll respond to messages now.
```

**In DMs:**
```
Customer: @bijou help
Bijou: [Shows help menu]

Customer: @bijou summarize
Bijou: 📝 Conversation Summary
       Messages: 12
       Last discussed: Shipping times...
```

---

## ⚡ SLASH COMMANDS (/)

Slash commands provide quick access and discovery:

```
/help                    → Show all commands
/status                  → Check Bijou status
/admin                   → Admin control panel (owner only)
```

**Admin Shortcuts (Owner Only):**
```
/admin mode quiet        → Observer mode
/admin mode auto         → Auto-respond
/admin kb add [text]     → Add knowledge
/admin report            → Generate report
/admin model use gemini  → Switch to Gemini
```

**Auto-Complete Experience:**

When user types `/`, they see:
```
💡 Available commands:
   /help - Show all commands
   /status - Check status
   /admin - Admin panel (owner only)

Type @bijou for more commands!
```

---

## 📊 AUTOMATED REPORTS

### Daily Report (9 AM local time)

Sent every day to owner via WhatsApp:

```
📊 Daily Report
📅 Wednesday, January 29, 2026

Message Activity:
📨 Total messages: 47
👥 Active customers: 12
🆕 New customers: 2

Sentiment:
😊 Positive: 65%
😐 Neutral: 25%
😟 Negative: 10%

AI Performance:
⚡ Avg response time: 2.3s
✅ Success rate: 94.5%

📈 Usage (Month):
💬 Messages: 45%
🛠️ Tools: 23%

💡 Full analytics: https://bijou.ai/dashboard
```

### Weekly Report (Monday 9 AM)

```
📊 Weekly Report
📅 Week of Jan 23 - Jan 29, 2026

📈 Growth:
📨 Total messages: 312 (+15%)
👥 Total customers: 45 (+8%)
🆕 New this week: 5

😊 Customer Happiness:
Average sentiment: 4.2/5.0
Positive interactions: 68%
Issues resolved: 23/25

🎯 Top Topics:
1. Shipping times (45 mentions)
2. Product availability (32 mentions)
3. Pricing (28 mentions)
4. Returns policy (15 mentions)
5. Payment methods (12 mentions)

⚡ Performance:
Avg response time: 2.1s
AI success rate: 95.2%
Human handovers: 3

💰 Business Insights:
🎯 8 sales opportunities detected
💎 Estimated value: $2,400

📊 View detailed analytics: https://bijou.ai/dashboard
```

### Monthly Report (1st of month, 9 AM)

Comprehensive analysis with:
- Key metrics and KPIs
- Customer experience scores
- AI performance trends
- Cost analysis
- Business insights
- ROI recommendations

---

## 🔧 PRICING ENGINE

### Usage Tracking

```python
# Track message usage
pricing_engine.track_usage(
    tenant_id="abc-123",
    message_count=1,
    customer_jid="60123456789@s.whatsapp.net"
)

# Track tool usage
pricing_engine.track_usage(
    tenant_id="abc-123",
    tool_call_count=1,
    customer_jid="60123456789@s.whatsapp.net"
)
```

### Limit Enforcement

```python
# Check before processing
allowed, error_msg = pricing_engine.check_limit(
    tenant_id="abc-123",
    usage_type="messages",
    increment=1
)

if not allowed:
    # Send upgrade message
    send_message(chat_jid, error_msg)
    return
```

### Warning at 80% Usage

```python
should_warn, warning = pricing_engine.should_warn_limit(tenant_id)
if should_warn:
    # Send warning to owner
    send_message(owner_jid, warning)
```

### Feature Checks

```python
# Check if tenant can use a feature
if pricing_engine.is_feature_enabled(tenant_id, "image_tool"):
    # Process image
    result = image_tool.analyze(image_path)
else:
    return "🔒 Image analysis is only available in Starter tier and above."
```

---

## 🏢 MULTI-TENANT ISOLATION

### How It Works

Each tenant has:
- Unique `tenant_id` (UUID)
- Separate customer data
- Isolated conversations
- Own knowledge base
- Individual settings
- Independent usage tracking

**Database Schema:**

```sql
-- Tenants table
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    business_name TEXT NOT NULL,
    whatsapp_number TEXT UNIQUE,
    owner_email TEXT,
    subscription_tier TEXT DEFAULT 'freemium',
    status TEXT DEFAULT 'active',
    settings JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- All other tables have tenant_id
CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    chat_jid TEXT NOT NULL,
    message_content TEXT,
    -- ... other fields
);

CREATE TABLE usage_tracking (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    message_count INT DEFAULT 0,
    tool_call_count INT DEFAULT 0,
    customer_jid TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Tenant Resolution

From WhatsApp number to tenant:

```python
# User sends message from +60123456789
tenant_id = tenant_manager.get_tenant_from_whatsapp(
    "+60123456789@s.whatsapp.net"
)

# Returns: "abc-123-def-456" (tenant's UUID)
```

### Data Isolation Guarantee

```python
# Ensure tenant can only access their data
allowed, error = tenant_manager.ensure_tenant_isolation(
    tenant_id="abc-123",
    chat_jid="60123456789@s.whatsapp.net"
)

if not allowed:
    logger.error(f"Isolation violation: {error}")
    return
```

---

## 🚦 FEATURE FLAGS

All SaaS features are controlled by environment variables:

### Core Flags

```bash
ENABLE_BIJOU_COMMANDS=true        # @bijou and / commands
ENABLE_MULTI_TENANT=true          # Multi-tenant isolation
ENABLE_USAGE_LIMITS=true          # Enforce subscription limits
ENABLE_AUTO_REPORTS=true          # Automated reporting
```

### Report Flags

```bash
ENABLE_DAILY_REPORTS=true         # Daily reports (9 AM)
ENABLE_WEEKLY_REPORTS=true        # Weekly reports (Monday 9 AM)
ENABLE_MONTHLY_REPORTS=true       # Monthly reports (1st, 9 AM)
REPORT_HOUR=9                     # Hour to send reports (0-23)
```

### Tenant Flags

```bash
DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000001
```

### Emergency Override

To disable all SaaS features instantly:

```bash
fly secrets set ENABLE_BIJOU_COMMANDS=false -a bijou-staging
fly secrets set ENABLE_USAGE_LIMITS=false -a bijou-staging
fly secrets set ENABLE_AUTO_REPORTS=false -a bijou-staging

fly apps restart bijou-staging
```

System reverts to basic operation (no SaaS features, no limits).

---

## 🧪 TESTING

### Test @bijou Commands

```bash
# Send to your test WhatsApp
@bijou help
@bijou quiet
[Send a message - Bijou should NOT respond]
@bijou resume
[Send a message - Bijou SHOULD respond]
@bijou status
@bijou summarize
```

### Test Usage Limits

```python
# Set test tenant to freemium (100 msg/month)
supabase.table("tenants").update({
    "subscription_tier": "freemium"
}).eq("id", test_tenant_id).execute()

# Send 101 messages
# The 101st should return upgrade prompt
```

### Test Reports

```python
# Manually trigger report
await reporting_engine.send_report(
    tenant_id=test_tenant_id,
    report_type="daily",
    owner_jid=owner_jid
)

# Check WhatsApp for report
```

---

## 🚀 DEPLOYMENT

### Deploy SaaS Features (Staging)

```bash
cd Bijou-Ai-With-whatsapp-mcp

# 1. Enable feature flags
fly secrets set \
  ENABLE_BIJOU_COMMANDS=true \
  ENABLE_MULTI_TENANT=true \
  ENABLE_USAGE_LIMITS=true \
  ENABLE_AUTO_REPORTS=true \
  ENABLE_DAILY_REPORTS=true \
  ENABLE_WEEKLY_REPORTS=true \
  -a bijou-staging

# 2. Deploy code
fly deploy --ha=false -a bijou-staging

# 3. Verify in logs
fly logs -a bijou-staging | grep -E "(CommandHandler|PricingEngine|TenantManager|ReportingEngine)"

# Expected output:
# ✅ CommandHandler initialized (enabled=true)
# ✅ PricingEngine initialized
# ✅ TenantManager initialized (multi_tenant=true)
# ✅ ReportingEngine initialized (enabled=true)
```

### Verify Everything Works

```bash
# 1. Test health endpoint
curl https://bijou-staging.fly.dev/health

# 2. Test @bijou command
# Send "@bijou help" via WhatsApp

# 3. Check logs
fly logs -a bijou-staging --grep "CommandHandler"

# Should see:
# 📨 Received command: @bijou help
# ✅ Command handled successfully
```

---

## 📈 MONITORING

### Key Metrics to Track

1. **Usage Metrics:**
   - Messages per tenant
   - Tool calls per tenant
   - Customer count per tenant

2. **Performance:**
   - Command response time
   - Report generation time
   - Limit check latency

3. **Business Metrics:**
   - Freemium → Starter conversion rate
   - Starter → Pro upgrade rate
   - Churn rate per tier
   - MRR (Monthly Recurring Revenue)

4. **Error Rates:**
   - Failed limit checks
   - Report send failures
   - Tenant isolation violations

### Dashboard Queries

```sql
-- Active tenants by tier
SELECT subscription_tier, COUNT(*) as count
FROM tenants
WHERE status = 'active'
GROUP BY subscription_tier;

-- Usage by tenant (current month)
SELECT
    t.business_name,
    SUM(u.message_count) as messages,
    SUM(u.tool_call_count) as tools
FROM usage_tracking u
JOIN tenants t ON u.tenant_id = t.id
WHERE u.created_at >= date_trunc('month', NOW())
GROUP BY t.business_name
ORDER BY messages DESC;

-- Tenants approaching limits
SELECT
    t.business_name,
    t.subscription_tier,
    SUM(u.message_count) as current_usage
FROM usage_tracking u
JOIN tenants t ON u.tenant_id = t.id
WHERE u.created_at >= date_trunc('month', NOW())
GROUP BY t.id, t.business_name, t.subscription_tier
HAVING SUM(u.message_count) > 80 -- 80% of freemium limit
ORDER BY current_usage DESC;
```

---

## 🐛 TROUBLESHOOTING

### Commands Not Working

**Symptom:** @bijou commands return nothing

**Check:**
```bash
# 1. Feature flag enabled?
fly secrets list -a bijou-staging | grep ENABLE_BIJOU_COMMANDS

# 2. Check logs
fly logs -a bijou-staging | grep CommandHandler

# Expected: "✅ CommandHandler initialized (enabled=true)"
# If not, flag is off or code not deployed
```

**Fix:**
```bash
fly secrets set ENABLE_BIJOU_COMMANDS=true -a bijou-staging
fly apps restart bijou-staging
```

---

### Limits Not Enforced

**Symptom:** Freemium users can send > 100 messages

**Check:**
```bash
# 1. Feature flag enabled?
fly secrets list -a bijou-staging | grep ENABLE_USAGE_LIMITS

# 2. Check database
# Query usage_tracking table
```

**Fix:**
```bash
fly secrets set ENABLE_USAGE_LIMITS=true -a bijou-staging
fly apps restart bijou-staging
```

---

### Reports Not Sending

**Symptom:** Daily/weekly reports not received

**Check:**
```bash
# 1. Feature flags
fly secrets list -a bijou-staging | grep REPORT

# 2. Check time
# Reports send at REPORT_HOUR (default 9 AM server time)

# 3. Check logs
fly logs -a bijou-staging | grep ReportingEngine
```

**Fix:**
```bash
# Enable reports
fly secrets set ENABLE_AUTO_REPORTS=true -a bijou-staging
fly secrets set ENABLE_DAILY_REPORTS=true -a bijou-staging

# Set correct timezone hour
fly secrets set REPORT_HOUR=9 -a bijou-staging

fly apps restart bijou-staging
```

---

### Tenant Isolation Issues

**Symptom:** Tenant A sees Tenant B's data

**This is CRITICAL - data breach!**

**Check:**
```sql
-- Verify all queries include tenant_id filter
SELECT * FROM conversations WHERE tenant_id = ?

-- Check for missing tenant_id
SELECT COUNT(*) FROM conversations WHERE tenant_id IS NULL;
```

**Fix:**
```bash
# Emergency: Disable multi-tenant
fly secrets set ENABLE_MULTI_TENANT=false -a bijou-staging

# Investigate and fix query
# Re-enable after fix verified
```

---

## 📚 NEXT STEPS

### Completed (Phase 1)

- ✅ Pricing engine with 4 tiers
- ✅ Command handler (@bijou, /)
- ✅ Tenant manager (multi-tenant isolation)
- ✅ Reporting engine (daily/weekly/monthly)
- ✅ Feature flags for safe rollout
- ✅ Usage tracking and limits

### In Progress (Phase 2)

- 🚧 Function calling (AI-driven tool orchestration)
- 🚧 Human handover queue system
- 🚧 Gemini retry logic with exponential backoff
- 🚧 Enhanced memory (semantic search, reminders)

### Planned (Phase 3)

- 📋 Client onboarding wizard
- 📋 Analytics dashboard (web UI)
- 📋 Billing integration (Stripe)
- 📋 API access for Pro/Enterprise
- 📋 Webhooks for integrations

### Future (Phase 4)

- 📋 White-label branding
- 📋 Multi-agent teams
- 📋 Custom model fine-tuning
- 📋 BI integrations (Looker, Tableau)
- 📋 Mobile app (React Native)

---

## 🎓 BEST PRACTICES

1. **Always use feature flags** - Deploy with flags OFF, enable gradually
2. **Test in staging first** - Never test SaaS limits on production
3. **Monitor usage daily** - Catch abuse or bugs early
4. **Respect data isolation** - Never query without tenant_id filter
5. **Graceful degradation** - If limits fail, log and allow (don't block users)
6. **Clear upgrade messaging** - Make it easy to upgrade when limits hit
7. **Track everything** - Metrics drive product decisions
8. **Report send time matters** - Use local timezone, not UTC
9. **Emergency rollback ready** - Can disable all SaaS features in 30 seconds
10. **Document changes** - Update AGENT.md when adding features

---

## 🔐 SECURITY NOTES

### Multi-Tenant Security

- **Row-level security (RLS)** in Supabase enforces tenant isolation
- Every query MUST filter by `tenant_id`
- Owner JID verified before admin commands
- API keys never exposed to clients

### Rate Limiting

Beyond subscription limits, also implement:
- IP-based rate limiting (anti-abuse)
- Exponential backoff for API calls
- Circuit breaker for external services

### Data Privacy

- GDPR compliance: data export and deletion
- Memory retention per tier
- Audit logs for sensitive operations
- Encryption at rest (Supabase default)

---

## 📞 SUPPORT

### For Development Issues:

1. Check this AGENT.md first
2. Check root `/AGENT.md` for system overview
3. Check `/packages/bijou-core/AGENT.md` for core app
4. Review logs: `fly logs -a bijou-staging`
5. Check Supabase dashboard for data

### For Production Issues:

1. Check feature flags: `fly secrets list -a bijou-staging`
2. Verify deployment: `fly status -a bijou-staging`
3. Emergency rollback: Set all ENABLE_* flags to false
4. Monitor errors in logs
5. Contact support if data breach suspected

---

**Last Updated:** 2026-01-30
**Version:** 1.0.0
**Status:** Phase 1 Complete, Phase 2 In Progress
**Maintained By:** W3J Consulting - Muhammad Nurunnabi (Jewel)

=============================================================================
