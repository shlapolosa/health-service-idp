#!/usr/bin/env python3
"""
Golden-thread traceability validator (reusable engine).

Sanity-checks coverage at EACH adjacent transition in the realization chain, in
both directions:

  FORWARD  coverage: every upstream node has >=1 edge to the downstream layer,
                     OR is declared in accepted_gaps  -> else FORWARD BREAK.
  BACKWARD coverage: every downstream node has >=1 edge from the upstream layer
                     (no orphan / unjustified solution element) -> else BACKWARD BREAK.

Two ways to use it (same engine):

  CLI   :  python3 check_traceability.py [model.yaml]   # default: ./traceability.yaml
           python3 check_traceability.py --model -        # read YAML/JSON from stdin
           python3 check_traceability.py model.yaml --json # machine-readable result
           exit 0 = CLEAN, 1 = unexpected break, 2 = bad input.

  LIBRARY (e.g. the architect agent's Code-Interpreter sandbox — deterministic,
          NO cluster, NO file needed):
           from check_traceability import check
           result = check(model_dict)        # model_dict = parsed traceability model
           assert result["ok"]               # the golden-thread sanity gate
           print(result["report"])           # human table

The model shape (dict): {chain:[layer,...], nodes:[{id,layer,label}], edges:[{from,to}],
accepted_gaps:[{id,layer,reason}], invariants:[{id,label,binds:[],obligation}]}.
"""

import json
import os
import sys


def check(model):
    """Pure function: validate a traceability model dict. Returns a result dict
    with ok/transitions/unexpected/integrity (+ a rendered text report). No I/O."""
    chain = model["chain"]
    nodes = model["nodes"]
    edges = model["edges"]
    accepted = model.get("accepted_gaps", []) or []
    invariants = model.get("invariants", []) or []

    by_layer = {layer: [] for layer in chain}
    id_layer, id_label = {}, {}
    for n in nodes:
        by_layer.setdefault(n["layer"], []).append(n["id"])
        id_layer[n["id"]] = n["layer"]
        id_label[n["id"]] = n.get("label", n["id"])
    accepted_ids = {g["id"] for g in accepted}

    out_edges, in_edges = {}, {}
    for e in edges:
        out_edges.setdefault(e["from"], set()).add(e["to"])
        in_edges.setdefault(e["to"], set()).add(e["from"])

    # referential integrity + adjacency
    integrity = []
    for e in edges:
        for endpoint in (e["from"], e["to"]):
            if endpoint not in id_layer:
                integrity.append(f"edge references unknown node id '{endpoint}' ({e})")
    adj = {chain[i]: chain[i + 1] for i in range(len(chain) - 1)}
    for e in edges:
        lf, lt = id_layer.get(e["from"]), id_layer.get(e["to"])
        if lf in adj and adj[lf] != lt:
            integrity.append(
                f"non-adjacent edge {e['from']}({lf}) -> {e['to']}({lt}); expected {lf}->{adj[lf]}"
            )

    transitions, unexpected = [], []
    for i in range(len(chain) - 1):
        up, down = chain[i], chain[i + 1]
        up_ids, down_ids = by_layer.get(up, []), by_layer.get(down, [])
        fwd_orphans = [nid for nid in up_ids
                       if nid not in accepted_ids
                       and not any(id_layer.get(t) == down for t in out_edges.get(nid, set()))]
        bwd_orphans = [nid for nid in down_ids
                       if nid not in accepted_ids
                       and not any(id_layer.get(s) == up for s in in_edges.get(nid, set()))]
        for nid in fwd_orphans:
            unexpected.append({"kind": "FORWARD", "transition": f"{up}->{down}", "node": nid,
                               "note": f"'{id_label[nid]}' has no realization into {down}"})
        for nid in bwd_orphans:
            unexpected.append({"kind": "BACKWARD", "transition": f"{up}->{down}", "node": nid,
                               "note": f"'{id_label[nid]}' is an orphan — nothing in {up} realizes it"})
        transitions.append({"up": up, "down": down, "up_n": len(up_ids), "down_n": len(down_ids),
                            "fwd_orphans": fwd_orphans, "bwd_orphans": bwd_orphans})

    inv_problems = []
    for inv in invariants:
        bad = [b for b in inv.get("binds", []) if b not in id_layer]
        if bad:
            inv_problems.append({"id": inv["id"], "binds": bad})
            integrity.append(f"invariant {inv['id']} binds unknown node(s): {bad}")

    ok = not unexpected and not integrity
    result = {"ok": ok, "transitions": transitions, "unexpected": unexpected,
              "integrity": integrity, "accepted_gaps": accepted, "invariants": invariants}
    result["report"] = render(result)
    return result


def render(result):
    """Human-readable report (the table CLI prints)."""
    L = []
    add = L.append
    bar = "=" * 100
    add(bar); add("GOLDEN-THREAD TRACEABILITY — per-transition coverage"); add(bar)
    header = f"{'transition':<34} {'up N':>5} {'down N':>7} {'fwd-orphans':>12} {'bwd-orphans':>12}"
    add(header); add("-" * len(header))
    for t in result["transitions"]:
        fo = ",".join(t["fwd_orphans"]) if t["fwd_orphans"] else "-"
        bo = ",".join(t["bwd_orphans"]) if t["bwd_orphans"] else "-"
        add(f"{t['up'] + ' -> ' + t['down']:<34} {t['up_n']:>5} {t['down_n']:>7} {fo:>12} {bo:>12}")
    add(""); add(bar); add("ACCEPTED GAPS (declared — expected, never silent)"); add(bar)
    if result["accepted_gaps"]:
        for g in result["accepted_gaps"]:
            add(f"  [{g['id']}] ({g.get('layer','?')}) {g['reason']}")
    else:
        add("  (none)")
    add(""); add(bar); add("INVARIANTS (side-links to components + REQUIREMENTS.md obligation)"); add(bar)
    for inv in result["invariants"]:
        add(f"  [{inv['id']}] {inv['label']}")
        add(f"        binds: {', '.join(inv.get('binds', []))}")
        add(f"        obligation: {inv['obligation']}")
    if result["integrity"]:
        add(""); add(bar); add("MODEL INTEGRITY PROBLEMS"); add(bar)
        for p in result["integrity"]:
            add(f"  !! {p}")
    add(""); add(bar); add("VERDICT"); add(bar)
    if result["ok"]:
        add("  CLEAN — every transition has full forward+backward coverage;")
        add("          the only non-realized elements are the declared accepted_gaps.")
    else:
        add(f"  {len(result['unexpected'])} UNEXPECTED break(s) + "
            f"{len(result['integrity'])} integrity problem(s):")
        for u in result["unexpected"]:
            add(f"   - {u['kind']} BREAK @ {u['transition']}: {u['node']} — {u['note']}")
        for p in result["integrity"]:
            add(f"   - INTEGRITY: {p}")
    return "\n".join(L)


def _load(path):
    """Load a model from a path ('-' = stdin). YAML if available, else JSON."""
    raw = sys.stdin.read() if path == "-" else open(path).read()
    try:
        import yaml
        return yaml.safe_load(raw)
    except ImportError:
        return json.loads(raw)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    path = argv[0] if argv and argv[0] != "--model" else (argv[1] if "--model" in argv else None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "traceability.yaml")
    try:
        model = _load(path)
    except Exception as exc:  # bad input
        sys.stderr.write(f"cannot load model from {path}: {exc}\n")
        return 2
    result = check(model)
    if as_json:
        print(json.dumps({k: v for k, v in result.items() if k != "report"}, indent=1))
    else:
        print(result["report"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
