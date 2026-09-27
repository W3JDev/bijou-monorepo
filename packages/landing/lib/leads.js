// lib/leads.js
// ---------------------------------------------------------------------------
// Shared lead persistence + owner notification for the serverless handlers
// (api/leads.js, api/chat.js, api/book.js). One place that knows the live
// `leads` table's CHECK constraints and the owner-notify channels.
//
// Live constraints (probed 2026-09-27, see migrations-py/0000_baseline.sql):
//   - email NOT NULL, CHECK valid_email: local part [A-Za-z0-9._%-] — a `+`
//     alias is REJECTED by the DB even though EMAIL_RE below accepts it.
//   - source CHECK: only VALID_SOURCES. The raw channel ("demo_chat",
//     "voice") therefore goes in utm_source.
//   - status CHECK: new | contacted | qualified | customer | lost.
// ---------------------------------------------------------------------------

import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";
import { normalizePhone } from "../utils/phone.js";

export const EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;

const VALID_SOURCES = [
  "hero_form",
  "cal_booking",
  "waitlist",
  "whatsapp_cta",
  "website",
  "referral",
];

// Map any incoming source to a valid DB source value
export function normaliseSource(raw) {
  if (!raw) return "website";
  const s = raw.toLowerCase();
  if (VALID_SOURCES.includes(s)) return s;
  if (s.includes("hero")) return "hero_form";
  if (s.includes("wait")) return "waitlist";
  if (s.includes("whats")) return "whatsapp_cta";
  if (s.includes("cal")) return "cal_booking";
  if (s.includes("referral")) return "referral";
  return "website";
}

export function getSupabase() {
  const url = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL;
  const key =
    process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;
  return url && key ? createClient(url, key) : null;
}

const TRANSCRIPT_MARK = "--- chat transcript ---\n";
const STATUS_RANK = { new: 0, contacted: 1, qualified: 2, customer: 3, lost: -1 };

// Keeps owner-written notes, appends `append`, replaces the transcript tail.
export function mergeNotes(existing, { append, transcript } = {}) {
  let [head = "", tail = ""] = (existing || "").split(TRANSCRIPT_MARK);
  head = [head.trimEnd(), append].filter(Boolean).join("\n");
  const t = transcript ?? tail;
  return [head, t && TRANSCRIPT_MARK + t].filter(Boolean).join("\n") || null;
}

/**
 * Insert or update one lead, deduped by email, then phone.
 * @param {{name?:string,email?:string,phone?:string,company?:string,industry?:string,
 *   source?:string,status?:string,transcript?:string,appendNote?:string}} input
 * @returns {Promise<{leadId:string|null,isNew:boolean,error?:string}>}
 */
export async function upsertLead(input) {
  const supabase = getSupabase();
  if (!supabase) return { leadId: null, isNew: false, error: "not_configured" };

  const email = String(input.email || "").toLowerCase().trim() || null;
  const phone = normalizePhone(input.phone) || null;
  if (!email && !phone) return { leadId: null, isNew: false, error: "no_contact" };

  let existing = null;
  for (const [col, val] of [["email", email], ["phone", phone]]) {
    if (existing || !val) continue;
    const { data, error } = await supabase
      .from("leads")
      .select("id,name,phone,company,industry,status,notes")
      .eq(col, val)
      .order("created_at", { ascending: true })
      .limit(1);
    if (error) return { leadId: null, isNew: false, error: error.code || "select_failed" };
    existing = data?.[0] || null;
  }

  const notesPatch = { append: input.appendNote, transcript: input.transcript };

  if (existing) {
    const patch = {
      notes: mergeNotes(existing.notes, notesPatch),
      ...(input.name && { name: input.name.trim() }),
      ...(phone && !existing.phone && { phone }),
      ...(input.company && !existing.company && { company: input.company.trim() }),
      ...(input.industry && !existing.industry && { industry: input.industry }),
      // Never downgrade (e.g. a "customer" re-booking stays "customer").
      ...(input.status &&
        (STATUS_RANK[input.status] ?? 0) > (STATUS_RANK[existing.status] ?? 0) && {
          status: input.status,
        }),
    };
    const { error } = await supabase.from("leads").update(patch).eq("id", existing.id);
    if (error) return { leadId: existing.id, isNew: false, error: error.code || "update_failed" };
    return { leadId: existing.id, isNew: false };
  }

  // email is NOT NULL in the table — a phone-only contact can't be a new row.
  if (!email) return { leadId: null, isNew: false, error: "email_required" };

  const row = {
    name: (input.name || input.company || email.split("@")[0]).trim(),
    email,
    phone,
    company: input.company?.trim() || null,
    industry: input.industry || null,
    source: normaliseSource(input.source),
    utm_source: input.source || null,
    status: input.status || "new",
    lead_score: input.status === "qualified" ? 60 : 30,
    notes: mergeNotes(null, notesPatch),
  };
  const { data, error } = await supabase.from("leads").insert(row).select("id").single();
  if (error) return { leadId: null, isNew: false, error: error.code || "insert_failed" };
  return { leadId: data?.id || null, isNew: true };
}

/**
 * Owner notification over the two existing channels: WhatsApp via the Fly
 * backend's /api/send (INTERNAL_API_TOKEN) and Resend email to EMAIL_NOTIFY.
 * Never throws — a notify failure must not break the user's flow.
 */
export async function notifyOwner({ title, lead, extra = "" }) {
  const lines =
    `Name: ${lead.name || "N/A"}\nEmail: ${lead.email || "N/A"}\n` +
    `Phone: ${lead.phone ? "+" + lead.phone : "N/A"}\n` +
    `Company: ${lead.company || "N/A"}\nSource: ${lead.source || "N/A"}` +
    (extra ? `\n\n${extra}` : "");
  const result = { whatsapp: false, email: false };

  const token = process.env.INTERNAL_API_TOKEN;
  if (token) {
    try {
      const r = await fetch("https://bijou-production.fly.dev/api/send", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Internal-Token": token },
        body: JSON.stringify({ to: "60174106981@s.whatsapp.net", message: `${title}\n\n${lines}` }),
      });
      result.whatsapp = r.ok;
      if (!r.ok) console.warn("WhatsApp owner-notify failed:", r.status);
    } catch (e) {
      console.warn("WhatsApp notification skipped:", e.message);
    }
  } else {
    console.warn("⚠️  INTERNAL_API_TOKEN not set — skipping WhatsApp owner-notify");
  }

  const resendKey = process.env.RESEND_API_KEY;
  const notifyEmail = process.env.EMAIL_NOTIFY;
  if (resendKey && notifyEmail) {
    try {
      const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
      const { error } = await new Resend(resendKey).emails.send({
        from: process.env.EMAIL_FROM || "Bijou AI <hello@mybijou.xyz>",
        to: notifyEmail,
        subject: `${title}: ${lead.name || lead.email || "lead"} (${lead.company || lead.source || "website"})`,
        html: `<pre style="font-family:inherit;white-space:pre-wrap">${esc(lines)}\n\nTime: ${new Date().toLocaleString("en-MY", { timeZone: "Asia/Kuala_Lumpur" })} MYT</pre>`,
      });
      result.email = !error;
      if (error) console.warn("Owner notify email failed:", error.message);
    } catch (e) {
      console.warn("Owner notify email failed:", e.message);
    }
  }
  return result;
}

// ---- Demo-chat contact extraction (regex only, no LLM call) ----------------

const OUR_EMAILS = /@mybijou\.xyz$/i;
const OUR_PHONE = "60174106981";
const NAME_WORD = "[A-Z][\\p{L}'\\-]*";
const NAME = `(${NAME_WORD}(?:\\s+${NAME_WORD}){0,3})`;

// ponytail: heuristics for name/business; the full transcript goes to notes,
// so the owner still sees anything the regexes miss.
/**
 * @param {{role:string,content:string}[]} turns user + model turns, oldest first
 */
export function extractContact(turns) {
  const out = { name: "", email: "", phone: "", company: "", industry: "" };
  turns.forEach((t, i) => {
    if (t.role !== "user") return;
    const text = String(t.content || "");
    const prevBot = String(turns[i - 1]?.role !== "user" ? turns[i - 1]?.content || "" : "");

    const email = text.match(/[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/)?.[0];
    if (email && !OUR_EMAILS.test(email)) out.email = email.toLowerCase();

    // Emails stripped first so digits in "jo123456789@x.com" aren't a phone.
    for (const m of text.replace(/\S+@\S+/g, " ").matchAll(/\+?\d[\d\s\-().]{6,18}\d/g)) {
      const p = normalizePhone(m[0]);
      // >=10 digits: keeps dates like 2026-10-01 from reading as a phone.
      if (p.length >= 10 && p !== OUR_PHONE) out.phone = p;
    }

    const name =
      text.match(new RegExp(`\\b(?:[Mm]y name(?: is|'s)|[Cc]all me|[Tt]his is|[Nn]ame(?: is|:))\\s+${NAME}`, "u"))?.[1] ||
      text.match(new RegExp(`\\b(?:I'm|I am|Im|i'm|i am)\\s+${NAME}`, "u"))?.[1] ||
      // Short reply straight after the bot asked for the name.
      (/\bname\b/i.test(prevBot) && /^[\p{L}'\- ]{2,40}$/u.test(text.trim()) && text.trim().split(/\s+/).length <= 4
        ? text.trim()
        : "");
    if (name) out.name = name.replace(/\s+(?:From|And|Here)\b.*$/, "").trim();

    const company = text.match(
      new RegExp(`\\b(?:called|named|business is|company is|clinic is|shop is)\\s+(${NAME_WORD}(?:\\s+(?:&|${NAME_WORD})){0,4})`, "u"),
    )?.[1];
    if (company) out.company = company.replace(/[.,!?]+$/, "");
    else if (/\bbusiness\b/i.test(prevBot) && !email && text.length <= 80) out.industry = text.trim();
  });
  return out;
}
