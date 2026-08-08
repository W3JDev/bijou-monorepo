const fs = require("fs");
const path = require("path");
const { Client } = require("pg");

const envRaw = fs.readFileSync(path.join(__dirname, "..", ".env"), "utf-8");
const env = {};
for (const line of envRaw.split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
  if (!m) continue;
  let v = m[2].trim();
  if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
  env[m[1]] = v;
}
const url = env.SUPABASE_URL;
const pw = env.SUPABASE_DB_PASSWORD;
const m = url.match(/https?:\/\/([^.]+)\.supabase\.co/);
const connStr = `postgresql://postgres:${encodeURIComponent(pw)}@db.${m[1]}.supabase.co:5432/postgres`;
(async () => {
  const c = new Client({ connectionString: connStr, ssl: { rejectUnauthorized: false } });
  await c.connect();
  // List schemas and tables
  const s = await c.query("select schema_name from information_schema.schemata where schema_name like 'bijou%' or schema_name = 'public' order by schema_name");
  console.log("Schemas:", s.rows.map(r => r.schema_name).join(", "));
  const t = await c.query("select table_schema, table_name from information_schema.tables where table_schema = 'bijou_agents' order by table_name");
  console.log("Tables in bijou_agents:", t.rows.length);
  t.rows.forEach(r => console.log("  " + r.table_name));
  // Force PostgREST to reload schema by sending a NOTIFY
  try {
    await c.query("NOTIFY pgrst, 'reload schema'");
    console.log("Sent NOTIFY pgrst, 'reload schema'");
  } catch (e) {
    console.log("NOTIFY failed:", e.message);
  }
  await c.end();
})();
