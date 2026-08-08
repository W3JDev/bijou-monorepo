// scripts/check-tables.cjs — verify which Bijou tables exist
const { Client } = require('pg');

const pw = process.env.SUPABASE_DB_PASSWORD;
const ref = 'lrwzlujomukzjykafmic';
const conn = `postgresql://postgres:${pw}@db.${ref}.supabase.co:5432/postgres`;

(async () => {
  const c = new Client({ connectionString: conn, ssl: { rejectUnauthorized: false } });
  await c.connect();
  const r = await c.query(`
    SELECT table_name, (SELECT count(*) FROM information_schema.columns c WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) AS columns
    FROM information_schema.tables t
    WHERE table_schema = 'public'
      AND table_name IN ('leads', 'onboarding_users', 'voice_waitlist', 'profiles', 'customers')
    ORDER BY table_name;
  `);
  console.log('Tables found:', r.rows);
  await c.end();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
