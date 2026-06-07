# GQL-1 — First-class GraphQL gateway in the OAM-driven platform (#155)

Status: PLAN (implementation-ready). Branch: `worktree-agent-a960b5819c6490d9e`.
Goal (user's words): "make graphql expose current services — if possible auto-discover
or add as part of config." When a `graphql-gateway` component is declared in an OAM it
must (1) scaffold from the existing template via the claim path, (2) deploy zero-touch
like webservices do (proven by the patient5 3-service monorepo), and (3) expose the
OAM's sibling webservices through a single GraphQL endpoint.

---

## 1. Empirical findings (research, not assumptions)

### 1.1 What `graphql-gateway.cd.yaml` renders today (post-#152)
`factory/production-lines/traditional-cloud/adapters/catalog/graphql-gateway.cd.yaml`
is a Knative-Service shape CD. Per OAM `graphql-gateway` component it renders:

- **`output`**: a Knative `Service` named `context.name`, image
  `docker.io/socrates12345/<name>:latest`, `serviceAccountName: graphql-gateway-sa`,
  a `gateway-config` ConfigMap volume mount, `minScale: 1`, health on **`/healthz`**.
  Env injected: `SERVICE_SELECTOR_LABELS` (from `parameter.serviceSelector`),
  `exposeIntrospection`, `exposePlayground`, resources.
- **`outputs.graphql-infrastructure`**: a ConfigMap (`<name>-config`) carrying
  `serviceSelector`, `exposeIntrospection`, `exposePlayground`, resources.
- **`outputs.istio-virtualservice`** + gateway: only when `enableIstioGateway: true`.
- **`scaffold-claim`** (RETIRE-WFT-2, #152): an `AppContainerClaim` (kind
  `platform.example.org/v1alpha1`) named `context.name`, with `language: nodejs`,
  `framework: graphql-gateway`, `gitHubOrg: shlapolosa`,
  `dockerRegistry: healthidpuaeacr.azurecr.io`, `deliveryTarget` from
  `targetEnvironment` else `host`. Gated on `parameter.language != _|_`.

Parameters: `version`, `serviceSelector` (default `{graphql.federation/enabled:"true"}`),
`autoSchema`, `schemaRefreshInterval`, `exposeIntrospection`, `exposePlayground`,
`enableCors`, `resources`, `environment`, `envFrom`, `language?`, `framework?`,
`repository?`, `customResolvers?`, `enableIstioGateway?`, `gatewayHost?`,
`configMapName?`, `targetEnvironment?`.

### 1.2 The template (`shlapolosa/graphql-federation-gateway-template`)
`microservices/graphql-gateway/`:
- **Stack**: Node ≥16, Express + `express-graphql`, **GraphQL Mesh**
  (`@graphql-mesh/cli@0.100`, `@graphql-mesh/openapi@1.0`,
  `@graphql-mesh/runtime@0.106`, `transform-prefix`, `transform-naming-convention`),
  `@graphql-tools/stitch`. `js-yaml`, `node-fetch`.
- **Discovery is RUNTIME via `kubectl`** (`src/service-discovery.js`): it
  `spawn('kubectl', ['get','ksvc',...])` filtered by `SERVICE_SELECTOR_LABELS`, then
  **only includes services annotated `graphql.federation/enabled: "true"`**, then for
  each probes a list of OpenAPI paths (`/openapi.json`, `/api/openapi.json`,
  `/v1/openapi.json`, `/docs/openapi.json`, ...) over
  `http://<name>.<ns>.svc.cluster.local`, and feeds the discovered spec URLs into a
  GraphQL Mesh `openapi` handler (one source per service, prefixed by service name).
- **Mesh config**: `mesh-config-template.yaml` + `generate-mesh-config.sh`
  (also shell `kubectl`-based) populate `sources[]` with
  `handler.openapi.source: http://<svc>.<ns>.svc.cluster.local:8080/openapi.json`.
  At runtime `src/mesh-manager.js` regenerates `.meshrc.yml` and rebuilds the mesh on a
  `DISCOVERY_INTERVAL` loop (`src/discovery-loop.js`).
- **HTTP surface** (`src/gateway-server.js`): `/graphql`, **`/healthz`**, `/readyz`,
  `/status`, `/metrics`, `POST /api/discovery/force`, `/`. **No `/health`,
  no `/openapi.json`** — diverges from the platform contract used by the python/java
  templates (which serve `/health` + `/openapi.json`).
- **Dockerfile**: multi-stage, non-root, `HEALTHCHECK` on `/healthz`. Entry
  `src/index.js`. Same build shape patient5 used.

### 1.3 Confirmed: GraphQL Mesh openapi handler CAN auto-build the graph
The Mesh `openapi` handler pointed at each sibling's `/openapi.json` auto-generates the
federated schema — exactly the KEY QUESTION. Every platform webservice serves
`/openapi.json` (FastAPI default; platform contract). So **no per-service schema authoring
is needed** — the graph is generated from the OpenAPI specs.

### 1.4 The binding contract & monorepo machinery we reuse
- `webservice-shape.yaml`: `database:`/`cache:`/`identity:` refs → `envFrom <ref>-conn`
  secretRef (optional). This is the wire shape we mirror for `sources:`.
- `expose-api.yaml` (BIND-2/EVENT-2 #151): stamps the ksvc with
  `expose-api.cafe.io/*` annotations; a substrate sensor fires an APIM-publish Job when
  the ksvc reports Ready. Carries `identity` (validate-jwt) wiring.
- UNIFY-1 (#153) `app-container-claim-xrd.yaml`: `spec.services[]`
  (`{name, language[python|java|rasa|nodejs], framework?}`); composition emits one
  `ApplicationClaim` per entry sharing one repo; `nodejs→graphql-gateway` derivation
  exists. `submit_use_case.py::_webservice_services()` derives `services[]` from EVERY
  `type: webservice` component with `language:` set and no/default image.
  **Critical gap**: that derivation keys on `type == "webservice"` only — a
  `type: graphql-gateway` component is NOT currently added to `services[]`, so it does
  NOT get scaffolded into the monorepo today.

---

## 2. Chosen discovery mechanism

**Decision: (a) explicit `sources:` on the component, render-injected by `app.submit`,
backed by the existing (b) runtime annotation-discovery as a zero-config fallback.**

Rationale in three sentences: The CD's CUE template can only see its own component's
params (not siblings), so a pure render-time graph (option c) is impossible without
`app.submit` injecting the sibling list — and `app.submit` already walks every component
for UNIFY-1, so adding a one-line derivation of the gateway's `sources:` is nearly free
and gives a deterministic, declarative, reviewable wire. We keep the template's existing
runtime `kubectl`+annotation discovery (option b) as the fallback/auto path so a gateway
declared with no `sources:` still federates anything labelled
`graphql.federation/enabled`, but we make the **explicit list authoritative when present**
(it pins exact in-cluster URLs and removes the cold-start race where siblings aren't Ready
yet). This is the reuse→repurpose→create principle: reuse the template's discovery engine,
repurpose `app.submit`'s component walk, create only a thin `sources:` env contract.

Net: declarative + reviewable (explicit), zero-touch (auto fallback), no new k8s-API code
in the gateway beyond the `kubectl` it already has.

---

## 3. Wire shape — OAM example

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: patient7
spec:
  components:
    - name: patient-api
      type: webservice
      properties:
        language: python          # scaffolds microservices/patient-api (FastAPI)
        identity: patient7-auth
        # serves /openapi.json + /health by platform contract
    - name: appointments-api
      type: webservice
      properties:
        language: python
        identity: patient7-auth
    - name: patient7-auth
      type: auth0-idp
    - name: patient7-graph
      type: graphql-gateway
      properties:
        language: nodejs          # triggers scaffold-claim → graphql template
        sources:                  # NEW: explicit sibling list (app.submit can auto-fill)
          - patient-api
          - appointments-api
        identity: patient7-auth   # NEW: pass-through Authorization to upstreams
      traits:
        - type: expose-api        # one public GraphQL endpoint, APIM in front
          properties:
            apiPathPrefix: /patient7/graphql
            identity: patient7-auth
```

`sources` accepts either bare component names (resolved to
`http://<name>.<ns>.svc.cluster.local:8080/openapi.json`) or full URL objects for
external/custom upstreams (maps to the template's existing `customResolvers`).

---

## 4. CD changes (`graphql-gateway.cd.yaml`)

R = reuse, C = change, N = new.

1. **(N) `sources?` parameter**: `sources?: [...( string | {name:string, url?:string, openApiPath?:string, headers?:{[string]:string}} )]`.
2. **(C) Render `sources` into the gateway-config ConfigMap** (`outputs.graphql-infrastructure`)
   as a JSON/YAML `MESH_SOURCES` key, AND as a `MESH_SOURCES` env on the ksvc. Shape:
   `[{name, source:"http://<name>.<ns>.svc.cluster.local:8080/openapi.json"}]` for bare
   names; pass `url`/`openApiPath`/`headers` through for object form. Use
   `context.namespace` for the FQDN.
3. **(C) Set `EXPLICIT_SOURCES=true`** env when `sources` is non-empty so the template
   prefers the explicit list over annotation-discovery.
4. **(N) `identity?` parameter + envFrom** mirroring webservice-shape: when set, add
   `envFrom: [{secretRef:{name: identity+"-conn", optional:true}}]` to the gateway
   container so the gateway can read JWT issuer config (`JWT_ISSUER_URI` etc.) for
   pass-through validation if desired. Keep `database?`/`cache?` parity optional (low cost).
5. **(R) `scaffold-claim`** stays as-is (already emits the nodejs/graphql-gateway claim).
   No change needed for the claim itself.
6. **(C) Health contract alignment**: keep `/healthz` probes in the CD only if the
   template keeps `/healthz`; preferred is to add `/health` to the template (see §5) and
   switch CD probes to `/health` to match every other shape. Decide together with §5.

No Argo workflow, no curl-Job: the claim path (proven zero-touch) carries scaffolding.

---

## 5. Template changes (`graphql-federation-gateway-template`)

1. **(C) Env-driven explicit sources**: in `src/service-discovery.js` /
   `src/mesh-manager.js`, when `EXPLICIT_SOURCES=true` and `MESH_SOURCES` is set, build
   the Mesh `sources[]` directly from that JSON (skip the `kubectl` walk). When unset,
   keep today's `kubectl get ksvc` + `graphql.federation/enabled` annotation discovery
   as fallback. This removes the gateway's hard dependency on cluster RBAC for the common
   case and kills the cold-start race.
2. **(C) Contract compliance — add `/health` and `/openapi.json` aliases**
   (`src/gateway-server.js`): alias `/health` → existing `/healthz` handler; serve
   `/openapi.json` (the gateway can expose its own minimal OpenAPI, or 200 with a stub) so
   it satisfies the same probe/expose-api contract as python/java templates and so a
   future gateway-of-gateways could federate it.
3. **(R) GraphQL Mesh openapi handler**: unchanged — it already auto-generates the graph
   from each `/openapi.json`. This is the load-bearing reuse.
4. **(N) Authorization pass-through**: set Mesh `operationHeaders.Authorization:
   "{context.headers.authorization}"` on each `openapi` source so the incoming JWT flows
   to upstreams. Drive on/off by a `FORWARD_AUTH=true` env (default true).
5. **(R) Dockerfile / entrypoint / non-root**: unchanged; already patient5-compatible.
6. **(C) RBAC**: when explicit sources are used, the `graphql-gateway-sa`'s `kubectl`
   RBAC (list ksvc) becomes optional. Keep the existing Role/RoleBinding for the fallback
   path but document that explicit-sources gateways need none.

---

## 6. Submit-side changes (`submit_use_case.py`)

1. **(C) Scaffold the gateway into the monorepo**: extend `_webservice_services()` (or add
   a sibling helper) so a `type: graphql-gateway` component WITH `language: nodejs` is
   appended to `services[]` as `{name, language:"nodejs", framework:"graphql-gateway"}`.
   This makes the gateway scaffold into `microservices/<name>/` of the shared OAM repo
   exactly like webservices — the zero-touch path. (Today it is skipped because the walk
   keys on `type == "webservice"`.)
2. **(N, optional) Auto-fill `sources:`**: when a `graphql-gateway` component omits
   `sources`, derive it from the OAM's `type: webservice` component names and inject it
   into the component properties before render (the only place that can see siblings).
   This delivers "auto-discover or add as part of config" with config as the default and
   auto as the convenience.
3. **(R) Identity invariant**: the existing exposed-webservice→single-identity check
   already covers the gateway when it carries `expose-api`; no change beyond ensuring the
   gateway's `identity:` points at the same component.
4. `SubmitResult` shape and tool signatures unchanged (additive only).

---

## 7. Identity flow

- One **public** GraphQL endpoint: the gateway component carries the `expose-api` trait →
  EVENT-2 sensor publishes `/<prefix>/graphql` to APIM with `validate-jwt` bound to the
  OAM's single `auth0-idp` identity component. APIM is the only externally reachable door.
- The gateway **forwards `Authorization`** to each upstream (Mesh `operationHeaders`,
  §5.4). Upstreams keep their own `identity:` binding; they remain in-cluster only.
- The gateway itself does NOT need to re-validate the JWT (APIM already did) but MAY read
  `<identity>-conn` (§4.4) if we later want defense-in-depth. Recommend: APIM validates,
  gateway forwards, upstreams trust the mesh — matches the existing webservice posture.

---

## 8. Zero-touch test design (patient7)

Mirror the patient5 3-service monorepo proof.

1. **Fixture**: a `patient7` OAM (§3) = 2 python webservices (`patient-api`,
   `appointments-api`, each `language: python`, serving `/openapi.json`), 1 `auth0-idp`
   (`patient7-auth`), 1 `graphql-gateway` (`patient7-graph`, `language: nodejs`,
   `sources:[patient-api, appointments-api]`, `expose-api`).
2. **Submit** via `app.submit` (or the consumer OAM path). Expect ONE
   `AppContainerClaim` named `patient7` with `services[]` = the 2 python services **plus**
   `patient7-graph` (nodejs/graphql-gateway) — assert the gateway is in `services[]`.
3. **Scaffold assertion**: shared repo `patient7` gets
   `microservices/{patient-api,appointments-api,patient7-graph}/`; CI builds all three
   images zero-touch (no manual trait, like patient5).
4. **Deploy assertion**: 3 ksvcs Ready; `patient7-graph` ConfigMap carries `MESH_SOURCES`
   with both sibling FQDNs; `EXPLICIT_SOURCES=true`.
5. **Federation assertion**: `POST /graphql` on the gateway returns a schema containing
   `PatientApi_*` and `AppointmentsApi_*` types/queries auto-generated from the two
   `/openapi.json`s. `/health` and `/openapi.json` on the gateway return 200.
6. **Identity assertion**: external call to the APIM `/patient7/graphql` route without a
   JWT is 401; with a valid JWT it succeeds and the `Authorization` header reaches the
   upstreams (assert via upstream log / echo).
7. **Auto-discovery fallback test**: a second gateway with NO `sources:` but siblings
   annotated `graphql.federation/enabled` still federates them (proves option b path).
8. Encode as a CI/e2e script analogous to the patient5 harness; keep it re-runnable.

---

## 9. Reuse → repurpose → create ledger

| Piece | Verdict |
|---|---|
| GraphQL Mesh openapi handler (auto-graph from `/openapi.json`) | **REUSE** — load-bearing, no change |
| Template Dockerfile / non-root / entrypoint | **REUSE** |
| `scaffold-claim` (AppContainerClaim nodejs/graphql-gateway) | **REUSE** (#152 already did it) |
| UNIFY-1 monorepo `services[]` + composition | **REUSE** machinery, **CHANGE** one derivation to include the gateway |
| webservice-shape `identity:`/`envFrom <ref>-conn` pattern | **REPURPOSE** for the gateway's `identity:`/`sources:` |
| expose-api / EVENT-2 / APIM validate-jwt | **REUSE** for the single public endpoint |
| Template runtime `kubectl` discovery | **REPURPOSE** as fallback; **CHANGE** to honour `MESH_SOURCES` first |
| `/health` + `/openapi.json` on gateway | **CREATE** (aliases, contract compliance) |
| `MESH_SOURCES` env/ConfigMap wire + `sources:` param | **CREATE** (thin) |

No new CRD, no new CD, no new workflow. Everything composes on proven spines.

---

## 10. Risks

- **R1 Cold-start race (mitigated)**: explicit `MESH_SOURCES` + Mesh `openapi` handler
  retry; gateway `minScale:1` already set. Fallback path must tolerate not-yet-Ready
  upstreams (skip + retry on the discovery loop) — verify, don't regress.
- **R2 Health-path contract drift**: CD currently probes `/healthz`, rest of platform
  uses `/health`. Decide §4.6/§5.2 together; pick one to avoid a probe mismatch on deploy.
- **R3 GraphQL Mesh version pinning**: pinned `@graphql-mesh/*` 0.10x is old; the openapi
  handler API may differ from current Mesh. Verify against context7 before editing the
  template; do NOT bump blindly (patient5 image built on these pins).
- **R4 Auth pass-through**: forwarding `Authorization` to every upstream is correct only
  if all upstreams trust the same issuer; the single-identity invariant (§7) enforces
  this. If a gateway federates services across identities, block at submit-time.
- **R5 submit derivation scope**: adding `graphql-gateway` to `services[]` must NOT break
  the existing exposed-webservice→single-identity check or the single-service backward
  compat path. Cover both in tests.
- **R6 RBAC for fallback**: annotation-discovery needs `graphql-gateway-sa` list-ksvc
  RBAC; ensure it exists in the target namespace or the fallback silently federates
  nothing. Explicit-sources path avoids this.

---

## 11. Effort estimate

| Workstream | Effort |
|---|---|
| CD: `sources`/`identity`/`MESH_SOURCES`/probe params (§4) | 0.5 day |
| Template: env-driven sources + `/health`+`/openapi.json` + auth pass-through (§5) | 1.5 days (incl. local Mesh smoke per memory rule) |
| submit: gateway→`services[]` + auto-fill `sources` (§6) | 0.5 day |
| patient7 e2e harness + zero-touch run (§8) | 1 day |
| Mesh-version verification (context7) + RBAC/contract reconciliation (R2/R3/R6) | 0.5 day |
| **Total** | **~4 days** |

Template-readiness verdict: **needs changes** (4 concrete: env-driven explicit sources,
`/health`+`/openapi.json` aliases, Authorization pass-through, prefer `MESH_SOURCES`
over kubectl). The auto-graph-from-OpenAPI core works as-is.

---

## ADDENDUM (post-plan, 2026-06-07): existing implementation reconciliation

USER DIRECTIVE: "there was already a graphql implementation — analyse and enhance."
See companion doc `gql-1-existing-implementation-analysis.md`. Material impacts on this plan:

1. **The discovery engine exists TWICE**: in the template repo (this plan's basis) AND
   vendored at `factory/substrate/crossplane/graphql/mesh-gateway/src/` (service-discovery.js
   kubectl walk + discovery-loop + schema-generator). Consolidate to ONE copy (template repo
   is the right home; substrate copy becomes dead after the CD scaffolds from template).
2. **TWO competing XRDs** (`xgraphqlplatformclaims` vs `xgraphqlplatforms`) — consolidate
   to the active one; delete the duplicate + `graphql-platform-component.yaml` + the manual
   configmap + legacy `generate-mesh-config.sh` bash variant (dead per analysis).
3. **Hasura decision point**: CLAUDE.md TODO #4 chose Hasura, but the shipped engine is
   GraphQL Mesh over OpenAPI; the hasura-backup composition is a non-functional skeleton.
   This plan formally RECOMMENDS Mesh-over-OpenAPI as the platform engine (it matches the
   binding contract + /openapi.json platform contract); Hasura remains a possible future
   `database-graphql` component for direct-Postgres exposure — separate, not GQL-1.
4. Work items absorbed into Phase 1: consolidation/deletion list from the analysis doc.

---

## IMPLEMENTED (2026-06-07)

Branch `worktree-agent-a6b440bc18dc840d2`. All four workstreams shipped + consolidation.

### 1. submit gap + sources injection (`submit_use_case.py`)
- `_SCAFFOLD_TYPES = ("webservice", "graphql-gateway")`; `_webservice_services()` now
  appends `type: graphql-gateway` components with `language: nodejs` as
  `{language:"nodejs", framework:"graphql-gateway"}` → the gateway scaffolds into the
  monorepo zero-touch like a webservice.
- New static `_inject_graphql_sources(app, ns, oam_yaml)`: for any graphql-gateway
  component WITHOUT explicit `sources:`, injects sibling webservice components as
  `sources: [{name, url: http://<name>.<ns>.svc.cluster.local, specPath: /openapi.json}]`
  into the component properties BEFORE the gitops commit. Explicit sources are left
  authoritative; no-webservice OAMs leave it to the runtime fallback. Wired into both
  `submit()` and `submit_wait()`.
- Tests: 6 new in `tests/test_submit_routing.py` (gateway-in-services, auto-inject,
  explicit-preserved, no-webservices-no-inject, byo-image-excluded, e2e-commit). Full
  capability-mcp-core suite green: **80 passed**.

### 2. CD enhancement (`graphql-gateway.cd.yaml`)
- `import "encoding/json"` (proven safe on this platform — neon-postgres.cd.yaml uses
  `import "encoding/base64"`).
- New params: `sources?` (bare string | {name,url?,openApiPath?,headers?}), `identity?`,
  `database?`, `cache?`. Computed internal `_meshSources` normalizes each entry to
  `{name, source, headers?}`.
- Renders `MESH_SOURCES` env (JSON via `json.Marshal`), `EXPLICIT_SOURCES=true`,
  `FORWARD_AUTH=true` (when identity set). envFrom `<ref>-conn` (optional:true) for
  identity/database/cache — binding-contract parity with webservice.cd.yaml.
- Probes switched `/healthz` → `/health`.
- Validated with `vela dry-run --offline`: Service+GraphQLPlatformClaim+AppContainerClaim
  all render; MESH_SOURCES JSON + envFrom + probes correct; no-sources gateway compiles
  with no MESH_SOURCES (pure fallback).
- NOTE/simplification: MESH_SOURCES is rendered as an ENV only (the template reads env),
  NOT also into the gateway-config ConfigMap — that would require changing the
  GraphQLPlatformClaim XRD/composition; env is sufficient and the template honours it.

### 3. Consolidation (deleted dead, per analysis doc)
DELETED: `factory/substrate/crossplane/graphql-platform-component.yaml`,
`graphql-gateway-configmap.yaml`, `compositions/graphql-platform-composition.yaml`
(duplicate `XGraphQLPlatform`/`xgraphqlplatforms` XRD — ACTIVE one kept:
`graphql-platform-claim-xrd.yaml`, kind `GraphQLPlatformClaim`, which the CD emits),
and the entire `graphql/mesh-gateway/` substrate copy (engine, legacy `server*.js`,
bash `generate-mesh-config.sh`, mesh-config-template, package-simple — the federation
engine now lives ONLY in the template repo, its correct home). The retired Argo WFT
`execute/workflow-templates/graphql-gateway-template.yaml` was already absent.
ANNOTATED (not deleted): `graphql-platform-claim-composition-hasura-backup.yaml` marked
DEFERRED (future `database-graphql` candidate). KEPT: active claim XRD+composition,
`graphql/schema-discovery/` (used only by hasura-backup), examples, rbac.

### 4. Template changes (`graphql-federation-gateway-template`, commit d992733, NOT pushed)
- `mesh-manager.js`: `applyExplicitSources()` builds the Mesh from `MESH_SOURCES` JSON
  (deriving baseUrl = host root of the spec URL) and bypasses kubectl discovery;
  `buildOperationHeaders()` forwards `Authorization: {context.headers.authorization}`
  when `FORWARD_AUTH != false`.
- `gateway-server.js`: `EXPLICIT_SOURCES` gate skips the discovery loop; adds `/health`,
  `/ready`, `/openapi.json` (platform contract; `{status:"healthy",service:<name>}`)
  alongside legacy `/healthz`,`/readyz`.
- `start.sh`: short-circuits to `node src/index.js` when `EXPLICIT_SOURCES=true`
  (no kubectl, no bash discovery layer).
- Probes: `knative-service.yaml` + Dockerfile HEALTHCHECK → `/health`.
- Validation: `node --check` green on all changed JS; standalone smoke of the
  MESH_SOURCES parse/baseUrl/auth/prefix logic passed. `bash -n start.sh` clean.

### Deferred / not done (with reasons)
- **No patient7 e2e harness (§8)**: requires a live cluster (no kubectl/az allowed in
  this run). Submit-side covered by unit tests; CD by offline vela dry-run; template by
  node --check + logic smoke.
- **Template push**: committed locally only (orchestrator pushes after review).
- **Pre-existing template bug**: `src/schema-generator.js` line 81 has a latent syntax
  error (`'';\n` literal) — NOT introduced here, NOT on the explicit-sources path; flag
  for separate fix.
- **MESH_SOURCES in ConfigMap**: env-only (see §2 NOTE).
- **GraphQL Mesh version pinning (R3)**: pins left untouched (patient5 image built on
  them); not bumped.
