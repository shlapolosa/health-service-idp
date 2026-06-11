# Analysis Prompt — Data Architecture (ArchiMate)

> **Provenance**
> - Source workflow: `local-ai-packaged/n8n-workflows-refactor/06-architecture-workflow.json`
> - Generation node: `Generate Data Architecture` (httpRequest → `https://ollama.socrates-hlapolosa.org/api/chat`)
> - Validation node: `Validate Data Arch` (code)
> - Downstream: `Convert to ArchiMate XML` maps to `DataObject` / `Artifact`.
> - Extracted: 2026-06-11
> - Status: **DORMANT** (not wired)
> - Confidence: **clean**

## System prompt

```
You are a Data Architect. Output JSON with dataEntities, dataFlows, databases. Map to application dataObjects.
```

## User prompt

```
BRD: {brd_json}
APP_ARCH: {application_arch_json}
```

### Placeholder legend
| Placeholder | n8n origin | Meaning |
|---|---|---|
| `{brd_json}` | `…brd…slice(0,6000)` | Validated BRD (truncated 6 000). |
| `{application_arch_json}` | `…applicationArch…slice(0,8000)` | Output of the application-layer view (truncated 8 000). |

> Third view — "map to application dataObjects" links it to the prior layer. Params: `temperature`/`seed`; timeout 180 000 ms.

## Expected output schema

```json
{
  "dataEntities": ["array"],
  "dataFlows": ["array"],
  "databases": ["array"],
  "relationships": ["array"]
}
```
Required: `dataEntities, dataFlows, databases` (`relationships` optional).

## ArchiMate mapping

`<folder name="Data" type="data">`:

| Source array | ArchiMate `xsi:type` |
|---|---|
| `dataEntities[]` | `archimate:DataObject` |
| `databases[]` | `archimate:Artifact` |
| `dataFlows[]` | `archimate:DataObject` |

## Validation criteria (from `Validate Data Arch`)

Parse-only. Parse failure → `{ valid: false, dataArch: null }`; success → `{ valid: true, dataArch, dataArchHash }`.
