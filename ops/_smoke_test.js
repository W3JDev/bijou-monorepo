// Smoke test: hit a couple of key endpoints as authenticated and anon to confirm nothing is broken.
const fs = require('fs');
const env = fs.readFileSync('packages/landing/.env', 'utf8');
const ANON = env.match(/SUPABASE_ANON_KEY=([^\n]+)/)[1].trim();
const SVC  = env.match(/SUPABASE_SERVICE_ROLE_KEY=([^\n]+)/)[1].trim();
const URL  = 'https://lrwzlujomukzjykafmic.supabase.co';

(async () => {
  // 1) Call public RPC `is_service_role` as anon (should work, returns false)
  const r1 = await fetch(`${URL}/rest/v1/rpc/is_service_role`, {
    method: 'POST',
    headers: { apikey: ANON, Authorization: `Bearer ${ANON}`, 'Content-Type': 'application/json' },
    body: '{}',
  });
  console.log('is_service_role as anon:', r1.status, (await r1.text()).substring(0, 200));

  // 2) Call SECURITY DEFINER `current_tenant_id` as anon (should work, returns null)
  const r2 = await fetch(`${URL}/rest/v1/rpc/current_tenant_id`, {
    method: 'POST',
    headers: { apikey: ANON, Authorization: `Bearer ${ANON}`, 'Content-Type': 'application/json' },
    body: '{}',
  });
  console.log('current_tenant_id as anon:', r2.status, (await r2.text()).substring(0, 200));

  // 3) Call SECURITY DEFINER `get_tenant_daily_sent_count` as anon (with a dummy uuid)
  const r3 = await fetch(`${URL}/rest/v1/rpc/get_tenant_daily_sent_count`, {
    method: 'POST',
    headers: { apikey: ANON, Authorization: `Bearer ${ANON}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ p_tenant_id: '00000000-0000-0000-0000-000000000000' }),
  });
  console.log('get_tenant_daily_sent_count as anon:', r3.status, (await r3.text()).substring(0, 200));

  // 4) List tables via REST as anon (RLS still enforced)
  const r4 = await fetch(`${URL}/rest/v1/dashboard_views?select=id&limit=1`, {
    headers: { apikey: ANON, Authorization: `Bearer ${ANON}` },
  });
  console.log('dashboard_views SELECT as anon:', r4.status, (await r4.text()).substring(0, 200));

  // 5) As service_role, query a couple of tables
  const r5 = await fetch(`${URL}/rest/v1/tenants?select=id&limit=1`, {
    headers: { apikey: SVC, Authorization: `Bearer ${SVC}` },
  });
  console.log('tenants SELECT as service_role:', r5.status, (await r5.text()).substring(0, 200));
})();
