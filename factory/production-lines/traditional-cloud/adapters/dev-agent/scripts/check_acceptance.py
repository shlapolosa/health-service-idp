#!/usr/bin/env python3
"""Acceptance-coverage gate for the dev-agent — mirrors the golden-thread
`traceability.check` discipline at the IMPLEMENTATION step:

  every `kind: test` acceptance criterion MUST have exactly one matching PASSING
  test `test_<id>_*`; `accepted-gap` must be declared (with a reason); nothing is a
  silent drop. Exits non-zero on any uncovered/failing `kind: test` id.

  CLI:  python3 check_acceptance.py REQUIREMENTS.md --service <svc> --junit junit.xml
        python3 check_acceptance.py REQUIREMENTS.md --service <svc> --tests test_ac_1_x,test_ac_2_y
  LIB:  from check_acceptance import check
        result = check(criteria, test_status)   # test_status = {name: 'pass'|'fail'|'skip'}
        assert result["ok"], result["report"]
"""
import json
import sys
import xml.etree.ElementTree as ET


def load_junit(path):
    """pytest --junitxml -> {testname: 'pass'|'fail'|'skip'}."""
    status = {}
    root = ET.parse(path).getroot()
    for tc in root.iter("testcase"):
        name = tc.get("name", "")
        st = "pass"
        for ch in tc:
            if ch.tag in ("failure", "error"):
                st = "fail"
            elif ch.tag == "skipped":
                st = "skip"
        status[name] = "fail" if status.get(name) == "fail" else st
    return status


def _nid(cid):
    return str(cid).replace("-", "_")


def check(criteria, test_status):
    """criteria: list of acceptance criterion dicts. test_status: {name: pass|fail|skip}.
    Returns {ok, rows, uncovered, report}."""
    rows, uncovered = [], []
    for c in criteria:
        cid, kind = c.get("id"), c.get("kind")
        nid = _nid(cid)
        if kind == "test":
            hits = {n: s for n, s in test_status.items()
                    if n == f"test_{nid}" or n.startswith(f"test_{nid}_")}
            passed = [n for n, s in hits.items() if s == "pass"]
            bad = [n for n, s in hits.items() if s != "pass"]
            if passed and not bad:
                verdict, detail = "PASS", ",".join(passed)
            elif not hits:
                verdict, detail = "MISSING", f"no test_{nid}_* found"
                uncovered.append((cid, "no test"))
            else:
                verdict, detail = "FAIL", ",".join(f"{n}:{hits[n]}" for n in bad)
                uncovered.append((cid, "test not passing"))
        elif kind == "accepted-gap":
            verdict, detail = "GAP", c.get("reason", "")
        else:  # config
            verdict, detail = "CONFIG", c.get("statement", "")
        rows.append({"id": cid, "kind": kind, "invariant": c.get("invariant", "-"),
                     "verdict": verdict, "detail": detail})
    ok = not uncovered
    result = {"ok": ok, "rows": rows, "uncovered": uncovered}
    result["report"] = render(result)
    return result


def render(result):
    L = ["=" * 92, "ACCEPTANCE COVERAGE — every kind:test criterion needs a passing test_<id>", "=" * 92,
         f"{'id':<10}{'kind':<14}{'invariant':<10}{'verdict':<9}detail"]
    L.append("-" * 92)
    for r in result["rows"]:
        L.append(f"{str(r['id']):<10}{r['kind']:<14}{str(r['invariant']):<10}{r['verdict']:<9}{r['detail'][:46]}")
    L.append("-" * 92)
    if result["ok"]:
        L.append("VERDICT: COVERED — every kind:test criterion has a passing test; gaps declared.")
    else:
        L.append(f"VERDICT: {len(result['uncovered'])} UNCOVERED kind:test criteria:")
        for cid, why in result["uncovered"]:
            L.append(f"   - {cid}: {why}")
    return "\n".join(L)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    service = junit = tests = None
    for flag, set_ in (("--service", "service"), ("--junit", "junit"), ("--tests", "tests")):
        if flag in argv:
            i = argv.index(flag); val = argv[i + 1]; del argv[i:i + 2]
            locals_ = {"service": None, "junit": None, "tests": None}
            if set_ == "service": service = val
            elif set_ == "junit": junit = val
            else: tests = val
    if not argv:
        sys.stderr.write("usage: check_acceptance.py REQUIREMENTS.md --service <svc> (--junit x.xml | --tests a,b)\n")
        return 2
    from parse_acceptance import parse
    text = open(argv[0]).read()
    res = parse(text, service=service)
    if res.get("absent"):
        print("acceptance block absent — legacy path (no coverage gate)"); return 0
    criteria = res["criteria"]
    if junit:
        test_status = load_junit(junit)
    elif tests:
        test_status = {t.strip(): "pass" for t in tests.split(",") if t.strip()}
    else:
        test_status = {}
    result = check(criteria, test_status)
    print(result["report"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
