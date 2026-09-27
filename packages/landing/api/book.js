// BIJOU AI - Meeting booking (Cal.com API v2)
//
//   GET  /api/book?date=YYYY-MM-DD&tz=Asia/Kuala_Lumpur
//        → 200 {ok, date, timeZone, slots:[ISO start, ...]}      (30-min slots)
//   POST /api/book {name, email, start, timeZone, phone?, company?, notes?, source?}
//        → 200 {ok, booking:{uid,start,end,meetingUrl}, lead_saved}
//
// Used by the demo chat's inline slot picker AND as a JSON webhook tool for
// the voice agent (source:"voice"). JSON in/out, no cookies. Unlike
// api/chat.js this returns honest status codes: 400 invalid input, 405,
// 4xx passed through when Cal.com rejects (400 bad email, 409 slot taken), 429 rate limited, 502 Cal.com down,
// 503 CAL_API_KEY missing.

import { checkRateLimit } from "../lib/rateLimit.js";
import { EMAIL_RE, notifyOwner, upsertLead } from "../lib/leads.js";
import { normalizePhone } from "../utils/phone.js";
import { captureServer, distinctIdFromReq } from "../lib/posthog-server.js";

const CAL = "https://api.cal.com/v2";
const EVENT_TYPE_ID = 4742864; // cal.com/getbijou/30min
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function validTimeZone(tz) {
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: tz });
    return true;
  } catch {
    return false;
  }
}

async function cal(path, { method = "GET", version, body } = {}) {
  const r = await fetch(`${CAL}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${process.env.CAL_API_KEY}`,
      "cal-api-version": version,
      ...(body && { "Content-Type": "application/json" }),
    },
    body: body && JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  const data = await r.json().catch(() => ({}));
  return { status: r.status, ok: r.ok, data };
}

const fail = (res, status, code, error) => res.status(status).json({ ok: false, code, error });

export default async function handler(req, res) {
  const origin = req.headers.origin || "";
  if (
    ["https://mybijou.xyz", "https://app.mybijou.xyz", "https://staging.mybijou.xyz"].includes(origin) ||
    origin.startsWith("http://localhost:")
  ) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Vary", "Origin");
  }
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "GET" && req.method !== "POST") {
    res.setHeader("Allow", ["GET", "POST", "OPTIONS"]);
    return fail(res, 405, "METHOD_NOT_ALLOWED", "Method not allowed");
  }

  const rl = await checkRateLimit(req, {
    bucket: req.method === "GET" ? "book_slots" : "book",
    limit: req.method === "GET" ? 30 : 5,
  });
  if (!rl.ok) {
    res.setHeader("Retry-After", String(rl.retryAfterSeconds));
    return fail(res, 429, "RATE_LIMITED", "Too many requests");
  }

  if (!process.env.CAL_API_KEY) {
    console.warn("⚠️  CAL_API_KEY not set — /api/book unavailable");
    return fail(res, 503, "NOT_CONFIGURED", "Booking is not configured");
  }

  try {
    return req.method === "GET" ? await getSlots(req, res) : await createBooking(req, res);
  } catch (err) {
    console.error("Book endpoint error:", err);
    await captureServer(distinctIdFromReq(req), "api_error", {
      endpoint: "/api/book",
      kind: err?.name || "error",
      message: String(err?.message || err).slice(0, 200),
    });
    return fail(res, 502, "UPSTREAM_ERROR", "Calendar is unavailable, please try again");
  }
}

async function getSlots(req, res) {
  const date = String(req.query?.date || "");
  const timeZone = String(req.query?.tz || "Asia/Kuala_Lumpur");
  if (!DATE_RE.test(date) || Number.isNaN(Date.parse(date))) {
    return fail(res, 400, "INVALID_DATE", "date must be YYYY-MM-DD");
  }
  if (!validTimeZone(timeZone)) return fail(res, 400, "INVALID_TIMEZONE", "tz must be an IANA time zone");

  const q = new URLSearchParams({ eventTypeId: String(EVENT_TYPE_ID), start: date, end: date, timeZone });
  const r = await cal(`/slots?${q}`, { version: "2024-09-04" });
  if (!r.ok) {
    console.error("Cal.com slots failed:", r.status, JSON.stringify(r.data).slice(0, 300));
    return fail(res, r.status >= 500 ? 502 : 400, "SLOTS_FAILED", r.data?.error?.message || "Could not load slots");
  }
  const slots = (r.data?.data?.[date] || []).map((s) => s.start);
  return res.status(200).json({ ok: true, date, timeZone, slots });
}

async function createBooking(req, res) {
  const b = req.body && typeof req.body === "object" ? req.body : {};
  const name = String(b.name || "").trim();
  const email = String(b.email || "").trim().toLowerCase();
  const timeZone = String(b.timeZone || "Asia/Kuala_Lumpur");
  const startMs = Date.parse(String(b.start || ""));
  const notes = String(b.notes || "").slice(0, 1000);
  const source = String(b.source || "demo_chat").slice(0, 40);
  const company = String(b.company || "").trim().slice(0, 120);

  if (!name || name.length > 100) return fail(res, 400, "INVALID_NAME", "name is required (max 100 chars)");
  if (!EMAIL_RE.test(email)) return fail(res, 400, "INVALID_EMAIL", "A valid email is required");
  if (!validTimeZone(timeZone)) return fail(res, 400, "INVALID_TIMEZONE", "timeZone must be an IANA time zone");
  if (Number.isNaN(startMs) || startMs < Date.now()) {
    return fail(res, 400, "INVALID_START", "start must be a future ISO 8601 datetime");
  }
  const phone = normalizePhone(b.phone);
  if (String(b.phone ?? "").trim() && !phone) {
    return fail(res, 400, "INVALID_PHONE", "phone must include the country code");
  }

  const start = new Date(startMs).toISOString();
  const r = await cal("/bookings", {
    method: "POST",
    version: "2024-08-13",
    body: {
      start,
      eventTypeId: EVENT_TYPE_ID,
      attendee: { name, email, timeZone, ...(phone && { phoneNumber: `+${phone}` }) },
      bookingFieldsResponses: {
        title: `Bijou AI call with ${company || name}`,
        ...(notes && { notes }),
      },
      metadata: { source },
    },
  });
  if (!r.ok) {
    const msg = r.data?.error?.message || r.data?.message || "Booking failed";
    console.error("Cal.com booking failed:", r.status, JSON.stringify(r.data).slice(0, 300));
    // 401/403 = our CAL_API_KEY is bad, not the caller's fault.
    if (r.status >= 500 || r.status === 401 || r.status === 403) {
      return fail(res, 502, "UPSTREAM_ERROR", "Calendar is unavailable, please try again");
    }
    // Other 4xx pass through (e.g. 400 undeliverable email, slot taken).
    return fail(res, r.status, "BOOKING_REJECTED", String(msg).slice(0, 200));
  }

  const d = r.data?.data || {};
  const booking = { uid: d.uid, start: d.start, end: d.end, meetingUrl: d.meetingUrl || d.location || null };

  // The booking stands even if the lead write fails; Cal.com already emailed
  // the owner, so WhatsApp/email notify only fires for a brand-new lead.
  const lead = { name, email, phone, company, source };
  const saved = await upsertLead({
    ...lead,
    status: "qualified",
    appendNote: `Booked 30-min call ${booking.start} (${timeZone}) via ${source}, Cal.com uid ${booking.uid}${notes ? ` — ${notes}` : ""}`,
  });
  if (saved.error) console.warn("[book] lead not saved:", saved.error);
  if (saved.isNew) {
    await notifyOwner({ title: "📅 NEW BOOKING!", lead, extra: `Call: ${booking.start} (${timeZone})` });
  }

  return res.status(200).json({ ok: true, booking, lead_saved: !saved.error });
}
