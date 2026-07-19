from html import escape
def xe(s): return escape(str(s),quote=True)
W,H=1620,880
INK="#1F2937";MUT="#6B7280"
SC={"green":"#15803D","amber":"#D97706","grey":"#6B7280","blue":"#2563EB"}
FL={"green":"#E7F5EC","amber":"#FEF3E2","grey":"#FFFFFF","blue":"#2563EB"}
RED="#DC2626"; REDF="#FDECEA"; BANDBG="#F1F2F4"; BANDBR="#C9CDD3"
p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif">',f'<rect width="{W}" height="{H}" fill="#fff"/>']
p.append('<defs><marker id="ak" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0L7,3L0,6Z" fill="#666"/></marker></defs>')
def rr(x,y,w,h,fill,stroke,sw=1.4,rx=10):
    p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def tx(x,y,s,sz=12,c=INK,b=False,a="start"):
    p.append(f'<text x="{x}" y="{y}" font-size="{sz}" fill="{c}" font-weight="{"bold" if b else "normal"}" text-anchor="{a}">{xe(s)}</text>')
def wrap(s,n):
    o=[];cur=""
    for w_ in s.split():
        if len(cur)+len(w_)+1>n:o.append(cur);cur=w_
        else:cur=(cur+" "+w_).strip()
    o.append(cur);return o
def card(x,y,w,h,num,title,sub,state):
    col=SC[state]; rr(x,y,w,h,FL[state],col,2.0)
    p.append(f'<circle cx="{x+15}" cy="{y+15}" r="10" fill="{col}"/>'); tx(x+15,y+19,str(num),10,"#fff",True,"middle")
    yy=y+17
    for i,ln in enumerate(wrap(title,18)): tx(x+31 if i==0 else x+11, yy, ln, 11.5, INK, True); yy+=14
    for ln in (wrap(sub,22) if sub else []): tx(x+11,yy+3,ln,9,MUT); yy+=12
def mbox(x,y,w,h,lines,sub=None):  # blue milestone box
    rr(x,y,w,h,SC["blue"],SC["blue"],2,12)
    p.append(f'<text x="{x+w/2}" y="{y+h*0.30}" font-size="22" fill="#fff" font-weight="bold" text-anchor="middle">★</text>')
    base=y+h*0.30+22
    for j,ln in enumerate(lines): tx(x+w/2,base+j*18,ln,13,"#fff",True,"middle")
    if sub: tx(x+w/2,base+len(lines)*18+8,sub,9.5,"#DCE7FB",False,"middle")
def gblock(x,y,w,h,lines):  # grey block
    rr(x,y,w,h,"#FFFFFF",SC["grey"],2,10)
    for j,ln in enumerate(lines): tx(x+w/2,y+h/2-(len(lines)-1)*9+j*18+4,ln,12,INK,True,"middle")
def arrow(pts,sw=1.8):
    dp="M "+" L ".join(f"{a} {b}" for a,b in pts)
    p.append(f'<path d="{dp}" fill="none" stroke="#666" stroke-width="{sw}" marker-end="url(#ak)"/>')

tx(W/2,40,"AI adoption — delivery roadmap (v0.2): two phases in parallel",26,INK,True,"middle")
tx(W/2,66,"Phase 1 (AI Agents) delivers now · Phase 2 (Agentic AI platform) runs in parallel — architecture & pricing finalised",13,MUT,"normal","middle")
for j,(lab,st) in enumerate([("Completed","green"),("In progress","amber"),("Milestone","blue"),("Not started","grey")]):
    lx=966+j*162; rr(lx,80,15,15,FL[st] if st!="grey" else "#FFFFFF",SC[st],2,3); tx(lx+22,92,lab,11,INK)

COL=[200,350,500,650,800,950]; CW=132
P1y=150; PLATy=366; PROCy=458; PEOPy=550; COEy=704; ch=84
rr(14,110,1592,206,BANDBG,BANDBR,1.4,12)
rr(14,332,1592,332,BANDBG,BANDBR,1.4,12)
rr(14,680,1592,118,BANDBG,BANDBR,1.4,12)
tx(26,150,"PHASE 1 · AI AGENTS",13,INK,True); tx(26,168,"deliver with AI agents",10,MUT)
tx(26,356,"PHASE 2 · AGENTIC AI",13,INK,True); tx(26,372,"(in parallel)",10,MUT)
tx(26,PLATy+34,"Platform",12,INK,True); tx(26,PROCy+34,"Process",12,INK,True); tx(26,PEOPy+34,"People",12,INK,True)
tx(26,724,"CENTER OF EXCELLENCE",12,INK,True)

P1=[("Scope, mandate, charter","","green"),("Collect use cases","Intake from business","green"),("Create solutions","Architecture per case","green"),("Allocate to teams","Ownership assigned","green"),("Teams prioritise","Sequencing per team","amber"),("Implement phase 1","Build skills, tools, agents","amber")]
PLAT=[("Architecture definition","","green"),("MS reference architecture","","green"),("DHS discovery & consolidate","","green"),("Cost estimate","","amber"),("Provisioning","","grey")]
PROC=[("Establish CoE","","grey"),("Resourcing","","grey"),("Operating model","phase 1 → phase 2","grey")]
PEOP=[("Team structure","","grey"),("Internal talent","","grey"),("External talent","","grey"),("Training schedule","","grey")]
COEL=[("Scope, mandate, charter","","amber"),("Contract partners","Microsoft · Delphi","amber"),("Collect use cases","","amber"),("Operating model","","amber"),("Adopt architecture + tools","","amber")]
def lane(cards,y):
    for i,(t,s,st) in enumerate(cards):
        x=COL[i]; card(x,y,CW,ch,i+1,t,s,st)
        if i>0: arrow([(COL[i-1]+CW,y+ch/2),(x,y+ch/2)])
lane(P1,P1y); lane(PLAT,PLATy); lane(PROC,PROCy); lane(PEOP,PEOPy); lane(COEL,COEy)

# Phase 1 -> Agent Capabilities (blue) at the end
AX=1108; mbox(AX,P1y,132,ch,["Agent","Capabilities"])
arrow([(COL[5]+CW,P1y+ch/2),(AX,P1y+ch/2)])
# Phase 1 challenges box (light red)
rr(200,250,882,52,REDF,RED,1.6,8)
tx(214,272,"⚠  Phase 1 challenges",12.5,RED,True)
tx(214,290,"Audit finding (policy controls) · rate limits · ability to use agents",11,INK)
# Phase 2 milestone (blue), spans rows
MX=1108; mbox(MX,PLATy,132,PEOPy+ch-PLATy,["Agentic AI","capability"],"milestone")
arrow([(COL[4]+CW,PLATy+ch/2),(MX,PLATy+ch/2)])
arrow([(COL[2]+CW,PROCy+ch/2),(MX,PROCy+ch/2)])
arrow([(COL[3]+CW,PEOPy+ch/2),(MX,PEOPy+ch/2)])
# consolidated + kickoff #1
CX=1262; gblock(CX,PROCy-3,150,ch+6,["Consolidated","Accenture","Agentic AI"])
K1=1438; gblock(K1,PROCy-3,150,ch+6,["Kickoff","factory"])
arrow([(MX+132,PROCy+ch/2),(CX,PROCy+ch/2)])
arrow([(CX+150,PROCy+ch/2),(K1,PROCy+ch/2)])
# CoE -> Agentic AI capability (blue) -> its own kickoff (grey)
CM=1108; mbox(CM,COEy,132,ch,["Agentic AI","capability"])
K2=1438; gblock(K2,COEy,150,ch,["Kickoff","factory"])
arrow([(COL[4]+CW,COEy+ch/2),(CM,COEy+ch/2)])
arrow([(CM+132,COEy+ch/2),(K2,COEy+ch/2)])
tx(20,864,"HSO · Agentic AI delivery · v0.2",10,MUT)
p.append("</svg>")
open("roadmap-v2.svg","w").write("\n".join(p))
