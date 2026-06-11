# Analysis Prompt — Infrastructure / Technology Architecture (ArchiMate)

> **Provenance**
> - Source workflow: `local-ai-packaged/n8n-workflows-refactor/06-architecture-workflow.json`
> - Generation node: `Generate Infrastructure Architecture` (httpRequest → `https://ollama.socrates-hlapolosa.org/api/chat`)
> - Validation node: `Validate Infrastructure Arch` (code)
> - Downstream: `Convert to ArchiMate XML` maps to `Node`, `CommunicationNetwork`, `SystemSoftware`, `Artifact` under the Technology layer.
> - Extracted: 2026-06-11
> - Status: **DORMANT** (not wired)
> - Confidence: **clean**

## System prompt

```
You are an Infrastructure Architect. Output JSON with nodes, networks, deployments, artifacts. Map to application components.
```

## User prompt

```
BRD: {brd_json}
APP_ARCH: {application_arch_json}
DATA_ARCH: {data_arch_json}
```

### Placeholder legend
| Placeholder | n8n origin | Meaning |
|---|---|---|
| `{brd_json}` | `…brd…slice(0,5000)` | Validated BRD (truncated 5 000). |
| `{application_arch_json}` | `…applicationArch…slice(0,6000)` | Application-layer view (truncated 6 000). |
| `{data_arch_json}` | `…dataArch…slice(0,5000)` | Data-layer view (truncated 5 000). |

> Fourth and final view — consumes BRD + application + data layers; "map to application components". Params: `temperature`/`seed`; timeout 180 000 ms.

## Expected output schema

```json
{
  "nodes": ["array"],
  "networks": ["array"],
  "deployments": ["array"],
  "artifacts": ["array"],
  "relationships": ["array"]
}
```
Required: `nodes, networks, deployments, artifacts` (`relationships` optional).

## ArchiMate mapping

`<folder name="Technology" type="technology">`:

| Source array | ArchiMate `xsi:type` |
|---|---|
| `nodes[]` | `archimate:Node` |
| `networks[]` | `archimate:CommunicationNetwork` |
| `deployments[]` | `archimate:SystemSoftware` |
| `artifacts[]` | `archimate:Artifact` |

> The combined `full.archimate` concatenates all four folders (Business, Application, Data, Technology) plus an empty `<folder name="Relations" type="relations">`. Model header:
> `<archimate:model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:archimate="http://www.archimatetool.com/archimate" name="{projectName}" id="…">` — i.e. the open-source **Archi** tool's native `.archimate` format, openable in Archi for diagramming.

## Validation criteria (from `Validate Infrastructure Arch`)

Parse-only. Parse failure → `{ valid: false, infraArch: null }`; success → `{ valid: true, infraArch, infraArchHash }`.
