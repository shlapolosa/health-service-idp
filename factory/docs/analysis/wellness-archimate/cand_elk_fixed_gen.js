#!/usr/bin/env node
/*
 * Candidate: ELK as an EDGE ROUTER ONLY (not a band layout engine).
 *
 * Idea: the prompt established ELK's *layered* algorithm refuses uniform bands.
 * But ELK also has a "fixed" node-placement mode where WE supply every node's
 * x/y/width/height and ELK only computes ORTHOGONAL, obstacle-avoiding edge
 * routes. So we:
 *   1. compute uniform full-width bands + a row of comps inside each (in Python-
 *      equivalent JS here) -> deterministic, guaranteed uniform + ordered.
 *   2. hand ELK the fixed coordinates and ask ONLY for ORTHOGONAL routing.
 *
 * Output: cand-elkfixed.svg  (then rsvg-convert -> png)
 */
const fs = require('fs');
const path = require('path');
const ELK = require('elkjs');
const elk = new ELK();

const HERE = __dirname;
const data = JSON.parse(fs.readFileSync(path.join(HERE, 'c4-data.json')));
const zones = data.zones, comps = data.comps, edges = data.edges;

// ---- deterministic uniform band geometry ----
const NODE_W = 150, NODE_H = 70, NODE_GAP = 28;
const BAND_PAD_X = 24, BAND_PAD_TOP = 34, BAND_PAD_BOT = 18;
const BAND_GAP = 46, MARGIN = 30;

const byZone = {};
zones.forEach(z => byZone[z.id] = []);
comps.forEach(c => (byZone[c.zone] = byZone[c.zone] || []).push(c));

const maxCols = Math.max(...zones.map(z => byZone[z.id].length));
const BAND_W = BAND_PAD_X * 2 + maxCols * NODE_W + (maxCols - 1) * NODE_GAP;
const BAND_H = BAND_PAD_TOP + NODE_H + BAND_PAD_BOT;

// place
const nodePos = {};   // id -> {x,y,w,h} absolute
let y = MARGIN;
const bandRects = [];
for (const z of zones) {
  const cs = byZone[z.id];
  const bx = MARGIN, by = y;
  bandRects.push({id: z.id, x: bx, y: by, w: BAND_W, h: BAND_H, label: z.label, fill: z.nodefill, stroke: z.stroke});
  // center the row of comps in the band
  const rowW = cs.length * NODE_W + (cs.length - 1) * NODE_GAP;
  let cx = bx + (BAND_W - rowW) / 2;
  const cy = by + BAND_PAD_TOP;
  for (const c of cs) {
    nodePos[c.id] = {x: cx, y: cy, w: NODE_W, h: NODE_H, zone: z.id, fill: z.nodefill, stroke: z.stroke, title: c.title};
    cx += NODE_W + NODE_GAP;
  }
  y += BAND_H + BAND_GAP;
}
const TOTAL_W = MARGIN * 2 + BAND_W;
const TOTAL_H = y - BAND_GAP + MARGIN;

// ---- build ELK graph: flat, fixed positions, route-only ----
const elkNodes = Object.entries(nodePos).map(([id, p]) => ({
  id, x: p.x, y: p.y, width: p.w, height: p.h,
}));
const compZone = {}; comps.forEach(c => compZone[c.id] = c.zone);
const elkEdges = edges
  .filter(e => nodePos[e.s] && nodePos[e.t])
  .map((e, i) => ({id: 'e' + i, sources: [e.s], targets: [e.t], _type: e.type}));

const graph = {
  id: 'root',
  layoutOptions: {
    'org.eclipse.elk.algorithm': 'org.eclipse.elk.layered',
    'org.eclipse.elk.edgeRouting': 'ORTHOGONAL',
    // keep OUR node coordinates: interactive everything
    'org.eclipse.elk.layered.layering.strategy': 'INTERACTIVE',
    'org.eclipse.elk.layered.crossingMinimization.strategy': 'INTERACTIVE',
    'org.eclipse.elk.layered.nodePlacement.strategy': 'INTERACTIVE',
    'org.eclipse.elk.interactive': 'true',
    'org.eclipse.elk.layered.cycleBreaking.strategy': 'INTERACTIVE',
  },
  children: elkNodes,
  edges: elkEdges,
};

const TYPE_STYLE = {
  sync:     {stroke: '#333333', w: 2, dash: ''},
  async:    {stroke: '#9673A6', w: 2, dash: '6 4'},
  xtrust:   {stroke: '#B85450', w: 3, dash: '3 3'},
  identity: {stroke: '#3A7CA5', w: 2, dash: '8 4'},
};

elk.layout(graph).then(g => {
  // map routed edges
  const routes = {};
  (g.edges || []).forEach(e => {
    const secs = e.sections || [];
    if (!secs.length) return;
    const s = secs[0];
    const pts = [s.startPoint, ...(s.bendPoints || []), s.endPoint];
    routes[e.id] = {pts, type: e._type};
  });

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${TOTAL_W}" height="${TOTAL_H}" viewBox="0 0 ${TOTAL_W} ${TOTAL_H}" font-family="Helvetica,Arial,sans-serif">`;
  svg += `<rect width="100%" height="100%" fill="#ffffff"/>`;
  // bands
  for (const b of bandRects) {
    svg += `<rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="6" fill="${b.fill}" fill-opacity="0.35" stroke="${b.stroke}" stroke-width="2"/>`;
    svg += `<text x="${b.x + 10}" y="${b.y + 20}" font-size="14" font-weight="bold" fill="${b.stroke}">${esc(b.label)}</text>`;
  }
  // edges
  for (const id in routes) {
    const r = routes[id];
    const st = TYPE_STYLE[r.type] || TYPE_STYLE.sync;
    const d = r.pts.map((p, i) => (i ? 'L' : 'M') + ` ${p.x} ${p.y}`).join(' ');
    svg += `<path d="${d}" fill="none" stroke="${st.stroke}" stroke-width="${st.w}" ${st.dash ? `stroke-dasharray="${st.dash}"` : ''}/>`;
    const last = r.pts[r.pts.length - 1], prev = r.pts[r.pts.length - 2] || last;
    svg += arrow(prev, last, st.stroke);
  }
  // nodes
  for (const id in nodePos) {
    const p = nodePos[id];
    svg += `<rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="6" fill="${p.fill}" stroke="${p.stroke}" stroke-width="1.5"/>`;
    svg += wrapText(p.title, p.x + p.w / 2, p.y + p.h / 2, p.w - 12);
  }
  svg += `</svg>`;
  const out = path.join(HERE, 'cand-elkfixed.svg');
  fs.writeFileSync(out, svg);
  console.log('wrote', out, 'bands', bandRects.length, 'edges routed', Object.keys(routes).length, 'canvas', TOTAL_W + 'x' + TOTAL_H);
}).catch(err => { console.error('ELK failed:', err.message); process.exit(1); });

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function arrow(a, b, color){
  const ang = Math.atan2(b.y - a.y, b.x - a.x), L = 9, w = 4;
  const x1 = b.x - L*Math.cos(ang) + w*Math.sin(ang), y1 = b.y - L*Math.sin(ang) - w*Math.cos(ang);
  const x2 = b.x - L*Math.cos(ang) - w*Math.sin(ang), y2 = b.y - L*Math.sin(ang) + w*Math.cos(ang);
  return `<polygon points="${b.x},${b.y} ${x1},${y1} ${x2},${y2}" fill="${color}"/>`;
}
function wrapText(t, cx, cy, maxw){
  const words = String(t).split(/\s+/); const lines = []; let cur = '';
  const cpl = Math.max(8, Math.floor(maxw / 6.5));
  for (const w of words){ if ((cur + ' ' + w).trim().length > cpl){ lines.push(cur.trim()); cur = w; } else cur += ' ' + w; }
  if (cur.trim()) lines.push(cur.trim());
  const lh = 12, start = cy - (lines.length - 1) * lh / 2;
  return lines.map((l, i) => `<text x="${cx}" y="${start + i*lh}" font-size="10.5" text-anchor="middle" dominant-baseline="middle" fill="#222">${esc(l)}</text>`).join('');
}
