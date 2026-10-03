#!/usr/bin/env bash
# The full gate: what CI runs, and what `make check` runs. Each tool
# invocation lives in the Makefile; this only sequences them.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Lint ==="
make -C "$repo_root" --no-print-directory lint

echo "=== Typecheck ==="
make -C "$repo_root" --no-print-directory typecheck

echo "=== Tests ==="
make -C "$repo_root" --no-print-directory test

# The frontend is optional: a backend-only checkout has no node_modules,
# and the backend checks alone are still a valid run.
if [ -d "$repo_root/frontend/node_modules" ]; then
    echo "=== Frontend check ==="
    make -C "$repo_root" --no-print-directory fe-check fe-test
else
    echo "=== Frontend check (skipped: frontend/node_modules absent) ==="
fi

echo "=== All checks passed ==="
