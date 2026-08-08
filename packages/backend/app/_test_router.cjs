// Quick smoke test for the router
const { callAI, routerStatus } = require('./ai-router.cjs');

(async () => {
  const r1 = await callAI({
    task: 'scorer',
    payload: {
      messages: [{ role: 'user', content: 'Reply with JSON: {"score": 75, "reason": "good fit"}' }],
      system: 'You are a scorer. Always output valid JSON only.',
    },
  });
  console.log('SCORER:', r1.ok, '|', JSON.stringify(r1.text), '| cost:', r1.cost_usd, '| latency:', r1.latency_ms);

  const r2 = await callAI({
    task: 'outreach',
    payload: {
      messages: [{ role: 'user', content: 'Bangsar Dental, dental clinic, online booking. Write 1-sentence opener in Manglish.' }],
      system: 'You are Bijou AI writing a Manglish DM to a dental clinic.',
    },
  });
  console.log('OUTREACH:', r2.ok, '|', (r2.text || '').substring(0, 200), '| cost:', r2.cost_usd, '| latency:', r2.latency_ms);

  const r3 = await callAI({
    task: 'classify',
    payload: {
      messages: [{ role: 'user', content: 'Classify this Malaysian business as: dental, aesthetic, or fnb. Reply with just the category name. Business: Klinik Pergigian Bangsar' }],
    },
  });
  console.log('CLASSIFY:', r3.ok, '|', JSON.stringify(r3.text), '| cost:', r3.cost_usd);

  console.log('---');
  const s = await routerStatus();
  console.log('PROVIDERS:', Object.entries(s.providers).map(([k, v]) => `${k}=${v.configured ? 'on' : 'off'}`).join(', '));
})().catch((e) => { console.error('FATAL:', e.message); process.exit(1); });
