// scripts/check-net-responses.cjs
const { Client } = require('pg');

(async () => {
  const c = new Client({
    connectionString: `postgresql://postgres:${process.env.SUPABASE_DB_PASSWORD}@db.lrwzlujomukzjykafmic.supabase.co:5432/postgres`,
    ssl: { rejectUnauthorized: false },
  });
  await c.connect();
  const q = await c.query(`
    SELECT id, method, url, headers, timeout_milliseconds
    FROM net.http_request_queue
    ORDER BY id DESC LIMIT 5
  `);
  console.log('Last 5 queued webhook requests:');
  for (const row of q.rows) {
    console.log(JSON.stringify(row, (k, v) => k === 'body' ? `[binary ${v?.length}b]` : v, 2));
  }
  console.log('---');
  const r = await c.query(`
    SELECT id, status_code, content_type, timed_out, error_msg, created
    FROM net._http_response
    ORDER BY id DESC LIMIT 5
  `);
  console.log('Last 5 webhook responses:');
  for (const row of r.rows) console.log(JSON.stringify(row, null, 2));
  await c.end();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
