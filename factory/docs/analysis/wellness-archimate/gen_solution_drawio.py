#!/usr/bin/env python3
"""Wellness Platform — Solution Architecture (C4 container/component), draw.io / mxGraph diagram-as-code.

Template style (banded layered architecture with trust-boundary zones, nested service containers,
typed connectors + legend). Enhancement over the template: connectors are orthogonal, fan to distinct
anchor points (exitX/entryX), routed in unique lanes — no diagonal, no trunk, no overlap with elements.

Stage 1 = banded layout + components + legend (this file emits it; edges added next).
Output: solution-architecture.drawio  (open/edit in https://app.diagrams.net)
"""
from xml.sax.saxutils import escape

W=1820                       # canvas width
ZX=40; ZW=W-80               # zone x + width (full-width bands)
COMPH=78                     # component height

# ---- bands (top -> down): id, label, stroke, fill, height ----  (y auto-stacked) ----
_BANDS=[
 ("z_client","Sahatna Client (citizen app)","#D79B00","#FFF6E6",118),
 ("z_apim_n","Integration North","#3A7CA5","#E6F1F7",110),
 ("z_bff","Sahatna (server-side)","#6C8EBF","#EAF1FB",118),
 ("z_admin","Platform Client (admin / partner console)","#2E6E8E","#E6F1F7",112),
 ("z_apim_s","Integration South","#3A7CA5","#E6F1F7",110),
 ("z_engine","Gamification Engine","#82B366","#EEF7E9",244),
 ("z_value","Wallet & Marketplace","#9673A6","#F3EEF8",244),
 ("z_persist","Persistence","#D6B656","#FFFBEC",128),
 ("z_trust","PARTNER TRUST BOUNDARY","#C9A100","#FBE9A0",46),
 ("z_external","External Partner APIs","#B85450","#FBECEC",128),
 ("z_platform","Platform Services","#666666","#F5F5F5",128),
 ("z_xcut","Cross-cutting","#666666","#F5F5F5",118),
]
GAP_BAND=80; _y=90
ZONES=[]
for zid,label,stroke,fill,h in _BANDS:
    ZONES.append((zid,label,stroke,fill,_y,h)); _y+=h+GAP_BAND
ZMETA={z[0]:z for z in ZONES}

# ---- components: id, zone, title, desc(\n), [optional explicit col 0..n-1 of that row], row(0/1) ----
# col is assigned left->right automatically per (zone,row) unless given.
COMPS=[
 # client
 ("cl_chal","z_client","Challenges","active list · join · progress\nclinical / demographic / telemetry mix",0,0),
 ("cl_wallet","z_client","Rewards & Wallet","points balance · transactions · vouchers\nre-display voucher (rate-limited)",1,0),
 ("cl_market","z_client","Marketplace & Redeem","item detail · confirm redemption\nIdempotency-Key (client UUIDv4)",2,0),
 ("cl_health","z_client","Health Connect SDK","on-device wearable telemetry source\nsteps · heart-rate · sleep · workouts",3,0),
 # api gateway north (citizen)
 ("apim_n","z_apim_n","Azure APIM — Citizen Gateway","JWT validation · rate-limit · routing\nproducts · subscription keys",0,0),
 ("idp_uaepass","z_apim_n","UAE Pass IdP","citizen identity federation (OIDC)\nnational ID · mints platform JWT",1,0),
 # bff
 ("bff_member","z_bff","Gamification Service","gameplay BFF · JWT relay · session\nfan-out: challenges · wallet · market",0,0),
 ("wearable_svc","z_bff","Wearable Service","ingest Health Connect SDK telemetry\nwrites telemetry to Event Hub",1,0),
 ("bff_admin","z_admin","Admin / Partner Console","partner onboarding · item approval · reconciliation\nno APIM ingress · connects to Platform APIM (south)",0,0),
 ("cms_sahatna","z_bff","Sahatna CMS","challenge CONTENT (copy · imagery · T&C)\nhydrates eligible challenge_ids → published",2,0),
 ("sah_notify","z_bff","Sahatna Notifications API","Sahatna OWNS end-user delivery (push·email·SMS·in-app)\nplatform calls via APIM · consent-gated · captures notify-consent → propagates down",3,0),
 # api gateway south (platform)
 ("apim_s","z_apim_s","Azure APIM — Platform Gateway","service-to-service (sync) · JWT · policy\nper-OAM product · mTLS",0,0),
 ("eh_integration","z_apim_s","Event Hub (EVENT-SVC)","async integration · Kafka + Lenses spine\nschema registry · activity.* · wallet.* · voucher.*",1,0),
 ("idp_entra","z_apim_s","Microsoft Entra IdP","workforce / service identity (OAuth2)\nB2B: Sahatna app-registration · client-credentials → token (via APIM)\nworkload/managed identity for direct Event-Hub ingest ACL",2,0),
 # engine row 0
 ("en_enrol","z_engine","Enrolment & Eligibility","resolve eligible challenges\nlocal-vs-Malaffi branch",0,0),
 ("en_cohort","z_engine","Local Segmentation","demographic/telemetry segments (local)\nclinical segments are external (Malaffi)",1,0),
 ("en_chal","z_engine","Challenge","authoring → publish → conclude\neligibility binding",2,0),
 ("en_verify","z_engine","Verification","wearable / activity verify\nemits activity.verified",3,0),
 ("en_score","z_engine","Scoring & Recognition","daily/weekly scoring\ntitles · badges · streaks",4,0),
 ("en_engage","z_engine","Engagement","nudges · goals · cohort plans",5,0),
 # engine row 1 (orchestrator / adapter)
 ("en_eligorch","z_engine","Eligibility Resolver","membership → segments → map to challenge_ids\nreturns ids; Sahatna CMS hydrates",0,1),
 ("en_maladapter","z_engine","Malaffi Adapter","segment metadata (author, no membership)\nscoped membership query (eligibility)",1,1),
 # value row 0
 ("wm_wallet","z_value","Wallet — Points Ledger","authoritative balance (versioned)\nappend-only · idempotent",0,0),
 ("wm_market","z_value","Marketplace & Voucher","catalog · reserve · issue voucher\nencrypted code/PIN",1,0),
 ("wm_partner","z_value","Partner & Settlement","contracting · reconciliation\nDoH settlement (Phase 4)",2,0),
 ("wm_fraud","z_value","Fraud & Integrity","anomaly detection\nvelocity / duplicate checks",3,0),
 # value row 1
 ("wm_redorch","z_value","Redemption Orchestrator (saga)","reserve → fraud → dispatch partner → confirm/release\nstate: reserved · partner_pending · fulfilled · uncertain",0,1),
 ("wm_padapter","z_value","Partner Adapter Framework","routing · auth · idempotency overlay\nYGG adapter · aggregator adapters",1,1),
 # persistence
 ("ps_wallet","z_persist","Wallet stores","WalletBalance · Transaction\nReservation (idempotency_key)",0,0),
 ("ps_engine","z_persist","Challenge & Cohort stores","Challenge · Segment · Score\nEligibility Result",1,0),
 ("ps_market","z_persist","Marketplace stores","Item · Redemption · Voucher\n(encrypted columns)",2,0),
 ("ps_kv","z_persist","Azure Key Vault","per-partner credentials\nversion-bumped rotation",3,0),
 # external
 ("ex_malaffi","z_external","Malaffi HIE","clinical membership / eligibility\nblack box · API only",0,0),
 ("ex_providers","z_external","Reward Providers","YouGotaGift (eGift v2.4) · aggregators\nvoucher issue / redeem",1,0),
 ("ex_doh","z_external","DoH ESB","sponsor · settlement (Phase 4)\nIBAN payouts · VAT invoice",2,0),
 # platform services (consumers of the integration Event Hub)
 ("pf_fraud","z_platform","FRAUD-SVC","anomaly detection\nDLQ signals",1,0),
 ("pf_nudge","z_platform","NUDGE-SVC","compose notification request (no channels of its own)\nconsent-checked → calls Sahatna Notifications API via APIM",2,0),
 ("pf_consent","z_platform","CONS-SVC","consent purpose · voucher / data sharing\nNOTIFY consent propagated from Sahatna · checked before notify",3,0),
 ("pf_id","z_platform","ID-SVC","session & token exchange\nmember ↔ platform identity",4,0),
 ("pf_data","z_platform","DATA-SVC","warehouse + analytics (OLAP)\nsettlement aggregation · dashboards",5,0),
 # cross-cutting
 ("xc_secrets","z_xcut","Secrets Management","Azure Key Vault + External Secrets\n<comp>-conn injection",0,0),
 ("xc_gitops","z_xcut","Declarative Provisioning","KubeVela + Crossplane + ArgoCD\nOAM control plane (GitOps)",1,0),
 ("xc_obs","z_xcut","Observability","Prometheus · Grafana · Jaeger · Kiali",2,0),
]

# ---------------- layout ----------------
PAD=18; GAP=26
pos={}                       # id -> (x,y,w,h)
# group comps by (zone,row)
from collections import defaultdict
rows=defaultdict(list)
for c in COMPS: rows[(c[1],c[5])].append(c)
for (zid,row),items in rows.items():
    items.sort(key=lambda c:c[4])
    z=ZMETA[zid]; zy=z[4]; zh=z[5]
    n=len(items); cw=min(300,(ZW-2*PAD-(n-1)*GAP)//n)
    rowh=COMPH
    total=n*cw+(n-1)*GAP; startx=ZX+(ZW-total)//2
    top=zy+30 + row*(rowh+40)
    for k,c in enumerate(items):
        x=startx+k*(cw+GAP)
        pos[c[0]]=(x,top,cw,rowh)

# ---------------- emit mxGraph ----------------
def esc(s): return escape(s).replace("\n","&#10;")
cells=[]
cid=2
def cell(s): cells.append(s)
# zones
for zid,label,stroke,fill,y,h in ZONES:
    fillv = fill if zid!="z_trust" else "#FBE9A0"
    dashed = "0" if zid=="z_trust" else "1"
    va = "middle" if zid=="z_trust" else "top"
    al = "center" if zid=="z_trust" else "left"
    fs = "13" if zid=="z_trust" else "12"
    cell(f'<mxCell id="{zid}" value="{esc(label)}" style="rounded=0;dashed={dashed};dashPattern=8 6;strokeColor={stroke};fillColor={fillv};verticalAlign={va};align={al};fontStyle=1;fontColor={stroke};fontSize={fs};spacingLeft=12;spacingTop=8;arcSize=4;opacity=100;" vertex="1" parent="1"><mxGeometry x="{ZX}" y="{y}" width="{ZW}" height="{h}" as="geometry"/></mxCell>')
# components
ZcompFill={"z_client":"#FFE6CC","z_apim_n":"#D7E8F2","z_bff":"#DAE8FC","z_admin":"#CCE5F5","z_apim_s":"#D7E8F2",
 "z_engine":"#D5E8D4","z_value":"#E1D5E7","z_persist":"#FFF2CC","z_external":"#F8CECC",
 "z_platform":"#EEEEEE","z_xcut":"#F5F5F5"}
for c in COMPS:
    i,zid,title,desc=c[0],c[1],c[2],c[3]
    x,y,w,h=pos[i]; stroke=ZMETA[zid][2]; fill=ZcompFill[zid]
    val="&lt;b&gt;"+esc(title)+"&lt;/b&gt;&#10;"+esc(desc)
    cell(f'<mxCell id="{i}" value="{val}" style="rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};align=center;verticalAlign=top;spacingTop=6;fontSize=10;arcSize=8;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
# ---------------- stage 2: typed connectors (A* orthogonal · obstacle-avoiding · fan anchors) ----------
from heapq import heappush,heappop
ESTYLE={"sync":"strokeColor=#1A1A1A;endArrow=block;",
        "async":"strokeColor=#777777;dashed=1;dashPattern=6 6;endArrow=open;",
        "xtrust":"strokeColor=#B85450;strokeWidth=2;endArrow=block;",
        "identity":"strokeColor=#9966AA;dashed=1;dashPattern=2 4;endArrow=open;"}
EDGES=[
 # sync (north path: client -> apim(uaepass) -> bff -> apim(entra) -> engine/value)
 ("cl_chal","apim_n","sync"),("cl_wallet","apim_n","sync"),("cl_market","apim_n","sync"),
 ("apim_n","bff_member","sync"),("apim_n","cms_sahatna","sync"),
 ("bff_member","apim_s","sync"),("bff_admin","apim_s","sync"),
 ("apim_s","en_enrol","sync"),("apim_s","en_chal","sync"),("apim_s","wm_wallet","sync"),("apim_s","wm_market","sync"),
 ("en_enrol","en_eligorch","sync"),("en_eligorch","en_cohort","sync"),
 # eligibility returns ids via the south gateway (apim_s→en_enrol request path); the BFF hydrates from CMS
 # WITHIN the BFF band, and the published content reaches the client back through apim_n — no BFF→client jump.
 ("bff_member","cms_sahatna","sync"),
 ("wm_market","wm_redorch","sync"),("wm_redorch","wm_wallet","sync"),("wm_redorch","wm_fraud","sync"),
 ("wm_wallet","ps_wallet","sync"),("wm_market","ps_market","sync"),("en_chal","ps_engine","sync"),
 # cross trust boundary (partner / settlement)
 ("en_maladapter","ex_malaffi","xtrust"),("wm_padapter","ex_providers","xtrust"),("wm_partner","ex_doh","xtrust"),
 # async (event hub integration -> consumers)
 ("en_verify","eh_integration","async"),("wm_wallet","eh_integration","async"),("wm_market","eh_integration","async"),
 ("eh_integration","pf_fraud","async"),("eh_integration","pf_nudge","async"),("eh_integration","pf_data","async"),
 # FRAUD-SVC anomaly signal reaches the inline Fraud & Integrity guard via the spine, not a direct band jump
 ("eh_integration","wm_fraud","async"),
 # telemetry.ingest: Health Connect SDK (device) → north gateway → Wearable Service → Event Hub → Verification
 ("cl_health","apim_n","async"),("apim_n","wearable_svc","async"),
 ("wearable_svc","eh_integration","async"),("eh_integration","en_verify","async"),
 # identity · consent · secret
 ("idp_uaepass","apim_n","identity"),("idp_entra","apim_s","identity"),
 ("pf_consent","en_enrol","identity"),("xc_secrets","ps_kv","identity"),
 # notifications: Sahatna owns delivery; platform composes + consent-checks then calls Sahatna API via APIM
 ("pf_nudge","pf_consent","sync"),("pf_nudge","apim_n","sync"),("apim_n","sah_notify","sync"),
 # (Sahatna Notifications API delivers to the citizen inside Sahatna — out of platform scope, no BFF→client edge)
 # consent propagation: Sahatna captures notify-consent → down to platform CONS-SVC (checked before notify)
 ("apim_s","pf_consent","identity"),
]
boxes={i:pos[i] for i in pos}
CB=ZONES[-1][4]+ZONES[-1][5]                       # canvas bottom (zones)
GUT_L=ZX-26; GUT_R=ZX+ZW+26
# ---- junction connectors: collapse fan-in / fan-out into a dot (many lines -> dot -> one line) ----
from collections import defaultdict
_zorder={z[0]:i for i,z in enumerate(ZONES)}; _czone={c[0]:c[1] for c in COMPS}
def band(c): return _zorder[_czone[c]]
# RULE: within a band, connect directly; ACROSS bands, route through an integration component
# (north/south APIM gateways + the async Event Hub). Exempt: external egress via an adapter (xtrust),
# identity/consent governance relations, persistence ownership (ps_*), and cross-cutting (xc_*).
_INTEG={"apim_n","apim_s","eh_integration"}
def _band_ok(s,t,ty):
    if band(s)==band(t) or s in _INTEG or t in _INTEG: return True
    if ty in ("xtrust","identity"): return True
    if s.startswith("ps_") or t.startswith("ps_") or s.startswith("xc_") or t.startswith("xc_"): return True
    return False
_bad_edges=[(s,t,ty) for s,t,ty in EDGES if not _band_ok(s,t,ty)]
assert not _bad_edges, f"band-rule violation (cross-band edge bypasses an integration component): {_bad_edges}"
fanin=defaultdict(list); fanout=defaultdict(list)
for s,t,ty in EDGES:                       # only CROSS-BAND edges trunk -> only they use junctions
    if band(s)!=band(t): fanin[(t,ty)].append(s); fanout[(s,ty)].append(t)
def _ccx(c): return boxes[c][0]+boxes[c][2]/2
def _ccy(c): return boxes[c][1]+boxes[c][3]/2
gapY=sorted(ZONES[k][4]+ZONES[k][5]+GAP_BAND/2 for k in range(len(ZONES)-1))
def _gapnear(y): return min(gapY,key=lambda g:abs(g-y))    # snap to nearest clear band-gap
NE=[]; JUN={}; jc=0; consumed=set()       # JUN: jid -> (x,y,type)
for (t,ty),srcs in fanin.items():
    if len(srcs)>=2:
        jid=f"jn{jc}"; jc+=1
        cx=sum(_ccx(m) for m in srcs+[t])/(len(srcs)+1)        # centre-x on ALL connected items
        cy=(sum(_ccy(s) for s in srcs)/len(srcs)+_ccy(t))/2    # midpoint between sources & target
        JUN[jid]=(cx, _gapnear(cy), ty)
        for s in srcs: NE.append((s,jid,ty)); consumed.add((s,t,ty))
        NE.append((jid,t,ty))
for (s,ty),tgts in fanout.items():
    rem=[t for t in tgts if (s,t,ty) not in consumed]
    if len(rem)>=2:
        jid=f"jn{jc}"; jc+=1
        cx=sum(_ccx(m) for m in [s]+rem)/(len(rem)+1)          # centre-x on ALL connected items
        cy=(_ccy(s)+sum(_ccy(t) for t in rem)/len(rem))/2      # midpoint between source & targets
        JUN[jid]=(cx, _gapnear(cy), ty)
        NE.append((s,jid,ty))
        for t in rem: NE.append((jid,t,ty)); consumed.add((s,t,ty))
for s,t,ty in EDGES:
    if (s,t,ty) not in consumed: NE.append((s,t,ty))
def _cxy(e): return (JUN[e][0],JUN[e][1]) if e in JUN else (boxes[e][0]+boxes[e][2]/2, boxes[e][1]+boxes[e][3]/2)
def _side_to(comp,px,py):                                # strictly top/bottom centre
    x,y,w,h=boxes[comp]; cy=y+h/2
    return 'B' if py>=cy else 'T'
# fan fractions for the COMPONENT endpoints (junction ends use the dot centre)
csides={}; cuse=defaultdict(list)
for k,(s,t,ty) in enumerate(NE):
    if s not in JUN:
        ox,oy=_cxy(t); sd=_side_to(s,ox,oy); csides[(k,'S')]=sd; cuse[(s,sd)].append((k,'S'))
    if t not in JUN:
        ox,oy=_cxy(s); sd=_side_to(t,ox,oy); csides[(k,'T')]=sd; cuse[(t,sd)].append((k,'T'))
cfrac={}
for (comp,sd),lst in cuse.items():
    n=len(lst)
    for j,(k,role) in enumerate(lst): cfrac[(k,role)]=(j+1)/(n+1)
def _anchor(k,role,e,other):
    if e in JUN: return (JUN[e][0],JUN[e][1])
    sd=csides[(k,role)]; f=cfrac[(k,role)]; x,y,w,h=boxes[e]
    return {'B':(x+f*w,y+h),'T':(x+f*w,y),'R':(x+w,y+f*h),'L':(x,y+f*h)}[sd]
def _astar(s,t,sa,ta):
    ign={s,t}; P=9                                       # clearance so edges never hug box borders
    xs={GUT_L,GUT_R,18,W-18,sa[0],ta[0]}; ys={60,CB+120,sa[1],ta[1]}
    for c,(bx,by,bw,bh) in boxes.items(): xs|={bx-P,bx+bw+P}; ys|={by-P,by+bh+P}
    for k in range(len(ZONES)-1): ys.add(ZONES[k][4]+ZONES[k][5]+GAP_BAND/2)
    xs=sorted(xs); ys=sorted(ys)
    xs=sorted(set(xs)|{(a+b)/2 for a,b in zip(xs,xs[1:])})   # mid-gap lanes (incl. between rows)
    ys=sorted(set(ys)|{(a+b)/2 for a,b in zip(ys,ys[1:])})
    xi={v:i for i,v in enumerate(xs)}; yi={v:i for i,v in enumerate(ys)}
    def hc(x1,x2,y):
        lo,hi=min(x1,x2),max(x1,x2)
        for c,(bx,by,bw,bh) in boxes.items():
            if c in ign: continue
            if by-P+1e-6<y<by+bh+P-1e-6 and lo<bx+bw+P-1e-6 and hi>bx-P+1e-6: return False
        return True
    def vc(x,y1,y2):
        lo,hi=min(y1,y2),max(y1,y2)
        for c,(bx,by,bw,bh) in boxes.items():
            if c in ign: continue
            if bx-P+1e-6<x<bx+bw+P-1e-6 and lo<by+bh+P-1e-6 and hi>by-P+1e-6: return False
        return True
    start=(sa[0],sa[1]); goal=(ta[0],ta[1])
    openq=[(0,start,None)]; best={start:0}; came={}
    while openq:
        f,cur,pd=heappop(openq)
        if cur==goal: break
        cx,cy=cur; ix=xi[cx]; iy=yi[cy]; nb=[]
        if ix+1<len(xs) and hc(cx,xs[ix+1],cy): nb.append((xs[ix+1],cy))
        if ix-1>=0 and hc(cx,xs[ix-1],cy): nb.append((xs[ix-1],cy))
        if iy+1<len(ys) and vc(cx,cy,ys[iy+1]): nb.append((cx,ys[iy+1]))
        if iy-1>=0 and vc(cx,cy,ys[iy-1]): nb.append((cx,ys[iy-1]))
        for n2 in nb:
            nd=(1 if n2[0]!=cx else 0,1 if n2[1]!=cy else 0)
            g=best[cur]+abs(n2[0]-cx)+abs(n2[1]-cy)+(40 if pd and pd!=nd else 0)
            if g<best.get(n2,1e18):
                best[n2]=g; came[n2]=(cur,nd)
                heappush(openq,(g+abs(n2[0]-goal[0])+abs(n2[1]-goal[1]),n2,nd))
    if goal not in came and goal!=start: return [start,goal]
    p=[goal]; n=goal
    while n in came: n=came[n][0]; p.append(n)
    p.reverse()
    simp=[p[0]]
    for i in range(1,len(p)-1):
        ax,ay=simp[-1]; bx,by=p[i]; cx2,cy2=p[i+1]
        if (ax==bx==cx2) or (ay==by==cy2): continue
        simp.append(p[i])
    simp.append(p[-1]); return simp
# junction dots
JCOL={"sync":"#1A1A1A","async":"#777777","xtrust":"#B85450","identity":"#9966AA"}
for jid,(jx,jy,jty) in JUN.items():
    c=JCOL[jty]
    cell(f'<mxCell id="{jid}" value="" style="ellipse;fillColor={c};strokeColor={c};" vertex="1" parent="1"><mxGeometry x="{round(jx-5)}" y="{round(jy-5)}" width="10" height="10" as="geometry"/></mxCell>')
STUB=18                                                  # an edge runs this far vertically before any bend
def _clear(horiz,a,b,fixed,ign,P=8):
    for c,(bx,by,bw,bh) in boxes.items():
        if c in ign: continue
        if horiz:
            if by-P<fixed<by+bh+P and min(a,b)<bx+bw+P and max(a,b)>bx-P: return False
        else:
            if bx-P<fixed<bx+bw+P and min(a,b)<by+bh+P and max(a,b)>by-P: return False
    return True
def _verify(path,s,t):
    for (x1,y1),(x2,y2) in zip(path,path[1:]):
        if abs(x1-x2)>1 and abs(y1-y2)>1: return False
        horiz=abs(y1-y2)<1
        for c,(bx,by,bw,bh) in boxes.items():
            if c in (s,t): continue
            if horiz:
                if by+1e-6<y1<by+bh-1e-6 and min(x1,x2)<bx+bw-1e-6 and max(x1,x2)>bx+1e-6: return False
            else:
                if bx+1e-6<x1<bx+bw-1e-6 and min(y1,y2)<by+bh-1e-6 and max(y1,y2)>by+1e-6: return False
    return True
def _emit(k,ty,s,t,sj,tj,path,sa,ta):
    extra=""
    if not sj: sx,sy,sw,sh=boxes[s]; extra+=f"exitX={(sa[0]-sx)/sw:.3f};exitY={(sa[1]-sy)/sh:.3f};exitDx=0;exitDy=0;"
    if not tj: tx,ty2,tw,th=boxes[t]; extra+=f"entryX={(ta[0]-tx)/tw:.3f};entryY={(ta[1]-ty2)/th:.3f};entryDx=0;entryDy=0;"
    pts="".join(f'<mxPoint x="{round(x)}" y="{round(y)}"/>' for (x,y) in path[1:-1])
    cell(f'<mxCell id="ne{k}" style="edgeStyle=none;rounded=0;html=1;{ESTYLE[ty]}{extra}" edge="1" parent="1" source="{s}" target="{t}"><mxGeometry relative="1" as="geometry"><Array as="points">{pts}</Array></mxGeometry></mxCell>')
edge_bad=0
for k,(s,t,ty) in enumerate(NE):
    sj=s in JUN; tj=t in JUN
    sa=_anchor(k,'S',s,t); ta=_anchor(k,'T',t,s); path=None
    if sj^tj:                                            # one junction -> try the symmetric comb
        if tj:                                           # comp -> junction: vertical to jy, then horizontal to jx
            jx,jy,_=JUN[t]; xs,ce=sa
            if _clear(False,ce,jy,xs,{s}) and _clear(True,xs,jx,jy,{s}): path=[(xs,ce),(xs,jy),(jx,jy)]
        else:                                            # junction -> comp: horizontal to xt, then vertical into comp
            jx,jy,_=JUN[s]; xt,ce=ta
            if _clear(False,jy,ce,xt,{t}) and _clear(True,jx,xt,jy,{t}): path=[(jx,jy),(xt,jy),(xt,ce)]
    if path is None:                                     # fallback: A* with vertical stubs off the boxes
        ss=sa if sj else (sa[0], sa[1]+(STUB if csides[(k,'S')]=='B' else -STUB))
        st=ta if tj else (ta[0], ta[1]+(STUB if csides[(k,'T')]=='B' else -STUB))
        mid=_astar(s,t,ss,st); path=([sa] if not sj else [])+mid+([ta] if not tj else [])
    if not _verify(path,s,t): edge_bad+=1
    _emit(k,ty,s,t,sj,tj,path,sa,ta)

# legend
ly=ZONES[-1][4]+ZONES[-1][5]+24
legend=[("Synchronous HTTPS (internal)","strokeColor=#000000;"),
        ("Async / event publish–consume","strokeColor=#777777;dashed=1;dashPattern=6 6;"),
        ("Cross trust boundary (partner / settlement)","strokeColor=#B85450;strokeWidth=2;"),
        ("Identity · consent · read-secret","strokeColor=#999999;dashed=1;dashPattern=2 4;")]
cell(f'<mxCell id="leg" value="Legend" style="rounded=0;dashed=0;strokeColor=#999;fillColor=#FFFFFF;align=left;verticalAlign=top;fontStyle=1;spacingLeft=10;spacingTop=6;fontSize=11;" vertex="1" parent="1"><mxGeometry x="{ZX}" y="{ly}" width="{ZW}" height="86" as="geometry"/></mxCell>')
lx=ZX+20
for k,(txt,st) in enumerate(legend):
    sy=ly+34+(k//2)*30; sx=lx+(k%2)*((ZW-40)//2)
    cell(f'<mxCell id="legl{k}" style="endArrow=block;html=1;{st}" edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="{sx}" y="{sy}" as="sourcePoint"/><mxPoint x="{sx+70}" y="{sy}" as="targetPoint"/></mxGeometry></mxCell>')
    cell(f'<mxCell id="legt{k}" value="{esc(txt)}" style="text;html=1;align=left;verticalAlign=middle;fontSize=10;" vertex="1" parent="1"><mxGeometry x="{sx+80}" y="{sy-10}" width="320" height="20" as="geometry"/></mxCell>')

canvas_h=ly+86+40
title='Wellness Platform — Solution Architecture (Value Path: eligibility · earn · redeem · settle)'
out=['<mxfile host="app.diagrams.net">',
 f'<diagram name="Solution Architecture" id="sol1">',
 f'<mxGraphModel dx="1422" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{canvas_h}" math="0" shadow="0">',
 '<root>','<mxCell id="0"/>','<mxCell id="1" parent="0"/>',
 f'<mxCell id="title" value="{esc(title)}" style="text;html=1;align=center;fontStyle=1;fontSize=18;" vertex="1" parent="1"><mxGeometry x="{ZX}" y="24" width="{ZW}" height="34" as="geometry"/></mxCell>']
out+=cells
out+=['</root>','</mxGraphModel>','</diagram>','</mxfile>']

# overlap check (components only)
bad=0
ids=[c[0] for c in COMPS]
for a in range(len(ids)):
    for b in range(a+1,len(ids)):
        ax,ay,aw,ah=pos[ids[a]]; bx,by,bw,bh=pos[ids[b]]
        if ax<bx+bw and bx<ax+aw and ay<by+bh and by<ay+bh: bad+=1; print("OVERLAP",ids[a],ids[b])
path="/Users/socrateshlapolosa/Development/health-service-idp/factory/docs/analysis/wellness-archimate/solution-architecture.drawio"
open(path,"w").write("\n".join(out))
print("components:",len(COMPS)," zones:",len(ZONES)," overlaps:",bad," edges:",len(EDGES),
      " edge box-crossings:",edge_bad," canvas:",W,"x",canvas_h)
print("wrote",path)
