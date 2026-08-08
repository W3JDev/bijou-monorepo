// backend/run_outreach_topfit.cjs
// Outreach only on top-fit prospects (fit >= 60). Joins bjx_prospects with
// bjx_prospect_scores. Skips ones that already have a pending draft.

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
    task: opts.task || 'outreach',
    payload: {
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
      max_tokens: opts.max_tokens || 700,
      temperature: opts.temperature ?? 0.7,
    },
  });
  if (!r.ok) throw new Error(r.error || 'router call failed');
  const content = String(r.text || '').replace(/^```json?\s*/i, '').replace(/```$/i, '').trim();
  if (!content) throw new Error('Empty content');
  return JSON.parse(content);
}

const OUTREACH_SYSTEM = `You are Bijou AI's outreach agent for the Malaysian SME market.
Write a personalised first-touch DM/email in Manglish for a single prospect.
Target vertical: aesthetic or dental clinic in Klang Valley.
Voice: warm, professional, never spammy. Reference one specific thing you noticed.

Output JSON: { subject, body, channel, reasoning }
- subject: <60 chars, no emojis (only for email)
- body: <300 words, max 2 emoji, max 1 'lah', no "boleh tahu" or "no hal"
- channel: 'email' | 'instagram_dm' (pick IG if prospect has Instagram, else email)
- reasoning: 1-sentence why this opener fits

Do NOT include marketing claims that aren't true. Do NOT offer discounts.
For Instagram DM: no subject line, opener should be casual, max 2-3 short paragraphs.
For email: include subject, full body with sign-off.`;

function outreachUserPrompt(p) {
  const channelHint = p.instagram_handle
    ? "Instagram DM (the prospect is active on Instagram, so reach them there)"
    : "Email (no Instagram on file, so reach them via email)";
  return `Prospect:
- Business: ${p.business_name}
- Vertical: ${p.vertical || "unknown"}
- Area: ${p.area || "Klang Valley"}, ${p.city || "Kuala Lumpur"}
- Instagram: ${p.instagram_handle || "not on file"}
- Facebook: ${p.facebook_page_url || "not on file"}
- Website: ${p.website || "not on file"}
- Has WhatsApp Business: ${p.has_whatsapp_business}
- Has online booking: ${p.has_booking_link}
- Evidence: ${p.evidence_notes || "no specific evidence captured"}
- Fit score from screener: ${p.fit_score}/100 (0-30 rejected, 30-60 lukewarm, 60-100 hot)

CHANNEL HINT: ${channelHint}

Write the first-touch draft. JSON only, no markdown fences.`;
}

async function main() {
  const minFit = parseInt(process.argv[2] || "50", 10);
  const limit = parseInt(process.argv[3] || "30", 10);
  // Find scored prospects with fit >= minFit, join with their full data
  const { data: scores, error: sErr } = await db
    .from("bjx_prospect_scores")
    .select("prospect_id, fit_score, reasoning")
    .gte("fit_score", minFit)
    .order("fit_score", { ascending: false })
    .limit(limit);
  if (sErr) throw sErr;
  console.log(`Found ${scores.length} scored prospects with fit >= ${minFit}`);

  // Check which already have a pending draft
  const ids = scores.map((s) => s.prospect_id);
  const { data: existingDrafts } = await db
    .from("bjx_review_queue")
    .select("source_prospect_id, status")
    .in("source_prospect_id", ids)
    .eq("status", "pending");
  const draftedIds = new Set((existingDrafts || []).map((d) => d.source_prospect_id));
  console.log(`${draftedIds.size} already have pending drafts; skipping those`);

  // Fetch full prospect data
  const { data: prospects, error: pErr } = await db
    .from("bjx_prospects")
    .select("*")
    .in("id", ids);
  if (pErr) throw pErr;

  // Merge score + prospect
  const merged = scores
    .map((s) => ({ ...prospects.find((p) => p.id === s.prospect_id), fit_score: s.fit_score, score_reasoning: s.reasoning }))
    .filter((p) => p.id && !draftedIds.has(p.id));
  console.log(`Will draft ${merged.length} fresh prospects`);

  let generated = 0, errors = 0;
  const CONCURRENCY = 4;
  for (let i = 0; i < merged.length; i += CONCURRENCY) {
    const batch = merged.slice(i, i + CONCURRENCY);
    await Promise.all(batch.map(async (p) => {
      try {
        const draft = await callGateway(OUTREACH_SYSTEM, outreachUserPrompt(p), { max_tokens: 700, task: 'outreach' });
        const payload = {
          prospect: {
            id: p.id, business_name: p.business_name, area: p.area,
            vertical: p.vertical, instagram_handle: p.instagram_handle,
            facebook_page_url: p.facebook_page_url, source: p.source, fit_score: p.fit_score,
          },
          channel: draft.channel || (p.instagram_handle ? "instagram_dm" : "email"),
          subject: draft.subject || null,
          body: draft.body || "",
          reasoning: draft.reasoning || null,
          fit_score: p.fit_score,
        };
        await db.from("bjx_review_queue").insert({
          item_type: "outreach_dm", payload,
          source_agent: "outreach-topfit", source_prospect_id: p.id,
          source_model: "auto/best-fast", priority: p.fit_score,
        });
        await db.from("bjx_prospects")
          .update({ status: "queued", updated_at: new Date().toISOString() })
          .eq("id", p.id);
        generated += 1;
        console.log(`  ✓ [${p.fit_score}] ${p.business_name} → ${payload.channel}`);
      } catch (e) {
        errors += 1;
        console.log(`  ✗ [${p.fit_score}] ${p.business_name}: ${e.message.slice(0, 100)}`);
      }
    }));
  }
  console.log(`\n=== Done: ${generated} drafted, ${errors} errors of ${merged.length} ===`);
  process.exit(0);
}

main().catch((e) => { console.error("FATAL:", e); process.exit(1); });
