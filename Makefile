# Local development shortcuts for OwlClaw.
# Windows note: if GNU make is unavailable, run equivalent PowerShell commands listed in `make help`.

.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
PS_TEST := powershell -ExecutionPolicy Bypass -File scripts/test-local.ps1
else
PS_TEST := ./scripts/test-local.sh
endif

help: ## Show available targets
	@echo "Targets:" && \
	echo "  dev-up       Start full dev stack" && \
	echo "  dev-down     Stop full dev stack" && \
	echo "  dev-reset    Stop and remove dev volumes" && \
	echo "  test-up      Start CI-mirror test DB" && \
	echo "  test-down    Stop CI-mirror test DB" && \
	echo "  test         Start test DB and run unit+integration (non-e2e)" && \
	echo "  test-unit    Run unit tests only (no external service)" && \
	echo "  test-int     Run integration tests (non-e2e)" && \
	echo "  lint         Run Ruff lint" && \
	echo "  typecheck    Run mypy"
	@echo "Windows PowerShell equivalents:" && \
	echo "  scripts\\test-local.ps1 [-UnitOnly] [-KeepUp]" && \
	echo "  docker compose -f docker-compose.dev.yml up -d"

dev-up: ## Start full local dev stack (Postgres + Hatchet + Langfuse + Redis)
	docker compose -f docker-compose.dev.yml up -d

dev-down: ## Stop full local dev stack
	docker compose -f docker-compose.dev.yml down

dev-reset: ## Stop full local dev stack and remove volumes
	docker compose -f docker-compose.dev.yml down -v

test-up: ## Start CI-mirror test database (pgvector pg16)
	docker compose -f docker-compose.test.yml up -d

test-down: ## Stop CI-mirror test database
	docker compose -f docker-compose.test.yml down

test: ## Run local test pipeline with managed test compose
	$(PS_TEST)

test-unit: ## Run unit tests only (no external service required)
	poetry run pytest tests/unit/ -q

test-int: ## Run integration tests excluding e2e
	poetry run pytest tests/integration/ -m "not e2e" -q

lint: ## Run Ruff lint
	poetry run ruff check .

typecheck: ## Run mypy static checks
	poetry run mypy owlclaw/
