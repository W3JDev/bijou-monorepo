# Deploying Bijou backend + GOWA bridge to Dokploy

Owner decisions (2026-09-26): **Dokploy is the production target for the
backend and the WhatsApp bridge.** Coolify is abandoned. Fly
(`bijou-production`) serves `app.mybijou.xyz` today and is the rollback
target. The landing site stays on Vercel (from `main`). Gemini keys are
revoked, so Gemini is not required. Stripe has to work.

**None of this has been deployed.** What was checked locally on 2026-09-26:

- `docker compose -f docker-compose.dokploy.yml config -q` exits 0 with every
  required var set, and fails with a named error when one is missing.
- The backend image builds and boots with no Gemini key: `/health` 200,
  `/openapi.json` 221 paths.
- Stripe webhook inside that container: an HMAC-signed event returns 200, a bad
  or missing signature returns 400.
- GOWA-style signed `/webhook/message` passes auth. An unsigned or wrong-signed
  request gets 401.
- The pinned GOWA image starts with the compose flags, and `/devices` answers
  only when basic auth is supplied.

Not checked yet: a real Supabase connection, a real Stripe key, a real
WhatsApp message, and anything on a Dokploy server.

| Artifact | Purpose |
|---|---|
| `docker-compose.dokploy.yml` | The stack: Traefik labels, healthchecks, the network split. |
| `ops/dokploy/Dockerfile.backend.dokploy` | Backend image, with the torch stack stripped. |
| `ops/dokploy/dokploy.env.example` | The full env contract, values redacted. Explains every variable. |
| ~~`ops/dokploy/Dockerfile.bridge.dokploy`~~, ~~`bridge-entrypoint.sh`~~ | **Not used.** They belong to `packages/bridge`. The bridge runs the GOWA image. |

---

## 0. Before you start (one day ahead)

1. **Lower the DNS TTL** on `app.mybijou.xyz` to 300 s at your DNS provider.
   Rollback then takes 5 minutes, not hours.
2. **Decide how WhatsApp sessions move.** Every tenant's WhatsApp link lives
   in the Fly bridge volume (`prod_bridge_data_v2`, mounted at
   `/app/storages` on `bijou-bridge-production-v2`). The new Dokploy bridge
   starts empty. There are two options:
   - **(a) Re-scan.** Each connected tenant scans a new QR after cutover.
     Nothing to copy, but every tenant has to do it.
   - **(b) Copy the session DB.** Stop the Fly bridge, run
     `fly ssh sftp get /app/storages/whatsapp.db -a bijou-bridge-production-v2`,
     and put the file in the Dokploy `bridge-data` volume before the bridge
     first starts. **NOT VERIFIED.** Fly is billing-locked, so ssh/sftp may be
     refused. Never run both bridges against the same WhatsApp session at
     once, or WhatsApp logs one of them out.
3. **Collect the values.** You need every variable in § 2 below.

## 1. Create the service in Dokploy

1. Dokploy → **Projects** → **Create Project** → name it `bijou`.
2. Inside it: **Create Service** → **Compose**.
3. **General** tab → Provider **GitHub**:
   - Repository: `mybijouai-creator/bijou-monorepo`
   - Branch: `main` (the Dokploy changes must be merged to `main` first; they
     are on `audit/hardening-pass` today)
   - Compose Path: `./docker-compose.dokploy.yml`
   - Compose type: **docker-compose** (not Stack)
4. Save.

The compose uses the external `dokploy-network`, which Dokploy creates when
it installs. The bridge stays on the internal network only. **Do not give it a
domain or ports.**

## 2. Environment tab

Paste `ops/dokploy/dokploy.env.example` and fill it in. The comments in that
file explain each variable. Names only:

**Required.** The compose uses `${VAR:?}`, so the deploy fails with a named
error if any of these is empty:

| Group | Variables |
|---|---|
| Identity | `PUBLIC_URL` (=`https://app.mybijou.xyz`), `BACKEND_DOMAIN` (=`app.mybijou.xyz`) |
| Database | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` |
| AI | `MINIMAX_API_KEY` |
| Secrets | `BIJOU_WEBHOOK_SECRET`, `ADMIN_API_KEY`, `DATA_REQUEST_SIGNING_KEY`. Generate each with `openssl rand -hex 32`. |
| Bridge | `BRIDGE_USER`, `BRIDGE_PASSWORD` (hex: it is embedded in the healthcheck URL) |
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_PRO_YEARLY` |

**Optional:**
- `OPENAI_API_KEY`. `ai://private` fails without it.
- `OPENROUTER_API_KEY`, `AI_GATEWAY_API_KEY`
- `STRIPE_PRICE_GROWTH_MONTHLY`, `STRIPE_PRICE_GROWTH_YEARLY`, `STRIPE_PUBLISHABLE_KEY`
- `RESEND_API_KEY` or `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD` plus
  `FROM_EMAIL`/`FROM_NAME`. **Without one of these, signup confirmation emails
  never send.**
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `NANGO_SECRET_KEY`, `NANGO_HOST`,
  `CALCOM_CLIENT_ID`, `CALCOM_CLIENT_SECRET`, `TELEGRAM_BOT_TOKEN`
- `LANGFUSE_*`, `LOG_LEVEL`, `WEB_CONCURRENCY`, `BACKEND_MEM_LIMIT`,
  `BRIDGE_MEM_LIMIT`, `IMAGE_TAG` (set it to the git SHA)

**DO NOT SET:**
- `LOGIN_URL`, `APP_URL`, `DASHBOARD_URL`, `GOOGLE_REDIRECT_URI`. Each one is
  read before the `PUBLIC_URL` fallback. A stale value sends users to the wrong
  origin and wipes their session. This bug class has hit the project twice.
- `ENABLE_COMPOSIO`. The compose pins it to `false`.
- `DB_TYPE`. The compose pins it to `supabase`.
- `BRIDGE_URL` / `WHATSAPP_BRIDGE_URL`. The compose pins both to
  `http://bridge:3000`.
- The old `packages/bridge` variables (`DEFAULT_TENANT_ID`, `ENABLE_HISTORY_SYNC`,
  `BIJOU_WEBHOOK_URL`, `DB_PATH`). GOWA does not read them.

Leave `GEMINI_API_KEY` empty. The keys are revoked.

A variable reaches a container **only** if the compose forwards it under that
service's `environment:`. Adding an unlisted variable in Dokploy does nothing.

## 3. Domains and volumes

1. **Domains** tab → Add Domain on service `backend`: host `app.mybijou.xyz`,
   container port `8080`, HTTPS on, certificate `letsencrypt`. The compose
   already carries the Traefik labels. Adding the domain here as well is
   harmless and makes it visible in the UI.
2. **Volumes.** The compose declares named volumes `backend-uploads` →
   `/app/uploads` and `bridge-data` → `/app/storages`. Keep them as named
   volumes, not bind mounts. **Back up `bridge-data`.** Losing it forces every
   tenant to re-scan the QR.

## 4. Deploy (order matters)

1. Click **Deploy**. Compose starts `backend` first. `bridge` has
   `depends_on: backend: service_healthy` and starts only after
   `/health/database` passes, which checks a real Supabase connection.
2. Watch **Logs**:
   - The backend should log `✅ Payment API routes included` and no
     `PROD CONFIG ERROR: Missing Stripe price-ID`.
   - The bridge should be listening on port 3000.
3. Both containers should show **healthy**. If `backend` never becomes
   healthy, check `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` first.

Before the DNS flip, you can check from the Dokploy server's shell:
`curl -s -H 'Host: app.mybijou.xyz' http://127.0.0.1/health`. Traefik routes
by Host, and the certificate is not issued yet.

## 5. DNS cutover: Fly → Dokploy

1. At the DNS provider, change the `app.mybijou.xyz` record from Fly (CNAME
   `bijou-production.fly.dev` or Fly A/AAAA records) to an **A record → the
   Dokploy server's public IP**. Remove any Fly AAAA record, or IPv6 clients
   keep hitting Fly.
2. Wait for propagation: `dig +short app.mybijou.xyz` should return the Dokploy
   IP.
3. Traefik requests the Let's Encrypt certificate on the first HTTPS request
   after DNS resolves. Expect roughly a minute of TLS errors.
4. **Stripe:** the endpoint URL does not change, because the domain is the
   same. In Stripe Dashboard → Developers → Webhooks, confirm the endpoint is
   exactly `https://app.mybijou.xyz/api/payment/webhook` and not a
   `*.fly.dev` URL. Confirm it sends `checkout.session.completed`,
   `customer.subscription.updated`, `customer.subscription.deleted` and
   `invoice.payment_failed`. `STRIPE_WEBHOOK_SECRET` in Dokploy must be **this
   endpoint's** signing secret (Reveal → `whsec_…`). Otherwise every event
   returns 400.
5. **Google OAuth** (only if it is used): the Cloud Console client must list
   `https://app.mybijou.xyz/api/auth/google/callback`. That is unchanged by
   the move.

## 6. Post-deploy verification (do all of these before announcing)

```bash
# 1. Liveness and DB. /health alone returns 200 even with the DB down.
curl -fsS https://app.mybijou.xyz/health            # expect "version":"2.2.0"
curl -fsS https://app.mybijou.xyz/health/database   # must be 200

# 2. Routers mounted. Measured 221 on this branch's image (2026-09-26).
#    Roughly 41 means startup did not finish.
curl -s https://app.mybijou.xyz/openapi.json | python3 -c "import json,sys;print(len(json.load(sys.stdin)['paths']))"

# 3. Serving from Dokploy, not Fly. Fly responses carry a fly-request-id header.
curl -sI https://app.mybijou.xyz/health | grep -i fly-request-id || echo "not Fly: good"

# 4. Stripe webhook rejects unsigned requests (expect 400)
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://app.mybijou.xyz/api/payment/webhook -d '{}'
```

5. **Stripe test webhook.** In Stripe Dashboard → Webhooks → the endpoint →
   **Send test event** → `invoice.payment_failed`. Expect a 200 with
   `"received":true` in Stripe's delivery log, and
   `📨 Stripe webhook processing: invoice.payment_failed` in the backend logs.
   With the Stripe CLI instead: `stripe trigger invoice.payment_failed`.
6. **Stripe checkout.** Sign in to the dashboard in a browser, go to Billing,
   choose PRO, and confirm you land on a `checkout.stripe.com` page. In test
   mode, pay with `4242 4242 4242 4242` and confirm the tenant's `plan`
   becomes `pro`.
7. **Browser sign-in.** Sign in at `https://app.mybijou.xyz/login` and reach
   the dashboard with a clean console. A 200 from the API does not prove
   this works.
8. **WhatsApp round trip.** Dashboard → WhatsApp → scan the QR with a test
   phone, or skip the scan if you migrated the sessions. From a *different*
   phone, message the connected number and confirm the AI reply arrives. This
   is the only check that proves bridge → backend (signed webhook) and
   backend → bridge (`BRIDGE_URL`) both work. In the backend logs, a `401` on
   `/webhook/message` means `BIJOU_WEBHOOK_SECRET` is inconsistent.
9. **Stop the Fly backend and bridge** once the checks pass, so two
   schedulers are not writing to the same Supabase. Keep the Fly apps and
   volumes (do not destroy them) until you no longer need rollback. With Fly
   billing-locked, `fly scale count 0` may itself be refused. **NOT
   VERIFIED.**

## 7. Rollback

1. Point the `app.mybijou.xyz` DNS record back to Fly (`bijou-production.fly.dev`).
   With TTL 300 this takes effect in about 5 minutes.
2. If you stopped the Fly machines, start them again. This needs the Fly
   account out of billing lock.
3. Stripe needs no change, because the URL is the same domain. Events
   delivered while DNS was switching are retried by Stripe automatically.
4. WhatsApp: if tenants re-scanned on Dokploy, their sessions now live in the
   Dokploy `bridge-data` volume. Rolling back to the Fly bridge means
   re-scanning again, or restoring the old Fly volume.
5. Within Dokploy, a bad image can be rolled back from **Deployments**. Set
   `IMAGE_TAG` to a git SHA so "previous" is unambiguous.

---

## Reference

### The bridge is GOWA, not packages/bridge

`packages/bridge` (Go + whatsmeow) is not the production bridge
(`src/saas/onboarding_api.py:576`; `packages/bridge/fly.bridge-production.toml`
runs `aldinokemal2104/go-whatsapp-web-multidevice`). They expose different
APIs. `packages/bridge` serves `/qr` and `/api/init`, but the backend calls
`/devices` and `/app/login`. Ship the wrong one and the QR step can never work.

- **Pinned by digest.** It is an unofficial WhatsApp Web client, and an
  unattended upgrade can break every session at once.
- **It signs webhooks.** Each request carries
  `X-Hub-Signature-256: sha256=<hmac(body, BIJOU_WEBHOOK_SECRET)>`, and
  `_verify_webhook_secret` in `src/core/bijou.py` checks it. The compose passes
  one `BIJOU_WEBHOOK_SECRET` to both the backend env and GOWA's
  `--webhook-secret`.
- Flags `--os`, `--auto-download-media`, `--auto-mark-read`,
  `--auto-reject-call` and `--webhook-events` mirror the live Fly bridge's
  `[env]`.

### Stripe

`src/saas/payment_api.py`, mounted in `src/core/bijou.py::_include_routers()`:

| Route | Auth | Notes |
|---|---|---|
| `GET /api/payment/plans` | public | |
| `POST /api/payment/checkout` | session | Price = `STRIPE_PRICE_<PLAN>_<MONTHLY\|YEARLY>`, read per request. Unset falls back to hardcoded ids of unknown mode. |
| `POST /api/payment/portal` | session | Needs `tenants.stripe_customer_id` |
| `POST /api/payment/webhook` | Stripe signature | `stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)`. Rejects every request when the secret is unset. |

Fixed 2026-09-26 (unit tests in `tests/unit/test_payment_webhook_endpoint.py`):
- A **correctly signed** webhook returned 500. stripe-python ≥8 returns a
  `StripeObject` with no `.get`. Reproduced in the container, then fixed.
- With `STRIPE_WEBHOOK_SECRET` unset, the webhook **skipped verification**.
  That let a forged `checkout.session.completed` change any tenant's plan. It
  now fails closed.
- `customer.subscription.updated` only knew `STRIPE_PRICE_STARTER`/`_PRO`, so
  a PRO trial converting to active was **downgraded to "starter"**. It now maps
  the ids checkout actually sells, and leaves the tier unchanged for an
  unknown price.
- Checkout passed `automatic_payment_methods`. That parameter is not in
  stripe-python's `checkout.Session.create` params, and Stripe rejects unknown
  parameters. Removed. **NOT VERIFIED against the live Stripe API**, since no
  key was available.
- The price-id startup guard now also treats `ENVIRONMENT=production` (which
  this compose sets) as production.

### Healthchecks

| Endpoint | Verdict |
|---|---|
| `/health` | Liveness only. It returns 200 with the DB unreachable. |
| `/api/self-test/summary` | Times out. Do not use it. |
| `/health/database` | **Used by the compose.** It checks the DB connection. |

The bridge healthcheck is `wget --spider http://$BRIDGE_USER:$BRIDGE_PASSWORD@127.0.0.1:3000/devices`.
Busybox wget has no `--user`, so the credentials go in the URL.

### AI without Gemini

Every alias except `ai://private` falls through to MiniMax
(`packages/backend/llm_gateway.yaml`). `ai://private` is strict-privacy
(gemini/openai only) and needs `OPENAI_API_KEY`. Known gap: image upload in
`src/core/bijou.py` and about 13 modules still call the Gemini SDK directly,
so those features degrade until they are migrated. The container boot log shows
`RoundRobinRotator: no API keys provided`, which is expected.

### Resources

`WEB_CONCURRENCY=2` and `BACKEND_MEM_LIMIT=2G` are reasoned defaults, not
measured ones. The backend image is 1.35 GB (built 2026-09-26, torch
stripped).

### TLS and CORS

Traefik terminates TLS, and the compose sets `X-Forwarded-Proto: https`. The
CORS allow-list in `src/core/bijou.py` is `mybijou.xyz`, `www.mybijou.xyz`,
`app.mybijou.xyz` and localhost. Add any other serving host there before
deploying.

### Schema

The existing Supabase project needs nothing extra. For a NEW environment,
apply `migrations-py/0000_baseline.sql`, then the rest of `migrations-py/`.
There is no automatic migration runner.
