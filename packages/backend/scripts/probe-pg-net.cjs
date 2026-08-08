// scripts/probe-pg-net.cjs — discover the installed pg_net function signatures
const { Client } = require('pg');

(async () => {
  const c = new Client({
    connectionString: `postgresql://postgres:${process.env.SUPABASE_DB_PASSWORD}@db.lrwzlujomukzjykafmic.supabase.co:5432/postgres`,
    ssl: { rejectUnauthorized: false },
  });
  await c.connect();
  const v = await c.query("SELECT extversion FROM pg_extension WHERE extname = 'pg_net'");
  console.log('pg_net version:', v.rows[0]?.extversion);
  const fns = await c.query(`
    SELECT proname, pg_get_function_arguments(p.oid) AS args, pg_get_function_result(p.oid) AS returns
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'net' AND proname LIKE 'http_%'
    ORDER BY proname
  `);
  console.log('net functions:');
  for (const r of fns.rows) console.log('  ', r.proname, '(', r.args, ') →', r.returns);
  await c.end();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
