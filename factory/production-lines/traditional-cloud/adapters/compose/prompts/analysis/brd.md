# Analysis Prompt — Business Requirements Document (BRD)

> **Provenance**
> - Source workflow: `local-ai-packaged/n8n-workflows-refactor/02-business-analysis-workflow.json`
> - Generation node: `Generate BRD` (httpRequest → `https://ollama.socrates-hlapolosa.org/api/chat`)
> - Validation node: `Validate BRD` (code)
> - Render node: `Render BRD.md` (code) — Markdown layout reproduced under "Rendered output layout"
> - Extracted: 2026-06-11
> - Status: **DORMANT** (not wired — see `README.md` in this directory)
> - Confidence: **clean**

## System prompt

```
You are a Business Analyst. Output ONLY JSON that matches the schema. No markdown.
```

## User prompt

```
{requirements}
```

### Placeholder legend
| Placeholder | n8n origin | Meaning |
|---|---|---|
| `{requirements}` | `$('Initialize Parameters').first().json.requirements` | The raw use-case / requirements text submitted by the user. |

> Original n8n generation parameters (carried for fidelity, drop when re-homing on Foundry): `temperature` and `seed` were sourced from `Initialize Parameters` (`ollamaTemperature`, `ollamaSeed`) for deterministic re-runs.

## Expected output schema

The n8n node enforced this via Ollama structured-output `format` (JSON schema, `additionalProperties: false`):

```json
{
  "type": "brd",
  "title": "string",
  "version": "string",
  "executiveSummary": "string",
  "problemStatement": {
    "currentState": "string",
    "painPoints": ["string"],
    "impact": "string"
  },
  "businessObjectives": ["array"],
  "stakeholders": ["array"],
  "scope": { "object — inclusions/exclusions (a.k.a. inScope/outOfScope)" },
  "constraints": ["array"],
  "assumptions": ["array"],
  "successCriteria": ["array"]
}
```

Required keys: `type, title, version, executiveSummary, problemStatement, businessObjectives, stakeholders, scope, constraints, assumptions, successCriteria`.

## Validation criteria (from `Validate BRD`)

A BRD is **valid** only if all of the following hold (else the listed error is recorded):
- JSON parses (else `BRD JSON parse failed: <msg>`)
- `type === 'brd'` (else `type must be brd`)
- `title` present (else `title is required`)
- `executiveSummary` present (else `executiveSummary is required`)
- `problemStatement` present (else `problemStatement is required`)
- `businessObjectives` is an array (else `businessObjectives must be array`)
- `stakeholders` is an array (else `stakeholders must be array`)
- `scope` present (else `scope is required`)

A content hash (`brdHash`, FNV-1a over the canonical JSON) is computed for change detection.

## Rendered output layout (`Render BRD.md`)

The validated BRD JSON was rendered to `BRD.md` with this section order:

1. `# Business Requirements Document: {projectName}`
2. `## Executive Summary`
3. `## Problem Statement` → `### Current State`, `### Pain Points` (bulleted), `### Impact`
4. `## Business Objectives` (each: `description (Metric: …) [Target: …]`)
5. `## Success Metrics (KPIs)` (each: `description [Target: …]`)
6. `## Stakeholders` (each: `**name**: description` + nested `Requirements:`)
7. `## Constraints & Assumptions` → `### Constraints` (`description (Impact: …)`), `### Assumptions` (`description (Rationale: …)`)
8. `## Scope` → `### In Scope` (`scope.inclusions` | `scope.inScope`), `### Out of Scope` (`scope.exclusions` | `scope.outOfScope`)

The renderer tolerated both string and object array entries (e.g. a stakeholder could be `"Ops team"` or `{name, description, requirements[]}`).
