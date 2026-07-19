#!/usr/bin/env node
/* eslint-disable no-console */
'use strict';

/*
 * gen_elk_c4_v2.js
 * Banded, top-down C4 "solution architecture" renderer.
 *
 * APPROACH A: ONE single `await elk.layout(rootGraph)` over the whole compound
 * graph. Root -> 10 band container nodes -> each band contains its component
 * nodes. ELK (layered, DOWN, ORTHOGONAL, INCLUDE_CHILDREN) computes node
 * positions AND edge routing (with crossing minimization). We then render the
 * SVG from ELK's computed coords + edge bendPoints.
 *
 * Band order is pinned with partitioning (partition = index in zones[]).
 * SVG styling (band rects, colors, component cards, legend, markers) is kept
 * IDENTICAL to gen_elk_c4.js.
 */

const fs = require('fs');
const path = require('path');
const ELK = require('elkjs/lib/elk.bundled.js');

const DIR = __dirname;
const DATA = JSON.parse(fs.readFileSync(path.join(DIR, 'c4-data.json'), 'utf8'));

// ---------------------------------------------------------------------------
// Geometry constants (kept identical to the prior renderer)
// ---------------------------------------------------------------------------
const COMP_W = 200;
const COMP_H = 78;
const BAND_LABEL_H = 26;
const FONT = 'Helvetica, Arial, sans-serif';

const BAND_PAD_TOP = BAND_LABEL_H + 16;
const BAND_PAD_SIDE = 18;
const BAND_PAD_BOTTOM = 18;

const zoneById = new Map(DATA.zones.map((z) => [z.id, z]));
const compById = new Map(DATA.comps.map((c) => [c.id, c]));

const compsByZone = new Map(DATA.zones.map((z) => [z.id, []]));
for (const c of DATA.comps) {
  if (!compsByZone.has(c.zone)) {
    throw new Error(`Component ${c.id} references unknown zone ${c.zone}`);
  }
  compsByZone.get(c.zone).push(c);
}

// ---------------------------------------------------------------------------
// Build the ELK compound graph (Approach A)
// ---------------------------------------------------------------------------
function buildGraph() {
  // Force EVERY band container to the same (widest) full width so partitioning
  // stacks them aligned top->bottom instead of letting sparse bands drift sideways.
  const SP = 34;
  let uniformW = 0;
  for (const z of DATA.zones) {
    const n = compsByZone.get(z.id).length;
    const w = n * COMP_W + (n - 1) * SP + 2 * BAND_PAD_SIDE;
    if (w > uniformW) uniformW = w;
  }
  uniformW = Math.ceil(uniformW) + 40;

  const children = DATA.zones.map((z, idx) => ({
    id: z.id,
    labels: [{ text: z.label }],
    layoutOptions: {
      // pin band order top->bottom
      'elk.partitioning.partition': String(idx),
      // children flow left-to-right inside the band
      'elk.direction': 'RIGHT',
      'elk.padding': `[top=${BAND_PAD_TOP},left=${BAND_PAD_SIDE},bottom=${BAND_PAD_BOTTOM},right=${BAND_PAD_SIDE}]`,
      // equal full width for every band => partitioning stacks them aligned, no sprawl
      'elk.nodeSize.constraints': '[MINIMUM_SIZE]',
      'elk.nodeSize.minimum': `${uniformW},${COMP_H + BAND_PAD_TOP + BAND_PAD_BOTTOM}`,
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
      'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
      'elk.layered.nodePlacement.strategy': 'BRANDES_KOEPF',
      'elk.layered.considerModelOrder.strategy': 'NODES_AND_EDGES',
      'elk.spacing.nodeNode': '34',
      'elk.layered.spacing.nodeNodeBetweenLayers': '60',
      'elk.spacing.edgeNode': '18',
      'elk.spacing.edgeEdge': '12',
    },
    children,
    edges,
  };
}

// ---------------------------------------------------------------------------
// Absolute-coordinate helpers. ELK returns child coords relative to parent.
// ---------------------------------------------------------------------------
function indexAbsolute(root) {
  // map id -> {x,y,w,h} in absolute (root) coords for bands + comps
  const abs = new Map();
  const bandAbs = new Map();
  (root.children || []).forEach((band) => {
    const bx = band.x || 0;
    const by = band.y || 0;
    bandAbs.set(band.id, { x: bx, y: by, w: band.width, h: band.height });
    (band.children || []).forEach((c) => {
      abs.set(c.id, {
        x: bx + (c.x || 0),
        y: by + (c.y || 0),
        w: c.width,
        h: c.height,
        bandX: bx,
        bandY: by,
      });
    });
  });
  return { abs, bandAbs };
}

// Collect edge sections from anywhere in the hierarchy (ELK with
// INCLUDE_CHILDREN may attach edges at root or inside band containers).
// Each section's coords are relative to the edge's CONTAINER node, so we must
// add the container's absolute origin.
function collectEdges(root, bandAbs) {
  const out = [];
  function walk(node, originX, originY) {
    (node.edges || []).forEach((e) => {
      (e.sections || []).forEach((sec) => {
        const pts = [];
        pts.push({ x: originX + sec.startPoint.x, y: originY + sec.startPoint.y });
        (sec.bendPoints || []).forEach((bp) =>
          pts.push({ x: originX + bp.x, y: originY + bp.y }),
        );
        pts.push({ x: originX + sec.endPoint.x, y: originY + sec.endPoint.y });
        out.push({ id: e.id, pts });
      });
    });
    (node.children || []).forEach((ch) => {
      // container child origin is parent origin + child x/y
      walk(ch, originX + (ch.x || 0), originY + (ch.y || 0));
    });
  }
  walk(root, 0, 0);
  return out;
}

// crossing count over a set of polylines (segment-segment intersection test).
function countCrossings(edges) {
  const segs = [];
  for (const e of edges) {
    for (let i = 0; i + 1 < e.pts.length; i++) {
      segs.push([e.pts[i], e.pts[i + 1], e.id]);
    }
  }
  function ccw(a, b, c) {
    return (c.y - a.y) * (b.x - a.x) - (b.y - a.y) * (c.x - a.x);
  }
  function intersect(a, b, c, d) {
    const d1 = ccw(c, d, a);
    const d2 = ccw(c, d, b);
    const d3 = ccw(a, b, c);
    const d4 = ccw(a, b, d);
    return (
      ((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) &&
      ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))
    );
  }
  let n = 0;
  for (let i = 0; i < segs.length; i++) {
    for (let j = i + 1; j < segs.length; j++) {
      if (segs[i][2] === segs[j][2]) continue; // same edge
      if (intersect(segs[i][0], segs[i][1], segs[j][0], segs[j][1])) n++;
    }
  }
  return n;
}

// ---------------------------------------------------------------------------
// SVG helpers (identical to prior renderer)
// ---------------------------------------------------------------------------
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
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
      lines.push(cur);
      cur = w;
      if (lines.length === maxLines - 1) break;
    } else {
      cur = cand;
    }
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
// Render
// ---------------------------------------------------------------------------
function render(root) {
  const { abs, bandAbs } = indexAbsolute(root);
  const edgesById = new Map();
  for (const er of collectEdges(root, bandAbs)) edgesById.set(er.id, er.pts);

  // normalize so min x/y = 0 (ELK can produce small negative coords from
  // edge routing margins)
  let minX = Infinity;
  let minY = Infinity;
  for (const [, r] of bandAbs) {
    minX = Math.min(minX, r.x);
    minY = Math.min(minY, r.y);
  }
  for (const [, pts] of edgesById) {
    for (const p of pts) {
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
    }
  }
  const dx = -minX;
  const dy = -minY;
  const shift = (r) => ({ ...r, x: r.x + dx, y: r.y + dy });

  let totalW = 0;
  let totalH = 0;
  for (const [, r] of bandAbs) {
    totalW = Math.max(totalW, r.x + dx + r.w);
    totalH = Math.max(totalH, r.y + dy + r.h);
  }

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

  // 1) Band containers
  const bandRects = [];
  DATA.zones.forEach((z) => {
    const raw = bandAbs.get(z.id);
    if (!raw) return;
    const r = shift(raw);
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

  // 2) Edges from ELK bendpoints
  let edgesRendered = 0;
  const renderedEdgePts = [];
  DATA.edges.forEach((e, i) => {
    const ptsRaw = edgesById.get(`e${i}`);
    if (!ptsRaw || ptsRaw.length < 2) return;
    const pts = ptsRaw.map((p) => ({ x: p.x + dx, y: p.y + dy }));
    renderedEdgePts.push({ id: `e${i}`, pts });
    const st = EDGE_STYLE[e.type] || EDGE_STYLE.sync;
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
    const raw = abs.get(c.id);
    if (!raw) return;
    const r = shift(raw);
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

  return {
    svg: parts.join('\n'),
    compsRendered,
    edgesRendered,
    bandCount: bandRects.length,
    bandRects,
    totalW,
    totalH,
    renderedEdgePts,
  };
}

// ---------------------------------------------------------------------------
// Overlap check (node-node)
// ---------------------------------------------------------------------------
function anyNodeOverlap(root) {
  const { abs } = indexAbsolute(root);
  const boxes = [...abs.entries()].map(([id, r]) => ({ id, r }));
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i].r;
      const b = boxes[j].r;
      const ox = a.x < b.x + b.w && b.x < a.x + a.w;
      const oy = a.y < b.y + b.h && b.y < a.y + a.h;
      if (ox && oy) return `${boxes[i].id} <-> ${boxes[j].id}`;
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
const elk = new ELK();

async function main() {
  if (DATA.comps.length !== 41) console.warn(`WARN expected 41 comps, got ${DATA.comps.length}`);
  if (DATA.edges.length !== 41) console.warn(`WARN expected 41 edges, got ${DATA.edges.length}`);

  const graph = buildGraph();
  fs.writeFileSync(
    path.join(DIR, 'solution-architecture-elk-input.json'),
    JSON.stringify(graph, null, 2),
  );

  let root;
  try {
    root = await elk.layout(graph);
  } catch (err) {
    console.error('ELK_LAYOUT_ERROR:', err && err.message ? err.message : String(err));
    throw err;
  }

  // band order check (top->bottom == zones[])
  const { bandAbs } = indexAbsolute(root);
  const order = DATA.zones.map((z) => ({ id: z.id, y: bandAbs.get(z.id).y }));
  const ascending = order.every((o, i) => i === 0 || o.y >= order[i - 1].y);
  if (!ascending) {
    throw new Error(
      'Band order NOT top->bottom in zones[] order: ' +
        order.map((o) => `${o.id}:${Math.round(o.y)}`).join(', '),
    );
  }

  const overlap = anyNodeOverlap(root);
  if (overlap) throw new Error(`Node overlap detected: ${overlap}`);

  const out = render(root);

  if (out.compsRendered !== DATA.comps.length) {
    throw new Error(`Component count mismatch: ${out.compsRendered} of ${DATA.comps.length}`);
  }
  if (out.edgesRendered !== DATA.edges.length) {
    throw new Error(`Edge count mismatch: ${out.edgesRendered} of ${DATA.edges.length}`);
  }
  if (out.bandCount !== DATA.zones.length) {
    throw new Error(`Band count mismatch: ${out.bandCount} of ${DATA.zones.length}`);
  }

  fs.writeFileSync(path.join(DIR, 'solution-architecture-elk.svg'), out.svg);

  const crossings = countCrossings(out.renderedEdgePts);

  console.log(
    JSON.stringify(
      {
        ok: true,
        approach: 'A (single elk.layout over compound graph)',
        canvas: { w: Math.ceil(out.totalW), h: Math.ceil(out.totalH) },
        comps: out.compsRendered,
        edges: out.edgesRendered,
        bands: out.bandCount,
        bandOrderTopToBottomMatchesZones: ascending,
        nodeOverlap: overlap || 'none',
        edgeCrossings: crossings,
        bandY: order.map((o) => `${o.id}:${Math.round(o.y)}`),
      },
      null,
      2,
    ),
  );
}

main().catch((err) => {
  console.error('FAILED:', err && err.message ? err.message : String(err));
  process.exit(1);
});
