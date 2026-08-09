// Show proacl for SECURITY DEFINER functions to understand the linter's interpretation
const ACCESS = '${SUPABASE_ACCESS_TOKEN}';
const REF    = 'lrwzlujomukzjykafmic';

async function execSql(sql) {
  const r = await fetch(`https://api.supabase.com/v1/projects/${REF}/database/query`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${ACCESS}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: sql }),
  });
  return { status: r.status, body: await r.text() };
}

(async () => {
  const r = await execSql(`
    SELECT
      n.nspname AS schema,
      p.proname AS name,
      pg_get_function_identity_arguments(p.oid) AS args,
      p.prosecdef AS is_security_definer,
      p.proacl::text AS acl
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname IN ('public','stripe')
      AND p.prokind = 'f'
      AND p.prosecdef = true
    ORDER BY n.nspname, p.proname, p.oid;
  `);
  if (r.status !== 201) {
    console.log('ERR:', r.body.substring(0, 500));
    return;
  }
  const fns = JSON.parse(r.body);
  for (const f of fns) {
    console.log(`  ${f.schema}.${f.name}(${f.args})  acl=${f.acl}`);
  }
})();
