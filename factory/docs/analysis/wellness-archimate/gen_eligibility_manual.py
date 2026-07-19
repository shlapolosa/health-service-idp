"""Manual application of 10-layout-ruleset.md to the Eligibility Determination view.

Positions are hand-assigned to prove the rules produce a clean view BEFORE we bake an engine.
A deterministic orthogonal router + the hard invariants (H1 no overlap, H2 no edge over a box,
H3 min connector length, H4 serving/realization upward) are checked at build time.

Top-down bands (single view spanning Business + Application; A1 domain order Business above Application;
A2 within-domain Active->Behaviour->Passive combined with A4 served-above-server):
  Business behaviour (served)      : Eligibility Evaluation
  Application service              : Eligibility Service
  Application behaviour flow (L->R) : Member -> User Logged In -> [Sahatna Mobile App: Presentation]
                                      -> Platform Public API -> [Eligibility Determination:
                                      Determine Eligible Challenges -> Eligibility Resolution
                                      -> Local Membership Check] -> Eligibility Resolved
  Application active (off-flow)     : Malaffi HIE black box (API + Membership service), right
  Passive (bottom channel)          : the data objects
"""
from xml.sax.saxutils import escape
from collections import Counter

NS = "http://www.opengroup.org/xsd/archimate/3.0/"
BIZ, APP = "#FFFFB5", "#B5FFFF"
def rgb(h): return (int(h[1:3],16),int(h[3:5],16),int(h[5:7],16))

# ---------------- elements: id -> (archimate type, name, fill, x, y, w, h, parent) ----------------
N = {}
def put(i,t,n,fill,x,y,w,h,parent=None): N[i]=dict(t=t,n=n,fill=fill,x=x,y=y,w=w,h=h,parent=parent)

# Business band (served behaviour, top) + the member actor (active, initiator, top-left)
put("act_member","BusinessActor","Member",BIZ, 80,60,170,64)
put("fn_p9","BusinessFunction","Eligibility Evaluation",BIZ, 854,60,210,58)
# Application service band
put("as_elig","ApplicationService","Eligibility Service",APP, 854,210,210,54)
# Application behaviour flow band (centres all at y=439)
put("ev_login","ApplicationEvent","User Logged In",APP, 90,416,150,46)
put("ac_mobile","ApplicationComponent","Sahatna Mobile App",APP, 320,380,222,100)        # container
put("fn_present","ApplicationFunction","Presentation & Aggregation",APP, 336,410,190,58, "ac_mobile")
put("if_pubapi","ApplicationInterface","Platform Public API",APP, 622,416,146,46)
put("col_elig","ApplicationCollaboration","Eligibility Determination",APP, 848,380,742,100)  # container
put("ia_elig","ApplicationInteraction","Determine Eligible Challenges",APP, 864,410,190,58, "col_elig")
put("fn_elig","ApplicationFunction","Eligibility Resolution",APP, 1124,410,190,58, "col_elig")
put("fn_localmem","ApplicationFunction","Local Membership Check",APP, 1384,410,190,58, "col_elig")
put("ev_elig","ApplicationEvent","Eligibility Resolved",APP, 1670,416,150,46)
# Malaffi black box (off the flow line, lower-right) — own mini-layering: service above component (A4),
# interface on the platform-facing (left) edge.
put("as_malmember","ApplicationService","Membership & Eligibility Service",APP, 1900,500,210,50)
put("ac_malaffi","ApplicationComponent","Malaffi HIE (external)",APP, 1900,620,210,64)
put("if_malapi","ApplicationInterface","Malaffi API",APP, 1700,629,146,46)
# Passive band (bottom channel) — challenge,eligresult,segment,demographic,telemetry,clinical
_data=[("do_challenge","Challenge Data"),("do_eligresult","Eligibility Result"),("do_segment","Segment Data"),
       ("do_demographic","Demographic Data"),("do_telemetry","Telemetry Data"),("do_clinical","Clinical Data")]
for k,(i,nm) in enumerate(_data): put(i,"DataObject",nm,APP, 200+k*236, 760, 180, 52)

# ---------------- relationships: (id, src, tgt, type, [access]) ----------------
R = []
def rel(i,s,t,ty,acc=None): R.append((i,s,t,ty,acc))
rel("r1","act_member","ev_login","Triggering")
rel("r2","ev_login","fn_present","Triggering")
rel("r3","fn_present","if_pubapi","Triggering")
rel("r4","if_pubapi","ia_elig","Triggering")
rel("r5","ia_elig","fn_elig","Triggering")
rel("r6","fn_elig","fn_localmem","Triggering")
rel("r7","fn_localmem","ev_elig","Triggering")
rel("r8","as_elig","fn_p9","Serving")          # service serves business function (up)
rel("r9","ia_elig","as_elig","Realization")    # interaction realizes the service (up)
rel("r10","ac_malaffi","if_malapi","Assignment")
rel("r11","ac_malaffi","as_malmember","Realization")
rel("r12","if_malapi","fn_elig","Serving")     # API serves the resolution
rel("r13","as_malmember","fn_elig","Serving")  # membership service serves the resolution
# access (data) — Read inputs / Write outputs
for i,(s,t,acc) in enumerate([("fn_elig","do_challenge","Read"),("fn_elig","do_eligresult","Write"),
        ("fn_elig","do_segment","Read"),("fn_localmem","do_segment","Read"),
        ("fn_localmem","do_demographic","Read"),("fn_localmem","do_telemetry","Read"),
        ("ac_malaffi","do_clinical","Write")]):
    rel(f"a{i}",s,t,"Access",acc)

# ================= geometry helpers =================
def box(i): b=N[i]; return (b["x"],b["y"],b["x"]+b["w"],b["y"]+b["h"])
def ctr(i): b=N[i]; return (b["x"]+b["w"]/2, b["y"]+b["h"]/2)
LEAVES=[i for i in N if not (i in ("ac_mobile","col_elig"))]   # containers are not obstacles
def _seg_hits(horizontal, a, b, fixed, ignore):
    lo,hi=min(a,b),max(a,b)
    for e in LEAVES:
        if e in ignore: continue
        x1,y1,x2,y2=box(e)
        if horizontal:
            if y1+1e-6 < fixed < y2-1e-6 and lo < x2-1e-6 and hi > x1+1e-6: return True
        else:
            if x1+1e-6 < fixed < x2-1e-6 and lo < y2-1e-6 and hi > y1+1e-6: return True
    return False
def hfree(y,x1,x2,ign): return not _seg_hits(True,x1,x2,y,ign)
def vfree(x,y1,y2,ign): return not _seg_hits(False,y1,y2,x,ign)

LANE=15            # min spacing between parallel routed runs (no two share a row/column)
USED_Y=[]; USED_X=[]
def _free_lane(desired, used):
    for k in range(0,80):
        for sgn in ((1,-1) if k else (1,)):
            v=desired+sgn*k*LANE
            if all(abs(v-u)>=LANE-1 for u in used): return v
    return desired

def classify(s,t):
    scx,scy=ctr(s); tcx,tcy=ctr(t)
    if abs(scy-tcy) < 70:                         # same band -> horizontal
        return 'H', ('R' if tcx>scx else 'L'), ('L' if tcx>scx else 'R')
    return 'V', ('B' if tcy>scy else 'T'), ('T' if tcy>scy else 'B')   # cross band -> vertical

def anchor(i, side, d):
    x,y=N[i]["x"],N[i]["y"]; w,h=N[i]["w"],N[i]["h"]; cx,cy=ctr(i)
    return {'B':(cx+d, y+h), 'T':(cx+d, y), 'R':(x+w, cy+d), 'L':(x, cy+d)}[side]

def build_routes():
    """Allocate fan anchors per (node,side) then route each edge orthogonally with a unique lane."""
    meta=[classify(s,t) for (_,s,t,_,_) in R]
    use={}                                        # (node,side) -> [(idx, role, key)]
    for idx,(rid,s,t,ty,acc) in enumerate(R):
        o,ss,st=meta[idx]
        ks=ctr(t)[0] if ss in 'TB' else ctr(t)[1]
        kt=ctr(s)[0] if st in 'TB' else ctr(s)[1]
        use.setdefault((s,ss),[]).append((idx,'S',ks)); use.setdefault((t,st),[]).append((idx,'T',kt))
    off={}
    for (node,side),mem in use.items():
        mem.sort(key=lambda z:z[2]); n=len(mem); span=(N[node]["w"] if side in 'TB' else N[node]["h"])*0.6
        for j,(idx,role,_) in enumerate(mem):
            off[(idx,role)]=((j+1)/(n+1)-0.5)*span
    routes={}
    for idx,(rid,s,t,ty,acc) in enumerate(R):
        o,ss,st=meta[idx]; ign={s,t}
        # center anchors (d=0): this tool draws connectors from the node CENTRE, so an offset attach
        # point would force a diagonal first segment. Exit straight from centre; lanes stay unique.
        sa=anchor(s,ss,0); ta=anchor(t,st,0)
        if o=='V':
            if abs(sa[0]-ta[0])<2 and vfree(sa[0],sa[1],ta[1],ign): routes[idx]=[sa,ta]; continue
            # jog to the target's own column right below the source box, so the long descent is at a
            # UNIQUE column (no vertical overlap); only a tiny centre stub remains shared.
            lo,hi=min(sa[1],ta[1]),max(sa[1],ta[1]); des=sa[1]+(16 if ta[1]>sa[1] else -16)
            ly=None
            for k in range(0,80):
                for sgn in ((1,-1) if k else (1,)):
                    v=des+sgn*k*LANE
                    if not(lo-1<=v<=hi+1): continue
                    if any(abs(v-u)<LANE for u in USED_Y): continue
                    if hfree(v,sa[0],ta[0],ign) and vfree(sa[0],sa[1],v,ign) and vfree(ta[0],v,ta[1],ign): ly=v;break
                if ly is not None: break
            if ly is None: ly=_free_lane(des,USED_Y)
            USED_Y.append(ly); routes[idx]=[sa,(sa[0],ly),(ta[0],ly),ta]
        else:
            if abs(sa[1]-ta[1])<2 and hfree(sa[1],sa[0],ta[0],ign): routes[idx]=[sa,ta]; continue
            lo,hi=min(sa[0],ta[0]),max(sa[0],ta[0]); des=sa[0]+(16 if ta[0]>sa[0] else -16)
            lx=None
            for k in range(0,80):
                for sgn in ((1,-1) if k else (1,)):
                    v=des+sgn*k*LANE
                    if not(lo-1<=v<=hi+1): continue
                    if any(abs(v-u)<LANE for u in USED_X): continue
                    if vfree(v,sa[1],ta[1],ign) and hfree(sa[1],sa[0],v,ign) and hfree(ta[1],v,ta[0],ign): lx=v;break
                if lx is not None: break
            if lx is None: lx=_free_lane(des,USED_X)
            USED_X.append(lx); routes[idx]=[sa,(lx,sa[1]),(lx,ta[1]),ta]
    return routes

# ================= self-checks (H1,H2,H3,H4) =================
def selfcheck(routes):
    leaves=[i for i in LEAVES]
    for a in range(len(leaves)):
        for b in range(a+1,len(leaves)):
            ia,ib=leaves[a],leaves[b]
            if N[ia]["parent"]==ib or N[ib]["parent"]==ia: continue
            ax1,ay1,ax2,ay2=box(ia); bx1,by1,bx2,by2=box(ib)
            assert not(ax1<bx2 and bx1<ax2 and ay1<by2 and by1<ay2), f"H1 overlap {ia}<>{ib}"
    bad=[]
    seen_h={}; seen_v={}                          # H5b: no two routed mid-run lanes share a row/column
    for idx,pts in routes.items():
        rid,s,t,ty,acc=R[idx]
        segs=list(zip(pts,pts[1:]))
        for k,((x1,y1),(x2,y2)) in enumerate(segs):
            horiz = abs(y1-y2)<1
            if abs(x1-x2)>1 and abs(y1-y2)>1: bad.append(f"DIAGONAL {rid} {s}->{t}")
            if _seg_hits(horiz, (x1 if horiz else y1), (x2 if horiz else y2), (y1 if horiz else x1), {s,t}):
                bad.append(f"H2 {rid} {s}->{t}")
            mid = 0 < k < len(segs)-1              # skip first/last (box-edge stubs share a column by design)
            if mid:
                if horiz and abs(x2-x1)>3:
                    for (a,b) in seen_h.get(round(y1),[]):
                        if min(x1,x2)<max(a,b) and max(x1,x2)>min(a,b): bad.append(f"OVERLAP-H {rid} y={round(y1)}")
                    seen_h.setdefault(round(y1),[]).append((x1,x2))
                elif (not horiz) and abs(y2-y1)>3:
                    for (a,b) in seen_v.get(round(x1),[]):
                        if min(y1,y2)<max(a,b) and max(y1,y2)>min(a,b): bad.append(f"OVERLAP-V {rid} x={round(x1)}")
                    seen_v.setdefault(round(x1),[]).append((y1,y2))
        length=sum(abs(x2-x1)+abs(y2-y1) for (x1,y1),(x2,y2) in segs)
        if length<40: bad.append(f"H3 short {rid} {s}->{t} ({length:.0f})")
    # H4 serving/realization upward (target row above source row)
    for (rid,s,t,ty,acc) in R:
        if ty in ("Serving","Realization") and N[t]["parent"] is None and N[s]["parent"] is None:
            if ctr(t)[1] > ctr(s)[1]+30 and t not in ("fn_elig","fn_localmem"):  # exempt in-flow servings
                bad.append(f"H4 down {rid} {s}->{t}")
    return bad

# ================= emit =================
def emit():
    routes=build_routes()
    bad=selfcheck(routes)
    out=[f'<model xmlns="{NS}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" identifier="m-elig">',
         '<name xml:lang="en">Eligibility Determination (manual)</name>','<elements>']
    for i,b in N.items():
        out.append(f'<element identifier="{i}" xsi:type="{b["t"]}"><name xml:lang="en">{escape(b["n"])}</name></element>')
    out.append('</elements><relationships>')
    for (rid,s,t,ty,acc) in R:
        extra=f' accessType="{acc}"' if acc else ''
        out.append(f'<relationship identifier="{rid}" source="{s}" target="{t}" xsi:type="{ty}"{extra}/>')
    out.append('</relationships><views><diagrams>')
    out.append('<view identifier="v-elig" xsi:type="Diagram"><name xml:lang="en">Eligibility Determination</name>')
    def node(i):
        b=N[i]; r,g,bl=rgb(b["fill"]); container=i in ("ac_mobile","col_elig"); fs=11 if container else 8
        out.append(f'<node identifier="n-{i}" elementRef="{i}" xsi:type="Element" x="{b["x"]}" y="{b["y"]}" w="{b["w"]}" h="{b["h"]}">'
                   f'<style><fillColor r="{r}" g="{g}" b="{bl}"/><lineColor r="90" g="110" b="130"/>'
                   f'<font name="Sans" size="{fs}"><color r="0" g="0" b="0"/></font></style>')
        for c in [k for k in N if N[k]["parent"]==i]: node(c)
        out.append('</node>')
    for i in N:
        if N[i]["parent"] is None: node(i)
    for idx,pts in routes.items():
        rid,s,t,ty,acc=R[idx]
        c=f'<connection identifier="c-{rid}" relationshipRef="{rid}" source="n-{s}" target="n-{t}" xsi:type="Relationship">'
        for (x,y) in pts[1:-1]: c+=f'<bendpoint x="{round(x)}" y="{round(y)}"/>'
        out.append(c+'</connection>')
    out.append('</view></diagrams></views></model>')
    open("eligibility-manual.archimate.xml","w").write("\n".join(out))
    return bad

if __name__=="__main__":
    bad=emit()
    print("elements:",len(N)," relationships:",len(R))
    if bad: print("INVARIANT VIOLATIONS:"); [print("  -",x) for x in bad]
    else: print("H1/H2/H3/H4 all pass — no overlaps, no edge over an element, min length ok, serving/realization upward")
    print("wrote: eligibility-manual.archimate.xml")
