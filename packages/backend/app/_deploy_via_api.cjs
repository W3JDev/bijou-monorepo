// Deploy via Vercel API directly (bypasses CLI auth issues)
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const envText = fs.readFileSync(path.join(__dirname, '..', '.env'), 'utf8');
const env = {};
for (const line of envText.split('\n')) {
  const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
  if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, '').trim();
}

const TOKEN = env.VERCEL_API_TOKEN;
const TEAM = 'team_XdCQw3V5TqcnxgeNYX46uGHv';
const PROJECT = 'prj_RT9KcMhL2xO7ZTiZRic4OsG1e2QV';

(async () => {
  // 1. Create a deployment record
  console.log('[deploy] creating deployment record...');
  const createRes = await fetch(`https://api.vercel.com/v13/deployments?teamId=${TEAM}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: 'bijou-ai-digital-employee',
      target: 'production',
      project: PROJECT,
      gitSource: { type: 'github', ref: 'main', repoId: undefined },
    }),
  });
  const createData = await createRes.json();
  if (!createRes.ok) {
    console.error('create failed:', createRes.status, JSON.stringify(createData).slice(0, 500));
    process.exit(1);
  }
  console.log('[deploy] deployment id:', createData.id);
  console.log('[deploy] upload URL:', createData.url ? 'present' : 'missing');
  console.log('[deploy] full response keys:', Object.keys(createData));
})().catch(e => { console.error('FATAL', e); process.exit(1); });
