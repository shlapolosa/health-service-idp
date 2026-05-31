# Makefile — convenience targets that wrap ./factory/utilities/bootstrap.sh.
#
# Real-world analogy: the factory's master control panel. One button per common
# operation; under the hood each calls bootstrap.sh with the right arguments.

.PHONY: help up down status images build push verify substrate factory line tc test parity rm-monolith clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ── Bring up ──────────────────────────────────────────────────────────
up: ## Bring the entire factory up (substrate → factory → production-line:traditional-cloud → verify)
	./factory/utilities/bootstrap.sh up

up-fast: ## Same as `up` but skip image rebuild (assumes images already pushed)
	./factory/utilities/bootstrap.sh up --skip-images

substrate: ## Apply only substrate (Crossplane, Argo, Knative, ArgoCD)
	./factory/utilities/bootstrap.sh phase substrate

factory: ## Deploy only factory cross-line adapters
	./factory/utilities/bootstrap.sh phase factory

line: tc ## Alias for `tc` (deploy production-line:traditional-cloud)

tc: ## Deploy production-line:traditional-cloud (catalog + composition + execute + compose-mcp)
	./factory/utilities/bootstrap.sh phase production-line:traditional-cloud

# ── Images ────────────────────────────────────────────────────────────
images: ## Build + push all service images
	./factory/utilities/bootstrap.sh images build-and-push

build: ## Build all service images locally (no push)
	./factory/utilities/bootstrap.sh images build-only

push: ## Push already-built images
	./factory/utilities/bootstrap.sh images push-only

# ── Operations ────────────────────────────────────────────────────────
status: ## Run health checks across all phases
	./factory/utilities/bootstrap.sh status

verify: status ## Alias for status

down: ## Tear down factory + production-line services (keep substrate + data)
	./factory/utilities/bootstrap.sh down --keep-data

# ── Testing ───────────────────────────────────────────────────────────
test: ## Run all unit tests (capability-mcp-core + factory MCPs)
	@echo "── factory/shared-libs/capability-mcp-core ──"
	@cd factory/shared-libs/capability-mcp-core && python3 -m pytest tests/ -q --no-header
	@echo "── factory/adapters/mcp-read-gateway ──"
	@cd factory/adapters/mcp-read-gateway && python3 -m pytest tests/ -q --no-header

parity: ## Run MFG-TC catalog↔M4-schema parity audit
	./factory/utilities/check-mfg-tc-parity.sh

evals: ## Run architect-v1 Foundry eval suite
	@if [ -f factory/production-lines/traditional-cloud/evals/run_evals.py ]; then \
		cd factory/production-lines/traditional-cloud/evals && python3 run_evals.py; \
	else \
		echo "evals script not found"; \
	fi

# ── Cleanup ───────────────────────────────────────────────────────────
clean: ## Remove local docker images for factory services
	@for svc in capability-mcp-factory capability-factory-mcp capability-web-mcp capability-mcp-mfg-tc slack-api-server; do \
		docker rmi healthidpuaeacr.azurecr.io/$$svc:* 2>/dev/null || true; \
	done

clean-pycache: ## Remove Python caches across the tree
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
