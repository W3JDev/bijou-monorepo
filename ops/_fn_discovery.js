// Functions discovery (simpler)
const fs = require('fs');
const path = require('path');
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
  // Get functions with their config and security definer flag
  const fnRes = await execSql(`
    SELECT
      n.nspname AS schema,
      p.proname AS name,
      pg_get_function_identity_arguments(p.oid) AS args,
      p.prosecdef AS is_security_definer,
      p.proconfig AS proconfig,
      p.proacl AS acl
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname IN ('public','stripe')
      AND p.prokind = 'f'
    ORDER BY n.nspname, p.proname;
  `);
  if (fnRes.status !== 201) {
    console.log('ERR:', fnRes.body.substring(0, 500));
    return;
  }
  const fns = JSON.parse(fnRes.body);
  fs.writeFileSync(path.join(__dirname, '_fn_discovery.json'), JSON.stringify(fns, null, 2));

  // For each function, check if PUBLIC has EXECUTE via has_function_privilege
  const publicExecChecks = [];
  for (const f of fns) {
    const quotedArgs = (f.args || '').replace(/'/g, "''");
    publicExecChecks.push(`
      SELECT '${f.schema}.${f.name}(${f.args})'::text AS fn,
             has_function_privilege('PUBLIC', '${f.schema}.${f.name}'::regproc, 'EXECUTE') AS pub_exec
    `);
  }
  // Batch into one query
  const batchRes = await execSql(publicExecChecks.join('\nUNION ALL\n'));
  let publicExecs = [];
  if (batchRes.status === 201) {
    publicExecs = JSON.parse(batchRes.body);
  } else {
    console.log('PUB EXEC BATCH ERR:', batchRes.body.substring(0, 500));
  }

  // Compose
  const pubExecMap = {};
  for (const r of publicExecs) pubExecMap[r.fn] = r.pub_exec;

  console.log('=== FUNCTIONS SUMMARY ===');
  console.log('total:', fns.length);
  const mutable = fns.filter(f => {
    const cfg = f.proconfig;
    if (!cfg) return true;
    return !cfg.some(c => c === 'search_path=public,pg_temp' || c === 'search_path=pg_catalog,public' || /search_path=/.test(c));
  });
  console.log('mutable search_path:', mutable.length);
  for (const f of mutable) {
    const key = `${f.schema}.${f.name}(${f.args})`;
    console.log(`  ${key}  proconfig=${JSON.stringify(f.proconfig)}  pub=${pubExecMap[key]}`);
  }

  const secDef = fns.filter(f => f.is_security_definer);
  console.log('\nSECURITY DEFINER total:', secDef.length);
  const secDefPub = secDef.filter(f => {
    const key = `${f.schema}.${f.name}(${f.args})`;
    return pubExecMap[key] === true;
  });
  console.log('SECURITY DEFINER + PUBLIC EXEC:', secDefPub.length);
  for (const f of secDefPub) {
    const key = `${f.schema}.${f.name}(${f.args})`;
    console.log(`  ${key}`);
  }

  // Write combined
  fs.writeFileSync(path.join(__dirname, '_fn_combined.json'), JSON.stringify(
    fns.map(f => ({
      ...f,
      public_execute: pubExecMap[`${f.schema}.${f.name}(${f.args})`],
    })),
    null, 2
  ));
  console.log('\nWrote ops/_fn_discovery.json and ops/_fn_combined.json');
})();
