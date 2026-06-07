# GQL-1 Existing GraphQL Implementation — Analyze & Enhance Context

The plan MUST be analyze-and-enhance. A substantial GraphQL gateway already exists and is wired
into the **current** declarative (CD/no-WFT) world. Do not greenfield.

## 1. What each artifact does

### `graphql-gateway.cd.yaml` (CURRENT, LIVE — the spine)
`factory/production-lines/traditional-cloud/adapters/catalog/graphql-gateway.cd.yaml`
This is the active ComponentDefinition `graphql-gateway` (OAM `core.oam.dev/v1beta1`), shape
`knative-service`, `requires-source-code: "false"`. CUE template emits:
- **Primary `output`**: a Knative `Service` named `context.name`, image
  `docker.io/socrates12345/<context.name>:latest`, port 8080, mounts `gateway-config` ConfigMap,
  env: `GATEWAY_NAME`, `NAMESPACE`, `SERVICE_SELECTOR_LABELS="graphql.federation/enabled=true"`,
  `AUTO_DISCOVERY`, `DISCOVERY_INTERVAL`. minScale 1 / maxScale 10.
- **Secondary `outputs["graphql-infrastructure"]`**: a `GraphQLPlatformClaim`
  (`platform.example.org/v1alpha1`) named `<name>-infrastructure`, ALWAYS created — passes
  serviceSelector, autoSchema, schemaRefreshInterval, exposeIntrospection, exposePlayground,
  enableCors, customResolvers, resources, targetEnvironment.
- Optional `istio-gateway` + `istio-virtualservice` (gated on `enableIstioGateway==true`).
- Optional `AppContainerClaim` for repo scaffolding, gated on `parameter.language != _|_`
  (language nodejs/typescript, framework `graphql-gateway`). Comment says this is the
  RETIRE-WFT-2 #152 replacement of the old curl→Argo `oam-driven-contract` workflow — i.e. the
  WFT path was DELIBERATELY retired in favor of this declarative claim.
- Params: gatewayImage, serviceSelector (default `{graphql.federation/enabled:true}`), autoSchema,
  schemaRefreshInterval (5m), exposeIntrospection/Playground, enableCors, resources, version,
  environment, envFrom, language?/framework?/repository?, customResolvers?.

### Gateway runtime code: `graphql/mesh-gateway/` (the actual federation engine)
`factory/substrate/crossplane/graphql/mesh-gateway/`
Two generations coexist:
- **`src/` (the real, structured engine)** — `index.js` → `GatewayServer` (gateway-server.js),
  `service-discovery.js`, `discovery-loop.js`, `mesh-manager.js`, `schema-generator.js`.
  - `service-discovery.js`: AUTO-DISCOVERS. Runs `kubectl` (via spawn) with the label selector to
    list **both Knative services AND regular services** (`Promise.all`), reads each pod's OpenAPI
    by probing a fixed path list (`/openapi.json`, `/openapi`, `/api/openapi.json`,
    `/v1/openapi.json`, `/docs/openapi.json`, `/.well-known/openapi.json`, plus `openapi.path`
    annotation override), validates `spec.openapi` starts with `3.`.
  - `discovery-loop.js`: scheduled tick loop (`start/stop/discoveryTick/forceDiscovery`) with
    retry/backoff and dynamic interval reschedule (DISCOVERY_INTERVAL).
  - `mesh-manager.js`: `updateConfiguration(discoveredServices)` filters services w/ OpenAPI,
    diffs vs `currentServices` (`hasServicesChanged`), regenerates `.meshrc.yml`, rebuilds mesh.
  - `schema-generator.js`: builds GraphQL Query fields from GET endpoints and Mutation fields from
    POST/PUT/PATCH/DELETE, with field-name camelCasing and a `fieldMap` for resolvers.
  - Config via env: NAMESPACE, SERVICE_SELECTOR_LABELS (default `app.kubernetes.io/managed-by=kubevela`),
    DISCOVERY_INTERVAL, AUTO_DISCOVERY, EXPOSE_PLAYGROUND/INTROSPECTION, ENABLE_CORS.
- **Legacy/duplicate top-level scripts** — `server.js`, `server-fixed.js`, `server-original.js`,
  `generate-mesh-config.sh`, `mesh-config-template.yaml`, `package-simple.json`. The shell
  `generate-mesh-config.sh` is an OLDER bash reimplementation of the same discovery: `kubectl get
  ksvc -A -l <selector>` + `-l graphql.oam.dev/exposed=true`, builds a `sources[]` array of
  GraphQL-Mesh `openapi` handlers into `.meshrc.yaml` from `mesh-config-template.yaml`. Superseded
  by `src/`. Image referenced in old OAM app: `graphql-mesh-gateway:openapi-fix`.
- Also `graphql/schema-discovery/` (separate Dockerfile + discover-schema.sh + merge-schemas.js) —
  the CronJob-based discovery used only by the hasura-backup composition.

### `graphql-platform-claim-xrd.yaml` + composition (the infra claim CURRENTLY targeted)
- XRD `xgraphqlplatformclaims.platform.example.org`, claim kind `GraphQLPlatformClaim`,
  connectionSecretKeys `hasura-admin-secret`,`graphql-endpoint`. Spec: name(req), serviceSelector,
  autoSchema, schemaRefreshInterval, exposeIntrospection, adminSecret, enableConsole,
  enableAllowList, customResolvers, resources, targetEnvironment. (NOTE: header comment still says
  "schema discovery and Hasura deployment" but the ACTIVE composition dropped Hasura.)
- `graphql-platform-claim-composition.yaml` ("Simplified … No database dependencies"): provisions
  ONLY discovery scaffolding — `<name>-graphql` Namespace, `gateway-config` ConfigMap (autoDiscovery,
  refreshInterval, selector `managed-by:kubevela`, cors, playground), `<name>-discovery-sa`
  ServiceAccount, ClusterRole/Binding for service discovery, NetworkPolicy. NO Hasura, NO Postgres.
- There is ALSO a second XRD `xgraphqlplatforms.platform.example.org` (kind `XGraphQLPlatform`,
  richer spec) in `compositions/graphql-platform-composition.yaml` — a near-duplicate/alternate.

### Hasura variant: `graphql-platform-claim-composition-hasura-backup.yaml` (PARKED)
Full original 14KB composition "Creates all infrastructure for GraphQL gateway" following the
realtime-platform pattern. Provisions: namespace; 3 schema ConfigMaps (generated/custom/merged);
`graphql-schema-discovery` SA+ClusterRole+Binding; a **CronJob** running
`socrates12345/graphql-schema-discovery:latest`; `<name>-hasura-admin-secret` Secret;
`hasura-metadata` ConfigMap; `hasura-network-policy`; connection Secret with endpoint
`http://<name>-hasura.<name>-graphql.svc.cluster.local:8080/v1/graphql`. It references Hasura but
(from the section labels) the actual `graphql-engine` Deployment/Service appears INCOMPLETE/missing —
it sets up secrets, metadata, netpol, and the endpoint string but the visible resource list shows no
running graphql-engine workload. Treat as a SKELETON, not functional.

### Other artifacts
- `graphql-platform-component.yaml`: OLD OAM ComponentDefinition `graphql-platform` (autodetect
  workload) → emits `GraphQLPlatformClaim` only. Superseded by the cd.yaml's richer component.
- `graphql-gateway-application.yaml`: sample OAM `Application` using `graphql-gateway` type, image
  `graphql-mesh-gateway:openapi-fix`. Example, not infra.
- `graphql-gateway-configmap.yaml`: "Manual ConfigMap … Temporary workaround for Crossplane
  composition issues" — a hand-rolled stopgap.
- `execute/workflow-templates/graphql-gateway-template.yaml`: Argo WFT that clones
  `graphql-federation-gateway-template` GitHub repo, customizes, pushes. This is the OLD WFT world,
  explicitly RETIRED per the cd.yaml comment (now an AppContainerClaim).
- `examples/graphql-federation-example.yaml`, `catalog/examples/graphql-gateway-example.yaml`,
  `rbac/service-discovery-rbac.yaml` — examples + RBAC.
- `archive/.../smart-parking-graphql-schema.graphql`: consumer example, "Schema-first design for
  Hasura federation of REST microservices" — shows the intended consumer-facing federated schema.

## 2. State / wiring
- **LIVE path (current world):** OAM app → `graphql-gateway` ComponentDefinition (cd.yaml) →
  Knative Service (runs `mesh-gateway/src` engine) + `GraphQLPlatformClaim` → simplified
  composition (discovery RBAC/ConfigMap/SA only). Federation happens at RUNTIME in the gateway pod
  via kubectl discovery + GraphQL Mesh, NOT via Hasura. This is wired and consistent.
- **RETIRED:** the `graphql-gateway-template` Argo WFT and the `oam-driven-contract` curl-Job path
  — replaced by the declarative AppContainerClaim branch in the cd.yaml.
- **ORPHANED / stopgap:** `graphql-platform-component.yaml` (old component), `graphql-gateway-
  configmap.yaml` (manual workaround), `compositions/graphql-platform-composition.yaml` (duplicate
  XRD `XGraphQLPlatform`), top-level `server*.js` + `generate-mesh-config.sh` (legacy bash gen
  superseded by `src/`).

## 3. Hasura angle vs CLAUDE.md TODO #4
TODO #4 picked Hasura for "auto-generate GraphQL from PostgreSQL (zero-code)". The shipped reality
DIVERGED: the LIVE implementation is a **GraphQL Mesh runtime federation gateway over REST/OpenAPI
microservices** (per-service OpenAPI→GraphQL), NOT Hasura-over-Postgres. The hasura-backup
composition is the only Hasura artifact and it is a non-functional skeleton (secrets/metadata/netpol
but no graphql-engine workload, depends on a CronJob image and an external Postgres that the
simplified active composition deleted). So TODO #4's Postgres-auto-gen ambition is UNREALIZED; the
delivered value is OpenAPI federation instead. The enhance-plan must reconcile these: either (a)
embrace Mesh/OpenAPI federation as the chosen direction and update TODO #4, or (b) actually finish
Hasura+Postgres as a separate source alongside Mesh.

## 4. Verdict — REUSE / REPURPOSE / DEAD

REUSE (core, keep & enhance):
- `graphql-gateway.cd.yaml` — the spine. Enhance here (it already has the claim + istio + repo-scaffold wiring).
- `mesh-gateway/src/*` — the real federation engine (service-discovery auto-discovery, discovery-loop,
  mesh-manager, schema-generator). This is the asset; harden + test it.
- `graphql-platform-claim-xrd.yaml` + simplified `graphql-platform-claim-composition.yaml` — the
  active infra claim. Fix the stale "Hasura" header comment.
- `smart-parking-graphql-schema.graphql` — consumer contract / target shape for federated schema.

REPURPOSE:
- `graphql-platform-claim-composition-hasura-backup.yaml` + `graphql/schema-discovery/*` — ONLY if
  the plan decides to deliver the Postgres/Hasura source (TODO #4). It needs the graphql-engine
  Deployment+Service finished and a Postgres dependency restored. Otherwise dead.
- `examples/*` + `rbac/service-discovery-rbac.yaml` — update to match final wiring; keep as docs.

DEAD / DELETE candidates:
- `mesh-gateway/server.js`, `server-fixed.js`, `server-original.js`, `generate-mesh-config.sh`,
  `mesh-config-template.yaml`, `package-simple.json` — legacy bash/standalone gen superseded by `src/`.
- `graphql-platform-component.yaml` — superseded by cd.yaml component.
- `graphql-gateway-configmap.yaml` — admitted temporary workaround.
- `compositions/graphql-platform-composition.yaml` (duplicate `XGraphQLPlatform` XRD) — collapse into
  the one active XRD to avoid two competing platform CRDs.
- `execute/workflow-templates/graphql-gateway-template.yaml` — retired WFT; remove once AppContainerClaim path confirmed.

KEY ENHANCE TARGETS: (1) decide Mesh-vs-Hasura and align TODO #4; (2) consolidate the two XRDs +
two discovery implementations (src vs bash) into one; (3) add tests for `src/` discovery+schema-gen;
(4) confirm the AppContainerClaim repo-scaffold branch actually replaces the retired WFT end-to-end.
