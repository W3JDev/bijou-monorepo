// scripts/list-net-tables.cjs
const { Client } = require('pg');

(async () => {
  const c = new Client({
    connectionString: `postgresql://postgres:${process.env.SUPABASE_DB_PASSWORD}@db.lrwzlujomukzjykafmic.supabase.co:5432/postgres`,
    ssl: { rejectUnauthorized: false },
  });
  await c.connect();
  const r = await c.query(`
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'net'
    ORDER BY table_name
  `);
  console.log('net.* tables:', r.rows.map(x => x.table_name));
  await c.end();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
