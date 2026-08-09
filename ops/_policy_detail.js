// Detail of policies on tables with multiple permissive policies
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
  const tables = [
    'agent_activity','agent_connections','agent_status',
    'business_profiles','dashboard_views','knowledge_base',
    'user_profiles','tenants','escalations',
    'knowledge_base','user_profiles','dashboard_views',
    'departments','checklist_state','team_activity',
  ];
  const r = await execSql(`
    SELECT tablename, policyname, cmd, roles::text, qual, with_check
    FROM pg_policies
    WHERE schemaname='public' AND tablename = ANY(ARRAY[${tables.map(t => `'${t}'`).join(',')}]::text[])
    ORDER BY tablename, cmd, policyname;
  `);
  if (r.status !== 201) { console.log(r.body.substring(0, 500)); return; }
  const arr = JSON.parse(r.body);
  const byTable = {};
  for (const p of arr) (byTable[p.tablename] ||= []).push(p);
  for (const t of Object.keys(byTable)) {
    console.log(`\n=== ${t} ===`);
    for (const p of byTable[t]) {
      console.log(`  ${p.policyname}`);
      console.log(`    cmd=${p.cmd}  roles=${p.roles}`);
      console.log(`    qual: ${p.qual || 'null'}`);
      console.log(`    with_check: ${p.with_check || 'null'}`);
    }
  }
})();
