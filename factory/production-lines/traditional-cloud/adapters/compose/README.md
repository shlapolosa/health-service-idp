# architect-v1

The Capability Factory architect — Foundry chat agent that translates "we need a capability for X"
into a reviewable PR on the health-service-idp repo.

## Files in this directory

| File | Purpose |
|---|---|
| `system-prompt.md` | The agent's instructions — 7-phase reasoning shape (UNDERSTAND → SCORE → BRANCH → PATTERN MATCH → SYNTHESISE → VALIDATE → PROPOSE). |
| `manifest.json` | Foundry agent definition — model, MCP tool wiring, consent rules. |
| `README.md` | This file. |

The pattern table that drives Phase 4 (pattern-match) lives in
`capability-factory/schema/quality-attributes-v0.yaml#provisioning.patterns`. The agent reads it
via the `examples.pattern_for` MCP tool — **the system prompt does not duplicate it**, so there is
exactly one source of truth.

## Identity model (P8.2 design — locked)

The agent uses **two separate** service principals against the same APIM gateway:

| MCP | Service Principal | APIM app role | What it gets |
|---|---|---|---|
| `/mcp/catalog` | `sp-architect-reader` | `catalog-reader` | All read tools (KB, examples, catalog, dry-runs) |
| `/mcp/factory` | `sp-architect-writer` | `factory-proposer` | `factory.propose` + `factory.list_open_prs` |

Two SPs (not one with two roles) so the writer can be revoked independently of the reader during
incident response. The reader's footprint = zero side effects; the writer's footprint = git PR
opens only.

## ⚠️ Use the right Foundry API path

The Foundry Agent Service has two REST surfaces in the data plane:

| API path | Purpose | MCP works? |
|---|---|---|
| `/assistants` + `/threads/{id}/runs` | OpenAI Assistants protocol compatibility (legacy) | **No.** Runs fail with `server_error / 0 tokens / 0 steps` for any MCP tool. |
| **`/agents` (create) + `/openai/v1/responses` (run)** | **Microsoft Foundry Agent Service GA contract** | **Yes.** Empirically proven on `usecase-architect-poc` UAE North + gpt-5.4. |

We previously misdiagnosed `/assistants` failures as a "regional preview gate" — they are not. The `/assistants` path on Foundry projects is the legacy compat surface and doesn't wire MCP tool calls. **Use `/openai/v1/responses` with `agent_reference: {name, type: "agent_reference"}`.**

CLI helper that does the right thing: `scripts/foundry_responses.py`.

```bash
# Upsert the agent + run a smoke
python3 scripts/foundry_responses.py \
  --endpoint https://aifoundry-socrates.services.ai.azure.com/api/projects/usecase-architect-poc \
  --agent architect-v1 \
  --create agents/architect-v1/manifest.json \
  --message "We need a durable, low-latency, lightweight messaging capability."

# Subsequent runs against the same agent — no --create needed
python3 scripts/foundry_responses.py \
  --endpoint https://aifoundry-socrates.services.ai.azure.com/api/projects/usecase-architect-poc \
  --agent architect-v1 \
  --message "What patterns are available?"
```

## Registering the agent in Foundry

There are two paths. Pick one.

### Path A — Foundry portal (manual, recommended for first-time setup)

1. Open `https://ai.azure.com` → select the `aifoundry-socrates` project.
2. **Agents → New agent**.
3. Name: `architect-v1`.
4. Model: `gpt-5.4` (already deployed).
5. **Instructions**: paste the entire content of `system-prompt.md`.
6. **Tools → Add MCP server**:
   - Label `catalog`, URL `https://aigw-apim-dev-w4x7ibwk4e2is.azure-api.net/mcp/catalog/mcp`,
     auth: bearer token from sp-architect-reader (scope `api://fe225ae2-…/.default`).
   - Label `factory`, URL `https://aigw-apim-dev-w4x7ibwk4e2is.azure-api.net/mcp/factory/mcp`,
     auth: bearer token from sp-architect-writer (scope `api://<factory-app-guid>/.default`).
7. Allow-list the tools listed in `manifest.json`'s `allowed_tools` arrays. Other tools (e.g. an
   accidentally-exposed write verb on the catalog side) should NOT be in the allow-list.
8. Mark `factory.propose` as **requires user confirmation** (the consent gate). Foundry's UI
   exposes this as a per-tool checkbox.
9. Save.

### Path B — REST API (idempotent, suitable for CI)

```bash
bash scripts/setup-architect-agent.sh \
  --foundry-endpoint https://aifoundry-socrates.openai.azure.com \
  --foundry-project-id <project-resource-id> \
  --catalog-mcp-url https://aigw-apim-dev-w4x7ibwk4e2is.azure-api.net/mcp/catalog/mcp \
  --factory-mcp-url https://aigw-apim-dev-w4x7ibwk4e2is.azure-api.net/mcp/factory/mcp \
  --reader-sp-tenant df03bef9-... --reader-sp-app-id <reader-sp-app-id> \
  --writer-sp-tenant df03bef9-... --writer-sp-app-id <writer-sp-app-id>
```

The script:
1. POSTs the agent definition to the Foundry Agents API.
2. Wires up both MCP servers.
3. Configures the per-tool consent gate.
4. Returns the agent ID for chat invocation.

## Testing the agent

### Chat-driven (the canonical UX)

In Foundry portal → Agents → architect-v1 → **Try it out**:

```
USER: We need a durable, low-latency, lightweight messaging capability.
```

Expected flow:
1. Agent calls `catalog.search` with `category: messaging` + derived quality attrs.
2. Recommends `nats-jetstream` (top-ranked, already published if P8.1's nats-jetstream KB row is published in the cluster).
3. Calls `kb.diff("nats-jetstream")` → `gap_kind: none` → agent recommends it without any PR action.

For a "needs OAM" path (proves the full propose loop):

```
USER: We need a high-throughput, strongly-durable, partition-ordered messaging capability for analytics workloads.
```

Expected:
1. Agent picks `kafka` from the scorer.
2. `kb.diff("kafka")` → `gap_kind: needs_oam` (kafka KB row is maturity:kb, no CD).
3. Agent calls `examples.pattern_for("operator-backed", false)` → pattern-c-operator-backed.
4. Agent synthesises kafka CD + ADR + KB promotion.
5. Agent calls `oam.dry_run` + `crossplane.dry_run`.
6. **Agent stops and asks for consent** before calling `factory.propose`.
7. User confirms → PR opens.

### Programmatic smoke test

Once the agent is registered, you can drive it from `n8n` (or any HTTP client) via the Foundry
Chat Completions API. See `scripts/test-architect-agent.sh` for an example.

## Reusing the system prompt in `scripts/architect.py`

The CLI architect (`scripts/architect.py`) does NOT load the system prompt — it hardcodes the
deterministic flow inline because it doesn't reason. The system prompt is **agent-only** behavior.

This keeps the two surfaces honest:
- **CLI** = deterministic orchestrator with two LLM-as-template-filler calls (no reasoning loop).
- **Foundry agent** = reasoning agent with the full 7-phase loop.

If the Foundry agent makes a recommendation, it should match what the CLI produces for the same
request — verified by the regression test in P8.1.
