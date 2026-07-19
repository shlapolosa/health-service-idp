# Full-Platform Regression Test — baseline → harden → re-run

Purpose: establish a **known-good baseline** across every capability *before* hardening, then
re-run after to detect regressions. Resource-heavy by design (deploys ~one of each capability).

## Coverage matrix

| # | Capability | Deploy | Data-plane assertion (PASS criteria) | HARD-4 CT |
|---|---|---|---|---|
| T1 | **webservice + db + cache + identity + expose-api** | fresh OAM `fulltest-api` (python + postgresql + redis + auth0 + expose-api) | APIM URL returns 200 with minted JWT; 401 without; reads db+cache | check_webservice |
| T2 | **realtime** (ingest→processor→gateway) | existing `rtdemo2` (keep) | POST /ingest → `/ws` streams aggregate | check_realtime_* |
| T3 | **webhook** (telemetry→Svix signed delivery) | existing `webhookdemo` (keep) | telemetry → wh-receiver gets `sig=v1` POST ✅ proven | check_webhook |
| T4 | **graphql-gateway** (Hive federation) | fresh OAM `fulltest-gql` + 2 sibling svcs | federated query through gateway, JWT-enforced | check_graphql |
| T5 | **camunda-orchestrator** (Zeebe 8) | fresh OAM `fulltest-flow` | deploy BPMN → start instance → assert complete | check_camunda |
| T6 | **rasa-chatbot** | fresh OAM `fulltest-bot` | POST a message → intent response (known-flaky: model load) | check_rasa |
| T7 | **dev-agent** (GPT-5.4/APIM) | run on a scaffolded repo | implements a function; output executes | edit-fidelity |
| I1 | **intake: MCP app.submit** | submit T1 OAM via capability-mcp-mfg-tc | claim created, repos scaffolded, ksvc Ready | — |
| I2 | **intake: Slack /microservice** | `/microservice` parsed → app.submit | same outcome via Slack path (no argo-token) | — |
| I3 | **intake: architect-v1** | Foundry agent proposes an OAM from a brief | valid OAM + factory.route resolves | evals |
| X1 | **bindings** | (covered by T1/T4) | `<comp>-conn` secrets minted + envFrom wired | — |
| X2 | **teardown / Orphan** | delete one fulltest claim | repos ORPHANED on GitHub; cluster resources gone | — |

## Execution waves (fit B2ms max-pods=30/node; scale nodes per wave)

- **Wave A (keep + light):** T2, T3 already live (verify). Deploy T1 (webservice+db+cache+identity). ~+6 pods. 5 nodes.
- **Wave B:** T4 graphql + T5 camunda. ~+12 pods. scale to 7 nodes.
- **Wave C:** T6 rasa (heavy, 3Gi) + T7 dev-agent + I1/I2/I3 intake. scale to 8 nodes.
- Record PASS/FAIL per row in `factory/docs/plans/FULL-PLATFORM-TEST-RESULTS.md`.

## Baseline → harden → regression
1. Run all waves → record baseline (✅/❌ + notes per row).
2. Harden (subagents, prioritized): #113 provider-k8s SA RBAC + #100 conversion-webhook · #123 mcp-factory tools · #172 vela-bump · #162 mscv push-race · #164 APIM republish.
3. Re-run the SAME matrix → diff against baseline. Any row that flips ✅→❌ = regression → block the harden PR.

## Resource / cost
Peak ~8 B2ms nodes during Wave C. Scale back to 3-4 after. ~$X/hr for the test window — acceptable per "will require resource". Stop cluster when done.
