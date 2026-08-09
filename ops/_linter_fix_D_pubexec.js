// Fix D: REVOKE PUBLIC EXECUTE on SECURITY DEFINER functions
// All entries are SECURITY DEFINER. We REVOKE PUBLIC (the empty grantee in proacl).
// Note: increment_click_count is excluded (its acl has no PUBLIC entry).
// Note: posthog_webhook_fire has search_path=public, extensions — keep that.
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
  ['public', 'calculate_campaign_stats',          ['uuid']],
  ['public', 'call_bookings_set_scheduled_date',  []],
  ['public', 'can_view_user',                     ['uuid', 'uuid']],
  ['public', 'cleanup_expired_onboarding_sessions', ['integer']],
  ['public', 'cleanup_expired_onboarding_sessions', []],
  ['public', 'cleanup_expired_qr_sessions',       []],
  ['public', 'count_monthly_conversations',       ['uuid', 'timestamp without time zone']],
  ['public', 'current_tenant_id',                 []],
  ['public', 'expire_old_onboarding_sessions',    []],
  ['public', 'get_contact_last_campaign',         ['uuid']],
  ['public', 'get_tenant_daily_sent_count',       ['uuid']],
  ['public', 'handle_new_user',                   []],
  ['public', 'increment_contact_message',         ['text', 'text']],
  ['public', 'is_service_role',                   []],
  ['public', 'posthog_webhook_fire',              []],
  ['public', 'prune_agent_status',                []],
  ['public', 'rls_auto_enable',                   []],
  ['public', 'search_knowledge',                  ['vector', 'text', 'double precision', 'integer', 'uuid']],
];

function buildArgs(types) {
  if (types === undefined || types === null) return '';
  return '(' + types.join(', ') + ')';
}

(async () => {
  const stmts = FNS.map(([schema, name, args]) =>
    `REVOKE EXECUTE ON FUNCTION ${schema}.${name}${buildArgs(args)} FROM PUBLIC;`
  );
  const batch = stmts.join('\n');
  console.log(`Sending ${stmts.length} REVOKE statements...`);
  const r = await execSql(batch);
  if (r.status !== 201) {
    console.log('ERR:', r.body.substring(0, 1500));
    return;
  }
  console.log('OK: PUBLIC EXECUTE revoked on', stmts.length, 'functions');

  // Verify: re-read proacl and confirm PUBLIC entry is gone
  const verifyStmts = FNS.map(([schema, name, args]) =>
    `SELECT '${schema}.${name}(${args.join(',')})' AS fn, p.proacl::text AS acl
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
  // Public entry looks like "=X/postgres" in the ACL list
  const stillPublic = rows.filter(x => x.acl && /=X\//.test(x.acl));
  console.log(`\nVerified ${rows.length} functions, ${stillPublic.length} still have PUBLIC.`);
  for (const b of stillPublic) console.log('  STILL HAS PUBLIC:', b.fn, '->', b.acl);
  console.log('\nACLs after revoke:');
  for (const x of rows) console.log('  ', x.fn, '->', x.acl);
})();
