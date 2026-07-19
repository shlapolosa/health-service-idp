#!/usr/bin/env node
/* eslint-disable no-console */
'use strict';

/*
 * gen_elk_c4_v3.js  —  Approach B: fixed uniform bands + barycenter node ordering
 *
 * Goal: keep v1's uniform, full-width, ALIGNED band containers (one row per zone,
 * stacked top->bottom in zones[] order) AND v1's exact SVG styling, but cut edge
 * crossings the way v2 does — WITHOUT letting bands sprawl.
 *
 * Two additions over v1:
 *   1. Barycenter/median node ordering within each band (down/up sweeps). This
 *      reorders WHO sits where in each row so connected nodes line up vertically.
 *      Bands stay full-width, uniform, evenly-spaced, centered.
 *   2. A cleaner orthogonal router with per-node port spreading + per-edge
 *      gap-lane staggering so parallel runs in the same inter-band gap don't overlap.
 *
 * Pure placement — no ELK needed. Reuses v1 geometry + styling verbatim.
 */

const fs = require('fs');
const path = require('path');

const DIR = __dirname;
const DATA = JSON.parse(fs.readFileSync(path.join(DIR, 'c4-data.json'), 'utf8'));

// ---------------------------------------------------------------------------
// Geometry constants (identical to v1)
// ---------------------------------------------------------------------------
const COMP_W = 200;
const COMP_H = 78;
const BAND_LABEL_H = 26;
const FONT = 'Helvetica, Arial, sans-serif';

const BAND_PAD_TOP = BAND_LABEL_H + 16;
const BAND_PAD_SIDE = 18;
const BAND_PAD_BOTTOM = 18;
const COMP_GAP = 34; // min horizontal gap between comps within a band
const BAND_GAP = 64; // vertical gap between bands

const zoneById = new Map(DATA.zones.map((z) => [z.id, z]));
const compById = new Map(DATA.comps.map((c) => [c.id, c]));

// Group components by zone, preserving comps[] order within a band.
const compsByZone = new Map(DATA.zones.map((z) => [z.id, []]));
for (const c of DATA.comps) {
  if (!compsByZone.has(c.zone)) {
    throw new Error(`Component ${c.id} references unknown zone ${c.zone}`);
  }
  compsByZone.get(c.zone).push(c);
}

const zoneIndex = new Map(DATA.zones.map((z, i) => [z.id, i]));

// ---------------------------------------------------------------------------
// STEP 1: fixed uniform band geometry.
//
// The widest band defines the canvas width. EVERY band spans that same full
// width (uniform + aligned), and its nodes are evenly spaced across it. This is
// v1's look: full-width rows, vertically stacked in zones[] order. The ONLY
// thing barycenter ordering changes is the left->right ORDER of nodes inside a
// row; the row's geometry (full width, even spacing) never changes.
// ---------------------------------------------------------------------------

// Width needed by the band with the most comps (so even spacing never overlaps).
const maxCount = Math.max(...DATA.zones.map((z) => compsByZone.get(z.id).length));
const innerW = maxCount * COMP_W + (maxCount - 1) * COMP_GAP;
const BAND_W = BAND_PAD_SIDE * 2 + innerW; // every band uses this full width
const CANVAS_W = BAND_W;

// Per-band vertical origin (stacked top->bottom, zones[] order).
const bandY = new Map();
{
  let cursorY = 0;
  for (const z of DATA.zones) {
    bandY.set(z.id, cursorY);
    cursorY += BAND_PAD_TOP + COMP_H + BAND_PAD_BOTTOM + BAND_GAP;
  }
}
const BAND_H = BAND_PAD_TOP + COMP_H + BAND_PAD_BOTTOM;
const CANVAS_H =
  DATA.zones.length * BAND_H + (DATA.zones.length - 1) * BAND_GAP;

// Even-spacing slot centers across the FULL band width for n nodes.
// Always full-width: slots span the inner area edge-to-edge and are centered.
function slotCentersX(n) {
  const left = BAND_PAD_SIDE + COMP_W / 2;
  const right = BAND_W - BAND_PAD_SIDE - COMP_W / 2;
  if (n <= 1) return [BAND_W / 2];
  const step = (right - left) / (n - 1);
  const out = [];
  for (let i = 0; i < n; i++) out.push(left + i * step);
  return out;
}

// order[zoneId] = array of comp ids, left->right. Init = comps[] order.
const order = new Map();
for (const z of DATA.zones) order.set(z.id, compsByZone.get(z.id).map((c) => c.id));

// Build absolute node boxes from the current per-band order.
function buildBoxes() {
  const boxes = new Map(); // id -> {x,y,w,h,cx,cy,zone}
  for (const z of DATA.zones) {
    const ids = order.get(z.id);
    const cxs = slotCentersX(ids.length);
    const by = bandY.get(z.id);
    ids.forEach((id, i) => {
      const cx = cxs[i];
      boxes.set(id, {
        x: cx - COMP_W / 2,
        y: by + BAND_PAD_TOP,
        w: COMP_W,
        h: COMP_H,
        cx,
        cy: by + BAND_PAD_TOP + COMP_H / 2,
        zone: z.id,
      });
    });
  }
  return boxes;
}

// ---------------------------------------------------------------------------
// STEP 2: barycenter / median ordering.
//
// Down-sweep then up-sweep for ROUNDS rounds. For each band, each node gets a
// key = median of the current x-rank (slot index) of its neighbours in the
// adjacent band(s). Re-sort the band by that key, then re-emit even-spaced
// full-width positions. Keep the arrangement with the fewest crossings.
// ---------------------------------------------------------------------------

// Adjacency (undirected) for ordering purposes.
const neighbours = new Map(DATA.comps.map((c) => [c.id, []]));
for (const e of DATA.edges) {
  if (neighbours.has(e.s) && neighbours.has(e.t)) {
    neighbours.get(e.s).push(e.t);
    neighbours.get(e.t).push(e.s);
  }
}

function median(arr) {
  if (arr.length === 0) return null;
  const s = arr.slice().sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

// Current slot index (0..n-1) of every node, given the order map.
function slotIndexMap() {
  const idx = new Map();
  for (const z of DATA.zones) {
    order.get(z.id).forEach((id, i) => idx.set(id, i));
  }
  return idx;
}

// Reorder a single band using barycenter keys drawn from one or both adjacent
// bands (whichever zone indices are passed in `refZones`).
function reorderBand(zoneId, refZoneIdxs, idx) {
  const ids = order.get(zoneId);
  const n = ids.length;
  // normalisation: map a neighbour's slot index (in a band of size m) to a
  // fractional rank in [0,1] so bands of different sizes compare fairly.
  const keyed = ids.map((id, curSlot) => {
    const ranks = [];
    for (const nb of neighbours.get(id)) {
      const nbZone = compById.get(nb).zone;
      if (!refZoneIdxs.has(zoneIndex.get(nbZone))) continue;
      const nbIds = order.get(nbZone);
      const m = nbIds.length;
      const r = m <= 1 ? 0.5 : idx.get(nb) / (m - 1);
      ranks.push(r);
    }
    const key = median(ranks);
    // nodes with no qualifying neighbour keep their current relative position
    const fallback = n <= 1 ? 0.5 : curSlot / (n - 1);
    return { id, key: key == null ? fallback : key, curSlot };
  });
  // stable sort by key, tie-break by current slot (keeps things from thrashing)
  keyed.sort((a, b) => (a.key - b.key) || (a.curSlot - b.curSlot));
  order.set(zoneId, keyed.map((k) => k.id));
}

// ---------------------------------------------------------------------------
// Crossing counter: counts pairs of edges whose straight source-center ->
// target-center segments intersect. A stable, layout-independent metric for
// before/after comparison (same metric concept v1/v2 reported).
// ---------------------------------------------------------------------------
function countCrossings(boxes) {
  const segs = [];
  for (const e of DATA.edges) {
    const s = boxes.get(e.s);
    const t = boxes.get(e.t);
    if (!s || !t) continue;
    segs.push({ x1: s.cx, y1: s.cy, x2: t.cx, y2: t.cy });
  }
  function ccw(ax, ay, bx, by, cx, cy) {
    return (cy - ay) * (bx - ax) - (by - ay) * (cx - ax);
  }
  function intersects(a, b) {
    const d1 = ccw(a.x1, a.y1, a.x2, a.y2, b.x1, b.y1);
    const d2 = ccw(a.x1, a.y1, a.x2, a.y2, b.x2, b.y2);
    const d3 = ccw(b.x1, b.y1, b.x2, b.y2, a.x1, a.y1);
    const d4 = ccw(b.x1, b.y1, b.x2, b.y2, a.x2, a.y2);
    if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) &&
        ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) return true;
    return false;
  }
  let n = 0;
  for (let i = 0; i < segs.length; i++) {
    for (let j = i + 1; j < segs.length; j++) {
      if (intersects(segs[i], segs[j])) n++;
    }
  }
  return n;
}

function snapshotOrder() {
  const m = new Map();
  for (const [k, v] of order) m.set(k, v.slice());
  return m;
}
function restoreOrder(snap) {
  for (const [k, v] of snap) order.set(k, v.slice());
}

// ---------------------------------------------------------------------------
// Run the sweeps.
// ---------------------------------------------------------------------------
// Greedy local refinement: try swapping each adjacent pair within every band;
// keep a swap only if it strictly lowers total crossings. Repeats until no
// improving swap exists or a cap is hit. This polishes whatever the barycenter
// sweeps produce and reliably squeezes out residual crossings while leaving the
// uniform full-width geometry untouched (it only changes left->right ORDER).
function greedyAdjacentSwaps(capPasses) {
  let cur = countCrossings(buildBoxes());
  for (let pass = 0; pass < capPasses; pass++) {
    let improvedAny = false;
    for (const z of DATA.zones) {
      const ids = order.get(z.id);
      for (let i = 0; i < ids.length - 1; i++) {
        [ids[i], ids[i + 1]] = [ids[i + 1], ids[i]];
        const c = countCrossings(buildBoxes());
        if (c < cur) { cur = c; improvedAny = true; }
        else { [ids[i], ids[i + 1]] = [ids[i + 1], ids[i]]; } // revert
      }
    }
    if (!improvedAny) break;
  }
  return cur;
}

const ROUNDS = 12;
const crossingsBefore = countCrossings(buildBoxes());

let best = snapshotOrder();
let bestCrossings = crossingsBefore;

function record() {
  const c = countCrossings(buildBoxes());
  if (c < bestCrossings) { bestCrossings = c; best = snapshotOrder(); }
}

for (let round = 0; round < ROUNDS; round++) {
  // DOWN sweep: order band i using the band ABOVE (i-1), already settled.
  for (let i = 1; i < DATA.zones.length; i++) {
    reorderBand(DATA.zones[i].id, new Set([i - 1]), slotIndexMap());
  }
  record();
  // UP sweep: order band i using the band BELOW (i+1).
  for (let i = DATA.zones.length - 2; i >= 0; i--) {
    reorderBand(DATA.zones[i].id, new Set([i + 1]), slotIndexMap());
  }
  record();
  // TWO-SIDED pass: order each band using BOTH neighbours (strongest aligner).
  for (let i = 0; i < DATA.zones.length; i++) {
    const refs = new Set();
    if (i > 0) refs.add(i - 1);
    if (i < DATA.zones.length - 1) refs.add(i + 1);
    reorderBand(DATA.zones[i].id, refs, slotIndexMap());
  }
  record();
}

// Polish the best barycenter result with greedy adjacent swaps.
restoreOrder(best);
greedyAdjacentSwaps(40);
record();
restoreOrder(best);
const boxes = buildBoxes();
const crossingsAfter = countCrossings(boxes);

// ---------------------------------------------------------------------------
// STEP 3: orthogonal router with port spreading + gap-lane staggering.
// ---------------------------------------------------------------------------
function routeEdges() {
  // fan-out attach points along bottom (out) / top (in) edges per node.
  const srcCount = new Map();
  const tgtCount = new Map();
  const srcTotal = new Map();
  const tgtTotal = new Map();
  for (const e of DATA.edges) {
    srcTotal.set(e.s, (srcTotal.get(e.s) || 0) + 1);
    tgtTotal.set(e.t, (tgtTotal.get(e.t) || 0) + 1);
  }
  function portX(box, idx, total) {
    if (total <= 1) return box.x + box.w / 2;
    const inset = 16;
    const span = box.w - inset * 2;
    return box.x + inset + (span * (idx + 1)) / (total + 1);
  }

  // Group cross-band edges by the gap they traverse so we can stagger lanes
  // within each gap deterministically (spread across the gap height).
  const gapEdges = new Map(); // key=`${minBandIdx}` -> list of edge indices
  DATA.edges.forEach((e, i) => {
    const s = boxes.get(e.s);
    const t = boxes.get(e.t);
    if (!s || !t) return;
    const zi = zoneIndex.get(s.zone);
    const zj = zoneIndex.get(t.zone);
    if (zi === zj) return;
    const key = Math.min(zi, zj);
    if (!gapEdges.has(key)) gapEdges.set(key, []);
    gapEdges.get(key).push(i);
  });
  const laneRank = new Map(); // edge index -> rank within its gap group
  for (const [, list] of gapEdges) {
    list.forEach((ei, k) => laneRank.set(ei, { k, total: list.length }));
  }

  const routed = [];
  DATA.edges.forEach((e, i) => {
    const s = boxes.get(e.s);
    const t = boxes.get(e.t);
    if (!s || !t) { routed.push(null); return; }

    const si = srcCount.get(e.s) || 0; srcCount.set(e.s, si + 1);
    const ti = tgtCount.get(e.t) || 0; tgtCount.set(e.t, ti + 1);
    const sx = portX(s, si, srcTotal.get(e.s));
    const tx = portX(t, ti, tgtTotal.get(e.t));

    const sTop = s.y, sBot = s.y + s.h, tTop = t.y, tBot = t.y + t.h;
    const pts = [];

    if (tTop >= sBot) {
      // target below: exit bottom -> gap lane -> enter top
      const gapTop = sBot, gapBot = tTop;
      const lr = laneRank.get(i);
      let laneY;
      if (lr && lr.total > 1) {
        const margin = 10;
        const usable = Math.max(8, (gapBot - gapTop) - margin * 2);
        laneY = gapTop + margin + (usable * (lr.k + 1)) / (lr.total + 1);
      } else {
        laneY = (gapTop + gapBot) / 2;
      }
      pts.push({ x: sx, y: sBot });
      pts.push({ x: sx, y: laneY });
      pts.push({ x: tx, y: laneY });
      pts.push({ x: tx, y: tTop });
    } else if (tBot <= sTop) {
      // target above: exit top -> gap lane -> enter bottom
      const gapTop = tBot, gapBot = sTop;
      const lr = laneRank.get(i);
      let laneY;
      if (lr && lr.total > 1) {
        const margin = 10;
        const usable = Math.max(8, (gapBot - gapTop) - margin * 2);
        laneY = gapTop + margin + (usable * (lr.k + 1)) / (lr.total + 1);
      } else {
        laneY = (gapTop + gapBot) / 2;
      }
      pts.push({ x: sx, y: sTop });
      pts.push({ x: sx, y: laneY });
      pts.push({ x: tx, y: laneY });
      pts.push({ x: tx, y: tBot });
    } else {
      // same band: small hop just below the row, staggered
      const jitter = ((i % 7) - 3) * 4;
      const midY = Math.max(sBot, tBot) + 24 + jitter;
      pts.push({ x: sx, y: sBot });
      pts.push({ x: sx, y: midY });
      pts.push({ x: tx, y: midY });
      pts.push({ x: tx, y: tBot });
    }
    routed.push({ type: e.type, pts });
  });
  return routed.filter(Boolean);
}

const routed = routeEdges();

// ---------------------------------------------------------------------------
// SVG helpers (identical to v1)
// ---------------------------------------------------------------------------
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function tint(hex, amt) {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  const mix = (c) => Math.round(c + (255 - c) * amt);
  const to2 = (c) => c.toString(16).padStart(2, '0');
  return `#${to2(mix(r))}${to2(mix(g))}${to2(mix(b))}`;
}
function wrap(text, maxChars, maxLines) {
  const words = String(text).split(/\s+/);
  const lines = [];
  let cur = '';
  for (const w of words) {
    const cand = cur ? `${cur} ${w}` : w;
    if (cand.length > maxChars && cur) {
      lines.push(cur); cur = w;
      if (lines.length === maxLines - 1) break;
    } else { cur = cand; }
  }
  if (cur) lines.push(cur);
  const used = lines.join(' ').split(/\s+/).length;
  if (used < words.length) {
    lines[lines.length - 1] += ' ' + words.slice(used).join(' ');
  }
  return lines.slice(0, maxLines);
}

const EDGE_STYLE = {
  sync: { stroke: '#000000', width: 1.2, dash: null, marker: 'arrow-sync' },
  async: { stroke: '#7F7F7F', width: 1.2, dash: '6,4', marker: 'arrow-async' },
  xtrust: { stroke: '#B85450', width: 2, dash: null, marker: 'arrow-xtrust' },
  identity: { stroke: '#9966AA', width: 1.4, dash: '5,4', marker: 'arrow-identity' },
};

// ---------------------------------------------------------------------------
// Render (styling identical to v1)
// ---------------------------------------------------------------------------
const totalW = CANVAS_W;
const totalH = CANVAS_H;
const PAD = 24;
const parts = [];

parts.push(
  `<svg xmlns="http://www.w3.org/2000/svg" version="1.1" ` +
    `width="${Math.ceil(totalW + PAD * 2)}" height="${Math.ceil(totalH + PAD * 2)}" ` +
    `viewBox="0 0 ${Math.ceil(totalW + PAD * 2)} ${Math.ceil(totalH + PAD * 2)}" ` +
    `font-family="${FONT}">`,
);

parts.push('<defs>');
for (const [, st] of Object.entries(EDGE_STYLE)) {
  parts.push(
    `<marker id="${st.marker}" viewBox="0 0 10 10" refX="9" refY="5" ` +
      `markerWidth="7" markerHeight="7" orient="auto-start-reverse">` +
      `<path d="M0,0 L10,5 L0,10 z" fill="${st.stroke}"/></marker>`,
  );
}
parts.push('</defs>');
parts.push(`<g transform="translate(${PAD},${PAD})">`);

// 1) Band containers (full width, stacked top->bottom)
let bandCount = 0;
DATA.zones.forEach((z) => {
  const by = bandY.get(z.id);
  bandCount += 1;
  const fill = tint(z.nodefill, 0.55);
  parts.push(
    `<rect x="0.0" y="${by.toFixed(1)}" ` +
      `width="${BAND_W.toFixed(1)}" height="${BAND_H.toFixed(1)}" rx="10" ry="10" ` +
      `fill="${fill}" stroke="${z.stroke}" stroke-width="1.6"/>`,
  );
  parts.push(
    `<text x="14.0" y="${(by + 19).toFixed(1)}" ` +
      `font-size="14" font-weight="700" fill="${z.stroke}">${esc(z.label)}</text>`,
  );
});

// 2) Edges
let edgesRendered = 0;
routed.forEach((edge) => {
  const st = EDGE_STYLE[edge.type] || EDGE_STYLE.sync;
  const pts = edge.pts;
  if (!pts || pts.length < 2) return;
  const d = pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const dash = st.dash ? ` stroke-dasharray="${st.dash}"` : '';
  parts.push(
    `<polyline points="${d}" fill="none" stroke="${st.stroke}" ` +
      `stroke-width="${st.width}"${dash} marker-end="url(#${st.marker})"/>`,
  );
  edgesRendered += 1;
});

// 3) Components
let compsRendered = 0;
DATA.comps.forEach((c) => {
  const r = boxes.get(c.id);
  if (!r) return;
  const z = zoneById.get(c.zone);
  compsRendered += 1;
  parts.push(
    `<rect x="${r.x.toFixed(1)}" y="${r.y.toFixed(1)}" ` +
      `width="${r.w.toFixed(1)}" height="${r.h.toFixed(1)}" rx="7" ry="7" ` +
      `fill="${z.nodefill}" stroke="${z.stroke}" stroke-width="1.4"/>`,
  );
  const cx = r.x + r.w / 2;
  const titleLines = wrap(c.title, 24, 2);
  const startY = r.y + 22 - (titleLines.length - 1) * 6;
  titleLines.forEach((ln, li) => {
    parts.push(
      `<text x="${cx.toFixed(1)}" y="${(startY + li * 14).toFixed(1)}" ` +
        `font-size="12" font-weight="700" text-anchor="middle" ` +
        `fill="#222222">${esc(ln)}</text>`,
    );
  });
  const descLines = wrap(c.desc, 30, 3);
  const dY = r.y + 22 + titleLines.length * 13;
  descLines.forEach((ln, li) => {
    parts.push(
      `<text x="${cx.toFixed(1)}" y="${(dY + li * 11).toFixed(1)}" ` +
        `font-size="8.5" text-anchor="middle" fill="#555555">${esc(ln)}</text>`,
    );
  });
});

// 4) Legend
const legendItems = [
  ['sync', 'sync (HTTP)'],
  ['async', 'async (event)'],
  ['xtrust', 'cross-trust'],
  ['identity', 'identity'],
];
const lx = 6;
let ly = totalH - legendItems.length * 18 - 6;
parts.push(
  `<rect x="${lx - 4}" y="${ly - 16}" width="170" ` +
    `height="${legendItems.length * 18 + 22}" rx="6" ry="6" ` +
    `fill="#ffffff" stroke="#999999" stroke-width="1"/>`,
);
parts.push(
  `<text x="${lx}" y="${ly - 2}" font-size="11" font-weight="700" ` +
    `fill="#333">Edge types</text>`,
);
legendItems.forEach(([k, label]) => {
  const st = EDGE_STYLE[k];
  const dash = st.dash ? ` stroke-dasharray="${st.dash}"` : '';
  parts.push(
    `<line x1="${lx}" y1="${ly + 6}" x2="${lx + 30}" y2="${ly + 6}" ` +
      `stroke="${st.stroke}" stroke-width="${st.width}"${dash} ` +
      `marker-end="url(#${st.marker})"/>`,
  );
  parts.push(
    `<text x="${lx + 38}" y="${ly + 10}" font-size="10" fill="#333">${esc(label)}</text>`,
  );
  ly += 18;
});

parts.push('</g>');
parts.push('</svg>');

const svg = parts.join('\n');
fs.writeFileSync(path.join(DIR, 'solution-architecture-elk.svg'), svg);

// ---------------------------------------------------------------------------
// Assertions / quality bar
// ---------------------------------------------------------------------------
if (compsRendered !== DATA.comps.length) {
  throw new Error(`Component count mismatch: ${compsRendered}/${DATA.comps.length}`);
}
if (edgesRendered !== DATA.edges.length) {
  throw new Error(`Edge count mismatch: ${edgesRendered}/${DATA.edges.length}`);
}
if (bandCount !== DATA.zones.length) {
  throw new Error(`Band count mismatch: ${bandCount}/${DATA.zones.length}`);
}
// Uniform full-width bands: every band rect spans the full canvas width, no sprawl.
// (BAND_W is constant for all bands by construction.)
// Bands ordered top->bottom in zones[] order:
const ys = DATA.zones.map((z) => bandY.get(z.id));
const ascending = ys.every((y, i) => i === 0 || y > ys[i - 1]);
if (!ascending) throw new Error('Bands not in zones[] top->bottom order');

// No node overlaps within a band (even spacing guarantees >= COMP_GAP, assert it).
for (const z of DATA.zones) {
  const ids = order.get(z.id);
  const cxs = slotCentersX(ids.length);
  for (let i = 1; i < cxs.length; i++) {
    if (cxs[i] - cxs[i - 1] < COMP_W - 0.5) {
      throw new Error(`Node overlap in band ${z.id}`);
    }
  }
}

console.log(JSON.stringify({
  ok: true,
  canvas: { w: Math.ceil(totalW), h: Math.ceil(totalH) },
  comps: compsRendered,
  edges: edgesRendered,
  bands: bandCount,
  bandWidthUniform: true,
  bandWidth: Math.round(BAND_W),
  crossingsBefore,
  crossingsAfter,
  v1: 125,
  v2: 34,
  rounds: ROUNDS,
  bandOrderTopToBottomMatchesZones: ascending,
}, null, 2));
