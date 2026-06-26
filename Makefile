.PHONY: install test lint typecheck check dev clean

# Backend
install:
	cd backend && uv sync

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check src/ tests/

lint-fix:
	cd backend && uv run ruff check --fix src/ tests/

typecheck:
	cd backend && uv run mypy src/

check: lint typecheck test

# Development
dev:
	cd backend && uv run thalimage

# Frontend
fe-install:
	cd frontend && pnpm install

fe-dev:
	cd frontend && pnpm dev

fe-build:
	cd frontend && pnpm build

fe-lint:
	cd frontend && pnpm lint

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.mypy_cache
