// backend/ai-router.cjs
// Phase 1 — AI Model Router
// Routes LLM calls by task + provider, with fallback chain, budget tracking, PostHog events.
//
// Usage:
//   const { callAI, routerStatus } = require('./backend/ai-router.cjs');
//   const result = await callAI({
//     task: 'outreach',           // task name (drives model + chain)
//     payload: { messages: [...], system?: '...' },
//     budget: { maxCostUsd: 0.05 } // optional per-call cap
//   });
//   // result: { ok, text, tokens, cost, provider_used, fallback_chain, latency_ms, error? }
//
// Provider priority chain (per task, overridable):
//   1. minimax  (MiniMax direct — primary)
//   2. gemini   (free rotator, GEMINI_API_KEY_3/4/FREE)
//   3. openrouter (BYOK, OPENROUTER_API_KEY)
//   4. omniroute (legacy gateway, CUSTOME_API_KEY)

const fs = require('fs');
const path = require('path');

// ---------- Env loading (works both as CJS module and from api/*.js) ----------
function loadEnv() {
  const envPath = path.resolve(__dirname, '..', '.env');
  if (!fs.existsSync(envPath)) return {};
  const env = {};
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, '').trim();
  }
  return env;
}

const ENV = loadEnv();

function envOr(key, fallback) {
  return process.env[key] || ENV[key] || fallback;
}

// ---------- Supabase (PostgREST) ----------
const SUPABASE_URL = envOr('SUPABASE_URL') || envOr('NEXT_PUBLIC_SUPABASE_URL');
const SUPABASE_KEY = envOr('SUPABASE_SERVICE_KEY') || envOr('SUPABASE_SERVICE_ROLE_KEY');

async function supabaseSelect(path) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
    },
  });
  if (!r.ok) throw new Error(`supabase ${path} ${r.status}`);
  return r.json();
}

async function supabaseInsert(table, rows) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: 'POST',
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      'Content-Type': 'application/json',
      Prefer: 'return=representation',
    },
    body: JSON.stringify(rows),
  });
  if (!r.ok) throw new Error(`supabase insert ${table} ${r.status} ${(await r.text()).slice(0, 200)}`);
  return r.json();
}

// ---------- Task routing ----------
// Maps task name → { model, maxTokens, temperature, timeoutMs, chain }
const TASK_ROUTING = {
  outreach:  { model: 'MiniMax-M3',   maxTokens: 800,  temperature: 0.7, timeoutMs: 30000, chain: ['minimax','gemini','openrouter','omniroute'] },
  listener:  { model: 'MiniMax-M3',   maxTokens: 500,  temperature: 0.5, timeoutMs: 30000, chain: ['minimax','gemini','openrouter','omniroute'] },
  followup:  { model: 'MiniMax-M3',   maxTokens: 500,  temperature: 0.7, timeoutMs: 30000, chain: ['minimax','gemini','openrouter','omniroute'] },
  chat:      { model: 'MiniMax-M3',   maxTokens: 2000, temperature: 0.8, timeoutMs: 45000, chain: ['minimax','gemini','openrouter','omniroute'] },
  scorer:    { model: 'MiniMax-M3',   maxTokens: 1500, temperature: 0.1, timeoutMs: 25000, chain: ['minimax','gemini','openrouter','omniroute'] },
  classify:  { model: 'MiniMax-M3',   maxTokens: 100,  temperature: 0,   timeoutMs: 10000, chain: ['minimax','gemini','openrouter','omniroute'] },
  research:  { model: 'MiniMax-M3',   maxTokens: 800,  temperature: 0.5, timeoutMs: 30000, chain: ['minimax','gemini','openrouter','omniroute'] },
  pillar:    { model: 'MiniMax-M3',   maxTokens: 600,  temperature: 0.7, timeoutMs: 30000, chain: ['minimax','gemini','openrouter','omniroute'] },
};

const DEFAULT_TASK = 'chat';

// ---------- Provider configs ----------
const PROVIDERS = {
  minimax: {
    type: 'openai-compat',
    apiKey: () => envOr('MINIMAX_API_KEY'),
    baseUrl: () => envOr('MINIMAX_API_ENDPOINT', 'https://api.minimax.io/v1'),
    modelMap: (m) => m, // pass through
    costPer1k: (m) => ({ 'MiniMax-M3': 0.003, 'MiniMax-M2.7': 0.001, 'MiniMax-M2.7-highspeed': 0.0006 }[m] || 0.001),
  },
  gemini: {
    type: 'gemini',
    apiKeys: () => [envOr('GEMINI_API_KEY_3'), envOr('GEMINI_API_KEY_4'), envOr('GEMINI_API_KEY'), envOr('GEMINI_API_KEY_FREE')].filter(Boolean),
    baseUrl: () => 'https://generativelanguage.googleapis.com/v1beta/models',
    modelMap: (m) => m.startsWith('MiniMax-') ? 'gemini-1.5-flash' : m, // fallback to flash if M3 requested
    costPer1k: () => 0, // free tier
  },
  openrouter: {
    type: 'openai-compat',
    apiKey: () => envOr('OPENROUTER_API_KEY'),
    baseUrl: () => 'https://openrouter.ai/api/v1',
    modelMap: (m) => m.startsWith('MiniMax-') ? 'anthropic/claude-3.5-sonnet' : m, // if no M3, use Claude
    costPer1k: (m) => 0.003,
  },
  omniroute: {
    type: 'openai-compat',
    apiKey: () => envOr('CUSTOME_API_KEY'),
    baseUrl: () => envOr('CUSTOM_API_ENDPOINT', 'https://ai-gateway-bufxd.sprites.app/v1'),
    modelMap: (m) => 'auto/best-fast', // legacy uses auto-router
    costPer1k: () => 0.002,
  },
};

// ---------- PostHog event ----------
async function emitPostHog(event, properties) {
  const apiKey = envOr('POSTHOG_PERSONAL_API_KEY') || envOr('POSTHOG_API_KEY');
  const host = envOr('POSTHOG_HOST', 'https://us.i.posthog.com');
  if (!apiKey) return; // silent
  try {
    await fetch(`${host}/capture/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key: envOr('POSTHOG_PROJECT_KEY'),
        event,
        distinct_id: 'bijou-backend',
        properties: { ...properties, $lib: 'ai-router' },
        timestamp: new Date().toISOString(),
      }),
    });
  } catch (e) {
    // PostHog failure should not break the call
    console.error('posthog_emit_failed', e.message);
  }
}

// ---------- Budget check ----------
async function getBudgetState(provider) {
  if (!SUPABASE_URL || !SUPABASE_KEY) return { ok: true }; // bypass if DB not configured
  const todayMYT = new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString().slice(0, 10);
  try {
    const rows = await supabaseSelect(
      `bjx_ai_budgets?provider=eq.${provider}&scope=eq.daily&scope_key=eq.${todayMYT}&limit=1`
    );
    if (rows.length === 0) return { ok: true };
    const b = rows[0];
    return {
      ok: Number(b.spent_usd) < Number(b.limit_usd),
      spent: Number(b.spent_usd),
      limit: Number(b.limit_usd),
    };
  } catch (e) {
    return { ok: true }; // fail-open on DB error
  }
}

async function recordSpend(provider, costUsd) {
  if (!SUPABASE_URL || !SUPABASE_KEY) return;
  const todayMYT = new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString().slice(0, 10);
  try {
    // Upsert via PostgREST RPC would be ideal; for now we read + update
    const rows = await supabaseSelect(
      `bjx_ai_budgets?provider=eq.${provider}&scope=eq.daily&scope_key=eq.${todayMYT}&limit=1`
    );
    if (rows.length === 0) {
      await supabaseInsert('bjx_ai_budgets', {
        provider, scope: 'daily', scope_key: todayMYT,
        limit_usd: 5.00, spent_usd: costUsd, call_count: 1,
      });
    } else {
      const b = rows[0];
      await fetch(`${SUPABASE_URL}/rest/v1/bjx_ai_budgets?id=eq.${b.id}`, {
        method: 'PATCH',
        headers: {
          apikey: SUPABASE_KEY,
          Authorization: `Bearer ${SUPABASE_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          spent_usd: Number(b.spent_usd) + costUsd,
          call_count: b.call_count + 1,
          updated_at: new Date().toISOString(),
        }),
      });
    }
  } catch (e) {
    console.error('recordSpend_failed', e.message);
  }
}

async function recordCall(row) {
  if (!SUPABASE_URL || !SUPABASE_KEY) return;
  try {
    await supabaseInsert('bjx_ai_calls', {
      provider: row.provider,
      model: row.model,
      task: row.task,
      tokens_in: row.tokens_in || 0,
      tokens_out: row.tokens_out || 0,
      total_tokens: row.total_tokens || 0,
      latency_ms: row.latency_ms || 0,
      cost_usd: row.cost_usd || 0,
      fallback: row.fallback || false,
      error: row.error || null,
    });
  } catch (e) {
    console.error('recordCall_failed', e.message);
  }
}

// ---------- Provider call ----------
async function callProvider(name, model, payload, timeoutMs) {
  const p = PROVIDERS[name];
  if (!p) throw new Error(`unknown provider: ${name}`);

  const actualModel = p.modelMap(model);
  const start = Date.now();

  if (p.type === 'openai-compat') {
    const apiKey = p.apiKey();
    if (!apiKey) throw new Error(`${name} no API key`);
    const url = `${p.baseUrl()}/chat/completions`;
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: actualModel,
          messages: payload.messages || [],
          ...(payload.system ? { system: payload.system } : {}),
          max_tokens: payload.max_tokens || 800,
          temperature: payload.temperature ?? 0.7,
        }),
        signal: controller.signal,
      });
      clearTimeout(tid);
      const latency = Date.now() - start;
      if (!r.ok) {
        const errTxt = (await r.text()).slice(0, 200);
        return { ok: false, error: `${name} ${r.status} ${errTxt}`, latency_ms: latency };
      }
      const data = await r.json();
      const text = data.choices?.[0]?.message?.content || '';
      const usage = data.usage || {};
      const cost = (usage.total_tokens || 0) / 1000 * (p.costPer1k(actualModel) || 0.001);
      return {
        ok: true,
        text: stripThinking(text),
        tokens_in: usage.prompt_tokens || 0,
        tokens_out: usage.completion_tokens || 0,
        total_tokens: usage.total_tokens || 0,
        cost_usd: cost,
        actual_model: actualModel,
        latency_ms: latency,
      };
    } catch (e) {
      clearTimeout(tid);
      return { ok: false, error: `${name} ${e.name === 'AbortError' ? 'timeout' : e.message}`, latency_ms: Date.now() - start };
    }
  }

  if (p.type === 'gemini') {
    const keys = p.apiKeys();
    if (keys.length === 0) throw new Error('gemini no API key');
    // Rotate keys: try each on 429/403
    let lastErr = null;
    for (const apiKey of keys) {
      const url = `${p.baseUrl()}/${actualModel}:generateContent?key=${apiKey}`;
      const controller = new AbortController();
      const tid = setTimeout(() => controller.abort(), timeoutMs);
      try {
        // Build Gemini-style contents from messages
        const contents = (payload.messages || []).map((m) => ({
          role: m.role === 'assistant' ? 'model' : 'user',
          parts: [{ text: m.content }],
        }));
        const sysInstr = payload.system ? { systemInstruction: { parts: [{ text: payload.system }] } } : {};
        const r = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...sysInstr,
            contents,
            generationConfig: {
              maxOutputTokens: payload.max_tokens || 800,
              temperature: payload.temperature ?? 0.7,
            },
          }),
          signal: controller.signal,
        });
        clearTimeout(tid);
        const latency = Date.now() - start;
        if (!r.ok) {
          const errTxt = (await r.text()).slice(0, 200);
          lastErr = `gemini ${r.status} ${errTxt}`;
          if (r.status === 429 || r.status === 403) continue; // try next key
          return { ok: false, error: lastErr, latency_ms: latency };
        }
        const data = await r.json();
        const text = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
        const usage = data.usageMetadata || {};
        const tokens_in = usage.promptTokenCount || 0;
        const tokens_out = usage.candidatesTokenCount || 0;
        const total = tokens_in + tokens_out;
        return {
          ok: true,
          text: stripThinking(text),
          tokens_in, tokens_out, total_tokens: total,
          cost_usd: 0, // free tier
          actual_model: actualModel,
          latency_ms: latency,
        };
      } catch (e) {
        clearTimeout(tid);
        lastErr = `gemini ${e.name === 'AbortError' ? 'timeout' : e.message}`;
      }
    }
    return { ok: false, error: lastErr || 'gemini all keys failed', latency_ms: Date.now() - start };
  }

  return { ok: false, error: `${name} unsupported provider type` };
}

function stripThinking(text) {
  // MiniMax M2.7 leaks <think>...</think> blocks. Strip them.
  if (!text) return '';
  return text.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
}

// ---------- Public API ----------
async function callAI({ task = DEFAULT_TASK, payload = {}, budget = {} } = {}) {
  const routing = TASK_ROUTING[task] || TASK_ROUTING[DEFAULT_TASK];
  const { model, maxTokens, temperature, timeoutMs, chain } = routing;
  const startTime = Date.now();

  const fallbackChain = [];
  let lastError = null;

  for (let i = 0; i < chain.length; i++) {
    const provider = chain[i];
    const isFallback = i > 0;

    // Budget check (only for paid providers)
    if (provider === 'minimax' || provider === 'openrouter' || provider === 'omniroute') {
      const b = await getBudgetState(provider);
      if (!b.ok) {
        fallbackChain.push({ provider, skipped: 'budget' });
        lastError = `${provider} budget exhausted (${b.spent}/${b.limit})`;
        continue;
      }
    }

    // Per-call cap
    if (budget.maxCostUsd) {
      // We don't know the cost up front; just trust the cap and let provider cost land
      // (could add an estTokens * costPer1k check here for stricter cap)
    }

    const result = await callProvider(provider, model, {
      ...payload,
      max_tokens: maxTokens,
      temperature,
    }, timeoutMs);

    const totalLatency = Date.now() - startTime;

    if (result.ok) {
      const cost = result.cost_usd || 0;
      // Record spend + call
      await recordSpend(provider, cost);
      await recordCall({
        provider, model: result.actual_model || model, task,
        tokens_in: result.tokens_in, tokens_out: result.tokens_out, total_tokens: result.total_tokens,
        latency_ms: result.latency_ms, cost_usd: cost, fallback: isFallback,
      });
      // PostHog event
      await emitPostHog('ai_call', {
        task, provider, model: result.actual_model || model,
        tokens_in: result.tokens_in, tokens_out: result.tokens_out, total_tokens: result.total_tokens,
        latency_ms: result.latency_ms, cost_usd: cost, fallback: isFallback,
      });
      return {
        ok: true,
        text: result.text,
        tokens: {
          in: result.tokens_in, out: result.tokens_out, total: result.total_tokens,
        },
        cost_usd: cost,
        provider_used: provider,
        model_used: result.actual_model || model,
        fallback_chain: fallbackChain,
        latency_ms: result.latency_ms,
        total_latency_ms: totalLatency,
      };
    } else {
      lastError = result.error;
      fallbackChain.push({ provider, error: result.error });
      await recordCall({
        provider, model, task,
        latency_ms: result.latency_ms, cost_usd: 0, fallback: true, error: result.error,
      });
      await emitPostHog('ai_call_failed', { task, provider, model, error: result.error, latency_ms: result.latency_ms });
    }
  }

  return {
    ok: false,
    error: lastError || 'all providers failed',
    fallback_chain: fallbackChain,
    total_latency_ms: Date.now() - startTime,
  };
}

// ---------- Router status ----------
async function routerStatus() {
  const providers = {};
  for (const name of Object.keys(PROVIDERS)) {
    const apiKey = PROVIDERS[name].apiKey
      ? PROVIDERS[name].apiKey()
      : PROVIDERS[name].apiKeys
      ? PROVIDERS[name].apiKeys().length
      : null;
    const configured = !!apiKey && (Array.isArray(apiKey) ? apiKey.length > 0 : true);
    let budget = { spent: 0, limit: 0 };
    if (SUPABASE_URL && SUPABASE_KEY) {
      try {
        const todayMYT = new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString().slice(0, 10);
        const rows = await supabaseSelect(
          `bjx_ai_budgets?provider=eq.${name}&scope=eq.daily&scope_key=eq.${todayMYT}&limit=1`
        );
        if (rows.length > 0) {
          budget = { spent: Number(rows[0].spent_usd), limit: Number(rows[0].limit_usd) };
        }
      } catch (e) { /* ignore */ }
    }
    providers[name] = {
      configured,
      budget_today_usd: budget.spent,
      limit_today_usd: budget.limit,
    };
  }
  return { ok: true, providers, task_routing: TASK_ROUTING };
}

module.exports = { callAI, routerStatus, PROVIDERS, TASK_ROUTING };
