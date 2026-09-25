// Shared by the browser (OnboardingModal) and the serverless handlers
// (api/leads.js, api/demo.js) so client and server agree on one rule.
//
// Returns the number as E.164 digits without the "+" (e.g. "14155550100"),
// the same digits-only shape the old Malaysia-only validator stored, or ""
// if it can't be a real international number.
// ponytail: length + no-leading-0 check only; swap in libphonenumber-js if
// per-country validation is ever needed.

/**
 * @param {unknown} input
 * @returns {string}
 */
export function normalizePhone(input) {
  let digits = String(input ?? "").replace(/\D/g, "");
  // "00" is the international dialling prefix in most of the world (= "+").
  if (digits.startsWith("00")) digits = digits.slice(2);
  // E.164 country codes never start with 0 — a leading 0 is a national trunk
  // prefix, so the country code is missing and we can't guess it.
  if (digits.startsWith("0")) return "";
  return digits.length >= 8 && digits.length <= 15 ? digits : "";
}
