// Fix C cleanup: drop the last missed duplicate
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
  const r = await execSql(`DROP INDEX IF EXISTS public.idx_tenants_whatsapp_number;`);
  if (r.status !== 201) { console.log('ERR:', r.body.substring(0, 1000)); return; }
  console.log('OK: dropped idx_tenants_whatsapp_number');

  // Final duplicate check
  const verify = await execSql(`
    SELECT schemaname, tablename, indexname, indexdef
    FROM pg_indexes WHERE schemaname='public' ORDER BY tablename, indexname;
  `);
  const rows = JSON.parse(verify.body);
  const colOf = (idx) => {
    const m = idx.indexdef.match(/\(([^)]+)\)/);
    return m ? m[1].replace(/\s+/g, '') : '';
  };
  const byTable = {};
  for (const i of rows) (byTable[i.tablename] ||= []).push(i);
  let dups = 0;
  for (const t of Object.keys(byTable)) {
    const seen = {};
    for (const i of byTable[t]) {
      const c = colOf(i);
      if (c) (seen[c] ||= []).push(i);
    }
    for (const c of Object.keys(seen)) {
      if (seen[c].length > 1) {
        const full = seen[c].filter(i => !/WHERE/.test(i.indexdef));
        if (full.length > 1) {
          dups++;
          console.log(`  REMAINING DUP ${t}(${c}):`);
          for (const i of seen[c]) console.log(`    - ${i.indexname}: ${i.indexdef}`);
        }
      }
    }
  }
  console.log(`\nRemaining non-partial duplicates: ${dups}`);
})();
