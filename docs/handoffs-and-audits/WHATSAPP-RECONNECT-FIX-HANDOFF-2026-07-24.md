# WhatsApp Reconnect Fix + Next Sprint — Handoff (2026-07-24)

**Author:** Claude (autonomous session while owner was out)
**Repo:** `w3j-bijou-enterprise` (product). Branch `feat/composio-connector-layer`.
**Integrity note:** Everything below is marked either ✅ VERIFIED (with evidence) or ⛔ NOT VERIFIED. No "done" claims without evidence.

---

## 🔴 HARD BLOCKER (do this first — only the owner can)

**Fly.io deploys are blocked by overdue invoices.** Both the Depot builder and the
legacy remote builder return:

```
Error: ...Your account has overdue invoices. Please update your payment information:
https://fly.io/dashboard/mn-bijou/billing
```

EVIDENCE: two deploy attempts to `bijou-agent-staging`, one `--depot=false`, both 403/failed on billing (2026-07-24).

Until billing is cleared, **nothing can deploy to staging or production**, and the
WhatsApp fix below cannot be tested end-to-end (needs the running app + a real phone scan).

---

## 1. WhatsApp Reconnect — ROOT CAUSE FOUND + FIXED IN CODE

### Symptoms (from screenshots + code trace)
- QR image broken (network showed the QR `.png` at ~0.1 kB = an error body, not an image).
- Page stuck on "Waiting for scan…", polls forever, never redirects after scan.
- Dashboard bounces back to the "Step 1: Business Information" setup form.
These are **one cascade**, not three bugs.

### Root cause (3-part stack in the onboarding QR path)
1. **Env-var name mismatch.** `src/saas/onboarding_api.py:get_whatsapp_bridge_url()` read
   ONLY `WHATSAPP_BRIDGE_URL`. The rest of the app + the deployment use `BRIDGE_URL`.
   → function raised → QR endpoint returned a ~60-byte 500 JSON that the `<img>` renders
   as a broken image.
2. **Missing bridge auth.** The `/qr` and `/api/init` calls used `params=` only, no auth.
   The GOWA bridge is behind HTTP auth (confirmed: `bijou-bridge-staging-v2.fly.dev`
   returns 401 unauthenticated) → even with a correct URL the calls would 401 → broken image.
3. **Staging config gap.** `bijou-agent-staging` had NEITHER `BRIDGE_URL` nor
   `WHATSAPP_BRIDGE_URL` set (only `BRIDGE_API_KEY`, `WHATSAPP_DEVICE_ID`).
   EVIDENCE: `flyctl secrets list --app bijou-agent-staging`.
   (Note: `bijou-agent-production` has BOTH set — same value hash — so prod's onboarding
   QR should already resolve there; the reported break reproduces where the URL is unset.)

### Secondary (latent) bug — connection status never flips even after a good scan
The webhook that sets `tenants.whatsapp_connected_at` (`src/core/bijou.py:~6621`) resolves
the tenant from a `whatsapp_devices(device_id → tenant_id)` row. Onboarding initializes the
bridge keyed by `tenant_id` and **never writes that row** (rows are only created later during
message handling, `bijou.py:5106`). So a connection event can't resolve the tenant →
`whatsapp_connected_at` stays null → status stuck → dashboard bounces. Real gap, exposed
once the QR works.

### Fixes applied (code only — NOT deployed)
- `src/saas/onboarding_api.py`
  - `get_whatsapp_bridge_url()` now falls back to `BRIDGE_URL` (matches
    `dashboard_api_simple.py:990`).
  - New `get_bridge_auth_headers()` mirrors the canonical auth priority documented at
    `dashboard_api_simple.py:1002` (BRIDGE_API_KEY "user:pass" → Basic > BRIDGE_USER+PASSWORD
    → Basic > BRIDGE_API_KEY → X-API-Key).
  - `/qr` + both `/api/init` calls now pass `headers=get_bridge_auth_headers()`.
- `src/core/bijou.py` (~6621) — guarded webhook fallback: if no `whatsapp_devices` row
  matches, and `device_id` IS a known `tenants.id`, link it and upsert the mapping.
  **Guarded = zero risk:** a phone-JID device_id matches no tenant → no-op, exactly as before.
- Staged secret: `flyctl secrets set BRIDGE_URL=https://bijou-bridge-staging-v2.fly.dev
  --stage --app bijou-agent-staging` (staged; applies on next deploy).

### Verification status
- ✅ VERIFIED: both files compile (`py_compile` OK).
- ✅ VERIFIED: new helpers are unit-tested — `tests/test_onboarding_bridge_helpers.py`,
  **7 passed** (`.venv/Scripts/python.exe -m pytest`).
- ⛔ NOT VERIFIED (billing-blocked): QR endpoint returning a real PNG in staging; a real
  phone scan flipping status to connected; dashboard no longer bouncing.

### To finish once billing is cleared
1. `flyctl deploy . --config fly.agent-staging.toml --app bijou-agent-staging --remote-only`
   (from the enterprise dir). Consider `.dockerignore` for `.venv-connectors/` (80MB) +
   `tests/` (34MB) to speed the 134MB build context.
2. Create a test tenant via the signup flow, then
   `curl -i https://bijou-agent-staging.fly.dev/api/onboarding/qr/<signup_token>` →
   expect `Content-Type: image/png` and a body >1KB (NOT a JSON error). That confirms fixes 1–3.
3. Scan with a real phone; watch logs for the webhook `connection.update`/`session.open`
   event and the `🔗 [WEBHOOK] Linked device … (onboarding fallback)` line; confirm
   `tenants.whatsapp_connected_at` is set and the dashboard stops bouncing.
4. If the bridge's connection event never arrives or uses a device_id ≠ tenant_id, inspect
   the bridge's real webhook payload and adjust the linkage in `bijou.py:~6621` accordingly.

---

## 2. Human-like Agent Persona — DIAGNOSIS (no blind edit made)

**Finding:** `src/core/bijou_system_prompt.txt` ALREADY contains the exact rules the owner
wants — auto language detection/mirroring (lines 43–53), "BE BRIEF — Max 30 words, sound
like texting a friend" (175), explicit anti-robotic examples (262), "Stay brief. Sound
human." (411). And the main reply path already loads this file (`bijou.py:4052-4057`,
"Always use file-based prompt (bypass persona manager)").

**So rewriting the prompt is the WRONG fix** (symptom, not cause). The robotic/verbose
regression most likely comes from one of these — confirm with a LIVE message + logs
(blocked by billing):
- (a) A different live path handles messages now (branch is `feat/composio-connector-layer`):
  check `gateway_agent.py` and the composio connector layer — do they use their own prompt
  or skip the persona?
- (b) Prompt dilution: the file gets appended with the vertical template (`bijou.py:4059+`)
  + knowledge context; the model may imitate verbose example blocks. Trim/prioritize the
  brevity rule to the END of the assembled prompt.
- (c) Token budget: `max_output_tokens` is 1024–3000 in various paths (`bijou.py:1524,2974,
  3102,4360`). Brevity is prompt-enforced, but a lower cap is a cheap belt-and-suspenders.

**Recommended:** this is a co-design + live-tuning task (owner said "we can talk n work n
that"). Start from the diagnosis above, not a rewrite.

---

## 3. NEXT SPRINT — proposed, ordered

1. **Clear Fly billing** → unblock all deploys. (Owner)
2. **Ship + verify the WhatsApp reconnect fix** in staging (steps in §1). Then set
   `BRIDGE_URL` on production parity if repointing.
3. **Persona regression** — live-diagnose which path/prompt the deployed agent uses (§2),
   fix the real cause, tune brevity together.
4. **Customer domain reach** — verify `bijou-agent-production` shares the same Supabase
   DB/secrets as whatever `app.mybijou.xyz` currently points at, THEN repoint the domain so
   customers see Google sign-in + the fixed reconnect. (Do NOT repoint blind.)
5. **Rotate the two scrubbed secrets** (Supabase service_role + Google client secret) —
   still outstanding from the 2026-07-23 scrub.
6. **Cleanup** — delete dead onboarding code (`onboarding_api_v3.py` is never mounted; the
   `/api/onboarding/v2/*` calls in `onboarding.html` hit no mounted router) to stop future
   debuggers chasing ghosts. Add the `.dockerignore` entries.

---

## Files touched this session
- `src/saas/onboarding_api.py` — bridge URL fallback + auth headers (MODIFIED)
- `src/core/bijou.py` — guarded webhook tenant-linkage fallback (MODIFIED)
- `tests/test_onboarding_bridge_helpers.py` — new unit tests, 7 passed (NEW)
- Staged secret `BRIDGE_URL` on `bijou-agent-staging` (NOT yet applied — needs deploy)
