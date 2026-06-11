# Analysis Prompt — Solution Architecture & Reuse Assessment

> **Provenance**
> - Source workflow: `local-ai-packaged/n8n-workflows-refactor/05a-solution-architecture-workflow.json`
> - LLM generation nodes: `Assess Component Changes` (httpRequest), `Generate Solution Package` (httpRequest)
> - Supporting code nodes (the "reuse" mechanics): `Extract Sequence Diagrams`, `Prepare Component Search`, `Search Existing Landscape` (Qdrant + Ollama embeddings), `Map Sequence to Components`, `Merge Change Assessment`, `Explode Solution Artifacts`
> - Validation node: `Validate Solution` (code)
> - Extracted: 2026-06-11
> - Status: **DORMANT** (not wired)
> - Confidence: **clean** (prompts) / **partial** (reuse mechanics — superseded, see legend)

This stage was the most elaborate: it (1) pulled sequence diagrams out of the architecture artifacts, (2) **searched an existing-landscape vector store** to resolve each abstract participant to a concrete component, (3) asked the LLM to assess per-step changes as Jira-ready tickets, then (4) asked the LLM to emit the integration package (OpenAPI/AsyncAPI/Avro/SQL).

> **NOTE on the reuse mechanics:** steps (1)-(2) used Ollama `nomic-embed-text` embeddings + a Qdrant collection `existing-landscape` (cosine match, `exists` threshold `score > 0.65`). This whole sub-system is **superseded** by the platform's catalog MCP (`kb.*` / `examples.*`) + the reuse→repurpose→create prompts — see dev-agent-factory.md supersession table. The prompts below are the residue worth keeping; the Qdrant plumbing is dropped.

---

## Part A — Component Change Assessment (`Assess Component Changes`)

### System prompt

```
You are a solution architect creating Jira-ready tickets for component changes.

For each sequence step, assess if changes are needed and produce ticket specifications.

Output JSON with structure:
{
  "assessedSequences": [{
    "useCaseId": "string",
    "useCaseName": "string",
    "enrichedFlow": [{
      "step": number,
      "from": { "component": "string", "type": "string" },
      "to": { "component": "string", "type": "string" },
      "action": "string",
      "componentStatus": "exists" | "needs_change" | "new_required",
      "ticket": {
        "title": "Action-oriented title",
        "type": "Story" | "Task" | "Bug",
        "priority": "Critical" | "High" | "Medium" | "Low",
        "component": "Affected service/module name",
        "description": "User story format",
        "acceptanceCriteria": ["GIVEN/WHEN/THEN statements"],
        "technicalRequirements": ["Specific implementation tasks"],
        "estimatedEffort": "T-shirt size with day range",
        "dependencies": ["Prerequisites"]
      } | null
    }],
    "newComponentsRequired": [{ "ticket": {...} }],
    "ticketSummary": {
      "totalTickets": number,
      "byPriority": { "High": number, "Medium": number, "Low": number },
      "byType": { "Story": number, "Task": number },
      "totalEffort": "estimated range"
    }
  }]
}

Be specific about:
- API endpoints (method, path)
- Database changes (table, column)
- Integration points
- Validation and error handling
```

### User prompt

```
PROJECT: {project_name}

BRD CONTEXT: {brd_json}

ENRICHED SEQUENCES TO ASSESS: {enriched_sequences_json}

PARTICIPANT MAP: {participant_map_json}
```

### Placeholder legend
| Placeholder | n8n origin | Meaning |
|---|---|---|
| `{project_name}` | `$json.projectName` | Project name. |
| `{brd_json}` | `…artifacts.brd…slice(0,4000)` | BRD context. |
| `{enriched_sequences_json}` | `…enrichedSequences…slice(0,8000)` | Sequence diagrams with each participant resolved to a concrete component (output of `Map Sequence to Components`). |
| `{participant_map_json}` | `…participantMap…slice(0,4000)` | Map abstract participant → `{concrete, type, isInternal, exists, score, port, capabilities, integrations, tables…}` from the landscape search. |

> Original generation params: `temperature: 0.1, seed: 42` (hard-coded for determinism); timeout 300 000 ms.
> The `enrichedFlow` / `participantMap` structures (built by `Map Sequence to Components`) carry the **reuse signal**: `exists` (score > 0.65), `isInternal`, resolved `endpoint`. These map directly onto the platform's reuse→repurpose→create decision.

---

## Part B — Solution Package (`Generate Solution Package`)

### System prompt

```
You are a Solution Architect producing integration artifacts. Output JSON with: integrationStyle (rest_only|events_only|hybrid), solutionMarkdown (starts with "# Solution Architecture:"), openapiYaml (OpenAPI 3.0 spec if REST), asyncapiYaml (AsyncAPI 2.0 spec if events), avroSchemasJson (Avro schemas object if events), cloudEventsMarkdown (Cloud Events documentation if events), sqlSchemaSql (PostgreSQL DDL). Include all relevant artifacts based on integrationStyle. No code fences anywhere.
```

### User prompt

```
PROJECT: {project_name}
BRD: {brd_json}
APP_ARCH: {application_arch_json}
DATA_ARCH: {data_arch_json}
INFRA_ARCH: {infrastructure_arch_json}
```

### Placeholder legend
| Placeholder | n8n origin |
|---|---|
| `{project_name}` | `…projectName` |
| `{brd_json}` | `…artifacts.brd…slice(0,6000)` |
| `{application_arch_json}` | `…artifacts.application_arch…slice(0,6000)` |
| `{data_arch_json}` | `…artifacts.data_arch…slice(0,4000)` |
| `{infrastructure_arch_json}` | `…artifacts.infrastructure_arch…slice(0,4000)` |

> Params: `temperature`/`seed` from `Initialize Parameters`; timeout 300 000 ms.

### Expected output schema

```json
{
  "integrationStyle": "rest_only | events_only | hybrid",
  "solutionMarkdown": "string (MUST start with '# Solution Architecture:')",
  "openapiYaml": "string|null (OpenAPI 3.0)",
  "asyncapiYaml": "string|null (AsyncAPI 2.0)",
  "avroSchemasJson": "object|null",
  "cloudEventsMarkdown": "string|null",
  "sqlSchemaSql": "string (PostgreSQL DDL)"
}
```
Required: `integrationStyle, solutionMarkdown, sqlSchemaSql`.

`Explode Solution Artifacts` then fanned this into per-artifact rows only when present: `solution_arch_md` (always), `openapi_yaml`, `asyncapi_yaml`, `avro_schemas_json`, `cloud_events_md`, `sql_schema_sql`.

## Validation criteria (from `Validate Solution`)

- Response JSON must parse (else `JSON parse failed: <msg>`).
- **`valid` requires `solutionMarkdown` to start with `# Solution Architecture:`**.
- Defaults applied: `integrationStyle` → `rest_only`; optional artifacts → `null`/`''`.
- Per-artifact FNV-1a hashes computed (`solution, openapi, asyncapi, avro, cloudEvents, sql`).
