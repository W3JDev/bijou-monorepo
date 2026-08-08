// backend/research_scan.cjs
// Daily market research for Bijou AI. Identifies in-demand verticals, cities,
// and pain keywords from public social signals. Writes structured output to
// bjx_listener_opportunities (source='research_scan') and a JSON digest.
//
// Sources (all free, no API key):
//   - Reddit RSS: r/malaysia, r/klangvalley, r/MalaysianBusiness, r/entrepreneur, r/smallbusiness
//   - (Future: Threads/IG public search via gateway LLM)
//
// Per plan §0: never scrape PII. Public post excerpts only.

const { createClient } = require("@supabase/supabase-js");
const https = require("https");
const path = require("path");
const fs = require("fs");

const envText = fs.readFileSync(path.join(__dirname, "..", ".env"), "utf8");
const env = {};
for (const line of envText.split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
  if (m) env[m[1]] = m[2].trim();
}

const db = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_KEY, { auth: { persistSession: false } });

const SUBREDDITS = [
  "malaysia",
  "klangvalley",
  "MalaysianBusiness",
  "entrepreneur",
  "smallbusiness",
];

// Pain keywords that indicate a Malaysian SME needs a tool like Bijou
const PAIN_PATTERNS = [
  /\bclinic\b/i, /\bdental\b/i, /\baesthetic\b/i, /\bdermatolog/i,
  /\bbooking\b/i, /\bappointment/i, /\bwhatsapp/i, /\bfront\s*desk/i,
  /\bno-?show/i, /\bmissed\s*(call|message|enquir)/i, /\bchatbot\b/i,
  /\bautomation\b/i, /\bafter-?hours\b/i, /\bweekend\s*book/i,
  /\bSME\b/i, /\bowner-?operator/i, /\bsmall\s*business/i,
  /\bsalon\b/i, /\bspa\b/i, /\brestaur(ant|ateur)\b/i, /\bfood\s*truck/i,
  /\bgym\b/i, /\byoga\b/i, /\bproperty\s*agent/i, /\bAirbnb\s*host/i,
];

const CITY_PATTERNS = [
  { name: "Kuala Lumpur", re: /\b(KL|Kuala Lumpur|KLCC|Mont Kiara|Bangsar)\b/i },
  { name: "Petaling Jaya", re: /\b(PJ|Petaling Jaya|SS2|The Curve)\b/i },
  { name: "Subang Jaya", re: /\b(Subang|USJ)\b/i },
  { name: "Shah Alam", re: /\b(Shah Alam)\b/i },
  { name: "Penang", re: /\b(Penang|George Town|Georgetown)\b/i },
  { name: "Johor Bahru", re: /\b(Johor|JB|Johor Bahru)\b/i },
  { name: "Klang", re: /\b(Klang)\b/i },
  { name: "Melaka", re: /\b(Melaka|Malacca)\b/i },
  { name: "Kuching", re: /\b(Kuching|Sarawak)\b/i },
  { name: "Kota Kinabalu", re: /\b(KK|Kota Kinabalu|Sabah)\b/i },
];

const VERTICAL_PATTERNS = [
  { name: "dental", re: /\b(dental|teeth|orthodont|braces|implant|klinik\s+pergigian)\b/i },
  { name: "aesthetic", re: /\b(aesthetic|skincare|dermatolog|beauty|slimming|skin\s*clinic|cosmetic)\b/i },
  { name: "f&b", re: /\b(restaurant|cafe|coffee|food\s*truck|kitchen|catering|F&B|fnb)\b/i },
  { name: "salon_spa", re: /\b(salon|spa|hair|nail|barber|massage)\b/i },
  { name: "fitness", re: /\b(gym|yoga|pilates|fitness|personal trainer)\b/i },
  { name: "property", re: /\b(property|real\s*estate|rent|airbnb|agent)\b/i },
  { name: "retail", re: /\b(retail|shop|boutique|ecommerce|shopee|lazada|store)\b/i },
  { name: "service", re: /\b(accounting|legal|consult|insurance|finance)\b/i },
];

function fetchRss(sub, attempt = 1) {
  return new Promise((resolve, reject) => {
    const url = `https://www.reddit.com/r/${sub}/new/.rss?limit=50`;
    const req = https.get(url, {
      headers: { "User-Agent": "BijouAI-Research/1.0 (contact: w3j.btc@gmail.com)" },
      timeout: 30000,
    }, (res) => {
      if (res.statusCode === 429 || res.statusCode === 403) {
        // Rate limited — retry with exponential backoff, max 3 attempts
        if (attempt < 3) {
          const wait = 3000 * attempt * attempt; // 3s, 12s, 27s
          console.log(`    r/${sub} hit ${res.statusCode}, retrying in ${wait / 1000}s...`);
          setTimeout(() => fetchRss(sub, attempt + 1).then(resolve).catch(reject), wait);
          return;
        }
        return reject(new Error(`Reddit ${res.statusCode} for r/${sub}`));
      }
      let data = "";
      res.on("data", (c) => (data += c));
      res.on("end", () => {
        if (res.statusCode !== 200) return reject(new Error(`Reddit ${res.statusCode} for r/${sub}`));
        resolve(data);
      });
    });
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error("Reddit timeout")));
  });
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

function parseAtom(xml) {
  // Light Atom XML parse — extract <entry> blocks with title, content, author, link, updated
  const entries = [];
  const entryRe = /<entry>([\s\S]*?)<\/entry>/g;
  const titleRe = /<title[^>]*>([\s\S]*?)<\/title>/;
  const contentRe = /<content[^>]*>([\s\S]*?)<\/content>/;
  const authorRe = /<author>\s*<name>([\s\S]*?)<\/name>/;
  const linkRe = /<link[^>]+href="([^"]+)"/;
  const updatedRe = /<updated>([\s\S]*?)<\/updated>/;
  let m;
  while ((m = entryRe.exec(xml)) !== null) {
    const body = m[1];
    const title = (body.match(titleRe) || [, ""])[1].replace(/<!\[CDATA\[|\]\]>/g, "").trim();
    const content = ((body.match(contentRe) || [, ""])[1].replace(/<!\[CDATA\[|\]\]>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim());
    const author = (body.match(authorRe) || [, ""])[1].trim();
    const link = ((body.match(linkRe) || [, ""])[1]).trim();
    const updated = (body.match(updatedRe) || [, ""])[1].trim();
    if (title) entries.push({ title, content, author, link, updated });
  }
  return entries;
}

function clusterKey(text, patterns) {
  for (const p of patterns) if (p.re.test(text)) return p.name;
  return null;
}

function countMatches(text, patterns) {
  const counts = {};
  for (const p of patterns) {
    const matches = text.match(new RegExp(p.re.source, p.re.flags + "g"));
    if (matches) counts[p.name] = matches.length;
  }
  return counts;
}

async function callGateway(systemPrompt, userPrompt, opts = {}) {
  // Phase 1: route through the new AI Model Router.
  const { callAI } = require("./ai-router.cjs");
  const r = await callAI({
    task: opts.task || 'research',
    payload: {
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
      max_tokens: opts.max_tokens || 800,
      temperature: opts.temperature ?? 0.3,
    },
  });
  if (!r.ok) throw new Error(r.error || 'router call failed');
  const content = String(r.text || '').replace(/^```json?\s*/i, '').replace(/```$/i, '').trim();
  if (!content) throw new Error('Empty content');
  return JSON.parse(content);
}

async function llmTrendAnalysis(redditPosts) {
  const sys = `You are a market research analyst for Bijou AI, a WhatsApp Manglish chatbot for Malaysian SMEs.
Given a sample of recent Reddit posts from r/malaysia, identify which SME verticals and Malaysian cities are
showing the most demand / pain signals. Output JSON only:
{ "top_verticals": [{"name": "dental", "demand_score": 0-100, "evidence": "..."}],
  "top_cities": [{"name": "Petaling Jaya", "demand_score": 0-100, "evidence": "..."}],
  "top_pain_themes": [{"name": "no-shows", "evidence": "..."}],
  "recommended_targeting": "1 sentence recommendation"
}

demand_score: 0=no signal, 100=very hot right now. Use BOTH the explicit posts AND your knowledge of
current Malaysian SME market dynamics.`;
  const user = `Sample of recent r/malaysia posts (last 7 days):
${redditPosts.slice(0, 30).map((p, i) => `${i + 1}. [r/${p.subreddit}] ${p.title}\n   ${p.content.slice(0, 200)}`).join("\n\n")}

Based on these posts AND your broader knowledge of Malaysian SMEs right now (mid-2026), identify the
hottest verticals, cities, and pain themes for a RM299/mo AI chatbot that handles WhatsApp enquiries.
Output JSON.`;
  return await callGateway(sys, user, { temperature: 0.4, max_tokens: 1500, task: 'research' });
}

async function main() {
  const sinceMs = Date.now() - 7 * 24 * 60 * 60 * 1000;
  let allPosts = [];
  const errors = [];
  for (const sub of SUBREDDITS) {
    try {
      const xml = await fetchRss(sub);
      const entries = parseAtom(xml);
      const recent = entries.filter((e) => new Date(e.updated).getTime() > sinceMs);
      console.log(`  r/${sub}: ${entries.length} total, ${recent.length} in last 7d`);
      for (const e of recent) allPosts.push({ ...e, subreddit: sub });
    } catch (e) {
      errors.push({ subreddit: sub, error: e.message });
      console.log(`  r/${sub}: ${e.message.slice(0, 80)}`);
    }
    // Space out requests to avoid 429
    if (SUBREDDITS.indexOf(sub) < SUBREDDITS.length - 1) await sleep(2500);
  }
  console.log(`\nTotal posts scanned (7d): ${allPosts.length}`);

  // Filter for pain posts
  const painPosts = allPosts.filter((p) => PAIN_PATTERNS.some((re) => re.test(p.title + " " + p.content)));
  console.log(`Pain posts: ${painPosts.length}`);

  // Cluster by vertical + city
  const verticalCounts = {};
  const cityCounts = {};
  const verticalCityPairs = {};
  const painKeywords = {};
  for (const p of painPosts) {
    const text = p.title + " " + p.content;
    const v = clusterKey(text, VERTICAL_PATTERNS);
    const c = clusterKey(text, CITY_PATTERNS);
    if (v) verticalCounts[v] = (verticalCounts[v] || 0) + 1;
    if (c) cityCounts[c] = (cityCounts[c] || 0) + 1;
    if (v && c) {
      const key = `${v}__${c}`;
      verticalCityPairs[key] = (verticalCityPairs[key] || 0) + 1;
    }
    for (const re of PAIN_PATTERNS) {
      const m = text.match(re);
      if (m) painKeywords[m[0].toLowerCase()] = (painKeywords[m[0].toLowerCase()] || 0) + 1;
    }
  }

  const sortedVerticals = Object.entries(verticalCounts).sort((a, b) => b[1] - a[1]);
  const sortedCities = Object.entries(cityCounts).sort((a, b) => b[1] - a[1]);
  const sortedKeywords = Object.entries(painKeywords).sort((a, b) => b[1] - a[1]).slice(0, 15);
  const sortedPairs = Object.entries(verticalCityPairs).sort((a, b) => b[1] - a[1]).slice(0, 10);

  // Write digest
  const today = new Date().toISOString().slice(0, 10);
  const opencodeDir = path.join(__dirname, ".opencode");
  if (!fs.existsSync(opencodeDir)) fs.mkdirSync(opencodeDir, { recursive: true });
  const digest = {
    date: today,
    window_days: 7,
    sources_scanned: SUBREDDITS.length,
    errors,
    totals: { posts_scanned: allPosts.length, pain_posts: painPosts.length },
    top_verticals: sortedVerticals.slice(0, 10),
    top_cities: sortedCities.slice(0, 10),
    top_pain_keywords: sortedKeywords,
    top_vertical_city_pairs: sortedPairs.map(([k, n]) => ({ pair: k.replace("__", " in "), n })),
    sample_pain_posts: painPosts.slice(0, 10).map((p) => ({
      subreddit: p.subreddit, title: p.title.slice(0, 200), link: p.link, updated: p.updated,
    })),
  };
  fs.writeFileSync(path.join(opencodeDir, `research-${today}.json`), JSON.stringify(digest, null, 2));
  console.log(`\nWrote backend/.opencode/research-${today}.json`);

  // Insert top 5 pain posts as listener_opportunities (source='research_scan')
  let inserted = 0;
  for (const p of painPosts.slice(0, 5)) {
    const text = p.title + " " + p.content;
    const v = clusterKey(text, VERTICAL_PATTERNS);
    const c = clusterKey(text, CITY_PATTERNS);
    const painSignals = (text.match(new RegExp(PAIN_PATTERNS.map((r) => r.source).join("|"), "gi")) || [])
      .slice(0, 5).map((s) => s.toLowerCase());
    const row = {
      source: "research_scan",
      source_url: p.link,
      source_group: `r/${p.subreddit}`,
      post_excerpt: p.title.slice(0, 280),
      post_author_handle: p.author || null,
      pain_signals: [...new Set(painSignals)],
      match_score: Math.min(100, Math.round(70 + (painSignals.length * 5))),
      status: "new",
    };
    const { error } = await db.from("bjx_listener_opportunities").upsert(row, { onConflict: "source,source_url", ignoreDuplicates: true });
    if (!error) inserted += 1;
  }
  console.log(`Inserted ${inserted} opportunities into bjx_listener_opportunities`);

  // Print summary
  console.log("\n=== TOP 3 VERTICALS (from raw posts) ===");
  sortedVerticals.slice(0, 3).forEach(([k, n]) => console.log(`  ${k}: ${n} pain posts (7d)`));
  console.log("\n=== TOP 3 CITIES (from raw posts) ===");
  sortedCities.slice(0, 3).forEach(([k, n]) => console.log(`  ${k}: ${n} pain posts (7d)`));
  console.log("\n=== TOP 5 PAIN KEYWORDS (from raw posts) ===");
  sortedKeywords.slice(0, 5).forEach(([k, n]) => console.log(`  "${k}": ${n} mentions`));

  // LLM enrichment — only if we have any posts (or always, to get a knowledge-based view)
  if (env.MINIMAX_API_KEY) {
    console.log("\n=== LLM TREND ANALYSIS (knowledge + sample posts) ===");
    try {
      const llm = await llmTrendAnalysis(allPosts);
      const enriched = { ...digest, llm_analysis: llm };
      fs.writeFileSync(path.join(opencodeDir, `research-${today}.json`), JSON.stringify(enriched, null, 2));
      console.log(`Top verticals (LLM):`);
      (llm.top_verticals || []).slice(0, 5).forEach((v) => console.log(`  ${v.name}: ${v.demand_score}/100 — ${v.evidence}`));
      console.log(`Top cities (LLM):`);
      (llm.top_cities || []).slice(0, 5).forEach((c) => console.log(`  ${c.name}: ${c.demand_score}/100 — ${c.evidence}`));
      console.log(`Top pain themes (LLM):`);
      (llm.top_pain_themes || []).slice(0, 5).forEach((t) => console.log(`  "${t.name}" — ${t.evidence}`));
      console.log(`\nRecommended targeting: ${llm.recommended_targeting || "n/a"}`);
    } catch (e) {
      console.log(`  LLM analysis failed: ${e.message.slice(0, 100)}`);
    }
  }

  process.exit(0);
}

main().catch((e) => { console.error("FATAL:", e); process.exit(1); });
