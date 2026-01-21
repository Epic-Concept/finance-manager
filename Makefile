.PHONY: install install-api install-web test test-api test-web lint lint-api lint-web format docker-build docker-build-api docker-build-web run clean help db-up db-down db-migrate db-reset seed-data seed-data-clear

# Default target
help:
	@echo "Finance Manager - Available targets:"
	@echo ""
	@echo "  install          Install all dependencies"
	@echo "  install-api      Install API dependencies"
	@echo "  install-web      Install Web dependencies"
	@echo ""
	@echo "  test             Run all tests"
	@echo "  test-api         Run API tests"
	@echo "  test-web         Run Web tests"
	@echo ""
	@echo "  lint             Run all linters"
	@echo "  lint-api         Run API linters"
	@echo "  lint-web         Run Web linters"
	@echo ""
	@echo "  format           Format all code"
	@echo "  format-api       Format API code"
	@echo "  format-web       Format Web code"
	@echo ""
	@echo "  db-up            Start database container"
	@echo "  db-down          Stop database container"
	@echo "  db-migrate       Run database migrations"
	@echo "  db-reset         Reset database (destroy and recreate)"
	@echo "  seed-data        Load CSV data into database"
	@echo "  seed-data-clear  Clear and reload CSV data"
	@echo ""
	@echo "  docker-build     Build all Docker images"
	@echo "  docker-build-api Build API Docker image"
	@echo "  docker-build-web Build Web Docker image"
	@echo ""
	@echo "  run              Start all services via docker-compose"
	@echo "  clean            Clean build artifacts"

# Install
install: install-api install-web

install-api:
	cd apps/api && pip install -e ".[dev]"

install-web:
	cd apps/web && npm install

# Test
test: test-api test-web

test-api:
	cd apps/api && pytest

test-web:
	cd apps/web && npm test

# Lint
lint: lint-api lint-web

lint-api:
	cd apps/api && ruff check src tests && black --check src tests && mypy src

lint-web:
	cd apps/web && npm run lint

# Format
format: format-api format-web

format-api:
	cd apps/api && ruff check --fix src tests && black src tests

format-web:
	cd apps/web && npm run format

# Database
db-up:
	docker-compose up -d db
	@echo "Waiting for database to be ready..."
	@sleep 10
	@echo "Database is ready at localhost:1433"

db-down:
	docker-compose stop db

db-migrate:
	cd apps/api && alembic upgrade head

db-reset:
	docker-compose down -v db
	docker-compose up -d db
	@echo "Waiting for database to be ready..."
	@sleep 15
	cd apps/api && alembic upgrade head

# Seed data
seed-data:
	cd apps/api && python -m finance_api.scripts.seed_data --data-dir ../../data

seed-data-clear:
	cd apps/api && python -m finance_api.scripts.seed_data --data-dir ../../data --clear

# Docker
docker-build: docker-build-api docker-build-web

docker-build-api:
	docker build -t finance-manager-api:latest apps/api

docker-build-web:
	docker build -t finance-manager-web:latest apps/web

# Run all services
run:
	docker-compose up

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
