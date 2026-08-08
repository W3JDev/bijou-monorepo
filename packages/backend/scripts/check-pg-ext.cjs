// scripts/check-pg-ext.cjs — check available PG extensions for webhooks
const { Client } = require('pg');

const pw = process.env.SUPABASE_DB_PASSWORD;
const ref = 'lrwzlujomukzjykafmic';
const conn = `postgresql://postgres:${pw}@db.${ref}.supabase.co:5432/postgres`;

(async () => {
  const c = new Client({ connectionString: conn, ssl: { rejectUnauthorized: false } });
  await c.connect();
  const r = await c.query(`
    SELECT
      extname
    FROM pg_extension
    WHERE extname IN ('pg_net', 'http', 'supabase_functions')
    ORDER BY extname;
  `);
  console.log('Available webhook-relevant extensions:', r.rows.map(x => x.extname));
  await c.end();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
