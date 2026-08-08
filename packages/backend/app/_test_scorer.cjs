// Debug: see what M2.7 actually returns
const { callAI } = require('./ai-router.cjs');

(async () => {
  const r = await callAI({
    task: 'scorer',
    payload: {
      system: 'You are a JSON scorer. Output valid JSON only. No thinking out loud.',
      messages: [{
        role: 'user',
        content: 'Score this business: Klinik Pergigian Rohaya in KL. Reply ONLY with JSON: {"appointment_driven":true,"active_whatsapp":true,"owner_reachable":true,"evidence_missed_enquiries":true,"active_online_presence":true,"reasoning":"dental clinic"}',
      }],
      max_tokens: 400,
      temperature: 0.1,
    },
  });
  console.log('OK:', r.ok);
  console.log('raw text:', JSON.stringify(r.text));
  console.log('tokens:', r.tokens);
  console.log('provider:', r.provider_used);
  console.log('latency:', r.latency_ms);
  console.log('fallback_chain:', r.fallback_chain);
})().catch(e => console.error('FATAL', e));
