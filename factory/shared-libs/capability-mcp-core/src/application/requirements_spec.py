"""REQUIREMENTS.md handling for app.submit (SPEC-1, #173, dev-agent W1).

The architect emits a REQUIREMENTS.md alongside the OAM. app.submit carries it
(optional, additive) and commits it next to the OAM on both the central ledger and
the app monorepo root, so the use-case spec travels into the repo the dev-agent
will implement against.

This module is the pure (no I/O) core: decode-or-passthrough, minimal validation,
and a deterministic spec hash. Kept framework-free (onion: application layer
helper) so the submit use-case and the unit tests share one source of truth.

Design note (deferred): mscv materialization (per-service
microservices/<svc>/REQUIREMENTS.md sections) is OUT of scope for W1. The submit
path commits the whole-spec file directly to the monorepo root + ledger; splitting
it per service is a later mscv concern.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re

# The one section the dev-agent's contract loop keys on. Validation requires it
# with at least one non-empty criterion line beneath it.
_ACCEPTANCE_HEADING = re.compile(r"^\s{0,3}#{2,6}\s+Acceptance\s+Criteria\s*$",
                                 re.IGNORECASE)
_ANY_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S")


class RequirementsError(ValueError):
    """Raised when supplied requirements are empty or structurally invalid."""


def decode_requirements(raw: str) -> str:
    """Accept markdown text OR a base64-encoded blob (mirrors how the OAM is
    accepted as text then b64-encoded internally — here we accept either form so
    callers/transports that base64 the markdown are handled transparently).

    Heuristic: a string that (a) has no markdown heading and no newline, (b)
    matches a base64 alphabet, and (c) decodes to valid UTF-8 that *does* contain
    a markdown heading is treated as base64. Everything else is passed through as
    literal markdown. This never mangles real markdown (which carries `#`/newlines
    and is not pure-base64).
    """
    if raw is None:
        return ""
    text = raw
    looks_like_markdown = ("\n" in raw) or _ANY_HEADING.match(raw.strip() or "")
    if not looks_like_markdown and re.fullmatch(r"[A-Za-z0-9+/=\s]+", raw or ""):
        try:
            decoded = base64.b64decode(raw, validate=True).decode("utf-8")
            if _ANY_HEADING.search(decoded) or "\n" in decoded:
                text = decoded
        except (binascii.Error, ValueError, UnicodeDecodeError):
            pass  # not base64 / not utf-8 → treat as literal markdown
    return text


def normalize(text: str) -> str:
    """Deterministic normalization for hashing and idempotent commits:
      - CRLF/CR → LF
      - strip trailing whitespace on each line
      - collapse 3+ blank lines to one
      - strip leading/trailing blank lines
      - exactly one trailing newline

    Two semantically-identical specs that differ only in trailing whitespace /
    blank-line runs / line endings hash identically → no re-fire churn (W3).
    """
    s = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in s.split("\n")]
    out: list[str] = []
    blank_run = 0
    for ln in lines:
        if ln == "":
            blank_run += 1
            if blank_run > 1:
                continue
        else:
            blank_run = 0
        out.append(ln)
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def validate(text: str) -> None:
    """Minimal structural gate. Raises RequirementsError on:
      - empty / whitespace-only content
      - missing a `## Acceptance Criteria` heading (any level 2-6)
      - an Acceptance Criteria section with no non-empty criterion line before
        the next heading

    Intentionally lenient on the rest (Use Case / Components / Non-Goals) — the
    file is read by both a human and the dev-agent; we only hard-require the one
    section the contract loop depends on.
    """
    if not text or not text.strip():
        raise RequirementsError("requirements is empty")

    lines = text.split("\n")
    heading_idx = next((i for i, ln in enumerate(lines)
                        if _ACCEPTANCE_HEADING.match(ln)), None)
    if heading_idx is None:
        raise RequirementsError(
            "requirements must contain an '## Acceptance Criteria' section")

    # Gather the section body (until the next markdown heading) and require at
    # least one non-empty, non-heading line.
    has_criterion = False
    for ln in lines[heading_idx + 1:]:
        if _ANY_HEADING.match(ln):
            break
        if ln.strip():
            has_criterion = True
            break
    if not has_criterion:
        raise RequirementsError(
            "'## Acceptance Criteria' section has no criterion lines")


def spec_hash(normalized_text: str) -> str:
    """Deterministic spec hash: `spec-<first 12 hex of sha256(normalized)>`.

    Format chosen to be a valid k8s annotation value and short enough for commit
    messages. The dev-agent trigger (W3) compares this to its stored marker to
    decide whether a re-implementation pass is needed."""
    digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return f"spec-{digest[:12]}"


def prepare(raw: str) -> tuple[str, str]:
    """Decode → validate → normalize → hash. Returns (normalized_content, hash).
    Raises RequirementsError if the supplied requirements are invalid."""
    decoded = decode_requirements(raw)
    validate(decoded)
    normalized = normalize(decoded)
    return normalized, spec_hash(normalized)
