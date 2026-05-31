# capability-mcp-core

Shared Python library for the capability-MCP family of servers. **Not deployed
directly** — only its *consumers* are containerised and run as Knative services.

## What's in here

```
src/
  domain/          # pure domain models (Pydantic): Capability, Recipe, etc.
  application/     # use-cases (no I/O):
    catalog_use_cases.py     # list/score/get capabilities + recipes
    submit_use_case.py       # render OAM + dry-run + push-PR pipeline
    route_use_case.py        # classify request + pick manufacturer
    kb_use_cases.py          # knowledge-base lookups for architect
    examples_use_cases.py    # curated OAM examples
    scoring.py               # capability-match scoring helpers
  infrastructure/  # adapters to external systems:
    k8s_catalog_client.py     # reads CRDs from the cluster
    argo_client.py            # Argo Workflows submit
    vela_client.py            # KubeVela dry-run
    github_client.py          # PR creation via GitHub App
    recipes_loader.py         # loads recipes from disk/git
    kb_loader.py              # loads KB markdown
    examples_loader.py        # loads OAM example files
    cue_param_parser.py       # extracts parameters from CUE
    crossplane_dryrun_client.py
    classify_router_client.py
  interface/       # transport-agnostic glue:
    auth.py            # JWT validation (Entra ID)
    dependencies.py    # DI container factories (FastMCP & FastAPI)
    __init__.py
tests/             # unit tests for all of the above
requirements.txt   # runtime deps shared across consumers
```

## Consumers

This library is consumed by:

| Consumer | Path | Role |
|---|---|---|
| **factory MCP (read gateway)** | `factory/adapters/mcp-read-gateway/` | factory.route + factory.propose; read-only catalog surface |
| **per-line compose MCP** | `factory/production-lines/traditional-cloud/adapters/compose-mcp/` | resolves OAM compositions for the traditional-cloud manufacturer line |

Each consumer adds its own thin `mcp_server.py` (FastMCP tool registration) +
`main.py` + `Dockerfile` + `knative-service.yaml`, but pulls all use-cases and
infrastructure adapters from this library. **This library itself is not
deployed** — only its consumers are containerised and run as Knative services.

## Why a library, not a service

The previous monolith `capability-mcp-server/` mixed two concerns:

1. **Capability mechanics** — domain, use-cases, adapters → now this library.
2. **Server-specific FastMCP tool surface** — now lives per-consumer.

Extracting the core lets multiple manufacturer/factory MCP servers share the
same vetted code without re-implementing scoring, CUE parsing, GitHub PR
creation, etc.

## Installing in a consumer

Consumers reference this library via Docker `COPY` in their Dockerfile (no
publish step; everything lives in the monorepo):

```dockerfile
COPY factory/shared-libs/capability-mcp-core/src/ /app/capability_mcp_core/
COPY factory/shared-libs/capability-mcp-core/requirements.txt /tmp/core-req.txt
RUN pip install -r /tmp/core-req.txt
```

Then import:

```python
from capability_mcp_core.application.catalog_use_cases import list_capabilities
from capability_mcp_core.interface.dependencies import build_catalog_container
```

## Testing

```bash
cd factory/shared-libs/capability-mcp-core
pip install -r requirements.txt
pytest tests/
```
