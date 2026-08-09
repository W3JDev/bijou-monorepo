// Fix B: Multiple Permissive Policies
// Conservative merges — only for SAME role+command with different qual conditions.
// Tables affected:
//   dashboard_views: 3 SELECT (authenticated) -> 1 with OR of org/private/dept
//   dashboard_views: 2 ALL (authenticated) -> 1 with OR of admin/creator
//   agent_connections: 2 SELECT (authenticated) -> 1 with OR of own/can_view_user
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
  // 1) dashboard_views SELECT: drop 3, create 1 merged
  const dvSelect = `
    DROP POLICY IF EXISTS "All users can view org views" ON public.dashboard_views;
    DROP POLICY IF EXISTS "Creator can view own private views" ON public.dashboard_views;
    DROP POLICY IF EXISTS "Dept members can view dept views" ON public.dashboard_views;

    CREATE POLICY "dashboard_views_select" ON public.dashboard_views
      FOR SELECT TO authenticated
      USING (
        visibility = 'org'::text
        OR (visibility = 'private'::text AND created_by = (auth.uid())::text)
        OR (visibility = 'department'::text AND department_id IN (
          SELECT user_profiles.department_id FROM user_profiles WHERE user_profiles.id = auth.uid()
        ))
      );
  `;
  console.log('--- Fixing dashboard_views SELECT ---');
  const r1 = await execSql(dvSelect);
  if (r1.status !== 201) { console.log('ERR:', r1.body.substring(0, 1000)); return; }
  console.log('OK');

  // 2) dashboard_views ALL: drop 2 authenticated ALL, create 1 merged; keep service_role ALL separate
  const dvAll = `
    DROP POLICY IF EXISTS "Admins can manage all views" ON public.dashboard_views;
    DROP POLICY IF EXISTS "Creator can manage own views" ON public.dashboard_views;

    CREATE POLICY "dashboard_views_all" ON public.dashboard_views
      FOR ALL TO authenticated
      USING (
        EXISTS (
          SELECT 1 FROM user_profiles
          WHERE user_profiles.id = auth.uid()
            AND user_profiles.role = ANY(ARRAY['owner'::text, 'admin'::text])
        )
        OR created_by = (auth.uid())::text
      )
      WITH CHECK (
        EXISTS (
          SELECT 1 FROM user_profiles
          WHERE user_profiles.id = auth.uid()
            AND user_profiles.role = ANY(ARRAY['owner'::text, 'admin'::text])
        )
        OR created_by = (auth.uid())::text
      );
  `;
  console.log('--- Fixing dashboard_views ALL ---');
  const r2 = await execSql(dvAll);
  if (r2.status !== 201) { console.log('ERR:', r2.body.substring(0, 1000)); return; }
  console.log('OK');

  // 3) agent_connections SELECT: drop 2 authenticated SELECT, create 1 merged; keep public SELECT separate
  const acSelect = `
    DROP POLICY IF EXISTS "Users can view own agent connections" ON public.agent_connections;
    DROP POLICY IF EXISTS "Department members can view dept agent connections" ON public.agent_connections;

    CREATE POLICY "agent_connections_select" ON public.agent_connections
      FOR SELECT TO authenticated
      USING (
        user_id = auth.uid()
        OR can_view_user(auth.uid(), user_id)
      );
  `;
  console.log('--- Fixing agent_connections SELECT ---');
  const r3 = await execSql(acSelect);
  if (r3.status !== 201) { console.log('ERR:', r3.body.substring(0, 1000)); return; }
  console.log('OK');

  // Verify: re-list policies on the 2 tables
  console.log('\n--- Verifying ---');
  const verify = await execSql(`
    SELECT tablename, policyname, cmd, roles::text
    FROM pg_policies
    WHERE schemaname='public' AND tablename IN ('dashboard_views','agent_connections')
    ORDER BY tablename, cmd, policyname;
  `);
  if (verify.status === 201) {
    const rows = JSON.parse(verify.body);
    for (const r of rows) console.log(`  ${r.tablename}  ${r.policyname}  cmd=${r.cmd}  roles=${r.roles}`);
  }
})();
