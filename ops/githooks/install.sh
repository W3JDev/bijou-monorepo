#!/usr/bin/env bash
# Point git at the tracked hooks in this directory.
#
# The old guard lived in .git/hooks/, which git never tracks, so it existed
# only on the machine of whoever wrote it. Two credentials have now been
# committed to this repo (2026-08-10, 2026-08-29). A guard that ships with the
# clone is the difference.
#
#     ./ops/githooks/install.sh
#
# Undo with:  git config --unset core.hooksPath
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

chmod +x ops/githooks/pre-commit ops/githooks/test-secret-guard.sh
git config core.hooksPath ops/githooks

echo "core.hooksPath -> $(git config core.hooksPath)"
echo "Verifying the guard still works before trusting it..."
./ops/githooks/test-secret-guard.sh >/dev/null && echo "secret guard self-test: PASS"
echo
echo "Installed. Note this is a last line of defence, not the only one —"
echo ".github/workflows/secret-scan.yml scans full history in CI."
