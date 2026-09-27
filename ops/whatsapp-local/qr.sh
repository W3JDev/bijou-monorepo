#!/usr/bin/env bash
# Fetch a FRESH login QR (valid ~30s) for the MY BIJOU AI device and open it.
# Usage: bash ops/whatsapp-local/qr.sh [out.png]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
set -a; . "$HERE/.env.local"; set +a
OUT="${1:-$HERE/whatsapp-qr.png}"
A="$BRIDGE_USER:$BRIDGE_PASSWORD"
LINK=$(curl -s -u "$A" "http://127.0.0.1:3120/app/login?device_id=bijou-dae52bc5-8ad7-40fb-81bb-84325b23c6ff" \
  | sed -E 's/.*"qr_link":"([^"]+)".*/\1/')
case "$LINK" in http*) ;; *) echo "No QR (already logged in?): $LINK" >&2; exit 1;; esac
curl -s -u "$A" -o "$OUT" "$LINK"
echo "QR saved: $OUT (scan within ~30s)"
command -v cygpath >/dev/null && explorer.exe "$(cygpath -w "$OUT")" || true
