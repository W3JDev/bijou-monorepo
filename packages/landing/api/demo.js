// BIJOU AI - Combined Demo-Booking Endpoint
//
// SECURITY (2026-07-20): Created to replace the public /api/send open-proxy
// call in OnboardingModal's demo flow. This endpoint:
//   1. Validates demo_time + email
//   2. Sends the WhatsApp owner-notify server-to-server (with INTERNAL_API_TOKEN)
//   3. Returns ok to the client without exposing any proxy surface
//
// See audit-report.md finding #1 (open proxy) and #21 (two-call demo flow).

import { captureServer, identifyServer, distinctIdFromReq } from "../lib/posthog-server.js";

const EMAIL_RE =
  /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;

export default async function handler(req, res) {
  // CORS — same-origin only; this is a same-origin endpoint.
  res.setHeader("Access-Control-Allow-Origin", "https://mybijou.xyz");
  res.setHeader("Vary", "Origin");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Max-Age", "86400");

  if (req.method === "OPTIONS") return res.status(200).json({ ok: true });
  if (req.method !== "POST") {
    res.setHeader("Allow", ["POST", "OPTIONS"]);
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const { lead_id, email, demo_time, business_name, phone, industry, source } =
      req.body || {};

    if (!email || !EMAIL_RE.test(String(email).trim())) {
      return res
        .status(400)
        .json({ error: "Valid email required", code: "INVALID_EMAIL" });
    }
    if (!demo_time || String(demo_time).trim().length < 2) {
      return res
        .status(400)
        .json({ error: "Demo time required", code: "MISSING_DEMO_TIME" });
    }

    // Server-to-server WhatsApp notify. Never expose this path to the client.
    const token = process.env.INTERNAL_API_TOKEN;
    if (!token) {
      console.warn(
        "⚠️  INTERNAL_API_TOKEN not set — skipping WhatsApp demo-notify",
      );
      // Don't fail the user's flow if notify is unavailable; the lead was
      // already saved by /api/leads in the prior step.
      return res.status(200).json({ ok: true, notified: false });
    }

    const message =
      `🎯 NEW DEMO REQUEST!\n\n` +
      `Business: ${business_name || "N/A"}\n` +
      `Email: ${email}\n` +
      `Phone: ${phone || "N/A"}\n` +
      `Industry: ${industry || "N/A"}\n` +
      `Preferred Time: ${demo_time}\n` +
      `Lead ID: ${lead_id || "n/a"}\n` +
      `Source: ${source || "unknown"}`;

    const r = await fetch("https://bijou-production.fly.dev/api/send", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Token": token,
      },
      body: JSON.stringify({ to: "60174106981@s.whatsapp.net", message }),
    });

    if (!r.ok) {
      const text = await r.text().catch(() => "");
      console.error("Upstream demo-notify failed:", r.status, text);
      await captureServer(distinctIdFromReq(req), "api_error", {
        endpoint: "/api/demo",
        kind: "upstream_failure",
        upstream_status: r.status,
      });
      // Still return ok to the user — the lead is saved either way.
      return res.status(200).json({ ok: true, notified: false });
    }

    // PostHog: identify + capture demo_booked (server-side, after the lead
    // is already saved by /api/leads so the funnel is correct).
    try {
      const distinctId = `email:${String(email).toLowerCase().trim()}`;
      await identifyServer(distinctId, {
        email: String(email).toLowerCase().trim(),
        name: business_name || undefined,
        industry: industry || undefined,
        source: source || undefined,
        demo_requested_at: new Date().toISOString(),
      });
      await captureServer(distinctId, "demo_booked", {
        source: source || undefined,
        industry: industry || undefined,
        lead_id: lead_id || undefined,
        demo_time: demo_time || undefined,
        has_phone: Boolean(phone),
      });
    } catch (e) {
      console.warn("[posthog:server] demo emit failed:", e?.message || e);
    }

    return res.status(200).json({ ok: true, notified: true });
  } catch (err) {
    console.error("Demo endpoint error:", err);
    await captureServer(distinctIdFromReq(req), "api_error", {
      endpoint: "/api/demo",
      kind: err?.name || "error",
      message: String(err?.message || err).slice(0, 200),
    });
    // Same reasoning: never block user UX on notify failure.
    return res.status(200).json({ ok: true, notified: false });
  }
}
