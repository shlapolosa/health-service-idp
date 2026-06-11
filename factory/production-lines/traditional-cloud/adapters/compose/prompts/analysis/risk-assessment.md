# Analysis Prompt — Risk Assessment

> **Provenance**
> - Source workflow: `local-ai-packaged/n8n-workflows-refactor/05b-risk-assessment-workflow.json`
> - Generation node: `Generate Risk Assessment` (httpRequest → `https://ollama.socrates-hlapolosa.org/api/chat`)
> - Validation node: `Validate Risk` (code)
> - Extracted: 2026-06-11
> - Status: **DORMANT** (not wired)
> - Confidence: **clean**

## System prompt

```
You are a Security Architect producing a risk assessment. Output JSON {"markdown": "..."} only. Markdown must start with "# Risk Assessment:" - no code fences. Cover: security risks, data privacy, compliance requirements, technical risks, and mitigation strategies.
```

## User prompt

```
PROJECT: {project_name}
BRD: {brd_json}
BUSINESS_ARCH: {business_arch_json}
APP_ARCH: {application_arch_json}
SOLUTION_ARCH: {solution_arch_md}
OPENAPI: {openapi_yaml}
ASYNCAPI: {asyncapi_yaml}
```

### Placeholder legend
| Placeholder | n8n origin | Truncation |
|---|---|---|
| `{project_name}` | `$json.projectName` | — |
| `{brd_json}` | `…artifacts.brd` | 5 000 |
| `{business_arch_json}` | `…artifacts.business_arch` | 4 000 |
| `{application_arch_json}` | `…artifacts.application_arch` | 4 000 |
| `{solution_arch_md}` | `…artifacts.solution_arch_md.markdown` | 5 000 |
| `{openapi_yaml}` | `…artifacts.openapi_yaml.yaml` | 3 000 |
| `{asyncapi_yaml}` | `…artifacts.asyncapi_yaml.yaml` | 3 000 |

> Params: `temperature`/`seed` from `Initialize Parameters`; timeout 300 000 ms.

## Expected output schema

```json
{ "markdown": "string (MUST start with '# Risk Assessment:')" }
```
Required: `markdown`. The markdown body is expected to cover: security risks, data privacy, compliance requirements, technical risks, mitigation strategies.

## Validation criteria (from `Validate Risk`)

- Response JSON must parse (else `{ valid: false, riskMarkdown: '', error: 'JSON parse failed' }`).
- **`valid` requires `markdown` to start with `# Risk Assessment:`**.
- `riskHash` (FNV-1a over the markdown) computed for change detection.
