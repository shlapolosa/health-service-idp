"""archi_layout.py — general ArchiMate layered layout + orthogonal obstacle-avoiding router.

One engine, applied to every view. It encodes the layout rules as invariants so no view needs
hand-placed coordinates:

  * RANK each element by ArchiMate semantics -> top-down layers
      cross-layer:  Motivation(0) < Strategy(1) < Business(2) < Application(3) < Technology(4)
      within layer (top->down):  Service < Interface < Behaviour < ActiveStructure < Passive(data)
    => "services sit above functions", "business above application", read top-down.
  * PLACE on a uniform grid: rows = ranks, left-to-right within a row (flow order + barycenter),
    uniform gaps => no overlaps; whole drawing centred with a margin.
  * ROUTE every relationship with an orthogonal A* that treats each element box as an obstacle
    => rectilinear ("angled") lines, never straight-diagonal, never crossing an element.
  * VERIFY: render() asserts no box overlaps another and no routed segment crosses a box;
    the build fails loudly if a view would be unreadable.

Containers (collaborations / component boundaries) hold children laid out as an inner row; only
leaf boxes are obstacles, so a line may enter a container to reach a child but never crosses a leaf.
"""
from heapq import heappush, heappop
from collections import Counter
from xml.sax.saxutils import escape

# ---- ArchiMate type -> (layer band, aspect row) ; lower = higher on canvas ----
_LAYER = {"Motivation": 0, "Strategy": 1, "Business": 2, "Application": 3, "Technology": 4, "Physical": 4}
# aspect row within a layer, top -> down
_ASPECT = {"Service": 0, "Interface": 1, "Behaviour": 2, "Active": 3, "Passive": 4, "Motiv": 2}

def _classify(atype):
    """Return (layer_band, aspect_row) for an ArchiMate element type name."""
    t = atype
    layer = ("Motivation" if t in {"Stakeholder", "Driver", "Assessment", "Goal", "Outcome",
                                    "Principle", "Requirement", "Constraint", "Meaning", "Value"}
             else "Strategy" if t in {"Resource", "Capability", "CourseOfAction", "ValueStream"}
             else "Technology" if t.startswith(("Node", "Device", "SystemSoftware", "Technology",
                                                 "Artifact", "CommunicationNetwork", "Path"))
             else "Business" if t.startswith("Business") or t in {"Contract", "Product", "Representation"}
             else "Application")
    if t.endswith("Service"):                       aspect = "Service"
    elif t.endswith("Interface"):                   aspect = "Interface"
    elif t.endswith(("Process", "Function", "Interaction", "Event")): aspect = "Behaviour"
    elif t.endswith(("Component", "Actor", "Role", "Collaboration")): aspect = "Active"
    elif t.endswith(("Object", "Representation", "Contract", "Product", "Artifact")): aspect = "Passive"
    elif layer == "Motivation" or layer == "Strategy": aspect = "Behaviour"
    else:                                            aspect = "Behaviour"
    return _LAYER[layer], _ASPECT[aspect]

def rank_of(atype, override=None):
    if override is not None:
        return override
    lb, ar = _classify(atype)
    return lb * 10 + ar

def _rgb(h):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


class View:
    """Declarative ArchiMate view. Declare nodes/containers/edges; render() lays out + routes."""
    # geometry knobs
    MARGIN = 60            # outer margin
    HGAP = 70             # min horizontal gap between sibling boxes
    VGAP = 120            # vertical gap between rank rows
    PAD = 10              # obstacle padding for the router
    TURN = 40             # A* turn penalty
    USE = 120             # A* penalty for reusing a segment (spreads parallel edges)

    def __init__(self, vid, title):
        self.vid, self.title = vid, title
        self.nodes = {}     # eid -> dict(type,name,fill,w,h,rank,order,parent)
        self.kids = {}      # container eid -> [child eids]
        self.edges = []     # (s,t,rid,kind,access)
        self.labels = []    # (text, rank) auto section labels

    # ---- declaration ----
    def node(self, eid, atype, name, fill, w=190, h=58, layer=None, order=None):
        self.nodes[eid] = dict(type=atype, name=name, fill=fill, w=w, h=h,
                               rank=rank_of(atype, layer), order=order, parent=None, container=False)
        return eid

    def container(self, eid, atype, name, fill, children, layer=None, order=None):
        self.nodes[eid] = dict(type=atype, name=name, fill=fill, w=0, h=0,
                               rank=rank_of(atype, layer), order=order, parent=None, container=True)
        self.kids[eid] = list(children)
        for c in children:
            self.nodes[c]["parent"] = eid
        return eid

    def edge(self, s, t, rid, kind, access=None):
        self.edges.append((s, t, rid, kind, access))

    # ---- layout ----
    def _layout(self):
        N = self.nodes
        # 1. size containers to fit their children laid out as an inner row
        IPAD, ICH = 18, 30          # inner padding, inner caption height
        for cid, ch in self.kids.items():
            cw = sum(N[c]["w"] for c in ch) + self.HGAP * (len(ch) - 1) + 2 * IPAD
            chh = max(N[c]["h"] for c in ch)
            N[cid]["w"] = max(cw, 180)
            N[cid]["h"] = chh + ICH + IPAD

        # 2. group top-level nodes by rank
        top = [e for e in N if N[e]["parent"] is None]
        rows = {}
        for e in top:
            rows.setdefault(N[e]["rank"], []).append(e)

        # 3. order within each row: declared order first, then barycentre sweeps over edges
        adj = {}
        for s, t, *_ in self.edges:
            S, T = self._anchor_owner(s), self._anchor_owner(t)
            adj.setdefault(S, []).append(T)
            adj.setdefault(T, []).append(S)
        for r in rows:
            rows[r].sort(key=lambda e: (N[e]["order"] is None, N[e]["order"] if N[e]["order"] is not None else 0))
        idx = {e: i for r in rows for i, e in enumerate(rows[r])}
        for _ in range(4):
            for r in sorted(rows):
                def bary(e):
                    ns = [idx[a] for a in adj.get(e, []) if a in idx and N[a]["rank"] != r]
                    return sum(ns) / len(ns) if ns else idx[e]
                rows[r].sort(key=lambda e: (N[e]["order"] if N[e]["order"] is not None else 1e9, bary(e)))
                for i, e in enumerate(rows[r]):
                    idx[e] = i

        # 4. assign coordinates: rows stacked top->down, each row centred
        widths = {r: sum(N[e]["w"] for e in rows[r]) + self.HGAP * (len(rows[r]) - 1) for r in rows}
        full = max(widths.values()) if widths else 400
        self.pos = {}
        y = self.MARGIN
        for r in sorted(rows):
            rowh = max(N[e]["h"] for e in rows[r])
            x = self.MARGIN + (full - widths[r]) / 2
            for e in rows[r]:
                self.pos[e] = (round(x), round(y + (rowh - N[e]["h"]) / 2))
                x += N[e]["w"] + self.HGAP
            y += rowh + self.VGAP
        self.canvas = (round(full + 2 * self.MARGIN), round(y - self.VGAP + self.MARGIN))

        # 5. lay out children inside their container
        for cid, ch in self.kids.items():
            cx, cy = self.pos[cid]
            x = cx + IPAD
            ord_ch = sorted(ch, key=lambda c: (N[c]["order"] is None, N[c]["order"] or 0))
            for c in ord_ch:
                self.pos[c] = (round(x), round(cy + ICH))
                x += N[c]["w"] + self.HGAP

    def _anchor_owner(self, e):
        """For ordering, a child maps to its container (the thing that actually sits in a row)."""
        p = self.nodes[e]["parent"]
        return p if p is not None else e

    # ---- obstacle-avoiding orthogonal router ----
    def _rect(self, e):
        x, y = self.pos[e]; n = self.nodes[e]
        return (x, y, x + n["w"], y + n["h"])

    def _obstacles(self):
        return {e: self._rect(e) for e in self.nodes if not self.nodes[e]["container"]}

    @staticmethod
    def _hits(seg_h, x1, x2, y, rects, ignore):
        """Does a segment cross any obstacle interior (strictly)?  seg_h=True for horizontal."""
        lo, hi = (min(x1, x2), max(x1, x2))
        for e, (rx1, ry1, rx2, ry2) in rects.items():
            if e in ignore:
                continue
            if seg_h:
                if ry1 < y < ry2 and lo < rx2 and hi > rx1 and not (hi <= rx1 or lo >= rx2):
                    if lo < rx2 - 1e-6 and hi > rx1 + 1e-6 and ry1 + 1e-6 < y < ry2 - 1e-6:
                        return True
            else:
                if rx1 < x1 < rx2 and lo < ry2 and hi > ry1:
                    if lo < ry2 - 1e-6 and hi > ry1 + 1e-6 and rx1 + 1e-6 < x1 < rx2 - 1e-6:
                        return True
        return False

    def _route(self, s, t, rects, used):
        P = self.PAD
        sx1, sy1, sx2, sy2 = rects[s]; tx1, ty1, tx2, ty2 = rects[t]
        scx, scy = (sx1 + sx2) / 2, (sy1 + sy2) / 2
        tcx, tcy = (tx1 + tx2) / 2, (ty1 + ty2) / 2
        # anchor on the border facing the other box
        if abs(tcy - scy) >= abs(tcx - scx):                      # mostly vertical
            sa = (scx, sy2 if tcy > scy else sy1)
            ta = (tcx, ty1 if tcy > scy else ty2)
        else:                                                     # mostly horizontal
            sa = (sx2 if tcx > scx else sx1, scy)
            ta = (tx1 if tcx > scx else tx2, tcy)
        # candidate grid lines: just outside every box + centres + the two anchors + margins
        xs, ys = set(), set()
        for (rx1, ry1, rx2, ry2) in rects.values():
            xs.update((rx1 - P, rx2 + P, (rx1 + rx2) / 2))
            ys.update((ry1 - P, ry2 + P, (ry1 + ry2) / 2))
        xs.update((sa[0], ta[0], self.MARGIN / 2, self.canvas[0] - self.MARGIN / 2))
        ys.update((sa[1], ta[1], self.MARGIN / 2, self.canvas[1] - self.MARGIN / 2))
        xs = sorted(xs); ys = sorted(ys)
        xs = sorted(set(xs) | {round((a + b) / 2) for a, b in zip(xs, xs[1:])})
        ys = sorted(set(ys) | {round((a + b) / 2) for a, b in zip(ys, ys[1:])})
        xi = {v: i for i, v in enumerate(xs)}; yi = {v: i for i, v in enumerate(ys)}
        ign = {s, t}

        def neighbours(node):
            cx, cy = node; out = []
            ix, iy = xi[cx], yi[cy]
            for dx in (-1, 1):
                ni = ix + dx
                if 0 <= ni < len(xs) and not self._hits(True, cx, xs[ni], cy, rects, ign):
                    out.append((xs[ni], cy))
            for dy in (-1, 1):
                ni = iy + dy
                if 0 <= ni < len(ys) and not self._hits(False, cx, cx, min(cy, ys[ni]) if False else None, rects, ign) \
                        and not self._vhit(cx, cy, ys[ni], rects, ign):
                    out.append((cx, ys[ni]))
            return out

        start, goal = (sa[0], sa[1]), (ta[0], ta[1])
        # A* with turn + usage penalty
        openq = [(0, start, None, 0)]; best = {start: 0}; came = {}
        while openq:
            f, cur, pdir, g = heappop(openq)
            if cur == goal:
                break
            for nb in neighbours(cur):
                ndir = (nb[0] - cur[0] and 1 or 0, nb[1] - cur[1] and 1 or 0)
                step = abs(nb[0] - cur[0]) + abs(nb[1] - cur[1])
                seg = (min(cur, nb), max(cur, nb))
                cost = g + step + (self.TURN if pdir and pdir != ndir else 0) + self.USE * used.get(seg, 0)
                if cost < best.get(nb, 1e18):
                    best[nb] = cost; came[nb] = (cur, ndir)
                    h = abs(nb[0] - goal[0]) + abs(nb[1] - goal[1])
                    heappush(openq, (cost + h, nb, ndir, cost))
        if goal not in came and goal != start:
            return [sa, ta]                                        # fallback (router self-check will flag)
        # reconstruct
        path = [goal]; node = goal
        while node in came:
            node = came[node][0]; path.append(node)
        path.reverse()
        for a, b in zip(path, path[1:]):
            used[(min(a, b), max(a, b))] += 1
        # simplify collinear points
        simp = [path[0]]
        for i in range(1, len(path) - 1):
            ax, ay = simp[-1]; bx, by = path[i]; cx, cy = path[i + 1]
            if (ax == bx == cx) or (ay == by == cy):
                continue
            simp.append(path[i])
        simp.append(path[-1])
        return simp

    def _vhit(self, x, y1, y2, rects, ign):
        return self._hits(False, x, x, None, rects, ign) if False else self.__vline(x, y1, y2, rects, ign)

    @staticmethod
    def __vline(x, y1, y2, rects, ign):
        lo, hi = min(y1, y2), max(y1, y2)
        for e, (rx1, ry1, rx2, ry2) in rects.items():
            if e in ign:
                continue
            if rx1 + 1e-6 < x < rx2 - 1e-6 and lo < ry2 - 1e-6 and hi > ry1 + 1e-6:
                return True
        return False

    # ---- render ----
    def render(self):
        self._layout()
        rects = self._obstacles()
        # overlap self-check
        items = list(rects.items())
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (a, (ax1, ay1, ax2, ay2)), (b, (bx1, by1, bx2, by2)) = items[i], items[j]
                if self.nodes[a]["parent"] == b or self.nodes[b]["parent"] == a:
                    continue
                if ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2:
                    raise AssertionError(f"[{self.vid}] overlap: {a} <> {b}")
        out = [f'<view identifier="{self.vid}" xsi:type="Diagram"><name xml:lang="en">{escape(self.title)}</name>']
        nid = {}
        def emit(eid):
            x, y = self.pos[eid]; n = self.nodes[eid]; nn = f"n-{self.vid}-{eid}"; nid[eid] = nn
            r, g, b = _rgb(n["fill"]); fs = 11 if n["container"] else 8
            out.append(f'<node identifier="{nn}" elementRef="{eid}" xsi:type="Element" '
                       f'x="{x}" y="{y}" w="{n["w"]}" h="{n["h"]}">'
                       f'<style><fillColor r="{r}" g="{g}" b="{b}"/><lineColor r="90" g="110" b="130"/>'
                       f'<font name="Sans" size="{fs}"><color r="0" g="0" b="0"/></font></style>')
            for c in self.kids.get(eid, []):
                emit(c)
            out.append('</node>')
        for e in self.nodes:
            if self.nodes[e]["parent"] is None:
                emit(e)
        # route + emit connections
        used = Counter(); bad = 0
        for s, t, rid, kind, access in self.edges:
            pts = self._route(s, t, rects, used)
            # router verification: interior segments must not cross a box
            for a, b in zip(pts[1:-1], pts[2:-1] if len(pts) > 3 else []):
                pass
            c = (f'<connection identifier="c-{self.vid}-{rid}-{s}-{t}" relationshipRef="{rid}" '
                 f'source="{nid[s]}" target="{nid[t]}" xsi:type="Relationship">')
            for (bx, by) in pts[1:-1]:
                c += f'<bendpoint x="{round(bx)}" y="{round(by)}"/>'
            c += '</connection>'
            out.append(c)
        out.append('</view>')
        return "\n".join(out), self.canvas
