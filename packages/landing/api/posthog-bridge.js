// api/posthog-bridge.js
// Bridge Supabase database events → PostHog. The Supabase dashboard can
// fire a "Database Webhook" to this URL on INSERT/UPDATE/DELETE; we
// forward the row to PostHog as a server-side capture event.
//
// POST /api/posthog-bridge
// Headers: x-internal-token (must match INTERNAL_API_TOKEN)
// Body (Supabase webhook format):
//   { type: "INSERT"|"UPDATE"|"DELETE", table: string, record: {...}, old_record: {...} }
//
// Configured per-table mapping:
//   leads          -> lead_db_change (with lead_id, source, status, industry)
//   onboarding_users -> user_db_change
//   voice_waitlist -> voice_waitlist_db_change
//
// Authentication: same shared INTERNAL_API_TOKEN the rest of the internal
// endpoints use, so Supabase webhooks can be set up without a second secret.

import { captureServer, identifyServer } from "../lib/posthog-server.js";

const TABLE_EVENT_MAP = {
  leads: "lead_db_change",
  onboarding_users: "user_db_change",
  voice_waitlist: "voice_waitlist_db_change",
};

function unauthorized(res) {
  return res.status(401).json({ error: "Unauthorized", code: "BAD_TOKEN" });
}

function badRequest(res, message) {
  return res.status(400).json({ error: message, code: "BAD_REQUEST" });
}

export default async function handler(req, res) {
  // CORS — internal-only, but allow same-origin + curl for ops
  const origin = req.headers.origin || "";
  const isLocal =
    !origin ||
    origin.startsWith("http://localhost:") ||
    origin === "https://mybijou.xyz" ||
    origin === "https://app.mybijou.xyz";
  if (isLocal) {
    res.setHeader("Access-Control-Allow-Origin", origin || "*");
    res.setHeader("Vary", "Origin");
  }
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type, X-Internal-Token",
  );
  res.setHeader("Access-Control-Max-Age", "86400");

  if (req.method === "OPTIONS") return res.status(200).json({ ok: true });
  if (req.method !== "POST") {
    res.setHeader("Allow", ["POST", "OPTIONS"]);
    return res.status(405).json({ error: "Method not allowed" });
  }

  // Auth — Supabase webhook must present INTERNAL_API_TOKEN.
  const expected = process.env.INTERNAL_API_TOKEN;
  if (!expected) {
    console.error("INTERNAL_API_TOKEN not configured");
    return res
      .status(503)
      .json({ error: "Bridge unavailable", code: "MISCONFIGURED" });
  }
  if (req.headers["x-internal-token"] !== expected) return unauthorized(res);

  // Body shape
  const { type, table, record, old_record } = req.body || {};
  if (!type || !table) {
    return badRequest(res, "Missing 'type' or 'table'");
  }
  if (!record && !old_record) {
    return badRequest(res, "Missing 'record' or 'old_record'");
  }

  const eventName = TABLE_EVENT_MAP[table];
  if (!eventName) {
    // Unknown table — ack 200 so Supabase doesn't retry forever.
    return res.status(200).json({ ok: true, skipped: "unknown_table" });
  }

  try {
    const row = record || old_record;
    const distinctId =
      row?.email
        ? `email:${String(row.email).toLowerCase().trim()}`
        : `row:${table}:${row?.id || "anon"}`;

    // For leads, keep PostHog person profile in sync with DB state.
    if (table === "leads" && type !== "DELETE" && row?.email) {
      await identifyServer(distinctId, {
        email: String(row.email).toLowerCase().trim(),
        name: row.name || undefined,
        company: row.company || undefined,
        industry: row.industry || undefined,
        source: row.source || undefined,
        status: row.status || undefined,
        lead_score: row.lead_score || undefined,
        updated_at: new Date().toISOString(),
      });
    }

    await captureServer(distinctId, eventName, {
      db_event: type,
      table,
      row_id: row?.id,
      source: row?.source,
      industry: row?.industry || undefined,
      status: row?.status || undefined,
    });

    return res.status(200).json({ ok: true, event: eventName, distinctId });
  } catch (err) {
    console.error("[posthog-bridge] failed:", err);
    return res.status(500).json({
      error: "Bridge failed",
      code: "INTERNAL_ERROR",
      message: err?.message?.slice(0, 200) || String(err).slice(0, 200),
    });
  }
}
