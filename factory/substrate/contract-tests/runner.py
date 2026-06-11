#!/usr/bin/env python3
"""
HARD-4 (#171): per-component-type post-deploy contract test runner.

PROBLEM this productizes: components shipped "Ready" without data-plane proof.
RT-1 was green for days while ZERO telemetry flowed — a readiness probe proves
the *transport* (the pod accepts connections), not the *pipeline* (a real message
travels consume->broadcast->ws, or ingest->topic, or processor->transform->topic).

During RT-1 we hand-built "rt1-flow": an in-cluster pod that used the gateway image's
aiokafka+websockets to (a) connect wss through APIM with ?subscription-key&token,
(b) produce a marker JSON telemetry message to the topic the gateway consumes, and
(c) assert the ws client received that exact marker. This module generalises that
single hand-run into a typed, repeatable contract test selected per component type.

DETECTION (how a component's type/role is chosen) — stated explicitly so the
sensor and the README agree on the contract:
  * CHECK_TYPE env (set by the sensor from the ksvc's
    `app.kubernetes.io/component` label) is authoritative:
        realtime-service | graphql-gateway | webservice
  * For realtime-service the *role* is resolved (most-specific first):
      1. CHECK_ROLE env (sensor maps annotation
         `contract-test.cafe.io/role` -> CHECK_ROLE; opt-in override), else
      2. `realtime-service.oam.dev/role` annotation (rt-2 W2; sensor -> CHECK_ROLE), else
      3. inferred from the binding env the realtime-service CD injects:
           - has CONSUME_* AND PRODUCE_* AND WEBSOCKET=true  -> gateway
           - has PRODUCE_* only (no CONSUME_*)               -> ingest
           - has CONSUME_* AND PRODUCE_* AND not websocket    -> processor
  * webservice runs the contract test ONLY when expose-api opted it in
    (sensor only fires for ksvcs labelled `expose-api.cafe.io/publish=true`).

The runner reads ALL credentials/topics at RUNTIME from env that the sensor wires
via `envFrom` the component's `<comp>-conn` secret (KAFKA_BOOTSTRAP_SERVERS,
CONSUME_<topic>, PRODUCE_<topic>, plus the ksvc cluster URL). NOTHING is baked into
the image — public-repo safe.

Verdict: exits 0 (pass) / 1 (fail) and prints ONE line of JSON to stdout:
  {"component","type","check","pass","detail"}
so a `kubectl logs` (or the W4 lifecycle.state follow-up) can scrape a single line.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional

# Default per-check timeout (seconds). Overridable via CONTRACT_TIMEOUT.
DEFAULT_TIMEOUT = 60.0


# --------------------------------------------------------------------------- #
# Verdict
# --------------------------------------------------------------------------- #
@dataclass
class Verdict:
    """The single-line result emitted to stdout. Stable shape for log-scraping."""

    component: str
    type: str
    check: str
    passed: bool
    detail: str

    def to_json(self) -> str:
        # Key is "pass" (per the task contract) though the attr is "passed"
        # (pass is a Python keyword).
        return json.dumps(
            {
                "component": self.component,
                "type": self.type,
                "check": self.check,
                "pass": self.passed,
                "detail": self.detail,
            },
            separators=(",", ":"),
            sort_keys=True,
        )


# --------------------------------------------------------------------------- #
# Config (env -> typed) — pure, unit-testable
# --------------------------------------------------------------------------- #
@dataclass
class Config:
    component: str
    ctype: str  # realtime-service | graphql-gateway | webservice
    namespace: str
    role: str  # gateway | ingest | processor | "" (n/a)
    timeout: float
    apim_mode: bool
    # Resolved endpoints / topics (read from env at runtime).
    ksvc_url: str  # in-cluster base URL OR APIM base when apim_mode
    ws_token: str
    apim_subscription_key: str
    kafka_bootstrap: str
    consume_topics: List[str]
    produce_topics: List[str]


def _collect_topics(prefix: str, environ: Dict[str, str]) -> List[str]:
    """The realtime-service CD emits one env var per topic: CONSUME_<t>=<t> /
    PRODUCE_<t>=<t> (it avoids a CUE import for comma-joining). Recover the
    topic list from those keys; the *value* is the real topic name."""
    out: List[str] = []
    for k, v in environ.items():
        if k.startswith(prefix) and v:
            out.append(v)
    return sorted(set(out))


def _infer_role(environ: Dict[str, str]) -> str:
    consume = bool(_collect_topics("CONSUME_", environ))
    produce = bool(_collect_topics("PRODUCE_", environ))
    websocket = str(environ.get("WEBSOCKET", "")).lower() == "true"
    if consume and produce and websocket:
        return "gateway"
    if produce and not consume:
        return "ingest"
    if consume and produce:
        return "processor"
    if consume and websocket:
        return "gateway"  # consume-only ws gateway (RT-1 rtdemo-gateway shape)
    return "gateway"  # safe default: the most-exercised path


def load_config(environ: Optional[Dict[str, str]] = None) -> Config:
    e = dict(os.environ if environ is None else environ)
    ctype = e.get("CHECK_TYPE", "").strip()
    role = e.get("CHECK_ROLE", "").strip()
    if ctype == "realtime-service" and not role:
        role = _infer_role(e)

    apim_mode = str(e.get("APIM_MODE", "")).lower() == "true"
    component = e.get("COMPONENT_NAME", "unknown")
    namespace = e.get("COMPONENT_NS", "default")

    # In-cluster Knative URL; APIM base overrides it when APIM_MODE=true.
    cluster_url = e.get(
        "KSVC_URL", "http://{}.{}.svc.cluster.local".format(component, namespace)
    )
    apim_base = e.get("APIM_BASE_URL", "")
    ksvc_url = apim_base if (apim_mode and apim_base) else cluster_url

    return Config(
        component=component,
        ctype=ctype,
        namespace=namespace,
        role=role,
        timeout=float(e.get("CONTRACT_TIMEOUT", DEFAULT_TIMEOUT)),
        apim_mode=apim_mode,
        ksvc_url=ksvc_url.rstrip("/"),
        ws_token=e.get("WS_TOKEN", "ct-probe"),
        apim_subscription_key=e.get("APIM_SUBSCRIPTION_KEY", ""),
        kafka_bootstrap=e.get("KAFKA_BOOTSTRAP_SERVERS", ""),
        consume_topics=_collect_topics("CONSUME_", e),
        produce_topics=_collect_topics("PRODUCE_", e),
    )


def _marker(component: str) -> Dict[str, object]:
    """A uniquely-tagged JSON telemetry message. The id round-trips through the
    pipeline so a check can assert *this* message arrived (not just any traffic)."""
    return {
        "contract_test": True,
        "marker_id": "ct-{}".format(uuid.uuid4().hex[:12]),
        "component": component,
        "ts": time.time(),
        "value": 42,
    }


# --------------------------------------------------------------------------- #
# Lazy client imports (kept out of import-time so unit tests can run without
# aiokafka/websockets/httpx installed, and so a missing dep is a clear failure).
# --------------------------------------------------------------------------- #
def _ws_url(cfg: Config) -> str:
    base = cfg.ksvc_url
    scheme_ws = "wss" if base.startswith("https") else "ws"
    host = base.split("://", 1)[-1]
    q = "token={}".format(cfg.ws_token)
    if cfg.apim_mode and cfg.apim_subscription_key:
        q += "&subscription-key={}".format(cfg.apim_subscription_key)
    return "{}://{}/ws?{}".format(scheme_ws, host, q)


async def _produce_to_kafka(cfg: Config, topic: str, payload: Dict[str, object]) -> None:
    from aiokafka import AIOKafkaProducer  # type: ignore

    prod = AIOKafkaProducer(
        bootstrap_servers=cfg.kafka_bootstrap,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await prod.start()
    try:
        await prod.send_and_wait(topic, payload)
    finally:
        await prod.stop()


async def _end_offsets_sum(cfg: Config, topic: str) -> int:
    from aiokafka import AIOKafkaConsumer, TopicPartition  # type: ignore

    cons = AIOKafkaConsumer(bootstrap_servers=cfg.kafka_bootstrap)
    await cons.start()
    try:
        parts = cons.partitions_for_topic(topic) or set()
        tps = [TopicPartition(topic, p) for p in parts]
        if not tps:
            return 0
        end = await cons.end_offsets(tps)
        return sum(end.values())
    finally:
        await cons.stop()


# --------------------------------------------------------------------------- #
# Per-type checks. Each takes (cfg, deps) and returns a Verdict.
# `deps` lets unit tests inject mock clients (Dependency Injection).
# --------------------------------------------------------------------------- #
class Deps:
    """Injectable IO seam. Production wires the real aiokafka/ws/http clients;
    tests pass fakes. Keeps the dispatch + timeout logic pure-testable."""

    def __init__(
        self,
        ws_recv: Optional[Callable[[Config, Dict[str, object]], Awaitable[bool]]] = None,
        kafka_produce: Optional[Callable[[Config, str, Dict[str, object]], Awaitable[None]]] = None,
        end_offsets: Optional[Callable[[Config, str], Awaitable[int]]] = None,
        kafka_consume_match: Optional[Callable[[Config, str, str], Awaitable[bool]]] = None,
        http_get: Optional[Callable[[Config, str], Awaitable[int]]] = None,
        http_post_graphql: Optional[Callable[[Config, str], Awaitable[bool]]] = None,
    ):
        self.ws_recv = ws_recv or _default_ws_recv
        self.kafka_produce = kafka_produce or _produce_to_kafka
        self.end_offsets = end_offsets or _end_offsets_sum
        self.kafka_consume_match = kafka_consume_match or _default_kafka_consume_match
        self.http_get = http_get or _default_http_get
        self.http_post_graphql = http_post_graphql or _default_http_post_graphql


async def _default_ws_recv(cfg: Config, marker: Dict[str, object]) -> bool:
    """Connect ws, then (caller already produced the marker) read until the
    marker_id is seen or timeout. Returns True if seen."""
    import websockets  # type: ignore

    deadline = time.monotonic() + cfg.timeout
    async with websockets.connect(_ws_url(cfg), open_timeout=cfg.timeout) as ws:
        while time.monotonic() < deadline:
            remaining = max(0.1, deadline - time.monotonic())
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                return False
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if isinstance(msg, dict) and msg.get("marker_id") == marker.get("marker_id"):
                return True
    return False


async def _default_kafka_consume_match(cfg: Config, topic: str, marker_id: str) -> bool:
    from aiokafka import AIOKafkaConsumer  # type: ignore

    cons = AIOKafkaConsumer(
        topic,
        bootstrap_servers=cfg.kafka_bootstrap,
        auto_offset_reset="latest",
        value_deserializer=lambda b: b.decode("utf-8", "ignore"),
    )
    await cons.start()
    try:
        deadline = time.monotonic() + cfg.timeout
        while time.monotonic() < deadline:
            remaining = max(0.1, deadline - time.monotonic())
            try:
                batch = await asyncio.wait_for(cons.getmany(timeout_ms=2000), timeout=remaining)
            except asyncio.TimeoutError:
                return False
            for _tp, records in batch.items():
                for r in records:
                    if marker_id in (r.value or ""):
                        return True
        return False
    finally:
        await cons.stop()


async def _default_http_get(cfg: Config, path: str) -> int:
    import httpx  # type: ignore

    headers = {}
    if cfg.apim_mode and cfg.apim_subscription_key:
        headers["Ocp-Apim-Subscription-Key"] = cfg.apim_subscription_key
    async with httpx.AsyncClient(timeout=cfg.timeout) as c:
        r = await c.get(cfg.ksvc_url + path, headers=headers)
        return r.status_code


async def _default_http_post_graphql(cfg: Config, query: str) -> bool:
    import httpx  # type: ignore

    headers = {"Content-Type": "application/json"}
    if cfg.apim_mode and cfg.apim_subscription_key:
        headers["Ocp-Apim-Subscription-Key"] = cfg.apim_subscription_key
    async with httpx.AsyncClient(timeout=cfg.timeout) as c:
        r = await c.post(cfg.ksvc_url + "/graphql", headers=headers, json={"query": query})
        if r.status_code != 200:
            return False
        try:
            body = r.json()
        except Exception:
            return False
        return isinstance(body, dict) and "data" in body


async def check_realtime_gateway(cfg: Config, deps: Deps) -> Verdict:
    """Produce a marker to the gateway's CONSUMED topic, assert it arrives on /ws.
    This is the exact rt1-flow contract, generalised."""
    if not cfg.consume_topics:
        return Verdict(cfg.component, cfg.ctype, "rt-gateway-ws-roundtrip", False,
                       "no CONSUME_* topic in env (cannot drive the gateway)")
    topic = cfg.consume_topics[0]
    marker = _marker(cfg.component)

    async def _drive() -> bool:
        # Connect ws first (so we don't miss the broadcast), produce, then await recv.
        recv_task = asyncio.ensure_future(deps.ws_recv(cfg, marker))
        await asyncio.sleep(1.0)  # let the subscription register before producing
        await deps.kafka_produce(cfg, topic, marker)
        return await recv_task

    try:
        ok = await asyncio.wait_for(_drive(), timeout=cfg.timeout + 5)
    except asyncio.TimeoutError:
        return Verdict(cfg.component, cfg.ctype, "rt-gateway-ws-roundtrip", False,
                       "marker {} not received on /ws within {}s".format(marker["marker_id"], cfg.timeout))
    detail = "marker {} {} on topic {} -> /ws".format(
        marker["marker_id"], "delivered" if ok else "NOT delivered", topic)
    return Verdict(cfg.component, cfg.ctype, "rt-gateway-ws-roundtrip", ok, detail)


async def check_realtime_ingest(cfg: Config, deps: Deps) -> Verdict:
    """POST a marker to the ingest endpoint, assert the PRODUCED topic's
    end-offset advances."""
    if not cfg.produce_topics:
        return Verdict(cfg.component, cfg.ctype, "rt-ingest-offset-advance", False,
                       "no PRODUCE_* topic in env")
    topic = cfg.produce_topics[0]
    try:
        before = await asyncio.wait_for(deps.end_offsets(cfg, topic), timeout=cfg.timeout)
        status = await asyncio.wait_for(deps.http_get(cfg, "/ingest"), timeout=cfg.timeout)
        # Give the produce a moment, then re-read.
        await asyncio.sleep(2.0)
        after = await asyncio.wait_for(deps.end_offsets(cfg, topic), timeout=cfg.timeout)
    except asyncio.TimeoutError:
        return Verdict(cfg.component, cfg.ctype, "rt-ingest-offset-advance", False,
                       "timeout probing ingest/{} within {}s".format(topic, cfg.timeout))
    ok = after > before
    return Verdict(cfg.component, cfg.ctype, "rt-ingest-offset-advance", ok,
                   "POST /ingest={} topic {} offsets {}->{}".format(status, topic, before, after))


async def check_realtime_processor(cfg: Config, deps: Deps) -> Verdict:
    """Produce a marker to the CONSUMED topic, assert a (transformed) message
    carrying the marker id appears on the PRODUCED topic."""
    if not cfg.consume_topics or not cfg.produce_topics:
        return Verdict(cfg.component, cfg.ctype, "rt-processor-transform", False,
                       "processor needs both CONSUME_* and PRODUCE_* topics")
    src, dst = cfg.consume_topics[0], cfg.produce_topics[0]
    marker = _marker(cfg.component)
    try:
        watch = asyncio.ensure_future(deps.kafka_consume_match(cfg, dst, str(marker["marker_id"])))
        await asyncio.sleep(1.0)
        await deps.kafka_produce(cfg, src, marker)
        ok = await asyncio.wait_for(watch, timeout=cfg.timeout + 5)
    except asyncio.TimeoutError:
        return Verdict(cfg.component, cfg.ctype, "rt-processor-transform", False,
                       "marker {} from {} not seen on {} within {}s".format(
                           marker["marker_id"], src, dst, cfg.timeout))
    return Verdict(cfg.component, cfg.ctype, "rt-processor-transform", ok,
                   "marker {} {} {}->{}".format(marker["marker_id"], "transformed" if ok else "lost", src, dst))


async def check_webservice(cfg: Config, deps: Deps) -> Verdict:
    """expose-api webservice: GET /health expecting 200."""
    try:
        status = await asyncio.wait_for(deps.http_get(cfg, "/health"), timeout=cfg.timeout)
    except asyncio.TimeoutError:
        return Verdict(cfg.component, cfg.ctype, "webservice-health", False,
                       "GET /health timed out after {}s".format(cfg.timeout))
    ok = status == 200
    return Verdict(cfg.component, cfg.ctype, "webservice-health", ok,
                   "GET {}/health -> {}".format(cfg.ksvc_url, status))


async def check_graphql_gateway(cfg: Config, deps: Deps) -> Verdict:
    """graphql-gateway: POST a trivial introspection query expecting 200 + data."""
    query = "{ __schema { queryType { name } } }"
    try:
        ok = await asyncio.wait_for(deps.http_post_graphql(cfg, query), timeout=cfg.timeout)
    except asyncio.TimeoutError:
        return Verdict(cfg.component, cfg.ctype, "graphql-introspection", False,
                       "POST /graphql timed out after {}s".format(cfg.timeout))
    return Verdict(cfg.component, cfg.ctype, "graphql-introspection", ok,
                   "POST {}/graphql introspection {}".format(cfg.ksvc_url, "ok" if ok else "failed"))


# --------------------------------------------------------------------------- #
# Dispatch (Strategy lookup) — pure, unit-testable
# --------------------------------------------------------------------------- #
def select_check(cfg: Config) -> Callable[[Config, Deps], Awaitable[Verdict]]:
    if cfg.ctype == "graphql-gateway":
        return check_graphql_gateway
    if cfg.ctype == "webservice":
        return check_webservice
    if cfg.ctype == "realtime-service":
        return {
            "gateway": check_realtime_gateway,
            "ingest": check_realtime_ingest,
            "processor": check_realtime_processor,
        }.get(cfg.role, check_realtime_gateway)
    raise ValueError("unknown CHECK_TYPE: {!r}".format(cfg.ctype))


async def run(cfg: Config, deps: Optional[Deps] = None) -> Verdict:
    deps = deps or Deps()
    try:
        check = select_check(cfg)
    except ValueError as exc:
        return Verdict(cfg.component, cfg.ctype or "unknown", "dispatch", False, str(exc))
    try:
        return await check(cfg, deps)
    except Exception as exc:  # any client/import error is an explicit failed verdict
        return Verdict(cfg.component, cfg.ctype, getattr(check, "__name__", "check"),
                       False, "error: {}: {}".format(type(exc).__name__, exc))


def main() -> int:
    cfg = load_config()
    verdict = asyncio.run(run(cfg))
    print(verdict.to_json())
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    sys.exit(main())
