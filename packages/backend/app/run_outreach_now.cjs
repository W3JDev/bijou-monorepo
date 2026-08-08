// backend/run_outreach_now.cjs
// Direct outreach run — bypasses Vercel 60s timeout, runs in parallel
// against the gateway, writes drafts straight to bjx_review_queue.
//
// Per plan §3: hard rule — never auto-send. Always writes to review_queue.
// Pick the channel per prospect: IG DM if instagram_handle, else email.

const { createClient } = require("@supabase/supabase-js");
const path = require("path");
const fs = require("fs");

// Load .env
const envText = fs.readFileSync(path.join(__dirname, "..", ".env"), "utf8");
const env = {};
for (const line of envText.split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
  if (m) env[m[1]] = m[2].trim();
}

const SUPABASE_URL = env.SUPABASE_URL;
const SUPABASE_KEY = env.SUPABASE_SERVICE_KEY;

if (!SUPABASE_URL || !SUPABASE_KEY) throw new Error("Supabase not configured");

const db = createClient(SUPABASE_URL, SUPABASE_KEY, { auth: { persistSession: false } });
const { callAI } = require("./ai-router.cjs");

async function callGateway(systemPrompt, userPrompt, opts = {}) {
  // Phase 1: route through the new AI Model Router.
  const r = await callAI({
    task: opts.task || 'outreach',
    payload: {
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
      max_tokens: opts.max_tokens || 800,
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
- Has WhatsApp Business: ${p.has_whatsapp_business}
- Has online booking: ${p.has_booking_link}
- Evidence: ${p.evidence_notes || "no specific evidence captured"}

CHANNEL HINT: ${channelHint}

Write the first-touch draft. JSON only, no markdown fences.`;
}

async function main() {
  // Pull real prospects (not manual_seed)
  const { data: prospects, error } = await db
    .from("bjx_prospects")
    .select("*")
    .neq("source", "manual_seed")
    .in("status", ["new", "scored"])
    .order("created_at", { ascending: true });
  if (error) throw error;
  console.log(`Found ${prospects.length} real prospects to draft`);

  // Run 4 in parallel
  const CONCURRENCY = 4;
  let generated = 0;
  const errors = [];
  for (let i = 0; i < prospects.length; i += CONCURRENCY) {
    const batch = prospects.slice(i, i + CONCURRENCY);
    await Promise.all(batch.map(async (p) => {
      try {
        const draft = await callGateway(OUTREACH_SYSTEM, outreachUserPrompt(p), { max_tokens: 700, task: 'outreach' });
        const payload = {
          prospect: {
            id: p.id, business_name: p.business_name, area: p.area,
            vertical: p.vertical, instagram_handle: p.instagram_handle,
            facebook_page_url: p.facebook_page_url, source: p.source,
          },
          channel: draft.channel || (p.instagram_handle ? "instagram_dm" : "email"),
          subject: draft.subject || null,
          body: draft.body || "",
          reasoning: draft.reasoning || null,
        };
        const { error: insErr } = await db.from("bjx_review_queue").insert({
          item_type: "outreach_dm",
          payload,
          source_agent: "outreach-direct",
          source_prospect_id: p.id,
          source_model: "auto/best-fast",
          priority: 60,
        });
        if (insErr) throw new Error(insErr.message);
        // Mark prospect as queued so we don't double-draft
        await db.from("bjx_prospects")
          .update({ status: "queued", updated_at: new Date().toISOString() })
          .eq("id", p.id);
        generated += 1;
        console.log(`  ✓ ${p.business_name} → ${payload.channel}`);
      } catch (e) {
        errors.push({ prospect: p.business_name, error: e.message });
        console.log(`  ✗ ${p.business_name}: ${e.message.slice(0, 100)}`);
      }
    }));
  }
  console.log(`\nGenerated: ${generated}/${prospects.length}`);
  if (errors.length) console.log(`Errors: ${errors.length}`);
  process.exit(0);
}

main().catch((e) => { console.error("FATAL:", e); process.exit(1); });
