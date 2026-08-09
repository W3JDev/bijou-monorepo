// Verify D v2: precise check - PUBLIC entry is the one that starts with '=X/'
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
    SELECT n.nspname AS schema, p.proname AS name,
           pg_get_function_identity_arguments(p.oid) AS args,
           p.proacl::text AS acl,
           p.prosecdef AS secdef
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname='public'
      AND p.prosecdef = true
    ORDER BY p.proname, p.oid;
  `);
  if (r.status !== 201) { console.log('ERR:', r.body.substring(0, 500)); return; }
  const rows = JSON.parse(r.body);
  // Parse ACL: '{a=X/grantor,b=Y/grantor,...}' -> check if any item starts with '=X/'
  const hasPublic = (aclStr) => {
    if (!aclStr) return false;
    const inner = aclStr.replace(/^{|}$/g, '');
    return inner.split(',').some(item => /^=X\//.test(item.trim()));
  };
  const stillPublic = rows.filter(x => hasPublic(x.acl));
  console.log(`SECURITY DEFINER public functions: ${rows.length}`);
  console.log(`Still have PUBLIC: ${stillPublic.length}`);
  for (const b of stillPublic) console.log('  ', b.name + '(' + b.args + ') ->', b.acl);
  console.log('\nFunctions WITH PUBLIC removed:');
  for (const x of rows.filter(x => !hasPublic(x.acl))) {
    console.log('  ✓', x.name + '(' + x.args + ') ->', x.acl);
  }
})();
