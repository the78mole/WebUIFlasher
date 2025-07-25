# WebUIFlasher Docker Operations
.PHONY: help build up down logs clean secure dev restart release

help: ## Show this help message
	@echo "WebUIFlasher Docker Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the Docker image
	docker compose build

up: ## Start the service (permissive USB access)
	docker compose up -d
	@echo "✅ WebUIFlasher started at http://localhost:8000"

secure: ## Start with selected TTY devices only
	docker compose -f docker-compose.selected-tty.yaml up -d
	@echo "✅ WebUIFlasher (secure) started at http://localhost:8000"

down: ## Stop the service
	docker compose down

secure-down: ## Stop the secure service
	docker compose -f docker-compose.selected-tty.yaml down

logs: ## Show service logs
	docker compose logs -f webflasher

dev: ## Start development service (alias for up)
	$(MAKE) up

clean: ## Remove containers and images
	docker compose down --rmi all --volumes --remove-orphans

shell: ## Open shell in running container
	docker compose exec webflasher /bin/bash

firmware: ## Download firmware in container
	docker compose exec webflasher uv run scripts/update_firmwares.py --sources=sources.yaml

status: ## Show container status
	docker compose ps

restart: ## Restart the service
	docker compose restart webflasher

release: ## Create a new release (usage: make release VERSION=v1.0.0 DESC="Release description")
	@if [ -z "$(VERSION)" ] || [ -z "$(DESC)" ]; then \
		echo "Usage: make release VERSION=v1.0.0 DESC='Release description'"; \
		exit 1; \
	fi
	./create-release.sh "$(VERSION)" "$(DESC)"
