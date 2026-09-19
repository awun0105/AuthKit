SHELL := /bin/sh

UV ?= uv
PNPM ?= pnpm
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000
AUTHKIT_API_URL ?= http://localhost:$(BACKEND_PORT)/auth
UI_DIR ?= .
PORT ?=

FULLSTACK_FILTER := --filter authkit-fullstack-nextjs-example
FRONTEND_PACKAGES := --filter @authkit/client --filter @authkit/react --filter @authkit/nextjs

.DEFAULT_GOAL := help

.PHONY: help setup install backend frontend dev frontend-build build \
	test test-backend test-frontend e2e e2e-chrome e2e-install lint typecheck \
	check ui-init free-port

help: ## Show the available developer commands
	@printf '%s\n' \
	  'AuthKit development commands:' \
	  '  make setup          Install Python and pnpm dependencies' \
	  '  make backend        Run the full-stack FastAPI example on port $(BACKEND_PORT)' \
	  '  make frontend       Run the Next.js example on port $(FRONTEND_PORT)' \
	  '  make dev            Run backend and frontend together' \
	  '  make build          Build Python, packages, and the example' \
	  '  make test           Run backend and frontend tests' \
	  '  make check          Run lint, type checks, and tests' \
	  '  make e2e            Run Playwright end-to-end tests' \
	  '  make e2e-chrome     Run E2E tests with installed Chrome' \
	  '  make e2e-install    Install the Playwright Chromium browser' \
	  '  make free-port PORT=8000  Stop the process listening on a TCP port' \
	  '  make ui-init        Scaffold AuthKit UI into UI_DIR (default: .)'

setup: ## Install all Python and JavaScript dependencies
	$(UV) sync --extra dev
	$(PNPM) install

install: setup ## Alias for setup

free-port: ## Stop the process listening on PORT, for example PORT=8000
	@test -n "$(PORT)" || { echo 'Usage: make free-port PORT=8000'; exit 2; }
	@command -v fuser >/dev/null 2>&1 || { echo 'fuser is required to release a port (install psmisc/util-linux)'; exit 2; }
	@pids="$$(fuser -n tcp "$(PORT)" 2>/dev/null || true)"; \
	if [ -n "$$pids" ]; then \
		echo "Stopping process(es) on TCP port $(PORT): $$pids"; \
		kill $$pids 2>/dev/null || true; \
		i=0; \
		while [ "$$i" -lt 10 ] && [ -n "$$(fuser -n tcp "$(PORT)" 2>/dev/null || true)" ]; do \
			sleep 0.2; i=$$((i + 1)); \
		done; \
		pids="$$(fuser -n tcp "$(PORT)" 2>/dev/null || true)"; \
		if [ -n "$$pids" ]; then \
			echo "Process still owns TCP port $(PORT); sending KILL: $$pids"; \
			kill -KILL $$pids 2>/dev/null || { echo "Cannot stop TCP port $(PORT); try sudo make free-port PORT=$(PORT)"; exit 1; }; \
		fi; \
	fi
	@if command -v ss >/dev/null 2>&1 && ss -H -ltn "sport = :$(PORT)" 2>/dev/null | grep -q .; then \
		echo "TCP port $(PORT) is still occupied and its process is not visible to this user."; \
		echo "Run: sudo fuser -k -TERM $(PORT)/tcp"; \
		echo "Or choose another port, for example: make dev BACKEND_PORT=8010 FRONTEND_PORT=3010"; \
		exit 1; \
	fi

backend: ## Run the FastAPI full-stack example
	$(MAKE) free-port PORT=$(BACKEND_PORT)
	$(UV) run --extra dev uvicorn main:app --app-dir examples/fullstack-nextjs/backend --reload --port $(BACKEND_PORT)

frontend-build: ## Build frontend runtime packages used by the example
	$(PNPM) $(FRONTEND_PACKAGES) build

frontend: frontend-build ## Run the Next.js full-stack example
	$(MAKE) free-port PORT=$(FRONTEND_PORT)
	NEXT_PUBLIC_AUTHKIT_API_URL=$(AUTHKIT_API_URL) \
	$(PNPM) $(FULLSTACK_FILTER) dev --port $(FRONTEND_PORT)

dev: frontend-build ## Run the FastAPI and Next.js examples together
	$(MAKE) free-port PORT=$(BACKEND_PORT)
	$(MAKE) free-port PORT=$(FRONTEND_PORT)
	@set -e; \
	cleanup() { \
		if [ -n "$$backend_pid" ]; then kill "$$backend_pid" 2>/dev/null || true; fi; \
		if [ -n "$$frontend_pid" ]; then kill "$$frontend_pid" 2>/dev/null || true; fi; \
	}; \
	trap cleanup INT TERM EXIT; \
	$(UV) run --extra dev uvicorn main:app --app-dir examples/fullstack-nextjs/backend --port $(BACKEND_PORT) & backend_pid=$$!; \
	NEXT_PUBLIC_AUTHKIT_API_URL=$(AUTHKIT_API_URL) \
	$(PNPM) $(FULLSTACK_FILTER) dev --port $(FRONTEND_PORT) & frontend_pid=$$!; \
	wait

build: ## Build the Python distribution, frontend packages, and example
	$(UV) build
	$(PNPM) build
	$(PNPM) build:example

test-backend: ## Run the backend tests except PostgreSQL-dependent tests
	$(UV) run pytest -m 'not postgres' -q

test-frontend: ## Run client, React, Next.js, and CLI package tests
	$(PNPM) test

test: test-backend test-frontend ## Run backend and frontend tests

e2e: ## Run Playwright tests using the configured browser
	$(PNPM) test:e2e

e2e-chrome: ## Run Playwright tests using an installed Chrome browser
	AUTHKIT_E2E_BROWSER_CHANNEL=chrome $(PNPM) test:e2e

e2e-install: ## Install the Playwright Chromium browser
	$(PNPM) $(FULLSTACK_FILTER) exec playwright install chromium

lint: ## Run Python and JavaScript linters
	$(UV) run ruff check authkit tests
	$(PNPM) lint

typecheck: ## Run Python and TypeScript type checks
	$(UV) run mypy authkit
	$(PNPM) typecheck

check: lint typecheck test ## Run the normal local quality gate

ui-init: ## Scaffold source-owned Next.js UI into UI_DIR
	$(PNPM) --filter @authkit/cli build
	node packages/cli/dist/index.js init --framework nextjs --dir "$(UI_DIR)"
