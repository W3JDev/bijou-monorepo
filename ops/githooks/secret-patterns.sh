# Credential shapes the pre-commit guard blocks.
#
# Sourced by ops/githooks/pre-commit AND ops/githooks/test-secret-guard.sh, so
# the test exercises the real pattern rather than a copy that can drift.
#
# Deliberately NOT matched case-insensitively. The previous guard used grep -i,
# which made an ordinary git log line —
#   "c0c07ba  ops/coolify: ops/coolify/PRODUCTION-CUTOVER-PLAN.md"
# — match the COOLIFY key=value alternative and block legitimate commits. Real
# env keys are uppercase. The value class also excludes "/" so that file paths
# are not read as secrets.
SECRET_PATTERN='(sk_live_[A-Za-z0-9]{10,}'\
'|AKIA[0-9A-Z]{16}'\
'|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}'\
'|xox[baprs]-[A-Za-z0-9-]{10,}'\
'|sbp_[a-f0-9]{40,}'\
'|-----BEGIN [A-Z ]*PRIVATE KEY-----'\
'|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'\
'|[0-9]+\|[A-Za-z0-9]{40,}'\
'|[Bb]earer[[:space:]]+[A-Za-z0-9][A-Za-z0-9_.|~+-]{29,}'\
'|(COOLIFY|SUPABASE_SERVICE|SUPABASE_ANON|FLY_API|BIJOU_FLY_API|INTERNAL_API|RESEND_API|STRIPE_SECRET|ADMIN_API|VERCEL|NANGO_SECRET|TELNYX_API|GEMINI_API|OPENAI_API|TELEGRAM_BOT|DATA_REQUEST_SIGNING)[A-Z_]*[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9_.+=-]{12,})'
