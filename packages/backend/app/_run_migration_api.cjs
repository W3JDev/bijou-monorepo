// Apply SQL via Supabase Management API (POST /v1/projects/{ref}/database/query)
const fs = require('fs');
const path = require('path');

const sqlPath = process.argv[2];
if (!sqlPath) { console.error('Usage: node _run_migration_api.cjs <sql>'); process.exit(1); }

const env = {};
for (const line of fs.readFileSync(path.resolve(__dirname, '..', '.env'), 'utf8').split('\n')) {
  const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
  if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, '').trim();
}

const token = env.SUPABASE_ACCESS_TOKEN;
const ref = 'lrwzlujomukzjykafmic';
const sql = fs.readFileSync(sqlPath, 'utf8');
console.log(`[migrate] file: ${sqlPath} (${sql.length} bytes)`);

(async () => {
  const url = `https://api.supabase.com/v1/projects/${ref}/database/query`;
  try {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: sql }),
    });
    const txt = await r.text();
    console.log(`[migrate] HTTP ${r.status}`);
    if (!r.ok) {
      console.error('FAIL body:', txt.slice(0, 800));
      process.exit(1);
    }
    console.log('OK body:', txt.slice(0, 800));
  } catch (e) {
    console.error('FATAL:', e.message);
    process.exit(1);
  }
})();
