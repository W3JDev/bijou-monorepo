// backend/_run_migration.cjs
// Apply a SQL migration file using pg against Supabase.
// Usage: node backend/_run_migration.cjs <path-to-sql>

const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

const sqlPath = process.argv[2];
if (!sqlPath) {
  console.error('Usage: node _run_migration.cjs <path-to-sql>');
  process.exit(1);
}

// Load .env
const envPath = path.resolve(__dirname, '..', '.env');
const env = {};
for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
  const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
  if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, '').trim();
}

const password = env.SUPABASE_DB_PASSWORD;
const ref = 'lrwzlujomukzjykafmic';
// Supabase pooler (transaction mode, port 6543)
const connStr = `postgresql://postgres.${ref}:${encodeURIComponent(password)}@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres`;

const sql = fs.readFileSync(sqlPath, 'utf8');
console.log(`[migration] file: ${sqlPath} (${sql.length} bytes)`);

(async () => {
  const client = new Client({ connectionString: connStr, ssl: { rejectUnauthorized: false } });
  try {
    await client.connect();
    console.log('[migration] connected');
    await client.query(sql);
    console.log('[migration] applied OK');
  } catch (e) {
    console.error('[migration] FAILED:', e.message);
    if (e.code) console.error('  code:', e.code);
    process.exit(1);
  } finally {
    await client.end();
  }
})();
