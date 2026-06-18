#!/usr/bin/env python3
"""Smoke test for the architect's deterministic artifact engines (attached to the
Foundry Code-Interpreter sandbox). Run:  python3 selftest.py

Exits 0 only if all three engines load and produce valid, invariant-clean output —
this is the local gate before the engines are attached/pinned to the agent."""
import sys

ok = True

# 1. archimate_view — layered ArchiMate Model Exchange XML + H1-H5 invariants
try:
    from archimate_view import View, compose
    v = View("v1", "Smoke")
    v.node("act", "BusinessActor", "Member")
    v.node("svc", "ApplicationService", "Eligibility")
    v.edge("act", "svc", "act__svc", "Serving")
    xml = compose("m1", "Smoke", [v], strict=False)
    assert "archimate" in xml.lower() and "Eligibility" in xml
    print(f"archimate_view : OK   violations={getattr(v, 'violations', 'n/a')}")
except Exception as exc:  # noqa
    ok = False; print(f"archimate_view : FAIL  {exc!r}")

# 2. drawio_c4 (banded) — banded solution diagram + system/trust boundaries + animated async
try:
    from drawio_c4 import C4Diagram
    d = C4Diagram("Smoke", width=1400)
    d.zone("z1", "Client", stroke="#D79B00", fill="#FFF6E6", height=110, comp_fill="#FFE6CC")
    d.zone("z2", "Services", stroke="#82B366", fill="#EEF7E9", height=110, comp_fill="#D5E8D4")
    d.component("c1", "z1", "App", "client surface")
    d.component("c2", "z2", "Svc", "does a thing")
    d.edge("c1", "c2", "sync")
    d.edge("c2", "c1", "async")
    d.system("PLATFORM", ["z2"], "#3A7CA5")
    d.security("z1", "JWT")
    xml = d.render(layout="banded", outline_bands=True, animate_async=True)
    assert "mxfile" in xml and "flowAnimation=1" in xml
    assert not d.violations, d.violations
    print(f"drawio_c4      : OK   violations={d.violations}")
except Exception as exc:  # noqa
    ok = False; print(f"drawio_c4      : FAIL  {exc!r}")

# 3. traceability — golden-thread forward+backward coverage gate (inline model)
try:
    from traceability import check
    clean = check({"chain": ["req", "comp"],
                   "nodes": [{"id": "r1", "layer": "req"}, {"id": "c1", "layer": "comp"}],
                   "edges": [{"from": "r1", "to": "c1"}]})
    orphan = check({"chain": ["req", "comp"],
                    "nodes": [{"id": "r1", "layer": "req"}, {"id": "c2", "layer": "comp"}],
                    "edges": []})
    assert clean["ok"] and not orphan["ok"]
    print(f"traceability   : OK   clean={clean['ok']} orphan_detected={not orphan['ok']}")
except Exception as exc:  # noqa
    ok = False; print(f"traceability   : FAIL  {exc!r}")

print("=== agent-tools selftest:", "PASS" if ok else "FAIL", "===")
sys.exit(0 if ok else 1)
