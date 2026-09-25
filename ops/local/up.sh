#!/usr/bin/env bash
# The one command. Mints local keys if needed, then brings the stack up.
#
#   ./ops/local/up.sh              backend + landing + bridge + supabase core
#   ./ops/local/up.sh --profile full        ... plus voice and posthog
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

[ -f ops/local/.env.local ] || ./ops/local/gen-local-keys.sh

# Regenerated every run by _preflight_gemini. Gitignored via ops/local/.env.*
GEMINI_ENV_FILE="ops/local/.env.gemini"

# Two --env-file flags: root .env first, ops/local/.env.local second, so the
# local override wins on conflict. That is the original order and the right one
# — an override file exists to override.
#
# The Gemini keys no longer depend on this order at all. _preflight_gemini
# below resolves and sanitises them and then EXPORTS them, and a shell variable
# outranks every --env-file in compose interpolation. That is deliberate: the
# ordering was previously load-bearing for those two variables, and getting it
# wrong silently substituted one key for another with no signal anywhere.
#
# Everything else still relies on the order, and on this rule: SUPABASE_URL is
# a hardcoded literal (http://supabase-gateway:8000) and the local Supabase
# keys arrive via `env_file:` on each service, so NOTHING in root .env can
# redirect a local container at the production database. Every other local knob
# is LOCAL_-prefixed for the same reason.
#
# Do not add a bare ${SUPABASE_...}, ${JWT_SECRET} or ${DB_PASSWORD}
# interpolation to this compose. ops/local/.env.local defines all of those
# under the SAME names root .env uses for PRODUCTION, and that rule is the only
# thing keeping the two apart. Sharing a Gemini key costs money; pointing local
# at prod costs data.

# ---------------------------------------------------------------------------
# Preflight: say out loud which Gemini key the stack will actually use.
#
# This exists because the failure it catches was invisible. A stale
# LOCAL_GEMINI_API_KEY in ops/local/.env.local shadowed the correct key in root
# .env, and the ONLY symptom was Google replying "API key not valid" — which
# reads as "your key is wrong" when the key was fine. Nothing anywhere said a
# substitution had happened.
#
# Prints shape only: length and first four characters, never the key.
# ---------------------------------------------------------------------------
_gem_shape() {
  # $1 = label, $2 = value
  local label="$1" val="${2:-}"
  if [ -z "$val" ]; then
    printf '  %-22s (unset)\n' "$label"
  else
    printf '  %-22s len=%-3s starts=%s\n' "$label" "${#val}" "$(printf '%.4s' "$val")"
  fi
}

_sanitise_key() {
  # Strip surrounding whitespace/CR, surrounding quotes, and a LEADING '='.
  #
  # The '=' is not hypothetical. `GEMINI_API_KEY==AQ.Ab8...` in an env file
  # yields the value "=AQ.Ab8..." — a paste where the '=' came along with the
  # key. No Google key format starts with '=', so this is always a typo and
  # never a real value. It cost a full debugging session because the only
  # symptom was Google rejecting the key, which reads as "your key is wrong".
  printf '%s' "$1" \
    | tr -d '\r' \
    | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
          -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'\$//" \
          -e 's/^=//'
}

_key_format() {
  # Both formats are current. Google AI Studio issues AQ.* keys now; AIza* keys
  # are the older format and still valid. I previously asserted AQ. was "a
  # different credential family" and wrong — it is not, it is the newer one.
  case "$1" in
    AQ.*)   echo "AQ (current AI Studio format)" ;;
    AIza*)  [ "${#1}" -eq 39 ] && echo "AIza (legacy, 39 chars)" || echo "AIza-like, but ${#1} chars not 39" ;;
    local-placeholder-key) echo "placeholder" ;;
    *)      echo "UNRECOGNISED" ;;
  esac
}

_preflight_gemini() {
  local root_key local_same local_pref raw resolved src

  root_key=$(sed -n 's/^GEMINI_API_KEY=//p' .env 2>/dev/null | head -1)
  # The override file may use either name. Check both.
  local_same=$(sed -n 's/^GEMINI_API_KEY=//p' ops/local/.env.local 2>/dev/null | head -1)
  local_pref=$(sed -n 's/^LOCAL_GEMINI_API_KEY=//p' ops/local/.env.local 2>/dev/null | head -1)

  # The override file wins — that is what an override file is FOR. Root .env is
  # the fallback for a machine that has no local override.
  if   [ -n "$local_pref" ]; then raw="$local_pref"; src="ops/local/.env.local (LOCAL_GEMINI_API_KEY)"
  elif [ -n "$local_same" ]; then raw="$local_same"; src="ops/local/.env.local (GEMINI_API_KEY)"
  elif [ -n "$root_key"   ]; then raw="$root_key";   src=".env"
  else raw="local-placeholder-key"; src="built-in default"
  fi

  resolved=$(_sanitise_key "$raw")

  echo "Gemini key the stack will use:"
  _gem_shape ".env"                 "$(_sanitise_key "$root_key")"
  _gem_shape "ops/local override"   "$(_sanitise_key "${local_pref:-$local_same}")"
  _gem_shape "-> resolved"          "$resolved"
  echo "     from: $src"
  echo "   format: $(_key_format "$resolved")"

  if [ "$resolved" = "local-placeholder-key" ]; then
    echo "  note: placeholder — LLM calls will fail by design, nothing is billed."
  elif [ "$raw" != "$resolved" ]; then
    echo "  WARNING: the env line needed cleaning up (stray '=' or quotes)." >&2
    echo "           Using the cleaned value so the stack works, but FIX THE LINE" >&2
    echo "           in $src — otherwise anything that reads it directly still breaks." >&2
  fi

  case "$(_key_format "$resolved")" in
    UNRECOGNISED*)
      echo "  WARNING: not an AQ.* or AIza* key. If Google rejects it, that is why." >&2 ;;
  esac

  # Write the cleaned values to a generated env file passed LAST to compose, so
  # they win outright. Last --env-file wins, which is verifiable and does not
  # depend on anything subtle.
  #
  # Exporting a shell variable was tried first and does NOT work here: the
  # stack is commonly driven from WSL against Windows Docker Desktop, and a
  # WSL shell variable does not cross into docker.exe unless it is listed in
  # WSLENV. Measured — the export was silently ignored and the container kept
  # the malformed key. A file crosses that boundary; an env var may not.
  # GEMINI_API_KEYS must agree with GEMINI_API_KEY, and this is not cosmetic.
  # The v1 rotator (src/core/llm_gateway.py RoundRobinRotator) PREFERS the list,
  # so a stale list silently wins over a freshly fixed primary key. Measured:
  # with the correct key in GEMINI_API_KEY, the gateway still failed with
  # "Consumer 'api_key:AIza...' has been suspended" because the list held three
  # copies of the dead key.
  #
  # So: put the resolved key FIRST, then any OTHER distinct keys from the list.
  # Rotation is preserved where it is real, and the working key always leads.
  # Duplicates are dropped — the list in .env was the same key three times,
  # which is not rotation, it just looks like it.
  local keys_raw
  keys_raw=$(sed -n 's/^GEMINI_API_KEYS=//p' ops/local/.env.local 2>/dev/null | head -1)
  [ -z "$keys_raw" ] && keys_raw=$(sed -n 's/^GEMINI_API_KEYS=//p' .env 2>/dev/null | head -1)

  local keys_out="$resolved" part clean dropped=0
  local IFS_SAVE="$IFS"
  IFS=','
  for part in $keys_raw; do
    clean=$(_sanitise_key "$part")
    [ -z "$clean" ] && continue
    case ",${keys_out}," in
      *",${clean},"*) dropped=$((dropped + 1)); continue ;;
    esac
    keys_out="${keys_out},${clean}"
  done
  IFS="$IFS_SAVE"

  local n_out
  n_out=$(printf '%s' "$keys_out" | awk -F, '{print NF}')
  echo "  rotator: ${n_out} distinct key(s)$([ "$dropped" -gt 0 ] && echo ", ${dropped} duplicate(s) dropped")"

  umask 077
  {
    echo "# GENERATED by ops/local/up.sh on every run. Do not edit; edits are lost."
    echo "# Holds the sanitised Gemini keys and nothing else. Passed to compose"
    echo "# LAST so it wins over both .env and ops/local/.env.local."
    echo "GEMINI_API_KEY=${resolved}"
    echo "GEMINI_API_KEYS=${keys_out}"
  } > "$GEMINI_ENV_FILE"
}

_preflight_gemini || exit 1
echo

exec docker compose \
  --env-file .env \
  --env-file ops/local/.env.local \
  --env-file "$GEMINI_ENV_FILE" \
  -f docker-compose.local.yml \
  up "$@"
