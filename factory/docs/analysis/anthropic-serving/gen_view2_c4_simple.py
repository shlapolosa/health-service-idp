#!/usr/bin/env python3
"""View 2 (SIMPLE) via drawio-c4 banded engine — the view2-logical component set & detail level,
laid out as banded top-down trust zones with typed edges. One box per concept."""
import sys
sys.path.insert(0, "/Users/socrateshlapolosa/.claude/skills/drawio-c4")
from drawio_c4 import C4Diagram

OUT = "/Users/socrateshlapolosa/Development/health-service-idp/factory/docs/analysis/anthropic-serving/view2-c4-simple.drawio"

EDGE_STYLES = {
    "sync":     "strokeColor=#1A1A1A;",                                  # request
    "resp":     "strokeColor=#7A7A7A;dashed=1;dashPattern=6 4;",         # response
    "identity": "strokeColor=#9966AA;dashed=1;dashPattern=2 4;",         # identity (Entra)
    "dep":      "strokeColor=#2E6FAE;",                                  # dependency
    "govern":   "strokeColor=#D26B72;dashed=1;dashPattern=4 4;",         # govern
    "observe":  "strokeColor=#8B6CB8;dashed=1;dashPattern=1 4;",         # observe
    "async":    "strokeColor=#7A7A7A;dashed=1;dashPattern=6 4;",
    "xtrust":   "strokeColor=#B85450;strokeWidth=2;",
}

d = C4Diagram("View 2 (simple) — Anthropic (Claude) via Microsoft Foundry + APIM  ·  request flow",
              width=1500, edge_styles=EDGE_STYLES)

# bands (top -> down) — one concept each (gateways + governance hold a few)
d.zone("z_client",  "Clients / Consumers  (outside Azure tenant)", stroke="#CC785C", comp_fill="#F4E3DC")
d.zone("z_id",      "Identity",                                    stroke="#8B5CF6", comp_fill="#EFEAFB")
d.zone("z_gw",      "Gateways",                                    stroke="#2E8B84", comp_fill="#E2F1F0")
d.zone("z_app",     "Application",                                 stroke="#0F6CBD", comp_fill="#EAF1FB")
d.zone("z_foundry", "Foundry / Agent platform",                   stroke="#3A7CA5", comp_fill="#D7E8F2")
d.zone("z_model",   "Model",                                      stroke="#CC785C", comp_fill="#F4E3DC")
d.zone("z_data",    "Dependencies & Data",                        stroke="#D6B656", comp_fill="#FFF2CC")
d.zone("z_gov",     "Governance & Observability",                 stroke="#666666", comp_fill="#EEEEEE")

# landing-zone system boundaries
d.system("OUTSIDE AZURE TENANT",           ["z_client"], "#CC785C")
d.system("AI GATEWAY LANDING ZONE",        ["z_gw"],     "#2E8B84")
d.system("FOUNDRY LANDING ZONE",           ["z_app", "z_foundry", "z_model", "z_data"], "#3A7CA5")
d.trust_boundary("Entra ID identity boundary (OAuth2 / OIDC)", "z_client")
d.trust_boundary("Entra-secured APIM · private network", "z_gw")
d.security("z_gw",      "JWT validate · quota · semantic cache · content safety")
d.security("z_foundry", "Managed Identity · Private Endpoints")
d.security("z_gov",     "Defender · Purview · Policy · Monitor")

# components (view2-logical granularity)
d.component("client", "z_client", "Clients / consumers", "Claude Code Web + CLI · app users · architect-v1 · dev-agent · external apps")
d.component("entra",  "z_id",     "Microsoft Entra ID", "OAuth2/OIDC · workload identity (Agent 365)")
d.component("apim",   "z_gw",     "APIM — AI Gateway", "JWT validate · quota · semantic cache · content safety · routing")
d.component("appgw",  "z_gw",     "Application Gateway + WAF", "app UX ingress")
d.component("micro",  "z_app",    "GenAI microservices (Container Apps)", "architect-v1 · capability-mcp · dev-agent · frontend (Dapr)")
d.component("foundry","z_foundry","Microsoft Foundry / AI Foundry Project", "Agent 365 / Foundry Agent Service · Managed Identity")
d.component("claude", "z_model",  "Anthropic CLAUDE", "Foundry model deployment · Opus / Sonnet / Haiku")
d.component("deps",   "z_data",   "Foundry / agent dependencies", "Key Vault · AI Search · Cosmos DB · Storage")
d.component("defender","z_gov", "Microsoft Defender", "threat protection")
d.component("purview", "z_gov", "Purview", "data governance")
d.component("policy",  "z_gov", "Azure Policy", "guardrails")
d.component("monitor", "z_gov", "Monitor / Log Analytics", "diagnostics · usage")

# typed edges (same flow as view2-logical)
d.edge("client","entra","identity")     # authenticate / acquire token
d.edge("client","apim","sync")          # model call + Bearer JWT
d.edge("client","appgw","sync")         # app UX
d.edge("entra","apim","identity"); d.edge("entra","appgw","identity"); d.edge("entra","foundry","identity")
d.edge("appgw","micro","sync")          # app UX -> microservices
d.edge("micro","apim","sync")           # microservices call models via the same gateway
d.edge("apim","foundry","sync")         # route model call (private)
d.edge("foundry","claude","sync")       # inference
d.edge("apim","client","resp")          # response (usage metered)
d.edge("micro","deps","dep"); d.edge("foundry","deps","dep")   # secrets · grounding · state
d.edge("policy","apim","govern"); d.edge("defender","foundry","govern"); d.edge("purview","deps","govern")
d.edge("monitor","apim","observe"); d.edge("monitor","foundry","observe")

d.legend([
    ("Request (sync)",   "strokeColor=#1A1A1A;"),
    ("Response",         "strokeColor=#7A7A7A;dashed=1;dashPattern=6 4;"),
    ("Identity (Entra)", "strokeColor=#9966AA;dashed=1;dashPattern=2 4;"),
    ("Dependency",       "strokeColor=#2E6FAE;"),
    ("Govern",           "strokeColor=#D26B72;dashed=1;dashPattern=4 4;"),
    ("Observe",          "strokeColor=#8B6CB8;dashed=1;dashPattern=1 4;"),
])

xml = d.render(layout="banded", outline_bands=True, animate_async=False, strict=False)
open(OUT, "w").write(xml)
print("wrote:", OUT)
print("violations:", d.violations)
