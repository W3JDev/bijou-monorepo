#!/usr/bin/env node
// Create-or-update the "Bijou Sales Concierge" Telnyx AI Assistant and point
// the sales line at it. Idempotent: finds the assistant by exact name and
// updates it in place instead of creating a duplicate.
//
//   node --env-file=.env packages/voice/scripts/setup-telnyx-assistant.mjs \
//     [--base-url https://www.mybijou.xyz] [--number +13079999692] [--no-assign] [--dry-run]
//
// Env: TELNYX_API_KEY (required), TELNYX_API_BASE (default https://api.telnyx.com/v2).
// API: POST /ai/assistants (create), POST /ai/assistants/{id} (update),
//      PATCH /phone_numbers/{id} {connection_id: <assistant's default_texml_app_id>} (assign).
// Rollback of the number: PATCH /phone_numbers/{id} with the previous connection_id
// (saved in the telnyx-backup-*.json taken before the first run).

const args = process.argv.slice(2);
const flag = (n) => args.includes(n);
const opt = (n, d) => (args.includes(n) ? args[args.indexOf(n) + 1] : d);

const NAME = "Bijou Sales Concierge";
const BASE_URL = opt("--base-url", "https://www.mybijou.xyz").replace(/\/$/, "");
const NUMBER = opt("--number", "+13079999692");
const API = process.env.TELNYX_API_BASE || "https://api.telnyx.com/v2";
const KEY = process.env.TELNYX_API_KEY;
if (!KEY) throw new Error("TELNYX_API_KEY not set (run with node --env-file=.env)");

async function tx(method, path, body) {
  const r = await fetch(API + path, {
    method,
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json", Accept: "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await r.json().catch(() => null);
  if (!r.ok) throw new Error(`${method} ${path} -> ${r.status}: ${JSON.stringify(json?.errors ?? json).slice(0, 500)}`);
  return json;
}

const INSTRUCTIONS = `You are Bijou, the voice sales concierge for Bijou AI. You are on a live phone or web call, so speak like a friendly person on the phone: short, warm, natural US English. One to two sentences per turn. Ask ONE question at a time. Never read out URLs, lists or formatting.

WHAT BIJOU AI IS (only these facts; never invent pricing, results, features or client names):
- A done-for-you AI agent service for businesses. We build, deploy and manage a WhatsApp and Telegram AI agent for the client, who doesn't lift a finger.
- The agent replies 24/7, answers FAQs from the client's knowledge base, books appointments, qualifies leads, follows up, and alerts the owner with full context when a human is needed.
- Handles English and major world languages and mirrors the customer's tone in the client's brand voice.
- Price: 2,500 US dollars one-time setup, plus 499 dollars a month, fully managed. No per-message fees, no annual lock-in, cancel anytime, 30-day money-back guarantee.
- Live in days, not months. Works well for real estate, clinics, professional services, agencies and service businesses.
- If you don't know something, say the founder can answer it on the call. Do not guess.

YOUR GOAL ON EVERY CALL, in this order, one step at a time:
1. Ask their name. Use it from then on. Never ask twice.
2. Ask what kind of business they run.
3. Ask what's frustrating them most right now, for example missed messages after hours or slow replies. Briefly explain how Bijou helps with THAT specific pain.
4. Get contact details: their email address (required to save them) and their WhatsApp number. The caller ID is {{telnyx_end_user_target}}. If it starts with a plus sign, ask "Is the number you're calling from your WhatsApp?" and use it if yes. If it does not start with a plus sign (a website call), never read it out; just ask for their WhatsApp number with country code. Read the email back, spelled out, to confirm.
5. As soon as you have name and email, call save_lead. Do this before booking.
6. Offer a free 30-minute call with the founder. Ask which day suits them and what city or time zone they're in; convert that to an IANA time zone like America/New_York, Europe/London or Asia/Kuala_Lumpur.
7. Call check_slots for that date. Offer at most two or three times, spoken naturally. When they pick one, call book_meeting with that slot's exact start value.
8. Only after book_meeting returns ok true: confirm the booked day and time and say a calendar invite goes to their email. Then close warmly and use hangup.

TOOL RULES:
- Today is {{telnyx_current_date}} (UTC now: {{telnyx_current_time}}). Dates you send must be YYYY-MM-DD and in the future.
- save_lead: send name, email, phone in international format with plus sign if you have it, company if given, industry as business type plus pain point (for example "Dental clinic - missing after-hours WhatsApp enquiries"), and source "voice".
- If save_lead fails, don't mention errors; just continue.
- If check_slots or book_meeting fails, times out, or returns anything that is not a clear list of slots or a booking with ok true (for example an HTML page or an error), do NOT retry more than once and do NOT make up times. Say: "Our booking system isn't letting me confirm a time right now, so our founder will WhatsApp you personally to lock one in." Make sure save_lead has been called, then close warmly and hang up.
- ONLY say a meeting is booked, or that a calendar invite is coming, if book_meeting returned ok true with a booking. Otherwise never claim a booking, a time, or an invite.
- Never tell the caller about tools, APIs or systems.

CONTACT (only if asked how to reach a human): the founder is on WhatsApp at plus 6 0 1 7 4 1 0 6 9 8 1, email jewel at mybijou dot x y z.

If the caller is not a prospect (wrong number, spam, job seeker), be polite, keep it brief and end the call.`;

const jsonHeaders = [{ name: "Content-Type", value: "application/json" }];
const str = (description, extra = {}) => ({ type: "string", description, ...extra });

const tools = [
  {
    type: "webhook",
    timeout_ms: 8000,
    webhook: {
      name: "save_lead",
      description: "Save the caller as a sales lead. Call once you have their name and email.",
      url: `${BASE_URL}/api/leads`,
      method: "POST",
      headers: jsonHeaders,
      body_parameters: {
        type: "object",
        properties: {
          name: str("Caller's full name"),
          email: str("Caller's email address, confirmed by reading it back"),
          phone: str("WhatsApp/phone number in international format with +, e.g. +14155550123"),
          company: str("Business name, if given"),
          industry: str("Business type plus main pain point"),
          source: str("Always the literal value voice", { enum: ["voice"] }),
        },
        required: ["name", "email", "source"],
      },
    },
  },
  {
    type: "webhook",
    timeout_ms: 8000,
    webhook: {
      name: "check_slots",
      description: "Get available 30-minute slots with the founder for one date.",
      url: `${BASE_URL}/api/book`,
      method: "GET",
      headers: jsonHeaders,
      query_parameters: {
        type: "object",
        properties: {
          date: str("Date as YYYY-MM-DD"),
          tz: str("Caller's IANA time zone, e.g. America/New_York"),
        },
        required: ["date", "tz"],
      },
    },
  },
  {
    type: "webhook",
    timeout_ms: 10000,
    webhook: {
      name: "book_meeting",
      description: "Book a 30-minute call with the founder in a slot returned by check_slots.",
      url: `${BASE_URL}/api/book`,
      method: "POST",
      headers: jsonHeaders,
      body_parameters: {
        type: "object",
        properties: {
          name: str("Caller's full name"),
          email: str("Caller's email"),
          phone: str("Phone in international format with +"),
          start: str("Exact slot start from check_slots, ISO 8601"),
          timeZone: str("Caller's IANA time zone"),
          notes: str("Business type and pain point, one line"),
          source: str("Always the literal value voice", { enum: ["voice"] }),
        },
        required: ["name", "email", "start", "timeZone", "source"],
      },
    },
  },
  { type: "hangup", hangup: { description: "End the call after closing warmly." } },
];

const assistant = {
  name: NAME,
  description: "Bijou AI inbound sales line: qualifies prospects, saves lead, books a founder call.",
  // Non-reasoning, fast, no BYO key needed on this account. Rejected: google/* (needs our own
  // key, err 10015), openai/gpt-4o-mini (not allowed for assistants, err 10027),
  // moonshotai/Kimi-K2.6 (leaked its chain-of-thought into replies -> spoken aloud on a call).
  model: opt("--model", "openai/gpt-4.1"),
  instructions: INSTRUCTIONS,
  greeting: "Hi, this is Bijou from Bijou AI! Who am I speaking with?",
  tools,
  enabled_features: ["telephony"],
  voice_settings: { voice: "Telnyx.Ultra.a5136bf9-224c-4d76-b823-52bd5efcffcc", voice_speed: 1 },
  transcription: { model: "deepgram/flux", language: "en" },
  // supports_unauthenticated_web_calls is what lets the landing-page widget
  // (<telnyx-ai-agent agent-id=...>) call this assistant with no credential.
  telephony_settings: { supports_unauthenticated_web_calls: true, time_limit_secs: 900 },
  widget_settings: { theme: "dark", start_call_text: "Talk to Bijou now", default_state: "collapsed" },
};

if (flag("--dry-run")) {
  console.log(JSON.stringify({ ...assistant, instructions: `${INSTRUCTIONS.length} chars` }, null, 2));
  process.exit(0);
}

// Find by exact name (list is small; paginate defensively).
const list = await tx("GET", "/ai/assistants");
const existing = (list.data || []).filter((a) => a.name === NAME);
if (existing.length > 1) console.warn(`WARN: ${existing.length} assistants named "${NAME}", updating the first`);

const saved = existing[0]
  ? await tx("POST", `/ai/assistants/${existing[0].id}`, assistant)
  : await tx("POST", "/ai/assistants", assistant);
console.log(`${existing[0] ? "updated" : "created"} assistant ${saved.id}`);
console.log("tool urls:", saved.tools?.filter((t) => t.webhook).map((t) => `${t.webhook.name} ${t.webhook.method} ${t.webhook.url}`));

const texmlApp = saved.telephony_settings?.default_texml_app_id;
console.log("default_texml_app_id:", texmlApp);

if (!flag("--no-assign")) {
  if (!texmlApp) throw new Error("assistant has no default_texml_app_id; cannot assign number");
  const nums = await tx("GET", `/phone_numbers?filter[phone_number]=${encodeURIComponent(NUMBER)}`);
  const num = nums.data?.[0];
  if (!num) throw new Error(`number ${NUMBER} not found on this account`);
  if (num.connection_id === texmlApp) {
    console.log(`${NUMBER} already on ${texmlApp}`);
  } else {
    const upd = await tx("PATCH", `/phone_numbers/${num.id}`, { connection_id: texmlApp });
    console.log(`${NUMBER}: ${num.connection_id} (${num.connection_name}) -> ${upd.data.connection_id} (${upd.data.connection_name})`);
  }
}
