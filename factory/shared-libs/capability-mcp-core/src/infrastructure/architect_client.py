"""HTTP client for the architect-v1 Foundry agent (W6 front-door — PROPOSE path).

The architect-v1 agent is a Microsoft Foundry "prompt" agent (gpt-5.4) reached
through the GA Foundry Agent Service contract:

    POST {endpoint}/openai/v1/responses?api-version=v1

where `endpoint` is the Foundry project endpoint, e.g.
    https://aifoundry-socrates.services.ai.azure.com/api/projects/usecase-architect-poc

The request body (mirrors factory/utilities/foundry_responses.py::respond):
    {
      "input": [{"type":"message","role":"user","content":"<free text>"}],
      "agent_reference": {"name":"<agent>","type":"agent_reference"}
    }

Auth is a Foundry data-plane bearer token. In-cluster this is supplied as a
pre-minted token (env ARCHITECT_AGENT_TOKEN, refreshed by a sidecar/secret) OR,
when running where az CLI is available, via DefaultAzureCredential. We keep the
client transport-only: the caller (FromRequirementUseCase) supplies the token.

APPROVAL GATE (this is the whole point of the front-door): the architect is told
to PROPOSE — it follows its golden-thread method, validates the OAM via
`oam.dry_run`, then opens a *review* Pull Request via the `factory.propose` MCP
tool (its native write surface) and STOPS. It does NOT call app.submit /
app.submit_wait. A human approves by merging the PR; a merge-triggered workflow
runs the real deploy (app.submit_wait). So the architect's final assistant text
carries the PR URL, which the use case extracts. Nothing here deploys.

This module is ADDITIVE — nothing imports it unless the W6 front-door tool is
invoked, so existing submit/status/delete paths are untouched.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

# The repo the architect opens its review PR against. On the factory.propose
# allow-list (FACTORY_ALLOWED_REPOS = "health-service-idp,health-service-idp-gitops").
DEFAULT_PROPOSE_REPO = "health-service-idp-gitops"


@dataclass
class ArchitectClient:
    """Thin transport client for the architect-v1 Foundry agent /responses surface."""

    endpoint: str                      # Foundry project endpoint (…/api/projects/<proj>)
    agent_name: str = "architect-v1"
    api_version: str = "v1"
    propose_repo: str = DEFAULT_PROPOSE_REPO
    timeout_seconds: float = 120.0
    poll_interval_seconds: float = 2.0
    poll_max_seconds: float = 240.0
    # Instruction appended to the user's free text. It pins the agent to the
    # APPROVAL-GATE behaviour: PROPOSE a review PR via factory.propose, do NOT deploy.
    output_contract: str = field(default=(
        "\n\n---\n"
        "You are being called by the platform front-door to PROPOSE an architecture for "
        "HUMAN APPROVAL — you are NOT deploying anything.\n"
        "Follow your golden-thread DELIVER method. Reuse existing ComponentDefinitions "
        "(use catalog.* to discover, oam.dry_run to validate). Run your traceability gate; "
        "do not proceed on an uncovered requirement.\n"
        "When the OAM passes oam.dry_run and your traceability gate is clean, call the "
        "`factory.propose` MCP tool ONCE to open a review Pull Request with:\n"
        f"  repo: \"{DEFAULT_PROPOSE_REPO}\"\n"
        "  title: \"architecture: <app-name>\"\n"
        "  files: {\n"
        "    \"proposed-architectures/<app-name>/oam.yaml\": <the validated OAM Application "
        "(apiVersion core.oam.dev/v1beta1, kind Application)>,\n"
        "    \"proposed-architectures/<app-name>/REQUIREMENTS.md\": <a REQUIREMENTS.md with a "
        "use-case summary and per-component responsibilities, PLUS — per service — exactly ONE "
        "fenced ```acceptance block in EXACTLY this schema (do NOT use a flat list or a 'verify' "
        "field):\n"
        "      ```acceptance\n"
        "      service: <microservice-name>\n"
        "      criteria:\n"
        "        - id: ac-1\n"
        "          statement: \"<short observable invariant>\"\n"
        "          kind: test            # test | config | accepted-gap\n"
        "          given: \"<precondition>\"   # REQUIRED for kind:test\n"
        "          when:  \"<action>\"         # REQUIRED for kind:test\n"
        "          then:  \"<observable outcome>\"  # REQUIRED for kind:test\n"
        "      ```\n"
        "      Every kind:test criterion MUST have given/when/then. Use kind:accepted-gap (with a "
        "'reason') for deferred obligations. >=1 kind:test per service. ids unique per service.>\n"
        "  }\n"
        "Do NOT call app.submit or app.submit_wait — deployment happens only after a human "
        "MERGES the PR. After factory.propose returns, your FINAL message MUST state the PR "
        "URL on its own line (e.g. 'PR: https://github.com/<owner>/"
        f"{DEFAULT_PROPOSE_REPO}/pull/<n>') and a one-line traceability-coverage summary."
    ))

    def propose_architecture(self, requirement_text: str, token: str) -> str:
        """Drive the agent once with the free-text requirement; return assistant text
        (which, on success, contains the review-PR URL).

        Raises requests.RequestException on transport failure and RuntimeError on a
        non-200 / errored Foundry response (the diagnostic body is surfaced)."""
        if not requirement_text or not requirement_text.strip():
            raise ValueError("requirement_text must be non-empty")

        # NOTE: the /openai/v1/ path rejects an api-version query param ("not allowed
        # when using /v1 path"), so we do NOT append one here.
        url = f"{self.endpoint.rstrip('/')}/openai/v1/responses"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body: dict[str, Any] = {
            "input": [{
                "type": "message",
                "role": "user",
                "content": requirement_text + self.output_contract,
            }],
            "agent_reference": {"name": self.agent_name, "type": "agent_reference"},
        }

        resp = requests.post(url, json=body, headers=headers, timeout=self.timeout_seconds)
        if resp.status_code != 200:
            raise RuntimeError(
                f"architect /responses POST failed: {resp.status_code} {resp.text[:500]}"
            )
        obj = resp.json()

        # Poll until terminal (Foundry may return queued/in_progress synchronously).
        deadline = time.monotonic() + self.poll_max_seconds
        status = obj.get("status", "")
        while status in ("queued", "in_progress") and time.monotonic() < deadline:
            time.sleep(self.poll_interval_seconds)
            rid = obj.get("id")
            r = requests.get(
                f"{self.endpoint.rstrip('/')}/openai/v1/responses/{rid}",
                headers=headers, timeout=self.timeout_seconds,
            )
            obj = r.json()
            status = obj.get("status", "")

        if obj.get("error"):
            raise RuntimeError(f"architect responded with error: {obj['error']}")
        if status not in ("completed", ""):
            raise RuntimeError(f"architect did not complete (status={status!r})")

        return self._assistant_text(obj)

    @staticmethod
    def _assistant_text(resp: dict[str, Any]) -> str:
        """Concatenate all assistant output_text fragments from a /responses object."""
        chunks: list[str] = []
        for o in resp.get("output", []) or []:
            if o.get("type") != "message":
                continue
            for c in o.get("content", []) or []:
                if c.get("type") == "output_text" and c.get("text"):
                    chunks.append(c["text"])
        return "\n".join(chunks)
