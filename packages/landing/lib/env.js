// lib/env.js
// ---------------------------------------------------------------------------
// Centralised environment-variable validation for Vercel serverless handlers.
//
// Why a single module?
//   - Each api/*.js file used to read its own process.env.* directly. That
//     meant a typo in a var name silently returned undefined, and the
//     handler failed with a confusing 500 instead of a 503 "misconfigured".
//   - Per audit-report.md finding #9, env vars named with the VITE_ prefix
//     are a footgun: Vite auto-exposes them to the client bundle. The vars
//     this repo uses server-side SHOULD NOT have the VITE_ prefix; we
//     surface that warning here so it can't slip through again.
//
// Usage:
//   import { requireEnv, optionalEnv, logTypoWarning } from "../lib/env.js";
//   const supabaseUrl = requireEnv("SUPABASE_URL");
//   const geminiKey   = optionalEnv("GEMINI_API_KEY");
//   logTypoWarning("CUSTOME_API_KEY", "CUSTOM_API_KEY");
// ---------------------------------------------------------------------------

const REQUIRED = new Set([
  "SUPABASE_URL",
  "SUPABASE_SERVICE_KEY",
  "INTERNAL_API_TOKEN",
  "RESEND_API_KEY",
]);

// Vars we *must* see, but whose absence is not fatal on the first call —
// the handler returns a 503 with a clear "misconfigured" code so a deploy
// that forgot one fails loudly instead of pretending to work.
const REQUIRED_EMAIL = new Set([
  "RESEND_API_KEY",
  "EMAIL_FROM",
  "EMAIL_NOTIFY",
]);

// Vars that should NEVER be VITE_-prefixed (audit-report.md finding #9).
// If they are, that's a security footgun — Vite ships them to the client
// bundle. We don't fail on this, we warn, so a misconfigured deploy
// doesn't break prod.
const SERVER_ONLY = new Set([
  "SUPABASE_SERVICE_KEY",
  "SUPABASE_SERVICE_ROLE_KEY",
  "RESEND_API_KEY",
  "GEMINI_API_KEY",
  "STRIPE_SECRET_KEY",
  "INTERNAL_API_TOKEN",
]);

/** Read a required env var. Throws a clear error if missing. */
export function requireEnv(name) {
  const value = process.env[name];
  if (!value || value.trim() === "") {
    throw new Error(
      `[env] required env var "${name}" is missing or empty. ` +
        `Add it to your Vercel project environment (Settings → Environment Variables).`,
    );
  }
  return value;
}

/** Read an optional env var. Returns undefined if missing. */
export function optionalEnv(name) {
  const value = process.env[name];
  if (!value || value.trim() === "") return undefined;
  return value;
}

/**
 * Read a required env var for a handler. If missing, returns a JSON 503
 * response (caller is expected to `return` it from the handler) so a
 * half-configured deploy surfaces the gap to the user instead of
 * failing with a generic 500.
 */
export function requireEnvOrFail(name, res) {
  const value = process.env[name];
  if (!value || value.trim() === "") {
    res.status(503).json({
      error: `${name} not configured`,
      code: "MISCONFIGURED",
    });
    return null;
  }
  return value;
}

/** Read all email-required env vars. If any missing, returns a 503 response. */
export function requireEmailEnv(res) {
  const missing = [...REQUIRED_EMAIL].filter(
    (n) => !process.env[n] || process.env[n].trim() === "",
  );
  if (missing.length > 0) {
    res.status(503).json({
      error: `Missing required env vars: ${missing.join(", ")}`,
      code: "MISCONFIGURED",
    });
    return null;
  }
  return {
    resendApiKey: process.env.RESEND_API_KEY,
    emailFrom: process.env.EMAIL_FROM,
    emailNotify: process.env.EMAIL_NOTIFY,
  };
}

/**
 * Log a one-time warning if a server-only secret is exposed with the
 * VITE_ prefix. Call once at module load time.
 */
export function logTypoWarning() {
  if (process.env.NODE_ENV === "production") return; // noisy in dev, silent in prod
  const warnings = [];
  for (const name of SERVER_ONLY) {
    const v = process.env[name];
    if (!v) continue; // not set at all — fine
    if (v.startsWith("VITE_") || name.startsWith("VITE_")) {
      warnings.push(`"${name}" has the VITE_ prefix — Vite will ship it to the client bundle.`);
    }
  }
  if (warnings.length > 0) {
    // eslint-disable-next-line no-console
    console.warn(`[env] SECURITY WARNINGS:\n  - ${warnings.join("\n  - ")}`);
  }
}

/**
 * Validate that the process has all REQUIRED vars. Throws if not.
 * Call once at module load (top of api/*.js).
 */
export function assertRequiredEnv() {
  const missing = [...REQUIRED].filter(
    (n) => !process.env[n] || process.env[n].trim() === "",
  );
  if (missing.length > 0) {
    throw new Error(
      `[env] required env vars missing: ${missing.join(", ")}`,
    );
  }
}

/**
 * Return a JSON 503 response for handlers that can't function without
 * a given env var. Use this in the catch block of a handler when the
 * env is misconfigured.
 */
export function envMissingResponse(res, varName) {
  return res.status(503).json({
    error: `${varName} not configured`,
    code: "MISCONFIGURED",
  });
}
