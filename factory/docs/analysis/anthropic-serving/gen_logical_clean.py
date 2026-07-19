#!/usr/bin/env python3
"""View 2 (logical, CLEAN) — same components as view2-logical, but grid-aligned like view1
with straight orthogonal (right-angle) connectors. Emits .svg (→png) and an editable .drawio."""
from html import escape
def xe(s): return escape(str(s), quote=True)

# edge kinds -> (color, dashed)
K={"req":("#1A1A1A",False),"resp":("#7A7A7A",True),"id":("#8B5CF6",True),
   "dep":("#2E6FAE",False),"gov":("#D26B72",True)}
ANT_F="#F4E3DC";ANT_B="#CC785C";ANT_T="#8A4B38";AZ="#0F6CBD";ENT="#8B5CF6";ENT_F="#EFEAFB"
GW_F="#E2F1F0";GW_B="#2E8B84";GW_T="#1E5C57";MON="#8B6CB8";SEC_B="#D26B72";MUT="#555"

# ---- nodes (x,y,w,h) on a clean grid ----
N=dict(
 entra =(390,100,240,64),
 client=(60,290,250,130), apim=(390,290,240,130), foundry=(710,290,240,130), claude=(1030,290,240,130),
 appgw =(60,480,250,120), micro=(390,480,240,120), deps=(710,480,240,120),
 gov   =(60,690,1210,140),
)
TITLE=dict(
 entra=("Microsoft Entra ID","OAuth2 / OIDC · workload identity (Agent 365)",ENT_F,ENT,"#5B3FA6"),
 client=("Clients / consumers","Claude Code Web + CLI\napp users · architect-v1 · dev-agent · external apps",ANT_F,ANT_B,ANT_T),
 apim=("APIM — AI Gateway","JWT validate · quota · semantic cache\ncontent safety · usage metering · routing",GW_F,GW_B,GW_T),
 foundry=("Microsoft Foundry","AI Foundry Project · Agent 365 /\nFoundry Agent Service · Managed Identity","#fff",AZ,AZ),
 claude=("Anthropic CLAUDE","Foundry model deployment\nOpus / Sonnet / Haiku",ANT_F,ANT_B,ANT_T),
 appgw=("Application Gateway + WAF","app UX ingress","#EAF1FB",AZ,AZ),
 micro=("GenAI microservices","Container Apps (Dapr)\narchitect-v1 · capability-mcp · dev-agent","#EAF1FB",AZ,AZ),
 deps=("Dependencies & data","Key Vault · AI Search\nCosmos DB · Storage","#FFF6E0","#C9A227","#7A5F00"),
)
# ---- orthogonal edges: list of waypoints + label(x,y) + kind ----
E=[
 ([(185,290),(185,132),(390,132)],"1 acquire token","id",(196,126)),
 ([(310,355),(390,355)],"2 call + JWT","req",(350,347)),
 ([(510,164),(510,290)],"3 validate","id",(548,235)),
 ([(630,355),(710,355)],"5 route","req",(670,347)),
 ([(950,355),(1030,355)],"6 inference","req",(990,347)),
 ([(185,420),(185,480)],"app UX","req",(220,453)),
 ([(310,540),(390,540)],"8 app UX","req",(350,532)),
 ([(510,480),(510,420)],"9 model calls","req",(556,453)),
 ([(830,420),(830,480)],"11 deps","dep",(862,453)),
 ([(630,540),(710,540)],"10 grounding / state","dep",(670,532)),
 ([(1210,420),(1210,650),(30,650),(30,355),(60,355)],"7 response (usage metered)","resp",(640,643)),
 ([(830,690),(830,600)],"govern data","gov",(866,650)),
]

# ============ SVG ============
def svg():
    W,H=1320,880; p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif">',f'<rect width="{W}" height="{H}" fill="#fff"/>']
    p.append('<defs>'+''.join(f'<marker id="m{k}" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0L7,3L0,6Z" fill="{v[0]}"/></marker>' for k,v in K.items())+'</defs>')
    p.append(f'<text x="{W/2}" y="34" font-size="20" font-weight="bold" text-anchor="middle">View 2 (logical) — Anthropic (Claude) via Microsoft Foundry + APIM</text>')
    p.append(f'<text x="{W/2}" y="55" font-size="12" fill="{MUT}" text-anchor="middle">Grid-aligned · orthogonal connectors · request · response · identity · dependency · govern</text>')
    # gov band first (behind)
    gx,gy,gw,gh=N["gov"]
    p.append(f'<rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" rx="8" fill="#FBFBFD" stroke="#9AA0A6" stroke-width="1.6"/>')
    p.append(f'<text x="{gx+12}" y="{gy+22}" font-size="13" font-weight="bold" fill="#444">Cross-cutting governance &amp; observability — governs / observes APIM · Foundry · microservices · data</text>')
    for j,(lab,col) in enumerate([("Microsoft Defender",SEC_B),("Purview (data governance)",SEC_B),("Azure Policy (guardrails)","#C9A227"),("Monitor / Log Analytics",MON),("Entra ID (identity)",ENT)]):
        cx=gx+18+j*238
        p.append(f'<rect x="{cx}" y="{gy+44}" width="224" height="36" rx="6" fill="#fff" stroke="{col}" stroke-width="1.3"/>')
        p.append(f'<text x="{cx+112}" y="{gy+67}" font-size="11" fill="#222" text-anchor="middle">{xe(lab)}</text>')
    # edges
    for pts,lab,kind,(lx,ly) in E:
        c,dash=K[kind]; d=' stroke-dasharray="6 4"' if dash else ''
        dpath="M "+" L ".join(f"{x} {y}" for x,y in pts)
        p.append(f'<path d="{dpath}" fill="none" stroke="{c}" stroke-width="1.7"{d} marker-end="url(#m{kind})"/>')
        p.append(f'<rect x="{lx-len(lab)*3.2-4}" y="{ly-11}" width="{len(lab)*6.4+8}" height="15" rx="3" fill="#fff" fill-opacity="0.9"/>')
        p.append(f'<text x="{lx}" y="{ly}" font-size="10" fill="{c}" text-anchor="middle">{xe(lab)}</text>')
    # nodes
    for k,(x,y,w,h) in N.items():
        if k=="gov": continue
        title,sub,fill,stroke,tc=TITLE[k]
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')
        p.append(f'<text x="{x+12}" y="{y+24}" font-size="13.5" font-weight="bold" fill="{tc}">{xe(title)}</text>')
        yy=y+43
        for ln in sub.split("\n"):
            p.append(f'<text x="{x+12}" y="{yy}" font-size="10.6" fill="#333">{xe(ln)}</text>'); yy+=15
    # legend
    p.append(f'<text x="{W-20}" y="78" font-size="10.5" fill="#333" text-anchor="end" font-weight="bold">── request   ┄ response   ┄ identity   ── dependency   ┄ govern</text>')
    p.append("</svg>")
    open("view2-logical-clean.svg","w").write("\n".join(p))

# ============ draw.io (orthogonal edges by source/target) ============
def drawio():
    cells=[]; i=[1]; ids={}
    def nid(): i[0]+=1; return f"n{i[0]}"
    for k,(x,y,w,h) in N.items():
        if k=="gov":
            v="Cross-cutting governance &amp; observability — governs / observes APIM · Foundry · microservices · data"
            st=f"rounded=1;html=1;fillColor=#FBFBFD;strokeColor=#9AA0A6;verticalAlign=top;align=left;spacingLeft=10;spacingTop=6;fontStyle=1;fontSize=12;"
        else:
            title,sub,fill,stroke,tc=TITLE[k]; v=xe(title+"\n"+sub)
            st=f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.8;verticalAlign=top;align=left;spacingLeft=8;spacingTop=5;fontSize=12;fontColor={tc};"
        cid=nid(); ids[k]=cid
        cells.append(f'<mxCell id="{cid}" value="{v}" style="{st}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    # governance chips
    for j,(lab,col) in enumerate([("Microsoft Defender",SEC_B),("Purview",SEC_B),("Azure Policy","#C9A227"),("Monitor / Log Analytics",MON),("Entra ID",ENT)]):
        gx,gy,_,_=N["gov"]; cx=gx+18+j*238
        cells.append(f'<mxCell id="{nid()}" value="{xe(lab)}" style="rounded=1;html=1;fillColor=#fff;strokeColor={col};fontSize=11;align=center;" vertex="1" parent="1"><mxGeometry x="{cx}" y="{gy+44}" width="224" height="36" as="geometry"/></mxCell>')
    # edges: (src,tgt,label,kind,exit(x,y),entry(x,y))
    ed=[("client","entra","1 acquire token","id",(0.5,0),(0,0.5)),
        ("client","apim","2 call + JWT","req",(1,0.5),(0,0.5)),
        ("entra","apim","3 validate","id",(0.5,1),(0.5,0)),
        ("apim","foundry","5 route","req",(1,0.5),(0,0.5)),
        ("foundry","claude","6 inference","req",(1,0.5),(0,0.5)),
        ("client","appgw","app UX","req",(0.5,1),(0.5,0)),
        ("appgw","micro","8 app UX","req",(1,0.5),(0,0.5)),
        ("micro","apim","9 model calls","req",(0.5,0),(0.5,1)),
        ("foundry","deps","11 deps","dep",(0.5,1),(0.5,0)),
        ("micro","deps","10 grounding / state","dep",(1,0.5),(0,0.5)),
        ("claude","client","7 response","resp",(0.5,1),(0,0.5)),
        ("gov","deps","govern data","gov",(0.5,0),(0.5,1))]
    for src,tgt,lab,kind,(ex,ey),(nx,ny) in ed:
        c,dash=K[kind]; d="dashed=1;dashPattern=6 4;" if dash else ""
        st=f"edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=classic;strokeColor={c};{d}exitX={ex};exitY={ey};entryX={nx};entryY={ny};fontSize=10;fontColor={c};labelBackgroundColor=#ffffff;"
        cells.append(f'<mxCell id="{nid()}" value="{xe(lab)}" style="{st}" edge="1" parent="1" source="{ids[src]}" target="{ids[tgt]}"><mxGeometry relative="1" as="geometry"/></mxCell>')
    body="\n".join(cells)
    open("view2-logical-clean.drawio","w").write(
        f'<mxfile host="app.diagrams.net"><diagram name="View 2 logical (clean)"><mxGraphModel dx="1320" dy="880" grid="0" page="1" pageWidth="1320" pageHeight="880"><root><mxCell id="0"/><mxCell id="1" parent="0"/>{body}</root></mxGraphModel></diagram></mxfile>\n')

svg(); drawio(); print("wrote view2-logical-clean.svg, view2-logical-clean.drawio")
