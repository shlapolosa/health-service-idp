#!/usr/bin/env python3
"""Banded C4 solution-architecture renderer -> draw.io / mxGraph.

Emits the EXACT banded layout produced by gen_band_svg.py (same constants, same band Y stacking,
same barycenter ordering, same channel router) but as a draw.io (mxGraph) file instead of SVG.
All ASYNC edges are animated (flowAnimation=1). Input: c4-data.json -> solution-architecture-elk.drawio.

The layout + routing section below is copied VERBATIM from gen_band_svg.py up to the point where,
for every edge, we have its routed polyline `pts` and `type`, every component has G[id]=(x,y,w,h),
plus band rects, the 3 SYSTEM boxes and the trust strip. Only the emit stage is replaced."""
import json, html
from collections import defaultdict
D=json.load(open("c4-data.json"))
zones=D["zones"]; comps=D["comps"]; edges=D["edges"]
zorder=[z["id"] for z in zones]; zmeta={z["id"]:z for z in zones}; zidx={z:i for i,z in enumerate(zorder)}
byz={z:[] for z in zorder}
for c in comps: byz[c["zone"]].append(c["id"])
title={c["id"]:c["title"] for c in comps}; bandof={c["id"]:c["zone"] for c in comps}
desc={c["id"]:c.get("desc","") for c in comps}
adj=defaultdict(list)
for e in edges: adj[e["s"]].append(e["t"]); adj[e["t"]].append(e["s"])

PAD=46; GUTTER=150; BAND_W=1640; NODEH=82; NGAP=20; INNERPAD=14; LABELH=20; LANE=110; MAXNW=210
SYSO=18; TRUSTGAP=104
bx0=PAD+GUTTER
BANDH=LABELH+INNERPAD+NODEH+INNERPAD
# system boundaries = dotted boxes that ENCOMPASS several layer-bands (a deployable system / trust zone)
SYSTEMS=[
 ("SAHATNA (server-side)  ·  north gateway · BFF · CMS · notifications     |     Citizen App (above) runs on the device, client-side",
   ["z_apim_n","z_bff"], "#D79B00"),
 ("GAMIFICATION PLATFORM  ·  admin console + Knative/Istio mesh · versioned event spine · financial-grade ledger",
   ["z_admin","z_apim_s","z_engine","z_value","z_persist"], "#3A7CA5"),
 ("PLATFORM SHARED SERVICES  ·  identity · consent · fraud · analytics · GitOps · secrets",
   ["z_platform","z_xcut"], "#5A5A5A"),
]
bandY={}; y=PAD+40
for z in zorder:
    if z=="z_external": y+=TRUSTGAP          # room for the PARTNER TRUST BOUNDARY strip
    bandY[z]=y; y+=BANDH+LANE
CANVAS_H=y-LANE+PAD+22; CANVAS_W=bx0+BAND_W+GUTTER+PAD
def inner_w(): return BAND_W-2*INNERPAD
def nodew(n): return min(MAXNW,(inner_w()-(n-1)*NGAP)/n)
def xpositions(order):
    n=len(order); w=nodew(n); tot=n*w+(n-1)*NGAP; sx=bx0+INNERPAD+(inner_w()-tot)/2
    return {nid: sx+i*(w+NGAP) for i,nid in enumerate(order)}, w
def node_geom(ob):
    G={}
    for z in zorder:
        xs,w=xpositions(ob[z]); ny=bandY[z]+LABELH+INNERPAD
        for nid in ob[z]: G[nid]=(xs[nid],ny,w,NODEH)
    return G
def centers(G): return {k:(x+w/2,y+h/2) for k,(x,y,w,h) in G.items()}
def seg_cross(a,b,c,d):
    def o(p,q,r): return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    return ((o(a,b,c)>0)!=(o(a,b,d)>0)) and ((o(c,d,a)>0)!=(o(c,d,b)>0))
def crossings(ob):
    C=centers(node_geom(ob)); segs=[(C[e["s"]],C[e["t"]],e["s"],e["t"]) for e in edges]
    n=0
    for i in range(len(segs)):
        for j in range(i+1,len(segs)):
            a,b,s1,t1=segs[i]; c,d,s2,t2=segs[j]
            if len({s1,t1,s2,t2})<4: continue
            if seg_cross(a,b,c,d): n+=1
    return n
# ---- barycenter ordering ----
order={z:list(byz[z]) for z in zorder}
def frac(z,nid): o=order[z]; return (o.index(nid)+0.5)/len(o)
def sweep(td):
    for z in (zorder if td else list(reversed(zorder))):
        if len(order[z])<=1: continue
        key={}
        for nid in order[z]:
            nb=[a for a in adj[nid] if bandof.get(a) and bandof[a]!=z]
            key[nid]=sum(frac(bandof[a],a) for a in nb)/len(nb) if nb else frac(z,nid)
        order[z]=sorted(order[z],key=lambda n:(key[n],byz[z].index(n)))
best=[{z:list(order[z]) for z in zorder},crossings(order)]
for it in range(14):
    sweep(it%2==0); c=crossings(order)
    if c<best[1]: best=[{z:list(order[z]) for z in zorder},c]
init=crossings({z:list(byz[z]) for z in zorder}); order=best[0]
print("crossings(straight-line metric): initial",init,"-> barycenter",best[1])

G=node_geom(order); C=centers(G); cx={k:v[0] for k,v in C.items()}
# ---- channel routing ----
def bot(z): return bandY[z]+BANDH
def top(z): return bandY[z]
def nb(n): x,y,w,h=G[n]; return y+h   # node (component) bottom edge
def nt(n): x,y,w,h=G[n]; return y     # node (component) top edge
# classify edges, pick gutter side+column for long edges
EI=[]; lcol=0; rcol=0
for idx,e in enumerate(edges):
    s,t,ty=e["s"],e["t"],e["type"]; bs,bt=zidx[bandof[s]],zidx[bandof[t]]; di=bt-bs
    long=abs(di)>=2; side=None; gutx=None
    if long:
        side="L" if (cx[s]+cx[t])/2 < bx0+BAND_W/2 else "R"
        if side=="L": gutx=bx0-18-lcol*14; lcol+=1
        else: gutx=bx0+BAND_W+18+rcol*14; rcol+=1
    EI.append(dict(idx=idx,s=s,t=t,ty=ty,bs=bs,bt=bt,di=di,long=long,gutx=gutx))
# port ordering: per (node, side) sort by heading-x, assign evenly across node width
attach=defaultdict(list)  # (node,'T'/'B') -> list of (idx, headkey, role)
for ei in EI:
    s,t=ei["s"],ei["t"]; di=ei["di"]
    sside='B' if di>=0 else 'T'; tside='T' if di>0 else ('B' if di<0 else 'B')
    hks=ei["gutx"] if ei["long"] else cx[t]; hkt=ei["gutx"] if ei["long"] else cx[s]
    attach[(s,sside)].append((ei["idx"],hks,'s',sside))
    attach[(t,tside)].append((ei["idx"],hkt,'t',tside))
portx={}
for (nid,side),lst in attach.items():
    lst.sort(key=lambda r:r[1]); x,y,w,h=G[nid]; n=len(lst)
    for k,(eidx,hk,role,sd) in enumerate(lst): portx[(eidx,role)]=x+w*(k+1)/(n+1)
# build horizontal runs per gap, then greedy-colour into tracks
runs=defaultdict(list)  # gap_index -> list of dict(xa,xb,eidx,key='A'/'B'/'S')
def addrun(gi,xa,xb,eidx,key): runs[gi].append(dict(xa=min(xa,xb),xb=max(xa,xb),eidx=eidx,key=key))
for ei in EI:
    i=ei["idx"]; s,t=ei["s"],ei["t"]; di=ei["di"]; sx=portx[(i,'s')]; tx=portx[(i,'t')]
    if not ei["long"]:
        if di==0: addrun(ei["bs"],sx,tx,i,'S')
        elif di>0: addrun(ei["bs"],sx,tx,i,'S')
        else: addrun(ei["bt"],sx,tx,i,'S')
    else:
        if di>0: addrun(ei["bs"],sx,ei["gutx"],i,'A'); addrun(ei["bt"]-1,ei["gutx"],tx,i,'B')
        else: addrun(ei["bs"]-1,sx,ei["gutx"],i,'A'); addrun(ei["bt"],ei["gutx"],tx,i,'B')
track={}  # (gap,eidx,key) -> track int
for gi,rs in runs.items():
    rs.sort(key=lambda r:r["xa"]); ends=[]  # track -> last xb
    for r in rs:
        placed=False
        for ti,last in enumerate(ends):
            if r["xa"]>last+8: ends[ti]=r["xb"]; track[(gi,r["eidx"],r["key"])]=ti; placed=True; break
        if not placed: track[(gi,r["eidx"],r["key"])]=len(ends); ends.append(r["xb"])
def laneY(gi,tr):
    nt=max((track[k] for k in track if k[0]==gi),default=0)+1
    sp=min(14,(LANE-20)/max(nt,1)); return bandY[zorder[gi+1]]-LANE+12+tr*sp if gi+1<len(zorder) else bot(zorder[gi])+12+tr*sp
def gaptopY(gi): return bot(zorder[gi])

# ---- compute routed polyline pts per edge (mirrors gen_band_svg.py emit() calls) ----
ROUTES={}   # edge idx -> (pts, type)
for ei in EI:
    i=ei["idx"]; s,t=ei["s"],ei["t"]; ty=ei["ty"]; di=ei["di"]
    sx=portx[(i,'s')]; tx=portx[(i,'t')]
    if not ei["long"]:
        gi=ei["bs"] if di>=0 else ei["bt"]; ly=laneY(gi,track[(gi,i,'S')])
        sy=nb(s) if di>=0 else nt(s); tyy=nt(t) if di>0 else nb(t)
        pts=[(sx,sy),(sx,ly),(tx,ly),(tx,tyy)]
    else:
        gx=ei["gutx"]
        if di>0:
            gA=ei["bs"]; gB=ei["bt"]-1; yA=laneY(gA,track[(gA,i,'A')]); yB=laneY(gB,track[(gB,i,'B')])
            pts=[(sx,nb(s)),(sx,yA),(gx,yA),(gx,yB),(tx,yB),(tx,nt(t))]
        else:
            gA=ei["bs"]-1; gB=ei["bt"]; yA=laneY(gA,track[(gA,i,'A')]); yB=laneY(gB,track[(gB,i,'B')])
            pts=[(sx,nt(s)),(sx,yA),(gx,yA),(gx,yB),(tx,yB),(tx,nb(t))]
    ROUTES[i]=(pts,ty)

def wrap(s,n=21):
    words=s.split(); lines=[]; cur=""
    for w in words:
        if len(cur)+len(w)+1<=n: cur=(cur+" "+w).strip()
        else: lines.append(cur); cur=w
    if cur: lines.append(cur)
    return lines[:3]

# per-band security context (right-aligned note), copied from SVG SEC dict
SEC={"z_apim_n":"UAE Pass OIDC · JWT mint · rate-limit","z_bff":"JWT validation · idempotency relay",
 "z_admin":"workforce SSO (Entra) · no public ingress",
 "z_apim_s":"Entra OAuth2 (B2B client-creds) · mTLS · per-OAM product","z_persist":"column-level KMS · Key Vault",
 "z_value":"financial-grade · append-only · inline fraud","z_platform":"consent-gated · PDPL / ADHICS",
 "z_external":"outside platform trust zone"}

# ---------- mxGraph emit ----------
def esc(s): return html.escape(s, quote=True)
cells=[]
_id=[100]
def nxt():
    _id[0]+=1; return f"c{_id[0]}"
def vcell(cid,value,style,x,y,w,h,parent="1"):
    cells.append(
      f'        <mxCell id="{cid}" value="{value}" style="{style}" vertex="1" parent="{parent}">\n'
      f'          <mxGeometry x="{round(x,2)}" y="{round(y,2)}" width="{round(w,2)}" height="{round(h,2)}" as="geometry"/>\n'
      f'        </mxCell>')
def ecell(cid,src,tgt,style,waypoints):
    geo='<mxGeometry relative="1" as="geometry">'
    if waypoints:
        geo+='\n            <Array as="points">'
        for (px,py) in waypoints:
            geo+=f'\n              <mxPoint x="{round(px,2)}" y="{round(py,2)}"/>'
        geo+='\n            </Array>\n          '
    geo+='</mxGeometry>'
    cells.append(
      f'        <mxCell id="{cid}" style="{style}" edge="1" parent="1" source="{src}" target="{tgt}">\n'
      f'          {geo}\n'
      f'        </mxCell>')

# --- system boundaries: dashed boxes ENCOMPASSING several layer-bands (drawn first/behind) ---
for name,bands,scol in SYSTEMS:
    bs=[b for b in bands if b in bandY]
    if not bs: continue
    ytop=min(bandY[b] for b in bs)-SYSO-17; ybot=max(bot(b) for b in bs)+SYSO
    st=(f"rounded=1;arcSize=4;fillColor=none;strokeColor={scol};strokeWidth=3.5;"
        f"dashed=1;dashPattern=3 7;verticalAlign=top;align=left;spacingLeft=12;spacingTop=4;"
        f"fontColor={scol};fontStyle=1;fontSize=12;html=1;")
    vcell(nxt(), esc(name), st, bx0-SYSO, ytop, BAND_W+2*SYSO, ybot-ytop)

# --- PARTNER TRUST BOUNDARY strip (gold) just above External ---
gy=bandY["z_external"]-46
trust=("PARTNER TRUST BOUNDARY  ·  mTLS / OAuth2  ·  idempotent  ·  "
       "10s timeout · 3 retries  ·  uncertain → manual reconcile")
st=("rounded=1;arcSize=20;fillColor=#FBE9A0;strokeColor=#C9A100;strokeWidth=3.5;"
    "dashed=1;dashPattern=3 7;align=center;verticalAlign=middle;fontColor=#6b5200;"
    "fontStyle=1;fontSize=11;html=1;")
vcell(nxt(), esc(trust), st, bx0-SYSO, gy, BAND_W+2*SYSO, 36)

# --- band containers (outline-only) with bold colored title + right-aligned SEC note ---
for z in zorder:
    m=zmeta[z]; by=bandY[z]
    st=(f"rounded=1;arcSize=6;fillColor=none;strokeColor={m['stroke']};strokeWidth=2;"
        f"verticalAlign=top;align=left;spacingLeft=13;spacingTop=3;fontColor={m['stroke']};"
        f"fontStyle=1;fontSize=12;html=1;")
    vcell(nxt(), esc(m["label"]), st, bx0, by, BAND_W, BANDH)
    if z in SEC:
        nst=(f"text;html=1;align=right;verticalAlign=top;fontColor={m['stroke']};"
             f"fontSize=9;fontStyle=2;strokeColor=none;fillColor=none;")
        vcell(nxt(), esc("\U0001F512 "+SEC[z]), nst, bx0+BAND_W-360, by+2, 348, 16)

# --- components ---
GID={}   # component id -> mxCell id
for z in zorder:
    m=zmeta[z]
    for nid in order[z]:
        x,y,w,h=G[nid]; cid=nxt(); GID[nid]=cid
        tline=" ".join(wrap(title[nid],22))
        dline=" ".join(wrap(desc[nid],34)[:3])
        # build HTML label then entity-escape the whole thing for the XML attribute
        # (draw.io stores rich-text labels as escaped entities)
        raw=f"<b>{esc(tline)}</b>"
        if dline:
            raw+=f'<br/><font style="font-size:8px;color:#555">{esc(dline)}</font>'
        val=esc(raw)
        st=(f"rounded=1;whiteSpace=wrap;html=1;fillColor={m['nodefill']};"
            f"strokeColor={m['stroke']};strokeWidth=1.3;fontSize=10;align=center;"
            f"verticalAlign=middle;arcSize=8;")
        vcell(cid, val, st, x, y, w, h)

# --- edges ---
ESTY={
 "sync":     "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#1A1A1A;",
 "async":    "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#7A7A7A;dashed=1;dashPattern=6 4;flowAnimation=1;",
 "xtrust":   "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#B85450;strokeWidth=2.4;",
 "identity": "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#9966AA;dashed=1;dashPattern=2 4;",
}
animated=0
for ei in EI:
    i=ei["idx"]; s,t=ei["s"],ei["t"]; pts,ty=ROUTES[i]
    # drop first/last endpoints, keep interior bend points as waypoints
    interior=pts[1:-1]
    st=ESTY[ty]
    if ty=="async": animated+=1
    ecell(nxt(), GID[s], GID[t], st, interior)

# --- legend (text cells) ---
ly=CANVAS_H-PAD+8
leg=("<b>Edges:</b>  sync = black solid · async = grey dashed (ANIMATED) · "
     "xtrust = red (cross trust boundary) · identity = purple dotted  |  "
     "dotted box = system / trust boundary")
lst=("text;html=1;align=left;verticalAlign=middle;fontSize=10;fontColor=#333;"
     "strokeColor=none;fillColor=none;")
vcell(nxt(), esc(leg), lst, bx0, ly, BAND_W, 18)

# --- title ---
tst="text;html=1;align=left;verticalAlign=middle;fontSize=15;fontStyle=1;fontColor=#1a1a1a;strokeColor=none;fillColor=none;"
vcell(nxt(),"Value Path — Wellness Platform Solution Architecture", tst, bx0, PAD-30, BAND_W, 22)

body="\n".join(cells)
xml=(
 '<mxfile host="app.diagrams.net" type="device">\n'
 '  <diagram id="wellness-band" name="Solution Architecture">\n'
 f'    <mxGraphModel dx="1200" dy="800" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" '
 f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="{int(CANVAS_W)}" pageHeight="{int(CANVAS_H)}" '
 'math="0" shadow="0">\n'
 '      <root>\n'
 '        <mxCell id="0"/>\n'
 '        <mxCell id="1" parent="0"/>\n'
 f'{body}\n'
 '      </root>\n'
 '    </mxGraphModel>\n'
 '  </diagram>\n'
 '</mxfile>\n'
)
open("solution-architecture-elk.drawio","w").write(xml)

# ---- validate / report ----
n_comp_cells=len(GID); n_edge_cells=len(EI); n_band=len(zorder)
assert n_comp_cells==43, f"expected 43 comps, got {n_comp_cells}"
assert n_edge_cells==42, f"expected 42 edges, got {n_edge_cells}"
assert n_band==11, f"expected 11 bands, got {n_band}"
import xml.dom.minidom as _m
_m.parseString(xml)   # raises if not well-formed
print(f"wrote solution-architecture-elk.drawio")
print(f"comps={n_comp_cells} edges={n_edge_cells} bands={n_band}")
print(f"async edges with flowAnimation=1: {animated}")
print("XML well-formed: yes")
