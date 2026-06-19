"""factory.from_requirement — W6 single front-door (PROPOSE / approval gate).

Takes a raw natural-language requirement and drives the architect-v1 Foundry
agent to PROPOSE an architecture for HUMAN APPROVAL. The architect follows its
golden-thread method, validates the OAM (oam.dry_run), and opens a *review*
Pull Request via its `factory.propose` MCP tool. It does NOT deploy.

This is the architecture-approval GATE: nothing reaches infrastructure until a
human MERGES the PR; a merge-triggered workflow then runs the real deploy
(app.submit_wait). So this use case never calls submit — it returns the PR for
review.

Flow:
    text -> ArchitectClient.propose_architecture(text) -> assistant markdown
         -> extract the review-PR URL (github.com/<owner>/<repo>/pull/<n>)
         -> ProposeResult(ok, pr_url, pr_number, message)

ADDITIVE: existing app.submit / app.submit_wait (the deploy path) are untouched.
This use case composes the architect call in front of the human gate; it adds no
provisioning logic and has NO dependency on SubmitUseCase.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Callable

from ..infrastructure.architect_client import ArchitectClient

logger = logging.getLogger(__name__)

# A GitHub PR URL in the architect's final message. Tolerant of owner/repo; we
# only require the /pull/<n> shape so the architect can target either the
# configured repo or a fork without breaking extraction.
_PR_URL = re.compile(r"https://github\.com/[^\s/]+/[^\s/]+/pull/(\d+)", re.IGNORECASE)


@dataclass
class ProposeResult:
    """Result of the PROPOSE front-door: a review PR for human approval (no deploy)."""
    ok: bool
    pr_url: str | None = None
    pr_number: int | None = None
    message: str = ""


class FromRequirementError(Exception):
    """Raised when the architect reply contains no review-PR URL to approve."""


class FromRequirementUseCase:
    def __init__(self, architect: ArchitectClient,
                 token_provider: Callable[[], str]):
        self.architect = architect
        # token_provider defers/refreshes the Foundry data-plane token without
        # baking auth into this layer (DI; mirrors the rest of the codebase).
        self._token_provider = token_provider

    def from_requirement(self, text: str) -> ProposeResult:
        """One-shot: free text -> architect proposes a review PR -> ProposeResult.

        Never deploys. The returned PR is the human approval gate; merging it is
        what triggers the real app.submit_wait deploy (a separate, merge-driven step)."""
        if not text or not text.strip():
            return ProposeResult(ok=False, message="requirement text must be non-empty")

        try:
            token = self._token_provider()
        except Exception as e:  # noqa: BLE001
            return ProposeResult(ok=False,
                                 message=f"could not acquire architect token: {e}")

        try:
            assistant_text = self.architect.propose_architecture(text, token)
        except Exception as e:  # noqa: BLE001
            return ProposeResult(ok=False, message=f"architect call failed: {e}")

        try:
            pr_url, pr_number = self.extract_pr(assistant_text)
        except FromRequirementError as e:
            return ProposeResult(
                ok=False,
                message=(f"architect did not open a review PR: {e}. "
                         f"Raw architect reply (first 500 chars): {assistant_text[:500]}"),
            )

        return ProposeResult(
            ok=True, pr_url=pr_url, pr_number=pr_number,
            message=(f"Architecture proposed for approval — review & merge PR #{pr_number} "
                     f"to deploy: {pr_url}"),
        )

    @staticmethod
    def extract_pr(assistant_text: str) -> tuple[str, int]:
        """Pull the review-PR URL + number out of the architect's final reply.
        Raises FromRequirementError if no PR URL is present (the architect did not
        successfully call factory.propose)."""
        m = _PR_URL.search(assistant_text or "")
        if not m:
            raise FromRequirementError("no GitHub PR URL found in the architect reply")
        return m.group(0), int(m.group(1))
