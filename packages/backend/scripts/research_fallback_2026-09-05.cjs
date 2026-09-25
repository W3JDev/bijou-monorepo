// Research fallback for Bijou AI: clusters bjx_listener_opportunities from
// the last 7 days. Used when research_scan.cjs (live Reddit RSS path) is
// not usable. Weights by the existing match_score + pain_signals, with
// text-check filtering to avoid false-positive tags (e.g. "spa" -> "&amp;").

const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const envRaw = fs.readFileSync(path.join(PROJECT_ROOT, '.env'), 'utf8');
const env = {};
for (const line of envRaw.split(/\r?\n/)) {
  const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
  if (m) env[m[1]] = m[2];
}

const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_KEY);

// Vertical canonical names. Each has a regex that must hit the cleaned
// post text for the vertical to count — filters noise from stray tags
// in pain_signals.
const VERTICAL_SIGNAL = {
  'clinic': { name: 'medical',   textCheck: /\b(clinic|klinik|doctor|medical|healthcare|physio|vet)\b/ },
  'dental': { name: 'dental',    textCheck: /\b(dental|klinik\s?pergigian|orthodont|braces|implant|gigi)\b/ },
  'aesthetic': { name: 'aesthetic', textCheck: /\b(aesthetic|skincare|beauty|salon|spa|kecantikan|botox|filler|laser)\b/ },
  'salon':   { name: 'aesthetic', textCheck: /\b(salon|beauty|kecantikan|aesthetic)\b/ },
  'spa':     { name: 'aesthetic', textCheck: /\b(spa|salon|aesthetic|beauty|kecantikan)\b/ },
  'gym':     { name: 'fitness',  textCheck: /\b(gym|fitness|yoga|pilates|crossfit|taekwondo|boxing|personal\s?trainer)\b/ },
  'restaurant': { name: 'f&b',   textCheck: /\b(restaurant|cafe|café|f&b|kopitiam|mamak|bistro|bar|pub|kedai\s?makan|warung)\b/ },
  'cafe':    { name: 'f&b',      textCheck: /\b(cafe|café|kopitiam)\b/ },
  'retail':  { name: 'retail',   textCheck: /\b(shop|retail|boutique|kedai|store|ecommerce|shopee|lazada)\b/ },
  'home care': { name: 'service', textCheck: /\b(home\s?care|caregiver|care\s?giver|agency)\b/ },
};

const CITY_SIGNAL = {
  'kl': 'kl', 'kuala lumpur': 'kl', 'mont kiara': 'kl', 'bangsar': 'kl',
  'pj': 'pj', 'petaling jaya': 'pj', 'damansara': 'pj', 'ss2': 'pj',
  'klang': 'klang', 'shah alam': 'klang', 'port klang': 'klang',
  'putrajaya': 'putrajaya', 'cyberjaya': 'putrajaya',
  'subang': 'subang', 'usj': 'subang', 'puchong': 'subang',
  'penang': 'penang', 'george town': 'penang', 'pulau pinang': 'penang',
  'johor': 'johor', 'jb': 'johor', 'johor bahru': 'johor', 'iskandar': 'johor',
  'melaka': 'melaka', 'malacca': 'melaka',
  'ipoh': 'ipoh', 'perak': 'ipoh',
  'kuching': 'kuching', 'sabah': 'sabah', 'kk': 'sabah', 'kota kinabalu': 'sabah',
  'sandakan': 'sabah', 'miri': 'sabah', 'sarawak': 'sabah',
};

const PAIN_KEYWORD = {
  'no-show': 'no-show',
  'booking': 'booking-friction',
  'appointment': 'booking-friction',
  'whatsapp': 'whatsapp',
  'chatbot': 'chatbot-ai',
  'agent': 'chatbot-ai',
  'ai': 'chatbot-ai',
  'automate': 'chatbot-ai',
  'automation': 'chatbot-ai',
  'customer service': 'reply-slow',
};

function cleanText(html) {
  return (html || '')
    .replace(/&[#a-z0-9]+;/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function isUrlOk(url) {
  if (!url) return false;
  if (url.includes('reddit.comhttps://')) return false;
  if (url.includes('preview.redd.it')) return false;
  return true;
}

function topN(map, n = 3) {
  return Object.entries(map)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([k, v]) => ({ name: k, count: v }));
}

function recommendTarget(verticals, cities, pains) {
  if (!verticals.length) {
    return 'Insufficient signal — no verticals scored >= 50 in last 7d. Hold current targeting and re-run tomorrow.';
  }
  const v = verticals[0].name;
  const c = cities[0]?.name || 'Klang Valley (default)';
  const p = pains[0]?.name;
  const angle = p === 'no-show' || p === 'booking-friction'
    ? '"stop losing after-hours enquiries"'
    : p === 'whatsapp' || p === 'chatbot-ai'
    ? '"AI receptionist for WhatsApp"'
    : p === 'reply-slow' || p === 'messaging'
    ? '"never miss a customer reply"'
    : 'operational efficiency';
  return `Double down on ${v} in ${c} this week; lead with the ${angle} angle.`;
}

(async () => {
  const cutoff = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
  const { data, error } = await supabase
    .from('bjx_listener_opportunities')
    .select('id,created_at,source,source_url,source_group,post_excerpt,pain_signals,match_score,status')
    .gte('created_at', cutoff)
    .gte('match_score', 50)
    .order('match_score', { ascending: false })
    .order('created_at', { ascending: false })
    .limit(500);

  if (error) { console.error('SUPABASE_ERR', error.message); process.exit(1); }
  const rows = data || [];
  console.log('high_score_rows_7d', rows.length);

  const verticalScore = {};
  const cityScore = {};
  const painScore = {};
  const realPosts = [];

  for (const r of rows) {
    if (!isUrlOk(r.source_url)) continue;
    const clean = cleanText(r.post_excerpt);
    const signals = r.pain_signals || [];
    const score = r.match_score || 0;

    const verticalsHit = new Set();
    for (const s of signals) {
      const v = VERTICAL_SIGNAL[s.toLowerCase()];
      if (v && v.textCheck.test(clean)) verticalsHit.add(v.name);
    }
    for (const v of verticalsHit) verticalScore[v] = (verticalScore[v] || 0) + score;

    const citiesHit = new Set();
    for (const [tok, name] of Object.entries(CITY_SIGNAL)) {
      if (clean.includes(tok)) citiesHit.add(name);
    }
    for (const c of citiesHit) cityScore[c] = (cityScore[c] || 0) + score;

    const painsHit = new Set();
    for (const s of signals) {
      const p = PAIN_KEYWORD[s.toLowerCase()];
      if (p) painsHit.add(p);
    }
    for (const p of painsHit) painScore[p] = (painScore[p] || 0) + score;

    realPosts.push({
      url: r.source_url,
      group: r.source_group,
      score,
      created: r.created_at,
      pain_signals: signals,
      verticals: [...verticalsHit],
      cities: [...citiesHit],
      pains: [...painsHit],
      clean_excerpt: clean.slice(0, 240),
    });
  }

  const topVerticals = topN(verticalScore, 3);
  const topCities = topN(cityScore, 3);
  const topPains = topN(painScore, 3);

  const topPosts = realPosts
    .filter(p => p.verticals.length > 0 || p.pains.length > 0)
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return (b.verticals.length + b.pains.length) - (a.verticals.length + a.pains.length);
    })
    .slice(0, 5)
    .map(p => ({
      url: p.url,
      group: p.group,
      score: p.score,
      created: p.created,
      verticals: p.verticals,
      pains: p.pains,
      excerpt: p.clean_excerpt,
    }));

  const rec = recommendTarget(topVerticals, topCities, topPains);

  const dateMYT = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Kuala_Lumpur' });
  const digest = {
    run_at_myt: new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Kuala_Lumpur' }).replace(' ', 'T') + '+08:00',
    window: '7d',
    method: 'fallback_from_bjx_listener_opportunities',
    rows_considered: rows.length,
    rows_after_url_filter: realPosts.length,
    top_verticals: topVerticals,
    top_cities: topCities,
    top_pain_keywords: topPains,
    top_posts: topPosts,
    recommendation: rec,
  };

  const outDir = path.join(PROJECT_ROOT, 'app', '.opencode');
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  const digestPath = path.join(outDir, `research-${dateMYT}.json`);
  fs.writeFileSync(digestPath, JSON.stringify(digest, null, 2), 'utf8');
  console.log('DIGEST', digestPath);
  console.log(JSON.stringify(digest, null, 2));
})();
