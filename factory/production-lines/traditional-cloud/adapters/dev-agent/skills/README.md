# dev-agent skills (opencode) — TDD discipline

The dev-agent drives **opencode + GPT-5.4** through a disciplined TDD loop using **opencode skills**
(Anthropic Agent-Skill format). Rather than hand-orchestrating red→green in bash, the discipline lives
in a versioned skill the model invokes; the **enforcement stays external** (the entrypoint's
`check_acceptance` coverage gate + the post-deploy HARD-4 contract test — a skill cannot gate itself).

## What's here
| Skill | Source | Role |
|---|---|---|
| `tdd-acceptance/` | this repo | **entry skill** — binds the TDD discipline to our structured `acceptance` block + `parse_acceptance.py`/`check_acceptance.py`; tells the model which tests to write and how it's gated |
| `test-driven-development/` | vendored from [obra/superpowers](https://github.com/obra/superpowers) (MIT) | RED→GREEN→REFACTOR + Iron Law ("no production code without a failing test first") + testing anti-patterns |
| `verification-before-completion/` | vendored from Superpowers (MIT) | "evidence before claims" — no completion without fresh verification |

Vendored skills are MIT © Jesse Vincent (see `LICENSE.superpowers`). Re-vendor by copying from a pinned
Superpowers checkout; keep this README's source row in sync.

## Wiring into opencode
Skills are **native in opencode** (graduated from the `opencode-skills` plugin): opencode auto-discovers
`SKILL.md` skills and exposes a `skill` tool the model calls; per-agent filtering is supported.
- **Native path (preferred):** the Dockerfile bakes these into opencode's skill discovery directory in
  the image (global, so they're available in headless `opencode run` regardless of the cloned repo).
  Confirm the pinned `OPENCODE_VERSION` includes native skills; bump if not.
- **Fallback (older opencode):** add `"plugin": ["opencode-skills"]` to `opencode.json` and place skills
  under `.opencode/skills/`.

The smoke gate (`tests/dry-run.sh`) must confirm the skill is discoverable and fires under headless
`opencode run` at the pinned version.

## How the loop uses it (entrypoint)
1. For a service with an `acceptance` block, the entrypoint asks opencode to **use the `tdd-acceptance`
   skill** for that service (it pulls in the TDD + verification skills).
2. opencode self-drives RED→GREEN→REFACTOR, writing `microservices/<svc>/tests/test_<id>_*` then the
   implementation.
3. The entrypoint then runs the **external gate**: `pytest --junitxml` → `check_acceptance.py`
   (must be COVERED) → `emit_traceability.py` (writes `TRACEABILITY.md`), then push → post-deploy
   `ct-<rev>` contract test. Iterates within `MAX_ITERATIONS` on a gate failure.
