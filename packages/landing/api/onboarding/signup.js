// BIJOU AI - Onboarding Signup Proxy
//
// SECURITY (2026-07-20): This endpoint was previously an unauthenticated open
// proxy — anyone could sign arbitrary businesses up for the production
// onboarding system. It is now restricted to known origins AND requires the
// `X-Internal-Token` header (matching the production app's shared secret).
//
// Public form submissions go through `api/leads.js` which carries the token
// itself. See audit-report.md finding #2.

const ALLOWED_ORIGINS = new Set([
  "https://mybijou.xyz",
  "https://app.mybijou.xyz",
  "https://staging.mybijou.xyz",
  "http://localhost:3000",
]);

function isAllowedOrigin(origin) {
  if (!origin) return true; // server-to-server or curl
  if (ALLOWED_ORIGINS.has(origin)) return true;
  try {
    const u = new URL(origin);
    return u.hostname === "localhost" || u.hostname === "127.0.0.1";
  } catch {
    return false;
  }
}

// Loose Malaysian phone format: 60-prefixed, 9-12 digits, optional +.
const PHONE_RE = /^\+?6?0?1[0-46-9]\d{7,11}$/;
const EMAIL_RE =
  /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;

export default async function handler(req, res) {
  const origin = req.headers.origin || "";
  if (isAllowedOrigin(origin)) {
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

  // Internal-only auth.
  const expected = process.env.INTERNAL_API_TOKEN;
  if (!expected) {
    return res
      .status(503)
      .json({ error: "Onboarding unavailable", code: "MISCONFIGURED" });
  }
  if (req.headers["x-internal-token"] !== expected) {
    return res
      .status(401)
      .json({ error: "Unauthorized", code: "BAD_TOKEN" });
  }

  try {
    const { business_name, email, phone } = req.body || {};
    if (!business_name || !email) {
      return res.status(400).json({
        error: "Business name and email are required",
        code: "MISSING_REQUIRED_FIELDS",
      });
    }
    if (typeof business_name !== "string" || business_name.trim().length < 2) {
      return res.status(400).json({
        error: "Invalid business name",
        code: "INVALID_BUSINESS_NAME",
      });
    }
    if (!EMAIL_RE.test(String(email).trim())) {
      return res
        .status(400)
        .json({ error: "Invalid email", code: "INVALID_EMAIL" });
    }
    if (phone && !PHONE_RE.test(String(phone).trim())) {
      return res
        .status(400)
        .json({ error: "Invalid phone format", code: "INVALID_PHONE" });
    }

    const response = await fetch(
      "https://bijou-production.fly.dev/api/onboarding/signup",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Internal-Token": expected,
        },
        body: JSON.stringify({
          business_name: business_name.trim().slice(0, 200),
          email: email.toLowerCase().trim().slice(0, 200),
          phone: phone ? phone.trim().slice(0, 30) : "",
        }),
      },
    );

    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      return res.status(response.status).json(result);
    }
    return res.status(200).json(result);
  } catch (error) {
    console.error("Onboarding signup proxy error:", error);
    return res
      .status(500)
      .json({ error: "Server error", code: "INTERNAL_ERROR" });
  }
}
