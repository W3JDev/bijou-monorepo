#!/bin/bash
# Apply the repo's own migrations after the Supabase base schema is in place.
#
# Mounted as a FILE into /docker-entrypoint-initdb.d/ with a zz- prefix so it
# runs after the supabase/postgres image's own migrate.sh. The migrations
# themselves live at /bijou-migrations — a path OUTSIDE initdb.d, because the
# postgres entrypoint ignores directories under initdb.d entirely ("ignoring
# /docker-entrypoint-initdb.d/<dir>") and would never have run them.
#
# Best-effort by design: several files in migrations-py reference core tables
# that no migration in this repo creates (79 queried, 13 created — see
# ops/LOCAL_DEV.md § The missing baseline schema), so some WILL fail until a
# baseline exists. A failure here must not abort database init, or the whole
# stack fails to come up over a known-missing baseline. Each failure is
# reported so it is visible rather than silent.
set -u

MIG_DIR=/bijou-migrations
[ -d "$MIG_DIR" ] || { echo "[bijou] no $MIG_DIR mounted, skipping"; exit 0; }

applied=0
failed=0
for f in $(ls -1 "$MIG_DIR"/*.sql 2>/dev/null | sort); do
    name=$(basename "$f")
    # ALL_MIGRATIONS_RUN_THIS.sql is a concatenation of the others; running it
    # too would double-apply everything.
    case "$name" in ALL_MIGRATIONS_RUN_THIS.sql) echo "[bijou] skip $name (aggregate)"; continue;; esac

    if psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${POSTGRES_DB:-postgres}" -f "$f" >/dev/null 2>&1; then
        echo "[bijou] applied $name"
        applied=$((applied+1))
    else
        echo "[bijou] FAILED  $name (expected while the baseline schema is missing)"
        failed=$((failed+1))
    fi
done

echo "[bijou] migrations: $applied applied, $failed failed"
exit 0
