// lib/rateLimit.js
// ---------------------------------------------------------------------------
// Per-IP rate limit for the public lead endpoints.
//
// Strategy:
//   - Primary: Upstash Redis (REST API), free tier 10k req/day. Setup:
//       1. Create an Upstash account at https://upstash.com
//       2. Create a Redis database (any region; the REST URL is global)
//       3. Copy the REST URL and REST Token
//       4. Add to Vercel env (Settings → Environment Variables):
//          UPSTASH_REDIS_REST_URL
//          UPSTASH_REDIS_REST_TOKEN
//       5. Done. The handler will start rate-limiting automatically.
//   - Fallback: in-process LRU (only effective on a single warm function
//     instance; on Vercel serverless each cold start resets the counter).
//     Use it as a stopgap if Upstash is not yet configured.
//
// Defaults: 10 requests per IP per 60s for lead endpoints. The Resend
// free tier is ~3k emails/month, so 10/min/IP is conservative.
//
// Why no @upstash/ratelimit SDK? Smaller dep, full control over the
// failure mode, and no extra @upstash/redis peer dep. The REST API is
// two fetch() calls and ~80 lines of code.
// ---------------------------------------------------------------------------

const DEFAULT_LIMIT = 10;
const DEFAULT_WINDOW_SECONDS = 60;

let warnedOnce = false;

function getClientIp(req) {
  // Vercel + Cloudflare + a generic fallback
  const xff = req.headers["x-forwarded-for"];
  if (typeof xff === "string" && xff.length > 0) {
    return xff.split(",")[0].trim();
  }
  if (req.socket && req.socket.remoteAddress) {
    return req.socket.remoteAddress;
  }
  return "unknown";
}

// ---- Upstash REST implementation -----------------------------------------

/**
 * Increment a counter in Upstash Redis. Returns the new value.
 * Uses the INCR + EXPIRE pattern so the window auto-resets.
 */
async function upstashIncr(restUrl, restToken, key, windowSeconds) {
  // Pipeline INCR + EXPIRE in a single round-trip.
  // The Upstash REST API accepts a pipeline as a JSON array of commands.
  const pipeline = [
    ["INCR", key],
    ["EXPIRE", key, String(windowSeconds)],
  ];
  const res = await fetch(`${restUrl}/pipeline`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${restToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(pipeline),
  });
  if (!res.ok) {
    throw new Error(`Upstash ${res.status} ${res.statusText}`);
  }
  const data = await res.json();
  // Pipeline response is an array of results; the first one is INCR's.
  const count = data && data[0] && typeof data[0].result === "number"
    ? data[0].result
    : NaN;
  return Number.isFinite(count) ? count : 0;
}

// ---- In-process LRU fallback --------------------------------------------

/**
 * Tiny in-process token bucket. NOT distributed — on Vercel serverless
 * each cold start resets state. Only useful as a stopgap.
 */
const inProcessStore = new Map();

function inProcessIncr(key, windowSeconds) {
  const now = Date.now();
  const entry = inProcessStore.get(key);
  if (!entry || entry.expiresAt < now) {
    inProcessStore.set(key, { count: 1, expiresAt: now + windowSeconds * 1000 });
    return 1;
  }
  entry.count += 1;
  return entry.count;
}

// Trim the in-process store occasionally to avoid unbounded growth.
let lastTrim = Date.now();
function trimInProcessStore() {
  const now = Date.now();
  if (now - lastTrim < 60_000) return; // once a minute at most
  lastTrim = now;
  for (const [k, v] of inProcessStore) {
    if (v.expiresAt < now) inProcessStore.delete(k);
  }
}

// ---- Public API ---------------------------------------------------------

/**
 * Apply a rate limit. Returns { ok: true } if the request is allowed,
 * or { ok: false, retryAfterSeconds } if the limit is exceeded.
 *
 * Usage in a handler:
 *   const rl = await checkRateLimit(req, { bucket: "leads" });
 *   if (!rl.ok) {
 *     res.setHeader("Retry-After", String(rl.retryAfterSeconds));
 *     return res.status(429).json({ error: "Too many requests", code: "RATE_LIMITED" });
 *   }
 */
export async function checkRateLimit(req, opts = {}) {
  const bucket = opts.bucket || "default";
  const limit = opts.limit || DEFAULT_LIMIT;
  const windowSeconds = opts.windowSeconds || DEFAULT_WINDOW_SECONDS;
  const ip = getClientIp(req);
  const key = `rl:${bucket}:${ip}`;

  const restUrl = process.env.UPSTASH_REDIS_REST_URL;
  const restToken = process.env.UPSTASH_REDIS_REST_TOKEN;

  // Primary: Upstash
  if (restUrl && restToken) {
    try {
      const count = await upstashIncr(restUrl, restToken, key, windowSeconds);
      if (count > limit) {
        return { ok: false, retryAfterSeconds: windowSeconds, count, limit };
      }
      return { ok: true, count, limit };
    } catch (err) {
      if (!warnedOnce) {
        // eslint-disable-next-line no-console
        console.warn(
          `[rateLimit] Upstash failed, falling back to in-process. ` +
            `Set UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN. Error: ${err.message}`,
        );
        warnedOnce = true;
      }
      // fall through to in-process
    }
  } else if (!warnedOnce) {
    // eslint-disable-next-line no-console
    console.warn(
      `[rateLimit] UPSTASH_REDIS_REST_URL/TOKEN not set — using in-process LRU. ` +
        `On Vercel serverless this resets per cold start. Set the env vars for ` +
        `distributed rate limiting.`,
    );
    warnedOnce = true;
  }

  // Fallback: in-process
  trimInProcessStore();
  const count = inProcessIncr(key, windowSeconds);
  if (count > limit) {
    return { ok: false, retryAfterSeconds: windowSeconds, count, limit };
  }
  return { ok: true, count, limit };
}
