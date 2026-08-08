// scripts/list-queue-cols.cjs
const { Client } = require('pg');

(async () => {
  const c = new Client({
    connectionString: `postgresql://postgres:${process.env.SUPABASE_DB_PASSWORD}@db.lrwzlujomukzjykafmic.supabase.co:5432/postgres`,
    ssl: { rejectUnauthorized: false },
  });
  await c.connect();
  const r = await c.query(`
    SELECT column_name, data_type FROM information_schema.columns
    WHERE table_schema = 'net' AND table_name = 'http_request_queue'
    ORDER BY ordinal_position
  `);
  console.log(r.rows);
  await c.end();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
