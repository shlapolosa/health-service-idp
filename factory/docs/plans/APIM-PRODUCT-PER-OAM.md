# APIM-PRODUCT-PER-OAM: One Developer-Portal Product per OAM Application (Plan)

**Task:** APIM-PRODUCT-PER-OAM — implementation-ready plan to auto-create ONE APIM Product per OAM Application, grouping all of that app's externally-accessible APIs and publishing it to the APIM Developer Portal.
**Status:** PLANNING (doc only). No code, no kubectl, no `az` writes.
**Date:** 2026-06-08.

---

## 1. Goal

Today each externally-exposed service gets its OWN APIM API (path `svc/<service-name>`), but there is no app-level grouping. A consumer browsing the Developer Portal sees a flat list of `svc/*` APIs with no notion of which app they belong to.

Target: **for each OAM Application (= one AppContainer = one "app") auto-create ONE APIM Product** that:

1. Is named/scoped per OAM file: OAM app `patient9` → APIM product id `patient9`.
2. Contains ALL of that OAM's externally-accessible APIs — every `webservice` carrying `expose-api` ∪ the `graphql-gateway` component ∪ (later) `realtime-service`. Internal-only components are excluded.
3. Is **published to the Developer Portal** so a consumer can discover the app, see its APIs, sign up, and get a subscription.

The Product is **purely additive** — per-service `svc/<name>` APIs and their `validate-jwt` enforcement are untouched.

---

## 2. What exists today (empirical findings)

### 2.1 Per-service API creation happens TWO ways (both verified)

**(a) The `expose-api` trait** — `factory/production-lines/traditional-cloud/adapters/catalog/webservice-modular/expose-api.yaml`.
- Renders a Job that runs `az apim api import` (line 165) with `--api-id "$SVC_NAME"` (line 168), `--display-name "$SVC_NAME"` (line 169), `--path "$API_SUFFIX"` (line 170, where `API_SUFFIX = parameter.apiPathPrefix + "/" + context.name`, line 109 — default prefix `svc`), `--subscription-required false` (line 175).
- WebSocket branch (`apiType: websocket`, lines 124–139): ARM `PUT .../apis/$SVC_NAME` with `type:websocket`, no spec.
- After import, if an identity is bound (`JWT_ISSUER_URI` present) it PUTs a `validate-jwt` policy to `.../apis/${SVC_NAME}/policies/policy` (lines 182–186, and 136–138 for ws). **This is the auth the trait owns.**
- `apiType` param: `*"http" | "websocket"` (line 218).

**(b) The EVENT-2 ksvc-Ready sensor** — `factory/substrate/argo-events/ksvc-ready-apim-publish.yaml`.
- Sensor `ksvc-ready-apim-publish` (ns `argo-events`) fires on ksvc Ready, creates a Job (`generateName: apim-publish-evt-`) that runs the same `az apim api import --api-id "$SVC_NAME"` (lines 176–187). It **only imports the spec**; `validate-jwt` remains the trait's job (sensor comment lines 23, 201). Both Jobs UPSERT by `--api-id` → mutually idempotent.

**Consequence for this design:** API *creation* is already idempotent and deterministic. The Product layer must therefore be a separate, independently-idempotent reconcile that LINKS already-named APIs — it must not create APIs itself, and must tolerate APIs appearing slightly after the Product (ordering).

### 2.2 `app.submit` already knows the external set — `submit_use_case.py`

`factory/shared-libs/capability-mcp-core/src/application/submit_use_case.py`:
- `_auto_expose_external_components(app, oam_yaml)` (line 127): external-by-default — auto-attaches the `expose-api` trait to every `graphql-gateway` and `realtime-service` component that lacks it (lines 138–148), wiring `identity` = the OAM's singleton `auth0-idp` (line 134).
- `_validate_identity_topology(app)` (line 249): computes `exposed` = components of type `webservice|webservice-shape|realtime-service` where `_is_exposed(c)` is true (`expose-api` trait OR `properties.exposeApi`) (lines 257–265). **This is exactly the membership predicate we need** — but it currently excludes `graphql-gateway` from `exposed` even though the gateway IS external (it is handled as a singleton, lines 282–290). The Product membership set = `exposed` ∪ `graphql-gateway` components.
- `_webservice_services(app)` (line 352): derives `services[]` (scaffoldable components) for the AppContainerClaim. NOTE this is the *scaffold* set, not the *exposed* set — they overlap but differ (a bring-your-own-image webservice is exposed but not scaffolded). Membership must use the exposed predicate, not this.
- The OAM app name (`app_name`, used as `<app>-gitops` repo and AppContainerClaim name, `_declarative_scaffold` line ~) is the natural Product id.

### 2.3 The AppContainerClaim composition — one claim per OAM

`factory/substrate/crossplane/app-container-claim-composition.yaml`: ONE `AppContainerClaim` named after the OAM, carrying `services[]`, fans out one `ApplicationClaim` per service (UNIFY-1 #153). This is the only per-OAM singleton resource in the system — a candidate emitter (option c).

### 2.4 Live APIM facts (verified 2026-06-08)

Instance `aigw-apim-dev-w4x7ibwk4e2is`, RG `rg-ai-gateway-dev-uae`, sub `ea9b2fed-51b7-42cc-84f3-328f5493a7b3`.

```
sku        = Developer            # <-- developer portal SUPPORTED (Developer/Basic/Std/Premium do; Consumption does not)
devPortal  = https://aigw-apim-dev-w4x7ibwk4e2is.developer.azure-api.net
gateway    = https://aigw-apim-dev-w4x7ibwk4e2is.azure-api.net
```

Existing **products** (`GET .../products`):

| id | state | subscriptionRequired | approvalRequired | displayName |
|---|---|---|---|---|
| mcp-external | published | false | – | MCP External (JWT) |
| mcp-internal | published | true | false | MCP Internal (sub-key) |
| starter | published | true | false | Starter |
| unlimited | published | true | true | Unlimited |

Existing **APIs** (12 total). `svc/*` APIs all have `subscriptionRequired=false`:

```
patient9-api    path=svc/patient9-api    subReq=false
patient9-graph  path=svc/patient9-graph  subReq=false
patient9-records path=svc/patient9-records subReq=false
items-api       path=svc/items-api       subReq=false
mcp-catalog     path=mcp/catalog ...      (+ anthropic, openai, factory, mcp-web, etc.)
```

→ **`patient9` is the live worked example**: an OAM whose external set is exactly `{patient9-api, patient9-graph, patient9-records}`. The Product `patient9` must link those three API ids.

`mcp-external` product → apis = `['mcp-catalog']`; groups = `['administrators']` (precedent for product→api link + group/visibility).

**Dual-auth precedent confirmed live.** `GET .../apis/mcp-catalog/policies/policy` contains a `<choose>` with two `<when>` branches: an `internal` profile branch keyed off `context.Subscription?.Id` (sub-key) and a `Bearer`-header branch running `<validate-jwt>` against an `openid-config`, falling through to `<otherwise>`. So **one API serving BOTH sub-key and JWT callers is an established, working pattern in this exact instance.** (Memory: "APIM mcp-catalog dual-auth".)

### 2.5 SKU constraints (cross-ref memory)

SKU is **Developer** → full Developer Portal, products, subscriptions, groups all supported. The known v1-SKU bugs in memory ("APIM-MCP POST body bug", "APIM tool filtering deferred") are about **Expose-as-MCP** request-body translation and MCP tool-list filtering — they do **not** touch the Products/portal/subscription ARM surface used here. **No SKU blocker for this capability.** (One operational note: Developer tier is single-unit / no SLA, fine for dev.)

---

## 3. The Product / Portal model (exact `az rest` calls)

ARM resource: `Microsoft.ApiManagement/service/{svc}/products/{pid}`, api-version `2022-08-01`. Let
`B=https://management.azure.com/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.ApiManagement/service/$NAME`.

**3.1 Create / upsert the product (idempotent PUT):**
```bash
az rest --method PUT --url "$B/products/$APP?api-version=2022-08-01" --body '{
  "properties": {
    "displayName": "<OAM displayName or app name>",
    "description": "<OAM description>",
    "state": "published",
    "subscriptionRequired": false,     # see §6 recommendation
    "approvalRequired": false,
    "terms": ""
  }
}'
```
`state:published` is what makes it visible in the Developer Portal. (Default group visibility on create is `administrators` + `developers`; we rely on `developers` for portal discovery — see 3.4.)

**3.2 Link an API to the product (idempotent PUT, empty body):**
```bash
az rest --method PUT --url "$B/products/$APP/apis/$APIID?api-version=2022-08-01"
# $APIID = the deterministic api-id == component name (patient9-api, patient9-graph, ...)
```

**3.3 Unlink an API that left the OAM (convergence):**
```bash
az rest --method DELETE --url "$B/products/$APP/apis/$APIID?api-version=2022-08-01"
```

**3.4 Ensure portal discoverability (developers group link — already default on create, explicit for safety):**
```bash
az rest --method PUT --url "$B/products/$APP/groups/developers?api-version=2022-08-01"
```

**3.5 Reconcile reads (to compute the diff):**
```bash
az rest --method GET --url "$B/products/$APP/apis?api-version=2022-08-01"     # current members
az rest --method GET --url "$B/apis?api-version=2022-08-01"                   # all api-ids exist?
```

All of these are PUT/DELETE-by-id → fully idempotent, safe to re-run every reconcile.

---

## 4. Recommended hook: **(a) app.submit creates/patches the Product, hardened by (b) a reconcile sensor** — hybrid, app.submit-primary

**Recommendation: (a) as the primary writer, with a thin (b) sensor as the convergence safety-net. Reject (c).**

### Rationale
- **(a) app.submit** already parses the full OAM, already computes the exposed set (`_validate_identity_topology`, line 257), already enforces the singleton/identity invariants, and already runs on every submit AND resubmit. It is the one place that authoritatively knows *the complete desired membership* up-front — including removals (a resubmitted OAM that dropped a component). Product create + full membership reconcile (link missing, unlink extra) belongs here because **only the submit-time view knows the full set; a per-service event only knows about one API.** This makes membership *converge* rather than append (the hard requirement in the brief).
- **Ordering caveat:** on day-0, `app.submit` runs before the `svc/*` APIs exist (CI build + ksvc-Ready precede EVENT-2 API import). A product→api PUT for an api-id that doesn't yet exist returns 404. So (a) must: create the product + link the APIs that already exist, and tolerate-skip the not-yet-created ones.
- **(b) reconcile sensor** closes that gap **level-triggered**, matching the platform's declarative-spine direction (it is REMOVING imperative Argo middles — RETIRE-WFT-2 #152). Make it a *sibling of EVENT-2*: it already fires on ksvc-Ready (the exact moment a new `svc/<name>` API gets imported). Add a step that, after the API exists, links it into the product whose name it derives from the OAM-app label on the ksvc. Because EVENT-2's job stamps the API, the sibling just needs `PUT $B/products/$APP/apis/$APIID` — idempotent. This guarantees the link lands even if it was a 404-skip at submit time, with zero polling.

### Why NOT (c) the AppContainerClaim composition
The composition is Crossplane/provider-kubernetes; emitting an APIM Product would require a provider that manages ARM APIM resources (provider-azure APIM CRDs or an Object→ARM bridge). The platform has **no provider-azure APIM provider installed** — APIM is driven exclusively by `az`/`az rest` from Jobs today (expose-api trait, EVENT-2). Introducing an ARM-APIM Crossplane provider for one Product is disproportionate, and the composition does not see per-component `expose-api` traits cleanly (it sees `services[]`, the scaffold set, not the exposed set — §2.2). Rejected.

### Why NOT (b) alone
A sensor-only design has no authoritative full-set view → cannot do **removals** (unlink an API that left the OAM). It would only ever append. Rejected as sole mechanism; kept as the accelerator/safety-net.

**Net:** app.submit = desired-state writer (create + full converge incl. unlink); EVENT-2-sibling sensor = eventual-link safety net for day-0 ordering. Both write through the same idempotent PUT/DELETE-by-id calls, so they never conflict.

---

## 5. Membership-derivation algorithm

Compute the external API-id set for an OAM exactly where `_validate_identity_topology` already computes `exposed`:

```
external_components(app):
  comps = app.spec.components
  exposed = []
  for c in comps:
    is_external =
        c.type in {webservice, webservice-shape, realtime-service} and _is_exposed(c)   # expose-api trait OR properties.exposeApi
        OR c.type == graphql-gateway                                                     # always external (singleton)
        # realtime-service already covered above once it carries expose-api (auto-attached, line 146)
    if is_external: exposed.append(c.name)
  return exposed                                  # api-id == component name (== --api-id in §2.1)
```

- api-id is **deterministic = component name** (expose-api `--api-id "$SVC_NAME"`, `SVC_NAME=context.name`). No lookup needed — the Product member id set == component-name set.
- **Add case (resubmit adds a component):** `_auto_expose_external_components` runs first; the new component is in `external_components`; submit PUTs the (maybe-404-skipped) link; the sensor lands it when the new ksvc goes Ready.
- **Remove case (resubmit drops a component):** submit GETs `$B/products/$APP/apis`, computes `current − desired`, DELETEs each extra link. The underlying `svc/<name>` API is left alone (it is torn down by its own component's lifecycle, not the product's). → membership **converges**.

Edge: a webservice with a non-default BYO image is exposed-but-not-scaffolded — still a member (membership uses the exposed predicate, NOT `_webservice_services`). Confirmed §2.2.

---

## 6. Auth / portal-subscription recommendation

**Recommendation: JWT-only discovery Product (`subscriptionRequired:false`), NOT dual-auth subscriptions — for v1.**

Rationale:
- Every member `svc/*` API already has `subscriptionRequired=false` (live §2.4) and enforces `validate-jwt` (Auth0) via the trait. The product is a **discovery + grouping surface** in the portal; it must not start *also* requiring an APIM subscription key, or it would break the existing JWT-only contract (non-breaking is a hard constraint).
- Setting `subscriptionRequired:false` on the product means: portal users can browse the app, see all its APIs, read docs, and "Try it" — but the gateway still enforces `validate-jwt`. The credential a consumer actually uses is the **Auth0 JWT** (unchanged), not an APIM sub-key. This is exactly the `mcp-external` model (product `subReq=false`, JWT-enforced, live §2.4).
- **Dual-auth (the mcp-catalog `<choose>` pattern, §2.4) is the documented v2 upgrade path** if a consumer later wants portal-issued sub-keys *in addition to* JWT. It is proven on this instance, so it is a known, low-risk future option — but it requires editing each member API's policy to add the sub-key `<when>` branch, which is per-API policy churn we don't need for a discovery product. Defer.

So: product display name + description come from OAM `metadata.name`/`metadata.annotations` (e.g. `description`), `subscriptionRequired:false`, `approvalRequired:false`, `state:published`, linked to the `developers` group. A developer "discovers" the app and its APIs; the auth they present at the gateway remains the Auth0 Bearer token.

---

## 7. Non-breaking guarantees

1. Per-service `svc/<name>` APIs: **untouched**. The product only PUT/DELETEs `products/$APP/apis/$id` *links*, never the API objects or their policies.
2. `validate-jwt` enforcement: **untouched** (lives on the API, set by the trait; product `subscriptionRequired:false` adds no key requirement).
3. Existing products `mcp-internal`/`mcp-external`/`starter`/`unlimited`: **no collision** — product ids are OAM app names (`patient9`, `items`, ...), a disjoint namespace from `mcp-*` and the built-in `starter`/`unlimited` (§8 guards this).
4. EVENT-2 and the expose-api trait Jobs: **unchanged**; the new sensor is a *sibling* that only adds product-link PUTs.

---

## 8. Naming / collision policy

- Product id = OAM app name (the same key already used for `<app>-gitops` and the AppContainerClaim — guaranteed unique per OAM by the existing repo-name uniqueness).
- **Reserved-prefix guard:** refuse/skip product creation if app name matches `^(mcp-|starter$|unlimited$)` to avoid clobbering platform products. (app.submit should validate this once, with an actionable message; cheap.)
- Cross-OAM clashes are impossible because the OAM app name already gates `<app>-gitops` repo creation (two OAMs can't share a name).

---

## 9. Teardown policy

**Policy: ORPHAN the product on AppContainer deletion (consistent with W1 `deletionPolicy:Orphan`).**

- The product is a thin, harmless grouping object. Leaving it published with zero linked APIs is inert (an empty product in the portal). Aligns with the platform's W1 Orphan philosophy (memory: declarative-spine / binding-contract).
- Optional later: a teardown sensor on AppContainer delete that DELETEs `products/$APP` for cleanliness. Defer to a follow-up workstream; not required for correctness.
- Note: deleting member `svc/*` APIs (their own lifecycle) auto-removes them from the product's api list, so an orphaned product self-empties over time.

---

## 10. Workstream breakdown (PR-sized, additive)

| WS | Scope | Files (no code here) |
|---|---|---|
| **P1** | Membership helper: factor the exposed-set predicate (reuse `_is_exposed`) into `_external_api_ids(app)` returning component names incl. `graphql-gateway`. Pure function + unit tests. | `submit_use_case.py` (additive method) |
| **P2** | Product reconcile in app.submit: after a successful submit, create/upsert product (§3.1), GET current members, link desired-that-exist (§3.2, skip-404), unlink extras (§3.3), ensure `developers` group (§3.4). Idempotent; gated by reserved-prefix guard (§8). Behind a thin APIM client (mirrors the existing `az rest` calls — but invoked as a Job, not in-process, to reuse the cluster SP, matching expose-api). | new APIM-product Job template + submit wiring |
| **P3** | EVENT-2-sibling sensor: on ksvc-Ready, derive `$APP` from the ksvc OAM-app label, `PUT products/$APP/apis/<api-id>` (idempotent link). | new `factory/substrate/argo-events/ksvc-ready-apim-product-link.yaml` |
| **P4** | (Deferred) teardown sensor on AppContainer delete → `DELETE products/$APP`. | new sensor |
| **P5** | (Deferred) dual-auth upgrade: add sub-key `<when>` branch to member API policies + flip product `subscriptionRequired`. Only if a consumer requests portal sub-keys. | per-API policy |

P1–P3 deliver the capability; P4–P5 are optional follow-ups.

---

## 11. Verification plan

1. **Unit:** `_external_api_ids` returns `{patient9-api, patient9-graph, patient9-records}` for the patient9 OAM; returns gateway-only when only a gateway is exposed; drops internal-only webservices.
2. **Live idempotency:** run the product reconcile twice for `patient9`; assert `GET products/patient9/apis` == the 3 ids both times (§2.4 gives the expected set).
3. **Add/remove convergence:** resubmit patient9 with one component removed → assert that link is DELETEd and the other two remain; re-add → link returns.
4. **Day-0 ordering:** submit a fresh OAM, assert product is created immediately with a partial/empty api list, then after ksvc-Ready assert the sibling sensor links the new api (no 404 left behind).
5. **Portal discovery:** `GET products/patient9` → `state=published`; product visible under `developers` group; portal lists the 3 APIs.
6. **Non-breaking:** assert each `svc/*` API still has `subscriptionRequired=false` and its `validate-jwt` policy unchanged; assert `mcp-*`/`starter`/`unlimited` products unchanged.

---

## 12. Top risks

1. **Day-0 ordering 404s** — product reconcile at submit precedes API creation. Mitigated by skip-404 at submit + the EVENT-2-sibling sensor (P3) as the level-triggered backstop. If the sensor/event-bus is dead (it has been silently dead before — EVENT-2 history), links never land; mitigation: app.submit should also re-attempt linking on every *resubmit* (it already runs the full reconcile), so a manual resubmit heals it.
2. **Membership predicate drift** — `graphql-gateway` is external but excluded from `_validate_identity_topology`'s `exposed`; if P1 forgets to union it, the gateway API won't be a member. Explicit test (verification #1) guards this. (realtime-service is already covered once its auto-attached `expose-api` lands.)
