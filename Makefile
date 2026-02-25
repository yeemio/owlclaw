.PHONY: help dev-up dev-down dev-reset test-up test-down test test-unit test-int lint typecheck

## Show available commands
help:
	@echo "OwlClaw development commands:"
	@echo "  dev-up       Start full local stack (docker-compose.dev.yml)"
	@echo "  dev-down     Stop full local stack"
	@echo "  dev-reset    Stop full stack and remove volumes"
	@echo "  test-up      Start test database stack (docker-compose.test.yml)"
	@echo "  test-down    Stop test database stack"
	@echo "  test         Run unit + integration tests"
	@echo "  test-unit    Run unit tests only"
	@echo "  test-int     Run integration tests only"
	@echo "  lint         Run Ruff checks"
	@echo "  typecheck    Run MyPy checks"
	@echo ""
	@echo "Windows: use PowerShell scripts under scripts/ when make is unavailable."

## Start full local stack
dev-up:
	docker compose -f docker-compose.dev.yml up -d

## Stop full local stack
dev-down:
	docker compose -f docker-compose.dev.yml down

## Reset full local stack and volumes
dev-reset:
	docker compose -f docker-compose.dev.yml down -v

## Start test stack
test-up:
	docker compose -f docker-compose.test.yml up -d

## Stop test stack
test-down:
	docker compose -f docker-compose.test.yml down

## Run unit and integration tests
test:
	poetry run pytest tests/unit/ tests/integration/ -q

## Run unit tests
test-unit:
	poetry run pytest tests/unit/ -q

## Run integration tests
test-int:
	poetry run pytest tests/integration/ -q

## Run lint
lint:
	poetry run ruff check .

## Run static type check
typecheck:
	poetry run mypy owlclaw/
