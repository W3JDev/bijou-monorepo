// scripts/find-tables.cjs — scan all schemas for any user/onboarding/waitlist tables
const { Client } = require('pg');

const pw = process.env.SUPABASE_DB_PASSWORD;
const ref = 'lrwzlujomukzjykafmic';
const conn = `postgresql://postgres:${pw}@db.${ref}.supabase.co:5432/postgres`;

(async () => {
  const c = new Client({ connectionString: conn, ssl: { rejectUnauthorized: false } });
  await c.connect();
  const r = await c.query(`
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_name ILIKE ANY (ARRAY['%user%','%onboard%','%waitlist%','%subscriber%','%customer%','%profile%','%contact%'])
      AND table_schema NOT IN ('pg_catalog','information_schema')
    ORDER BY table_schema, table_name;
  `);
  console.log('Found:', r.rows);
  await c.end();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
