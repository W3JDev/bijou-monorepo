# SECURITY ALERT — Coolify API token exposure (2026-09-06)

**Severity: P0.** A live Coolify API token is committed in this repository and
has been pushed to `origin/main`. It still matches the value in the operator's
local `.env`, so it has not been rotated.

Found during the 2026-09-05/06 hardening audit. This is the **second** credential
committed to this repo — see `docs/SECURITY_ALERT_2026-08-24_admin_key.md`. That
one was an admin API key on 2026-08-10. This one was committed on **2026-08-29/30,
five days after that post-mortem was written.**

## What is exposed

A Coolify API token (Laravel Sanctum format, `1|…`, 50 chars) for
`https://coolify.getbijou.xyz`.

Present in three **tracked** files:

| File | Occurrences |
|---|---|
| `ops/coolify/load-agentops-image.sh` | 1 |
| `ops/coolify/PRODUCTION-CUTOVER-PLAN.md` | 1 |
| `docs/handoffs-and-audits/2026-08-29-coolify-cutover-prep.md` | 2 |

Reachable in pushed history from at least these commits:

```
6052bb2  chore(2026-08-30): Coolify CI/CD + P0 fixes
5fcf02b  docs: coolify cutover prep
c0c07ba  ops/coolify: ops/coolify/PRODUCTION-CUTOVER-PLAN.md
```

How this was confirmed (the token value is deliberately not reproduced here):

```bash
git ls-files -z | xargs -0 grep -l -F "$TOK"     # 3 tracked files
git log --oneline origin/main -S"$TOK"           # 3 commits, pushed
grep -qF "$TOK" .env && echo "still live"        # still live
```

## Blast radius

A Coolify API token is **platform-level control**, which is broader than the
2026-08-10 admin key. With it an attacker can:

- **Read every environment variable of every service.** That includes
  `SUPABASE_SERVICE_KEY` — which, because RLS was hardened to service-role-only
  (`ops/_fix_rls_v6.js`), is unrestricted read/write on all tenant data — plus
  `GEMINI_API_KEY`, `STRIPE_SECRET_KEY`, `ADMIN_API_KEY` and the rest.
- **Deploy arbitrary code** by changing a service's image or compose and
  triggering a deploy.
- **Stop, start, or delete services**, including the database-backed ones.

So the practical assumption is that **every secret held in Coolify is also
compromised**, not just this token.

## Owner actions — required, in this order

These need platform access and cannot be done from the repo.

1. **Revoke the token now.** Coolify → Keys & Tokens → API Tokens → revoke it.
   Do this before anything else; it is the only step that stops active use.
2. **Rotate every secret Coolify held**, on the assumption they were readable:
   `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`, `STRIPE_SECRET_KEY`,
   `STRIPE_WEBHOOK_SECRET`, `ADMIN_API_KEY`, `RESEND_API_KEY`, and any OAuth
   client secrets.
3. **Audit Coolify's activity log** for deploys, service edits, or token use
   between 2026-08-29 and today that you do not recognise.
4. **Audit Supabase logs** for service-role access from unfamiliar IPs over the
   same window.
5. **Scrub git history** (`git filter-repo`) and force-push, then have every
   collaborator re-clone. Note this only removes it from the canonical repo —
   any clone or fork taken since 2026-08-29 still contains it, which is why
   rotation (step 1) is what actually protects you.

## What this audit already did

Removed the token from all three tracked files in the working tree and replaced
it with a `${COOLIFY_API_TOKEN}` reference, so the script still works when the
variable is set and fails loudly when it is not:

```bash
curl -X POST https://coolify.getbijou.xyz/api/v1/services/<uuid>/start \
  -H "Authorization: Bearer ${COOLIFY_API_TOKEN:?set COOLIFY_API_TOKEN}"
```

**This does not rotate anything and does not remove it from history.** The token
remains live and remains in every pushed commit above until an owner does steps
1 and 5.

## Also on disk, not in git

`ops/_fix_rls_v6.js` and nine sibling scripts under `ops/` contain a live
Supabase **Management API** personal access token in plaintext. Those files are
gitignored and untracked — verified — so this is a local-disk exposure, not a
repository leak, and it is a lower severity than the above. It still warrants
rotation, and those scripts are the ones that *drop RLS policies on the
production database*, so they are worth moving out of the working tree entirely.

`ops/.fly_token` and `ops/.vercel_token` are likewise untracked but plaintext.

## Why the existing controls did not catch this

There is a pre-commit secret guard, and it works — it fired on JWT-shaped
strings during this very audit. It did not fire here because it does not match
the Coolify/Sanctum `1|…` token format.

Concretely: add `1\|[A-Za-z0-9]{40,}` to the guard's patterns, and add a CI
secret-scan (gitleaks or trufflehog) that runs on history rather than only on
the staged diff. The 2026-08-24 post-mortem already queued "a git-secrets or
gitleaks pre-commit hook + a CI step" as a follow-up; it was not done, and the
same class of incident recurred five days later.
