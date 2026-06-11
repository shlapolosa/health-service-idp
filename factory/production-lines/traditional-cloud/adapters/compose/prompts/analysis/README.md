# Analysis-Pack Prompts (DORMANT)

**Status: DORMANT — these prompts are NOT wired into any runtime path.** They are
documented assets, ported verbatim (cleaned of n8n expression syntax) from the legacy
n8n architecture pipeline. Nothing here is invoked by `app.submit`, architect-v1, the
compose adapter, or any sensor today.

Extracted 2026-06-11 as part of task **N8N-ABSORB** (#174, `dev-agent-factory.md` W0).

## What these are

The legacy pipeline (`local-ai-packaged/n8n-workflows-refactor/`, never deployed in-cluster)
was a 7-stage document factory: use case → BRD → 4-view architecture → solution/reuse
assessment → risk → test strategy → PRD → Taskmaster decomposition. Its mechanics are
superseded by the platform; its **LLM system prompts are the valuable residue**, captured
here one file per artifact:

| File | Artifact | Source workflow |
|---|---|---|
| `brd.md` | Business Requirements Document | `02-business-analysis-workflow.json` |
| `architecture-business.md` | ArchiMate Business layer | `06-architecture-workflow.json` |
| `architecture-application.md` | ArchiMate Application layer | `06-architecture-workflow.json` |
| `architecture-data.md` | ArchiMate Data layer | `06-architecture-workflow.json` |
| `architecture-infrastructure.md` | ArchiMate Technology layer | `06-architecture-workflow.json` |
| `solution-reuse-assessment.md` | Solution package + reuse/change tickets | `05a-solution-architecture-workflow.json` |
| `risk-assessment.md` | Security/risk assessment | `05b-risk-assessment-workflow.json` |
| `test-strategy.md` | Test strategy + scenarios (QA package) | `05c-test-strategy-workflow.json` |
| `prd.md` | PRD (RPG Method) | `04-project-management-workflow.json` |

Each file carries: provenance header (source file + node names + extraction date),
the cleaned system prompt, the user prompt with a `{placeholder}` legend, the expected
output schema, and the matching `Validate X` node's criteria.

## How W5 will wire them (future, not now)

Per `factory/docs/plans/dev-agent-factory.md` **W5 — analysis pack (optional depth)**:

> architect-v1 gains an opt-in **"deep analysis" mode** generating the 4-view
> architecture + risk + test-strategy docs into `docs/analysis/` of the monorepo.
> Not on the critical path; exists because the prompts are already written and
> enterprise consumers will ask for them.

Concretely, when W5 lands these become the prompt bodies for an architect-v1 deep-analysis
toggle: the placeholders map to artifacts architect-v1 already has in hand (the REQUIREMENTS.md
spec, the composed OAM, catalog reuse hits), generation runs on **Foundry architect-v1**
(not Ollama), validation reuses architect-v1's existing `validate.*` pattern (the
"validate-after-generate" discipline these `Validate X` nodes embody), and the rendered
docs are committed to the monorepo `docs/analysis/` by mscv / FactoryBot. The critical path
(use case → OAM + REQUIREMENTS.md → dev-agent) is unchanged; this is additive depth only.

## What was deliberately dropped (and why)

Per the supersession table in `dev-agent-factory.md`, the following n8n mechanics were
**intentionally not ported** — the platform already provides them better:

| Dropped | Why (superseded by) |
|---|---|
| **Postgres job/artifact/project state** (`Upsert Project`, `Create * Job`, `Store * Artifact`, `Update Job Status`) | intake ledger + Crossplane claims / ArgoCD conditions + OAM `lifecycle.state` |
| **SSH + git artifact commits** (`Build Git Script`, `SSH: Commit *`) | mscv / Socrates-FactoryBot GitHub App |
| **Ollama specifics** (`ollamaModel`/`ollamaTemperature`/`ollamaSeed`, structured-output `format`, `nomic-embed-text` embeddings, `https://ollama.socrates-hlapolosa.org`) | Foundry architect-v1 for generation (and Claude for the dev-agent) |
| **Qdrant `existing-landscape` vector search** (the reuse mechanic in `05a`) | catalog MCP `kb.*` / `examples.*` + reuse→repurpose→create prompts |
| **webhook intake + classify + slugify** | slack-api-server → `app.submit` + architect-v1 |
| **The 7-stage waterfall + Taskmaster hand-off** | lean v1 compresses to architect → OAM + REQUIREMENTS.md; the dev-agent runs task-master against REQUIREMENTS.md |

The Ollama generation params (`temperature`/`seed`) and char-truncation limits are noted in
each file **for fidelity only** — they document the original deterministic behaviour and are
expected to be re-tuned (or dropped) when re-homed on Foundry.

## Reusable findings worth keeping

- **ArchiMate element mapping** (`architecture-*.md`): a complete source-array → `archimate:xsi:type`
  map producing Archi-tool-native `.archimate` files (Business/Application/Data/Technology folders +
  Relations), with **stable FNV-1a element IDs** (`id-` + hash(`type:name`)) enabling cross-view
  de-duplication. Directly reusable if the deep-analysis mode emits diagrammable models.
- **Reuse signal** (`solution-reuse-assessment.md`): the `participantMap` (`exists` @ score>0.65,
  `isInternal`, resolved endpoint/port/tables) is the same reuse→repurpose→create decision the
  platform's catalog MCP now makes — the *ticket* schema (`componentStatus: exists|needs_change|new_required`)
  is a clean shape for change assessment.
- **RPG-Method PRD** (`prd.md`): Capability Tree / Repository Structure / Module Definitions /
  Dependency Chain sections are a ready-made task-decomposition scaffold for the dev-agent.
- **Validate-after-generate** discipline: every stage asserts a structural anchor (a required
  `# Heading:` prefix or required keys) — the pattern architect-v1's `validate.*` already follows.

## Constraints honoured

- Read-only against `local-ai-packaged` — nothing there was modified.
- No secrets/tokens were present in the prompts; the only URL (`ollama.socrates-hlapolosa.org`)
  is public and retained in provenance headers only.
