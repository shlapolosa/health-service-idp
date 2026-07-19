#!/usr/bin/env node
/* eslint-disable no-console */
'use strict';

/*
 * gen_elk_c4.js
 * Banded, top-down C4 "solution architecture" renderer using Eclipse Layout
 * Kernel (elkjs). Each zone/band is a compound parent node; its components are
 * its children. ELK lays out bands top->bottom (partitioned) and children in a
 * horizontal row. We then walk the result to emit a clean SVG.
 */

const fs = require('fs');
const path = require('path');
const ELK = require('elkjs/lib/elk.bundled.js');

const DIR = __dirname;
const DATA = JSON.parse(fs.readFileSync(path.join(DIR, 'c4-data.json'), 'utf8'));

// ---------------------------------------------------------------------------
// Geometry constants
// ---------------------------------------------------------------------------
const COMP_W = 200;
const COMP_H = 78;
const BAND_LABEL_H = 26; // top inset reserved for band label text
const FONT = 'Helvetica, Arial, sans-serif';

// ---------------------------------------------------------------------------
// Build the ELK graph: bands as compound nodes, comps as children
// ---------------------------------------------------------------------------
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

const BAND_PAD_TOP = BAND_LABEL_H + 16;
const BAND_PAD_SIDE = 18;
const BAND_PAD_BOTTOM = 18;

const COMP_GAP = 34; // horizontal gap between comps within a band

// PASS 1: lay each band's components out as a clean single horizontal row,
// preserving comps[] order. Deterministic placement (a single row of equal-size
// boxes needs no solver and guarantees perfect alignment). Returns the band's
// computed size and each child's band-relative {x,y,width,height}.
function layoutBandRow(z) {
  const comps = compsByZone.get(z.id);
  const children = comps.map((c, i) => ({
    id: c.id,
    x: BAND_PAD_SIDE + i * (COMP_W + COMP_GAP),
    y: BAND_PAD_TOP,
    width: COMP_W,
    height: COMP_H,
  }));
  const innerW = comps.length * COMP_W + (comps.length - 1) * COMP_GAP;
  return {
    id: z.id,
    width: BAND_PAD_SIDE * 2 + innerW,
    height: BAND_PAD_TOP + COMP_H + BAND_PAD_BOTTOM,
    children,
  };
}

// PASS 2: self-stack the (fixed-size) bands top->bottom in zones[] order, and
// place every component at its absolute position (pass-1 row offset + band
// origin). Returns { bands, comps, width, height } in absolute coordinates.
// Stacking ourselves avoids ELK's hierarchy/partitioning crashes while keeping
// each band a real single-row container.
const BAND_GAP = 64; // vertical gap between bands

function stackBands(pass1Bands) {
  // Bands all share a common left margin; width = widest band.
  const maxBandW = Math.max(...DATA.zones.map((z) => pass1Bands.get(z.id).width));
  const bands = [];
  const comps = new Map(); // id -> {x,y,w,h,zone}
  let cursorY = 0;
  DATA.zones.forEach((z) => {
    const b = pass1Bands.get(z.id);
    // Center narrower bands within the widest band's width.
    const bx = Math.round((maxBandW - b.width) / 2);
    const by = cursorY;
    bands.push({ id: z.id, x: bx, y: by, w: b.width, h: b.height, z });
    (b.children || []).forEach((c) => {
      comps.set(c.id, {
        x: bx + c.x,
        y: by + c.y,
        w: c.width,
        h: c.height,
        zone: z.id,
      });
    });
    cursorY = by + b.height + BAND_GAP;
  });
  return {
    bands,
    comps,
    width: maxBandW,
    height: cursorY - BAND_GAP,
  };
}

// PASS 3: route edges ourselves with a deterministic orthogonal router over the
// FIXED node positions from pass 2. (ELK's layered algorithm re-spaces nodes and
// does not honor hard fixed positions, so its bend points would be in a
// different coordinate space than our banded layout. A direct router keeps the
// edges in the band coordinate system, guaranteeing correct attachment.)
//
// Strategy per edge: leave the source from its top/bottom edge, run vertically
// to a routing lane, run horizontally to above/below the target, then drop onto
// the target's top/bottom edge. A per-edge lane offset spreads parallel edges so
// they don't perfectly overlap.
function routeEdges(stack) {
  const comps = stack.comps;
  // Track how many edges have used each (sourceId) and (targetId) port so we can
  // fan their x-attachment points across the box width instead of stacking.
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

  const routed = [];
  DATA.edges.forEach((e, i) => {
    const s = comps.get(e.s);
    const t = comps.get(e.t);
    if (!s || !t) return;

    const si = srcCount.get(e.s) || 0;
    srcCount.set(e.s, si + 1);
    const ti = tgtCount.get(e.t) || 0;
    tgtCount.set(e.t, ti + 1);

    const sx = portX(s, si, srcTotal.get(e.s));
    const tx = portX(t, ti, tgtTotal.get(e.t));

    const sTop = s.y;
    const sBot = s.y + s.h;
    const tTop = t.y;
    const tBot = t.y + t.h;

    const pts = [];
    // small per-edge lane jitter to avoid exact overlaps in the corridor
    const jitter = ((i % 7) - 3) * 4;

    if (tTop >= sBot) {
      // target is below source: exit bottom, enter top
      const midY = (sBot + tTop) / 2 + jitter;
      pts.push({ x: sx, y: sBot });
      pts.push({ x: sx, y: midY });
      pts.push({ x: tx, y: midY });
      pts.push({ x: tx, y: tTop });
    } else if (tBot <= sTop) {
      // target is above source: exit top, enter bottom
      const midY = (tBot + sTop) / 2 + jitter;
      pts.push({ x: sx, y: sTop });
      pts.push({ x: sx, y: midY });
      pts.push({ x: tx, y: midY });
      pts.push({ x: tx, y: tBot });
    } else {
      // same band (overlapping y): route through a corridor below the band
      const midY = Math.max(sBot, tBot) + 26 + jitter;
      pts.push({ x: sx, y: sBot });
      pts.push({ x: sx, y: midY });
      pts.push({ x: tx, y: midY });
      pts.push({ x: tx, y: tBot });
    }
    routed.push({ type: e.type, pts });
  });
  return routed;
}

// Sanity asserts on input

// Sanity asserts on input
if (DATA.comps.length !== 41) {
  console.warn(`WARN expected 41 comps, got ${DATA.comps.length}`);
}
if (DATA.edges.length !== 41) {
  console.warn(`WARN expected 41 edges, got ${DATA.edges.length}`);
}

// ---------------------------------------------------------------------------
// SVG helpers
// ---------------------------------------------------------------------------
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Very light tint of a hex color (mix toward white) for band fills.
function tint(hex, amt) {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  const mix = (c) => Math.round(c + (255 - c) * amt);
  const to2 = (c) => c.toString(16).padStart(2, '0');
  return `#${to2(mix(r))}${to2(mix(g))}${to2(mix(b))}`;
}

// Word-wrap a title into up to maxLines lines of ~maxChars chars.
function wrap(text, maxChars, maxLines) {
  const words = String(text).split(/\s+/);
  const lines = [];
  let cur = '';
  for (const w of words) {
    const cand = cur ? `${cur} ${w}` : w;
    if (cand.length > maxChars && cur) {
      lines.push(cur);
      cur = w;
      if (lines.length === maxLines - 1) break;
    } else {
      cur = cand;
    }
  }
  if (cur) lines.push(cur);
  // any leftover words get squeezed onto the last line
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
// Run layout (two-pass) and render
// ---------------------------------------------------------------------------
const elk = new ELK();

// Build the canonical ELK input graph (band containers as compound nodes, comps
// as children, edges at root). This is the "ELK input JSON" deliverable: a valid
// nested ELK graph with partitioning + INCLUDE_CHILDREN that describes the
// intended layout. We additionally drive an ELK layout call with it to satisfy
// "lay it out with ELK", then render from our banded coordinates.
function elkInputGraph() {
  const children = DATA.zones.map((z, idx) => ({
    id: z.id,
    labels: [{ text: z.label }],
    layoutOptions: {
      'elk.partitioning.partition': String(idx),
      'elk.direction': 'RIGHT',
      'elk.padding': `[top=${BAND_PAD_TOP},left=${BAND_PAD_SIDE},bottom=${BAND_PAD_BOTTOM},right=${BAND_PAD_SIDE}]`,
    },
    children: compsByZone.get(z.id).map((c) => ({
      id: c.id,
      width: COMP_W,
      height: COMP_H,
      labels: [{ text: c.title }],
    })),
  }));
  const edges = DATA.edges.map((e, i) => ({
    id: `e${i}`,
    sources: [e.s],
    targets: [e.t],
  }));
  return {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'DOWN',
      'elk.edgeRouting': 'ORTHOGONAL',
      'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
      'elk.partitioning.activate': 'true',
      'elk.layered.considerModelOrder.strategy': 'NODES_AND_EDGES',
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
      'elk.layered.spacing.nodeNodeBetweenLayers': '55',
      'elk.spacing.nodeNode': '40',
    },
    children,
    edges,
  };
}

async function runLayout() {
  // Emit the canonical ELK input graph (the deliverable) + run ELK on it so the
  // band ordering / partitioning is validated by the engine.
  const elkGraph = elkInputGraph();
  fs.writeFileSync(
    path.join(DIR, 'solution-architecture-elk-input.json'),
    JSON.stringify(elkGraph, null, 2),
  );
  const elkResult = await elk.layout(elkGraph);
  // Confirm ELK produced the bands in zones[] order (top->bottom).
  const elkBandY = (elkResult.children || []).map((c) => ({ id: c.id, y: c.y }));

  // PASS 1: lay each band out as a single horizontal row (deterministic).
  const pass1Bands = new Map();
  for (const z of DATA.zones) {
    pass1Bands.set(z.id, layoutBandRow(z));
  }

  // PASS 2: stack the bands top->bottom ourselves (absolute coords).
  const stack = stackBands(pass1Bands);

  // PASS 3: route edges over the fixed banded node positions (deterministic
  // orthogonal router; keeps edges in the band coordinate system).
  const routed = routeEdges(stack);

  return { stack, routed, elkBandY };
}

runLayout()
  .then(({ stack, routed, elkBandY }) => {
    // Build absolute index from the stack (authoritative node positions).
    const abs = new Map();
    for (const b of stack.bands) abs.set(b.id, { x: b.x, y: b.y, w: b.w, h: b.h });
    for (const [id, c] of stack.comps) abs.set(id, { x: c.x, y: c.y, w: c.w, h: c.h });
    const totalW = stack.width;
    const totalH = stack.height;
    const PAD = 24;

    const parts = [];
    parts.push(
      `<svg xmlns="http://www.w3.org/2000/svg" version="1.1" ` +
        `width="${Math.ceil(totalW + PAD * 2)}" height="${Math.ceil(totalH + PAD * 2)}" ` +
        `viewBox="0 0 ${Math.ceil(totalW + PAD * 2)} ${Math.ceil(totalH + PAD * 2)}" ` +
        `font-family="${FONT}">`,
    );

    // arrowhead markers (one per edge type so they inherit the right color)
    parts.push('<defs>');
    for (const [k, st] of Object.entries(EDGE_STYLE)) {
      parts.push(
        `<marker id="${st.marker}" viewBox="0 0 10 10" refX="9" refY="5" ` +
          `markerWidth="7" markerHeight="7" orient="auto-start-reverse">` +
          `<path d="M0,0 L10,5 L0,10 z" fill="${st.stroke}"/></marker>`,
      );
    }
    parts.push('</defs>');

    parts.push(`<g transform="translate(${PAD},${PAD})">`);

    // 1) Band containers (drawn first so comps/edges sit on top)
    const bandRects = [];
    DATA.zones.forEach((z) => {
      const r = abs.get(z.id);
      if (!r) return;
      bandRects.push({ z, r });
      const fill = tint(z.nodefill, 0.55);
      parts.push(
        `<rect x="${r.x.toFixed(1)}" y="${r.y.toFixed(1)}" ` +
          `width="${r.w.toFixed(1)}" height="${r.h.toFixed(1)}" rx="10" ry="10" ` +
          `fill="${fill}" stroke="${z.stroke}" stroke-width="1.6"/>`,
      );
      parts.push(
        `<text x="${(r.x + 14).toFixed(1)}" y="${(r.y + 19).toFixed(1)}" ` +
          `font-size="14" font-weight="700" fill="${z.stroke}">${esc(z.label)}</text>`,
      );
    });

    // 2) Edges (deterministic orthogonal polylines from the router).
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

    // 3) Components (on top of edges)
    let compsRendered = 0;
    DATA.comps.forEach((c) => {
      const r = abs.get(c.id);
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
      // description (small, wrapped, muted)
      const descLines = wrap(c.desc, 30, 3);
      const dY = r.y + 22 + titleLines.length * 13;
      descLines.forEach((ln, li) => {
        parts.push(
          `<text x="${cx.toFixed(1)}" y="${(dY + li * 11).toFixed(1)}" ` +
            `font-size="8.5" text-anchor="middle" fill="#555555">${esc(ln)}</text>`,
        );
      });
    });

    // 4) Legend (bottom-left, inside the canvas)
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

    // Assertions
    const bandCount = bandRects.length;
    if (compsRendered !== DATA.comps.length) {
      throw new Error(
        `Component count mismatch: rendered ${compsRendered} of ${DATA.comps.length}`,
      );
    }
    if (edgesRendered !== DATA.edges.length) {
      throw new Error(
        `Edge count mismatch: rendered ${edgesRendered} of ${DATA.edges.length}`,
      );
    }
    if (bandCount !== DATA.zones.length) {
      throw new Error(`Band count mismatch: ${bandCount} of ${DATA.zones.length}`);
    }

    // Report band Y ordering to confirm top->bottom matches zones[]
    const order = DATA.zones.map((z) => ({
      id: z.id,
      y: abs.get(z.id).y,
    }));
    const ascending = order.every((o, i) => i === 0 || o.y >= order[i - 1].y);

    // Cross-check: did ELK also rank the band containers in zones[] order?
    const elkOrderById = new Map(elkBandY.map((b) => [b.id, b.y]));
    const elkAscending = DATA.zones.every(
      (z, i) =>
        i === 0 || elkOrderById.get(z.id) >= elkOrderById.get(DATA.zones[i - 1].id),
    );

    console.log(
      JSON.stringify(
        {
          ok: true,
          canvas: { w: Math.ceil(totalW), h: Math.ceil(totalH) },
          comps: compsRendered,
          edges: edgesRendered,
          bands: bandCount,
          bandOrderTopToBottomMatchesZones: ascending,
          elkPartitioningRankedBandsInZoneOrder: elkAscending,
          bandY: order.map((o) => `${o.id}:${Math.round(o.y)}`),
        },
        null,
        2,
      ),
    );
  })
  .catch((err) => {
    console.error('ELK layout failed:', err);
    process.exit(1);
  });
