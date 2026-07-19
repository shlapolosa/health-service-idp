#!/usr/bin/env python3
"""View 2 (LOGICAL) — request flow & relationships for serving Anthropic (Claude) via Foundry + APIM.
Emits an editable .drawio AND a rendered .svg/.png. Nodes + typed directional edges (not a reference catalog)."""
from html import escape
def xe(s): return escape(str(s), quote=True)

# ---- shared palette ----
AZ="#0F6CBD"; ENT="#8B5CF6"; ENT_F="#EFEAFB"; ANT_F="#F4E3DC"; ANT_B="#CC785C"; ANT_T="#8A4B38"
GW_F="#E2F1F0"; GW_B="#2E8B84"; GW_T="#1E5C57"; SEC_B="#D26B72"; MON="#8B6CB8"; MUT="#555"
NET_F="#FFF8E6"; NET_B="#C9A227"
# edge kinds: (color, dashed, width)
KIND={"req":("#1A1A1A",False,1.8),"resp":("#7A7A7A",True,1.6),"id":(ENT,True,1.6),
      "dep":("#2E6FAE",False,1.4),"gov":(SEC_B,True,1.5),"obs":(MON,True,1.4)}

# ---------- SVG builder ----------
class SVG:
    def __init__(s,w,h): s.w,s.h=w,h; s.p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="Helvetica,Arial,sans-serif">',f'<rect width="{w}" height="{h}" fill="#fff"/>','<defs>'+''.join(f'<marker id="a{k}" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0L7,3L0,6Z" fill="{v[0]}"/></marker>' for k,v in KIND.items())+'</defs>']
    def box(s,x,y,w,h,title,sub="",fill="#fff",stroke=AZ,tcolor=None,dash=False,fs=12.5):
        d=' stroke-dasharray="7 5"' if dash else ''
        s.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.7"{d}/>')
        s.p.append(f'<text x="{x+11}" y="{y+21}" font-size="{fs}" font-weight="bold" fill="{tcolor or stroke}">{xe(title)}</text>')
        yy=y+39
        for ln in sub.split("\n"):
            if ln: s.p.append(f'<text x="{x+11}" y="{yy}" font-size="10.6" fill="#333">{xe(ln)}</text>'); yy+=15
    def edge(s,p1,p2,label,kind="req",mid=0.5,loff=-6):
        c,dash,wd=KIND[kind]; d=' stroke-dasharray="6 4"' if dash else ''
        s.p.append(f'<line x1="{p1[0]}" y1="{p1[1]}" x2="{p2[0]}" y2="{p2[1]}" stroke="{c}" stroke-width="{wd}"{d} marker-end="url(#a{kind})"/>')
        mx,my=p1[0]+(p2[0]-p1[0])*mid,p1[1]+(p2[1]-p1[1])*mid
        s.p.append(f'<rect x="{mx-len(label)*3.2-4}" y="{my+loff-11}" width="{len(label)*6.4+8}" height="15" rx="3" fill="#fff" fill-opacity="0.85"/>')
        s.p.append(f'<text x="{mx}" y="{my+loff}" font-size="10" fill="{c}" text-anchor="middle">{xe(label)}</text>')
    def text(s,x,y,t,size=12,color="#1A1A1A",weight="normal",anchor="start"):
        s.p.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{xe(t)}</text>')
    def out(s): return "\n".join(s.p)+"\n</svg>\n"

# ---------- DrawIO builder ----------
class DIO:
    def __init__(s,w,h): s.w,s.h=w,h; s.c=[]; s.i=1
    def _id(s): s.i+=1; return f"n{s.i}"
    def box(s,x,y,w,h,title,sub="",fill="#fff",stroke=AZ,tcolor=None,dash=False,fs=12.5):
        val=title+("\n"+sub if sub else "")
        st=f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.7;verticalAlign=top;align=left;spacingLeft=8;spacingTop=5;fontSize={fs};fontColor={tcolor or stroke};"
        if dash: st+="dashed=1;dashPattern=8 5;"
        s.c.append(f'<mxCell id="{s._id()}" value="{xe(val)}" style="{st}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    def edge(s,p1,p2,label,kind="req",mid=0.5,loff=0):
        c,dash,wd=KIND[kind]; d="dashed=1;dashPattern=6 4;" if dash else ""
        st=f"endArrow=classic;html=1;strokeColor={c};strokeWidth={wd};{d}fontSize=10;fontColor={c};labelBackgroundColor=#ffffff;rounded=0;"
        s.c.append(f'<mxCell id="{s._id()}" value="{xe(label)}" style="{st}" edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="{p1[0]}" y="{p1[1]}" as="sourcePoint"/><mxPoint x="{p2[0]}" y="{p2[1]}" as="targetPoint"/></mxGeometry></mxCell>')
    def text(s,x,y,t,size=12,color="#1A1A1A",weight="normal",anchor="start"):
        al={"start":"left","middle":"center","end":"right"}[anchor]; fs="fontStyle=1;" if weight=="bold" else ""
        w=max(60,int(len(t)*size*0.6)); tx=x if anchor=="start" else (x-w/2 if anchor=="middle" else x-w)
        s.c.append(f'<mxCell id="{s._id()}" value="{xe(t)}" style="text;html=1;align={al};verticalAlign=middle;fontSize={size};fontColor={color};{fs}" vertex="1" parent="1"><mxGeometry x="{tx}" y="{y-size}" width="{w}" height="{size+8}" as="geometry"/></mxCell>')
    def out(s):
        return (f'<mxfile host="app.diagrams.net"><diagram name="View 2 logical — Anthropic via Foundry+APIM">'
                f'<mxGraphModel dx="{s.w}" dy="{s.h}" grid="0" page="1" pageWidth="{s.w}" pageHeight="{s.h}">'
                f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>'+"\n".join(s.c)+'</root></mxGraphModel></diagram></mxfile>\n')

# anchors
def RM(b): return (b[0]+b[2], b[1]+b[3]/2)
def LM(b): return (b[0], b[1]+b[3]/2)
def TM(b): return (b[0]+b[2]/2, b[1])
def BM(b): return (b[0]+b[2]/2, b[1]+b[3])

def layout(s):
    W=1760
    s.text(W/2,32,"View 2 (LOGICAL) — Serving Anthropic (Claude) via Microsoft Foundry + APIM: request flow & relationships",20,"#111","bold","middle")
    s.text(W/2,54,"Logical interaction view (complements the landing-zone reference view). Typed edges: request · response · identity · dependency · govern · observe.",12,MUT,"normal","middle")
    # network substrate band
    s.box(40,70,1680,30,"Private network substrate — all flows traverse Private Endpoints → Hub Firewall · Private DNS (spoke↔hub peering) · no public model egress","",NET_F,NET_B,fs=11)
    # nodes (x,y,w,h)
    entra=(60,150,250,66); client=(60,300,250,150); appgw=(60,520,250,66)
    apim=(430,250,330,250); micro=(430,560,330,130)
    foundry=(910,250,300,210); claude=(1350,300,360,120); deps=(910,540,300,130)
    gov=(60,760,1660,150)
    s.box(*entra,"Entra ID — identity plane","OAuth2 / OIDC · app registrations\nWorkload identity (Agent 365)",ENT_F,ENT,tcolor="#5B3FA6")
    s.box(*client,"Clients / consumers","Claude Code — Web + CLI\nApplication users (browser)\narchitect-v1 · dev-agent · external apps",ANT_F,ANT_B,tcolor=ANT_T)
    s.box(*appgw,"Application Gateway + WAF","app UX traffic only",fill="#EAF1FB",stroke=AZ)
    s.box(*apim,"APIM — AI Gateway","Single governed entry for model calls:\n• validate Entra JWT / scopes\n• token limit · quota · rate limit\n• semantic cache (Redis)\n• content safety / PII\n• usage metering · routing",GW_F,GW_B,tcolor=GW_T)
    s.box(*micro,"GenAI microservices (Container Apps)","architect-v1 · capability-mcp · dev-agent\nfrontend · ingestion (Dapr)",fill="#EAF1FB",stroke=AZ)
    s.box(*foundry,"Microsoft Foundry / AI Foundry Project","Agent 365 / Foundry Agent Service\nConnections · Managed Identity\nhosts the model deployment",fill="#fff",stroke=AZ)
    s.box(*claude,"Anthropic CLAUDE","Foundry model deployment\nOpus / Sonnet / Haiku",ANT_F,ANT_B,tcolor=ANT_T)
    s.box(*deps,"Foundry / agent dependencies","Key Vault · AI Search (grounding)\nCosmos DB · Storage",fill="#fff",stroke=AZ)
    s.box(*gov,"Cross-cutting governance & observability plane","",fill="#FBFBFD",stroke="#9AA0A6")
    # governance chips
    s.text(80,800,"Security & governance:",11,"#222","bold","start")
    for j,(lab,col) in enumerate([("Microsoft Defender",SEC_B),("Purview (data governance)",SEC_B),("Azure Policy (guardrails)",NET_B),("Entra ID (identity)",ENT)]):
        s.box(80+j*210,808,196,34,lab,"",fill="#fff",stroke=col,fs=10.5)
    s.text(80,872,"Observability:",11,"#222","bold","start")
    for j,lab in enumerate(["Monitor / Log Analytics","Diagnostic settings","App Insights","Alerts"]):
        s.box(180+j*200,856,188,34,lab,"",fill="#F1ECF8",stroke=MON,fs=10.5)
    # ---- relationships (typed, numbered) ----
    s.edge(TM(client),(client[0]+90,entra[1]+entra[3]),"1 acquire token","id",mid=0.5,loff=-4)
    s.edge((client[0]+client[2],client[1]+50),(apim[0],apim[1]+60),"2 model call + Bearer JWT","req")
    s.edge((apim[0],apim[1]+30),(entra[0]+entra[2],entra[1]+entra[3]-12),"3 validate JWT / scopes","id",mid=0.45,loff=-4)
    s.edge((apim[0]+apim[2],apim[1]+70),(foundry[0],foundry[1]+60),"5 route (private)","req")
    s.edge(RM(foundry),LM(claude),"6 inference","req")
    s.edge((claude[0],claude[1]+claude[3]-20),(apim[0]+apim[2],apim[1]+apim[3]-30),"7 response","resp",mid=0.5,loff=12)
    s.edge((apim[0],apim[1]+apim[3]-30),(client[0]+client[2],client[1]+110),"7 response (usage metered)","resp",mid=0.5,loff=12)
    s.edge((client[0]+90,client[1]+client[3]),(appgw[0]+120,appgw[1]),"app users","req",mid=0.5,loff=-4)
    s.edge(RM(appgw),(micro[0],micro[1]+30),"8 app UX","req")
    s.edge(TM(micro),(apim[0]+120,apim[1]+apim[3]),"9 model calls (same gateway)","req",mid=0.5,loff=-4)
    s.edge(RM(micro),LM(deps),"10 secrets · grounding · state","dep")
    s.edge(BM(foundry),TM(deps),"11 agent deps","dep")
    # governance/observe (dashed up into plane)
    s.edge((apim[0]+60,apim[1]+apim[3]),(apim[0]+60,gov[1]),"govern","gov",mid=0.55,loff=-2)
    s.edge((foundry[0]+150,foundry[1]+foundry[3]),(foundry[0]+150,gov[1]),"govern + observe","gov",mid=0.7,loff=-2)
    s.edge((micro[0]+250,micro[1]+micro[3]),(micro[0]+250,gov[1]),"observe","obs",mid=0.6,loff=-2)
    # legend
    s.text(1240,792,"Edges:  ── request   ┄ response   ┄ identity   ── dependency   ┄ govern   ┄ observe",10.5,"#333","bold","start")

# build SVG (+png) and drawio
sv=SVG(1760,940); layout(sv); open("view2-logical.svg","w").write(sv.out())
di=DIO(1760,940); layout(di); open("view2-logical.drawio","w").write(di.out())
print("wrote view2-logical.svg, view2-logical.drawio")
