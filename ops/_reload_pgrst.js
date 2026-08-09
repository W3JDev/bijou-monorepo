// Reload PostgREST after schema changes
const ACCESS = '${SUPABASE_ACCESS_TOKEN}';
const REF    = 'lrwzlujomukzjykafmic';

(async () => {
  const r = await fetch(`https://api.supabase.com/v1/projects/${REF}/database/query`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${ACCESS}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: "NOTIFY pgrst, 'reload schema';" }),
  });
  console.log('NOTIFY status:', r.status);
  console.log('body:', (await r.text()).substring(0, 200));
})();
