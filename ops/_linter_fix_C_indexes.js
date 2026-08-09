// Fix C: Drop duplicate indexes.
// We keep: UNIQUE indexes (they enforce constraints AND serve as indexes).
// We drop: non-unique duplicates of unique indexes (redundant).
// We drop: one of two identical non-unique indexes.
// We KEEP: partial indexes (WHERE ...) — they're not functionally duplicates.
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

// Indexes to drop (the non-unique one, when a unique version exists; or the duplicate non-unique).
const DROP = [
  // Non-unique dup of UNIQUE
  'idx_api_keys_hash',                          // -> api_keys_key_hash_key (UNIQUE)
  'idx_business_profiles_tenant',               // -> unique_tenant_profile (UNIQUE)
  'idx_call_settings_tenant_id',                // -> call_settings_tenant_id_key (UNIQUE)
  'idx_client_configs_tenant_id',               // -> client_configs_tenant_id_key (UNIQUE)
  'idx_contacts_tenant_jid',                    // -> contacts_tenant_jid_unique (UNIQUE)
  'idx_customer_memory_tenant_chat',            // -> customer_memory_tenant_id_chat_jid_key (UNIQUE)
  'idx_device_sessions_device_id',              // -> device_sessions_device_id_key (UNIQUE)
  'idx_email_tokens_token',                     // -> email_verification_tokens_token_key (UNIQUE)
  'idx_jid_mappings_tenant_lid',                // -> uq_jid_mappings_tenant_lid (UNIQUE)
  'idx_personas_key',                           // -> personas_persona_key_key (UNIQUE)
  'idx_setup_progress_tenant',                  // -> tenant_setup_progress_tenant_id_key (UNIQUE)
  'idx_tenants_slug',                           // -> tenants_slug_key (UNIQUE)
  'idx_tenants_telegram_username',              // -> tenants_telegram_username_key (UNIQUE)
  'idx_tenants_token',                          // -> tenants_signup_token_key (UNIQUE)
  'idx_vertical_templates_vertical_id',         // -> vertical_templates_vertical_id_key (UNIQUE)
  // Identical non-unique pairs (drop one)
  'idx_tenants_stripe_customer',                // -> idx_tenants_stripe_customer_id
  'idx_tenants_whatsapp',                       // -> idx_tenants_whatsapp_jid
  'idx_agent_connections_user_id',              // -> idx_agent_connections_user
  'idx_agent_activity_connection_id',           // -> idx_agent_activity_connection
  'idx_agent_status_connection_id',             // -> idx_agent_status_connection
];

// KEEP (partial indexes — not functional duplicates, mention in report):
// - idx_email_templates_tenant_type  WHERE is_active = true  (vs full UNIQUE)
// - idx_tenant_email_config_tenant_id  WHERE is_active = true  (vs full UNIQUE)
// - idx_follow_ups_pending  WHERE status = 'pending'  (vs full status,scheduled_at)
// - idx_onboarding_token  WHERE status <> 'completed'  (vs pkey on token)

(async () => {
  console.log(`Dropping ${DROP.length} duplicate indexes...`);
  const stmts = DROP.map(n => `DROP INDEX IF EXISTS public.${n};`);
  const batch = stmts.join('\n');
  const r = await execSql(batch);
  if (r.status !== 201) {
    console.log('ERR:', r.body.substring(0, 1500));
    return;
  }
  console.log('OK: dropped', DROP.length, 'indexes');

  // Verify: re-check for duplicates
  const verify = await execSql(`
    SELECT schemaname, tablename, indexname, indexdef
    FROM pg_indexes
    WHERE schemaname='public'
    ORDER BY tablename, indexname;
  `);
  if (verify.status !== 201) { console.log('VERIFY ERR:', verify.body.substring(0, 500)); return; }
  const rows = JSON.parse(verify.body);
  // Find any remaining duplicates (same column list)
  const colOf = (idx) => {
    const m = idx.indexdef.match(/\(([^)]+)\)/);
    return m ? m[1].replace(/\s+/g, '') : '';
  };
  const byTable = {};
  for (const i of rows) (byTable[i.tablename] ||= []).push(i);
  let dups = 0;
  for (const t of Object.keys(byTable)) {
    const seen = {};
    for (const i of byTable[t]) {
      const c = colOf(i);
      if (c) (seen[c] ||= []).push(i);
    }
    for (const c of Object.keys(seen)) {
      if (seen[c].length > 1) {
        // Only count if BOTH are non-partial (otherwise partial is fine)
        const full = seen[c].filter(i => !/WHERE/.test(i.indexdef));
        if (full.length > 1) {
          dups++;
          console.log(`  REMAINING DUP ${t}(${c}):`);
          for (const i of seen[c]) console.log(`    - ${i.indexname}: ${i.indexdef}`);
        }
      }
    }
  }
  console.log(`\nRemaining non-partial duplicates: ${dups}`);
})();
