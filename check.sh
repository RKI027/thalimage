#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Lint ==="
cd "$repo_root/backend" && uv run ruff check src/ tests/

echo "=== Typecheck ==="
uv run mypy src/

echo "=== Tests ==="
uv run pytest -q

# The frontend is optional: a backend-only checkout has no node_modules,
# and the backend checks alone are still a valid run.
if [ -d "$repo_root/frontend/node_modules" ]; then
    echo "=== Frontend check ==="
    make -C "$repo_root" fe-check fe-test
else
    echo "=== Frontend check (skipped: frontend/node_modules absent) ==="
fi

echo "=== All checks passed ==="
