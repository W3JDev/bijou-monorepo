// Run: node --test lib/leads.test.js
import { test } from "node:test";
import assert from "node:assert/strict";
import { extractContact, mergeNotes, normaliseSource } from "./leads.js";

test("extracts contact from user turns only, ignoring Bijou's own contact info", () => {
  const c = extractContact([
    { role: "model", content: "Hi! What's your name? WhatsApp us at +60 17-410 6981 or jewel@mybijou.xyz" },
    { role: "user", content: "Test Lead Claude" },
    { role: "model", content: "So what kind of business do you run?" },
    { role: "user", content: "I run a clinic called Test Dental and we are busy" },
    { role: "user", content: "Can we meet 2026-10-01? my email is claude-test-1@example.com, WhatsApp +60 12-345 6789" },
  ]);
  assert.equal(c.name, "Test Lead Claude");
  assert.equal(c.company, "Test Dental");
  assert.equal(c.email, "claude-test-1@example.com");
  assert.equal(c.phone, "60123456789");
});

test("digits inside an email address are not a phone number", () => {
  assert.equal(extractContact([{ role: "user", content: "my email is claude-test-1790507084679@example.com" }]).phone, "");
});

test("explicit name patterns; lowercase 'I'm a ...' is not a name", () => {
  assert.equal(extractContact([{ role: "user", content: "Hi, my name is Alex Tan" }]).name, "Alex Tan");
  assert.equal(extractContact([{ role: "user", content: "I'm a property agent" }]).name, "");
});

test("mergeNotes keeps owner notes and replaces only the transcript", () => {
  const a = mergeNotes("owner note", { transcript: "t1" });
  const b = mergeNotes(a, { append: "Booked X", transcript: "t2" });
  assert.equal(b, "owner note\nBooked X\n--- chat transcript ---\nt2");
  assert.equal(mergeNotes(b, { append: "Booked Y" }), "owner note\nBooked X\nBooked Y\n--- chat transcript ---\nt2");
});

test("unknown channels map to a DB-valid source", () => {
  assert.equal(normaliseSource("demo_chat"), "website");
  assert.equal(normaliseSource("voice"), "website");
});
