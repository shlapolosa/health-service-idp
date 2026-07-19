#!/usr/bin/env python3
"""Generate a D2 source file from c4-data.json for the banded swimlane C4 look.

Strategy for FIXED UNIFORM BANDS:
  - root sets `grid-rows` per band count won't help; instead we use a single
    top-level grid with grid-columns:1 so the 10 band-containers stack
    vertically in DECLARED ORDER at uniform full width.
  - each band container sets grid-columns:N (or grid-rows:1) so its comps lay
    out in a single row inside it.
Grid layout in D2 IGNORES the layout engine for positioning of grid cells
(it is deterministic), but edges are still routed by the chosen engine
(elk/dagre) with orthogonal obstacle-avoidance.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "c4-data.json")))

zones = data["zones"]
comps = data["comps"]
edges = data["edges"]

# edge type -> style
EDGE_STYLE = {
    "sync":     '{style.stroke: "#333333"; style.stroke-width: 2}',
    "async":    '{style.stroke: "#9673A6"; style.stroke-width: 2; style.stroke-dash: 4}',
    "xtrust":   '{style.stroke: "#B85450"; style.stroke-width: 3; style.stroke-dash: 2}',
    "identity": '{style.stroke: "#3A7CA5"; style.stroke-width: 2; style.stroke-dash: 6}',
}

comps_by_zone = {z["id"]: [] for z in zones}
for c in comps:
    comps_by_zone.setdefault(c["zone"], []).append(c)

def esc(s):
    return s.replace('"', "'")

lines = []
lines.append("# auto-generated D2 banded swimlane C4")
lines.append("direction: down")
lines.append("")
# top-level grid: one column => bands stack vertically in declared order, uniform width
lines.append("vars: {}")
lines.append("")

# We wrap all bands in a single parent grid container to force vertical stacking.
# grid-columns: 1 => single column => rows stacked top to bottom, full width.
lines.append("layers_root: {")
lines.append("  grid-columns: 1")
lines.append("  grid-gap: 40")
lines.append("")

for z in zones:
    zid = z["id"]
    zlabel = esc(z["label"])
    czs = comps_by_zone.get(zid, [])
    ncols = max(1, len(czs))
    lines.append(f'  {zid}: "{zlabel}" {{')
    lines.append(f"    grid-rows: 1")
    lines.append(f"    grid-gap: 30")
    lines.append(f'    style.fill: "{z["nodefill"]}"')
    lines.append(f'    style.stroke: "{z["stroke"]}"')
    lines.append(f"    style.stroke-width: 2")
    lines.append(f"    style.font-size: 18")
    lines.append(f"    style.bold: true")
    for c in czs:
        title = esc(c["title"])
        lines.append(f'    {c["id"]}: "{title}" {{')
        lines.append(f'      style.fill: "{z["nodefill"]}"')
        lines.append(f'      style.stroke: "{z["stroke"]}"')
        lines.append(f"      style.border-radius: 6")
        lines.append(f"    }}")
    lines.append("  }")
    lines.append("")

lines.append("}")
lines.append("")

# edges: reference full path layers_root.<zone>.<comp>
comp_zone = {c["id"]: c["zone"] for c in comps}
for e in edges:
    s, t = e["s"], e["t"]
    if s not in comp_zone or t not in comp_zone:
        continue
    sp = f'layers_root.{comp_zone[s]}.{s}'
    tp = f'layers_root.{comp_zone[t]}.{t}'
    style = EDGE_STYLE.get(e.get("type", "sync"), EDGE_STYLE["sync"])
    lines.append(f"{sp} -> {tp}: {style}")

out = os.path.join(HERE, "cand-d2.d2")
open(out, "w").write("\n".join(lines) + "\n")
print("wrote", out, "lines", len(lines))
