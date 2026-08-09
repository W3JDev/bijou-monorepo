// Verify A v2: re-check all 25 functions with simpler logic
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
  // Just dump all functions with their proconfig
  const r = await execSql(`
    SELECT n.nspname AS schema, p.proname AS name,
           pg_get_function_identity_arguments(p.oid) AS args,
           p.proconfig::text AS cfg
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname IN ('public','stripe')
      AND p.prokind = 'f'
      AND p.proname IN (
        'calculate_campaign_stats','calculate_lead_score','call_bookings_set_scheduled_date',
        'count_monthly_conversations','create_default_templates','current_tenant_id',
        'get_contact_last_campaign','get_conversation_threads','get_tenant_daily_sent_count',
        'increment_click_count','increment_contact_message','is_service_role',
        'update_contacts_updated_at','update_escalation_notifications_updated_at',
        'update_follow_ups_timestamp','update_help_ticket_timestamp','update_jid_mappings_updated_at',
        'update_leads_updated_at_column','update_onboarding_current_step','update_updated_at',
        'update_updated_at_column','update_web_support_ticket_timestamp',
        'set_updated_at','set_updated_at_metadata','check_rate_limit'
      )
    ORDER BY n.nspname, p.proname, p.oid;
  `);
  if (r.status !== 201) { console.log('ERR:', r.body.substring(0, 500)); return; }
  const rows = JSON.parse(r.body);
  console.log('Total rows returned:', rows.length);
  const bad = rows.filter(x => !x.cfg || !x.cfg.includes('search_path=public'));
  console.log('Missing or wrong search_path:', bad.length);
  for (const b of bad) console.log('  ', b.schema + '.' + b.name + '(' + b.args + ') ->', b.cfg);
  console.log('\nAll functions:');
  for (const x of rows) console.log('  ', x.schema + '.' + x.name + '(' + x.args + ') ->', x.cfg);
})();
