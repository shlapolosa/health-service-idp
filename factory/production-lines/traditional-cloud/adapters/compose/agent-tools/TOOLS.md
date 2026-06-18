# Architect agent — deterministic artifact engines (Code-Interpreter tools)

These three pure-Python engines are **attached to the architect-v1 Foundry agent's Code-Interpreter
sandbox**. The **agent determines the components/relationships; the engine deterministically renders the
layout + look-and-feel and self-validates invariants** (the LLM never draws). Same input → byte-identical
output. They need **no cluster** — cluster/state actions (validate an OAM against live CDs, submit) stay
**MCP tools** (`catalog.validate` / `oam.dry_run` / `app.submit_wait`).

Pinned/vendored here (source of truth): `archimate_view.py`, `drawio_c4.py`, `traceability.py`. The
`selftest.py` gate must pass before they are (re)attached to the agent. Re-vendor with `sync.sh` when the
upstream skills change; CI runs `selftest.py`.

## 1. `archimate_view` — layered ArchiMate Model Exchange view
```python
from archimate_view import View, compose
v = View("view-motivation", "Motivation / Strategy")
v.node("g1", "Goal", "Members stay engaged")          # node(id, archimate_type, label)
v.node("r1", "Requirement", "Eligibility < 50ms")
v.edge("r1", "g1", "r1__g1", "Realization")           # edge(src, tgt, id, kind[, access])
xml = compose("model-1", "Wellness", [v], strict=False)   # -> ArchiMate Exchange XML
assert not v.violations                                # H1-H5 layout invariants (must be [])
```
Use one `View` per layer (Motivation/Strategy/Business/Application/Technology). `strict=True` raises on a
violation. Kinds: `Realization, Serving, Triggering, Flow, Access, Assignment, Association, Composition`.

## 2. `drawio_c4` — banded C4 solution architecture (the look we standardized)
```python
from drawio_c4 import C4Diagram
d = C4Diagram("Solution Architecture", width=1820)
d.zone("z_client", "Client", stroke="#D79B00", fill="#FFF6E6", height=118, comp_fill="#FFE6CC")
d.zone("z_engine", "Engine", stroke="#82B366", fill="#EEF7E9", height=244, comp_fill="#D5E8D4")
d.component("bff", "z_client", "BFF", "JWT relay")     # component(id, zone, title, desc)
d.component("svc", "z_engine", "Service", "domain logic")
d.edge("bff", "svc", "sync")                           # edge(src, tgt, kind=sync|async|xtrust|identity)
d.system("PLATFORM", ["z_engine"], "#3A7CA5")          # dotted system boundary over bands
d.trust_boundary("PARTNER TRUST BOUNDARY", "z_engine") # gold strip after a band
d.security("z_client", "UAE Pass · JWT")               # per-band security note
xml = d.render(layout="banded", outline_bands=True, animate_async=True)   # async edges animated
assert not d.violations                                # overlaps / box-crossings / band-rule (must be [])
```
`layout="astar"` keeps the legacy router; `layout="banded"` is the standardized look (barycenter ordering,
channel router, system/trust boundaries, security context, descriptions, `flowAnimation` async).

## 3. `traceability.check` — golden-thread sanity gate (run at EVERY layer transition)
```python
from traceability import check
result = check(model)        # model = {chain:[layers], nodes:[{id,layer,label}], edges:[{from,to}],
                             #          accepted_gaps:[{id,layer,reason}], invariants:[{id,label,binds,obligation}]}
assert result["ok"], result["report"]    # forward+backward coverage; no silent drop/orphan
print(result["report"])                  # human table  (or result["unexpected"] for the breaks)
```
**This is the hard gate.** Build the trace model as you go (goal→outcome→requirement→coa→capability→
process→app_component→sbb→solution_component→oam_component), and `check()` it before proceeding to the OAM.
Every requirement must realize downstream and every component must justify upstream; deferred obligations
go in `accepted_gaps` (with a `reason`) so they are declared, never dropped. Carry each `invariant` into
the service's `REQUIREMENTS.md` acceptance block (the dev-agent turns those into gating tests).

## Discipline
- Engines are **deterministic** — never hand-edit their XML; change the input and re-render.
- `violations == []` and `result["ok"] == True` are **gates**, not advisories — do not proceed on a break.
- These produce *artifacts + sanity checks*; the cluster decisions (validate/submit) remain MCP.
