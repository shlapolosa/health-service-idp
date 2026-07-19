#!/usr/bin/env python3
"""Banded C4 solution-architecture renderer.
Uniform full-width bands (aligned, top->bottom) + barycenter node ordering to cut crossings +
a channel router: ports ordered by heading, parallel runs packed into non-overlapping tracks per
band-gap (greedy interval colouring), and long multi-band edges pushed into SIDE GUTTERS (vertical
buses) so they never cut through the interior. Input: c4-data.json -> solution-architecture-elk.svg."""
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
# ---- emit SVG ----
ESTY={"sync":("#1A1A1A","none","1.5"),"async":("#7A7A7A","5,4","1.4"),
      "xtrust":("#B85450","none","2.4"),"identity":("#9966AA","3,4","1.4")}
def tint(hx,amt=0.87):
    h=hx.lstrip("#"); r,g,b=int(h[:2],16),int(h[2:4],16),int(h[4:],16)
    return f"#{int(r+(255-r)*amt):02x}{int(g+(255-g)*amt):02x}{int(b+(255-b)*amt):02x}"
out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(CANVAS_W)}" height="{int(CANVAS_H)}" font-family="Helvetica,Arial">',
     '<rect width="100%" height="100%" fill="#FFFFFF"/>','<defs>']
for k,(col,_,_) in ESTY.items():
    out.append(f'<marker id="a_{k}" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="{col}"/></marker>')
out.append('</defs>')
out.append(f'<text x="{bx0}" y="22" font-size="17" font-weight="bold" fill="#1a1a1a">Value Path &#8212; Wellness Platform Solution Architecture</text>')
out.append(f'<text x="{bx0}" y="37" font-size="11" fill="#666">eligibility &#183; earn &#183; redeem &#183; settle  &#8226;  dotted = system / trust boundary  &#183;  per-band security context noted</text>')
# --- system boundaries: dotted boxes ENCOMPASSING several layer-bands (drawn behind the bands) ---
for name,bands,scol in SYSTEMS:
    bs=[b for b in bands if b in bandY]
    if not bs: continue
    ytop=min(bandY[b] for b in bs)-SYSO-17; ybot=max(bot(b) for b in bs)+SYSO
    out.append(f'<rect x="{bx0-SYSO}" y="{ytop}" width="{BAND_W+2*SYSO}" height="{ybot-ytop}" rx="13" fill="none" stroke="{scol}" stroke-width="3.5" stroke-dasharray="3,7" stroke-linecap="round" opacity="0.95"/>')
    out.append(f'<text x="{bx0-SYSO+12}" y="{ytop+14}" font-size="12" font-weight="bold" letter-spacing="0.4" fill="{scol}">{html.escape(name)}</text>')
# --- PARTNER TRUST BOUNDARY strip (security context) in the gap above External ---
gy=bandY["z_external"]-46          # sit just above External, below the routing lanes
out.append(f'<rect x="{bx0-SYSO}" y="{gy}" width="{BAND_W+2*SYSO}" height="36" rx="7" fill="#FBE9A0" stroke="#C9A100" stroke-width="3.5" stroke-dasharray="3,7" stroke-linecap="round" opacity="1"/>')
out.append(f'<text x="{bx0+BAND_W/2}" y="{gy+22}" font-size="11.5" font-weight="bold" text-anchor="middle" fill="#6b5200">PARTNER TRUST BOUNDARY  &#183;  mTLS / OAuth2  &#183;  idempotent  &#183;  10s timeout &#183; 3 retries  &#183;  uncertain &#8594; manual reconcile</text>')
# per-band security context (right-aligned, small)
SEC={"z_apim_n":"UAE Pass OIDC &#183; JWT mint &#183; rate-limit","z_bff":"JWT validation &#183; idempotency relay",
 "z_admin":"workforce SSO (Entra) &#183; no public ingress",
 "z_apim_s":"Entra OAuth2 (B2B client-creds) &#183; mTLS &#183; per-OAM product","z_persist":"column-level KMS &#183; Key Vault",
 "z_value":"financial-grade &#183; append-only &#183; inline fraud","z_platform":"consent-gated &#183; PDPL / ADHICS",
 "z_external":"outside platform trust zone"}
for z in zorder:
    m=zmeta[z]; by=bandY[z]
    out.append(f'<rect x="{bx0}" y="{by}" width="{BAND_W}" height="{BANDH}" rx="8" fill="none" stroke="{m["stroke"]}" stroke-width="2"/>')
    out.append(f'<text x="{bx0+13}" y="{by+15}" font-size="12" font-weight="bold" fill="{m["stroke"]}">{html.escape(m["label"])}</text>')
    if z in SEC:
        out.append(f'<text x="{bx0+BAND_W-12}" y="{by+15}" font-size="9.5" font-style="italic" text-anchor="end" fill="{m["stroke"]}">&#128274; {SEC[z]}</text>')
def emit(pts,col,dash,wd,ty):
    d="M "+" L ".join(f"{round(px,1)},{round(py,1)}" for px,py in pts)
    # class="flow" is inert in the static SVG (no stylesheet); the animated variant adds the keyframes.
    out.append(f'<path class="flow" d="{d}" fill="none" stroke="{col}" stroke-width="{wd}" stroke-dasharray="{dash}" marker-end="url(#a_{ty})" opacity="0.92"/>')
for ei in EI:
    i=ei["idx"]; s,t=ei["s"],ei["t"]; ty=ei["ty"]; di=ei["di"]; col,dash,wd=ESTY[ty]
    sx=portx[(i,'s')]; tx=portx[(i,'t')]; sz=bandof[s]; tz=bandof[t]
    if not ei["long"]:
        gi=ei["bs"] if di>=0 else ei["bt"]; ly=laneY(gi,track[(gi,i,'S')])
        sy=nb(s) if di>=0 else nt(s); tyy=nt(t) if di>0 else nb(t)
        emit([(sx,sy),(sx,ly),(tx,ly),(tx,tyy)],col,dash,wd,ty)
    else:
        gx=ei["gutx"]
        if di>0:
            gA=ei["bs"]; gB=ei["bt"]-1; yA=laneY(gA,track[(gA,i,'A')]); yB=laneY(gB,track[(gB,i,'B')])
            emit([(sx,nb(s)),(sx,yA),(gx,yA),(gx,yB),(tx,yB),(tx,nt(t))],col,dash,wd,ty)
        else:
            gA=ei["bs"]-1; gB=ei["bt"]; yA=laneY(gA,track[(gA,i,'A')]); yB=laneY(gB,track[(gB,i,'B')])
            emit([(sx,nt(s)),(sx,yA),(gx,yA),(gx,yB),(tx,yB),(tx,nb(t))],col,dash,wd,ty)
def wrap(s,n=21):
    words=s.split(); lines=[]; cur=""
    for w in words:
        if len(cur)+len(w)+1<=n: cur=(cur+" "+w).strip()
        else: lines.append(cur); cur=w
    if cur: lines.append(cur)
    return lines[:3]
for z in zorder:
    m=zmeta[z]
    for nid in order[z]:
        x,y,w,h=G[nid]; cxx=x+w/2
        out.append(f'<rect x="{round(x,1)}" y="{round(y,1)}" width="{round(w,1)}" height="{h}" rx="6" fill="{m["nodefill"]}" stroke="{m["stroke"]}" stroke-width="1.3"/>')
        tl=wrap(title[nid],22); ty0=y+15
        for k,ln in enumerate(tl):
            out.append(f'<text x="{round(cxx,1)}" y="{round(ty0+k*11,1)}" font-size="9.7" text-anchor="middle" font-weight="bold" fill="#1c1c1c">{html.escape(ln)}</text>')
        dl=wrap(desc[nid],34)[:3]
        dy0=ty0+len(tl)*11+9
        for k,ln in enumerate(dl):
            out.append(f'<text x="{round(cxx,1)}" y="{round(dy0+k*9.5,1)}" font-size="7.3" text-anchor="middle" fill="#5a5a5a">{html.escape(ln)}</text>')
lx,ly=bx0,CANVAS_H-PAD+12
items=[("sync","Synchronous HTTPS (internal)"),("async","Async / event publish-consume"),
       ("xtrust","Cross trust boundary (partner / settlement)"),("identity","Identity / consent / read-secret")]
ex=lx
for k,lab in items:
    col,dash,wd=ESTY[k]
    out.append(f'<line x1="{ex}" y1="{ly-8}" x2="{ex+30}" y2="{ly-8}" stroke="{col}" stroke-width="{wd}" stroke-dasharray="{dash}" marker-end="url(#a_{k})"/>')
    out.append(f'<text x="{ex+37}" y="{ly-4}" font-size="10" fill="#333">{lab}</text>')
    ex+=44+len(lab)*5.6
out.append(f'<rect x="{ex}" y="{ly-15}" width="26" height="15" rx="4" fill="none" stroke="#5A5A5A" stroke-width="1.6" stroke-dasharray="2,4"/>')
out.append(f'<text x="{ex+32}" y="{ly-4}" font-size="10" fill="#333">System / trust boundary (dotted)</text>')
out.append('</svg>')
svg_static="\n".join(out)
open("solution-architecture-elk.svg","w").write(svg_static)
# --- animated variant: flowing dashes show direction of info flow (source -> target). Open in a browser. ---
anim_style=('<style>'
 '.flow{stroke-dasharray:5 11 !important;animation:flow 1.1s linear infinite}'
 '@keyframes flow{to{stroke-dashoffset:-32}}'   # offset decreasing => dashes march source->target
 '</style>')
open("solution-architecture-animated.svg","w").write(svg_static.replace(">", ">"+anim_style, 1))
print("wrote solution-architecture-animated.svg (open in a browser to see flow direction)")
long_n=sum(1 for ei in EI if ei["long"])
print("nodes",len(comps),"edges",len(edges),"bands",len(zorder),"| long edges via gutters:",long_n,"| interior(short):",len(edges)-long_n)
