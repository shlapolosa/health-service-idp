# Analysis Prompt — Business Architecture (ArchiMate Business Layer)

> **Provenance**
> - Source workflow: `local-ai-packaged/n8n-workflows-refactor/06-architecture-workflow.json`
> - Generation node: `Generate Business Architecture` (httpRequest → `https://ollama.socrates-hlapolosa.org/api/chat`)
> - Validation node: `Validate Business Arch` (code)
> - Downstream: `Convert to ArchiMate XML` (code) maps this layer to `archimate:Capability`, `BusinessActor`, `BusinessProcess`, `BusinessService` elements.
> - Extracted: 2026-06-11
> - Status: **DORMANT** (not wired)
> - Confidence: **clean**

## System prompt

```
You are a Business Architect. Output JSON matching ArchiMate business layer schema with capabilities, actors, processes, services. No extra keys.
```

## User prompt

```
BRD: {brd_json}
```

### Placeholder legend
| Placeholder | n8n origin | Meaning |
|---|---|---|
| `{brd_json}` | `JSON.stringify($json.brd).slice(0, 12000)` | The validated BRD JSON (truncated to 12 000 chars) from the BA stage. |

> This is the **first** of a 4-view chain; it depends only on the BRD. The other three views (application/data/infrastructure) are fed this view's output. Original Ollama params: `temperature`/`seed` from `Initialize Parameters`; httpRequest timeout 180 000 ms.

## Expected output schema

```json
{
  "capabilities": ["array"],
  "actors": ["array"],
  "processes": ["array"],
  "services": ["array"],
  "relationships": ["array"]
}
```
Required: `capabilities, actors, processes, services` (`relationships` optional).

## ArchiMate mapping (reusable detail)

`Convert to ArchiMate XML` emits a per-layer `.archimate` file (and a combined `full.archimate`) under `<folder name="Business" type="business">` with element types:

| Source array | ArchiMate `xsi:type` |
|---|---|
| `capabilities[]` | `archimate:Capability` |
| `actors[]` | `archimate:BusinessActor` |
| `processes[]` | `archimate:BusinessProcess` |
| `services[]` | `archimate:BusinessService` |

Element IDs are stable: `id-` + FNV-1a(`<type>:<name>`) — enabling de-duplication across views. `name` is resolved from `item.name` / `item.title` / `item.id` (string or object tolerated).

## Validation criteria (from `Validate Business Arch`)

Minimal: response JSON must parse. On parse failure → `{ valid: false, businessArch: null }`. On success → `{ valid: true, businessArch, businessArchHash }` (FNV-1a). No field-level assertions beyond parseability (the structured-output `format` carries the shape contract).
