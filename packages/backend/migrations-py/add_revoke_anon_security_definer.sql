-- P0: revoke anon/authenticated EXECUTE on SECURITY DEFINER functions
-- ============================================================================
-- 2026-09-06. Found by running Supabase's own advisors against the live project
-- and confirming the exploit path end to end.
--
-- THE HOLE
-- RLS was hardened so service_role is the only role that reads or writes
-- (ops/_fix_rls_v6.js). That holds for tables — verified, as anon:
--     GET /rest/v1/tenants?select=id        -> 200  []
--     GET /rest/v1/conversations?...        -> 200  []
--
-- But 14 SECURITY DEFINER functions in `public` were EXECUTE-able by anon and
-- authenticated. A SECURITY DEFINER function runs as its owner and therefore
-- BYPASSES RLS, and PostgREST exposes every non-trigger function in an exposed
-- schema at /rest/v1/rpc/<name>. So the functions were a tunnel straight
-- through RLS, reachable with the PUBLIC anon key that ships in every browser.
--
-- Confirmed, as anon, against production:
--     POST /rest/v1/rpc/get_tenant_daily_sent_count
--          {"p_tenant_id":"<another tenant's uuid>"}   -> 200, returned a value
--
-- Postgres grants EXECUTE to PUBLIC on every new function by default, and
-- anon/authenticated inherit from PUBLIC — so this happens silently whenever
-- someone adds a function, without any explicit GRANT.
--
-- WORST OFFENDERS
--   search_knowledge(...)            returns TABLE(id, title, CONTENT, ...) —
--                                    cross-tenant knowledge-base exfiltration
--   get_contact_last_campaign(uuid)  returns another tenant's campaign history
--   calculate_campaign_stats(uuid)   returns another tenant's campaign metrics
--   count_monthly_conversations(...) returns another tenant's volume
--   get_tenant_daily_sent_count(...) returns another tenant's send volume
--   increment_contact_message(...)   WRITES to another tenant's contact counters
--   cleanup_expired_onboarding_sessions()  DELETES rows
--   cleanup_expired_qr_sessions()          DELETES rows
--   expire_old_onboarding_sessions()       mutates rows
--   rls_auto_enable()                      event-trigger function
--
-- WHY THIS IS SAFE TO APPLY
-- Nothing calls these with the anon key. Every .rpc() call in the codebase goes
-- through the service-role client, and service_role keeps EXECUTE. Verified:
--     grep -rn "\.rpc(" packages/ --include=*.py --include=*.js --include=*.html
-- returns only service-role call sites, plus increment_click_count, which was
-- already correctly NOT granted to anon.
--
--
-- EXCLUSION: can_view_user(uuid, uuid)  — added 2026-09-06, before applying
-- It is SECURITY DEFINER and anon-executable like the rest, but it is also
-- CALLED FROM INSIDE four RLS policies that target the `authenticated` role:
--     agent_connections.agent_connections_select
--     calendar_events."Users can view own calendar events"
--     drive_documents."Users can view accessible drive docs"
--     email_summaries."Users can view own emails"
-- all of the form:  (user_id = auth.uid()) OR can_view_user(auth.uid(), user_id)
--
-- A policy expression is evaluated with the privileges of the QUERYING role,
-- not the policy author's. Revoking EXECUTE from `authenticated` therefore does
-- not make those tables return fewer rows — it makes them raise
--     ERROR: permission denied for function can_view_user
-- on every authenticated SELECT. That is a louder failure than the hole it
-- would close, and the function itself returns only a boolean about a
-- viewer/target pair; it is a predicate, not an exfiltration tunnel like
-- search_knowledge. Left granted deliberately.
--
-- Verified before excluding:
--   SELECT ... FROM pg_policies WHERE qual ~ 'can_view_user'   -> the 4 rows above
--
-- Reversible: GRANT EXECUTE ... TO anon, authenticated puts it back.
-- ============================================================================

DO $$
DECLARE
  fn record;
  n int := 0;
BEGIN
  FOR fn IN
    SELECT p.oid,
           quote_ident(p.proname) AS name,
           pg_get_function_identity_arguments(p.oid) AS args
    FROM pg_proc p
    JOIN pg_namespace ns ON ns.oid = p.pronamespace
    WHERE ns.nspname = 'public'
      AND p.prosecdef                       -- SECURITY DEFINER only
      AND (has_function_privilege('anon', p.oid, 'EXECUTE')
        OR has_function_privilege('authenticated', p.oid, 'EXECUTE'))
      -- See EXCLUSION note in the header: called from inside RLS policies.
      -- current_tenant_id: same reason, found 2026-09-26 — it is referenced by
      -- 21 PUBLIC-role policies (tenants, messages, conversations, ...).
      -- Revoking it turns anon's empty [] into "permission denied" errors.
      -- It returns only the caller's own tenant id, so it is not a tunnel.
      AND p.proname NOT IN ('can_view_user', 'current_tenant_id')
  LOOP
    -- Revoke from PUBLIC as well. Revoking only from anon/authenticated leaves
    -- the inherited PUBLIC grant in place and the function stays callable.
    EXECUTE format('REVOKE ALL ON FUNCTION public.%s(%s) FROM PUBLIC, anon, authenticated',
                   fn.name, fn.args);
    EXECUTE format('GRANT EXECUTE ON FUNCTION public.%s(%s) TO service_role',
                   fn.name, fn.args);
    n := n + 1;
  END LOOP;
  RAISE NOTICE 'revoked anon/authenticated EXECUTE on % SECURITY DEFINER function(s)', n;
END
$$;

-- Stop the same hole reopening on the next function someone adds. Postgres
-- grants EXECUTE to PUBLIC by default; this changes the default for functions
-- created by postgres and supabase_admin in this schema from here on.
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- Verify: this must return zero rows after the migration.
--   SELECT p.proname
--   FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
--   WHERE n.nspname='public' AND p.prosecdef
--     AND p.proname NOT IN ('can_view_user', 'current_tenant_id')
--     AND (has_function_privilege('anon', p.oid, 'EXECUTE')
--       OR has_function_privilege('authenticated', p.oid, 'EXECUTE'));
