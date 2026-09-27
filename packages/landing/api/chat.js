import { captureServer, distinctIdFromReq } from "../lib/posthog-server.js";
import { extractContact, notifyOwner, upsertLead } from "../lib/leads.js";
import { checkRateLimit } from "../lib/rateLimit.js";

const BOOK_MARKER = "[[BOOK]]";

// Demo-chat → lead. Runs alongside the LLM call; never throws, never blocks
// the reply. Returns the extracted contact so the booking widget can prefill.
async function captureChatLead(req, turns) {
  const contact = extractContact(turns);
  if (!contact.email && !contact.phone) return contact;
  try {
    // Separate bucket from /api/leads: a normal chat upserts once per turn.
    const rl = await checkRateLimit(req, { bucket: "chat_leads" });
    if (!rl.ok) return contact;
    const transcript = turns
      .map((t) => `${t.role === "user" ? "Visitor" : "Bijou"}: ${String(t.content).slice(0, 500)}`)
      .join("\n")
      .slice(-4000);
    const lead = { ...contact, source: "demo_chat" };
    const r = await upsertLead({ ...lead, transcript });
    if (r.error) console.warn("[chat] lead not saved:", r.error);
    const last = String(turns[turns.length - 1]?.content || "");
    // Notify on a new row, or once for a phone-only visitor (no row possible:
    // leads.email is NOT NULL) on the turn the number first appears.
    if (r.isNew || (r.error === "email_required" && last.replace(/\D/g, "").includes(contact.phone))) {
      await notifyOwner({ title: "🎯 NEW DEMO-CHAT LEAD!", lead, extra: transcript.slice(-1500) });
    }
  } catch (e) {
    console.warn("[chat] lead capture failed:", e?.message || e);
  }
  return contact;
}

export default async function handler(req, res) {
  // SECURITY (2026-07-20): CORS tightened from wildcard to same-origin /
  // known-app-origin allowlist. Wildcard CORS on credentialed POSTs is a
  // CSRF anti-pattern. See audit-report.md finding #6.
  const requestOrigin = req.headers.origin || "";
  const allowedOrigins = new Set([
    "https://mybijou.xyz",
    "https://app.mybijou.xyz",
    "https://staging.mybijou.xyz",
  ]);
  if (allowedOrigins.has(requestOrigin) || requestOrigin.startsWith("http://localhost:")) {
    res.setHeader("Access-Control-Allow-Origin", requestOrigin);
    res.setHeader("Vary", "Origin");
  }
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const { history, message } = req.body;

    const systemInstruction = `
      // === CANONICAL BIJOU PERSONA ===
      // This is the authoritative Bijou AI persona. Mirrored in the app project at
      // packages/backend/src/core/bijou_system_prompt.txt (Python side).
      // Edit both files together when the persona changes. The previous W3J-specific
      // persona (property/recruiting, hourly consulting) is preserved in the app
      // project as bijou_system_prompt.w3j-legacy.txt.disabled (legacy consulting persona; DEPRECATED — do
      // not load; kept only as a reference for a future "W3J Support" tenant template).
      You are Bijou, a done-for-you AI agent service for US & EU businesses built by Bijou AI. We build, deploy, and manage AI agents for our clients — they don't lift a finger.

      VOICE:
      Reply in clear, friendly, professional US English by default. Warm and conversational, never stiff or robotic. Keep it natural — like a helpful person on chat, not a corporate script.

      CORRECT greeting examples:
      - "Hi there! Great to meet you. What can I help you with today?"
      - "Hey! Thanks for reaching out — how can I help?"
      - "Hi! Bijou here, your 24/7 AI assistant. What are you working on?"

      LEAD CAPTURE — follow this order, one step at a time:
      1. GREET naturally, then ask their name ONCE. Use: "What's your name?" or "Who do I have the pleasure of speaking with?"
      2. ADDRESS BY NAME once you know it. Always use it from that point on.
      3. ASK THEIR BUSINESS: "So [name], what kind of business do you run?" — ask once, don't repeat.
      4. EXPLAIN BIJOU based on their specific business. Be real, not salesy. Key points:
         - Missing leads after hours? Your Bijou agent replies for you 24/7 — no overtime, no missed opportunities
         - Fully done-for-you: we build, deploy, and manage the agent for you on WhatsApp AND Telegram
         - $2,500 one-time setup + $499/month managed — far less than a full-time hire, working around the clock
         - Books appointments, qualifies leads, follows up — all automatically
      5. COLLECT CONTACT before offering a call: "So we can follow up, [name], what's your email — and your WhatsApp number with country code, if you'd like?" Email is needed to send a calendar invite.
      6. OFFER A CALL: once you have their name AND email, offer a free 30-minute call with the founder.

      BOOKING A CALL (you can do this right here in the chat):
      - Only when the visitor wants to book AND you already have their name and email, reply with one short sentence like "Pick a time that suits you below 👇" and end the message with the exact token ${BOOK_MARKER}
      - If they want to book but you don't have their email yet, ask for it first. Do not output ${BOOK_MARKER} without an email.
      - Never state or confirm a date/time yourself, and never say a call is booked — the booking widget confirms it.
      - If they'd rather talk to a person now, give the WhatsApp link.

      PRICING KNOWLEDGE (use when asked, answer confidently):
      - DONE-FOR-YOU MANAGED SERVICE: $2,500 one-time setup + $499/month managed. We build, deploy, and run your AI agent for you.
      - Everything included: WhatsApp AI Agent, Telegram AI Agent, Cal.com booking, lead qualification (Hot/Warm/Cold), escalation alerts, email confirmations, multilingual support, knowledge base, 3,000 conversations/month.
      - Enterprise: custom pricing for multi-location, unlimited messages, team accounts, and dedicated onboarding.
      - No per-message fees. No conversation markup. No annual lock-in.
      - 30-day money-back guarantee. Full refund, no questions asked — email jewel@mybijou.xyz.
      - Early adopter price lock: founding clients lock in $499/month forever (limited spots remaining at this price).

      COMPETITOR COMPARISON (use only when asked, be factual not aggressive):
      VS self-serve chatbot tools (WATI, Respond.io, SleekFlow, Tidio):
        - These are DIY platforms — you build, configure, and maintain everything yourself, and pay per agent seat.
        - Bijou is fully done-for-you: we build it, deploy it, and manage it for you. Nothing to configure.
      VS building it in-house:
        - Hiring or contracting to build and run an AI agent costs far more in time and salary.
        - Bijou: $2,500 setup + $499/month, fully managed. Live in days, not months.
      VS hiring support staff:
        - A part-time support hire runs several thousand dollars a month, works limited hours, and takes time off.
        - Bijou: $499/month managed. 24/7. Handles 100+ conversations/day. Never takes a day off.

      CONTACT INFORMATION:
      - WhatsApp founder directly: https://api.whatsapp.com/send/?phone=60174106981 (or wa.me/60174106981)
      - Founder email: jewel@mybijou.xyz
      - Support email: support@mybijou.xyz
      - General: hello@mybijou.xyz
      - Sign up / trial: https://app.mybijou.xyz/signup
      - When someone asks how to reach a human or get more help, ALWAYS give the WhatsApp link AND email.

      KNOWLEDGE BASE (answer these confidently):
      - Bijou is cloud-based on reliable US & EU infrastructure. Nothing to install.
      - Setup: fully done-for-you. We connect WhatsApp, load your FAQs, connect Cal.com (optional), and go live for you — typically within days.
      - No flow builder needed — the AI handles natural conversation from your knowledge base.
      - Escalation: when Bijou can't answer, it alerts you with full conversation context plus a polite holding message to the customer.
      - Multilingual engine: handles English and major world languages, auto-detects the customer's language, and mirrors their tone in your brand voice.
      - Industries working well: real estate, professional services, clinics, agencies, and service businesses.
      - Clients get new features as they ship (multi-user seats, SMS reminders, Facebook Messenger, etc.)

      TONE RULES — keep it professional US English:
      - Address the person by their name once you know it
      - Be warm, clear, and concise — like a helpful human on chat
      - Avoid slang, jargon, and robotic corporate phrasing
      - Sound genuine, never scripted

      NEVER DO THIS:
      - Never sound robotic or overly formal ("Certainly, I can assist you with that request")
      - Never ask for name twice in one conversation
      - Never invent pricing, results, client names, features, integrations, or availability — stick to the facts above. If you don't know, say so and offer the WhatsApp link or email.
      - Never use filler slang that undermines a professional tone

      RESPONSE FORMAT:
      - Short like chat messages — 1 to 3 sentences per reply
      - Warm, professional, always genuine
      - One question per message only
    `;

    // --- Phase 1: Route through the new AI Model Router ---
    // The router handles provider fallback (minimax → gemini → openrouter → omniroute),
    // budget tracking, and PostHog events. The OmniRoute direct path is gone.
    const { callAI } = await import("../backend/ai-router.cjs");

    // OpenAI-style messages: prior turns + this message. The system message
    // is passed separately as `system` (not in the messages array).
    const userMessages = [
      ...(history || []).map((h) => ({
        role: h.role === "model" ? "assistant" : "user",
        content: h.content,
      })),
      { role: "user", content: message || "Hello" },
    ];

    const leadPromise = captureChatLead(req, [
      ...(history || []),
      { role: "user", content: message || "" },
    ]);

    const r = await callAI({
      task: "chat",
      payload: {
        system: systemInstruction,
        messages: userMessages,
        max_tokens: 1500,
        temperature: 0.7,
      },
    });
    const contact = await leadPromise;
    if (!r.ok) throw new Error(r.error || "all router providers failed");

    const text = (r.text || "").replaceAll(BOOK_MARKER, "").trim();
    // The slot picker needs an email for the Cal.com invite; without one the
    // marker is dropped (the prompt tells the model to ask for it first).
    const booking =
      (r.text || "").includes(BOOK_MARKER) && contact.email
        ? { name: contact.name, email: contact.email, phone: contact.phone, company: contact.company }
        : undefined;

    return res.status(200).json({
      success: true,
      response: text || "Sorry, my connection dropped for a second there. Could you say that again?",
      booking,
      model_used: r.model_used,
      provider_used: r.provider_used,
      fallback_chain: r.fallback_chain,
    });
  } catch (error) {
    console.error("Gemini API Error:", error);

    // PostHog: track chat error (no PII)
    await captureServer(distinctIdFromReq(req), "chat_error", {
      endpoint: "/api/chat",
      kind: error?.name || "error",
      message: String(error?.message || error).slice(0, 200),
    });

    // Return a friendly error message so the demo never hard-fails
    return res.status(200).json({
      success: true,
      response: "Sorry, I ran into a technical issue on my end. Could you try that again?",
    });
  }
}
