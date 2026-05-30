# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.


# Developer Process & Principles
First go through REALTIME_SYSTEM.md for context.

Welcome to the CLAUDE development process. This document outlines the core development methodology, tools, design patterns, and quality standards expected from all contributors. This platform aims to deliver a Kubernetes-native Internal Developer Platform (IDP) using GitOps principles and automated infrastructure. To ensure maintainability, quality, and scalability, all contributors must follow the principles below.

---
# Pre dev

Note! always check your current-context and that you are running commands in the correct context. all workload commands should be executed in the vcluster and some infrustructure commands will be in the host cluster.

Always remember to check your mcp servers and any coding task much be preceeded by using context7 to check versions.

before starting a task, check if already implimented, then just test and verify.

## 🔍 Infrastructure Health Check

**CRITICAL**: Before starting any development work, always run the infrastructure health check to ensure all components are operational:

```bash
./scripts/infrastructure-health-check.sh
```

This diagnostic script validates:
- Slack API server accessibility and external routing
- Essential secrets (Docker registry, Slack, Argo tokens)
- Service accounts and RBAC configurations  
- OAM ComponentDefinitions and WorkloadDefinitions
- Argo Workflows infrastructure and templates
- Crossplane CRDs and compositions
- Istio service mesh and ingress gateway
- ArgoCD applications and sync status

Only proceed with development work after confirming all infrastructure components are healthy. If issues are found, resolve them before continuing with any tasks.


## 🧩 Development Methodology

### 🔧 Task Management via Taskmaster

All work is defined and tracked using **Taskmaster**. Every contributor must:
can use task-master cli, start with command below to see options

```
task-master
```

1. **Check Taskmaster** for their next assigned task.
to see what to work on next 
```
task-master next
```
2. **Implement the task** in line with all guidelines below.
Start working: 
```
task-master set-status --id=11 --status=in-progress 
```
3. **Push code incrementally**, with meaningful commit messages.
4. **Mark task complete** only after functional and regression testing is performed.

Tasks may span multiple commits, but only functionally complete and tested code should be merged.
After completing a task or subtask, go through ARCHITECTURAL_DECISIONS.md and check if any have been made and update accordingly if and only if an architectural decision was taken i.e. a trade-off made.
---

## 🧪 Testing Requirements

### 🔄 TDD Process (Red-Green-Refactor)

All code must be developed using Test-Driven Development:

* **Red**: Write failing test first
* **Green**: Write minimum code to make test pass
* **Refactor**: Improve the code using design patterns and principles

### 🔁 Regression Testing

You must create a repeatable test suite per repo (preferably using `pytest`, `unittest`, `bash`, or `curl`) to ensure new changes do not break existing functionality. This suite should:

* Be runnable at any time locally or in CI.
* Cover happy paths and known failure cases.
* Be documented in `tests/README.md`.

### 🔍 Manual Testing

If the task cannot be covered by automated tests (e.g. infrastructure bootstrapping), provide a script or `Makefile` that executes reproducible `curl`, `kubectl`, or `terraform` commands.

---

## 🧱 Code Principles

### 🧰 12-Factor Adherence

Every service must explicitly follow the [12-factor app](https://12factor.net/) methodology:

* **Codebase**: Single codebase, version controlled
* **Dependencies**: Explicitly declared in `requirements.txt`, `pyproject.toml`, or equivalent
* **Config**: Store in environment variables (never in code)
* **Backing services**: Treat DBs, caches, queues as attachable resources
* **Build, release, run**: Separation of stages
* **Processes**: Stateless and disposable
* **Port binding**: Self-contained service listening on a port
* **Concurrency**: Scale via process model
* **Dev/prod parity**: Keep environments as similar as possible
* **Logs**: Treat logs as event streams
* **Admin processes**: Run as one-off processes (e.g., migrations)

### 🧅 Onion Architecture

Every repo must implement a minimal **Hello World** app using the Onion Architecture pattern:

* **Domain Layer**: Business rules
* **Application Layer**: Use cases
* **Interface Layer**: REST/gRPC endpoints
* **Infrastructure Layer**: DBs, network, cache

This is a mandatory starting point for all service templates.

---

## 📐 Design Patterns & Quality

### 🧬 Dependency Injection

All services must support Dependency Injection (DI) out of the box. This applies to:

* Database access
* API clients
* Services and interfaces

Use frameworks like `fastapi.Depends`, `inject`, `wire`, or `dagger` as appropriate.

### ♻️ Refactor with GoF Patterns

During the **refactor** stage of TDD, aim to incorporate appropriate [Gang of Four (GoF)](https://refactoring.guru/design-patterns) design patterns such as:

* **Factory**: Object instantiation
* **Strategy**: Replace `if-else` logic
* **Adapter**: Wrap legacy components
* **Observer**: Event-driven hooks

This elevates long-term maintainability and flexibility.

---

## 🚀 Automation & Operations

### 🤖 DevOps

* **Linting**: should include steps for linting, owasp, container scan

### 🤖 GitOps

All deployable services or infrastructure must adhere to GitOps:

* Declarative manifests (Helm/OAM/CRDs)
* Managed via ArgoCD or Flux
* Configuration stored in Git

### 🤖 MLOps (Where Applicable)

Services using ML (e.g., data enrichment agents) must:

* Package and version models
* Declare training & evaluation pipelines in GitHub Actions or Argo Workflows
* Maintain `model/README.md` describing usage and requirements

---

## 🔍 Code Review Checklist

Before pushing or opening a PR:

1. ✅ Task checked off in Taskmaster?
2. ✅ Functional testing complete?
3. ✅ Regression tests passing?
4. ✅ TDD red-green-refactor loop followed?
5. ✅ Dependency injection used?
6. ✅ GoF design patterns applied where appropriate?
7. ✅ 12-factor principles followed?
8. ✅ Code pushed to GitHub?
9. ✅ GitOps/OAM manifests created or updated?

Only then may a PR be opened or branch merged.

---

## 📦 Repo Template Requirements

Each service repo must include:

The GitOps configuration repo (`shlapolosa/health-service-idp-gitops`) houses both ArgoCD and OAM application definitions, including manifests such as Knative services, OAM components, and Helm charts. These define deployment specifications, environments, and application topology and must not live in the source repo.

All actual application source code resides in a separate source code repository (e.g., `shlapolosa/health-service-idp`) and should only contain domain logic, application logic, infrastructure code, interfaces, tests, and CI configurations.

```
README.md
pyproject.toml / pom.xml
src/
  domain/
  application/
  infrastructure/
  interface/
tests/
.gitignore
Dockerfile
Makefile or setup.sh
manifest/
  knative-service.yaml
  oam-component.yaml
.github/workflows/ci.yml
```

---

## 👥 Collaboration

* Prefer small, atomic PRs
* All commits should be meaningful
* Use draft PRs for early feedback

---

## 📋 TODOs: Platform Improvements & Findings

### **🔧 Critical OAM Platform Fixes**

#### **1. Default Unified Repository Pattern**
- **Status**: 🔴 HIGH PRIORITY  
- **Issue**: Each OAM component creates separate ApplicationClaim → separate repositories by default
- **Current**: Separate repos unless user explicitly specifies same `repository` property
- **Target**: Unified repo unless user explicitly specifies separate repositories  
- **Implementation**: 
  - Modify `crossplane/application-claim-composition.yaml` (lines 1018-1086)
  - Extract `repository` property from OAM Application level → auto-populate `APP_CONTAINER` env var
  - Default to shared repository pattern like `healthcare-quality-platform` example

#### **2. Advanced Traits & Policies Support**
- **Status**: 🟡 MEDIUM PRIORITY
- **Issue**: Custom traits (sensor-burst-scaler, parking-circuit-breaker, parking-monitoring, parking-security) cause parsing failures
- **Current**: Only 4 basic TraitDefinitions, 1 WorkloadDefinition (webservice)
- **Gap**: Missing TraitDefinitions for advanced OAM features
- **Solution**: 
  - Create missing TraitDefinitions for circuit breakers, monitoring, security policies
  - Expand WorkloadDefinition support beyond just Knative Services
  - Add PolicyDefinition implementations that don't cause parsing errors

#### **3. Multi-Namespace OAM Deployment**
- **Status**: 🟡 MEDIUM PRIORITY  
- **Blocker**: ComponentDefinitions are namespace-scoped, only exist in `default` namespace
- **Impact**: OAM Applications can only deploy where ComponentDefinitions exist
- **Analysis Required**:
  - Cluster-scoped ComponentDefinitions vs replicate to each namespace
  - RBAC implications, network policies, resource quotas per namespace
  - Service accounts, secrets, roles must exist in target namespace
- **Options**: 
  - Make ComponentDefinitions cluster-scoped (breaking change)
  - Auto-replicate ComponentDefinitions to target namespaces
  - Multi-tenancy strategy with namespace isolation

#### **4. GraphQL API Aggregation Integration**
- **Status**: 🟢 LOW PRIORITY - ENHANCEMENT
- **Decision**: **Hasura wins over Apollo Server**
- **Rationale**: 
  - ✅ Auto-generates GraphQL from PostgreSQL (zero-code)
  - ✅ Real-time subscriptions out-of-the-box  
  - ✅ Built-in admin UI and role-based permissions
  - ✅ Simpler setup and maintenance
- **Integration Point**: Add Hasura component to ApplicationClaim creation process
- **Dependency**: Requires PostgreSQL connection (already provided by neon-postgres ComponentDefinition)
- **Implementation**: 
  - Create `hasura` ComponentDefinition
  - Auto-add to ApplicationClaims that request GraphQL exposure
  - Configure auto-schema generation from existing PostgreSQL databases

#### **5. OAM Standard Compliance Assessment**
- **Status**: 🟡 MEDIUM PRIORITY - ANALYSIS
- **Current Compliance**: ~60% with vanilla OAM specification
- **Compliant Areas**:
  - ✅ Using core.oam.dev/v1beta1 APIs correctly
  - ✅ CUE templates for component definitions follow standard
  - ✅ Basic trait composition works
- **Non-Compliant Areas**:
  - ❌ Custom ApplicationClaim XRD (not standard OAM)
  - ❌ Crossplane infrastructure integration dependencies
  - ❌ Custom ComponentDefinitions (realtime-platform, rasa-chatbot, application-infrastructure)
- **Path Forward**:
  - Create "Standard OAM Mode" alongside current enhanced mode
  - Remove Crossplane dependencies for vanilla compatibility
  - Maintain backward compatibility with current enhanced features

### **📊 Current Platform State Analysis**
- **ComponentDefinitions**: 11 total, all in default namespace only
- **WorkloadDefinitions**: 1 (webservice), only supports Knative Services  
- **TraitDefinitions**: 4 basic traits (autoscaler, ingress, kafka-consumer, kafka-producer)
- **OAM Applications**: 3 running successfully, all in default namespace
- **Repository Pattern**: APP_CONTAINER env var in ApplicationClaim composition controls unified repos
- **Cross-namespace Deployment**: Blocked by ComponentDefinition namespace scoping

### **🎯 Implementation Priority Order**
1. **Default Unified Repository Pattern** - Critical for developer experience
2. **Advanced Traits & Policies Support** - Enable complex OAM features  
3. **Multi-Namespace Deployment** - Enterprise multi-tenancy support
4. **OAM Standard Compliance** - Industry standard compatibility
5. **GraphQL Integration** - API aggregation enhancement

---


## Cloud-Native Architecture Visualization Platform

This is a GitOps-enabled cloud-native platform for intelligent architecture visualization, built with minimal cost and maximum stability principles. The system leverages vCluster isolation, Karpenter cost optimization, and comprehensive observability integration.

## High-Level Architecture

### Infrastructure Stack
- **EKS Cluster**: Minimal managed control plane with Karpenter-managed workload nodes
- **vCluster**: Virtual Kubernetes environment for workload isolation (`architecture-visualization`)
- **Knative + Istio**: Service mesh for 18 microservices with automatic scaling
- **ArgoCD**: GitOps deployment watching `health-service-idp-gitops` repository
- **Observability**: Prometheus, Grafana, Jaeger, Kiali accessible via subpath routing

### Application Architecture
- **18 Microservices**: 9 Anthropic-powered + 9 deterministic variants of AI agents
- **FastAPI-based**: All agents use shared `agent-common` library for standardized APIs
- **Orchestration Service**: Central workflow coordinator using Redis for state management
- **Streamlit Frontend**: Web interface for architecture design and agent interaction

### Agent Types
Each agent type has both `-anthropic` (AI-powered) and `-deterministic` (rule-based) variants:
- `business-analyst` - Requirements processing and entity extraction
- `business-architect` - Business strategy and governance
- `application-architect` - API design and technology selection
- `infrastructure-architect` - Infrastructure design and capacity planning
- `solution-architect` - Solution consolidation and reference architecture
- `project-manager` - Project planning and resource management
- `developer` - Code generation and test automation
- `accountant` - Financial analysis and cost optimization

## Essential Commands

### Infrastructure Management



### Microservice Development

```bash
# Build individual microservice
cd microservices/business-analyst-anthropic
./build.sh

# Run locally with Docker
./run.sh

# Run with docker-compose (includes environment variables)
docker-compose up

# Test deployed Knative service
./test-deployment.sh
```

### Python Development (Poetry-based)

```bash
# Install dependencies for a microservice
cd microservices/business-analyst-anthropic
poetry install

# Run tests
poetry run pytest

# Format code
poetry run black src/
poetry run isort src/

# Type checking
poetry run mypy src/
```

### Shared Libraries

```bash
# Build and distribute agent-common library
cd microservices/shared-libs/agent-common
poetry build
poetry install  # Install locally for development
```

### CI/CD and Versioning

```bash

# main file
.github/workflow/comprehensive-gitops.yml

# generate shedule events in github
.github/workflow/argocd-sync.yml

# Generate semantic version for service
.github/scripts/version-manager.sh version streamlit-frontend

```

### Testing

```bash
# Run unit tests for specific service
cd microservices/business-analyst-anthropic
poetry run pytest tests/

# Run single test
poetry run pytest tests/test_main.py::test_health_check

# Run integration tests against deployed services
./test-deployment.sh

# Test with specific namespace
NAMESPACE=my-namespace ./test-deployment.sh
```

## Development Patterns

### Agent Microservice Structure
All agent microservices follow this pattern:
- `src/main.py` - FastAPI app using `agent_common.fastapi_base.create_agent_app()`
- `src/{agent_name}.py` - Agent implementation extending `BaseMicroserviceAgent`
- `src/models.py` - Service-specific Pydantic models
- `pyproject.toml` - Poetry configuration with standardized dependencies
- `knative-service.yaml` - Knative deployment configuration
- `Dockerfile` - Multi-stage build copying from `shared-libs/agent-common`

### Shared Library Integration
The `agent-common` library provides:
- `BaseMicroserviceAgent` - Base class for all agents
- `create_agent_app()` - FastAPI factory with standard endpoints
- Common models: `AgentRequestModel`, `AgentResponseModel`
- Standardized health checks and error handling

### Standard API Endpoints
All agents expose:
- `GET /health` - Health check for Kubernetes probes
- `GET /` - Service status
- `POST /{task-specific-endpoints}` - Agent capabilities (varies by agent type)
- `GET /docs` - Auto-generated OpenAPI documentation

### GitOps Workflow
1. Code changes trigger `.github/workflows/comprehensive-gitops.yml`
2. Semantic versioning with `MAJOR.MINOR.COMMIT_SHA` format
3. Container images built and pushed to `docker.io/socrates12345/*`
4. Repository dispatch event updates `health-service-idp-gitops` repository
5. ArgoCD syncs OAM applications to vCluster environment

## Important Configuration

### Environment Variables
- `ANTHROPIC_API_KEY` - Required for Anthropic-powered agents
- `LOG_LEVEL` - Logging level (INFO, DEBUG, ERROR)
- `AGENT_TYPE` - Agent type identifier
- `IMPLEMENTATION_TYPE` - anthropic or deterministic

### Port Mappings
- **Production**: All services use port 8080 (except frontend: 8501)
- **Development**: Services use ports 8081-8096 (odd for anthropic, even for deterministic)
- **Frontend**: Always uses port 8501

### Knative Configuration
- Auto-scaling between 0-10 replicas
- Resource limits: 500m CPU, 1Gi memory
- Health checks on `/health` endpoint
- Service mesh integration via Istio

## Key Files and Directories

- `.version` - Base semantic version (currently `1.1`)
- `cluster-lifecycle.sh` - Infrastructure management script
- `vcluster-infrastructure.yaml` - AWS CloudFormation template
- `.github/workflows/comprehensive-gitops.yml` - Complete CI/CD pipeline
- `.github/scripts/version-manager.sh` - Semantic versioning and OAM updates
- `microservices/shared-libs/agent-common/` - Shared FastAPI base classes
- `microservices/orchestration-service/` - Central workflow coordinator
- `microservices/streamlit-frontend/` - Web interface

## Observability Access

All observability tools are accessible via subpath routing when the load balancer is configured:
- ArgoCD: `/argocd`
- Grafana: `/grafana`
- Jaeger: `/jaeger`
- Kiali: `/kiali`
- Prometheus: `/prometheus`

## Development Workflow

1. Make changes to microservice code in `microservices/{service-name}/`
2. Test locally with `docker-compose up` or `./run.sh`
3. Run unit tests with `poetry run pytest`
4. Push to feature branch for CI/CD validation
5. Push to main branch for automatic deployment
6. Monitor deployment in ArgoCD and metrics in Grafana

## Cost Optimization

The platform is designed for minimal cost:
- vCluster pause/resume for complete workload shutdown
- Karpenter auto-scaling only provisions nodes when needed
- Single t3.medium managed node hosts control plane components
- Complete infrastructure shutdown capability via `./cluster-lifecycle.sh down`

## Slack Testing Notes

* When testing slack, find the ingress external url, gateway, vs to the slack service and always use that. 
* The endpoint is `slack/command`
* **When testing first run scripts/infrastructure-health-check-enhanced.sh then find istio external ingress url, then go through gateway, vs to find slack api slack/command endpoint, you can look at the model.py and controller to better understand request structure. then submit request and monitor, fixing accordingly**
```

# context-mode — MANDATORY routing rules

You have context-mode MCP tools available. These rules are NOT optional — they protect your context window from flooding. A single unrouted command can dump 56 KB into context and waste the entire session.

## BLOCKED commands — do NOT attempt these

### curl / wget — BLOCKED
Any Bash command containing `curl` or `wget` is intercepted and replaced with an error message. Do NOT retry.
Instead use:
- `ctx_fetch_and_index(url, source)` to fetch and index web pages
- `ctx_execute(language: "javascript", code: "const r = await fetch(...)")` to run HTTP calls in sandbox

### Inline HTTP — BLOCKED
Any Bash command containing `fetch('http`, `requests.get(`, `requests.post(`, `http.get(`, or `http.request(` is intercepted and replaced with an error message. Do NOT retry with Bash.
Instead use:
- `ctx_execute(language, code)` to run HTTP calls in sandbox — only stdout enters context

### WebFetch — BLOCKED
WebFetch calls are denied entirely. The URL is extracted and you are told to use `ctx_fetch_and_index` instead.
Instead use:
- `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` to query the indexed content

## REDIRECTED tools — use sandbox equivalents

### Bash (>20 lines output)
Bash is ONLY for: `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`, and other short-output commands.
For everything else, use:
- `ctx_batch_execute(commands, queries)` — run multiple commands + search in ONE call
- `ctx_execute(language: "shell", code: "...")` — run in sandbox, only stdout enters context

### Read (for analysis)
If you are reading a file to **Edit** it → Read is correct (Edit needs content in context).
If you are reading to **analyze, explore, or summarize** → use `ctx_execute_file(path, language, code)` instead. Only your printed summary enters context. The raw file content stays in the sandbox.

### Grep (large results)
Grep results can flood context. Use `ctx_execute(language: "shell", code: "grep ...")` to run searches in sandbox. Only your printed summary enters context.

## Tool selection hierarchy

1. **GATHER**: `ctx_batch_execute(commands, queries)` — Primary tool. Runs all commands, auto-indexes output, returns search results. ONE call replaces 30+ individual calls.
2. **FOLLOW-UP**: `ctx_search(queries: ["q1", "q2", ...])` — Query indexed content. Pass ALL questions as array in ONE call.
3. **PROCESSING**: `ctx_execute(language, code)` | `ctx_execute_file(path, language, code)` — Sandbox execution. Only stdout enters context.
4. **WEB**: `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` — Fetch, chunk, index, query. Raw HTML never enters context.
5. **INDEX**: `ctx_index(content, source)` — Store content in FTS5 knowledge base for later search.

## Subagent routing

When spawning subagents (Agent/Task tool), the routing block is automatically injected into their prompt. Bash-type subagents are upgraded to general-purpose so they have access to MCP tools. You do NOT need to manually instruct subagents about context-mode.

## Output constraints

- Keep responses under 500 words.
- Write artifacts (code, configs, PRDs) to FILES — never return them as inline text. Return only: file path + 1-line description.
- When indexing content, use descriptive source labels so others can `ctx_search(source: "label")` later.

## ctx commands

| Command | Action |
|---------|--------|
| `ctx stats` | Call the `ctx_stats` MCP tool and display the full output verbatim |
| `ctx doctor` | Call the `ctx_doctor` MCP tool, run the returned shell command, display as checklist |
| `ctx upgrade` | Call the `ctx_upgrade` MCP tool, run the returned shell command, display as checklist |
