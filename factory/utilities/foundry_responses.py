#!/usr/bin/env python3
"""Drive a Foundry Agent via the actual GA contract: /agents + /openai/v1/responses.

Background — we previously used the legacy `/assistants` + `/threads/{id}/runs` path (OpenAI
Assistants-compat) and every MCP-tool run failed with the generic `server_error / 0 tokens`. The
*correct* Foundry Agent Service contract on Microsoft Foundry projects is two-piece:

  1. /api/projects/{proj}/agents POST                  — create / version the agent definition
  2. /api/projects/{proj}/openai/v1/responses POST     — run, passing agent_reference

This is the actual GA path. Same agent, same project, same model, same MCP tool — but model
invocation only works through the /responses surface. The /assistants path is left for
OpenAI-Assistants protocol compatibility and doesn't fully wire MCP tools.

Empirically proven 2026-05-28 against gitmcp.io on aifoundry-socrates/usecase-architect-poc
(UAE North, S0, gpt-5.4): status=completed, 532+22 tokens, tools enumerated, mcp_approval_request
emitted. See agents/architect-v1/README.md for the design + memory/foundry-mcp-uaenorth-blocked.md
for the misdiagnosis trail.

Usage:
  python3 scripts/foundry_responses.py \\
    --endpoint https://aifoundry-socrates.services.ai.azure.com/api/projects/usecase-architect-poc \\
    --agent architect-v1-agents \\
    --message "We need a durable lightweight messaging capability."

If the agent doesn't exist yet, pass --create to define it inline from a YAML manifest
(`agents/<name>/manifest.json`).

Auth: az CLI session (DefaultAzureCredential). For CI, set AZURE_CLIENT_ID/SECRET/TENANT_ID env
vars and run from a runtime that supports them.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests


def get_token() -> str:
    """Acquire a Foundry data-plane token via az CLI."""
    out = subprocess.check_output(
        ["az", "account", "get-access-token", "--resource", "https://ai.azure.com",
         "--query", "accessToken", "-o", "tsv"],
        text=True,
    )
    return out.strip()


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_agent(endpoint: str, token: str, name: str) -> dict | None:
    r = requests.get(f"{endpoint}/agents/{name}?api-version=v1", headers=headers(token), timeout=30)
    return r.json() if r.status_code == 200 else None


def create_or_update_agent(endpoint: str, token: str, name: str, definition: dict) -> dict:
    """Create the agent if absent, otherwise add a new version. Returns the agent doc."""
    existing = get_agent(endpoint, token, name)
    payload = {"definition": definition}
    if existing is None:
        payload["name"] = name
        r = requests.post(f"{endpoint}/agents?api-version=v1", json=payload, headers=headers(token), timeout=30)
    else:
        r = requests.post(f"{endpoint}/agents/{name}/versions?api-version=v1", json=payload,
                          headers=headers(token), timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"agent upsert failed: {r.status_code} {r.text[:300]}")
    return r.json()


def respond(endpoint: str, token: str, agent_name: str, message: str,
            previous_response_id: str | None = None,
            approval_responses: list[dict] | None = None) -> dict:
    """POST /openai/v1/responses. Returns the (terminal) response object."""
    # Body shape per MS Learn runtime-components docs:
    # - input: string or array of items
    # - agent_reference: {name, type:"agent_reference"}
    # - previous_response_id: thread-stitching (use the previous run's id for multi-turn)
    if approval_responses:
        body_input = approval_responses
    else:
        body_input = [{"type": "message", "role": "user", "content": message}]
    body = {
        "input": body_input,
        "agent_reference": {"name": agent_name, "type": "agent_reference"},
    }
    if previous_response_id:
        body["previous_response_id"] = previous_response_id

    r = requests.post(f"{endpoint}/openai/v1/responses", json=body, headers=headers(token), timeout=60)
    if r.status_code != 200:
        # Surface Foundry's diagnostic so we never go back to guessing
        raise RuntimeError(f"responses POST failed: {r.status_code} {r.text[:500]}")
    resp = r.json()

    # If it returned immediately (synchronous mode), poll until terminal
    status = resp.get("status", "")
    while status in ("queued", "in_progress"):
        time.sleep(2)
        r = requests.get(f"{endpoint}/openai/v1/responses/{resp['id']}", headers=headers(token), timeout=30)
        resp = r.json()
        status = resp.get("status", "")
    return resp


def summarise(resp: dict, verbose: bool = False) -> None:
    print(f"\nresponse_id: {resp.get('id')}")
    print(f"status:      {resp.get('status')}")
    print(f"usage:       {resp.get('usage')}")
    if resp.get("error"):
        print(f"error:       {resp['error']}")
    pending_approvals: list[dict] = []
    for o in resp.get("output", []):
        t = o.get("type", "?")
        if t == "message":
            for c in o.get("content", []):
                if c.get("type") == "output_text":
                    print(f"\n[ASSISTANT]\n{c['text']}\n")
        elif t == "mcp_call":
            print(f"[MCP_CALL] {o.get('server_label')}.{o.get('name')}")
            if verbose:
                print(f"  args:   {(o.get('arguments') or '')[:200]}")
                print(f"  output: {(o.get('output') or '')[:300]}")
        elif t == "mcp_list_tools":
            tools = [tt["name"] for tt in o.get("tools", [])]
            print(f"[MCP_LIST_TOOLS {o.get('server_label')}] {tools}")
        elif t == "mcp_approval_request":
            print(f"[APPROVAL_REQUEST id={o.get('id')}] "
                  f"server={o.get('server_label')} tool={o.get('name')} args={(o.get('arguments') or '')[:120]}")
            pending_approvals.append(o)
    return pending_approvals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True,
                    help="Foundry project endpoint, e.g. https://aifoundry-socrates.services.ai.azure.com/api/projects/usecase-architect-poc")
    ap.add_argument("--agent", required=True, help="Agent name (must already exist unless --create)")
    ap.add_argument("--message", required=True)
    ap.add_argument("--create", default=None,
                    help="Path to a manifest JSON ({definition: {kind,model,instructions,tools}}) to upsert before running")
    ap.add_argument("--auto-approve", action="store_true",
                    help="Auto-approve any mcp_approval_request (use ONLY for fully-trusted tools / smoke tests)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    token = get_token()

    if args.create:
        manifest = json.loads(Path(args.create).read_text())
        defn = manifest.get("definition") or manifest  # tolerate either wrapper or flat
        d = create_or_update_agent(args.endpoint, token, args.agent, defn)
        print(f"[architect] agent {args.agent} upserted -> version {d.get('versions',{}).get('latest',{}).get('id')}")

    resp = respond(args.endpoint, token, args.agent, args.message)
    pending = summarise(resp, verbose=args.verbose)

    # Approval loop — Foundry pauses on mcp_approval_request; we POST another /responses
    # with input=[{type:"mcp_approval_response", approval_request_id, approve}] + previous_response_id.
    while pending:
        if not args.auto_approve:
            ans = input(f"\nApprove {len(pending)} tool call(s)? [y/N]: ").strip().lower()
            if ans != "y":
                print("aborting")
                sys.exit(0)
        approval_input = [
            {"type": "mcp_approval_response",
             "approval_request_id": ap_["id"],
             "approve": True}
            for ap_ in pending
        ]
        resp = respond(args.endpoint, token, args.agent, message="",
                       previous_response_id=resp["id"], approval_responses=approval_input)
        pending = summarise(resp, verbose=args.verbose)


if __name__ == "__main__":
    main()
