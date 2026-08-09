// Verify D: re-check PUBLIC is gone from ACL on all 18 SECURITY DEFINER functions
const ACCESS = '${SUPABASE_ACCESS_TOKEN}';
const REF    = 'lrwzlujomukzjykafmic';

async function execSql(sql) {
  const r = await fetch(`https://api.supabase.com/v1/projects/${REF}/database/query`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${ACCESS}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: sql }),
  });
  return { status: r.status, body: await r.text() };
}

const FNS = [
  ['public', 'calculate_campaign_stats',          'p_campaign_id uuid'],
  ['public', 'call_bookings_set_scheduled_date',  ''],
  ['public', 'can_view_user',                     'viewer_id uuid, target_id uuid'],
  ['public', 'cleanup_expired_onboarding_sessions', 'days_old integer'],
  ['public', 'cleanup_expired_onboarding_sessions', ''],
  ['public', 'cleanup_expired_qr_sessions',       ''],
  ['public', 'count_monthly_conversations',       'p_tenant_id uuid, p_month_start timestamp without time zone'],
  ['public', 'current_tenant_id',                 ''],
  ['public', 'expire_old_onboarding_sessions',    ''],
  ['public', 'get_contact_last_campaign',         'p_contact_id uuid'],
  ['public', 'get_tenant_daily_sent_count',       'p_tenant_id uuid'],
  ['public', 'handle_new_user',                   ''],
  ['public', 'increment_contact_message',         'p_tenant_id text, p_jid text'],
  ['public', 'is_service_role',                   ''],
  ['public', 'posthog_webhook_fire',              ''],
  ['public', 'prune_agent_status',                ''],
  ['public', 'rls_auto_enable',                   ''],
  ['public', 'search_knowledge',                  'query_embedding vector, query_text text, match_threshold double precision, match_count integer, filter_department uuid'],
];

(async () => {
  // Use a single query with array
  const r = await execSql(`
    SELECT n.nspname AS schema, p.proname AS name,
           pg_get_function_identity_arguments(p.oid) AS args,
           p.proacl::text AS acl,
           p.prosecdef AS secdef
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname='public'
      AND p.prosecdef = true
    ORDER BY p.proname, p.oid;
  `);
  if (r.status !== 201) { console.log('ERR:', r.body.substring(0, 500)); return; }
  const rows = JSON.parse(r.body);
  console.log('All SECURITY DEFINER public functions:', rows.length);
  const stillPublic = rows.filter(x => x.acl && /=X\//.test(x.acl));
  console.log(`Still have PUBLIC: ${stillPublic.length}`);
  for (const b of stillPublic) console.log('  ', b.schema + '.' + b.name + '(' + b.args + ') ->', b.acl);
  console.log('\nAll ACLs:');
  for (const x of rows) console.log('  ', x.name + '(' + x.args + ') ->', x.acl);
})();
