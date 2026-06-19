"""Platform-composition policies — the OAM-shaping invariants the platform
enforces at submit time, factored out so they are ALSO discoverable to the
architect pre-propose (via `oam.dry_run` / `catalog.validate`).

Background: the architect (architect-v1) self-corrects OAM problems only when a
validation tool it already calls reports them. The identity-topology invariant
(and the sibling singleton rules) used to live inline in `submit_use_case` and
fired ONLY at `app.submit` — invisible to `oam.dry_run` — so the architect kept
proposing OAMs that vela accepted but submit later rejected. Centralising the
checks here lets BOTH surfaces (submit + dry-run) share one source of truth with
identical, actionable messages.

`validate_policies(app)` is a PURE function on the parsed OAM Application dict.
It returns ALL violation strings (not just the first) so the dry-run surface can
show the architect every problem in one round-trip. `submit_use_case` keeps its
single-string contract by taking the first violation.
"""
from __future__ import annotations

from typing import Any

# Component types whose exposure is gated by the `is_exposed` predicate (kept in
# lock-step with SubmitUseCase._EXPOSABLE_TYPES).
_EXPOSABLE_TYPES = ("webservice", "webservice-shape", "realtime-service")

# Platform singletons: an OAM declares at most ONE of each; siblings REUSE it via
# refs instead of declaring another instance.
_SINGLETONS = (
    ("realtime-platform", "bind webservices to it via `realtime: <name>`"),
    ("graphql-gateway", "add upstream services to its `sources:` instead"),
)


def is_exposed(c: dict[str, Any]) -> bool:
    """A webservice-class component is externally exposed iff it carries the
    `expose-api` trait OR sets `properties.exposeApi`. Shared by both the
    identity-topology check and submit's APIM-product membership helper."""
    for t in c.get("traits") or []:
        if t.get("type") == "expose-api":
            return True
    return bool((c.get("properties") or {}).get("exposeApi"))


def validate_policies(app: dict[str, Any]) -> list[str]:
    """Return ALL platform-composition policy violations for the parsed OAM
    Application dict `app` (empty list when compliant). Pure: no I/O, no mutation.

    Checks (messages are byte-identical to the historical submit-time strings):
      1. >1 identity (auth0-idp) component -> reject.
      2. exposed webservice-class component(s) with NO identity component -> reject.
      3. >1 realtime-platform OR >1 graphql-gateway (platform singletons) -> reject.
    """
    comps = app.get("spec", {}).get("components", []) or []
    violations: list[str] = []

    identity_comps = [c.get("name") for c in comps if c.get("type") == "auth0-idp"]
    exposed = [c.get("name") for c in comps
               if c.get("type") in _EXPOSABLE_TYPES and is_exposed(c)]

    if len(identity_comps) > 1:
        violations.append(
            "identity topology: found %d identity components (%s) - an OAM must "
            "have at most ONE; point every webservice's `identity:` ref and every "
            "expose-api trait at the same component"
            % (len(identity_comps), ", ".join(identity_comps)))
    elif exposed and not identity_comps:
        # `elif`: when there are >1 identity comps the exposed-without-identity
        # branch is unreachable anyway (identity_comps is non-empty), preserving
        # submit's historical single-violation-per-call behaviour for this pair.
        violations.append(
            "identity topology: components %s are externally exposed but the OAM "
            "has no identity component - add ONE auth0-idp component and reference "
            "it via `identity:` + expose-api(identity=...)" % ", ".join(exposed))

    for singleton_type, reuse_hint in _SINGLETONS:
        dupes = [c.get("name") for c in comps if c.get("type") == singleton_type]
        if len(dupes) > 1:
            violations.append(
                "singleton topology: found %d %s components (%s) - an OAM must "
                "declare at most ONE; %s"
                % (len(dupes), singleton_type, ", ".join(dupes), reuse_hint))

    return violations
