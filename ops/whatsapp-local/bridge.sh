#!/usr/bin/env bash
# Start the local GOWA bridge (same pinned digest as docker-compose.dokploy.yml)
# on 127.0.0.1:3120 and register the MY BIJOU AI device. Idempotent.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
set -a; . "$HERE/.env.local"; set +a
export MSYS_NO_PATHCONV=1   # Git Bash would otherwise mangle /app/storages
IMAGE=aldinokemal2104/go-whatsapp-web-multidevice@sha256:2b942792de76be3940e507507f24b50012e4b4048f31a2eb2380f1d01ca3a9f0
DEV=bijou-dae52bc5-8ad7-40fb-81bb-84325b23c6ff

if ! docker ps -q --filter name=^bijou-gowa-local$ | grep -q .; then
  docker rm -f bijou-gowa-local >/dev/null 2>&1 || true
  docker run -d --name bijou-gowa-local --restart unless-stopped \
    -p 127.0.0.1:3120:3000 --add-host host.docker.internal:host-gateway \
    -v bijou-gowa-local:/app/storages "$IMAGE" rest --port=3000 \
    --os=BijouAI-Local --auto-download-media=true --auto-mark-read=false \
    --auto-reject-call=true --webhook-events=message,message.ack,group.participants \
    --webhook=http://host.docker.internal:8000/webhook/message \
    --webhook-secret="$BIJOU_WEBHOOK_SECRET" \
    --basic-auth="$BRIDGE_USER:$BRIDGE_PASSWORD" \
    "--db-uri=file:/app/storages/whatsapp.db?_foreign_keys=on"
  sleep 5
fi
# Registering an existing device just returns an error; harmless.
curl -s -u "$BRIDGE_USER:$BRIDGE_PASSWORD" -X POST http://127.0.0.1:3120/devices \
  -H "Content-Type: application/json" -d "{\"device_id\":\"$DEV\"}" >/dev/null || true
curl -s -u "$BRIDGE_USER:$BRIDGE_PASSWORD" http://127.0.0.1:3120/devices; echo
