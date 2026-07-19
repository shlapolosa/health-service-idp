#!/usr/bin/env python3
"""Emit editable draw.io (mxGraph) files for the two views — same layout as the PNGs.
Open in https://app.diagrams.net . Cells are draggable; edit and re-export PNG/SVG from draw.io."""
from html import escape

def xesc(s): return escape(str(s), quote=True)

class DrawIO:
    """Same method surface as the SVG builder, but emits mxGraph cells (absolute coords, parent='1')."""
    def __init__(self, w, h):
        self.w, self.h = w, h; self.cells=[]; self._id=1
    def _nid(self): self._id+=1; return f"n{self._id}"
    def _cell(self, x, y, w, h, value="", style=""):
        i=self._nid()
        self.cells.append(f'<mxCell id="{i}" value="{xesc(value)}" style="{style}" vertex="1" parent="1">'
                          f'<mxGeometry x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" as="geometry"/></mxCell>')
        return i
    def rect(self, x, y, w, h, fill="none", stroke="#888", sw=1.2, rx=6, dash=None):
        fc = "none" if fill=="none" else fill
        st=f"rounded=1;whiteSpace=wrap;html=1;fillColor={fc};strokeColor={stroke};strokeWidth={sw};"
        if dash: st+="dashed=1;dashPattern=6 4;"
        self._cell(x,y,w,h,"",st)
    def container(self, x, y, w, h, title, fill, stroke, dash=None, tcolor=None):
        st=(f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.6;"
            f"verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontStyle=1;fontSize=13;"
            f"fontColor={tcolor or stroke};")
        if dash: st+="dashed=1;dashPattern=8 5;"
        self._cell(x,y,w,h,title,st)
    def text(self, x, y, s, size=12, color="#1A1A1A", weight="normal", anchor="start"):
        align={"start":"left","middle":"center","end":"right"}[anchor]
        fs="fontStyle=1;" if weight=="bold" else ""
        w=max(40,int(len(s)*size*0.62));
        tx = x if anchor=="start" else (x-w/2 if anchor=="middle" else x-w)
        st=f"text;html=1;align={align};verticalAlign=middle;fontSize={size};fontColor={color};{fs}"
        self._cell(tx, y-size, w, size+8, s, st)
    def line(self, x1, y1, x2, y2, stroke="#444", sw=1.4, dash=None, arrow=False):
        i=self._nid(); end="classic" if arrow else "none"
        d="dashed=1;dashPattern=6 4;" if dash else ""
        st=f"endArrow={end};html=1;strokeColor={stroke};strokeWidth={sw};{d}rounded=0;"
        self.cells.append(f'<mxCell id="{i}" style="{st}" edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{x1:.0f}" y="{y1:.0f}" as="sourcePoint"/>'
            f'<mxPoint x="{x2:.0f}" y="{y2:.0f}" as="targetPoint"/></mxGeometry></mxCell>')
    def chips(self, items, x, y, maxx, ch=30, gap=8, fill="#FFFFFF", stroke="#BBD6F2",
              tcolor="#1A1A1A", size=11, padx=9, line_gap=8):
        cx, cy = x, y
        for label in items:
            cw=int(len(label)*(size*0.58))+padx*2
            if cx+cw>maxx and cx>x: cx=x; cy+=ch+line_gap
            st=(f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                f"fontSize={size};fontColor={tcolor};align=center;verticalAlign=middle;")
            self._cell(cx,cy,cw,ch,label,st); cx+=cw+gap
        return cy+ch
    def out(self, name):
        body="\n".join(self.cells)
        return (f'<mxfile host="app.diagrams.net">\n<diagram name="{xesc(name)}">\n'
                f'<mxGraphModel dx="{self.w}" dy="{self.h}" grid="0" gridSize="10" guides="1" '
                f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
                f'pageWidth="{self.w}" pageHeight="{self.h}" math="0" shadow="0">\n<root>\n'
                f'<mxCell id="0"/>\n<mxCell id="1" parent="0"/>\n{body}\n</root>\n</mxGraphModel>\n</diagram>\n</mxfile>\n')

# palettes (shared with the SVG generator)
AZ="#0F6CBD"; AZ_FILL="#EAF1FB"; SUBFILL="#F4F8FE"; RGFILL="#FBFCFE"; RGB="#9CC3EB"
WHITE="#FFFFFF"; INNERB="#BBD6F2"
ANT_F="#F4E3DC"; ANT_B="#CC785C"; ANT_T="#8A4B38"
SEC_F="#FDE7E9"; SEC_B="#D26B72"; SEC_T="#8E2F36"
GOV_F="#FFF4CE"; GOV_B="#C9A227"; GOV_T="#7A5F00"
MON_F="#EEE7F6"; MON_B="#8B6CB8"; MON_T="#4E3A78"
GW_F="#E2F1F0"; GW_B="#2E8B84"; GW_T="#1E5C57"; MUT="#555555"

# ---------------- VIEW 1 ----------------
def view1():
    s=DrawIO(1120,640)
    s.text(560,40,"View 1 — Standard Claude Code consuming Anthropic models (direct SaaS)",20,"#111","bold","middle")
    s.text(560,64,"No Azure landing zone / gateway · Anthropic-hosted · customer-managed API key or OAuth",12.5,MUT,"normal","middle")
    s.container(120,100,380,150,"Client surfaces",AZ_FILL,AZ)
    s.chips(["Claude Code — Web (claude.ai/code)"],150,135,470,ch=40,fill=WHITE,stroke=AZ,size=12.5)
    s.chips(["Claude Code — CLI (terminal / IDE extensions)"],150,190,490,ch=40,fill=WHITE,stroke=AZ,size=12.5)
    s.rect(120,300,380,46,fill=GOV_F,stroke=GOV_B); s.text(310,328,"HTTPS / TLS · API key (Bearer) or OAuth",12.5,GOV_T,"bold","middle")
    s.container(640,100,360,150,"Anthropic (SaaS)",ANT_F,ANT_B,tcolor=ANT_T)
    s.chips(["Anthropic API — api.anthropic.com"],666,135,980,ch=40,fill=WHITE,stroke=ANT_B,size=12.5,tcolor=ANT_T)
    s.chips(["Claude models — Opus 4.x · Sonnet · Haiku"],666,190,1000,ch=40,fill=WHITE,stroke=ANT_B,size=12.5,tcolor=ANT_T)
    s.container(640,300,360,150,"Anthropic-side controls",ANT_F,ANT_B,tcolor=ANT_T)
    s.chips(["Org / workspace + members","Usage & rate limits","Data-retention controls","Audit logs"],
            666,330,990,ch=30,fill=WHITE,stroke=ANT_B,size=11,tcolor=ANT_T)
    s.line(500,175,640,175,arrow=True,sw=1.8); s.text(570,165,"prompt / completion",11,MUT,"normal","middle")
    s.line(820,250,820,300,stroke=ANT_B,sw=1.6,arrow=True)
    s.line(310,250,310,300,stroke=GOV_B,sw=1.4,arrow=True); s.text(310,275,"auth on every call",11,GOV_T,"normal","middle")
    s.text(560,500,"Trust boundary: the client talks straight to Anthropic's SaaS API. Governance (identity, quota, retention, audit) lives in the Anthropic org/workspace —",12.5,"#222","normal","middle")
    s.text(560,520,"there is no Azure tenant, landing zone, APIM gateway, Entra, Defender or Purview in this path.",12.5,"#222","normal","middle")
    open("view1-claude-code-direct.drawio","w").write(s.out("View 1 — Claude Code direct to Anthropic"))

# ---------------- VIEW 2 ----------------
def view2():
    W,H=1780,1372; s=DrawIO(W,H); L,R=24,W-24
    s.text(W/2,34,"View 2 — Serving Anthropic (Claude) via Microsoft Foundry + APIM on Azure AI Landing Zones",21,"#111","bold","middle")
    s.text(W/2,57,"Same control plane as the current GPT-5.4 implementation — only the Foundry model deployment changes (Claude instead of GPT-5.4). Agent 365 / Foundry Agent Service · Entra ID · APIM AI Gateway · Defender/Purview.",12.5,MUT,"normal","middle")
    # client layer
    s.container(L,74,R-L,58,"Client / Consumer layer  (outside the Azure tenant)","#FDF1EC",ANT_B,tcolor=ANT_T)
    s.chips(["Claude Code — Web (claude.ai/code)","Claude Code — CLI (terminal / IDE)","Application users (browser)",
             "Programmatic consumers — architect-v1 · dev-agent · external apps"],
            L+14,100,1300,ch=28,fill=WHITE,stroke=ANT_B,tcolor=ANT_T,size=11)
    s.text(1320,118,"model calls → APIM (AI Gateway) · app UX → Application Gateway",10.5,MUT,"bold","start")
    s.line(900,132,900,160,stroke=ANT_B,sw=1.6,arrow=True)
    s.text(900,176,"↓ Entra-authenticated calls into the landing zones",10,ANT_T,"normal","middle")
    # A management groups
    s.container(L,168,R-L,80,"Management Groups (Azure tenant) — landing-zone hierarchy + tenant governance",AZ_FILL,AZ)
    s.chips(["Org Root","Platform LZ","Connectivity","Application LZ","Corp","AI Landing-Zone Governance Hub"],
            L+14,192,980,ch=28,fill=WHITE,stroke=AZ,size=11)
    s.chips(["Role assignments (RBAC)","Policy assignments (Azure Policy)","Tags","Blueprints / guardrails"],
            1010,192,R-14,ch=28,fill=GOV_F,stroke=GOV_B,tcolor=GOV_T,size=11)
    # B connectivity
    s.container(L,258,R-L,112,"Connectivity Subscription (Platform) — Hub VNet (region 1..N) · DNS provided by hub",SUBFILL,AZ)
    s.chips(["On-premises / ExpressRoute","Azure Firewall (+ policies)","DNS Private Resolver","Private DNS Zones",
             "VPN / ExpressRoute Gateways","DDoS Protection","Azure Bastion"],L+14,286,R-14,ch=28,fill=WHITE,stroke=INNERB,size=11)
    s.text(L+14,360,"VNet peering to spoke landing zones (Foundry + AI Gateway)",11,MUT,"bold","start")
    # C foundry LZ
    cy=384; ch=452
    s.container(L,cy,R-L,ch,"Foundry Landing Zone Subscription  (spoke · region-1 stamp)",SUBFILL,"#4A90D9",dash="7 5")
    rgx,rgy,rgw,rgh=L+16,cy+30,R-L-32,ch-100
    s.container(rgx,rgy,rgw,rgh,"AI Agent Resource Group",RGFILL,RGB); colw=(rgw-48)/3
    x1=rgx+16; y1=rgy+34
    s.container(x1,y1,colw,rgh-58,"Microsoft Foundry · AI Foundry Project",WHITE,AZ)
    yy=s.chips(["Foundry models = ANTHROPIC CLAUDE (Opus/Sonnet/Haiku)"],x1+14,y1+34,x1+colw-14,ch=40,fill=ANT_F,stroke=ANT_B,tcolor=ANT_T,size=11.5)
    yy=s.chips(["Agents = Agent 365 / Foundry Agent Service","Connections","Managed Identities","AI Services endpoints"],x1+14,yy+10,x1+colw-14,ch=30,fill=WHITE,stroke=INNERB,size=10.5)
    s.chips(["architect-v1 (Foundry agent)","grounding w/ Bing","AI Search"],x1+14,yy+10,x1+colw-14,ch=28,fill="#EFF6EF",stroke="#6FAE6F",size=10)
    x2=x1+colw+16
    s.container(x2,y1,colw,rgh-58,"Foundry dependencies (private)",WHITE,AZ)
    s.chips(["Storage Account","AI Search","Cosmos DB","Key Vault","Container Registry","App Configuration"],x2+14,y1+34,x2+colw-14,ch=30,fill=WHITE,stroke=INNERB,size=10.5)
    s.text(x2+14,y1+150,"All reached over Private Endpoints",10.5,MUT,"normal","start")
    s.chips(["Private Endpoints subnet","Jump box subnet","Build agent subnet","UDR → hub firewall"],x2+14,y1+165,x2+colw-14,ch=28,fill=AZ_FILL,stroke=AZ,size=10)
    x3=x2+colw+16
    s.container(x3,y1,colw,rgh-58,"AI Services VNet (spoke) — App stamp",WHITE,AZ)
    s.chips(["App Gateway (+ WAF)","Foundry Agent subnet","Container App Environment subnet"],x3+14,y1+34,x3+colw-14,ch=28,fill=AZ_FILL,stroke=AZ,size=10)
    s.text(x3+14,y1+110,"Container App Environment — GenAI microservices (Dapr):",10.5,"#222","bold","start")
    s.chips(["capability-mcp (MCP)","architect orchestrator","dev-agent (build/CI)","frontend","ingestion"],x3+14,y1+122,x3+colw-14,ch=28,fill="#EAF1FB",stroke=AZ,size=10)
    s.text(x3+14,y1+200,"Application users → App Gateway → microservices",10,MUT,"normal","start")
    fy=rgy+rgh+8
    s.rect(rgx,fy,rgw,40,fill="#FAFAFC",stroke="#DDDDDD"); s.text(rgx+12,fy+25,"Security & governance:",11,"#222","bold","start")
    s.chips(["Microsoft Defender","Entra ID","Purview"],rgx+150,fy+5,rgx+520,ch=30,fill=SEC_F,stroke=SEC_B,tcolor=SEC_T,size=10.5)
    s.chips(["Monitor","Diagnostic settings","App Insights","Log Analytics","Network Watcher"],rgx+540,fy+5,rgx+rgw-10,ch=30,fill=MON_F,stroke=MON_B,tcolor=MON_T,size=10.5)
    # D gateway LZ
    gy=856; gh=470
    s.container(L,gy,R-L,gh,"AI Gateway Landing Zone Subscription  (spoke · region-1 stamp)",SUBFILL,"#4A90D9",dash="7 5")
    rg2x,rg2y,rg2w,rg2h=L+16,gy+30,R-L-32,gh-100
    s.container(rg2x,rg2y,rg2w,rg2h,"AI Hub Resource Group",RGFILL,RGB); cw=(rg2w-48)/3
    a1=rg2x+16; b1=rg2y+34
    s.container(a1,b1,cw,rg2h-58,"Microsoft Foundry Service",WHITE,AZ)
    s.chips(["Connections","Foundry models (Claude)","Managed Identities"],a1+14,b1+34,a1+cw-14,ch=30,fill=ANT_F,stroke=ANT_B,tcolor=ANT_T,size=10.5)
    s.text(a1+14,b1+150,"AI Hub VNet (spoke) subnets:",10.5,"#222","bold","start")
    s.chips(["Private Endpoints","Logic App subnet","UDR → hub firewall"],a1+14,b1+162,a1+cw-14,ch=28,fill=AZ_FILL,stroke=AZ,size=10)
    a2=a1+cw+16
    s.container(a2,b1,cw,rg2h-58,"AI Gateway — API Management subnet",GW_F,GW_B,tcolor=GW_T)
    s.chips(["APIM (aigw-apim-dev) — serves ANTHROPIC models"],a2+14,b1+34,a2+cw-14,ch=40,fill=ANT_F,stroke=ANT_B,tcolor=ANT_T,size=11)
    s.chips(["AI Gateway (API Center / Universal AI Registry)","Entra-secured products & subscriptions","token limits · quotas · semantic cache","Logic Apps (usage ingestion)"],a2+14,b1+84,a2+cw-14,ch=30,fill=WHITE,stroke=GW_B,tcolor=GW_T,size=10.5)
    s.text(a2+14,b1+rg2h-90,"Consumers (architect-v1 · dev-agent · external apps) → APIM → Foundry (Claude)",10,GW_T,"normal","start")
    a3=a2+cw+16
    s.container(a3,b1,cw,rg2h-58,"Pluggable Safety + Governance Supporting Services",WHITE,AZ)
    s.chips(["Content Safety","Language / PII processing"],a3+14,b1+34,a3+cw-14,ch=30,fill=SEC_F,stroke=SEC_B,tcolor=SEC_T,size=10.5)
    s.chips(["Event Hub","Cosmos DB","Key Vault","Storage","Managed Redis (semantic cache)"],a3+14,b1+74,a3+cw-14,ch=28,fill=WHITE,stroke=INNERB,size=10)
    s.chips(["Gov Workflows (Logic Apps)","AI Registry (API Center)","Monitor · Alerts · Log Analytics"],a3+14,b1+146,a3+cw-14,ch=28,fill=MON_F,stroke=MON_B,tcolor=MON_T,size=10)
    f2=rg2y+rg2h+8
    s.rect(rg2x,f2,rg2w,40,fill="#FAFAFC",stroke="#DDDDDD"); s.text(rg2x+12,f2+25,"Security & governance:",11,"#222","bold","start")
    s.chips(["Microsoft Defender","Entra ID","Purview"],rg2x+150,f2+5,rg2x+520,ch=30,fill=SEC_F,stroke=SEC_B,tcolor=SEC_T,size=10.5)
    s.text(rg2x+560,f2+25,"Role assignments · Policy assignments · Tags (inherited from management group)",10.5,GOV_T,"normal","start")
    # peering rail
    s.line(14,311,14,616,stroke="#4A90D9",sw=2,dash="5 5"); s.line(14,311,L,311,stroke="#4A90D9",sw=2)
    s.line(14,576,L,576,stroke="#4A90D9",sw=2,arrow=True); s.line(14,1076,L,1076,stroke="#4A90D9",sw=2,arrow=True)
    s.line(14,616,14,1076,stroke="#4A90D9",sw=2,dash="5 5"); s.text(20,301,"VNet peering",10,"#4A90D9","normal","start")
    s.text(W/2,1354,"Request path: Consumer → APIM (AI Gateway, Entra-authenticated, quota/cache/safety) → Microsoft Foundry (Foundry model deployment = Claude) → response.   Identity: Entra ID · Agents: Agent 365 / Foundry Agent Service · Governance: Defender + Purview + Azure Policy.",11.5,"#222","normal","middle")
    open("view2-anthropic-foundry-apim-landingzones.drawio","w").write(s.out("View 2 — Anthropic via Foundry + APIM on AI Landing Zones"))

view1(); view2()
print("wrote view1-claude-code-direct.drawio, view2-anthropic-foundry-apim-landingzones.drawio")
