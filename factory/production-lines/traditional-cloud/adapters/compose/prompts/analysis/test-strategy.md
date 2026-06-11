# Analysis Prompt — Test Strategy / QA Package

> **Provenance**
> - Source workflow: `local-ai-packaged/n8n-workflows-refactor/05c-test-strategy-workflow.json`
> - Generation node: `Generate QA Package` (httpRequest → `https://ollama.socrates-hlapolosa.org/api/chat`)
> - Validation node: `Validate QA` (code)
> - Fan-out node: `Explode QA Artifacts` → `test_strategy_md`, `test_scenarios_md`
> - Extracted: 2026-06-11
> - Status: **DORMANT** (not wired)
> - Confidence: **clean**

## System prompt

```
You are a QA Architect. Output JSON with testStrategyMarkdown (starts with "# Test Strategy:") and testScenariosMarkdown (starts with "# Test Scenarios:"). No code fences. Include: testing approach, test types (unit, integration, e2e, performance, security), environments, tools, acceptance criteria, and detailed test scenarios with steps and expected results.
```

## User prompt

```
PROJECT: {project_name}
BRD: {brd_json}
APP_ARCH: {application_arch_json}
SOLUTION_ARCH: {solution_arch_md}
OPENAPI: {openapi_yaml}
RISK_ASSESSMENT: {risk_assessment_md}
```

### Placeholder legend
| Placeholder | n8n origin | Truncation |
|---|---|---|
| `{project_name}` | `$json.projectName` | — |
| `{brd_json}` | `…artifacts.brd` | 4 000 |
| `{application_arch_json}` | `…artifacts.application_arch` | 4 000 |
| `{solution_arch_md}` | `…artifacts.solution_arch_md.markdown` | 5 000 |
| `{openapi_yaml}` | `…artifacts.openapi_yaml.yaml` | 3 000 |
| `{risk_assessment_md}` | `…artifacts.risk_assessment_md.markdown` | 4 000 |

> Params: `temperature`/`seed` from `Initialize Parameters`; timeout 300 000 ms.

## Expected output schema

```json
{
  "testStrategyMarkdown": "string (MUST start with '# Test Strategy:')",
  "testScenariosMarkdown": "string (MUST start with '# Test Scenarios:')"
}
```
Required: `testStrategyMarkdown, testScenariosMarkdown`.
- `testStrategyMarkdown` body: testing approach, test types (unit, integration, e2e, performance, security), environments, tools, acceptance criteria.
- `testScenariosMarkdown` body: detailed scenarios with steps and expected results.

## Validation criteria (from `Validate QA`)

- Response JSON must parse (else `{ valid: false, error: 'JSON parse failed' }`).
- **`valid` requires `testStrategyMarkdown` to start with `# Test Strategy:`** (note: the scenarios prefix is documented in the prompt but not asserted in the validator).
- Per-artifact FNV-1a hashes: `strategy`, `scenarios`.
