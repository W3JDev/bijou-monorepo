# Bijou SaaS – Architecture Plan

**Document:** CPO & Senior Solutions Architect  
**Date:** February 03, 2026 (Updated)  
**Status:** 🟢 Implemented & Deployed to Staging  
**Deployment:** https://bijou-staging.fly.dev

> **✅ IMPLEMENTATION STATUS:** Core architecture successfully deployed. Agent management, multi-tenancy, and dashboard fully operational.

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           BIJOU SAAS ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────────┐ │
│  │   WhatsApp   │     │   Stripe     │     │   Self-Serve Dashboard (Future)   │ │
│  │   (Users)    │     │   (Payments) │     │   app.bijou.ai                    │ │
│  └──────┬───────┘     └──────┬───────┘     └──────────────┬───────────────────┘ │
│         │                    │                            │                      │
│         ▼                    ▼                            ▼                      │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                     WHATSAPP BRIDGE (Go)                                  │   │
│  │  - Single/multi-session                                                   │   │
│  │  - Webhook → Bijou API (POST /webhook/message)                            │   │
│  │  - Media download: GET /api/media/{id}?chat_jid=...                       │   │
│  └──────────────────────────────────┬───────────────────────────────────────┘   │
│                                     │                                            │
│                                     ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                     BIJOU CORE (Python / FastAPI)                         │   │
│  │  - One codebase, N tenants                                                │   │
│  │  - TenantRouter → ClientConfig → PersonaEngine → ToolOrchestrator         │   │
│  │  - Gemini 2.5 Flash (text + vision + function calling)                    │   │
│  └──────────────────────────────────┬───────────────────────────────────────┘   │
│                                     │                                            │
│         ┌───────────────────────────┼───────────────────────────┐                │
│         ▼                           ▼                           ▼                │
│  ┌─────────────┐            ┌──────────────┐            ┌──────────────┐        │
│  │  Supabase   │            │  Redis       │            │  Cloud       │        │
│  │  PostgreSQL │            │  (optional   │            │  Storage     │        │
│  │  - tenants  │            │   cache)     │            │  (media)     │        │
│  │  - configs  │            └──────────────┘            └──────────────┘        │
│  │  - messages │                                                                 │
│  └─────────────┘                                                                 │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Deployment Strategy (Solo Founder)

### Recommended: SaaS Monolith + Single Region

| Approach                   | Pros                           | Cons                    | Verdict       |
| -------------------------- | ------------------------------ | ----------------------- | ------------- |
| **Docker Swarm**           | Native Docker, rolling updates | Multi-node complexity   | Overkill      |
| **Kubernetes**             | Industry standard              | High ops burden         | No            |
| **SaaS Monolith**          | One deploy, simple, low cost   | Single point of failure | **Yes**       |
| **Serverless (Cloud Run)** | Auto-scale, pay-per-use        | Cold starts, state      | Backup option |

**Recommendation:** Deploy Bijou as a **single monolith** on Render, Railway, or Fly.io.

- **Update flow:** Push to `main` → CI/CD builds → deploy new container.
- **All tenants** get the new code in one deploy.
- **Rollback:** Revert commit or redeploy previous image.

### Update Propagation

```
Git push (main)
    │
    ▼
GitHub Actions (ci-cd.yml)
    │
    ├─► Build Docker image
    ├─► Run tests
    └─► Deploy to Render/Railway/Fly
              │
              ▼
        Single Bijou container
        serves ALL 50+ clients
```

No per-tenant containers. Configuration (prompt, tools, business name) comes from `ClientConfig` in DB.

---

## 3. Database Schema: ClientConfig

### Purpose

One codebase serves many “vibes”: different prompts, tools, and business rules per tenant.

### Proposed Schema

```sql
-- ClientConfig: Per-tenant AI and behavior configuration
CREATE TABLE IF NOT EXISTS client_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Business Identity
    business_name TEXT NOT NULL,
    business_type TEXT,  -- 'dental', 'retail', 'restaurant', 'healthcare', etc.

    -- System Prompt (dynamic)
    system_prompt_template TEXT NOT NULL,
    system_prompt_variables JSONB DEFAULT '{}',  -- {business_hours, services, etc.}

    -- Persona / Vibe
    persona_name TEXT DEFAULT 'default',
    tone TEXT DEFAULT 'friendly',  -- 'friendly', 'professional', 'casual', 'warm'
    language_default TEXT DEFAULT 'en',
    manglish_level TEXT DEFAULT 'moderate',  -- 'off', 'light', 'moderate', 'heavy'

    -- Tools
    tools_allowed TEXT[] DEFAULT ARRAY['calculator', 'crm', 'calendar'],
    tools_config JSONB DEFAULT '{}',  -- Per-tool settings

    -- Vision
    vision_enabled BOOLEAN DEFAULT true,
    vision_prompts JSONB DEFAULT '{}',  -- {dental: "...", retail: "..."}

    -- Response Strategy
    default_response_style TEXT DEFAULT 'balanced',  -- 'short', 'balanced', 'detailed'
    max_response_tokens INT DEFAULT 500,

    -- Feature Flags
    features JSONB DEFAULT '{"media": true, "escalation": true}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id)
);

CREATE INDEX idx_client_configs_tenant ON client_configs(tenant_id);
```

### Example Row

```json
{
  "tenant_id": "uuid-...",
  "business_name": "Smile Dental Clinic",
  "business_type": "dental",
  "system_prompt_template": "You are {{business_name}}'s AI assistant...",
  "persona_name": "dental_receptionist",
  "tone": "warm",
  "manglish_level": "moderate",
  "tools_allowed": ["calculator", "crm", "calendar", "image"],
  "vision_prompts": {
    "dental": "Describe this dental/oral image in lay terms. Note teeth, gums, visible issues.",
    "general": "Describe this image briefly."
  },
  "default_response_style": "short",
  "max_response_tokens": 300
}
```

---

## 4. Tech Stack Recommendation

| Layer        | Technology                | Rationale                                     |
| ------------ | ------------------------- | --------------------------------------------- |
| **AI**       | Gemini 2.5 Flash          | Vision, function calling, cost-effective      |
| **Backend**  | Python + FastAPI          | Existing bijou.py, async, OpenAPI             |
| **Database** | Supabase (PostgreSQL)     | Already integrated, RLS, realtime             |
| **Cache**    | Optional Redis            | For config caching; skip initially            |
| **Queue**    | None (sync)               | Add Celery/Redis only if needed               |
| **Storage**  | Supabase Storage or S3    | Media, documents                              |
| **Hosting**  | Render / Railway / Fly.io | Simple, cheap, CI/CD                          |
| **Bridge**   | Go (whatsmeow)            | Keep existing; extend for multi-session later |

---

## 5. Data Flow (Request Path)

```
1. WhatsApp message arrives at Bridge
2. Bridge sends webhook to Bijou: POST /webhook/message
   Body: { id, chat_jid, sender, content, media_type, filename, tenant_id? }
3. Bijou:
   a. Resolve tenant_id (from body or chat_jid → tenants lookup)
   b. Load ClientConfig (with caching)
   c. If media: MediaHandler.download() → ToolOrchestrator.process_media()
   d. Build prompt with PersonaEngine (system + user)
   e. Call Gemini (with tools if tools_allowed)
   f. If functionCall: execute tools, re-call Gemini (loop)
   g. Post-process (Humanizer, chunking)
   h. Send response via Bridge POST /api/send
4. Log to Supabase (messages, usage_tracking)
```

---

## 6. Multi-Tenancy: Tenant Resolution

### Option 1: Webhook includes tenant_id (preferred)

Bridge looks up `chat_jid` or sender in `whatsapp_instances` / config and adds `tenant_id` to webhook payload.

### Option 2: Bijou infers from chat_jid

```python
def resolve_tenant(chat_jid: str, sender: str) -> Optional[UUID]:
    # Check tenants.whatsapp_number or whatsapp_instances
    # Match chat_jid prefix (e.g. 60123456789@s.whatsapp.net)
    phone = extract_phone(chat_jid)
    return db.query("SELECT tenant_id FROM tenants WHERE whatsapp_number LIKE ?", f"%{phone}%")
```

### Option 3: Single-tenant MVP

One `DEFAULT_TENANT_ID` env var; all traffic goes to that tenant until multi-bridge is ready.

---

## 7. Security Considerations

- **API keys**: Per-tenant keys in `client_configs` or env; never in logs.
- **RLS**: Supabase RLS on all tenant-scoped tables.
- **Webhook secret**: Verify `X-Webhook-Signature` or shared secret.
- **Rate limiting**: Per tenant_id to avoid abuse.
- **Data isolation**: All queries filtered by `tenant_id`.

---

## 8. Scaling Path (Future)

| Stage  | Tenants                               | Approach             |
| ------ | ------------------------------------- | -------------------- |
| 0–50   | Single monolith, single bridge        | Current plan         |
| 50–200 | Add Redis cache for ClientConfig      | Reduce DB load       |
| 200+   | Multi-region bridge (one per region)  | Geolocation          |
| 500+   | Read replicas, worker queue for async | When sync limits hit |

---

_Next: See `PERSONA_ENGINEERING.md` for system prompt and persona design._
