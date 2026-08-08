// scripts/install-webhook-triggers.cjs
// Installs a generic PostHog webhook trigger on the `leads` and `User`
// public tables. On INSERT/UPDATE/DELETE, fires `net.http_post` to
// /api/posthog-bridge. Idempotent — safe to re-run.
//
// Why not use the Supabase dashboard "Database Webhooks"?
//   The Supabase Management API for database webhooks is not currently
//   exposed (404s as of 2026-07-30). The dashboard does it via the
//   `supabase_functions.hooks` table + an internal trigger; we replicate
//   the same shape using pg_net so the bridge gets the row payload on
//   every change.

const { Client } = require('pg');

const pw = process.env.SUPABASE_DB_PASSWORD;
const ref = 'lrwzlujomukzjykafmic';
const conn = `postgresql://postgres:${pw}@db.${ref}.supabase.co:5432/postgres`;

// Bridge URL — must be reachable from the Supabase project.
// We default to the just-deployed Vercel URL. If your real production is
// at https://mybijou.xyz, set BRIDGE_URL in the script env.
const BRIDGE_URL = process.env.BRIDGE_URL || 'https://bijou-landing.vercel.app/api/posthog-bridge';
const INTERNAL_TOKEN = process.env.INTERNAL_API_TOKEN;

if (!INTERNAL_TOKEN) {
  console.error('Set INTERNAL_API_TOKEN in the env before running this.');
  process.exit(1);
}

const SQL = `
  -- 1. Generic trigger function: POST the row to the bridge endpoint.
  CREATE OR REPLACE FUNCTION public.posthog_webhook_fire()
  RETURNS TRIGGER
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path = public, extensions
  AS $$
  DECLARE
    payload jsonb;
    target_table text := TG_TABLE_NAME;
    op text := lower(TG_OP);
    safe_record jsonb;
    safe_old jsonb;
  BEGIN
    -- Build a minimal, non-sensitive payload.
    safe_record := case when TG_OP = 'DELETE' then null else to_jsonb(NEW) end;
    safe_old    := case when TG_OP = 'DELETE' then to_jsonb(OLD) when TG_OP = 'UPDATE' then to_jsonb(OLD) else null end;

    -- Strip password / secret columns if present
    safe_record := safe_record - 'password' - 'password_hash' - 'encrypted_password';
    safe_old    := safe_old    - 'password' - 'password_hash' - 'encrypted_password';

    payload := jsonb_build_object(
      'type',       op,
      'table',      target_table,
      'record',     safe_record,
      'old_record', safe_old,
      'schema',     TG_TABLE_SCHEMA,
      'at',         to_char(now() at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')
    );

    -- Fire and forget. pg_net queues the request and returns immediately,
    -- so the user-facing INSERT/UPDATE is not blocked on the network.
    -- Signature (pg_net 0.19+): http_post(url, body jsonb, params jsonb, headers jsonb, timeout int) → bigint
    PERFORM net.http_post(
      url     := '${BRIDGE_URL}',
      body    := payload,
      params  := '{}'::jsonb,
      headers := jsonb_build_object(
        'Content-Type',     'application/json',
        'X-Internal-Token', '${INTERNAL_TOKEN}'
      ),
      timeout_milliseconds := 5000
    );

    RETURN coalesce(NEW, OLD);
  END;
  $$;

  -- 2. Drop existing triggers if present (idempotent)
  DROP TRIGGER IF EXISTS posthog_webhook_leads_trg ON public.leads;
  DROP TRIGGER IF EXISTS posthog_webhook_user_trg   ON public."User";

  -- 3. Attach AFTER INSERT/UPDATE/DELETE triggers
  CREATE TRIGGER posthog_webhook_leads_trg
  AFTER INSERT OR UPDATE OR DELETE ON public.leads
  FOR EACH ROW EXECUTE FUNCTION public.posthog_webhook_fire();

  CREATE TRIGGER posthog_webhook_user_trg
  AFTER INSERT OR UPDATE OR DELETE ON public."User"
  FOR EACH ROW EXECUTE FUNCTION public.posthog_webhook_fire();
`;

(async () => {
  const c = new Client({ connectionString: conn, ssl: { rejectUnauthorized: false } });
  await c.connect();
  try {
    await c.query('BEGIN');
    await c.query(SQL);
    await c.query('COMMIT');
    console.log('✅ Triggers installed.');
    console.log('   leads        → public.posthog_webhook_leads_trg');
    console.log('   User         → public.posthog_webhook_user_trg');
    console.log('   bridge URL   →', BRIDGE_URL);
  } catch (e) {
    await c.query('ROLLBACK');
    console.error('❌ Install failed:', e.message);
    process.exit(1);
  } finally {
    await c.end();
  }
})();
