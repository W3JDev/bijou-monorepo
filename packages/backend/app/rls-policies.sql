-- RLS Policies for `leads` table
--
-- SECURITY (2026-07-20): `backend/schema.sql:103-104` enabled RLS on the
-- `leads` table but never created any policies. With RLS enabled and no
-- policies, anon/authenticated clients are denied ALL operations. The
-- existing API worked only because every Supabase client is constructed
-- with the service-role key, which bypasses RLS. This migration adds the
-- policies that make the security posture explicit and auditable.
--
-- See audit-report.md finding #4.

-- ============================================================================
-- 1. Enable RLS (idempotent)
-- ============================================================================
alter table leads enable row level security;

-- ============================================================================
-- 2. Allow anonymous INSERT for lead capture
--    (The public form on mybijou.xyz / app.mybijou.xyz creates leads.)
--    All other operations (SELECT, UPDATE, DELETE) are denied for anon.
-- ============================================================================
drop policy if exists "leads_anon_insert" on leads;
create policy "leads_anon_insert"
  on leads
  for insert
  to anon, authenticated
  with check (true);

-- ============================================================================
-- 3. INSERT/UPDATE/SELECT only via service role
--    The service role bypasses RLS by default, but having explicit
--    no-access policies for the other roles documents the intent.
-- ============================================================================
-- (no policy = no access; explicit REVOKE for clarity)
revoke all on leads from anon, authenticated;
grant insert on leads to anon, authenticated;

-- ============================================================================
-- 4. Tighten `leads` table SELECT for authenticated founder role
--    (Uncomment when a founder-authenticated dashboard exists.)
-- ============================================================================
-- drop policy if exists "leads_founder_select" on leads;
-- create policy "leads_founder_select"
--   on leads
--   for select
--   to authenticated
--   using (auth.jwt() ->> 'email' = 'jewel@mybijou.xyz');

-- ============================================================================
-- 5. `short_links` and `link_clicks` should be LOCKED DOWN
--    These tables should only be readable/writable by the service role.
--    If RLS is ever enabled on them, NO anon policies should be created.
-- ============================================================================
alter table short_links enable row level security;
alter table link_clicks enable row level security;
-- (no policies = no anon access)

-- ============================================================================
-- 6. Required cleanup for any existing `short_links` rows whose
--    destination_url is not on the wa.me allowlist. The redirect function
--    now refuses to follow non-allowlist URLs (returns 410 Gone), but
--    delete them to be safe.
-- ============================================================================
-- delete from short_links
-- where destination_url !~* '^https://(wa\.me|www\.wa\.me|api\.whatsapp\.com)/';
