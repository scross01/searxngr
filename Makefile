.PHONY: build install test test-integration test-live integration-up integration-down clean fmt lint check help

# Default: run the offline test suite
all: test

build: ## Build sdist and wheel into dist/
	uv build

install: ## Install the package into the current venv
	uv sync

test: ## Run the offline test suite (integration tests skip automatically)
	uv run --locked pytest

test-integration: ## Run the live integration suite in docker (builds the image, starts SearXNG, runs tests, stops)
	docker compose --profile integration -f docker/docker-compose.yml build
	docker compose --profile integration -f docker/docker-compose.yml up -d --wait searxng
	docker compose --profile integration -f docker/docker-compose.yml run --rm integration
	docker compose --profile integration -f docker/docker-compose.yml down

test-live: ## Run the live integration suite from the host against a reachable SearXNG
	SEARXNG_URL=$${SEARXNG_URL:-http://127.0.0.1:8080} uv run --locked pytest tests/integration -v

integration-up: ## Start the compose SearXNG server only
	docker compose --profile integration -f docker/docker-compose.yml up -d --wait searxng

integration-down: ## Stop the compose SearXNG server
	docker compose --profile integration -f docker/docker-compose.yml down

clean: ## Remove build artifacts and caches
	uv clean
	rm -rf dist build .pytest_cache tests/__pycache__ tests/integration/__pycache__ searxngr/__pycache__

fmt: ## Format code and docs
	uv run black searxngr/ tests/
	uv run mdformat --wrap 80 *.md docs/*.md

lint: ## Run flake8 (informational: pre-existing findings are not gated)
	-uv run flake8 searxngr/ --max-line-length 120

check: test ## Alias for test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
