#!/bin/sh
# Fix ownership of the mounted /data volume, then drop privileges.
#
# Build-time `chown /data` is masked by any runtime mount. A fresh empty NAMED
# volume inherits the image's ownership, so this is a no-op there; a BIND MOUNT
# to a host directory arrives owned by whoever owns it on the host (usually
# root), and the bridge then fails to create /data/store or open bridge.db.
# That is the failure the 7aea6ec / a8241c1 / 12e481f commit chain kept chasing.
set -e

DATA_DIR="${DATA_DIR:-/data}"
RUN_UID="${RUN_UID:-1000}"
RUN_GID="${RUN_GID:-0}"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$DATA_DIR/store" "$DATA_DIR/logs"
    # Only chown when it is actually wrong — recursive chown on a large
    # session store is slow, and on every restart it would be pure waste.
    current_uid="$(stat -c '%u' "$DATA_DIR" 2>/dev/null || echo unknown)"
    if [ "$current_uid" != "$RUN_UID" ]; then
        echo "[entrypoint] $DATA_DIR owned by uid=$current_uid, chowning to $RUN_UID:$RUN_GID"
        chown -R "$RUN_UID:$RUN_GID" "$DATA_DIR"
    fi
    exec su-exec "$RUN_UID:$RUN_GID" /app/bridge "$@"
fi

# Already unprivileged (e.g. the platform pinned a user). Verify we can write
# and fail loudly rather than crashing later with an opaque sqlite error.
if [ ! -w "$DATA_DIR" ]; then
    echo "[entrypoint] FATAL: $DATA_DIR is not writable by uid=$(id -u)." >&2
    echo "[entrypoint] Mount it with the right ownership or start the container as root" >&2
    echo "[entrypoint] so this script can chown it. See ops/DOKPLOY_DEPLOY.md." >&2
    exit 1
fi

exec /app/bridge "$@"
