#!/usr/bin/env bash
# Self-test for ops/githooks/pre-commit.
#
# Two regressions are pinned here specifically:
#   MUST CATCH  a Coolify/Laravel Sanctum token ("1|<40+ chars>"), which the
#               previous guard missed — that is how a live token reached
#               origin/main on 2026-08-29.
#   MUST PASS   a git log line like "c0c07ba  ops/coolify: ops/coolify/FOO.md",
#               which the previous guard blocked because it matched
#               case-insensitively and let "/" into the value class.
#
# Run after any change to PATTERN:  ./ops/githooks/test-secret-guard.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$HERE/secret-patterns.sh" ] || { echo "FATAL: secret-patterns.sh not found"; exit 1; }

. "$HERE/secret-patterns.sh"
PATTERN="$SECRET_PATTERN"

# Credential SHAPES, assembled at runtime rather than written as literals.
#
# They are fixtures, not secrets — but a literal "ghp_<40 chars>" in a tracked
# file is enough for GitHub push protection to reject the entire push, which is
# exactly what it did:
#   remote: path: ops/githooks/test-secret-guard.sh:41
#   remote: push declined due to repository rule violations
# Splitting the prefix from the body keeps the regex under real test while
# leaving nothing for a scanner to match on disk.
Z=0123456789
A=abcdefghijklmnopqrstuvwxyz
JWT_H="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
JWT_P="eyJyb2xlIjoiYW5vbiJ9"
GH_PAT="gh""p_${Z}${A}${Z}"
SLACK_TOK="xox""b-${Z}-${A}"
STRIPE_TOK="sk_""live_${Z}${A}"
SBP_TOK="sb""p_${Z}${Z}${Z}${Z}"
AWS_ID="AKI""AIOSFODNN7EXAMPLE"
SANCTUM="1|""${A}${A}${Z}"

pass=0; fail=0

check() { # check <expect: CATCH|PASS> <label> <line>
  # Mirrors what the HOOK decides, not just what the regex matches. The two
  # differ on purpose: the pattern legitimately matches inside
  #   "${LOCAL_GEMINI_API_KEY:-${GEMINI_API_KEY:-local-placeholder-key}}"
  # because the inner fallback looks like KEY:-value. The hook then drops any
  # line containing ${, since that is a reference to a secret rather than one.
  # Testing only the pattern would assert the wrong thing.
  local expect="$1" label="$2" line="$3" got
  if printf '%s\n' "$line" | grep -Eq "$PATTERN" \
     && ! printf '%s\n' "$line" | grep -q '\${' \
     && ! printf '%s\n' "$line" | grep -q 'pragma: allowlist secret' \
     && ! printf '%s\n' "$line" | grep -oE "$PATTERN" | head -1 \
          | grep -qiE 'placeholder|changeme|not-a-real|local-dev-only|<your-|your-key-here|xxxxx'; then
    got=CATCH
  else
    got=PASS
  fi
  if [ "$got" = "$expect" ]; then
    pass=$((pass+1)); printf '  ok    %-52s (%s)\n' "$label" "$got"
  else
    fail=$((fail+1)); printf '  FAIL  %-52s expected %s got %s\n' "$label" "$expect" "$got"
  fi
}

echo "MUST CATCH — these are credential shapes:"
check CATCH "Sanctum/Coolify token (the 2026-08-29 leak)" "+  -H \"Authorization: Bearer ${SANCTUM}\""  # pragma: allowlist secret
check CATCH "Sanctum token bare, no Bearer"               "+COOLIFY_TOKEN=${SANCTUM}"  # pragma: allowlist secret
check CATCH "JWT (three dot-separated segments)"          "+key: ${JWT_H}.${JWT_P}.AAAAAAAAAAAAAA"  # pragma: allowlist secret
check CATCH "Supabase management PAT"                     "+SUPABASE_PAT=${SBP_TOK}"  # pragma: allowlist secret
check CATCH "Stripe live key"                             "+STRIPE_SECRET_KEY=${STRIPE_TOK}"  # pragma: allowlist secret
check CATCH "AWS access key id"                           "+aws_key = ${AWS_ID}"  # pragma: allowlist secret
check CATCH "GitHub PAT"                                  "+token: ${GH_PAT}"  # pragma: allowlist secret
check CATCH "Slack token"                                 "+SLACK=${SLACK_TOK}"  # pragma: allowlist secret
check CATCH "private key header"                          '+-----BEGIN RSA PRIVATE KEY-----'  # pragma: allowlist secret
check CATCH "generic Bearer with long opaque token"       '+Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789'  # pragma: allowlist secret
check CATCH "service key assignment"                      '+SUPABASE_SERVICE_KEY=abcdefghij0123456789'  # pragma: allowlist secret

echo
echo "MUST PASS — these are NOT credentials:"
check PASS  "git log line (the false positive that blocked me)" '+c0c07ba  ops/coolify: ops/coolify/PRODUCTION-CUTOVER-PLAN.md'
check PASS  "env var referenced, not assigned"            '+  -H "Authorization: Bearer ${COOLIFY_API_TOKEN:?set COOLIFY_API_TOKEN}"'
check PASS  "empty assignment in a .env.example"          '+SUPABASE_SERVICE_KEY='
check PASS  "placeholder value"                           '+SUPABASE_SERVICE_KEY=<your-supabase-service-role-key>'
check CATCH "REAL key on a line that mentions placeholder" '+STRIPE_SECRET_KEY=sk_live_9x8y7z6w5v4u3t2s1r  # replaces the placeholder'  # pragma: allowlist secret
check PASS  "doc line telling you to set a placeholder"   '+# Set LOCAL_GEMINI_API_KEY=local-placeholder-key to opt back out.'
check PASS  "env template with an angle-bracket stub"     '+SUPABASE_SERVICE_KEY=<your-service-role-key>'
check PASS  "prose mentioning a key by name"              '+The ADMIN_API_KEY gates every /api/admin/* endpoint.'
check PASS  "compose interpolation"                       '+  GEMINI_API_KEY: "${GEMINI_API_KEY:?set GEMINI_API_KEY}"'
check PASS  "NESTED compose interpolation with fallback"  '+  GEMINI_API_KEY: "${LOCAL_GEMINI_API_KEY:-${GEMINI_API_KEY:-local-placeholder-key}}"'
check PASS  "bearer header built from a variable"         '+  -H "Authorization: Bearer ${COOLIFY_API_TOKEN:?set COOLIFY_API_TOKEN}"'
check PASS  "a file path containing coolify"              '+  dockerfile: ops/coolify/Dockerfile.backend.coolify'
check PASS  "short hex that is a commit sha"              '+see commit 41f9f05 for the CI change'

echo
echo "passed: $pass   failed: $fail"
[ "$fail" -eq 0 ] || exit 1
