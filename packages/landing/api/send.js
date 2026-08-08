// BIJOU AI - Internal WhatsApp Send Relay
//
// SECURITY (2026-07-20): This endpoint was previously an unauthenticated open
// proxy — anyone could send arbitrary WhatsApp messages through the
// production bridge. It is now locked down:
//   - Requires `X-Internal-Token` header matching `INTERNAL_API_TOKEN` env var.
//   - CORS restricted to same-origin and the Bijou app domains.
//   - `to` field must be the founder's verified WhatsApp JID.
//
// Public callers (OnboardingModal demo flow, leads owner-notify) have been
// moved to server-to-server calls in `api/leads.js` and `api/demo.js`,
// which carry the token themselves. See audit-report.md finding #1.

import { captureServer, distinctIdFromReq } from "../lib/posthog-server.js";

const ALLOWED_ORIGINS = new Set([
  "https://mybijou.xyz",
  "https://app.mybijou.xyz",
  "https://staging.mybijou.xyz",
  "http://localhost:3000",
]);

// Hard-coded recipient — this endpoint is for FOUNDER notifications only.
// All other send traffic goes through the production app directly.
const FOUNDER_JID = "60174106981@s.whatsapp.net";

function isLoopbackOrigin(origin) {
  if (!origin) return true; // server-to-server, same-origin, or curl
  if (ALLOWED_ORIGINS.has(origin)) return true;
  // Allow any localhost port for dev
  try {
    const u = new URL(origin);
    return u.hostname === "localhost" || u.hostname === "127.0.0.1";
  } catch {
    return false;
  }
}

export default async function handler(req, res) {
  const origin = req.headers.origin || "";
  if (isLoopbackOrigin(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin || "*");
    res.setHeader("Vary", "Origin");
    res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
    res.setHeader(
      "Access-Control-Allow-Headers",
      "Content-Type, X-Internal-Token",
    );
    res.setHeader("Access-Control-Max-Age", "86400");
  }

  if (req.method === "OPTIONS") {
    return res.status(200).json({ ok: true });
  }
  if (req.method !== "POST") {
    res.setHeader("Allow", ["POST", "OPTIONS"]);
    return res.status(405).json({ error: "Method not allowed" });
  }

  // Internal-only auth. Anonymous calls are rejected before any I/O.
  const expected = process.env.INTERNAL_API_TOKEN;
  if (!expected) {
    console.error("INTERNAL_API_TOKEN not configured");
    return res
      .status(503)
      .json({ error: "Relay unavailable", code: "MISCONFIGURED" });
  }
  const presented = req.headers["x-internal-token"];
  if (presented !== expected) {
    return res
      .status(401)
      .json({ error: "Unauthorized", code: "BAD_TOKEN" });
  }

  try {
    const { message } = req.body || {};
    if (!message || typeof message !== "string") {
      return res
        .status(400)
        .json({ error: "message is required", code: "MISSING_MESSAGE" });
    }
    if (message.length > 4000) {
      return res
        .status(400)
        .json({ error: "message too long", code: "MESSAGE_TOO_LONG" });
    }

    // Single hard-coded recipient. Any `to` in the body is ignored.
    const response = await fetch("https://bijou-production.fly.dev/api/send", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Token": expected,
      },
      body: JSON.stringify({ to: FOUNDER_JID, message }),
    });

    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      console.error("Upstream send failed:", response.status, result);
      await captureServer(distinctIdFromReq(req), "api_error", {
        endpoint: "/api/send",
        kind: "upstream_failure",
        upstream_status: response.status,
      });
      return res.status(502).json({
        error: "Upstream send failed",
        code: "UPSTREAM_ERROR",
      });
    }
    await captureServer(distinctIdFromReq(req), "whatsapp_relay_sent", {
      endpoint: "/api/send",
      message_length: message.length,
    });
    return res.status(200).json({ ok: true, result });
  } catch (error) {
    console.error("Send relay error:", error);
    await captureServer(distinctIdFromReq(req), "api_error", {
      endpoint: "/api/send",
      kind: error?.name || "error",
      message: String(error?.message || error).slice(0, 200),
    });
    return res
      .status(500)
      .json({ error: "Server error", code: "INTERNAL_ERROR" });
  }
}
