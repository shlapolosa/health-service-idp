# factory/adapters/

Concrete implementations of the **cross-manufacturer ports** declared in
[`cafe-spec/`](../../../cafe-spec/). Each subdirectory is one adapter: it
implements a port contract and plugs into the factory floor. Swapping an
adapter (e.g. Slack → Teams for Intake) does not require changes to the core
or any manufacturer.

| Adapter dir | Port implemented | Role |
|---|---|---|
| [`intake-slack/`](./intake-slack) | Intake | Receives use-case submissions over Slack slash commands and forwards to the dispatcher. |
| [`mcp-read-gateway/`](./mcp-read-gateway) | Catalog (read) / Govern (read) | MCP server exposing read-only tools: KB queries, capability catalog lookup, examples. |
| [`mcp-write-gateway/`](./mcp-write-gateway) | Catalog (write) / Execute (factory PR path) | MCP server exposing mutating tools — chiefly the PR opener for new/updated capabilities. |
| [`mcp-web-gateway/`](./mcp-web-gateway) | UI (discovery) | Web-facing MCP surface for discovering capabilities and triggering flows from outside Slack. |
| [`operator/`](./operator) | Observe + Govern (steward) | Operator-v1 agent — continuously diagnoses RBAC / CD / template / config issues under guardrails. |
