#!/usr/bin/env bash
# Start the FastAPI backend on :8000 wired to the local GOWA bridge (bridge.sh).
# LLM + Supabase keys come from packages/backend/.env (loaded by bijou.py).
# Do NOT source the root .env here: its MINIMAX_API_KEY is stale (401) and would
# override the working one, and its BRIDGE_URL points at the Fly bridge.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
set -a; . "$HERE/.env.local"; set +a
ROOT="$HERE/../.."
val() { grep -E "^$1=" "$2" | head -1 | cut -d= -f2- | tr -d '"\r'; }

# LLM keys. A Windows user-level MINIMAX_API_KEY (the stale root-.env one, 401)
# beats load_dotenv, so pin the working key from packages/backend/.env explicitly.
export MINIMAX_API_KEY="$(val MINIMAX_API_KEY "$ROOT/packages/backend/.env")"
# Fallbacks in llm_gateway.yaml's chains; both verified 200 on 2026-09-27.
export OPENROUTER_API_KEY="$(val OPENROUTER_API_KEY "$ROOT/.env")"
export CLOUDFLARE_API_TOKEN="$(val CLOUDFLARE_API_TOKEN "$ROOT/.env")"
export CLOUDFLARE_ACCOUNT_ID="$(val CLOUDFLARE_ACCOUNT_ID "$ROOT/.env")"
export GEMINI_API_KEY="$(val GEMINI_API_KEY "$ROOT/.env")"   # ai://private (gemini-3.8-flash)

export DB_TYPE=supabase
export BRIDGE_URL=http://127.0.0.1:3120
export WHATSAPP_BRIDGE_URL=http://127.0.0.1:3120
export MULTI_TENANT_ENABLED=TRUE
# MY BIJOU AI (60174106981) - the tenant with the real sales traffic.
export DEFAULT_TENANT_ID=dae52bc5-8ad7-40fb-81bb-84325b23c6ff
export WHATSAPP_DEVICE_ID=bijou-dae52bc5-8ad7-40fb-81bb-84325b23c6ff
export PUBLIC_URL=https://app.mybijou.xyz
# Only reply to inbound messages. Both schedulers send unprompted WhatsApp
# messages from the owner's number; production runs its own copies.
export ENABLE_OUTREACH_SCHEDULER=false
export ENABLE_PROACTIVE_MESSAGING=false
# Reply 24/7 like production (root .env has the same). Unset = silent after hours.
export DISABLE_BUSINESS_HOURS=TRUE
# Emoji log lines otherwise raise UnicodeEncodeError on the Windows console.
export PYTHONUTF8=1

cd "$HERE/../../packages/backend"
exec ./.venv/Scripts/python.exe -m uvicorn src.core.bijou:app --host 0.0.0.0 --port 8000
