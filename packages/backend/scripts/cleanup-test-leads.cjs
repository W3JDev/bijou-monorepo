// scripts/cleanup-test-leads.cjs — clean up any mavis-test-* leads
const { Client } = require('pg');

(async () => {
  const c = new Client({
    connectionString: `postgresql://postgres:${process.env.SUPABASE_DB_PASSWORD}@db.lrwzlujomukzjykafmic.supabase.co:5432/postgres`,
    ssl: { rejectUnauthorized: false },
  });
  await c.connect();
  const r = await c.query(`DELETE FROM public.leads WHERE email LIKE 'mavis-test-%@example.com'`);
  console.log('Deleted', r.rowCount, 'test leads');
  await c.end();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
