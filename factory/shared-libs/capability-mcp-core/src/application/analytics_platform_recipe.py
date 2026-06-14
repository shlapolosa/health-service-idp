"""analytics-platform OAM pre-processor (submit-time recipe).

The `analytics-platform` component is a DECLARATIVE intent ("I want CDC/streaming
ingestion of these tables into a warehouse, with these feature streams"). It is not
a deployable workload itself — it expands, at submit time, into concrete substrate:

  - a `realtime-platform` component (reused if one exists, injected otherwise) that
    carries the Kafka Connect `connectors[]` (Debezium source + Snowflake sink) and
    Lenses SQL `processors[]` derived from the analytics-platform's fields, plus the
    `topics[]` every connector/processor references.

This mirrors the GQL-1 `_inject_graphql_sources` pattern: app.submit is the only
render stage that can see SIBLING components, so it is where the analytics-platform
is resolved against the realtime-platform / source / warehouse components.

Pure function, deterministic, additive:
  - an OAM without an analytics-platform component passes through UNCHANGED;
  - NO secret VALUES ever appear here — connector config uses ${VAR} placeholders
    resolved at provisioning time from the named `secretRefs` (the `<comp>-conn`
    binding secrets), exactly like the rest of the platform's binding contract.

CONTRACT agreed with the realtime-platform XRD (concurrent change):
  connectors[] item: {name: str, class: str, config: {str:str}, secretRefs: [str]}
  processors[] item: {name: str, sql: str}
"""
from __future__ import annotations

import copy
from typing import Any

__all__ = ["apply_analytics_platform", "AnalyticsPlatformError"]


class AnalyticsPlatformError(ValueError):
    """Raised on an invalid analytics-platform topology (e.g. >1 per OAM)."""


# Debezium Postgres source connector class (CDC ingestion).
_DEBEZIUM_PG_CLASS = "io.debezium.connector.postgresql.PostgresConnector"
# Snowflake Kafka sink connector class (warehouse load).
_SNOWFLAKE_SINK_CLASS = "com.snowflake.kafka.connector.SnowflakeSinkConnector"
# Default warehouse credentials secret when the analytics-platform omits it.
_DEFAULT_WAREHOUSE_SECRET = "snowflake-conn"
# Topic prefix Debezium writes change events under (database.topic.prefix).
_CDC_PREFIX = "cdc"


def apply_analytics_platform(oam: dict[str, Any]) -> dict[str, Any]:
    """Expand a single `analytics-platform` component into realtime-platform
    connectors/processors/topics. Returns a NEW (deep-copied) OAM dict; the input
    is never mutated. OAMs without an analytics-platform are returned unchanged
    (a structural copy, so the caller can treat the result uniformly).

    Raises AnalyticsPlatformError if more than one analytics-platform exists.
    """
    oam = copy.deepcopy(oam)
    comps: list[dict[str, Any]] = oam.get("spec", {}).get("components", []) or []

    aps = [c for c in comps if c.get("type") == "analytics-platform"]
    if not aps:
        return oam
    if len(aps) > 1:
        names = ", ".join(c.get("name", "<unnamed>") for c in aps)
        raise AnalyticsPlatformError(
            f"exactly one analytics-platform per application — found {len(aps)} "
            f"({names}); merge them into one"
        )

    ap = aps[0]
    app_name = oam.get("metadata", {}).get("name") or ap.get("name") or "app"
    ap_props: dict[str, Any] = ap.setdefault("properties", {})

    # (a) RESOLVE / INJECT the realtime-platform the analytics streams flow through.
    rtp = _resolve_realtime_platform(oam, comps, ap_props, app_name)
    rtp_props: dict[str, Any] = rtp.setdefault("properties", {})

    # (b) GENERATE connectors (Debezium source [cdc only] + Snowflake sink).
    connectors = _build_connectors(oam, comps, ap, ap_props, app_name)
    if connectors:
        existing = rtp_props.setdefault("connectors", [])
        _merge_by_name(existing, connectors)

    # (c) GENERATE processors from features (+ optional roundtrip republish).
    processors = _build_processors(ap_props, app_name)
    if processors:
        existing_p = rtp_props.setdefault("processors", [])
        _merge_by_name(existing_p, processors)

    # (d) TOPICS: ensure every referenced topic exists on the platform (dedup by name).
    topics = _referenced_topics(ap_props, app_name)
    if topics:
        existing_t = rtp_props.setdefault("topics", [])
        _ensure_topics(existing_t, topics)

    # (e) WIRE realtime-services (conservative: only when AP + such services present).
    _wire_realtime_services(comps, ap_props, app_name)

    return oam


# ----------------------------------------------------------------------
# (a) realtime-platform resolution / injection
# ----------------------------------------------------------------------

def _resolve_realtime_platform(oam: dict[str, Any], comps: list[dict[str, Any]],
                               ap_props: dict[str, Any],
                               app_name: str) -> dict[str, Any]:
    """Return the realtime-platform component the analytics streams flow through.

    - AP.realtime already set    -> reuse the named component (or, if not present
                                     as a component, inject one with that name).
    - exactly one rtp component  -> reuse it; set AP.realtime to its name.
    - no rtp component            -> inject `<app>-stream` and set AP.realtime to it.
    """
    rtps = [c for c in comps if c.get("type") == "realtime-platform"]
    named = ap_props.get("realtime")

    if named:
        for c in rtps:
            if c.get("name") == named:
                return c
        # AP names a platform that isn't declared as a component yet — inject it.
        return _inject_realtime_platform(oam, comps, named)

    if len(rtps) == 1:
        ap_props["realtime"] = rtps[0].get("name")
        return rtps[0]

    # None declared (the >1 case is rejected upstream by the singleton invariant).
    rtp_name = f"{app_name}-stream"
    ap_props["realtime"] = rtp_name
    return _inject_realtime_platform(oam, comps, rtp_name)


def _inject_realtime_platform(oam: dict[str, Any], comps: list[dict[str, Any]],
                              name: str) -> dict[str, Any]:
    comp = {"name": name, "type": "realtime-platform", "properties": {"topics": []}}
    comps.append(comp)
    # comps may be a fresh list (when spec.components was absent) — re-attach it.
    oam.setdefault("spec", {})["components"] = comps
    return comp


# ----------------------------------------------------------------------
# (b) connectors
# ----------------------------------------------------------------------

def _build_connectors(oam: dict[str, Any], comps: list[dict[str, Any]],
                      ap: dict[str, Any], ap_props: dict[str, Any],
                      app_name: str) -> list[dict[str, Any]]:
    connectors: list[dict[str, Any]] = []
    ingestion = ap_props.get("ingestion", {}) or {}
    mode = str(ingestion.get("mode", "cdc")).strip().lower()
    tables = list(ingestion.get("tables", []) or [])

    # SOURCE connector (cdc mode only). gateway mode => ingestion comes from
    # existing realtime-service producers, so no source connector is generated.
    if mode == "cdc":
        source_name = ingestion.get("source")
        source_secret = f"{source_name}-conn" if source_name else f"{app_name}-conn"
        connectors.append({
            "name": f"{app_name}-pg-source",
            "class": _DEBEZIUM_PG_CLASS,
            "config": {
                "connector.class": _DEBEZIUM_PG_CLASS,
                "database.hostname": "${PG_HOST}",
                "database.port": "${PG_PORT|5432}",
                "database.user": "${PG_USER}",
                "database.password": "${PG_PASSWORD}",
                "database.dbname": "${PG_DBNAME}",
                "database.sslmode": "require",
                "plugin.name": "pgoutput",
                "slot.name": _slot_name(app_name),
                "topic.prefix": _CDC_PREFIX,
                "table.include.list": ",".join(tables),
                "key.converter": "org.apache.kafka.connect.json.JsonConverter",
                "value.converter": "org.apache.kafka.connect.json.JsonConverter",
                "key.converter.schemas.enable": "false",
                "value.converter.schemas.enable": "false",
                # Emit only the post-image (the row's new state) — feature streams
                # consume current state, not the full before/after envelope.
                "after.state.only": "true",
            },
            "secretRefs": [source_secret],
        })

    # SINK connector (always): land the cdc + feature topics into Snowflake.
    warehouse = ap_props.get("warehouse", {}) or {}
    wh_secret = warehouse.get("credentialsSecret") or _DEFAULT_WAREHOUSE_SECRET
    sink_topics = _sink_topics(ap_props, app_name)
    connectors.append({
        "name": f"{app_name}-sf-sink",
        "class": _SNOWFLAKE_SINK_CLASS,
        "config": {
            "connector.class": _SNOWFLAKE_SINK_CLASS,
            "snowflake.url.name": "${SNOWFLAKE_ACCOUNT}.snowflakecomputing.com",
            "snowflake.user.name": "${SNOWFLAKE_USER}",
            "snowflake.private.key": "${SNOWFLAKE_PRIVATE_KEY}",
            "snowflake.database.name": "${SNOWFLAKE_DATABASE}",
            "snowflake.schema.name": "${SNOWFLAKE_SCHEMA}",
            # Json converter is schema-registry-free (v1). Avro
            # (SnowflakeAvroConverter + a registry) is the option for typed columns.
            "value.converter": "com.snowflake.kafka.connector.records.SnowflakeJsonConverter",
            "buffer.count.records": "1000000",
            "buffer.flush.time": "10",
            "buffer.size.bytes": "250000000",
            "tasks.max": "1",
            "topics": ",".join(sink_topics),
        },
        "secretRefs": [wh_secret],
    })

    return connectors


def _slot_name(app_name: str) -> str:
    # Postgres replication slot names: lowercase letters, digits, underscores only.
    return app_name.replace("-", "_")


# ----------------------------------------------------------------------
# (c) processors
# ----------------------------------------------------------------------

def _build_processors(ap_props: dict[str, Any], app_name: str) -> list[dict[str, Any]]:
    processors: list[dict[str, Any]] = []
    for feat in ap_props.get("features", []) or []:
        if not isinstance(feat, dict):
            continue
        name = feat.get("name")
        sql = feat.get("sql")
        if name and sql:
            processors.append({"name": name, "sql": sql})

    # Optional roundtrip republish: stream a feature topic back onto a topic the
    # gateway realtime-service consumes (best-effort Lenses SQL; the operator can
    # refine the SELECT). Only emitted when roundtrip.topic is set.
    roundtrip = ap_props.get("roundtrip", {}) or {}
    rt_topic = roundtrip.get("topic")
    if rt_topic:
        source_topic = roundtrip.get("from") or _first_feature_topic(ap_props, app_name)
        processors.append({
            "name": f"{app_name}-roundtrip",
            # best-effort: republish the feature stream onto the roundtrip topic so
            # a gateway realtime-service can fan it out to /ws subscribers.
            "sql": f"INSERT INTO {rt_topic} SELECT STREAM * FROM {source_topic}",
        })
    return processors


def _first_feature_topic(ap_props: dict[str, Any], app_name: str) -> str:
    for feat in ap_props.get("features", []) or []:
        if isinstance(feat, dict) and feat.get("name"):
            return feat["name"]
    return f"{app_name}-features"


# ----------------------------------------------------------------------
# (d) topics
# ----------------------------------------------------------------------

def _referenced_topics(ap_props: dict[str, Any], app_name: str) -> list[str]:
    """Every topic referenced by the generated connectors/processors, deduped,
    order-preserving: cdc.<table> per included table, the feature topics, the
    roundtrip topic, and any explicit sinkTopics."""
    topics: list[str] = []

    def _add(t: str | None) -> None:
        if t and t not in topics:
            topics.append(t)

    ingestion = ap_props.get("ingestion", {}) or {}
    if str(ingestion.get("mode", "cdc")).strip().lower() == "cdc":
        for tbl in ingestion.get("tables", []) or []:
            _add(_cdc_topic(tbl))

    for feat in ap_props.get("features", []) or []:
        if isinstance(feat, dict):
            _add(feat.get("name"))

    roundtrip = ap_props.get("roundtrip", {}) or {}
    _add(roundtrip.get("topic"))

    for t in ap_props.get("sinkTopics", []) or []:
        _add(t)

    return topics


def _cdc_topic(table: str) -> str:
    """Debezium topic for a table: `<prefix>.<schema>.<table>` — but the platform's
    `table.include.list` already accepts `schema.table`, and Debezium derives the
    topic as `<topic.prefix>.<schema>.<table>`. When a bare table is given we
    namespace it under the prefix as `<prefix>.<table>` (best-effort)."""
    return f"{_CDC_PREFIX}.{table}"


def _sink_topics(ap_props: dict[str, Any], app_name: str) -> list[str]:
    """Topics the Snowflake sink loads. Explicit AP.sinkTopics wins; otherwise
    default to the cdc topics (for the included tables) + the feature topics."""
    explicit = list(ap_props.get("sinkTopics", []) or [])
    if explicit:
        return explicit
    out: list[str] = []
    ingestion = ap_props.get("ingestion", {}) or {}
    if str(ingestion.get("mode", "cdc")).strip().lower() == "cdc":
        for tbl in ingestion.get("tables", []) or []:
            t = _cdc_topic(tbl)
            if t not in out:
                out.append(t)
    for feat in ap_props.get("features", []) or []:
        if isinstance(feat, dict) and feat.get("name") and feat["name"] not in out:
            out.append(feat["name"])
    return out


def _ensure_topics(existing: list[dict[str, Any]], names: list[str]) -> None:
    have = {t.get("name") for t in existing if isinstance(t, dict)}
    for n in names:
        if n not in have:
            existing.append({"name": n})
            have.add(n)


# ----------------------------------------------------------------------
# (e) realtime-service wiring (conservative)
# ----------------------------------------------------------------------

def _wire_realtime_services(comps: list[dict[str, Any]], ap_props: dict[str, Any],
                            app_name: str) -> None:
    """Conservative wiring: only when BOTH an analytics-platform and role-bearing
    realtime-services are present, and ONLY when the service has no consumes/produces
    referencing analytics topics yet.

      - a `gateway`  service CONSUMES the roundtrip topic (fans it to /ws);
      - a `processor`/`output` service CONSUMES feature topics (further transform).

    Never overwrites an explicit consumes/produces list."""
    roundtrip = ap_props.get("roundtrip", {}) or {}
    rt_topic = roundtrip.get("topic")
    feature_topics = [f["name"] for f in ap_props.get("features", []) or []
                      if isinstance(f, dict) and f.get("name")]

    for c in comps:
        if c.get("type") != "realtime-service":
            continue
        props = c.setdefault("properties", {})
        role = str(props.get("role", "gateway")).strip().lower()
        if props.get("consumes") or props.get("produces"):
            continue  # explicit wiring already present — leave it authoritative
        if role == "gateway" and rt_topic:
            props["consumes"] = [rt_topic]
        elif role in ("processor", "output") and feature_topics:
            props["consumes"] = list(feature_topics)


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def _merge_by_name(existing: list[dict[str, Any]], new: list[dict[str, Any]]) -> None:
    """Append items from `new` whose `name` is not already present in `existing`
    (idempotent re-run; never duplicates a connector/processor)."""
    have = {item.get("name") for item in existing if isinstance(item, dict)}
    for item in new:
        if item.get("name") not in have:
            existing.append(item)
            have.add(item.get("name"))
