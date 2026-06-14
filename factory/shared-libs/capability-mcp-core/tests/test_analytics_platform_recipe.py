"""Unit tests for the analytics-platform submit-time recipe.

Covers: inject-when-absent, reuse-when-present, >1 analytics rejected, cdc
connectors (secretRefs + ${VARS}), topic dedup, gateway-mode skips the source
connector, processors from features + roundtrip, and the additive pass-through.
"""
from __future__ import annotations

import copy

import pytest

from src.application.analytics_platform_recipe import (
    AnalyticsPlatformError,
    apply_analytics_platform,
)


def _ap_oam(app_name="orders", *, realtime=None, mode="cdc",
            tables=("public.orders", "public.lineitems"), source="ordersdb",
            warehouse_secret=None, features=None, roundtrip=None, sink_topics=None,
            extra_components=None):
    ap_props = {
        "ingestion": {"mode": mode, "tables": list(tables), "source": source},
    }
    if realtime:
        ap_props["realtime"] = realtime
    if warehouse_secret:
        ap_props["warehouse"] = {"credentialsSecret": warehouse_secret}
    if features is not None:
        ap_props["features"] = features
    if roundtrip is not None:
        ap_props["roundtrip"] = roundtrip
    if sink_topics is not None:
        ap_props["sinkTopics"] = sink_topics

    comps = [{"name": "analytics", "type": "analytics-platform", "properties": ap_props}]
    if extra_components:
        comps = list(extra_components) + comps
    return {
        "apiVersion": "core.oam.dev/v1beta1", "kind": "Application",
        "metadata": {"name": app_name, "namespace": "default"},
        "spec": {"components": comps},
    }


def _rtp(oam):
    return next(c for c in oam["spec"]["components"] if c["type"] == "realtime-platform")


def _conn(oam, name):
    return next(c for c in _rtp(oam)["properties"]["connectors"] if c["name"] == name)


# ----------------------------------------------------------------------
# pass-through
# ----------------------------------------------------------------------

def test_no_analytics_platform_passes_through_unchanged():
    oam = {"apiVersion": "core.oam.dev/v1beta1", "kind": "Application",
           "metadata": {"name": "plain"},
           "spec": {"components": [{"name": "w", "type": "webservice", "properties": {}}]}}
    out = apply_analytics_platform(oam)
    assert out == oam  # structurally identical


def test_input_not_mutated():
    oam = _ap_oam()
    snapshot = copy.deepcopy(oam)
    apply_analytics_platform(oam)
    assert oam == snapshot  # pure function — caller's dict untouched


# ----------------------------------------------------------------------
# realtime-platform inject / reuse
# ----------------------------------------------------------------------

def test_inject_realtime_platform_when_absent():
    out = apply_analytics_platform(_ap_oam(app_name="orders"))
    rtp = _rtp(out)
    assert rtp["name"] == "orders-stream"
    ap = next(c for c in out["spec"]["components"] if c["type"] == "analytics-platform")
    assert ap["properties"]["realtime"] == "orders-stream"


def test_reuse_single_existing_realtime_platform():
    existing = {"name": "mystream", "type": "realtime-platform", "properties": {"topics": []}}
    out = apply_analytics_platform(_ap_oam(extra_components=[existing]))
    # no NEW realtime-platform injected
    rtps = [c for c in out["spec"]["components"] if c["type"] == "realtime-platform"]
    assert len(rtps) == 1 and rtps[0]["name"] == "mystream"
    ap = next(c for c in out["spec"]["components"] if c["type"] == "analytics-platform")
    assert ap["properties"]["realtime"] == "mystream"


def test_explicit_realtime_ref_kept():
    existing = {"name": "named", "type": "realtime-platform", "properties": {}}
    out = apply_analytics_platform(_ap_oam(realtime="named", extra_components=[existing]))
    ap = next(c for c in out["spec"]["components"] if c["type"] == "analytics-platform")
    assert ap["properties"]["realtime"] == "named"
    assert _rtp(out)["name"] == "named"


# ----------------------------------------------------------------------
# guard
# ----------------------------------------------------------------------

def test_two_analytics_platforms_rejected():
    oam = _ap_oam()
    oam["spec"]["components"].append(
        {"name": "analytics2", "type": "analytics-platform", "properties": {}})
    with pytest.raises(AnalyticsPlatformError) as ei:
        apply_analytics_platform(oam)
    assert "exactly one analytics-platform" in str(ei.value)


# ----------------------------------------------------------------------
# connectors
# ----------------------------------------------------------------------

def test_cdc_source_connector_generated():
    out = apply_analytics_platform(_ap_oam(app_name="orders", source="ordersdb"))
    src = _conn(out, "orders-pg-source")
    assert src["class"] == "io.debezium.connector.postgresql.PostgresConnector"
    assert src["secretRefs"] == ["ordersdb-conn"]
    cfg = src["config"]
    # ${VAR} placeholders, NO secret values
    assert cfg["database.hostname"] == "${PG_HOST}"
    assert cfg["database.port"] == "${PG_PORT|5432}"
    assert cfg["database.user"] == "${PG_USER}"
    assert cfg["database.password"] == "${PG_PASSWORD}"
    assert cfg["database.dbname"] == "${PG_DBNAME}"
    assert cfg["plugin.name"] == "pgoutput"
    assert cfg["slot.name"] == "orders"
    assert cfg["topic.prefix"] == "cdc"
    assert cfg["database.sslmode"] == "require"
    assert cfg["table.include.list"] == "public.orders,public.lineitems"
    assert cfg["after.state.only"] == "true"
    # no literal secret leaked anywhere
    assert all(v.startswith("${") or "${" not in v for v in cfg.values())


def test_snowflake_sink_connector_generated():
    out = apply_analytics_platform(_ap_oam(app_name="orders"))
    sink = _conn(out, "orders-sf-sink")
    assert sink["class"] == "com.snowflake.kafka.connector.SnowflakeSinkConnector"
    assert sink["secretRefs"] == ["snowflake-conn"]  # default warehouse secret
    cfg = sink["config"]
    assert cfg["snowflake.url.name"] == "${SNOWFLAKE_ACCOUNT}.snowflakecomputing.com"
    assert cfg["snowflake.private.key"] == "${SNOWFLAKE_PRIVATE_KEY}"
    assert cfg["value.converter"].endswith("SnowflakeJsonConverter")
    assert cfg["tasks.max"] == "1"


def test_warehouse_secret_override_used():
    out = apply_analytics_platform(_ap_oam(warehouse_secret="prod-snowflake-conn"))
    assert _conn(out, "orders-sf-sink")["secretRefs"] == ["prod-snowflake-conn"]


def test_gateway_mode_skips_source_connector():
    out = apply_analytics_platform(_ap_oam(mode="gateway"))
    names = [c["name"] for c in _rtp(out)["properties"]["connectors"]]
    assert "orders-pg-source" not in names  # no source in gateway mode
    assert "orders-sf-sink" in names         # sink still present


# ----------------------------------------------------------------------
# processors
# ----------------------------------------------------------------------

def test_processors_from_features():
    feats = [
        {"name": "orders-hourly", "sql": "SELECT STREAM count(*) FROM cdc_orders"},
        {"name": "revenue", "sql": "SELECT STREAM sum(total) FROM cdc_orders"},
    ]
    out = apply_analytics_platform(_ap_oam(features=feats))
    procs = _rtp(out)["properties"]["processors"]
    assert [p["name"] for p in procs] == ["orders-hourly", "revenue"]
    assert procs[0]["sql"].startswith("SELECT STREAM")


def test_roundtrip_processor_appended():
    feats = [{"name": "orders-hourly", "sql": "SELECT STREAM count(*) FROM cdc_orders"}]
    out = apply_analytics_platform(
        _ap_oam(features=feats, roundtrip={"topic": "orders-live"}))
    procs = _rtp(out)["properties"]["processors"]
    rt = [p for p in procs if p["name"] == "orders-roundtrip"]
    assert rt and "INSERT INTO orders-live" in rt[0]["sql"]


# ----------------------------------------------------------------------
# topics
# ----------------------------------------------------------------------

def test_topics_deduped_and_complete():
    feats = [{"name": "orders-hourly", "sql": "x"}]
    out = apply_analytics_platform(_ap_oam(
        features=feats, roundtrip={"topic": "orders-live"},
        sink_topics=["cdc.public.orders"]))  # duplicate of a cdc topic
    names = [t["name"] for t in _rtp(out)["properties"]["topics"]]
    assert names == list(dict.fromkeys(names)), "no duplicate topics"
    assert "cdc.public.orders" in names
    assert "cdc.public.lineitems" in names
    assert "orders-hourly" in names
    assert "orders-live" in names


def test_topics_merge_into_existing_platform():
    existing = {"name": "mystream", "type": "realtime-platform",
                "properties": {"topics": [{"name": "cdc.public.orders"}]}}
    out = apply_analytics_platform(_ap_oam(extra_components=[existing]))
    names = [t["name"] for t in _rtp(out)["properties"]["topics"]]
    assert names.count("cdc.public.orders") == 1  # not re-added


# ----------------------------------------------------------------------
# idempotency
# ----------------------------------------------------------------------

def test_idempotent_rerun_no_duplicate_connectors():
    once = apply_analytics_platform(_ap_oam())
    twice = apply_analytics_platform(once)
    names = [c["name"] for c in _rtp(twice)["properties"]["connectors"]]
    assert names.count("orders-pg-source") == 1
    assert names.count("orders-sf-sink") == 1


# ----------------------------------------------------------------------
# realtime-service wiring (conservative)
# ----------------------------------------------------------------------

def test_gateway_realtime_service_consumes_roundtrip_topic():
    gw = {"name": "live-gw", "type": "realtime-service",
          "properties": {"name": "live-gw", "role": "gateway"}}
    out = apply_analytics_platform(_ap_oam(
        roundtrip={"topic": "orders-live"}, extra_components=[gw]))
    gw_out = next(c for c in out["spec"]["components"] if c["name"] == "live-gw")
    assert gw_out["properties"]["consumes"] == ["orders-live"]


def test_explicit_realtime_service_wiring_preserved():
    gw = {"name": "live-gw", "type": "realtime-service",
          "properties": {"name": "live-gw", "role": "gateway", "consumes": ["custom"]}}
    out = apply_analytics_platform(_ap_oam(
        roundtrip={"topic": "orders-live"}, extra_components=[gw]))
    gw_out = next(c for c in out["spec"]["components"] if c["name"] == "live-gw")
    assert gw_out["properties"]["consumes"] == ["custom"]  # untouched
