#!/usr/bin/env python3
"""Parse + validate the fenced ```acceptance blocks in a REQUIREMENTS.md.

Contract: factory/docs/contracts/requirements-acceptance-block.md

  CLI:  python3 parse_acceptance.py REQUIREMENTS.md [--service <svc>]
          -> prints JSON {service, criteria:[...]} for the matched service (or all)
          exit 0 = valid (or block fully ABSENT = legacy, prints {"absent":true})
          exit 3 = MALFORMED block (hard fail — caller must abort, never silent-fallback)

  LIB:  from parse_acceptance import parse
        res = parse(text, service="wallet-svc")   # raises ValueError on malformed
"""
import json
import re
import sys

_BLOCK = re.compile(r"```acceptance\s*\n(.*?)```", re.DOTALL)
_VALID_KINDS = {"test", "config", "accepted-gap"}


def extract_blocks(text):
    """Return the raw YAML strings of every ```acceptance block (in order)."""
    return [m.group(1) for m in _BLOCK.finditer(text)]


def _validate(block, idx):
    """Validate one parsed block dict; return list of error strings ([] = ok)."""
    errs = []
    if not isinstance(block, dict):
        return [f"block #{idx}: not a mapping"]
    svc = block.get("service")
    if not svc:
        errs.append(f"block #{idx}: missing 'service'")
    criteria = block.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        errs.append(f"block #{idx} ({svc}): 'criteria' must be a non-empty list")
        return errs
    seen = set()
    for c in criteria:
        if not isinstance(c, dict):
            errs.append(f"{svc}: a criterion is not a mapping"); continue
        cid = c.get("id")
        tag = f"{svc}/{cid or '?'}"
        if not cid:
            errs.append(f"{svc}: a criterion is missing 'id'")
        elif cid in seen:
            errs.append(f"{tag}: duplicate id")
        else:
            seen.add(cid)
        if not c.get("statement"):
            errs.append(f"{tag}: missing 'statement'")
        kind = c.get("kind")
        if kind not in _VALID_KINDS:
            errs.append(f"{tag}: kind must be one of {sorted(_VALID_KINDS)} (got {kind!r})")
        if kind == "test":
            for k in ("given", "when", "then"):
                if not c.get(k):
                    errs.append(f"{tag}: kind:test requires '{k}'")
        if kind == "accepted-gap" and not c.get("reason"):
            errs.append(f"{tag}: kind:accepted-gap requires 'reason'")
    return errs


def parse(text, service=None):
    """Parse all acceptance blocks from REQUIREMENTS.md text. Raises ValueError on
    malformed. Returns {'absent':True} if no block, else {'service','criteria'} for
    the matched service (or the single block / merged list when service is None)."""
    import yaml
    raws = extract_blocks(text)
    if not raws:
        return {"absent": True}
    blocks = []
    errors = []
    for i, raw in enumerate(raws):
        try:
            blk = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            errors.append(f"block #{i}: YAML error: {exc}"); continue
        errors += _validate(blk, i)
        if isinstance(blk, dict):
            blocks.append(blk)
    if errors:
        raise ValueError("malformed acceptance block(s):\n  - " + "\n  - ".join(errors))
    if service is not None:
        match = [b for b in blocks if b.get("service") == service]
        if not match:
            return {"absent": True, "service": service}
        return {"service": service, "criteria": match[0]["criteria"]}
    return {"blocks": [{"service": b["service"], "criteria": b["criteria"]} for b in blocks]}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    service = None
    if "--service" in argv:
        i = argv.index("--service"); service = argv[i + 1]; del argv[i:i + 2]
    if not argv:
        sys.stderr.write("usage: parse_acceptance.py REQUIREMENTS.md [--service <svc>]\n")
        return 2
    text = sys.stdin.read() if argv[0] == "-" else open(argv[0]).read()
    try:
        res = parse(text, service=service)
    except ValueError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 3
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
