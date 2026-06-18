#!/usr/bin/env python3
"""Deterministic golden-thread traceability emitter for the dev-agent (NOT model-written).

For a service, map each acceptance criterion -> its test -> the impl file(s) that changed,
and whether the test passed. Emits a human TRACEABILITY.md + a machine traceability.json so
coverage is auditable (the same "no silent drop" discipline as the architect's traceability gate).

  python3 emit_traceability.py REQUIREMENTS.md \
      --service <svc> --junit junit.xml --changed "src/handlers.py,src/x.py" \
      --md microservices/<svc>/TRACEABILITY.md --json microservices/<svc>/.dev-agent/traceability.json
"""
import json
import os
import sys

from parse_acceptance import parse
from check_acceptance import check, load_junit, _nid


def build(requirements_text, service, test_status, changed_files):
    res = parse(requirements_text, service=service)
    if res.get("absent"):
        return None
    criteria = res["criteria"]
    cov = check(criteria, test_status)
    impl = [f for f in changed_files if f and (f"microservices/{service}/" in f or f.startswith("src/"))]
    rows = []
    by_id = {r["id"]: r for r in cov["rows"]}
    for c in criteria:
        cid = c["id"]; nid = _nid(cid); cr = by_id[cid]
        tests = sorted(n for n in test_status if n == f"test_{nid}" or n.startswith(f"test_{nid}_"))
        rows.append({
            "id": cid, "statement": c.get("statement", ""), "invariant": c.get("invariant", "-"),
            "kind": c["kind"], "tests": tests, "impl": impl if c["kind"] == "test" else [],
            "verdict": cr["verdict"], "reason": c.get("reason", ""),
        })
    return {"service": service, "ok": cov["ok"], "rows": rows,
            "accepted_gaps": [r for r in rows if r["kind"] == "accepted-gap"]}


def to_markdown(model):
    L = [f"# TRACEABILITY — {model['service']}", "",
         "Golden thread: every `kind: test` acceptance criterion → a passing test → the impl that changed.",
         f"_Coverage gate: **{'COVERED' if model['ok'] else 'INCOMPLETE'}**_", "",
         "| id | invariant | kind | statement | test(s) | impl | verdict |",
         "|---|---|---|---|---|---|---|"]
    for r in model["rows"]:
        L.append(f"| {r['id']} | {r['invariant']} | {r['kind']} | {r['statement']} | "
                 f"{', '.join(r['tests']) or '—'} | {', '.join(r['impl']) or '—'} | {r['verdict']} |")
    gaps = model["accepted_gaps"]
    if gaps:
        L += ["", "## Accepted gaps (declared — carried elsewhere, never silently dropped)"]
        for g in gaps:
            L.append(f"- **{g['id']}** — {g['statement']} — _{g['reason']}_")
    return "\n".join(L) + "\n"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    opt = {"service": None, "junit": None, "changed": "", "md": None, "json": None}
    for flag in list(opt):
        f = f"--{flag}"
        if f in argv:
            i = argv.index(f); opt[flag] = argv[i + 1]; del argv[i:i + 2]
    if not argv or not opt["service"]:
        sys.stderr.write("usage: emit_traceability.py REQUIREMENTS.md --service <svc> "
                         "[--junit x.xml] [--changed a,b] [--md path] [--json path]\n")
        return 2
    text = open(argv[0]).read()
    test_status = load_junit(opt["junit"]) if opt["junit"] and os.path.exists(opt["junit"]) else {}
    changed = [c.strip() for c in opt["changed"].split(",") if c.strip()]
    model = build(text, opt["service"], test_status, changed)
    if model is None:
        print("no acceptance block for service — nothing to emit (legacy)"); return 0
    md = to_markdown(model)
    if opt["md"]:
        os.makedirs(os.path.dirname(opt["md"]) or ".", exist_ok=True)
        open(opt["md"], "w").write(md)
    if opt["json"]:
        os.makedirs(os.path.dirname(opt["json"]) or ".", exist_ok=True)
        open(opt["json"], "w").write(json.dumps(model, indent=1))
    if not opt["md"] and not opt["json"]:
        print(md)
    return 0 if model["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
