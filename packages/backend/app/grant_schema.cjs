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
  try {
    await c.query("GRANT USAGE ON SCHEMA bijou_agents TO anon, authenticated, service_role");
    await c.query("GRANT ALL ON ALL TABLES IN SCHEMA bijou_agents TO anon, authenticated, service_role");
    await c.query("GRANT ALL ON ALL SEQUENCES IN SCHEMA bijou_agents TO anon, authenticated, service_role");
    await c.query("GRANT ALL ON ALL FUNCTIONS IN SCHEMA bijou_agents TO anon, authenticated, service_role");
    console.log("grants applied");
    try {
      await c.query("NOTIFY pgrst, 'reload schema'");
      console.log("NOTIFY pgrst sent");
    } catch (e) {
      console.log("NOTIFY err:", e.message);
    }
  } catch (e) {
    console.error("grants failed:", e.message);
  }
  await c.end();
})();
