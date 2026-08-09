// Full re-verification of all linter fixes
const fs = require('fs');
const path = require('path');
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

(async () => {
  const summary = {};

  // 1) Functions: search_path set
  const fnRes = await execSql(`
    SELECT n.nspname AS schema, p.proname AS name,
           pg_get_function_identity_arguments(p.oid) AS args,
           p.proconfig::text AS cfg
    FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname IN ('public','stripe') AND p.prokind='f'
    ORDER BY n.nspname, p.proname, p.oid;
  `);
  const fns = JSON.parse(fnRes.body);
  const targetFns = [
    'calculate_campaign_stats','calculate_lead_score','call_bookings_set_scheduled_date',
    'count_monthly_conversations','create_default_templates','current_tenant_id',
    'get_contact_last_campaign','get_conversation_threads','get_tenant_daily_sent_count',
    'increment_click_count','increment_contact_message','is_service_role',
    'update_contacts_updated_at','update_escalation_notifications_updated_at',
    'update_follow_ups_timestamp','update_help_ticket_timestamp','update_jid_mappings_updated_at',
    'update_leads_updated_at_column','update_onboarding_current_step','update_updated_at',
    'update_updated_at_column','update_web_support_ticket_timestamp',
    'set_updated_at','set_updated_at_metadata','check_rate_limit',
  ];
  const targetFnRows = fns.filter(f => targetFns.includes(f.name));
  summary.functions_total = targetFnRows.length;
  summary.functions_with_search_path = targetFnRows.filter(f => f.cfg && f.cfg.includes('search_path=public')).length;
  summary.functions_missing_search_path = targetFnRows.filter(f => !f.cfg || !f.cfg.includes('search_path=public')).map(f => f.schema + '.' + f.name + '(' + f.args + ')');

  // 2) SECURITY DEFINER functions: PUBLIC revoked
  const sdRes = await execSql(`
    SELECT n.nspname AS schema, p.proname AS name,
           pg_get_function_identity_arguments(p.oid) AS args,
           p.proacl::text AS acl
    FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname='public' AND p.prokind='f' AND p.prosecdef=true
    ORDER BY p.proname, p.oid;
  `);
  const sd = JSON.parse(sdRes.body);
  const hasPublic = (aclStr) => {
    if (!aclStr) return false;
    const inner = aclStr.replace(/^{|}$/g, '');
    return inner.split(',').some(item => /^=X\//.test(item.trim()));
  };
  summary.secdef_total = sd.length;
  summary.secdef_still_public = sd.filter(f => hasPublic(f.acl)).map(f => f.name + '(' + f.args + ')');
  summary.secdef_clean = sd.length - summary.secdef_still_public.length;

  // 3) Policies: count of policies per (table, role, cmd)
  const polRes = await execSql(`
    SELECT tablename, cmd, roles::text, count(*) AS cnt
    FROM pg_policies WHERE schemaname='public'
    GROUP BY tablename, cmd, roles ORDER BY tablename, cmd, roles;
  `);
  const pols = JSON.parse(polRes.body);
  const sameRoleCmd = pols.filter(p => p.cnt > 1);
  summary.policies_total = pols.reduce((a, b) => a + Number(b.cnt), 0);
  summary.policies_same_role_cmd = sameRoleCmd.map(p => `${p.tablename} ${p.cmd} ${p.roles} (${p.cnt})`);

  // 4) Indexes: count of dups
  const idxRes = await execSql(`
    SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename, indexname;
  `);
  const idx = JSON.parse(idxRes.body);
  const colOf = (i) => {
    const m = i.indexdef.match(/\(([^)]+)\)/);
    return m ? m[1].replace(/\s+/g, '') : '';
  };
  const byTable = {};
  for (const i of idx) (byTable[i.tablename] ||= []).push(i);
  const dupList = [];
  for (const t of Object.keys(byTable)) {
    const seen = {};
    for (const i of byTable[t]) {
      const c = colOf(i);
      if (c) (seen[c] ||= []).push(i);
    }
    for (const c of Object.keys(seen)) {
      if (seen[c].length > 1) {
        const full = seen[c].filter(i => !/WHERE/.test(i.indexdef));
        if (full.length > 1) {
          dupList.push(`${t}(${c}) = ${seen[c].map(i => i.indexname).join(', ')}`);
        }
      }
    }
  }
  summary.indexes_total = idx.length;
  summary.indexes_dups_remaining = dupList;
  summary.indexes_partial_kept = idx.filter(i => /WHERE/.test(i.indexdef)).map(i => `${i.tablename}.${i.indexname}  ${i.indexdef}`);

  fs.writeFileSync(path.join(__dirname, '_linter_postcheck.json'), JSON.stringify(summary, null, 2));
  console.log('--- POST-FIX SUMMARY ---');
  console.log(JSON.stringify(summary, null, 2));
})();
