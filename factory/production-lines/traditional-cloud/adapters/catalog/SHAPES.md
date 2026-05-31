# ComponentDefinition Shapes

Every ComponentDefinition in this catalog conforms to one of six **shapes** — the underlying
Kubernetes/Crossplane resource pattern that the CD's CUE template renders. The shape is
declared via the `definition.oam.dev/shape` annotation and drives:

- Which scaffolding boilerplate the CD inherits / repeats
- Which traits & policies are compatible
- Which authoring template to start from when adding a new CD

Knowing the shape lets the architect agent (and humans) reuse rather than re-invent.

---

## 1. `helm-release`

**Wraps:** `helm.crossplane.io/v1beta1` `Release` (Crossplane Helm provider).

**Members (6):** `postgresql`, `redis`, `mongodb`, `kafka`, `nats-jetstream`, `vcluster`.

**Common scaffolding it provides**
- Crossplane `Release` envelope (`forProvider.chart.{name,repository,version}`)
- `providerConfigRef.name` wiring to the in-cluster helm provider
- Namespace handling via `context.namespace`
- Release name derived from `context.name`

**Per-CD customization the consumer/architect supplies**
- Chart repo URL + chart name + chart version
- Helm `values` block (DB sizing, replicas, auth, persistence class, etc.)
- Optional `connectionDetails` / `writeConnectionSecretToRef` for credential propagation
- Whether the chart needs a CRD pre-install hook

**Authoring template (new helm-release CD)**

```yaml
# In CUE template: only the chart coords + values block should change between helm-release CDs.
forProvider: { chart: { name: "<chart>", repository: "<url>", version: "<x.y.z>" }, values: { ... } }
```

---

## 2. `knative-service`

**Wraps:** `serving.knative.dev/v1` `Service`.

**Members (6 in main catalog + 1 modular):** `webservice`, `camunda-orchestrator`,
`graphql-gateway`, `rasa-chatbot`, `realtime-platform`, plus `webservice-modular/webservice-shape`.
(`webservice` is the legacy monolith; `webservice-shape` is the modular replacement.)

**Common scaffolding it provides**
- Knative `Service` with single PodSpec container
- Autoscaling annotations (`autoscaling.knative.dev/{min,max}-scale`, target concurrency)
- Liveness/readiness probes on `/health` (override via `healthPath`)
- ServiceAccount + image-pull-secret wiring
- Istio sidecar injection labels

**Per-CD customization the consumer/architect supplies**
- Container image + port
- Env vars / secret refs
- Resource requests/limits
- Domain-specific args (e.g., Rasa actions URL, Camunda Zeebe broker, GraphQL schema mode)
- Optional auxiliary services in the same CUE template (rare — prefer separate components)

**Authoring template (new knative-service CD)**

```yaml
# PREFERRED: do NOT author a new full CD. Use webservice-shape + composable traits
# (auto-scaffold-bootstrap, image-source-policy, language-enum-policy) instead.
```

---

## 3. `statefulset`

**Wraps:** `apps/v1` `StatefulSet`.

**Members (1):** `clickhouse`.

**Common scaffolding it provides**
- StatefulSet headless service + PVC template
- Pod anti-affinity hints
- Init containers for cluster bootstrap

**Per-CD customization the consumer/architect supplies**
- Image + replicas + storage class + storage size
- Database-specific config (shard/replica topology, users, dictionaries)
- Service ports

**Authoring template (new statefulset CD)**

```yaml
spec: { workload: { definition: { apiVersion: apps/v1, kind: StatefulSet } } }
# Use only when Helm chart unavailable or insufficient. Prefer helm-release shape.
```

---

## 4. `external-secret`

**Wraps:** `external-secrets.io/v1` `ExternalSecret` (External Secrets Operator).

**Members (2):** `auth0-idp`, `neon-postgres`.

**Common scaffolding it provides**
- `ExternalSecret` skeleton referencing a `ClusterSecretStore` (typically Key Vault / SSM)
- `target` secret name templated from `context.name`
- Refresh interval defaults

**Per-CD customization the consumer/architect supplies**
- Vault path / key mapping (`spec.data[].remoteRef`)
- Output secret schema (which keys land in the cluster Secret)
- Optional template transformations (concatenated connection strings, base64)

**Authoring template (new external-secret CD)**

```yaml
spec: { workload: { definition: { apiVersion: external-secrets.io/v1, kind: ExternalSecret } } }
# Use for any SaaS or vault-backed credential surface. Keep CUE template minimal — vault refs only.
```

---

## 5. `argo-workflow`

**Wraps:** `argoproj.io/v1alpha1` `Workflow`.

**Members (1):** `identity-service`.

**Common scaffolding it provides**
- `Workflow` envelope with `serviceAccountName` + `workflowTemplateRef`
- Parameter passing from CUE `parameter` block into Argo `arguments.parameters`
- `ttlStrategy` cleanup defaults

**Per-CD customization the consumer/architect supplies**
- Which WorkflowTemplate to call (`workflowTemplateRef.name`)
- Parameter list specific to that template (e.g., domain name, git target, language)
- Output artifact location (if any)

**Authoring template (new argo-workflow CD)**

```yaml
spec: { workload: { definition: { apiVersion: argoproj.io/v1alpha1, kind: Workflow } } }
# Use for one-shot generators (scaffold a repo, run a migration, kick off a build).
# Pair with a corresponding WorkflowTemplate registered in the cluster.
```

---

## 6. `application-claim`

**Wraps:** `platform.example.org/v1alpha1` `ApplicationClaim` (Crossplane composite).

**Members (1):** `application-infrastructure`.

**Common scaffolding it provides**
- ApplicationClaim composite that fans out to networking + storage + compute resources
- Repository / branch / language inputs
- Bootstrap workflow trigger

**Per-CD customization the consumer/architect supplies**
- Language, framework, container registry
- Database & cache attachments
- Domain hostname

**Authoring template (new application-claim CD)**

```yaml
# AVOID adding new application-claim CDs. This shape exists once as the omnibus
# bootstrap. New capabilities should be composed via narrower shapes instead.
```

---

## Reuse opportunities

### Helm-release shape — 6 CDs share envelope

The 6 helm-release CDs all wrap an almost-identical Crossplane `Release` envelope. Only the
chart coordinates and `values` block change. **Recommendation:** extract a single
`helm-release-shape` ComponentDefinition (see CUE-R3) that takes
`{chart, repo, version, values}` as parameters. Existing per-DB CDs (`postgresql`,
`redis`, etc.) are retained for backward compatibility, but new helm-backed capabilities
should use the shape + a thin recipe overlay.

### Knative-service shape — 6 CDs share autoscaling/probe/SA boilerplate

The 6 knative-service CDs each re-author Service envelope, probes, SA wiring, and
autoscaling annotations. **Recommendation:** new CDs should use the modular
`webservice-modular/webservice-shape` ComponentDefinition + composable traits
(`auto-scaffold-bootstrap`, `image-source-policy`, `language-enum-policy`) rather than
authoring a fresh full CD. Domain-specific capabilities (Rasa, Camunda, etc.) can layer
their config via traits or a small post-render patch.

### Backward compatibility

Today's per-CD CDs are retained as-is so existing OAM Applications continue to deploy.
New CDs added going forward should follow the **modular pattern (S3)**:
- One shape per resource family (helm-release-shape, webservice-shape, ...)
- Domain knobs lifted into traits + policies
- Recipes (`forProvider.values` overlays, sidecar envelopes) live as separate small files

This keeps the catalog from accreting near-duplicate 200-line CDs every time a new
backing service is onboarded.
