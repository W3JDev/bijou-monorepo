// Direct check of one function to see what pg_get_function_identity_arguments returns
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
  // List all overloads of cleanup_expired_onboarding_sessions
  const r1 = await execSql(`
    SELECT p.oid, p.proname,
           pg_get_function_identity_arguments(p.oid) AS id_args,
           pg_get_function_arguments(p.oid) AS full_args,
           p.proacl::text AS acl
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname='public' AND p.proname='cleanup_expired_onboarding_sessions';
  `);
  console.log('--- cleanup_expired_onboarding_sessions overloads ---');
  console.log('status:', r1.status);
  console.log('body:', r1.body.substring(0, 1500));

  // Check can_view_user
  const r2 = await execSql(`
    SELECT p.oid, p.proname,
           pg_get_function_identity_arguments(p.oid) AS id_args,
           pg_get_function_arguments(p.oid) AS full_args,
           p.proacl::text AS acl
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname='public' AND p.proname='can_view_user';
  `);
  console.log('\n--- can_view_user ---');
  console.log('body:', r2.body.substring(0, 1500));
})();
