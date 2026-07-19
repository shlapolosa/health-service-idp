#!/usr/bin/env python3
"""Analyze a D2-emitted SVG: band rects (uniform width? ordered?) + edge crossings."""
import re, sys, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
zones = [z["id"] for z in json.load(open(os.path.join(HERE,"c4-data.json")))["zones"]]

def load(p):
    return open(p).read()

def band_rects(svg):
    """Find rects belonging to band containers by matching their id labels."""
    # d2 wraps shapes in <g class="..."> with the element id in a data attr or
    # via the label text. Simplest: find all rect with x/y/width/height and the
    # nearest preceding id. d2 puts id in <g id="..."> on the shape group.
    out = {}
    # groups: <g id="ID-class"...> ... <rect ... x= y= width= height= />
    for m in re.finditer(r'<g[^>]*\bclass="[^"]*"[^>]*>\s*<rect\b([^>]*)/?>', svg):
        attrs = m.group(1)
    # fallback: parse all rects with their coordinates
    rects = []
    for m in re.finditer(r'<rect\b([^>]*?)/?>', svg):
        a = m.group(1)
        def g(k):
            mm = re.search(rf'{k}="([-\d.]+)"', a)
            return float(mm.group(1)) if mm else None
        x,y,w,h = g("x"),g("y"),g("width"),g("height")
        if None in (x,y,w,h): continue
        rects.append((x,y,w,h))
    return rects

def seg_intersect(a,b,c,d):
    def ccw(p,q,r): return (r[1]-p[1])*(q[0]-p[0]) > (q[1]-p[1])*(r[0]-p[0])
    return ccw(a,c,d)!=ccw(b,c,d) and ccw(a,b,c)!=ccw(a,b,d)

def edge_segments(svg):
    """Extract polyline segments from connection paths."""
    segs=[]
    for m in re.finditer(r'<path[^>]*class="connection"[^>]*\bd="([^"]+)"', svg):
        d=m.group(1)
        pts=[]
        for cmd in re.finditer(r'([MLC])\s*([-\d.,\s]+)', d):
            nums=[float(x) for x in re.findall(r'[-\d.]+', cmd.group(2))]
            # take pairs
            for i in range(0,len(nums)-1,2):
                pts.append((nums[i],nums[i+1]))
        for i in range(len(pts)-1):
            segs.append((pts[i],pts[i+1]))
    return segs

def crossings(segs):
    n=0
    for i in range(len(segs)):
        for j in range(i+1,len(segs)):
            a,b=segs[i]; c,d=segs[j]
            # skip if share endpoint
            if a in (c,d) or b in (c,d): continue
            if seg_intersect(a,b,c,d): n+=1
    return n

for tag in ["elk","dagre"]:
    p=os.path.join(HERE,f"cand-d2-{tag}.svg")
    if not os.path.exists(p): continue
    svg=load(p)
    rects=band_rects(svg)
    # band rects = the widest rects (full width). Heuristic: rects with width > 60% max width
    if not rects:
        print(tag,"no rects"); continue
    maxw=max(r[2] for r in rects)
    bands=sorted([r for r in rects if r[2] > 0.85*maxw], key=lambda r:r[1])
    print(f"\n=== {tag} ===")
    print(f"total rects: {len(rects)}, canvas widest rect: {maxw:.0f}")
    print(f"band-like rects (w>85% max): {len(bands)}")
    widths=[round(r[2]) for r in bands]
    xs=[round(r[0]) for r in bands]
    print(f"band widths: {widths}")
    print(f"band x-starts: {xs}")
    uniform = len(set(widths))<=2 and len(set(xs))<=2
    print(f"UNIFORM width+aligned x: {uniform}")
    segs=edge_segments(svg)
    print(f"edge segments: {len(segs)}, CROSSINGS: {crossings(segs)}")
