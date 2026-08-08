// scripts/check-net-responses-detailed.cjs
const { Client } = require('pg');

(async () => {
  const c = new Client({
    connectionString: `postgresql://postgres:${process.env.SUPABASE_DB_PASSWORD}@db.lrwzlujomukzjykafmic.supabase.co:5432/postgres`,
    ssl: { rejectUnauthorized: false },
  });
  await c.connect();
  const r = await c.query(`
    SELECT id, status_code, content_type, timed_out, error_msg,
           substring(content, 1, 400) AS body_preview,
           created
    FROM net._http_response
    ORDER BY id DESC LIMIT 3
  `);
  console.log('Last 3 webhook responses (with body):');
  for (const row of r.rows) {
    console.log(JSON.stringify(row, null, 2));
    console.log('---');
  }
  await c.end();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
