const fs = require("fs");
const path = require("path");
const { Client } = require("pg");

const envRaw = fs.readFileSync(path.join(__dirname, "..", ".env"), "utf-8");
const env = {};
for (const line of envRaw.split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
  if (!m) continue;
  let v = m[2].trim();
  if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
    v = v.slice(1, -1);
  }
  env[m[1]] = v;
}

const url = env.SUPABASE_URL;
const pw = env.SUPABASE_DB_PASSWORD;
if (!url || !pw) { console.error("Missing env"); process.exit(1); }
const m = url.match(/https?:\/\/([^.]+)\.supabase\.co/);
if (!m) { console.error("Bad URL"); process.exit(1); }
const projectRef = m[1];
const connStr = `postgresql://postgres:${encodeURIComponent(pw)}@db.${projectRef}.supabase.co:5432/postgres`;

const sql = fs.readFileSync(path.join(__dirname, "agent_fleet_schema.sql"), "utf-8");

(async () => {
  const client = new Client({ connectionString: connStr, ssl: { rejectUnauthorized: false } });
  await client.connect();
  console.log(`Connected to db.${projectRef}.supabase.co`);
  try {
    await client.query(sql);
    console.log("Schema applied successfully.");
  } catch (e) {
    console.error("Schema apply failed:", e.message);
    process.exit(1);
  } finally {
    await client.end();
  }
})();
