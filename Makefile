.PHONY: install test cov lint lint-fix typecheck lock-check check dev clean \
	fe-install fe-dev fe-build fe-preview fe-check fe-test

# Backend
install:
	cd backend && uv sync

test:
	cd backend && uv run pytest -q

# Line + branch coverage of the backend, with the lines missed.
cov:
	cd backend && uv run pytest --cov=thalimage --cov-branch --cov-report=term-missing

lint:
	cd backend && uv run ruff check src/ tests/

lint-fix:
	cd backend && uv run ruff check --fix src/ tests/

typecheck:
	cd backend && uv run mypy src/

# uv.lock matches pyproject.toml.
lock-check:
	cd backend && uv lock --check

# Everything CI checks, backend and (when installed) frontend.
check:
	./check.sh

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

fe-preview:
	cd frontend && pnpm preview

fe-check:
	cd frontend && pnpm check

fe-test:
	cd frontend && pnpm test

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.mypy_cache
