# Supabase Linter Fix Report — Bijou Project

**Date:** 2026-08-10
**Project ref:** `lrwzlujomukzjykafmic`
**Tier:** Free (Pro features like HIBP unavailable)

## Summary

| Finding | Count | Status |
|---|---|---|
| A. Function Search Path Mutable | 25 (22 public + 3 stripe) | **Fixed** |
| B. Multiple Permissive Policies | 7 policy-groups (3 safe merges) | **Fixed (conservative)** |
| C. Duplicate Indexes | 21 (4 partial-index pairs intentionally kept) | **Fixed** |
| D. PUBLIC Can Execute SECURITY DEFINER | 18 (of 19; 1 was already clean) | **Fixed** |
| E. Email Bounce Backs (BijouAi.xyz) | 4 warnings | **Manual — Postmark side** |
| PostgREST reload | — | **Done** (`NOTIFY pgrst, 'reload schema'`) |

## A. Function Search Path Mutable (25/25 fixed)

Set `search_path = public, pg_temp` on every flagged function. Extension functions in `stripe` schema (`gbt_*`, `_dist`, `gbtreekey*`) were **not touched** — they belong to `btree_gist`.

```sql
ALTER FUNCTION public.calculate_campaign_stats(p_campaign_id uuid) SET search_path = public, pg_temp;
ALTER FUNCTION public.calculate_lead_score(lead_data leads) SET search_path = public, pg_temp;
ALTER FUNCTION public.call_bookings_set_scheduled_date() SET search_path = public, pg_temp;
ALTER FUNCTION public.count_monthly_conversations(p_tenant_id uuid, p_month_start timestamp without time zone) SET search_path = public, pg_temp;
ALTER FUNCTION public.create_default_templates() SET search_path = public, pg_temp;
ALTER FUNCTION public.current_tenant_id() SET search_path = public, pg_temp;
ALTER FUNCTION public.get_contact_last_campaign(p_contact_id uuid) SET search_path = public, pg_temp;
ALTER FUNCTION public.get_conversation_threads(p_tenant_id uuid, p_chat_jid text, p_limit integer, p_offset integer) SET search_path = public, pg_temp;
ALTER FUNCTION public.get_tenant_daily_sent_count(p_tenant_id uuid) SET search_path = public, pg_temp;
ALTER FUNCTION public.increment_click_count(row_id bigint) SET search_path = public, pg_temp;
ALTER FUNCTION public.increment_contact_message(p_tenant_id text, p_jid text) SET search_path = public, pg_temp;
ALTER FUNCTION public.is_service_role() SET search_path = public, pg_temp;
ALTER FUNCTION public.update_contacts_updated_at() SET search_path = public, pg_temp;
ALTER FUNCTION public.update_escalation_notifications_updated_at() SET search_path = public, pg_temp;
ALTER FUNCTION public.update_follow_ups_timestamp() SET search_path = public, pg_temp;
ALTER FUNCTION public.update_help_ticket_timestamp() SET search_path = public, pg_temp;
ALTER FUNCTION public.update_jid_mappings_updated_at() SET search_path = public, pg_temp;
ALTER FUNCTION public.update_leads_updated_at_column() SET search_path = public, pg_temp;
ALTER FUNCTION public.update_onboarding_current_step() SET search_path = public, pg_temp;
ALTER FUNCTION public.update_updated_at() SET search_path = public, pg_temp;
ALTER FUNCTION public.update_updated_at_column() SET search_path = public, pg_temp;
ALTER FUNCTION public.update_web_support_ticket_timestamp() SET search_path = public, pg_temp;
ALTER FUNCTION stripe.check_rate_limit(rate_key text, max_requests integer, window_seconds integer) SET search_path = public, pg_temp;
ALTER FUNCTION stripe.set_updated_at() SET search_path = public, pg_temp;
ALTER FUNCTION stripe.set_updated_at_metadata() SET search_path = public, pg_temp;
```

**Note on `posthog_webhook_fire`:** this SECURITY DEFINER function already had `search_path = public, extensions` (preserves access to the `pg_net` extension). It was correctly left alone for finding A but **was** included in finding D.

## B. Multiple Permissive Policies (3 merges)

Conservative policy: only merged policies for the **same role + same command**. Policies for different roles (`public` vs `authenticated`, or `authenticated` vs `service_role`) were kept separate to avoid breaking authorization.

### B.1 `dashboard_views` SELECT — 3 → 1

Dropped:
- `All users can view org views`
- `Creator can view own private views`
- `Dept members can view dept views`

Created (OR-merged):
```sql
CREATE POLICY dashboard_views_select ON public.dashboard_views
  FOR SELECT TO authenticated
  USING (
    visibility = 'org'::text
    OR (visibility = 'private'::text AND created_by = (auth.uid())::text)
    OR (visibility = 'department'::text AND department_id IN (
      SELECT user_profiles.department_id FROM user_profiles WHERE user_profiles.id = auth.uid()
    ))
  );
```

### B.2 `dashboard_views` ALL — 2 → 1 (for `authenticated`)

Dropped (the `Service role full access to dashboard_views` policy is **kept**, different role):
- `Admins can manage all views`
- `Creator can manage own views`

Created (OR-merged):
```sql
CREATE POLICY dashboard_views_all ON public.dashboard_views
  FOR ALL TO authenticated
  USING (
    EXISTS (SELECT 1 FROM user_profiles
            WHERE user_profiles.id = auth.uid()
              AND user_profiles.role = ANY(ARRAY['owner'::text, 'admin'::text]))
    OR created_by = (auth.uid())::text
  )
  WITH CHECK (
    EXISTS (SELECT 1 FROM user_profiles
            WHERE user_profiles.id = auth.uid()
              AND user_profiles.role = ANY(ARRAY['owner'::text, 'admin'::text]))
    OR created_by = (auth.uid())::text
  );
```

### B.3 `agent_connections` SELECT — 2 → 1 (for `authenticated`)

Dropped (the `connections_read` policy on `public` is **kept**, different role):
- `Users can view own agent connections`
- `Department members can view dept agent connections`

Created (OR-merged):
```sql
CREATE POLICY agent_connections_select ON public.agent_connections
  FOR SELECT TO authenticated
  USING (
    user_id = auth.uid()
    OR can_view_user(auth.uid(), user_id)
  );
```

### B.4 Other tables — left as-is (manual decision needed)

These tables have policies for **different roles** (`public` vs `authenticated` or `authenticated` vs `service_role`) on the same command. The linter still flags them as multiple permissive, but merging would change the access semantics. Recommend manual review in a future pass — see *Findings needing manual decision* below.

| Table | Cmd | Policies (different roles) |
|---|---|---|
| `agent_activity` | SELECT | `Users can view activity of own agents` (auth) + `activity_read` (public) |
| `agent_connections` | DELETE | `Users can delete own agent connections` (auth) + `connections_delete` (public) |
| `agent_connections` | UPDATE | `Users can update own agent connections` (auth) + `connections_update` (public) |
| `agent_status` | SELECT | `Users can view status of own agents` (auth) + `status_read` (public) |
| `business_profiles` | ALL | `business_profiles_service_role` (service_role) + `business_profiles_tenant_isolation` (public) |
| `knowledge_base` | ALL | `Service role full access` (service_role) + `tenant_isolation_knowledge` (public) |
| `user_profiles` | UPDATE | `Users can update own profile` (auth) + `profiles_update` (public) |

## C. Duplicate Indexes (21 dropped, 4 partial pairs kept)

Dropped redundant indexes (the UNIQUE index always serves as both constraint and index; for non-unique pairs, kept the older/shorter name).

```sql
DROP INDEX public.idx_api_keys_hash;                  -- kept: api_keys_key_hash_key (UNIQUE)
DROP INDEX public.idx_business_profiles_tenant;       -- kept: unique_tenant_profile (UNIQUE)
DROP INDEX public.idx_call_settings_tenant_id;        -- kept: call_settings_tenant_id_key (UNIQUE)
DROP INDEX public.idx_client_configs_tenant_id;       -- kept: client_configs_tenant_id_key (UNIQUE)
DROP INDEX public.idx_contacts_tenant_jid;            -- kept: contacts_tenant_jid_unique (UNIQUE)
DROP INDEX public.idx_customer_memory_tenant_chat;    -- kept: customer_memory_tenant_id_chat_jid_key (UNIQUE)
DROP INDEX public.idx_device_sessions_device_id;      -- kept: device_sessions_device_id_key (UNIQUE)
DROP INDEX public.idx_email_tokens_token;             -- kept: email_verification_tokens_token_key (UNIQUE)
DROP INDEX public.idx_jid_mappings_tenant_lid;        -- kept: uq_jid_mappings_tenant_lid (UNIQUE)
DROP INDEX public.idx_personas_key;                   -- kept: personas_persona_key_key (UNIQUE)
DROP INDEX public.idx_setup_progress_tenant;          -- kept: tenant_setup_progress_tenant_id_key (UNIQUE)
DROP INDEX public.idx_tenants_slug;                   -- kept: tenants_slug_key (UNIQUE)
DROP INDEX public.idx_tenants_telegram_username;      -- kept: tenants_telegram_username_key (UNIQUE)
DROP INDEX public.idx_tenants_token;                  -- kept: tenants_signup_token_key (UNIQUE)
DROP INDEX public.idx_tenants_whatsapp_number;        -- kept: tenants_whatsapp_number_unique (UNIQUE)
DROP INDEX public.idx_tenants_stripe_customer;        -- kept: idx_tenants_stripe_customer_id
DROP INDEX public.idx_tenants_whatsapp;               -- kept: idx_tenants_whatsapp_jid
DROP INDEX public.idx_vertical_templates_vertical_id; -- kept: vertical_templates_vertical_id_key (UNIQUE)
DROP INDEX public.idx_agent_connections_user_id;      -- kept: idx_agent_connections_user
DROP INDEX public.idx_agent_activity_connection_id;   -- kept: idx_agent_activity_connection
DROP INDEX public.idx_agent_status_connection_id;     -- kept: idx_agent_status_connection
```

### Partial indexes kept (intentional — not duplicates)

These are `WHERE`-clause partial indexes that complement their full counterparts. Dropping them would change query plans.

| Index | Partial predicate | Companion |
|---|---|---|
| `idx_email_templates_tenant_type` | `WHERE (is_active = true)` | `email_templates_tenant_type_unique` (full) |
| `idx_tenant_email_config_tenant_id` | `WHERE (is_active = true)` | `tenant_email_config_tenant_id_key` (full) |
| `idx_follow_ups_pending` | `WHERE (status = 'pending')` | `idx_follow_ups_status` (full) |
| `idx_onboarding_token` | `WHERE (status <> 'completed')` | `onboarding_sessions_pkey` (token) |

The full list of 39 partial indexes in the database is captured in `_linter_postcheck.json` under `indexes_partial_kept`.

## D. PUBLIC Can Execute SECURITY DEFINER Function (18/19 fixed)

`REVOKE EXECUTE ON FUNCTION ... FROM PUBLIC` for every SECURITY DEFINER function that had a `=X/postgres` (PUBLIC) entry in its ACL. `increment_click_count` was already clean (no PUBLIC entry) but is listed for completeness.

```sql
REVOKE EXECUTE ON FUNCTION public.calculate_campaign_stats(p_campaign_id uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.call_bookings_set_scheduled_date() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.can_view_user(viewer_id uuid, target_id uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.cleanup_expired_onboarding_sessions(days_old integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.cleanup_expired_onboarding_sessions() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.cleanup_expired_qr_sessions() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.count_monthly_conversations(p_tenant_id uuid, p_month_start timestamp without time zone) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.current_tenant_id() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.expire_old_onboarding_sessions() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.get_contact_last_campaign(p_contact_id uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.get_tenant_daily_sent_count(p_tenant_id uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.increment_contact_message(p_tenant_id text, p_jid text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.is_service_role() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.posthog_webhook_fire() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.prune_agent_status() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.search_knowledge(query_embedding vector, query_text text, match_threshold double precision, match_count integer, filter_department uuid) FROM PUBLIC;
```

After revoke, the ACL for all 19 functions is:
```
{postgres=X/postgres, anon=X/postgres, authenticated=X/postgres, service_role=X/postgres}
```
— no PUBLIC grant. The Supabase standard roles still have EXECUTE.

**Note on `cleanup_expired_onboarding_sessions`:** this is an overloaded function with both 0-arg and `(days_old integer)` signatures. Both were revoked.

## E. Email Bounce Backs (BijouAi.xyz) — manual

Cannot be fixed via SQL. Actions for the user (in Postmark dashboard):
1. **Clean up bad recipients** — open Postmark → Activity → Bounced, remove or suppress any hard bounces from the `BijouAi.xyz` sender.
2. **Reduce send rate** — drop per-minute cap to a safer value (e.g. 30/min) and warm up the sender reputation.
3. **Use double opt-in** — only send to addresses that confirmed a signup.
4. **Monitor suppression list** — Postmark auto-suppresses after 5 hard bounces; export the list and reconcile against your contacts.

## Findings needing manual decision

1. **B.4 Multiple permissive policies on `public` role vs `authenticated` role** — 7 policy pairs left as-is. The `public` role policies with `auth.uid() = ...` checks are functionally equivalent to `authenticated` policies for non-anonymous requests, but they were intentionally kept separate. Consider renaming the `public` ones to `authenticated` and dropping the duplicates — requires business sign-off.
2. **`tenants` policies** — `service_role_all_tenants` (ALL, public) and `tenant_read_own` (SELECT, public) overlap for `service_role`. Could be consolidated by dropping the SELECT and relying on the ALL. Kept both to avoid behavior change.
3. **C partial indexes** — listed in the JSON dump. All have `WHERE` predicates that are not duplicates of their full counterparts. Kept.

## Verification (post-fix snapshot)

```
functions_total: 25          functions_with_search_path: 25
secdef_total: 19             secdef_clean: 19 (no PUBLIC)
policies_total: 134          policies_same_role_cmd: 0
indexes_total: 476           indexes_dups_remaining: 0
indexes_partial_kept: 39     (intentional, listed in _linter_postcheck.json)
```

Smoke tests through REST API (anon + service_role keys) all returned `200`:
- `is_service_role` (anon) → `false`
- `current_tenant_id` (anon) → `null`
- `get_tenant_daily_sent_count` (anon, dummy uuid) → `0`
- `dashboard_views` SELECT (anon) → `[]` (RLS still blocks)
- `tenants` SELECT (service_role) → `[{...}]`

## Files in this fix

| File | Purpose |
|---|---|
| `ops/_linter_discover.js` | Initial discovery of functions/policies/indexes |
| `ops/_fn_discovery.js` | Function-level discovery (with proconfig + ACL) |
| `ops/_fn_pubexec.js` | SECURITY DEFINER + PUBLIC EXEC check |
| `ops/_fn_acl.js` | Raw proacl dump |
| `ops/_policy_detail.js` | Full policy detail dump |
| `ops/_linter_fix_A_searchpath.js` | Fix A: set search_path on 25 functions |
| `ops/_linter_fix_D_pubexec.js` | Fix D: REVOKE PUBLIC on 18 functions |
| `ops/_linter_fix_B_policies.js` | Fix B: 3 safe policy merges |
| `ops/_linter_fix_C_indexes.js` | Fix C: drop 20 duplicate indexes |
| `ops/_linter_fix_C_indexes2.js` | Fix C cleanup: drop 1 more (idx_tenants_whatsapp_number) |
| `ops/_reload_pgrst.js` | PostgREST schema reload |
| `ops/_verify_A.js` / `_verify_A_v2.js` | Fix A verification |
| `ops/_verify_D.js` / `_verify_D_v2.js` | Fix D verification |
| `ops/_linter_postcheck.js` | Full post-fix verification |
| `ops/_smoke_test.js` | REST API smoke test |
| `ops/_linter_discovery.json` | Raw discovery dump |
| `ops/_fn_discovery.json` | Raw function dump |
| `ops/_fn_combined.json` | Function dump with public_execute |
| `ops/_linter_postcheck.json` | Post-fix summary JSON |

## Cannot fix via API

None of the linter findings required Pro-tier features. All were fixable via the Management API.
