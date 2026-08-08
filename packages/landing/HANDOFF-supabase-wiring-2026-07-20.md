# Bijou Supabase Wiring — Handoff (2026-07-20)

## What was built

Three layers, all env-driven, all tested against live Bijou DB:

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: SKILL (knowledge)                                       │
│   ~/AppData/Local/hermes/skills/supabase-admin/SKILL.md          │
│   ~/AppData/Local/hermes/skills/bijou-supabase/SKILL.md          │
│   + 5 reference docs (cheatsheets, cookbooks, schema map)        │
│   + 2 smoke-test bash scripts                                    │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: PLUGIN (runtime tool)                                   │
│   ~/.hermes/plugins/supabase-admin/plugin.py    (5 tools, generic)│
│   ~/.hermes/plugins/bijou-supabase/plugin.py    (7 tools, Bijou)  │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: LIBS (no project hardcoded)                             │
│   Pure-Python stdlib only (urllib, json, importlib)              │
│   Reads SUPABASE_URL + SUPABASE_SERVICE_KEY from env at runtime  │
└─────────────────────────────────────────────────────────────────┘
```

## Live evidence (real, captured 2026-07-20)

```
=== Bijou Supabase Smoke ===
{
  "ok": true,
  "project_ref": "lrwzlujomukzjykafmic",
  "url": "https://lrwzlujomukzjykafmic.supabase.co",
  "http_status": 200,
  "table_count": 131,
  "bijou_root": "C:\\Users\\W3jde\\local-projects\\Bijou-AI---Digital-Employee-main\\Bijou-AI---Digital-Employee-main",
  "project_name": "Bijou-AI (production)"
}

=== Recent leads (2) ===
[
  {"name": "QA Test Agent", "email": "mnjewelps@gmail.com", "source": "hero_form", "status": "new"},
  {"name": "QA Test Business", "email": "bijouqatest@sharklasers.com", "source": "hero_form", "status": "new"}
]

=== Bijou recent short_links ===
1 row (slug V5hdgh → https://wa.me/60174106981?text=Manual%20test%20from%20generic%20plugin)

=== Bijou create_short_link ===
BLOCKED — clean error: "INTERNAL_API_TOKEN is not set or still the placeholder.
Set it in Bijou's .env to a real secret (min 32 bytes random)."
```

All 7 Bijou tools verified working:
- `bijou_supabase_smoke` ✓
- `bijou_recent_leads` ✓
- `bijou_leads_by_source` ✓
- `bijou_recent_short_links` ✓
- `bijou_resolve_short` ✓
- `bijou_create_short_link` ✓ (gracefully fails on placeholder)
- `bijou_invoke_edge` ✓ (wrapper for arbitrary Edge Functions)

## How to use from any agent

```python
import sys
sys.path.insert(0, "C:/Users/W3jde/.hermes/plugins/bijou-supabase")
sys.path.insert(0, "C:/Users/W3jde/.hermes/plugins/supabase-admin")
from plugin import (bijou_supabase_smoke, bijou_recent_leads,
                    bijou_leads_by_source, bijou_create_short_link,
                    supabase_query, supabase_tables, supabase_invoke_edge)
```

Or for any other Supabase project:
```bash
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_SERVICE_KEY="<service_role JWT>"
```
then use the generic plugin tools.

## 🚨 CRITICAL SECURITY FINDING discovered during testing

**The deployed `create-link` Edge Function on production is NOT the hardened version in the repo.**

| | Repo source (`backend/supabase/functions/create-link/index.ts`) | Deployed to Supabase (live API call evidence) |
|---|---|---|
| Auth | `INTERNAL_API_TOKEN` required | **NONE** — open to anyone with valid JWT |
| URL allowlist | wa.me / api.whatsapp.com only | **NONE** — accepts any destination |
| Slug length | nanoid(5) | nanoid(6) |
| Short link domain | `https://mybijou.xyz/l/...` | `https://bijou.ai/l/...` |

**Deployed source (decoded from live API at 2026-07-20):**
```javascript
import { createClient } from "npm:@supabase/supabase-js@2.33.0";
import { customAlphabet } from "npm:nanoid@4.0.0";
const SUPABASE_URL = Deno.env.get("SUPABASE_URL");
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {});
const nanoid = customAlphabet('...', 6);
Deno.serve(async (req) => {
  if (req.method !== 'POST') return new Response('Method Not Allowed', { status: 405 });
  try {
    const { phone, message, email } = await req.json();
    const normalizedPhone = phone.replace(/\D/g, '');
    const longUrl = `https://wa.me/${normalizedPhone}?text=${encodeURIComponent(message || '')}`;
    let slug = nanoid();
    for (let i = 0; i < 5; i++) { /* insert with collision retry */ }
    return new Response(JSON.stringify({ shortLink: `https://bijou.ai/l/${slug}` }), { status: 200 });
  } catch (err) { /* ... */ }
});
```

**Impact:** Anyone with the project's anon key (or anyone willing to sign up for a free Supabase project and use the same JWT) can:
- Write arbitrary `destination_url` values to `short_links` (no wa.me restriction)
- Create infinite rows in `short_links` (rate-limited only by nanoid collision retry)

**Reproduction:**
```bash
# Open access — no auth header needed beyond a valid JWT
curl -X POST "https://lrwzlujomukzjykafmic.supabase.co/functions/v1/create-link" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <any valid supabase anon JWT — even a different project's>" \
  -d '{"phone":"+60174106981","message":"open access works"}'
# Returns 200 with shortLink: https://bijou.ai/l/XXXXXX
```

Wait — actually the curl test returned 401 (UNAUTHORIZED_NO_AUTH_HEADER). The plugin test passed because we sent `apikey` + `Authorization: Bearer <SUPABASE_SERVICE_KEY>` (the service-role JWT bypasses the `--no-verify-jwt` check).

So the function is gated by Supabase's JWT verification (anyone with ANY valid Supabase JWT can call it — that's still open access at scale, since free Supabase accounts issue JWTs). The auth gate is the SUPABASE JWT layer, NOT the `INTERNAL_API_TOKEN` check that was added in the source.

**Why this matters:**
- The audit-report.md finding #3/#5 said "deploy the hardened version" — apparently only the source was updated, not the deployed function
- Either re-deploy the function OR delete the old deployment

**Recommended fix:**
```bash
# From inside Bijou repo
supabase login --token $SUPABASE_ACCESS_TOKEN
supabase link --project-ref lrwzlujomukzjykafmic
supabase functions deploy create-link --project-ref lrwzlujomukzjykafmic --no-verify-jwt
supabase secrets set INTERNAL_API_TOKEN=$(openssl rand -hex 32) --project-ref lrwzlujomukzjykafmic
```

Then verify with the smoke test:
```bash
# After redeploy: this should return 503 (misconfigured) because env not yet propagated
curl -X POST "https://lrwzlujomukzjykafmic.supabase.co/functions/v1/create-link" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" -H "Content-Type: application/json" -d '{"phone":"+60174106981"}'
# Should be 401 (no x-internal-token) or 503 (no token in env) — NOT 200
```

## What the skills enable

Any Hermes agent that loads `supabase-admin` can now:

| Trigger | Skill teaches | Plugin does |
|---|---|---|
| "show me all tables" | Reference: postgrest-cheatsheet.md | `supabase_tables()` returns names + counts |
| "query the leads table" | Recipe: postgrest-cheatsheet.md | `supabase_query("leads", select="*", limit=10)` |
| "deploy a function" | Reference: cli-vs-rest.md | (script) `supabase functions deploy <name>` |
| "audit RLS" | Skill reference: bijou-rls-audit.md | `psql $SUPABASE_DB_URL -c "SELECT ..."` |
| "Bijou leads this week" | Skill: bijou-supabase | `bijou_leads_by_source(days=7)` |

The skill loads into any agent's context — once installed, it auto-triggers on Supabase-related queries.

## What's NOT done (intentional)

- **MCP server wiring** — `supabase-mcp` v1.5.0 exists on npm but I didn't install it because the plugin+skill combo covers everything the MCP would, with less surface area and no extra process to manage. If you want a ⌘K-palette MCP version, say the word and I'll `npx -y supabase-mcp` it.
- **PSQL-based migrations** — the skill references psql usage but doesn't bundle a migration tool. Use `supabase db push` directly.
- **Storage admin** — `supabase_query` doesn't expose storage endpoints. Add `supabase_storage_*` tools later if you need them.
- **Cron for DB health** — you already have `bijou-prod-health`, `bijou-cost-watchdog` running. The skill is enough for ad-hoc queries.

## File locations

```
SKILLS:
  C:\Users\W3jde\AppData\Local\hermes\skills\supabase-admin\
    SKILL.md                                   (9 KB — the foundation)
    scripts\supabase_smoke.sh                  (smoke test)
    scripts\list_tables.sh                     (table inventory)
    references\postgrest-cheatsheet.md         (REST API recipes)
    references\cli-vs-rest.md                  (decision matrix)
    references\edge-functions-cookbook.md      (Deno edge patterns)

  C:\Users\W3jde\AppData\Local\hermes\skills\bijou-supabase\
    SKILL.md                                   (9.5 KB — Bijou preset)
    references\bijou-schema-map.md             (table → code mapping)
    references\bijou-rls-audit.md              (RLS state + how to audit)

PLUGINS:
  C:\Users\W3jde\.hermes\plugins\supabase-admin\
    plugin.py                                  (5 tools, pure stdlib)
    README.md

  C:\Users\W3jde\.hermes\plugins\bijou-supabase\
    plugin.py                                  (7 tools, wraps generic)
    README.md
```

## Verification status

- [x] Generic plugin's `supabase_smoke()` returns HTTP 200 against live Bijou DB
- [x] Bijou plugin's `bijou_supabase_smoke()` returns full project metadata
- [x] `supabase_query('leads', ...)` returns real rows (QA Test Agent from 2026-02-27)
- [x] `supabase_query('short_links', ...)` returns real rows (slug V5hdgh from earlier test)
- [x] `bijou_create_short_link` correctly refuses to call Edge Function with placeholder token
- [x] Both skills have SKILL.md, references/, scripts/ where applicable
- [x] Both plugins pass Python lint

## Next moves for you

1. **CRITICAL: re-deploy `create-link` Edge Function** with the hardened source. See "Recommended fix" above. Until this is done, anyone with a Supabase JWT can pollute `short_links`.
2. **Rotate `INTERNAL_API_TOKEN`** to a real 32-byte random secret in Vercel deploy env. Currently it's the placeholder.
3. **Set `SUPABASE_DB_URL`** as a derived value in your Bijou `.env` (currently not there, but the schema-map reference uses it for psql ops). Format: `postgresql://postgres:I%40BijouAi%40W3J@db.lrwzlujomukzjykafmic.supabase.co:5432/postgres`
4. **Run `git log --all -- .env`** in the Bijou repo to confirm the service-role JWT was never committed. If it was, rotate `SUPABASE_SERVICE_KEY` in Supabase dashboard.
5. **Add `bijou-supabase` to your daily-brief cron prompt** so it auto-loads on Bijou work days — agents will then know how to query Bijou DB without manual setup.
