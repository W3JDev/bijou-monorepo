// Simulate the Vercel function locally to see what's happening
const { createClient } = require('@supabase/supabase-js');
const { callAI } = require('./ai-router.cjs');
const fs = require('fs');

// Read the system prompt directly from chat.js
const chatJs = fs.readFileSync('C:\\Users\\W3jde\\local-projects\\Bijou-AI---Digital-Employee-main\\Bijou-AI---Digital-Employee-main\\api\\chat.js', 'utf8');
const sysMatch = chatJs.match(/const systemInstruction = `([\s\S]*?)`;/);
const sys = sysMatch ? sysMatch[1] : 'You are Bijou.';

(async () => {
  const message = 'hi';
  const history = [];
  const userMessages = [
    ...(history || []).map((h) => ({ role: h.role === 'model' ? 'assistant' : 'user', content: h.content })),
    { role: 'user', content: message || 'Hello' },
  ];

  console.log('System prompt chars:', sys.length);
  console.log('Calling callAI...');

  try {
    const r = await callAI({
      task: 'chat',
      payload: { system: sys, messages: userMessages, max_tokens: 1500, temperature: 0.7 },
    });
    console.log('OK:', r.ok);
    console.log('text:', JSON.stringify((r.text || '').substring(0, 300)));
    console.log('provider:', r.provider_used);
    console.log('model:', r.model_used);
    console.log('tokens:', r.tokens);
    console.log('error:', r.error);
  } catch (e) {
    console.error('THROWN:', e.message);
    console.error('STACK:', e.stack);
  }
})();
