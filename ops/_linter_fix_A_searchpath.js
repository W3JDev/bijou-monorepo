// Fix A: Function Search Path Mutable
// ALTER FUNCTION ... SET search_path = public, pg_temp;
// Note: stripe.* extension functions (gbt_*, _dist, etc.) are NOT touched.
const fs = require('fs');
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

const PUBLIC_FNS = [
  ['public', 'calculate_campaign_stats',            ['uuid']],
  ['public', 'calculate_lead_score',                ['leads']],
  ['public', 'call_bookings_set_scheduled_date',    []],
  ['public', 'count_monthly_conversations',         ['uuid', 'timestamp without time zone']],
  ['public', 'create_default_templates',            []],
  ['public', 'current_tenant_id',                   []],
  ['public', 'get_contact_last_campaign',           ['uuid']],
  ['public', 'get_conversation_threads',            ['uuid', 'text', 'integer', 'integer']],
  ['public', 'get_tenant_daily_sent_count',         ['uuid']],
  ['public', 'increment_click_count',               ['bigint']],
  ['public', 'increment_contact_message',           ['text', 'text']],
  ['public', 'is_service_role',                     []],
  ['public', 'update_contacts_updated_at',          []],
  ['public', 'update_escalation_notifications_updated_at', []],
  ['public', 'update_follow_ups_timestamp',         []],
  ['public', 'update_help_ticket_timestamp',        []],
  ['public', 'update_jid_mappings_updated_at',      []],
  ['public', 'update_leads_updated_at_column',      []],
  ['public', 'update_onboarding_current_step',      []],
  ['public', 'update_updated_at',                   []],
  ['public', 'update_updated_at_column',            []],
  ['public', 'update_web_support_ticket_timestamp', []],
];
// Stripe schema functions we own (extension functions gbt_*, _dist etc. are NOT touched)
const STRIPE_FNS = [
  ['stripe', 'set_updated_at',          []],
  ['stripe', 'set_updated_at_metadata', []],
  ['stripe', 'check_rate_limit',        ['text', 'integer', 'integer']],
];

const ALL = [...PUBLIC_FNS, ...STRIPE_FNS];

function buildArgs(types) {
  if (types === undefined || types === null) return '';
  return '(' + types.join(', ') + ')';
}

(async () => {
  // Build a single SQL batch
  const stmts = ALL.map(([schema, name, args]) =>
    `ALTER FUNCTION ${schema}.${name}${buildArgs(args)} SET search_path = public, pg_temp;`
  );
  const batch = stmts.join('\n');
  console.log(`Sending ${stmts.length} ALTER FUNCTION statements...`);
  const r = await execSql(batch);
  if (r.status !== 201) {
    console.log('ERR:', r.body.substring(0, 1500));
    return;
  }
  console.log('OK: search_path set on', stmts.length, 'functions');

  // Verify by re-reading proconfig for the changed functions
  const verifyStmts = ALL.map(([schema, name, args]) =>
    `SELECT '${schema}.${name}${buildArgs(args)}' AS fn, p.proconfig::text AS cfg
     FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
     WHERE n.nspname='${schema}' AND p.proname='${name}'
       AND pg_get_function_identity_arguments(p.oid)='${args.join(', ')}'`
  ).join('\nUNION ALL\n');
  const vr = await execSql(verifyStmts);
  if (vr.status !== 201) {
    console.log('VERIFY ERR:', vr.body.substring(0, 500));
    return;
  }
  const rows = JSON.parse(vr.body);
  const bad = rows.filter(r => !r.cfg || !r.cfg.includes('search_path=public,pg_temp'));
  console.log(`\nVerified ${rows.length} functions, ${bad.length} still missing search_path.`);
  for (const b of bad) console.log('  MISSING:', b.fn, '->', b.cfg);
})();
