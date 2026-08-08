// Vercel serverless function — voice waitlist email capture
// Uses Resend (already in package.json) to notify founder of new signups.
// POST /api/voice-waitlist  { email: string, source?: string }

import { Resend } from "resend";
import { checkRateLimit } from "../lib/rateLimit.js";
import { logTypoWarning, requireEmailEnv } from "../lib/env.js";
import { captureServer, identifyServer, distinctIdFromReq } from "../lib/posthog-server.js";

logTypoWarning();

// Resend is constructed lazily inside the handler so a misconfigured
// deploy (missing RESEND_API_KEY) does not crash the function on import.
// Matches the lazy-init pattern used in api/leads.js and api/slide-deck.js.

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  // Rate limit BEFORE email send. Without this, a 10-line browser
  // script can exhaust the Resend free tier in minutes (audit #5).
  const rl = await checkRateLimit(req, { bucket: "voice-waitlist" });
  if (!rl.ok) {
    res.setHeader("Retry-After", String(rl.retryAfterSeconds));
    return res
      .status(429)
      .json({ error: "Too many requests", code: "RATE_LIMITED" });
  }

  // Env-var check AFTER the cheap pre-checks (method + rate limit) so
  // a GET /api/voice-waitlist returns 405, not 503. The previous eager
  // `new Resend(undefined)` at module top crashed the whole function
  // with FUNCTION_INVOCATION_FAILED when RESEND_API_KEY was unset.
  const env = requireEmailEnv(res);
  if (!env) return; // requireEmailEnv already wrote the 503
  const { resendApiKey, emailNotify } = env;

  const { email, source = "voice-teaser" } = req.body ?? {};

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email || typeof email !== "string" || !emailRegex.test(email)) {
    return res.status(400).json({ error: "Valid email required" });
  }

  const cleanEmail = email.trim().toLowerCase();

  try {
    // Notify founder
    const resend = new Resend(resendApiKey);
    await resend.emails.send({
      from: "Bijou Voice Waitlist <noreply@mybijou.xyz>",
      to: emailNotify,
      subject: `Voice waitlist signup: ${cleanEmail}`,
      html: `
        <h2>New Voice Waitlist Signup</h2>
        <p><strong>Email:</strong> ${cleanEmail}</p>
        <p><strong>Source:</strong> ${source}</p>
        <p><strong>Time:</strong> ${new Date().toISOString()}</p>
        <hr />
        <p style="color:#888;font-size:12px">Bijou Voice — Coming Q4 2026</p>
      `,
    });

    // Confirm to user
    await resend.emails.send({
      from: "Bijou <noreply@mybijou.xyz>",
      to: cleanEmail,
      subject: "You're on the Bijou Voice waitlist",
      html: `
        <h2>You're on the list!</h2>
        <p>Hey boss,</p>
        <p>We got your request for <strong>Bijou Voice</strong> — AI phone calls in Manglish, for Malaysian SMEs.</p>
        <p>We're targeting <strong>Q4 2026</strong>. You'll be first to know when it ships.</p>
        <p>In the meantime, Bijou for WhatsApp + Telegram is live now at <strong>RM299/month</strong> at <a href="https://mybijou.xyz">mybijou.xyz</a>.</p>
        <p>— MN Jewel, Bijou</p>
        <hr />
        <p style="color:#888;font-size:12px">Built in KL. Made for Malaysian SMEs. Unsubscribe: reply with "remove".</p>
      `,
    });

    // PostHog: server-side capture (after email send attempt)
    await emitVoiceWaitlistEvent({ req, cleanEmail, source });

    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error("voice-waitlist error:", err);
    // PostHog: server-side error tracking (no PII)
    await captureServer(distinctIdFromReq(req), "api_error", {
      endpoint: "/api/voice-waitlist",
      kind: err?.name || "error",
      message: String(err?.message || err).slice(0, 200),
    });
    // Return 200 anyway — don't block the user UX on email send failure
    return res.status(200).json({ ok: true, warn: "email_send_failed" });
  }
}

// PostHog hooks fire AFTER the success response — won't block user.
async function emitVoiceWaitlistEvent({ req, cleanEmail, source }) {
  try {
    const distinctId = `email:${cleanEmail}`;
    await identifyServer(distinctId, {
      email: cleanEmail,
      source,
      voice_waitlist: true,
      created_at: new Date().toISOString(),
    });
    await captureServer(distinctId, "voice_waitlist_joined", {
      source,
      ip_distinct_id: distinctIdFromReq(req),
    });
  } catch (e) {
    console.warn("[posthog:server] voice-waitlist emit failed:", e?.message || e);
  }
}
