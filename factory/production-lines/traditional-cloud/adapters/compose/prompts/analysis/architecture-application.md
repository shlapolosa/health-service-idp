# Analysis Prompt — Application Architecture (ArchiMate Application Layer)

> **Provenance**
> - Source workflow: `local-ai-packaged/n8n-workflows-refactor/06-architecture-workflow.json`
> - Generation node: `Generate Application Architecture` (httpRequest → `https://ollama.socrates-hlapolosa.org/api/chat`)
> - Validation node: `Validate Application Arch` (code)
> - Downstream: `Convert to ArchiMate XML` maps to `ApplicationComponent`, `ApplicationInterface`, `DataObject`.
> - Extracted: 2026-06-11
> - Status: **DORMANT** (not wired)
> - Confidence: **clean**

## System prompt

```
You are an Application Architect. Output JSON with components, interfaces, dataObjects. Map to business services.
```

## User prompt

```
BRD: {brd_json}
BUSINESS_ARCH: {business_arch_json}
```

### Placeholder legend
| Placeholder | n8n origin | Meaning |
|---|---|---|
| `{brd_json}` | `JSON.stringify($('Collect BRD').first().json.brd).slice(0,8000)` | Validated BRD (truncated 8 000). |
| `{business_arch_json}` | `JSON.stringify($('Validate Business Arch').first().json.businessArch).slice(0,8000)` | Output of the business-layer view (truncated 8 000). |

> Second view in the chain — explicitly "map to business services" (traceability to the prior layer). Original params: `temperature`/`seed`; timeout 180 000 ms.

## Expected output schema

```json
{
  "components": ["array"],
  "interfaces": ["array"],
  "dataObjects": ["array"],
  "relationships": ["array"]
}
```
Required: `components, interfaces, dataObjects` (`relationships` optional).

## ArchiMate mapping

`<folder name="Application" type="application">`:

| Source array | ArchiMate `xsi:type` |
|---|---|
| `components[]` | `archimate:ApplicationComponent` |
| `interfaces[]` | `archimate:ApplicationInterface` |
| `dataObjects[]` | `archimate:DataObject` |

## Validation criteria (from `Validate Application Arch`)

Parse-only. Parse failure → `{ valid: false, applicationArch: null }`; success → `{ valid: true, applicationArch, applicationArchHash }`.
