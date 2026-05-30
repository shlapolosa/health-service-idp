# Modular webservice CD (S3 refactor)

The original `webservice` ComponentDefinition (in
`../consolidated-core-components.yaml`) accumulated 23 parameters spanning
multiple responsibilities: container shape, bootstrap orchestration,
image-source policy, language enumeration, GraphQL federation,
multi-cluster targeting, realtime-platform integration.

This directory contains the **modular replacement** that splits those
concerns into single-responsibility OAM resources, per the S3 refactor
plan documented in `/Users/socrateshlapolosa/.claude/plans/buzzing-hugging-sunset.md`.

## What's here

| File | Kind | Responsibility |
|---|---|---|
| `webservice-shape.yaml` | ComponentDefinition | ONLY container shape (image, port, probes, resources, env) |
| `auto-scaffold-bootstrap.yaml` | TraitDefinition | Fires oam-driven-contract workflow to scaffold source repo + build pipeline |
| `image-source-policy.yaml` | PolicyDefinition | Validates image registry against an allowlist (catches `nginx:1.27` hallucinations) |
| `language-enum-policy.yaml` | PolicyDefinition | Validates bootstrap language against an allowlist |

## What's NOT here

- GraphQL federation, multi-cluster targeting, realtime-platform integration
  — each of these should be its own opt-in trait, authored separately as
  needed. They were monolith-CD concerns that don't belong on the shape.

## Usage

See `../../examples/webservice-modular-example.yaml` for a complete OAM
Application that uses all four resources.

## Comparison

```yaml
# Monolith — single CD, 23 params, mixed responsibilities
- name: my-svc
  type: webservice
  properties:
    image: ...
    port: 8080
    language: python      # bootstrap concern
    framework: fastapi    # bootstrap concern
    realtime: kafka       # different concern entirely
    enableGraphQLFederation: true   # different concern entirely
    # ... 17 more params

# Modular — shape CD + trait + policies
- name: my-svc
  type: webservice-shape       # ONLY shape
  properties:
    image: ...
    port: 8080
  traits:
    - type: auto-scaffold-bootstrap   # only when scaffolding
      properties:
        language: python
        framework: fastapi
```

## Migration

The existing `webservice` CD remains active and used by all current
applications. The modular path is opt-in. Migration of existing apps is
a separate later effort once architect-v1 prompt + agent-v1 evals are
updated to prefer the modular composition.

## Acid test (per the factory abstractions)

Adding a new language to MFG-TC = updating `language-enum-policy.yaml`
parameter list. **No** CD change. **No** trait change. **No** agent
prompt change. **No** workflow change.

Adding a new image registry = updating `image-source-policy.yaml`.

Adding a NEW bootstrap mechanism (e.g. AI-generated source) = authoring
a sibling TraitDefinition `auto-scaffold-ai-bootstrap`, leaving
`auto-scaffold-bootstrap` untouched. Consumers pick which trait to
attach.

This is what "definition-only extensibility" looks like in practice.
