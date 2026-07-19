# Full-Platform Test — BASELINE Results (wave-with-teardown, ≤5 nodes / vCPU-quota-capped)

Run start: 2026-06-13. Mode: deploy bundle → verify (HARD-4 contract test + manual probe) → teardown.

| # | Capability | Bundle | Baseline | Notes |
|---|---|---|---|---|
| T2 | realtime (ingest→processor→gateway) | rtdemo2 (live) | ✅ PASS | ksvcs Ready; sensor_agg flows (verified this session) |
| T3 | webhook (telemetry→Svix signed delivery) | webhookdemo (live) | ✅ PASS | bridge Ready; `sig=v1` external delivery 200 (proven #180) |
| T1 | webservice + db + cache + expose-api | binding-contract-example | ⏳ running | — |
| T4 | graphql-gateway (Hive federation) | graphql-federation-example | ⬜ pending | — |
| T5 | camunda-orchestrator (Zeebe 8) | workflowdemo (camunda part) | ⬜ pending | — |
| T6 | rasa-chatbot | chatdemo | ⬜ pending | — |
| T7 | dev-agent (GPT-5.4/APIM) | (on a scaffolded repo) | ⬜ pending | proven #179 |
| I1 | intake: MCP app.submit | (covered by T1 deploy) | ⬜ pending | — |
| I2 | intake: Slack /microservice | slack path | ⬜ pending | — |
| I3 | intake: architect-v1 | Foundry agent | ⬜ pending | — |

Legend: ✅ PASS · ❌ FAIL · ⏳ running · ⬜ pending · 🔁 known-flaky
