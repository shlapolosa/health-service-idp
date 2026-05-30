#!/usr/bin/env python3
"""Architect agent — thin CLI wrapper around the Capability MCP tools (P8.1 form).

Replaces the prior monolithic architect.py (lost to `git reset --hard` in an earlier session).
The orchestration is now reified as MCP tools served by capability-mcp-server; this script is the
non-interactive entry point a human or CI can use to drive them end-to-end.

Flow (mirrors the planned Foundry agent's reasoning shape — UNDERSTAND → SCORE → BRANCH →
PATTERN MATCH → SYNTHESISE → VALIDATE → PROPOSE):

  1. Read CapabilityRequest YAML (arg).
  2. Mint Entra client-credentials token (SP_CLIENT_ID/SP_CLIENT_SECRET/ENTRA_TENANT/APIM_AUDIENCE).
  3. catalog.search(request)              → ranked candidates (deterministic scorer).
  4. kb.diff(top.technology)              → gap signal.
  5. Branch on gap_kind:
        none        → AOAI: write ADR; PR with ADR only.
        needs_oam   → examples.pattern_for(kind, requires_cluster_permissions) → AOAI synth CD +
                      KB promotion + ADR → oam.dry_run + crossplane.dry_run → PR with 3 files.
        drift       → same as needs_oam (KB row present but maturity ≠ published).
        oam_orphan  → warn + exit (P8.5 will backfill KB rows; out of scope here).
        unknown     → warn + exit (P8.4 DISCOVER will research; out of scope here).
  6. PR via GitHub Contents API + PAT (factory.propose MCP tool replaces this in P8.2).

Env (all required unless noted):
  MCP_BASE_URL              — e.g. https://aigw-apim-dev-...azure-api.net/mcp/catalog (prod)
                              or http://localhost:8080 (local dev — no /mcp/catalog suffix needed if
                              the server is bare; check the AKS ingress vs. local boot)
  SP_CLIENT_ID, SP_CLIENT_SECRET, ENTRA_TENANT, APIM_AUDIENCE — Entra client-credentials for MCP
  AOAI_BASE_URL             — e.g. https://aigw-apim-dev-...azure-api.net/openai  (APIM-fronted)
  AOAI_DEPLOYMENT           — defaults to gpt-5.4
  PERSONAL_ACCESS_TOKEN     — GitHub PAT with contents:write + pull_requests:write on the repo
  GITHUB_OWNER, GITHUB_REPO — defaults: shlapolosa, health-service-idp
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import requests
import yaml

# ---------- config ----------

MCP_BASE_URL = os.environ.get("MCP_BASE_URL", "http://localhost:8080")
AOAI_BASE_URL = os.environ.get("AOAI_BASE_URL", "")
AOAI_DEPLOYMENT = os.environ.get("AOAI_DEPLOYMENT", "gpt-5.4")
AOAI_API_VERSION = os.environ.get("AOAI_API_VERSION", "2024-10-21")
GH_OWNER = os.environ.get("GITHUB_OWNER", "shlapolosa")
GH_REPO = os.environ.get("GITHUB_REPO", "health-service-idp")
GH_TOKEN = os.environ.get("PERSONAL_ACCESS_TOKEN", "")


# ---------- Entra ----------

def mint_token() -> str:
    """Client-credentials token for both the catalog MCP and the APIM-fronted AOAI."""
    tenant = os.environ["ENTRA_TENANT"]
    body = {
        "client_id": os.environ["SP_CLIENT_ID"],
        "client_secret": os.environ["SP_CLIENT_SECRET"],
        "scope": f"{os.environ['APIM_AUDIENCE']}/.default",
        "grant_type": "client_credentials",
    }
    r = requests.post(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                      data=body, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


# ---------- MCP RPC ----------

def mcp_call(token: str, tool: str, args: dict[str, Any]) -> Any:
    """One-shot Streamable-HTTP tools/call. The catalog MCP is stateless so no session needed."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/call",
        "params": {"name": tool, "arguments": args},
    }
    url = f"{MCP_BASE_URL.rstrip('/')}/mcp"
    r = requests.post(url, json=payload, timeout=60, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    r.raise_for_status()
    # FastMCP Streamable-HTTP returns either JSON or text/event-stream; handle both.
    txt = r.text
    if txt.lstrip().startswith("event:"):
        # Pull the JSON out of the data: line.
        for line in txt.splitlines():
            if line.startswith("data: "):
                txt = line[len("data: "):]
                break
    body = json.loads(txt)
    if "error" in body:
        raise RuntimeError(f"MCP tool {tool} error: {body['error']}")
    result = body.get("result", {})
    # FastMCP wraps tool returns in {content: [{type, text, ...}]}.
    content = result.get("content", [])
    if content and content[0].get("type") == "text":
        try:
            return json.loads(content[0]["text"])
        except json.JSONDecodeError:
            return content[0]["text"]
    return result


# ---------- AOAI ----------

def aoai_chat(token: str, system: str, user: str, max_tokens: int = 2000) -> str:
    """Call APIM-fronted AOAI gpt-5.4. gpt-5.* requires max_completion_tokens, not max_tokens."""
    if not AOAI_BASE_URL:
        raise RuntimeError("AOAI_BASE_URL not set; cannot synthesise content")
    url = f"{AOAI_BASE_URL.rstrip('/')}/deployments/{AOAI_DEPLOYMENT}/chat/completions" \
          f"?api-version={AOAI_API_VERSION}"
    for key in ("max_completion_tokens", "max_tokens"):  # fallback for older deployments
        body = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            key: max_tokens,
        }
        r = requests.post(url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }, json=body, timeout=120)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        if "max_completion_tokens" not in r.text and "max_tokens" not in r.text:
            r.raise_for_status()
    raise RuntimeError(f"aoai_chat failed: {r.status_code} {r.text[:300]}")


# ---------- synthesis prompts ----------

_ADR_SYS = (
    "You are the platform architect. Write a concise ADR (Architecture Decision Record) for the "
    "chosen capability. Output Markdown only, no preamble. Sections: Status, Context, Decision, "
    "Consequences. Keep under 350 words."
)

_CD_SYS = (
    "You are the platform architect. Render a KubeVela ComponentDefinition YAML for the requested "
    "technology, mirroring the structure of the provided exemplar file(s). Output ONLY the YAML — "
    "no fences, no preamble. Replace identifiers + chart coordinates as needed; keep CUE structure, "
    "workload kind, and parameter shape consistent with the exemplar. If the KB entry declares "
    "requires_cluster_permissions=true, ALSO append (separated by `---`) a ClusterRoleBinding that "
    "grants the provider-helm ServiceAccount the listed cluster_permissions."
)


def synth_adr(token: str, request: dict[str, Any], chosen: dict[str, Any],
              diff: dict[str, Any]) -> str:
    user = (f"Capability request:\n{yaml.safe_dump(request, sort_keys=False)}\n\n"
            f"Chosen technology (top of scored list):\n{yaml.safe_dump(chosen, sort_keys=False)}\n\n"
            f"KB-vs-cluster diff:\n{yaml.safe_dump(diff, sort_keys=False)}")
    return aoai_chat(token, _ADR_SYS, user, max_tokens=900)


def synth_componentdefinition(token: str, kb_entry: dict[str, Any],
                              exemplar_files: dict[str, str]) -> str:
    exemplar_block = "\n\n".join(f"# --- exemplar: {p} ---\n{c}" for p, c in exemplar_files.items())
    user = (f"KB entry to implement:\n{yaml.safe_dump(kb_entry, sort_keys=False)}\n\n"
            f"Exemplar file(s) to mirror:\n{exemplar_block}")
    return aoai_chat(token, _CD_SYS, user, max_tokens=3000)


# ---------- GitHub PR ----------

def _gh_headers() -> dict[str, str]:
    return {"Authorization": f"token {GH_TOKEN}",
            "Accept": "application/vnd.github+json", "User-Agent": "capability-architect"}


def _gh_default_branch_sha() -> str:
    r = requests.get(f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/git/ref/heads/main",
                     headers=_gh_headers(), timeout=30)
    r.raise_for_status()
    return r.json()["object"]["sha"]


def open_pr(branch: str, title: str, body: str, files: dict[str, str]) -> str:
    """Create a branch, commit `files` (path → content), open a PR. Returns PR URL."""
    if not GH_TOKEN:
        raise RuntimeError("PERSONAL_ACCESS_TOKEN not set; cannot open PR")
    base_sha = _gh_default_branch_sha()
    # Create branch ref.
    requests.post(f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/git/refs",
                  headers=_gh_headers(),
                  json={"ref": f"refs/heads/{branch}", "sha": base_sha}, timeout=30).raise_for_status()
    # Commit each file via Contents API (idempotent — fetches sha if it exists).
    import base64
    for path, content in files.items():
        url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{path}"
        existing = requests.get(url, headers=_gh_headers(),
                                params={"ref": branch}, timeout=30)
        sha = existing.json().get("sha") if existing.status_code == 200 else None
        body_put = {
            "message": f"architect: {path}",
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if sha:
            body_put["sha"] = sha
        r = requests.put(url, headers=_gh_headers(), json=body_put, timeout=30)
        r.raise_for_status()
    # Open PR.
    r = requests.post(f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/pulls",
                      headers=_gh_headers(),
                      json={"title": title, "body": body, "head": branch, "base": "main"},
                      timeout=30)
    r.raise_for_status()
    return r.json()["html_url"]


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Architect agent (P8.1 CLI form)")
    ap.add_argument("request", help="Path to CapabilityRequest YAML")
    ap.add_argument("--dry-run", action="store_true",
                    help="Don't open a PR; print the synthesised bundle to stdout")
    args = ap.parse_args()

    req_path = Path(args.request)
    request = yaml.safe_load(req_path.read_text())
    req_id = request.get("id") or req_path.stem  # used in branch + ADR names

    print(f"[architect] req={req_id}  mcp={MCP_BASE_URL}", file=sys.stderr)
    token = mint_token()

    # Phase 2: SCORE
    ranked = mcp_call(token, "catalog.search", {
        "category": request.get("category", ""),
        "qualityAttributes": request.get("qualityAttributes", {}),
        "weights": request.get("weights", {}),
    })
    passed = [c for c in ranked if c.get("passed_hard")]
    if not passed:
        print(f"[architect] no candidate passed hard filters. P8.4 DISCOVER not implemented.",
              file=sys.stderr)
        print(json.dumps({"ranked": ranked}, indent=2))
        sys.exit(1)
    top = passed[0]
    tech = top["technology"]
    print(f"[architect] top={tech} score={top.get('score')}", file=sys.stderr)

    # Phase 3: BRANCH on KB diff
    diff = mcp_call(token, "kb.diff", {"tech": tech})
    gap_kind = diff.get("gap_kind")
    print(f"[architect] gap_kind={gap_kind}", file=sys.stderr)

    kb_entry = mcp_call(token, "kb.read", {"tech": tech}) or {}

    files: dict[str, str] = {}
    branch = f"architect/{req_id}-{int(time.time())}"
    adr_path = f"docs/adr/{req_id}-{tech}.md"

    if gap_kind == "none":
        adr = synth_adr(token, request, top, diff)
        files[adr_path] = adr
        title = f"ADR: {req_id} → {tech} (existing OAM)"
    elif gap_kind in ("needs_oam", "drift"):
        # Phase 4: PATTERN MATCH (deterministic via MCP)
        prov = kb_entry.get("provisioning", {}) or {}
        bundle = mcp_call(token, "examples.pattern_for", {
            "kind": prov.get("kind", "helm-chart"),
            "requires_cluster_permissions": bool(prov.get("requires_cluster_permissions", False)),
        })
        pattern = bundle["pattern"]
        exemplars = bundle["files"]
        print(f"[architect] pattern={pattern} exemplars={list(exemplars)}", file=sys.stderr)

        # Phase 5: SYNTHESISE
        cd_yaml = synth_componentdefinition(token, kb_entry, exemplars)

        # Phase 6: VALIDATE (server-side; loop budget kept tiny in P8.1 — fail loudly on retry exhaustion)
        validation = mcp_call(token, "crossplane.dry_run", {"yaml_text": cd_yaml})
        if not validation.get("ok"):
            print(f"[architect] crossplane.dry_run FAILED:\n{validation.get('diagnostics')}",
                  file=sys.stderr)
            # P8.1: no retry loop yet. The user reviews diagnostics and re-runs.
            sys.exit(2)

        # KB promotion: kb → published.
        kb_promoted = dict(kb_entry)
        kb_promoted["maturity"] = "published"
        kb_yaml = yaml.safe_dump(kb_promoted, sort_keys=False)

        adr = synth_adr(token, request, top, diff)

        files = {
            f"crossplane/oam/{tech}-componentdefinition.yaml": cd_yaml,
            f"capability-factory/kb/{tech}.yaml": kb_yaml,
            adr_path: adr,
        }
        title = f"feat({tech}): introduce ComponentDefinition + promote KB to published"
    elif gap_kind == "oam_orphan":
        print(f"[architect] {tech}: OAM exists but no KB ledger row. "
              f"Backfill KB manually or wait for P8.5.", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"[architect] gap_kind={gap_kind}: nothing to do here in P8.1.", file=sys.stderr)
        sys.exit(0)

    if args.dry_run:
        print("=== DRY RUN — bundle ===")
        for p, c in files.items():
            print(f"\n# === {p} ===\n{c}")
        return

    body = (f"Auto-generated by `scripts/architect.py` from `{req_path}`.\n\n"
            f"- Top candidate: **{tech}** (score `{top.get('score')}`)\n"
            f"- Gap: `{gap_kind}`\n"
            f"- Pattern: see exemplar files referenced in the synthesised CD\n")
    url = open_pr(branch, title, body, files)
    print(f"[architect] PR opened: {url}")


if __name__ == "__main__":
    main()
