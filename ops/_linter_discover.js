// Discovery script: enumerate functions, policies, indexes for the Bijou Supabase linter audit.
// Writes JSON snapshots to ops/_linter_discovery.json.
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
  const out = {};

  // 1) Functions: name, schema, args, security definer, search_path mutable, executable by PUBLIC
  const fnRes = await execSql(`
    SELECT
      n.nspname AS schema,
      p.proname AS name,
      pg_get_function_identity_arguments(p.oid) AS args,
      p.prosecdef AS is_security_definer,
      p.proconfig AS proconfig,
      array_to_string(p.proacl, E'\\n') AS acl,
      EXISTS (
        SELECT 1 FROM pg_proc p2
        WHERE p2.oid = p.oid
          AND ('PUBLIC' = ANY (
            SELECT b.rolname FROM pg_roles b WHERE b.oid = ANY (p2.proacl::oid[])
          ) OR has_function_privilege('PUBLIC', p2.oid, 'EXECUTE')
        )
      ) AS public_execute
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname IN ('public','stripe')
      AND p.prokind = 'f'
    ORDER BY n.nspname, p.proname;
  `);
  out.functions = fnRes.status === 201 ? JSON.parse(fnRes.body) : { err: fnRes.body.substring(0, 500) };

  // 2) Policies: per-table list of policies with role + cmd
  const polRes = await execSql(`
    SELECT tablename, policyname, cmd, roles::text, qual, with_check
    FROM pg_policies
    WHERE schemaname='public'
    ORDER BY tablename, cmd, policyname;
  `);
  out.policies = polRes.status === 201 ? JSON.parse(polRes.body) : { err: polRes.body.substring(0, 500) };

  // 3) Indexes
  const idxRes = await execSql(`
    SELECT schemaname, tablename, indexname, indexdef
    FROM pg_indexes
    WHERE schemaname='public'
    ORDER BY tablename, indexname;
  `);
  out.indexes = idxRes.status === 201 ? JSON.parse(idxRes.body) : { err: idxRes.body.substring(0, 500) };

  fs.writeFileSync(path.join(__dirname, '_linter_discovery.json'), JSON.stringify(out, null, 2));

  // Also print a summary to stdout
  console.log('--- FUNCTIONS ---');
  console.log('count:', Array.isArray(out.functions) ? out.functions.length : 'err');
  if (Array.isArray(out.functions)) {
    const withMutable = out.functions.filter(f => !f.proconfig || !f.proconfig.some(c => c === 'search_path=public,pg_temp' || c === 'search_path=pg_catalog,public' || /search_path=/.test(c)));
    const secDefPub = out.functions.filter(f => f.is_security_definer && f.public_execute);
    console.log('  search_path NOT explicitly set (mutable):', withMutable.length);
    console.log('  SECURITY DEFINER + PUBLIC EXECUTE:', secDefPub.length);
    for (const f of withMutable) {
      console.log(`    [${f.schema}] ${f.name}(${f.args})  proconfig=${JSON.stringify(f.proconfig)}`);
    }
    console.log('\n  --- SECURITY DEFINER + PUBLIC EXECUTE ---');
    for (const f of secDefPub) {
      console.log(`    ${f.schema}.${f.name}(${f.args})`);
    }
  }

  console.log('\n--- POLICIES ---');
  if (Array.isArray(out.policies)) {
    console.log('count:', out.policies.length);
    // Find tables with > 1 SELECT policy
    const byTableCmd = {};
    for (const p of out.policies) {
      const key = p.tablename + '|' + p.cmd;
      (byTableCmd[key] ||= []).push(p);
    }
    console.log('\n  Tables with multiple SELECT policies:');
    for (const k of Object.keys(byTableCmd)) {
      if (k.endsWith('|SELECT') && byTableCmd[k].length > 1) {
        const [t] = k.split('|');
        console.log(`    ${t} (${byTableCmd[k].length} SELECT policies):`);
        for (const p of byTableCmd[k]) {
          console.log(`      - ${p.policyname}  roles=${p.roles}  qual=${(p.qual||'').substring(0, 80)}`);
        }
      }
    }
    console.log('\n  Tables with multiple permissive policies for any cmd:');
    for (const k of Object.keys(byTableCmd)) {
      if (byTableCmd[k].length > 1) {
        const [t, cmd] = k.split('|');
        console.log(`    ${t} ${cmd} (${byTableCmd[k].length})`);
      }
    }
  }

  console.log('\n--- INDEXES ---');
  if (Array.isArray(out.indexes)) {
    console.log('count:', out.indexes.length);
    // Find duplicate indexes (same def prefix or same column list)
    const byTable = {};
    for (const i of out.indexes) (byTable[i.tablename] ||= []).push(i);
    for (const t of Object.keys(byTable)) {
      // Extract column expression from indexdef
      const colOf = (idx) => {
        const m = idx.indexdef.match(/\(([^)]+)\)/);
        return m ? m[1].replace(/\s+/g, '') : '';
      };
      const seen = {};
      for (const i of byTable[t]) {
        const c = colOf(i);
        if (c) (seen[c] ||= []).push(i);
      }
      for (const c of Object.keys(seen)) {
        if (seen[c].length > 1) {
          console.log(`  DUP ${t}(${c}):`);
          for (const i of seen[c]) console.log(`    - ${i.indexname}: ${i.indexdef}`);
        }
      }
    }
  }

  console.log('\nWrote ops/_linter_discovery.json');
})();
