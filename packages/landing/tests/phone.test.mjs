// Run: node --test packages/landing/tests/phone.test.mjs
// Regression: the lead form used to force Malaysian format (0 -> 60) and
// reject valid international numbers.
import { test } from "node:test";
import assert from "node:assert/strict";
import { normalizePhone } from "../utils/phone.js";

test("international numbers normalise to E.164 digits", () => {
  assert.equal(normalizePhone("+1 415 555 0100"), "14155550100");
  assert.equal(normalizePhone("+44 20 7946 0958"), "442079460958");
  assert.equal(normalizePhone("0049 30 123456"), "4930123456");
  assert.equal(normalizePhone("(415) 555-0100"), "4155550100");
});

test("rejects national trunk format, too short, too long", () => {
  assert.equal(normalizePhone("012 345 6789"), ""); // no longer rewritten to +60
  assert.equal(normalizePhone("+1 555"), "");
  assert.equal(normalizePhone("+1234567890123456"), "");
  assert.equal(normalizePhone(""), "");
  assert.equal(normalizePhone(undefined), "");
});
