.PHONY: help up down build logs dev test lint clean helm-template helm-install helm-upgrade

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Docker Compose ──────────────────────────────────────────────────

up: ## Start with docker-compose (builds if needed)
	docker compose up -d --build

down: ## Stop docker-compose
	docker compose down

build: ## Build Docker images
	docker compose build

logs: ## Tail docker-compose logs
	docker compose logs -f

# ── Local Development ───────────────────────────────────────────────

dev: ## Start local dev (backend + frontend)
	@echo "Starting backend and frontend..."
	@trap 'kill 0' EXIT; \
		uvicorn primer.server.app:app --reload --port 8000 & \
		cd frontend && npm run dev & \
		wait

test: ## Run all tests
	pytest -v
	cd frontend && npm test

lint: ## Run linters
	ruff check .
	ruff format --check .
	cd frontend && npm run lint

# ── Cleanup ─────────────────────────────────────────────────────────

clean: ## Remove containers, volumes, build artifacts
	docker compose down -v
	rm -rf frontend/dist

# ── Helm ────────────────────────────────────────────────────────────

HELM_RELEASE ?= primer
HELM_NAMESPACE ?= default
HELM_CHART = deploy/helm/primer

helm-template: ## Render Helm templates locally
	helm template $(HELM_RELEASE) $(HELM_CHART) --debug

helm-install: ## Install Helm chart
	helm install $(HELM_RELEASE) $(HELM_CHART) --namespace $(HELM_NAMESPACE)

helm-upgrade: ## Upgrade Helm release
	helm upgrade $(HELM_RELEASE) $(HELM_CHART) --namespace $(HELM_NAMESPACE)
