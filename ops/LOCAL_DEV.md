# Local development — the whole system on one machine

Before this existed the only compose file in the repo was
`docker-compose.coolify.yml`, which needs a live cloud Supabase project and a
real Gemini key just to start. There was no way to run Bijou locally.

```bash
./ops/local/up.sh
```

That is the command. It mints local keys on first run, then brings up the
stack. Add `-d` to detach, `--profile full` to include voice and PostHog.

> **Signup, email confirmation and login all work locally** as of 2026-09-06,
> using a generated dev scaffold schema (`ops/local/devschema/`). That scaffold
> is **not** your production schema — column types are inferred from column
> names. Read [§ The missing baseline schema](#the-missing-baseline-schema);
> replacing it with a real dump is still the #1 backlog item.

---

## What comes up

| Service | Host URL | What it is |
|---|---|---|
| `backend` | http://localhost:8080 | FastAPI, `packages/backend`. The real product UI is the hand-written HTML in `static/`, not `packages/landing`. |
| `landing` | http://localhost:3001 | Marketing site, `packages/landing`, built and served by nginx. |
| `bridge` | http://localhost:8081 | Go WhatsApp bridge, `packages/bridge`. |
| `supabase-gateway` | http://localhost:54321 | nginx joining GoTrue + PostgREST under one origin. |
| `supabase-db` | `localhost:54322` | Postgres 15 (`supabase/postgres`). User `postgres`, password `postgres`. |
| `mailpit` | http://localhost:8025 | Catches every confirmation email GoTrue sends. |
| `voice` | http://localhost:8100 | Telnyx concierge. `--profile voice`. |
| `posthog` | http://localhost:8000 | Analytics. `--profile analytics`. Slow to start (~90s). |

Ports are deliberately odd. `5432`, `6379` and `3000` are usually already
taken on a working dev machine, so the stack sits at `54322`, its own Redis,
and `3001`.

## Why there is a Supabase gateway

The cloud Supabase project serves GoTrue at `/auth/v1` and PostgREST at
`/rest/v1` from a single origin, and `supabase-py` builds its URLs on that
assumption. Running the two containers separately would mean every call site
needed a local-only special case. The nginx gateway
(`ops/local/supabase-gateway.conf`) reproduces the cloud shape, so
`SUPABASE_URL` is the only thing that differs between local and production.

## Keys

`ops/local/gen-local-keys.sh` mints an `anon` and a `service_role` JWT signed
with the local JWT secret and writes `ops/local/.env.local` (gitignored,
mode 600). `up.sh` runs it automatically when the file is absent.

They are real HS256 tokens, not dummy strings, because PostgREST verifies the
signature against `PGRST_JWT_SECRET` and rejects anything else. They are not
committed because a JWT-shaped literal in the diff trips the repo's
pre-commit secret guard — correctly.

### `up.sh` passes `--env-file` on purpose

`docker compose` auto-loads `.env` from the project directory. The root `.env`
here holds **live production credentials**. Running plain
`docker compose -f docker-compose.local.yml up` interpolates them into the
local stack — verified: the real 39-character production `GEMINI_API_KEY` was
being injected. Local-only variables are `LOCAL_`-prefixed for the same
reason.

The sharper version of this hazard: running
`docker compose -f docker-compose.coolify.yml up` on a dev machine points
local containers at the **production Supabase project with the production
service-role key**, and writes land in production. Don't.

### WSL without Docker Desktop integration

`up.sh` calls `docker compose`, which is right on Linux and macOS. In a WSL
distro where Docker Desktop's WSL integration is off there is no `docker` on
PATH at all:

```
$ docker ps
The command 'docker' could not be found in this WSL 2 distro.
```

Either turn on WSL integration in Docker Desktop → Settings → Resources → WSL
Integration (the clean fix), or drive the Windows binary directly:

```bash
DOCKER="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"
"$DOCKER" compose --env-file ops/local/.env.local -f docker-compose.local.yml up -d
```

Two things bite when using `docker.exe` from WSL:

- **Run it from the repo root.** Paths in `--env-file` and `-f` are resolved by
  a Windows process, so a relative path is interpreted against whatever
  directory the shell is in. Running from `packages/backend` fails with
  `couldn't find env file: C:\...\packages\backend\ops\local\.env.local`.
- **Volume mounts need Windows paths.** `-v "$(pwd)/x:/y"` hands it `/mnt/c/...`,
  which it cannot resolve; use `-v 'C:\Users\...\x:/y'`.

## Daily use

```bash
./ops/local/up.sh -d                       # start detached
docker compose -f docker-compose.local.yml logs -f backend
docker compose -f docker-compose.local.yml restart backend
docker compose -f docker-compose.local.yml down            # stop, keep data
docker compose -f docker-compose.local.yml down -v         # stop, wipe data
```

`down -v` is how you re-run the DB init scripts — they only execute on an
empty volume.

### Backend without Docker

Faster for iterating on Python. Note the venv here is a **Windows** venv, so
from WSL it is `.venv/Scripts/python.exe`, not `.venv/bin/python`:

```bash
cd packages/backend
./.venv/Scripts/python.exe -m uvicorn src.core.bijou:app --host 0.0.0.0 --port 8080
```

Bind `0.0.0.0`, not `127.0.0.1`. WSL and Windows have separate loopbacks, so a
Windows process bound to `127.0.0.1` is unreachable from WSL. Reach it at the
WSL default gateway: `ip route show default | awk '{print $3}'`.

### Tests

```bash
cd packages/backend
./.venv/Scripts/python.exe -m pytest tests/ -q --tb=short -p no:cacheprovider -s
```

**The `-s` is not optional.** Without it the run dies during capture teardown
with `ValueError: I/O operation on closed file` after collecting only part of
the suite — which looks like a small green run and is neither.

Baseline as of 2026-09-05: **182 failed, 521 passed, 28 skipped, 15 errors**
out of 731 collected. CI does not run pytest at all (see `CLAUDE.md`), so
that number had gone unnoticed. Do not treat a green CI badge as evidence.

---

## The missing baseline schema

The single biggest gap in the repo, and the reason this stack cannot yet
complete a signup.

```
tables the application code queries : 79
tables any .sql file in the repo creates : 13
```

`tenants`, `tenant_users`, `messages`, `conversations`, `contacts`, `leads`,
`subscription_plans` and 61 others are created by **no migration in this
repository**. They exist only as live state inside the cloud Supabase project
`lrwzlujomukzjykafmic`.

Reproduce:

```bash
grep -rhoE '\.table\(\s*["'"'"'][a-z_]+["'"'"']' packages/backend/src \
  | grep -oE '["'"'"'][a-z_]+' | tr -d "\"'" | sort -u > /tmp/code_tables.txt
grep -hoiE "CREATE TABLE (IF NOT EXISTS )?[a-z_.\"]+" \
  packages/backend/migrations-py/*.sql packages/backend/supabase/migrations/*.sql \
  | sed 's/.*EXISTS //I;s/CREATE TABLE //I' | tr -d '"' | sed 's/^public\.//' \
  | sort -u > /tmp/sql_tables.txt
comm -23 /tmp/code_tables.txt /tmp/sql_tables.txt | wc -l   # -> 68
```

What this costs, beyond local dev:

- **No disaster recovery.** If that project is lost or corrupted, the schema
  cannot be rebuilt from source.
- **No staging.** A second environment cannot be provisioned.
- **No schema review.** Changes to the core tables never appear in a diff.

The fix is to dump the live schema and commit it as
`migrations-py/0000_baseline.sql`. It needs someone with read access to the
project (this audit did not have it — the MCP call returned
`You do not have permission to perform this action`, so the live schema was
never inspected and the 68-table figure is code-vs-file only):

```bash
supabase db dump --db-url "$SUPABASE_DB_URL" --schema public -f \
  packages/backend/migrations-py/0000_baseline.sql
```

Until that lands, the local Postgres has the 13 tables the repo does define,
plus roles and extensions from `ops/local/initdb/00-roles.sql`. Enough to boot
and to exercise routes that do not touch the missing tables; not enough for
signup, onboarding, or the inbound-message path.

## Walking the signup flow

With the stack up:

```bash
D="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"   # or just: docker
EMAIL="founder$(date +%s)@bijoudemo.com"

# 1. Sign up. Returns 200 with access_token=null and
#    email_confirmation_required=true — that is CORRECT, not a failure.
#    Production runs mailer_autoconfirm=false and local matches.
$D exec bijou-local-backend curl -s -X POST http://127.0.0.1:8080/api/auth/signup \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"TestPassw0rd!23\",\"business_name\":\"Kedai Kopi Ahmad\",\"phone\":\"+60123456789\",\"plan\":\"free\",\"vertical\":\"fnb\"}"

# 2. The confirmation email is in Mailpit: http://localhost:8025
#    Click the link, or follow it with curl. It 303s and sets
#    email_confirmed_at.

# 3. Log in. Now returns a real access_token and your tenant_id.
$D exec bijou-local-backend curl -s -X POST http://127.0.0.1:8080/api/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"TestPassw0rd!23\"}"
```

Two email addresses that will NOT work: anything at a reserved TLD
(`.test`, `.local`, `.example`, `.invalid`). Pydantic's `EmailStr` rejects them
with a 422 before the handler ever runs. Use a normal-looking domain.

## Troubleshooting

**`bind: address already in use`** — something already holds the port. This is
why the stack avoids 5432/6379/3000; if it still collides, edit the left-hand
side of the `ports:` mapping.

**Bridge exits with a permission error on `/data`** — `ops/local/bridge-entrypoint.sh`
chowns the volume at runtime, which is the fix for the bind-mount case that a
build-time `chown` cannot cover. If it still fails, the platform pinned a
non-root user and the entrypoint could not chown; the log says so explicitly.

**Backend healthy but every request 500s** — almost certainly the missing
baseline schema above, not a code fault.

**Confirmation email never arrives** — it did; it went to Mailpit.
http://localhost:8025. Production runs `mailer_autoconfirm=false` and local
matches deliberately, so a successful signup returns `session=None`. Per
`CLAUDE.md` that is *not* the "email already exists" case — the discriminator
is `user.identities == []`.
