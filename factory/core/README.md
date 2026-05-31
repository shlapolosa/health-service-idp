# factory/core/

The factory's **central library and toolkit specifications** — the
factory-level state, data, and knowledge that adapters read from and write
back into.

In factory terms: this is the room with the recipe books, the schematics
binders, the tool specifications, and the policy weightings. Operators
(the adapters next door) consult this room; they don't own its contents.

## Contents

| Dir | Role |
|---|---|
| [`knowledge-base/`](./knowledge-base) | Capability knowledge base — capability entries, recipes, schemas, weightings, examples used by the architect, the operator, and the read gateway. |

## What does NOT belong here

- Per-manufacturer state (recipes, M4 capability catalogs) — those live under
  the manufacturer's own dir.
- Adapter implementation code — that lives under `factory/adapters/`.
- Port contracts — those live in the sibling `cafe-spec/` repo (see
  [`../ports/README.md`](../ports/README.md)).
