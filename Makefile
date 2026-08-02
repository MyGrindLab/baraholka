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

## --- to define once infrastructure/ is scaffolded -------------------------------
# COMPOSE       := <compose invocation against the file(s) in infrastructure/>
# RUN           := <one-shot wrapper, e.g. $(COMPOSE) run --rm>
# FRONTEND_TEST := <frontend test command, run in its container>
# FRONTEND_LINT := <frontend lint command>
# FRONTEND_FMT  := <frontend format command>
# BACKEND_TEST  := <backend test command, run in its container>
# BACKEND_LINT  := <backend lint command>
# BACKEND_FMT   := <backend format command>

.DEFAULT_GOAL := help
.PHONY: help up up-frontend up-backend down restart ps logs build rebuild \
        sh-frontend sh-backend test test-frontend test-backend e2e \
        lint lint-frontend lint-backend fmt check migrate clean

help: ## Show available targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

## --- run ---------------------------------------------------------------

up: ## Start the full stack (detached)
	$(TODO)

up-frontend: ## Start only the frontend and what it depends on
	$(TODO)

up-backend: ## Start only the backend and what it depends on
	$(TODO)

down: ## Stop the stack, keep volumes
	$(TODO)

restart: down up ## Restart the full stack

ps: ## Show container status
	$(TODO)

logs: ## Tail logs from all services (make logs S=<service> for one)
	$(TODO)

## --- build -------------------------------------------------------------

build: ## Build all images
	$(TODO)

rebuild: ## Rebuild all images from scratch
	$(TODO)

sh-frontend: ## Shell into the frontend container
	$(TODO)

sh-backend: ## Shell into the backend container
	$(TODO)

## --- verify ------------------------------------------------------------

test: test-frontend test-backend ## Run every test suite

test-frontend: ## Run frontend tests in its container
	$(TODO)

test-backend: ## Run backend tests in its container
	$(TODO)

e2e: ## Bring the stack up for browser E2E (driven via the Playwright MCP)
	$(TODO)

lint: lint-frontend lint-backend ## Lint every component

lint-frontend:
	$(TODO)

lint-backend:
	$(TODO)

fmt: ## Format all code in place
	$(TODO)

check: lint test ## Full pre-PR gate — must be green before a PR is opened

## --- data --------------------------------------------------------------

migrate: ## Apply database migrations
	$(TODO)

clean: ## Stop everything and delete volumes (destroys local data)
	$(TODO)
