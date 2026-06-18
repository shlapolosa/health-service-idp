"""archi_layout.py — ArchiMate layered auto-layout + orthogonal router (reusable engine).

Implements the consolidated layout ruleset (see ruleset.md). Declare elements / containers /
relationships; the engine ranks them into top-down layers, orders each row left-to-right, places
them without overlap (centred, good margin), routes every relationship orthogonally with unique
lanes, and emits ArchiMate Model Exchange 3.0 XML. Renders cleanly in Archi desktop with
Preferences > Connections > Routing = orthogonal (and well enough in any viewer).

Pipeline:  declare -> rank (A1-A4) -> order (barycentre) -> place -> route -> verify (H1-H5) -> emit.

Hard invariants (render raises AssertionError if violated):
  H1 no two leaf boxes overlap
  H2 no routed segment crosses a leaf box
  H3 every connector >= MIN_CONN
  H4 every Serving/Realization points upward (served element above its server)
  H5 no two routed mid-run lanes share a row/column   (box-edge trunks are allowed, see ruleset)
"""
from xml.sax.saxutils import escape

# ---- ArchiMate type -> domain + aspect (for the A1/A2 default ranking) ----
LAYER_ORDER = ["Motivation", "Strategy", "Business", "Application", "Technology", "Physical", "Implementation"]
def _layer(t):
    if t in {"Stakeholder","Driver","Assessment","Goal","Outcome","Principle","Requirement",
             "Constraint","Meaning","Value"}: return "Motivation"
    if t in {"Resource","Capability","CourseOfAction","ValueStream"}: return "Strategy"
    if t in {"Equipment","Facility","DistributionNetwork","Material"}: return "Physical"
    if t in {"WorkPackage","Deliverable","ImplementationEvent","Plateau","Gap"}: return "Implementation"
    if t.startswith(("Node","Device","SystemSoftware","Technology","Artifact","CommunicationNetwork","Path")):
        return "Technology"
    if t.startswith("Business") or t in {"Contract","Product","Representation"}: return "Business"
    return "Application"

STD_FILL = {"Motivation":"#E6E6FA","Strategy":"#F5DEAA","Business":"#FFFFB5",
            "Application":"#B5FFFF","Technology":"#C9E7B8","Physical":"#C9E7B8","Implementation":"#E5C9F2"}
def fill_for(atype): return STD_FILL[_layer(atype)]
def _rgb(h): return (int(h[1:3],16),int(h[3:5],16),int(h[5:7],16))


class View:
    HGAP = 72          # min horizontal gap between sibling boxes
    VGAP = 132         # vertical gap between rank rows (keeps connectors >= MIN_CONN)
    LANE = 15          # min spacing between parallel routed runs (no two share a row/column)
    MARGIN = 70        # outer margin
    MIN_CONN = 40      # H3

    def __init__(self, vid, title):
        self.vid, self.title = vid, title
        self.nodes = {}      # eid -> dict
        self.kids = {}       # container eid -> [child ids]
        self.edges = []      # (s,t,rid,kind,access)

    # ---------- declaration ----------
    def node(self, eid, atype, name, fill=None, w=190, h=58, rank=None, order=None):
        self.nodes[eid]=dict(t=atype,n=name,fill=fill or fill_for(atype),w=w,h=h,
                             parent=None,container=False,rank=rank,order=order); return eid
    def container(self, eid, atype, name, children, fill=None, rank=None, order=None):
        self.nodes[eid]=dict(t=atype,n=name,fill=fill or fill_for(atype),w=0,h=0,
                             parent=None,container=True,rank=rank,order=order)
        self.kids[eid]=list(children)
        for c in children: self.nodes[c]["parent"]=eid
        return eid
    def edge(self, s, t, rid, kind, access=None): self.edges.append((s,t,rid,kind,access))

    def _owner(self, e):
        p=self.nodes[e]["parent"]; return p if p is not None else e

    # ---------- 1. rank: layered top-down (A1 domain, A4 served-above-server, flow keeps a row) ----------
    def _rank(self):
        N=self.nodes; top=[e for e in N if N[e]["parent"] is None]
        uf={e:e for e in top}
        def find(x):
            while uf[x]!=x: uf[x]=uf[uf[x]]; x=uf[x]
            return x
        for (s,t,rid,kind,acc) in self.edges:                 # Triggering/Flow keep nodes on one row
            if kind in ("Triggering","Flow"): uf[find(self._owner(s))]=find(self._owner(t))
        grp={e:find(e) for e in top}; groups=set(grp.values())
        above={g:set() for g in groups}
        for (s,t,rid,kind,acc) in self.edges:                 # vertical constraints (above -> below)
            S,T=grp[self._owner(s)],grp[self._owner(t)]
            if S==T: continue
            if kind in ("Serving","Realization"): above[S].add(T)   # server below served
            elif kind=="Access":                  above[T].add(S)   # data below its accessor
        memo={}
        def rk(g,seen):
            if g in memo: return memo[g]
            if g in seen: return 0
            r=max([rk(a,seen|{g})+1 for a in above[g]],default=0); memo[g]=r; return r
        for g in groups: rk(g,set())
        self.grp=grp
        self.rank={e:(N[e]["rank"] if N[e]["rank"] is not None else memo[grp[e]]) for e in top}

    # ---------- 2. order within rows (triggering sequence first, then barycentre) ----------
    def _order(self):
        N=self.nodes; rows={}
        for e in self.rank: rows.setdefault(self.rank[e],[]).append(e)
        # flow position: left->right by the Triggering/Flow chain (so a value chain never reorders)
        succ={}
        for (s,t,rid,kind,acc) in self.edges:
            if kind in ("Triggering","Flow"):
                succ.setdefault(self._owner(s),[]).append(self._owner(t))
        flowpos={}
        def fp(n,seen):
            if n in flowpos: return flowpos[n]
            if n in seen: return 0
            preds=[m for m in succ if n in succ.get(m,[])]
            p=max([fp(m,seen|{n})+1 for m in preds],default=0); flowpos[n]=p; return p
        for n in list(succ)+[x for v in succ.values() for x in v]: fp(n,set())
        adj={}
        for (s,t,rid,kind,acc) in self.edges:
            S,T=self._owner(s),self._owner(t)
            if S in self.rank and T in self.rank: adj.setdefault(S,[]).append(T); adj.setdefault(T,[]).append(S)
        idx={}
        for r in rows:
            rows[r].sort(key=lambda e:(N[e]["order"] is None, N[e]["order"] or 0, flowpos.get(e,0)))
            for i,e in enumerate(rows[r]): idx[e]=i
        for _ in range(6):
            for r in sorted(rows):
                def bary(e):
                    ns=[idx[a] for a in adj.get(e,[]) if a in idx and self.rank[a]!=r]
                    return sum(ns)/len(ns) if ns else idx[e]
                # keep each flow-chain (triggering group) contiguous, ordered by where it connects;
                # within a chain order by flow position; non-flow nodes ride barycentre.
                gmembers={}
                for e in rows[r]: gmembers.setdefault(self.grp.get(e,e),[]).append(e)
                gbary={g:(sum(bary(m) for m in ms)/len(ms)) for g,ms in gmembers.items()}
                rows[r].sort(key=lambda e:(N[e]["order"] if N[e]["order"] is not None else 1e9,
                                           gbary[self.grp.get(e,e)],
                                           flowpos[e] if e in flowpos else 1e6, bary(e)))
                for i,e in enumerate(rows[r]): idx[e]=i
        self.rows=rows

    # ---------- 3. place (centred rows, container children inline) ----------
    def _place(self):
        N=self.nodes; IPAD,ICAP=18,28
        for cid,ch in self.kids.items():
            cw=sum(N[c]["w"] for c in ch)+self.HGAP*(len(ch)-1)+2*IPAD
            N[cid]["w"]=max(cw,180); N[cid]["h"]=max(N[c]["h"] for c in ch)+ICAP+IPAD
        rows=self.rows
        rowW={r:sum(N[e]["w"] for e in rows[r])+self.HGAP*(len(rows[r])-1) for r in rows}
        full=max(rowW.values()) if rowW else 400
        self.pos={}; y=self.MARGIN
        for r in sorted(rows):
            rh=max(N[e]["h"] for e in rows[r]); x=self.MARGIN+(full-rowW[r])/2
            for e in rows[r]:
                self.pos[e]=(round(x),round(y+(rh-N[e]["h"])/2)); x+=N[e]["w"]+self.HGAP
            y+=rh+self.VGAP
        self.canvas=(round(full+2*self.MARGIN),round(y-self.VGAP+self.MARGIN))
        for cid,ch in self.kids.items():
            cx,cy=self.pos[cid]; x=cx+IPAD
            for c in sorted(ch,key=lambda c:(N[c]["order"] is None,N[c]["order"] or 0)):
                self.pos[c]=(round(x),round(cy+ICAP)); x+=N[c]["w"]+self.HGAP

    # ---------- 4. route (band-aware orthogonal, centre exits, unique lanes) ----------
    def _box(self,i): x,y=self.pos[i]; b=self.nodes[i]; return (x,y,x+b["w"],y+b["h"])
    def _ctr(self,i): x,y=self.pos[i]; b=self.nodes[i]; return (x+b["w"]/2,y+b["h"]/2)
    def _hits(self,horiz,a,b,fixed,ign):
        lo,hi=min(a,b),max(a,b)
        for e in self._leaves:
            if e in ign: continue
            x1,y1,x2,y2=self._box(e)
            if horiz:
                if y1+1e-6<fixed<y2-1e-6 and lo<x2-1e-6 and hi>x1+1e-6: return True
            else:
                if x1+1e-6<fixed<x2-1e-6 and lo<y2-1e-6 and hi>y1+1e-6: return True
        return False
    def _hfree(self,y,x1,x2,ign): return not self._hits(True,x1,x2,y,ign)
    def _vfree(self,x,y1,y2,ign): return not self._hits(False,y1,y2,x,ign)
    def _classify(self,s,t):
        scx,scy=self._ctr(s); tcx,tcy=self._ctr(t)
        if abs(scy-tcy)<70: return 'H',('R' if tcx>scx else 'L'),('L' if tcx>scx else 'R')
        return 'V',('B' if tcy>scy else 'T'),('T' if tcy>scy else 'B')
    def _anchor(self,i,side):
        x,y=self.pos[i]; b=self.nodes[i]; cx,cy=self._ctr(i)
        return {'B':(cx,y+b["h"]),'T':(cx,y),'R':(x+b["w"],cy),'L':(x,cy)}[side]

    def _route_all(self):
        self._leaves=[e for e in self.nodes if not self.nodes[e]["container"]]
        usedY=[]; usedX=[]; routes={}
        for idx,(s,t,rid,kind,acc) in enumerate(self.edges):
            o,ss,st=self._classify(s,t); ign={s,t}
            sa=self._anchor(s,ss); ta=self._anchor(t,st)
            if o=='V':
                if abs(sa[0]-ta[0])<2 and self._vfree(sa[0],sa[1],ta[1],ign): routes[idx]=[sa,ta]; continue
                lo,hi=min(sa[1],ta[1]),max(sa[1],ta[1]); des=sa[1]+(16 if ta[1]>sa[1] else -16); ly=None
                for k in range(0,80):
                    for sg in ((1,-1) if k else (1,)):
                        v=des+sg*k*self.LANE
                        if not(lo-1<=v<=hi+1): continue
                        if any(abs(v-u)<self.LANE for u in usedY): continue
                        if self._hfree(v,sa[0],ta[0],ign) and self._vfree(sa[0],sa[1],v,ign) and self._vfree(ta[0],v,ta[1],ign): ly=v;break
                    if ly is not None: break
                if ly is None: ly=des
                usedY.append(ly); routes[idx]=[sa,(sa[0],ly),(ta[0],ly),ta]
            else:
                if abs(sa[1]-ta[1])<2 and self._hfree(sa[1],sa[0],ta[0],ign): routes[idx]=[sa,ta]; continue
                lo,hi=min(sa[0],ta[0]),max(sa[0],ta[0]); des=sa[0]+(16 if ta[0]>sa[0] else -16); lx=None
                for k in range(0,80):
                    for sg in ((1,-1) if k else (1,)):
                        v=des+sg*k*self.LANE
                        if not(lo-1<=v<=hi+1): continue
                        if any(abs(v-u)<self.LANE for u in usedX): continue
                        if self._vfree(v,sa[1],ta[1],ign) and self._hfree(sa[1],sa[0],v,ign) and self._hfree(ta[1],v,ta[0],ign): lx=v;break
                    if lx is not None: break
                if lx is None: lx=des
                usedX.append(lx); routes[idx]=[sa,(lx,sa[1]),(lx,ta[1]),ta]
        return routes

    # ---------- 5. verify ----------
    def _check(self,routes):
        N=self.nodes; bad=[]
        leaves=self._leaves
        for a in range(len(leaves)):
            for b in range(a+1,len(leaves)):
                ia,ib=leaves[a],leaves[b]
                if N[ia]["parent"]==ib or N[ib]["parent"]==ia: continue
                ax1,ay1,ax2,ay2=self._box(ia); bx1,by1,bx2,by2=self._box(ib)
                if ax1<bx2 and bx1<ax2 and ay1<by2 and by1<ay2: bad.append(f"H1 overlap {ia}<>{ib}")
        seenH={}; seenV={}
        for idx,pts in routes.items():
            s,t,rid,kind,acc=self.edges[idx]
            segs=list(zip(pts,pts[1:]))
            for k,((x1,y1),(x2,y2)) in enumerate(segs):
                horiz=abs(y1-y2)<1
                if abs(x1-x2)>1 and abs(y1-y2)>1: bad.append(f"DIAGONAL {rid}")
                if self._hits(horiz,(x1 if horiz else y1),(x2 if horiz else y2),(y1 if horiz else x1),{s,t}): bad.append(f"H2 {rid}")
                if 0<k<len(segs)-1:
                    if horiz and abs(x2-x1)>3:
                        for (a,b) in seenH.get(round(y1),[]):
                            if min(x1,x2)<max(a,b) and max(x1,x2)>min(a,b): bad.append(f"H5 overlap-H {rid}")
                        seenH.setdefault(round(y1),[]).append((x1,x2))
                    elif (not horiz) and abs(y2-y1)>3:
                        for (a,b) in seenV.get(round(x1),[]):
                            if min(y1,y2)<max(a,b) and max(y1,y2)>min(a,b): bad.append(f"H5 overlap-V {rid}")
                        seenV.setdefault(round(x1),[]).append((y1,y2))
            if sum(abs(x2-x1)+abs(y2-y1) for (x1,y1),(x2,y2) in segs)<self.MIN_CONN: bad.append(f"H3 short {rid}")
        for (s,t,rid,kind,acc) in self.edges:
            if kind in ("Serving","Realization") and N[s]["parent"] is None and N[t]["parent"] is None:
                if self._ctr(t)[1]>self._ctr(s)[1]+30: bad.append(f"H4 down {rid}")
        return bad

    # ---------- build (layout + route + verify) ----------
    def build(self, strict=True):
        self._rank(); self._order(); self._place()
        self.routes=self._route_all(); self.violations=self._check(self.routes)
        if self.violations and strict:
            raise AssertionError(f"[{self.vid}] invariant violations: {self.violations[:8]}")
        return self

    def _view_xml(self):
        out=[f'<view identifier="{self.vid}" xsi:type="Diagram"><name xml:lang="en">{escape(self.title)}</name>']
        # node ids are namespaced by view so an element can appear in several views
        def emit(i):
            x,y=self.pos[i]; b=self.nodes[i]; r,g,bl=_rgb(b["fill"]); fs=11 if b["container"] else 8
            out.append(f'<node identifier="n-{self.vid}-{i}" elementRef="{i}" xsi:type="Element" x="{x}" y="{y}" w="{b["w"]}" h="{b["h"]}">'
                       f'<style><fillColor r="{r}" g="{g}" b="{bl}"/><lineColor r="90" g="110" b="130"/>'
                       f'<font name="Sans" size="{fs}"><color r="0" g="0" b="0"/></font></style>')
            for c in self.kids.get(i,[]): emit(c)
            out.append('</node>')
        for i in self.nodes:
            if self.nodes[i]["parent"] is None: emit(i)
        for idx,pts in self.routes.items():
            s,t,rid,kind,acc=self.edges[idx]
            c=(f'<connection identifier="c-{self.vid}-{rid}" relationshipRef="{rid}" '
               f'source="n-{self.vid}-{s}" target="n-{self.vid}-{t}" xsi:type="Relationship">')
            for (x,y) in pts[1:-1]: c+=f'<bendpoint x="{round(x)}" y="{round(y)}"/>'
            out.append(c+'</connection>')
        out.append('</view>')
        return "\n".join(out)

    # ---------- render (single-view standalone model) ----------
    def render(self, strict=True):
        return compose(f"m-{self.vid}", self.title, [self], strict=strict)


def compose(model_id, title, views, strict=True):
    """Merge several Views into one importable ArchiMate model (shared elements/relationships,
    multiple diagrams). Element/relationship definitions are de-duped by id."""
    NS="http://www.opengroup.org/xsd/archimate/3.0/"
    els={}; rels={}
    for v in views:
        v.build(strict=strict)
        for i,b in v.nodes.items(): els[i]=(b["t"],b["n"])
        for (s,t,rid,kind,acc) in v.edges: rels[rid]=(s,t,kind,acc)
    out=[f'<model xmlns="{NS}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" identifier="{model_id}">',
         f'<name xml:lang="en">{escape(title)}</name>','<elements>']
    for i,(t,n) in els.items():
        out.append(f'<element identifier="{i}" xsi:type="{t}"><name xml:lang="en">{escape(n)}</name></element>')
    out.append('</elements><relationships>')
    for rid,(s,t,kind,acc) in rels.items():
        ex=f' accessType="{acc}"' if acc else ''
        out.append(f'<relationship identifier="{rid}" source="{s}" target="{t}" xsi:type="{kind}"{ex}/>')
    out.append('</relationships><views><diagrams>')
    for v in views: out.append(v._view_xml())
    out.append('</diagrams></views></model>')
    return "\n".join(out)
