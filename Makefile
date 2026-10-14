# Root Makefile — the one entry point for the project.
#
# This file declares the *interface* the whole project is driven through. The
# target names are the agreed structure. Targets that are not implemented yet
# fail loudly with a pointer rather than pretending to work.
#
# Contract for whoever fills it in — `devops` owns this file:
#   - Every target executes inside a container. No host toolchain, ever.
#   - Keep the target names below: the agents, the skills, and CI depend on them.
#   - `make check` must be exactly the gate CI runs.
#   - Each component stays independently runnable (`up-frontend`, `up-backend`).
#   - Add targets for new components the same way; don't work around this file.
#
# To fill in a remaining placeholder: replace its $(TODO) / `exit 1` with the
# real command.

TODO = @echo "Makefile: target '$@' is not filled in yet — see the header." && exit 1

## --- component wiring ---------------------------------------------------
BACKEND_ENV     := --env-file infrastructure/backend/.env
COMPOSE_BACKEND := docker compose -p baraholka-backend $(BACKEND_ENV) -f infrastructure/backend/docker-compose.yml
COMPOSE_INFRA   := docker compose -p baraholka-infra $(BACKEND_ENV) -f infrastructure/backend/docker-compose-infra.yml
BACKEND_IMAGE   := baraholkabackend:local
BACKEND_TEST_IMAGE := baraholkabackend:test
BACKEND_RUN     := $(COMPOSE_BACKEND) run --rm baraholka-app
# Hermetic runner for tests/lint/fmt: the Dockerfile `test` stage (dev extras),
# backend/src bind-mounted for live edits. No env file, no network, no secrets.
BACKEND_TEST_RUN := docker run --rm --network none -v "$(CURDIR)/backend/src:/app/src" $(BACKEND_TEST_IMAGE)
BACKEND_TEST    := uv run pytest
BACKEND_LINT    := uv run ruff check src/ && uv run mypy src/
BACKEND_FMT     := uv run ruff format src/

COMPOSE_FRONTEND   := docker compose -p baraholka-frontend -f infrastructure/frontend/docker-compose.yml
FRONTEND_DEV_IMAGE := baraholkafrontend:dev
FRONTEND_IMAGE     := baraholkafrontend:local
# Hermetic runner for frontend lint/tests: the Dockerfile `dev` stage,
# frontend/src bind-mounted for live edits. No network.
FRONTEND_TEST_RUN  := docker run --rm --network none -v "$(CURDIR)/frontend/src:/app/src" $(FRONTEND_DEV_IMAGE)

NETWORK_CREATE  := docker network inspect baraholka-network >/dev/null 2>&1 || docker network create baraholka-network

.DEFAULT_GOAL := help
.PHONY: help up up-frontend up-backend up-infra down down-infra restart ps logs build rebuild \
        build-test build-backend build-frontend-dev lock-frontend sh-frontend sh-backend \
        test test-frontend test-backend e2e lint lint-frontend lint-backend fmt check migrate clean

help: ## Show available targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

## --- run ---------------------------------------------------------------

up: ## Start the full stack (detached)
	$(MAKE) up-infra
	$(MAKE) up-backend
	$(MAKE) up-frontend

up-frontend: ## Start the frontend dev server (Vite, hot reload; FRONTEND_PORT, default 3000)
	$(NETWORK_CREATE)
	$(MAKE) build-frontend-dev
	$(COMPOSE_FRONTEND) up --detach

up-infra: ## Start MongoDB + mongo-express
	$(NETWORK_CREATE)
	$(COMPOSE_INFRA) up --detach

down-infra: ## Stop MongoDB + mongo-express
	$(COMPOSE_INFRA) down

up-backend: ## Start only the backend and what it depends on
	$(NETWORK_CREATE)
	$(MAKE) build-backend
	$(COMPOSE_BACKEND) up --detach

down: ## Stop the stack, keep volumes
	$(COMPOSE_FRONTEND) down
	$(COMPOSE_BACKEND) down

restart: down up ## Restart the full stack

ps: ## Show container status
	$(COMPOSE_FRONTEND) ps
	$(COMPOSE_BACKEND) ps
	$(COMPOSE_INFRA) ps

# S=baraholka-frontend* routes to the frontend project; anything else to the backend.
logs: ## Tail backend + frontend logs (make logs S=<service> for one)
ifeq ($(S),)
	$(COMPOSE_BACKEND) logs -f & $(COMPOSE_FRONTEND) logs -f; wait
else
	$(if $(filter baraholka-frontend%,$(S)),$(COMPOSE_FRONTEND),$(COMPOSE_BACKEND)) logs -f $(S)
endif

## --- build -------------------------------------------------------------

build: build-backend ## Build all images (backend + production frontend)
	docker build --tag $(FRONTEND_IMAGE) -f infrastructure/frontend/Dockerfile frontend

build-backend: ## Build the backend runtime image
	docker build --tag $(BACKEND_IMAGE) -f infrastructure/backend/Dockerfile .

build-test: ## Build the backend test image (runtime deps + dev extras)
	docker build --target test --tag $(BACKEND_TEST_IMAGE) -f infrastructure/backend/Dockerfile .

build-frontend-dev: ## Build the frontend dev image (Vite + dev deps)
	docker build --target dev --tag $(FRONTEND_DEV_IMAGE) -f infrastructure/frontend/Dockerfile frontend

lock-frontend: ## Update frontend/package-lock.json in a container (add packages: P="-D pkg@ver")
	docker run --rm --user $$(id -u):$$(id -g) -e npm_config_cache=/tmp/.npm \
	  -v "$(CURDIR)/frontend:/app" -w /app node:24-alpine npm install --package-lock-only $(P)

rebuild: ## Rebuild all images from scratch
	docker build --no-cache --tag $(BACKEND_IMAGE) -f infrastructure/backend/Dockerfile .
	docker build --no-cache --tag $(FRONTEND_IMAGE) -f infrastructure/frontend/Dockerfile frontend

sh-frontend: build-frontend-dev ## Shell into the frontend container
	$(COMPOSE_FRONTEND) run --rm baraholka-frontend sh

sh-backend: ## Shell into the backend container
	$(BACKEND_RUN) bash

## --- verify ------------------------------------------------------------

test: test-frontend test-backend ## Run every test suite

test-frontend: build-frontend-dev ## Run frontend tests in a container (extra args: A="...")
	$(FRONTEND_TEST_RUN) npm test$(if $(A), -- $(A))

test-backend: build-test ## Run backend tests in a container (extra pytest args: A="...")
	$(BACKEND_TEST_RUN) $(BACKEND_TEST) $(A)

e2e: ## Bring the stack up for browser E2E (driven via the Playwright MCP)
	$(MAKE) up
	docker run --rm --network baraholka-network curlimages/curl:8.10.1 -fsS --retry 30 --retry-all-errors \
	  --retry-delay 2 -o /dev/null http://baraholka-frontend:3000/api/health \
	  && echo "E2E ready: http://localhost:$${FRONTEND_PORT:-3000}"

lint: lint-frontend lint-backend ## Lint every component

lint-frontend: build-frontend-dev ## Lint the frontend (ESLint)
	$(FRONTEND_TEST_RUN) npm run lint $(A)

lint-backend: build-test ## Lint + typecheck the backend (ruff, mypy)
	$(BACKEND_TEST_RUN) sh -c '$(BACKEND_LINT)'

fmt: build-test ## Format all code in place
	$(BACKEND_TEST_RUN) $(BACKEND_FMT)

check: lint test ## Full pre-PR gate — must be green before a PR is opened

## --- data --------------------------------------------------------------

migrate: ## Apply database migrations
	@echo "migrate: no migrations yet — Mongo index creation is tracked in KAN-63" && exit 1

clean: ## Stop everything and delete volumes (destroys local data)
	$(COMPOSE_FRONTEND) down -v
	$(COMPOSE_BACKEND) down -v
	$(COMPOSE_INFRA) down -v
