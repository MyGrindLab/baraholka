# Root Makefile — TEMPLATE, not yet functional.
#
# This file declares the *interface* the whole project is driven through. The
# target names are the agreed structure; the bodies are placeholders to be
# filled in once the components and infrastructure/ exist. Until then every target fails
# with a pointer rather than pretending to work.
#
# Contract for whoever fills it in — `devops` owns this file:
#   - Every target executes inside a container. No host toolchain, ever.
#   - Keep the target names below: the agents, the skills, and CI depend on them.
#   - `make check` must be exactly the gate CI runs.
#   - Each component stays independently runnable (`up-frontend`, `up-backend`).
#   - Add targets for new components the same way; don't work around this file.
#
# To fill in: define the variables below, then replace each $(TODO) with the
# real command.

TODO = @echo "Makefile: target '$@' is not filled in yet — see the header." && exit 1

## --- component wiring ---------------------------------------------------
BACKEND_ENV     := --env-file infrastructure/backend/.env
COMPOSE_BACKEND := docker compose -p baraholka-backend $(BACKEND_ENV) -f infrastructure/backend/docker-compose.yml
COMPOSE_INFRA   := docker compose -p baraholka-infra $(BACKEND_ENV) -f infrastructure/backend/docker-compose-infra.yml
BACKEND_IMAGE   := baraholkabackend:local
BACKEND_RUN     := $(COMPOSE_BACKEND) run --rm baraholka-app
BACKEND_TEST    := uv run pytest
BACKEND_LINT    := uv run ruff check src/ && uv run mypy src/
BACKEND_FMT     := uv run ruff format src/

.DEFAULT_GOAL := help
.PHONY: help up up-frontend up-backend up-infra down down-infra restart ps logs build rebuild \
        sh-frontend sh-backend test test-frontend test-backend e2e \
        lint lint-frontend lint-backend fmt check migrate clean

help: ## Show available targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

## --- run ---------------------------------------------------------------

up: ## Start the full stack (detached)
	$(MAKE) up-infra
	$(MAKE) up-backend

up-frontend: ## Start only the frontend and what it depends on
	$(TODO)  # no frontend image yet — devops to add infrastructure/frontend/

up-infra: ## Start MongoDB + mongo-express
	docker network inspect baraholka-network >/dev/null 2>&1 || docker network create baraholka-network
	$(COMPOSE_INFRA) up --detach

down-infra: ## Stop MongoDB + mongo-express
	$(COMPOSE_INFRA) down

up-backend: ## Start only the backend and what it depends on
	$(MAKE) build
	$(COMPOSE_BACKEND) up --detach

down: ## Stop the stack, keep volumes
	$(COMPOSE_BACKEND) down

restart: down up ## Restart the full stack

ps: ## Show container status
	$(COMPOSE_BACKEND) ps
	$(COMPOSE_INFRA) ps

logs: ## Tail logs from all services (make logs S=<service> for one)
	$(COMPOSE_BACKEND) logs -f $(S)

## --- build -------------------------------------------------------------

build: ## Build all images
	docker build --tag $(BACKEND_IMAGE) -f infrastructure/backend/Dockerfile .

rebuild: ## Rebuild all images from scratch
	docker build --no-cache --tag $(BACKEND_IMAGE) -f infrastructure/backend/Dockerfile .

sh-frontend: ## Shell into the frontend container
	$(TODO)

sh-backend: ## Shell into the backend container
	$(BACKEND_RUN) bash

## --- verify ------------------------------------------------------------

test: test-frontend test-backend ## Run every test suite

test-frontend: ## Run frontend tests in its container
	$(TODO)

test-backend: ## Run backend tests in its container
	$(BACKEND_RUN) $(BACKEND_TEST)

e2e: ## Bring the stack up for browser E2E (driven via the Playwright MCP)
	$(TODO)

lint: lint-frontend lint-backend ## Lint every component

lint-frontend:
	$(TODO)

lint-backend:
	$(BACKEND_RUN) sh -c '$(BACKEND_LINT)'

fmt: ## Format all code in place
	$(BACKEND_RUN) $(BACKEND_FMT)

check: lint test ## Full pre-PR gate — must be green before a PR is opened

## --- data --------------------------------------------------------------

migrate: ## Apply database migrations
	$(TODO)

clean: ## Stop everything and delete volumes (destroys local data)
	$(COMPOSE_BACKEND) down -v
	$(COMPOSE_INFRA) down -v
