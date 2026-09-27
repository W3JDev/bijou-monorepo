# WhatsApp on +60174106981, run locally

Local GOWA bridge (same pinned digest as `docker-compose.dokploy.yml`) + the
FastAPI backend on this machine. The backend talks to the **production**
Supabase project, so replies, conversations and messages land in the real
`MY BIJOU AI` tenant (`dae52bc5-8ad7-40fb-81bb-84325b23c6ff`).

Secrets live in `ops/whatsapp-local/.env.local` (gitignored):
`BIJOU_WEBHOOK_SECRET`, `BRIDGE_USER`, `BRIDGE_PASSWORD`. The same webhook
secret goes to both processes, so GOWA's `X-Hub-Signature-256` verifies.

## Start

```bash
bash ops/whatsapp-local/bridge.sh        # GOWA on 127.0.0.1:3120, registers the device
bash ops/whatsapp-local/run-backend.sh   # backend on :8000 (foreground)
```

`run-backend.sh` turns off the outreach and proactive schedulers, so this
instance only replies to inbound messages. It also sets `MINIMAX_API_KEY`
explicitly, because a Windows user-level variable holds a stale key that
returns 401.

## Link the phone (QR codes expire in about 30 s)

```bash
bash ops/whatsapp-local/qr.sh            # saves ops/whatsapp-local/whatsapp-qr.png and opens it
```

On the phone go to WhatsApp → Settings → Linked devices → Link a device, then
scan. Run `qr.sh` again if the code expires. The GOWA web UI at
http://127.0.0.1:3120/ (basic auth from `.env.local`) is another way to get a QR.

## After scanning, check

```bash
. ops/whatsapp-local/.env.local
curl -s -u "$BRIDGE_USER:$BRIDGE_PASSWORD" http://127.0.0.1:3120/devices   # state should be logged_in/connected
curl -s http://localhost:8000/bridge/health                                 # connected: 1
```

Then send a WhatsApp to +60174106981 from a **different** phone. You should get
a Manglish sales reply within about 15 s. The backend log shows
`Identified tenant: MY BIJOU AI` and does not show `[WA] Send failed`.

Before scanning, remove stale entries under Linked devices. Any other bridge
that still holds a session for this number would answer customers as well.

## Stop

`Ctrl+C` the backend, then `docker rm -f bijou-gowa-local`. The session is
kept in the `bijou-gowa-local` volume, so a restart does not need a new scan.
