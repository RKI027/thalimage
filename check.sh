#!/usr/bin/env bash
set -euo pipefail

echo "=== Lint ==="
cd backend && uv run ruff check src/ tests/

echo "=== Typecheck ==="
uv run mypy src/

echo "=== Tests ==="
uv run pytest -q

echo "=== All checks passed ==="
