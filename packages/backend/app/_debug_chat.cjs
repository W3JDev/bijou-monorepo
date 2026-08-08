// Debug the chat endpoint with the actual Bijou system prompt
const { callAI } = require('./ai-router.cjs');
const fs = require('fs');

const sysFromFile = fs.readFileSync('C:\\Users\\W3jde\\local-projects\\Bijou-AI---Digital-Employee-main\\Bijou-AI---Digital-Employee-main\\api\\chat.js', 'utf8');
const sysMatch = sysFromFile.match(/const systemInstruction = `([\s\S]*?)`;/);
const sys = sysMatch ? sysMatch[1] : 'You are Bijou.';

console.log('System prompt chars:', sys.length);

(async () => {
  const r = await callAI({
    task: 'chat',
    payload: {
      system: sys,
      messages: [{ role: 'user', content: 'hi' }],
      max_tokens: 2000,
      temperature: 0.7,
    },
  });
  console.log('OK:', r.ok);
  console.log('text length:', r.text?.length || 0);
  console.log('text preview:', JSON.stringify((r.text || '').substring(0, 200)));
  console.log('provider:', r.provider_used);
  console.log('model:', r.model_used);
  console.log('tokens:', r.tokens);
  console.log('latency:', r.latency_ms);
  console.log('error:', r.error);
})().catch(e => console.error('FATAL', e));
