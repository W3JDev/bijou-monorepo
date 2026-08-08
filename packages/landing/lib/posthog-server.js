// lib/posthog-server.js
// Server-side PostHog client for Vercel serverless functions (api/*.js).
// Uses posthog-node. Lazy-init so cold-starts stay fast.
//
// Required env vars (server-side only — never use VITE_ prefix):
//   POSTHOG_PROJECT_KEY   - phc_… token, matches VITE_POSTHOG_PROJECT_KEY
//   POSTHOG_HOST          - https://us.i.posthog.com (or eu / self-hosted)
//
// Optional:
//   POSTHOG_ENABLED       - "0" to force-disable (kill switch)

import { PostHog } from "posthog-node";

let client = null;
let enabled = true;

function init() {
  if (client !== null) return client;

  const projectKey = process.env.POSTHOG_PROJECT_KEY;
  const host = process.env.POSTHOG_HOST || "https://us.i.posthog.com";
  if (process.env.POSTHOG_ENABLED === "0") enabled = false;

  if (!enabled || !projectKey) {
    if (process.env.NODE_ENV !== "production" && process.env.POSTHOG_DEBUG === "1") {
      console.log("[posthog:server] disabled — set POSTHOG_PROJECT_KEY to enable");
    }
    client = null;
    return null;
  }

  client = new PostHog(projectKey, {
    host,
    // Serverless: flush on each call, don't keep a long-lived queue.
    flushInterval: 0,
    // We do not want to block the response on network I/O — but we DO want
    // a short timeout so failures are visible.
    requestTimeout: 3000,
  });

  return client;
}

/**
 * Capture a server-side event. DistinctId can be a sessionId, a user id, or
 * a synthetic "$server" id for anonymous events.
 *
 * IMPORTANT (2026-07-30): on Vercel serverless we MUST await the flush
 * before returning, otherwise the function freezes the process and the
 * queued event never reaches PostHog. Initial symptom: bridge returns 200
 * with `ok:true` but events never show up in PostHog Activity.
 */
export async function captureServer(
  distinctId,
  event,
  properties = {},
) {
  const c = init();
  if (!c) return;
  try {
    c.capture({
      distinctId: distinctId || "anonymous",
      event,
      properties: {
        ...properties,
        app: "bijou-api",
        runtime: "vercel-serverless",
      },
    });
    // Wait for the queue to flush before the serverless function returns.
    // Bounded to 3s so a PostHog outage doesn't block the user response.
    await Promise.race([
      c.flush(),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]);
  } catch (e) {
    console.warn("[posthog:server] capture failed:", e?.message || e);
  }
}

/**
 * Identify a server-side user (e.g. when a lead's email becomes known).
 */
export async function identifyServer(
  distinctId,
  traits = {},
) {
  const c = init();
  if (!c) return;
  try {
    c.identify({ distinctId, properties: traits });
    // Same serverless caveat as captureServer — await the flush so the
    // queued identify actually ships before the function freezes.
    await Promise.race([
      c.flush(),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]);
  } catch (e) {
    console.warn("[posthog:server] identify failed:", e?.message || e);
  }
}

/**
 * Shutdown — call this only on graceful exits. Vercel serverless usually
 * kills the process before this runs; included for completeness.
 */
export async function shutdown() {
  if (!client) return;
  try {
    await client.shutdown();
  } catch (e) {
    // best effort
  } finally {
    client = null;
  }
}

/** True if PostHog is wired and the project key is set. */
export function isServerEnabled() {
  return Boolean(process.env.POSTHOG_PROJECT_KEY) && enabled;
}

/**
 * Best-effort distinctId from a Vercel request. Falls back to a
 * process-level synthetic id. Never PII — does NOT log the email.
 */
export function distinctIdFromReq(req, fallback = "anonymous") {
  try {
    const xf = req.headers?.["x-forwarded-for"];
    if (typeof xf === "string" && xf.length) {
      return `ip:${xf.split(",")[0].trim()}`;
    }
    return `ip:${req.socket?.remoteAddress || fallback}`;
  } catch {
    return fallback;
  }
}
