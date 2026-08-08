import Stripe from "stripe";
import { captureServer, distinctIdFromReq } from "../lib/posthog-server.js";

const TOTAL_EARLY_ADOPTER_SPOTS = 10;

export default async function handler(req, res) {
  // SECURITY (2026-07-20): CORS tightened to known-origin allowlist.
  // See audit-report.md finding #6.
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
  res.setHeader("Cache-Control", "s-maxage=60, stale-while-revalidate=120");

  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "GET")
    return res.status(405).json({ error: "Method not allowed" });

  try {
    if (!process.env.STRIPE_SECRET_KEY) {
      // Graceful fallback — no Stripe key configured yet
      const out = {
        total: 3,
        remaining: TOTAL_EARLY_ADOPTER_SPOTS - 3,
        spotsTotal: TOTAL_EARLY_ADOPTER_SPOTS,
        fallback: true,
      };
      await captureServer(distinctIdFromReq(req), "spot_count_fetched", {
        fallback: true,
        reason: "no_stripe_key",
      });
      return res.status(200).json(out);
    }

    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: "2024-06-20",
    });

    // Fetch active subscriptions (handles pagination up to 100)
    const customers = await stripe.customers.list({
      limit: 100,
      expand: ["data.subscriptions"],
    });

    const activeCustomers = customers.data.filter((customer) =>
      customer.subscriptions?.data?.some(
        (sub) => sub.status === "active" || sub.status === "trialing",
      ),
    );

    const total = activeCustomers.length;
    const remaining = Math.max(0, TOTAL_EARLY_ADOPTER_SPOTS - total);

    await captureServer(distinctIdFromReq(req), "spot_count_fetched", {
      fallback: false,
      total,
      remaining,
    });

    return res.status(200).json({
      total,
      remaining,
      spotsTotal: TOTAL_EARLY_ADOPTER_SPOTS,
      fallback: false,
    });
  } catch (error) {
    console.error("Spots API error:", error);
    await captureServer(distinctIdFromReq(req), "api_error", {
      endpoint: "/api/spots",
      kind: error?.name || "error",
      message: String(error?.message || error).slice(0, 200),
    });
    // Graceful fallback on any error — never break the page
    return res.status(200).json({
      total: 3,
      remaining: 7,
      spotsTotal: TOTAL_EARLY_ADOPTER_SPOTS,
      fallback: true,
    });
  }
}
