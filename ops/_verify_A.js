// Verify A: confirm search_path set on all 25 functions
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
  ['public', 'calculate_campaign_stats', 'uuid'],
  ['public', 'calculate_lead_score', 'leads'],
  ['public', 'call_bookings_set_scheduled_date', ''],
  ['public', 'count_monthly_conversations', 'uuid, timestamp without time zone'],
  ['public', 'create_default_templates', ''],
  ['public', 'current_tenant_id', ''],
  ['public', 'get_contact_last_campaign', 'uuid'],
  ['public', 'get_conversation_threads', 'uuid, text, integer, integer'],
  ['public', 'get_tenant_daily_sent_count', 'uuid'],
  ['public', 'increment_click_count', 'bigint'],
  ['public', 'increment_contact_message', 'text, text'],
  ['public', 'is_service_role', ''],
  ['public', 'update_contacts_updated_at', ''],
  ['public', 'update_escalation_notifications_updated_at', ''],
  ['public', 'update_follow_ups_timestamp', ''],
  ['public', 'update_help_ticket_timestamp', ''],
  ['public', 'update_jid_mappings_updated_at', ''],
  ['public', 'update_leads_updated_at_column', ''],
  ['public', 'update_onboarding_current_step', ''],
  ['public', 'update_updated_at', ''],
  ['public', 'update_updated_at_column', ''],
  ['public', 'update_web_support_ticket_timestamp', ''],
  ['stripe', 'set_updated_at', ''],
  ['stripe', 'set_updated_at_metadata', ''],
  ['stripe', 'check_rate_limit', 'text, integer, integer'],
];

(async () => {
  const stmts = FNS.map(([schema, name, args]) =>
    `SELECT '${schema}.${name}(${args})' AS fn, p.proconfig::text AS cfg
     FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
     WHERE n.nspname='${schema}' AND p.proname='${name}'
       AND pg_get_function_identity_arguments(p.oid)='${args}'`
  ).join('\nUNION ALL\n');
  const r = await execSql(stmts);
  if (r.status !== 201) { console.log('ERR:', r.body.substring(0, 500)); return; }
  const rows = JSON.parse(r.body);
  const bad = rows.filter(x => !x.cfg || !x.cfg.includes('search_path=public,pg_temp'));
  console.log(`Verified ${rows.length} functions, ${bad.length} still missing search_path.`);
  for (const b of bad) console.log('  MISSING:', b.fn, '->', b.cfg);
  console.log('All OK (' + (rows.length - bad.length) + '):');
  for (const x of rows) console.log('  ', x.fn, '->', x.cfg);
})();
