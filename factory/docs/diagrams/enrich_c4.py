#!/usr/bin/env python3
"""
enrich_c4.py — post-process a Structurizr-exported C4-PlantUML file into a "rich" variant.

Adds the four enhancements that Structurizr's C4 export cannot emit itself:
  1. ICONS      — sprite includes (tupadr3 font-awesome-5, logos, k8s) + per-Container $sprite=
  2. BOLD+COLOR BOUNDARIES — trust-zone colored, bold System_Boundary/Boundary
  3. ASYNC vs SYNC — Async-tagged Rel() (Structurizr stuffs the tag into $techn="Async")
                     rewritten to dashed/purple; everything else solid/grey
  4. SECURITY ZONES — each capability boundary mapped to a trust zone (color + auth note)
                      plus a legend (color->zone, line-style->sync/async).

Usage: python3 enrich_c4.py <in.puml> <out.puml>
Render WITHOUT graphviz: the output injects `!pragma layout smetana` as line 2.
"""
import sys, re

IN, OUT = sys.argv[1], sys.argv[2]
src = open(IN, encoding="utf-8").read()
lines = src.splitlines()

# ---------------------------------------------------------------- 1. sprite includes
# Internet-fetched PlantUML stdlib sprite libraries (resolved by plantuml.jar at render).
SPRITE_INCLUDES = r"""!include <tupadr3/common>
!include <tupadr3/font-awesome-5/server>
!include <tupadr3/font-awesome-5/database>
!include <tupadr3/font-awesome-5/cloud>
!include <tupadr3/font-awesome-5/cogs>
!include <tupadr3/font-awesome-5/shield_alt>
!include <tupadr3/font-awesome-5/network_wired>
!include <tupadr3/font-awesome-5/satellite_dish>
!include <tupadr3/font-awesome-5/comments>
!include <tupadr3/font-awesome-5/sitemap>
!include <tupadr3/font-awesome-5/project_diagram>
!include <tupadr3/font-awesome-5/key>
!include <tupadr3/font-awesome-5/broadcast_tower>
!include <tupadr3/devicons/redis>
!include <tupadr3/devicons/postgresql>
!include <logos/kafka>
!include <logos/elasticsearch>
!include <logos/kubernetes>
!include <logos/auth0-icon>
!include <logos/azure>
!include <logos/graphql>"""

# Map: substring-of-element-id (lowercased) -> sprite name. First match wins.
# Order matters (most-specific first).
SPRITE_MAP = [
    ("kafkabroker", "kafka"),
    ("realtimeplatform.kafka", "kafka"),
    (".kafka", "kafka"),
    ("mqttbroker", "broadcast_tower"),
    ("elasticsearch", "elasticsearch"),
    ("postgres", "postgresql"),
    ("postgresql", "postgresql"),
    ("neonpostgres", "postgresql"),
    ("redis", "redis"),
    ("hivegateway", "graphql"),
    ("subgrapha", "graphql"),
    ("subgraphb", "graphql"),
    ("auth0idp", "auth0-icon"),
    ("azurekeyvault", "key"),
    ("azureapim", "azure"),
    ("istioingressgateway", "network_wired"),
    ("svixengine", "satellite_dish"),
    ("webhookbridge", "satellite_dish"),
    ("appportal", "sitemap"),
    ("rasaserver", "comments"),
    ("rasaactions", "comments"),
    ("zeebe", "project_diagram"),
    ("operate", "project_diagram"),
    ("tasklist", "project_diagram"),
    ("optimize", "project_diagram"),
    ("camunda", "project_diagram"),
    ("metabase", "project_diagram"),
    ("lenses", "cogs"),
    ("kubevela", "kubernetes"),
    ("crossplane", "kubernetes"),
    ("argocd", "kubernetes"),
    ("knative", "kubernetes"),
    ("ksvc", "kubernetes"),
    ("identityservice", "shield_alt"),
    ("ingest", "satellite_dish"),
    ("processor", "cogs"),
    ("gateway", "network_wired"),
    ("webservice", "server"),
]

# External System() sprites
SYS_SPRITE = {
    "IoTTelemetrySource": "satellite_dish",
    "ExternalWebhookReceiver": "cloud",
    "Auth0": "auth0-icon",
    "AzureAPIM": "azure",
    "AzureKeyVault": "key",
}

def sprite_for(elem_id):
    low = elem_id.lower()
    for key, spr in SPRITE_MAP:
        if key in low:
            return spr
    return "cogs"

# ---------------------------------------------------------------- 2/4. trust zones per boundary
# boundary-title-substring -> (zone, hexcolor, auth-note)
RED, ORANGE, GREEN, BLUE, GREY = "#c0392b", "#e67e22", "#27ae60", "#2471a3", "#7f8c8d"
ZONES = {
    "edge":               ("EDGE/DMZ",   ORANGE, "Istio mTLS terminate"),
    "webservice":         ("INTERNAL",   GREEN,  "Auth0 JWT verify"),
    "identity-service":   ("INTERNAL",   GREEN,  "issues/validates JWT"),
    "realtime-platform":  ("INTERNAL",   GREEN,  "mesh mTLS"),
    "webhook-platform":   ("INTERNAL",   GREEN,  "HMAC-signed out; portal=EXTERNAL"),
    "graphql":            ("INTERNAL",   GREEN,  "Hive JWT-enforced"),
    "camunda":            ("INTERNAL",   GREEN,  "mesh mTLS"),
    "rasa":               ("INTERNAL",   GREEN,  "mesh mTLS"),
    "identity":           ("DATA/SECRET",BLUE,   "ESO->Key Vault"),
    "data stores":        ("DATA/SECRET",BLUE,   "at-rest; in-mesh only"),
    "platform plane":     ("INTERNAL",   GREY,   "control plane RBAC"),
}

def zone_for(title):
    t = title.lower()
    for key, v in ZONES.items():
        if key in t:
            return v
    return ("INTERNAL", GREEN, "")

out = []
for ln in lines:
    # AddBoundaryTag(...) — recolor + bold + zone+auth annotation in title
    m = re.match(r'(\s*)AddBoundaryTag\("([^"]+)",', ln)
    if m:
        indent, title = m.group(1), m.group(2)
        zone, color, auth = zone_for(title)
        out.append(f'{indent}AddBoundaryTag("{title}", $borderColor="{color}", '
                   f'$fontColor="{color}", $borderStyle="bold")')
        continue

    # Boundary("group_x", "title", ...) — append zone+auth label to the boundary title
    mb = re.match(r'(\s*)Boundary\((\w+), "([^"]+)"(.*)\)\s*\{?\s*$', ln)
    if mb:
        indent, gid, title, rest = mb.groups()
        zone, color, auth = zone_for(title)
        newtitle = f"{title}\\n[{zone}] {auth}" if auth else f"{title}\\n[{zone}]"
        brace = " {" if ln.rstrip().endswith("{") else ""
        out.append(f'{indent}Boundary({gid}, "{newtitle}"{rest}){brace}')
        continue

    # System_Boundary top-level — make it bold/dark
    msb = re.match(r'(\s*)System_Boundary\("([^"]+)", "([^"]+)"(.*)\)\s*\{?\s*$', ln)
    if msb:
        indent, bid, title, rest = msb.groups()
        out.append(f'{indent}AddBoundaryTag("idp_root", $borderColor="#1b2631", '
                   f'$fontColor="#1b2631", $borderStyle="bold")')
        out.append(f'{indent}System_Boundary("{bid}", "{title}\\n[mesh: Istio mTLS + per-svc JWT]", $tags="idp_root") {{')
        continue

    # Container(id, "name", ...) — inject $sprite=
    mc = re.match(r'(\s*)Container\(([^,]+),(.*)\)\s*$', ln)
    if mc:
        indent, cid, rest = mc.groups()
        if "$sprite=" not in rest:
            spr = sprite_for(cid.strip())
            rest = rest.rstrip()
            # insert sprite before trailing ) — append as last arg
            out.append(f'{indent}Container({cid},{rest}, $sprite="{spr}")')
            continue

    # System(id, "name", ...) external — inject $sprite=
    ms = re.match(r'(\s*)System\(([^,]+),(.*)\)\s*$', ln)
    if ms:
        indent, sid, rest = ms.groups()
        key = sid.strip()
        if "$sprite=" not in rest and key in SYS_SPRITE:
            out.append(f'{indent}System({sid},{rest.rstrip()}, $sprite="{SYS_SPRITE[key]}")')
            continue

    # Rel(...) — Structurizr stuffs the Async tag into $techn="Async". Rewrite to dashed/purple.
    mr = re.match(r'(\s*)Rel\((.+?), (.+?), "([^"]*)", \$techn="([^"]*)"(.*)\)\s*$', ln)
    if mr:
        indent, a, b, label, techn, rest = mr.groups()
        if techn == "Async":
            out.append(f'{indent}Rel({a}, {b}, "{label} «async»", $techn="event/stream", '
                       f'$tags="", $link="")')
            out.append(f'{indent}Lay_D({a}, {b})' if False else '')  # no-op placeholder removed below
            continue
    out.append(ln)

# strip accidental empty placeholder lines we may have added
out = [l for l in out if l is not None]

text = "\n".join(out)

# ---------------------------------------------------------------- inject pragma + includes + styles + legend
# pragma must be line 2 (after @startuml)
text = text.replace("@startuml", "@startuml\n!pragma layout smetana", 1)

# add sprite includes right after the last C4 include
text = text.replace(
    "!include <C4/C4_Container>",
    "!include <C4/C4_Container>\n" + SPRITE_INCLUDES,
    1,
)

# Async relationship style: dashed + purple. Sync default style: solid grey.
# Use UpdateRelStyle on the technology we set ("event/stream") via a tag-less global:
STYLE_BLOCK = """
' ===== sync vs async edge styling =====
skinparam defaultTextAlignment center
' async edges carry «async» in label + technology event/stream; color them purple-dashed
AddRelTag("async", $textColor="#8e44ad", $lineColor="#8e44ad", $lineStyle=DashedLine())
"""
text = text.replace("!include <C4/C4_Container>", "!include <C4/C4_Container>", 1)

# Tag async rels: convert their $techn marker into a proper $tags="async" so AddRelTag applies.
text = re.sub(
    r'Rel\((.+?), (.+?), "([^"]*«async»[^"]*)", \$techn="event/stream", \$tags="", \$link=""\)',
    r'Rel(\1, \2, "\3", $techn="event/stream", $tags="async", $link="")',
    text,
)

# place the AddRelTag + skinparam after includes
text = text.replace(SPRITE_INCLUDES, SPRITE_INCLUDES + "\n" + STYLE_BLOCK, 1)

# drop the C4 auto-legend so our custom trust-zone legend is the only one
text = re.sub(r'(?m)^\s*SHOW_LEGEND\([^)]*\)\s*$', '', text)

# legend before @enduml
# NOTE: under `!pragma layout smetana` (no graphviz) PlantUML drops the *text* of
# legend/creole-table cells (colours still render). We therefore put the legend as a
# coloured `caption` (which smetana renders reliably) instead of a `legend` block.
CAPTION = (
    "caption "
    "<b>Trust zones:</b> "
    "<color:#e67e22><b>EDGE/DMZ</b></color> (Istio mTLS terminate)  |  "
    "<color:#27ae60><b>INTERNAL/mesh</b></color> (mTLS + JWT)  |  "
    "<color:#2471a3><b>DATA/secrets</b></color> (pg/redis/kafka/KV, at-rest)  |  "
    "<color:#c0392b><b>EXTERNAL/untrusted</b></color> (Auth0/APIM/IoT/webhook)        "
    "<b>Edges:</b> "
    "<color:#707070>solid</color> = sync (HTTP/REST/WS)  ,  "
    "<color:#8e44ad>dashed</color> = async (Kafka/queue/webhook)\n"
)
text = text.replace("@enduml", CAPTION + "@enduml", 1)

open(OUT, "w", encoding="utf-8").write(text)
print(f"wrote {OUT}  ({len(text)} bytes)")
