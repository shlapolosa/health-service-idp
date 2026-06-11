# Analysis Prompt — PRD (Product Requirements Document, RPG Method)

> **Provenance**
> - Source workflow: `local-ai-packaged/n8n-workflows-refactor/04-project-management-workflow.json`
> - Generation node: `Generate PRD` (httpRequest → `https://ollama.socrates-hlapolosa.org/api/chat`)
> - Validation node: `Validate PRD` (code)
> - Extracted: 2026-06-11
> - Status: **DORMANT** (not wired)
> - Confidence: **clean**

This is the terminal document of the n8n pipeline — the PRD that fed Taskmaster decomposition (stage 7, Software Delivery). It uses the **RPG (Repository Planning Graph) Method**, which makes it directly relevant to the dev-agent: its `Capability Tree` / `Repository Structure` / `Module Definitions` / `Dependency Chain` sections are exactly the task-decomposition scaffold the dev-agent needs.

## System prompt

```
You are a Business Analyst writing a PRD using the RPG (Repository Planning Graph) Method. Output JSON with {"markdown": "..."} only. First line of markdown MUST be: # PRD: <Project Name>. Include sections: Problem Statement, Target Users, Success Metrics, Capability Tree, Repository Structure, Module Definitions, Dependency Chain, Development Phases, Test Pyramid, Coverage Requirements, Critical Test Scenarios, System Components, Data Models, Technology Stack, Technical Risks, Open Questions.
```

## User prompt

```
PROJECT_NAME: {project_name}
BRD: {brd_json}
BUSINESS_ARCH: {business_arch_json}
APP_ARCH: {application_arch_json}
DATA_ARCH: {data_arch_json}
INFRA_ARCH: {infrastructure_arch_json}
RISK_MD: {risk_assessment_md}
SOLUTION_MD: {solution_arch_md}
TEST_STRATEGY: {test_strategy_md}
TEST_SCENARIOS: {test_scenarios_md}
```

### Placeholder legend
| Placeholder | n8n origin | Truncation |
|---|---|---|
| `{project_name}` | `$json.projectName` | — |
| `{brd_json}` | `…artifacts.brd` | 8 000 |
| `{business_arch_json}` | `…artifacts.business_arch` | 6 000 |
| `{application_arch_json}` | `…artifacts.application_arch` | 6 000 |
| `{data_arch_json}` | `…artifacts.data_arch` | 4 000 |
| `{infrastructure_arch_json}` | `…artifacts.infrastructure_arch` | 4 000 |
| `{risk_assessment_md}` | `…artifacts.risk_assessment_md.markdown` | 4 000 |
| `{solution_arch_md}` | `…artifacts.solution_arch_md.markdown` | 4 000 |
| `{test_strategy_md}` | `…artifacts.test_strategy_md.markdown` | 4 000 |
| `{test_scenarios_md}` | `…artifacts.test_scenarios_md.markdown` | 4 000 |

> This stage is the integration point: it consumes **every** prior artifact. Params: `temperature`/`seed` from `Initialize Parameters`; timeout 180 000 ms.

## Expected output schema

```json
{ "markdown": "string (first line MUST be '# PRD: <Project Name>')" }
```
Required: `markdown`. Mandated sections (RPG Method): Problem Statement, Target Users, Success Metrics, **Capability Tree, Repository Structure, Module Definitions, Dependency Chain**, Development Phases, **Test Pyramid, Coverage Requirements, Critical Test Scenarios**, System Components, Data Models, Technology Stack, Technical Risks, Open Questions.

## Validation criteria (from `Validate PRD`)

- Response JSON must parse (else `valid: false`, `errors: ['PRD parse failed: <msg>']`).
- **First line must start with `# PRD:`** (else `errors: ['First line must start with "# PRD:"']`).
- `valid` iff `errors` empty; `prdHash` (FNV-1a) computed.
