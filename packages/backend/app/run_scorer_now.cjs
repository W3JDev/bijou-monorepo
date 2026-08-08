// backend/run_scorer_now.cjs
// Parallel scorer — bypasses Vercel 60s limit, runs 4 gateway calls in parallel.
// Writes fit scores to bjx_prospect_scores, marks prospect as scored or rejected.

const { createClient } = require("@supabase/supabase-js");
const path = require("path");
const fs = require("fs");

const envText = fs.readFileSync(path.join(__dirname, "..", ".env"), "utf8");
const env = {};
for (const line of envText.split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
  if (m) env[m[1]] = m[2].trim();
}

const db = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_KEY, { auth: { persistSession: false } });
const { callAI } = require("./ai-router.cjs");

async function callGateway(systemPrompt, userPrompt, opts = {}) {
  // Phase 1: route through the new AI Model Router.
  const r = await callAI({
    task: opts.task || 'scorer',
    payload: {
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
      max_tokens: opts.max_tokens || 400,
      temperature: opts.temperature ?? 0.3,
    },
  });
  if (!r.ok) throw new Error(r.error || 'router call failed');
  const content = String(r.text || '').replace(/^```json?\s*/i, '').replace(/```$/i, '').trim();
  if (!content) throw new Error('Empty content');
  return JSON.parse(content);
}

const SCORER_SYSTEM = `You are Bijou AI's prospect scoring agent. Evaluate Malaysian SME businesses (aesthetic & dental clinics, Klang Valley) for fit with a RM299/mo Manglish-first chatbot for appointment-driven businesses.

Score 5 binary signals, each true/false, with a one-sentence reasoning:
- appointment_driven
- active_whatsapp
- owner_reachable
- evidence_missed_enquiries
- active_online_presence

Output JSON only:
{ "appointment_driven": bool, "active_whatsapp": bool, "owner_reachable": bool, "evidence_missed_enquiries": bool, "active_online_presence": bool, "reasoning": str }`;

function scoreUserPrompt(p) {
  return `Business to score:
- Name: ${p.business_name}
- Vertical: ${p.vertical || "unknown"}
- Area: ${p.area || "Klang Valley"}, ${p.city || "Kuala Lumpur"}
- Instagram: ${p.instagram_handle || "not on file"}
- Facebook: ${p.facebook_page_url || "not on file"}
- Website: ${p.website || "not on file"}
- Has WhatsApp Business: ${p.has_whatsapp_business}
- Has online booking: ${p.has_booking_link}
- Evidence: ${p.evidence_notes || "none captured"}

Score the 5 signals. JSON only.`;
}

function computeScore(s) {
  return (
    (s.appointment_driven ? 30 : 0) +
    (s.active_whatsapp ? 20 : 0) +
    (s.owner_reachable ? 20 : 0) +
    (s.evidence_missed_enquiries ? 20 : 0) +
    (s.active_online_presence ? 10 : 0)
  );
}

async function main() {
  const limit = parseInt(process.argv[2] || "60", 10);
  const { data: prospects, error } = await db
    .from("bjx_prospects")
    .select("*")
    .eq("status", "new")
    .order("created_at", { ascending: true })
    .limit(limit);
  if (error) throw error;
  console.log(`Scoring ${prospects.length} prospects (4 parallel)...`);
  let scored = 0, errors = 0;
  const CONCURRENCY = 4;
  for (let i = 0; i < prospects.length; i += CONCURRENCY) {
    const batch = prospects.slice(i, i + CONCURRENCY);
    await Promise.all(batch.map(async (p) => {
      try {
        const s = await callGateway(SCORER_SYSTEM, scoreUserPrompt(p), { temperature: 0.3, max_tokens: 400, task: 'scorer' });
        const fit = computeScore(s);
        await db.from("bjx_prospect_scores").insert({
          prospect_id: p.id, fit_score: fit,
          appointment_driven: !!s.appointment_driven,
          active_whatsapp: !!s.active_whatsapp,
          owner_reachable: !!s.owner_reachable,
          evidence_missed_enquiries: !!s.evidence_missed_enquiries,
          active_online_presence: !!s.active_online_presence,
          model: "auto/best-fast", prompt_version: "2026-07-30",
          reasoning: s.reasoning || null,
        });
        const newStatus = fit < 30 ? "rejected" : "scored";
        await db.from("bjx_prospects").update({
          status: newStatus,
          rejection_reason: newStatus === "rejected" ? `fit_score ${fit} < 30` : null,
          updated_at: new Date().toISOString(),
        }).eq("id", p.id);
        scored += 1;
        process.stdout.write(`  ✓ ${p.business_name} (fit=${fit}) `);
      } catch (e) {
        errors += 1;
        process.stdout.write(`  ✗ ${p.business_name}: ${e.message.slice(0, 60)} `);
      }
    }));
    if ((i + CONCURRENCY) % 20 === 0 || (i + CONCURRENCY) >= prospects.length) {
      console.log(`\n[${Math.min(i + CONCURRENCY, prospects.length)}/${prospects.length}] ${scored} scored, ${errors} errors`);
    }
  }
  console.log(`\n=== Done: ${scored} scored, ${errors} errors of ${prospects.length} total ===`);
  process.exit(0);
}

main().catch((e) => { console.error("FATAL:", e); process.exit(1); });
