#!/usr/bin/env python3
"""View 2 as a banded C4 solution diagram via the drawio-c4 engine.
Top-down trust-zone bands · landing-zone system boundaries · trust-boundary strips · typed edges."""
import sys
sys.path.insert(0, "/Users/socrateshlapolosa/.claude/skills/drawio-c4")
from drawio_c4 import C4Diagram

OUT = "/Users/socrateshlapolosa/Development/health-service-idp/factory/docs/analysis/anthropic-serving/view2-c4.drawio"

# typed edge styles (defaults + governance/observe)
EDGE_STYLES = {
    "sync":     "strokeColor=#1A1A1A;",
    "async":    "strokeColor=#7A7A7A;dashed=1;dashPattern=6 4;",
    "xtrust":   "strokeColor=#B85450;strokeWidth=2;",
    "identity": "strokeColor=#9966AA;dashed=1;dashPattern=2 4;",
    "govern":   "strokeColor=#D26B72;dashed=1;dashPattern=4 4;",
    "observe":  "strokeColor=#8B6CB8;dashed=1;dashPattern=1 4;",
}

d = C4Diagram("View 2 — Serving Anthropic (Claude) via Microsoft Foundry + APIM on Azure AI Landing Zones",
              width=1860, edge_styles=EDGE_STYLES)

# ---- bands (top -> down) ----
d.zone("z_client",  "Client / Consumer Surfaces  (outside Azure tenant)", stroke="#CC785C", comp_fill="#F4E3DC")
d.zone("z_id",      "Identity & Edge  (platform / connectivity)",          stroke="#8B5CF6", comp_fill="#EFEAFB")
d.zone("z_gw",      "AI Gateway — Azure API Management",                    stroke="#2E8B84", comp_fill="#E2F1F0")
d.zone("z_app",     "GenAI Microservices  (Azure Container Apps · Dapr)",   stroke="#0F6CBD", comp_fill="#EAF1FB")
d.zone("z_foundry", "Microsoft Foundry / Agent platform",                  stroke="#3A7CA5", comp_fill="#D7E8F2")
d.zone("z_model",   "Model deployment",                                    stroke="#CC785C", comp_fill="#F4E3DC")
d.zone("z_data",    "Dependencies & Data  (private endpoints)",            stroke="#D6B656", comp_fill="#FFF2CC")
d.zone("z_gov",     "Governance & Observability plane  (cross-cutting)",    stroke="#666666", comp_fill="#EEEEEE")

# ---- system boundaries (encompass contiguous bands) ----
d.system("CLIENT  ·  outside Azure tenant",                 ["z_client"], "#CC785C")
d.system("PLATFORM — Identity & Edge (Connectivity hub)",   ["z_id"],     "#8B5CF6")
d.system("AI GATEWAY LANDING ZONE  (spoke)",                ["z_gw"],     "#2E8B84")
d.system("FOUNDRY LANDING ZONE  (spoke)",                   ["z_app", "z_foundry", "z_model", "z_data"], "#3A7CA5")
d.system("GOVERNANCE PLANE",                                ["z_gov"],    "#666666")

# ---- trust-boundary strips ----
d.trust_boundary("AZURE TENANT BOUNDARY  ·  Entra ID identity (OAuth2 / OIDC)", "z_client")
d.trust_boundary("B2B  ·  Entra-secured APIM products  ·  private network (Private Endpoints, no public model egress)", "z_gw")

# ---- per-band security context ----
d.security("z_id",      "Entra ID · workload identity (Agent 365) · WAF")
d.security("z_gw",      "JWT validate · quota · semantic cache · content safety · usage metering")
d.security("z_foundry", "Managed Identity · Private Endpoints")
d.security("z_data",    "Key Vault · KMS · Private Endpoints")
d.security("z_gov",     "Defender · Purview · Azure Policy · Monitor")

# ---- components ----
d.component("cc_web",  "z_client", "Claude Code — Web", "claude.ai/code")
d.component("cc_cli",  "z_client", "Claude Code — CLI", "terminal / IDE")
d.component("users",   "z_client", "Application users", "browser")
d.component("cons",    "z_client", "Programmatic consumers", "architect-v1 · dev-agent · external apps")

d.component("entra",   "z_id", "Microsoft Entra ID", "OAuth2/OIDC · app regs · workload identity")
d.component("appgw",   "z_id", "Application Gateway + WAF", "app UX ingress")

d.component("apim",    "z_gw", "APIM — AI Gateway", "Entra-secured products · JWT validate · quota · routing")
d.component("aigw",    "z_gw", "AI Gateway (API Center)", "Universal AI Registry · semantic cache · content safety")

d.component("arch",    "z_app", "architect-v1 orchestrator", "Foundry agent")
d.component("mcp",     "z_app", "capability-mcp", "MCP tools over APIM")
d.component("dev",     "z_app", "dev-agent", "build / CI (opencode)")
d.component("front",   "z_app", "frontend / ingestion", "Dapr")

d.component("foundry", "z_foundry", "Microsoft Foundry / AI Foundry Project", "Connections · Managed Identity")
d.component("agentsvc","z_foundry", "Foundry Agent Service", "agent runtime (build & run)")

d.component("claude",  "z_model", "Anthropic CLAUDE", "Foundry model deployment · Opus / Sonnet / Haiku")

d.component("kv",      "z_data", "Key Vault", "secrets · keys")
d.component("search",  "z_data", "AI Search", "grounding")
d.component("cosmos",  "z_data", "Cosmos DB", "state")
d.component("storage", "z_data", "Storage", "blobs")
d.component("redis",   "z_data", "Managed Redis", "semantic cache")

d.component("agent365","z_gov", "Agent 365", "agent mgmt & governance · registry · Entra Agent ID · security · observability")
d.component("defender","z_gov", "Microsoft Defender", "threat protection")
d.component("purview", "z_gov", "Purview", "data governance")
d.component("policy",  "z_gov", "Azure Policy", "guardrails")
d.component("monitor", "z_gov", "Monitor / Log Analytics", "diagnostics · usage")

# ---- typed edges ----
# clients -> gateway / edge
d.edge("cc_web","apim","sync"); d.edge("cc_cli","apim","sync"); d.edge("cons","apim","sync")
d.edge("users","appgw","sync"); d.edge("appgw","front","sync")
# identity — (1) clients AUTHENTICATE with Entra to acquire a token (incl. Claude CLI/Web, users, consumers)
d.edge("cc_web","entra","identity"); d.edge("cc_cli","entra","identity")
d.edge("users","entra","identity"); d.edge("cons","entra","identity")
# identity — (2) Entra secures the resources / APIM validates the JWT
d.edge("entra","apim","identity"); d.edge("entra","appgw","identity"); d.edge("entra","foundry","identity")
# gateway -> foundry (route model call); microservices -> gateway (model calls)
d.edge("apim","foundry","sync")
d.edge("arch","apim","sync"); d.edge("mcp","apim","sync"); d.edge("dev","apim","sync")
# foundry -> model (inference)
d.edge("foundry","claude","sync"); d.edge("agentsvc","claude","sync")
# Agent 365 — agent management & governance control plane
d.edge("entra","agent365","identity")    # Entra Agent ID → agent identities
d.edge("agent365","agentsvc","govern")   # registers & governs the agent runtime / agents
d.edge("agent365","arch","govern")       # governs the architect-v1 agent (registry · policy · observability)
# dependencies
d.edge("arch","cosmos","sync"); d.edge("arch","search","sync")
d.edge("foundry","kv","sync"); d.edge("foundry","storage","sync"); d.edge("apim","redis","sync")
# governance / observe (cross-cutting, dashed up into the plane)
d.edge("policy","apim","govern"); d.edge("defender","foundry","govern"); d.edge("purview","cosmos","govern")
d.edge("monitor","apim","observe"); d.edge("monitor","foundry","observe")

d.legend([
    ("Request (sync)",        "strokeColor=#1A1A1A;"),
    ("Identity (Entra)",      "strokeColor=#9966AA;dashed=1;dashPattern=2 4;"),
    ("Govern (Defender/Purview/Policy)", "strokeColor=#D26B72;dashed=1;dashPattern=4 4;"),
    ("Observe (Monitor)",     "strokeColor=#8B6CB8;dashed=1;dashPattern=1 4;"),
])

xml = d.render(layout="banded", outline_bands=True, animate_async=True, strict=False)
open(OUT, "w").write(xml)
print("wrote:", OUT)
print("violations:", d.violations)
