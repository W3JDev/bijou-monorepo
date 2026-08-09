// Re-check PUBLIC EXEC for SECURITY DEFINER functions (use regprocedure to disambiguate overloaded names)
const fs = require('fs');
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
  // Find SECURITY DEFINER functions and their PUBLIC EXEC status, with proper disambiguation
  const r = await execSql(`
    SELECT
      n.nspname AS schema,
      p.proname AS name,
      pg_get_function_identity_arguments(p.oid) AS args,
      p.prosecdef AS is_security_definer,
      p.proconfig AS proconfig,
      p.proacl,
      EXISTS (
        SELECT 1
        FROM pg_roles r
        WHERE r.rolname = 'PUBLIC'
          AND has_function_privilege(r.oid, p.oid, 'EXECUTE')
      ) AS public_execute
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
  console.log('SECURITY DEFINER functions (total):', fns.length);
  const pub = fns.filter(f => f.public_execute);
  console.log('SECURITY DEFINER + PUBLIC EXEC:', pub.length);
  for (const f of pub) {
    console.log(`  ${f.schema}.${f.name}(${f.args})  proconfig=${JSON.stringify(f.proconfig)}`);
  }
  console.log('\nNot PUBLIC exec:');
  for (const f of fns.filter(f => !f.public_execute)) {
    console.log(`  ${f.schema}.${f.name}(${f.args})  proconfig=${JSON.stringify(f.proconfig)}`);
  }
})();
