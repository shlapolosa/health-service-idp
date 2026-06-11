"""HARD-4 (#171) unit tests for the contract-test runner.

Covers the *mockable* logic — verdict formatting, env->config parsing, per-type
dispatch, role inference, and timeout behaviour with injected (fake) clients.
The real aiokafka/ws/http IO is behind the `Deps` seam so these tests need no
broker, no cluster, and no network. Run with:
    PYTHONPATH=.. /tmp/rtvenv/bin/python -m pytest -q
"""
import asyncio
import json

import pytest

import runner as r


# --------------------------------------------------------------------------- #
# Verdict formatting
# --------------------------------------------------------------------------- #
def test_verdict_json_shape_uses_pass_key():
    v = r.Verdict("comp-a", "webservice", "webservice-health", True, "ok")
    obj = json.loads(v.to_json())
    assert obj == {
        "component": "comp-a",
        "type": "webservice",
        "check": "webservice-health",
        "pass": True,
        "detail": "ok",
    }
    # single line, no spaces
    assert "\n" not in v.to_json()
    assert ", " not in v.to_json()


# --------------------------------------------------------------------------- #
# Config parsing + topic recovery + role inference
# --------------------------------------------------------------------------- #
def test_collect_topics_recovers_topic_names_from_values():
    env = {"CONSUME_sensor_raw": "sensor_raw", "PRODUCE_sensor_agg": "sensor_agg", "X": "y"}
    assert r._collect_topics("CONSUME_", env) == ["sensor_raw"]
    assert r._collect_topics("PRODUCE_", env) == ["sensor_agg"]


def test_infer_role_gateway_when_consume_produce_ws():
    env = {"CONSUME_a": "a", "PRODUCE_b": "b", "WEBSOCKET": "true"}
    assert r._infer_role(env) == "gateway"


def test_infer_role_ingest_when_produce_only():
    assert r._infer_role({"PRODUCE_b": "b"}) == "ingest"


def test_infer_role_processor_when_consume_produce_no_ws():
    env = {"CONSUME_a": "a", "PRODUCE_b": "b", "WEBSOCKET": "false"}
    assert r._infer_role(env) == "processor"


def test_load_config_apim_mode_prefers_apim_base():
    cfg = r.load_config({
        "CHECK_TYPE": "webservice",
        "COMPONENT_NAME": "svc1",
        "COMPONENT_NS": "default",
        "APIM_MODE": "true",
        "APIM_BASE_URL": "https://apim.example.com/svc/svc1",
        "KSVC_URL": "http://svc1.default.svc.cluster.local",
    })
    assert cfg.apim_mode is True
    assert cfg.ksvc_url == "https://apim.example.com/svc/svc1"


def test_load_config_cluster_url_default_when_not_apim():
    cfg = r.load_config({"CHECK_TYPE": "webservice", "COMPONENT_NAME": "svc1"})
    assert cfg.ksvc_url == "http://svc1.default.svc.cluster.local"


def test_load_config_realtime_infers_role_when_unset():
    cfg = r.load_config({
        "CHECK_TYPE": "realtime-service",
        "COMPONENT_NAME": "gw",
        "CONSUME_t1": "t1",
        "PRODUCE_t2": "t2",
        "WEBSOCKET": "true",
    })
    assert cfg.role == "gateway"
    assert cfg.consume_topics == ["t1"] and cfg.produce_topics == ["t2"]


def test_load_config_explicit_check_role_wins():
    cfg = r.load_config({
        "CHECK_TYPE": "realtime-service",
        "CHECK_ROLE": "processor",
        "CONSUME_t1": "t1",
        "PRODUCE_t2": "t2",
        "WEBSOCKET": "true",  # would infer gateway, but explicit role overrides
    })
    assert cfg.role == "processor"


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #
def _cfg(**kw):
    base = dict(component="c", ctype="webservice", namespace="default", role="",
                timeout=1.0, apim_mode=False, ksvc_url="http://c", ws_token="ct-probe",
                apim_subscription_key="", kafka_bootstrap="b:9092",
                consume_topics=[], produce_topics=[])
    base.update(kw)
    return r.Config(**base)


def test_select_check_dispatch_by_type_and_role():
    assert r.select_check(_cfg(ctype="webservice")) is r.check_webservice
    assert r.select_check(_cfg(ctype="graphql-gateway")) is r.check_graphql_gateway
    assert r.select_check(_cfg(ctype="realtime-service", role="gateway")) is r.check_realtime_gateway
    assert r.select_check(_cfg(ctype="realtime-service", role="ingest")) is r.check_realtime_ingest
    assert r.select_check(_cfg(ctype="realtime-service", role="processor")) is r.check_realtime_processor


def test_select_check_unknown_type_raises():
    with pytest.raises(ValueError):
        r.select_check(_cfg(ctype="mystery"))


def test_run_unknown_type_returns_failed_verdict_not_exception():
    v = asyncio.run(r.run(_cfg(ctype="mystery")))
    assert v.passed is False and v.check == "dispatch"


# --------------------------------------------------------------------------- #
# Per-type checks with injected fake clients
# --------------------------------------------------------------------------- #
def _await(coro):
    return asyncio.run(coro)


def test_webservice_pass_on_200():
    async def http_get(cfg, path):
        assert path == "/health"
        return 200
    deps = r.Deps(http_get=http_get)
    v = _await(r.check_webservice(_cfg(ctype="webservice"), deps))
    assert v.passed is True and "200" in v.detail


def test_webservice_fail_on_503():
    async def http_get(cfg, path):
        return 503
    v = _await(r.check_webservice(_cfg(ctype="webservice"), r.Deps(http_get=http_get)))
    assert v.passed is False


def test_webservice_timeout_is_failed_verdict():
    async def http_get(cfg, path):
        await asyncio.sleep(5)
        return 200
    cfg = _cfg(ctype="webservice", timeout=0.1)
    v = _await(r.check_webservice(cfg, r.Deps(http_get=http_get)))
    assert v.passed is False and "timed out" in v.detail


def test_graphql_pass_when_data_present():
    async def post(cfg, query):
        assert "__schema" in query
        return True
    v = _await(r.check_graphql_gateway(_cfg(ctype="graphql-gateway"), r.Deps(http_post_graphql=post)))
    assert v.passed is True


def test_graphql_fail_when_no_data():
    async def post(cfg, query):
        return False
    v = _await(r.check_graphql_gateway(_cfg(ctype="graphql-gateway"), r.Deps(http_post_graphql=post)))
    assert v.passed is False


def test_realtime_gateway_roundtrip_pass():
    produced = {}

    async def produce(cfg, topic, payload):
        produced["topic"] = topic
        produced["marker"] = payload["marker_id"]

    async def ws_recv(cfg, marker):
        # simulate the broadcast arriving
        return True

    cfg = _cfg(ctype="realtime-service", role="gateway", consume_topics=["sensor_raw"], timeout=2.0)
    v = _await(r.check_realtime_gateway(cfg, r.Deps(ws_recv=ws_recv, kafka_produce=produce)))
    assert v.passed is True
    assert produced["topic"] == "sensor_raw"
    assert produced["marker"] in v.detail


def test_realtime_gateway_fail_when_ws_never_receives():
    async def produce(cfg, topic, payload):
        return None

    async def ws_recv(cfg, marker):
        return False

    cfg = _cfg(ctype="realtime-service", role="gateway", consume_topics=["sensor_raw"], timeout=1.0)
    v = _await(r.check_realtime_gateway(cfg, r.Deps(ws_recv=ws_recv, kafka_produce=produce)))
    assert v.passed is False


def test_realtime_gateway_no_consume_topic_fails():
    cfg = _cfg(ctype="realtime-service", role="gateway", consume_topics=[])
    v = _await(r.check_realtime_gateway(cfg, r.Deps()))
    assert v.passed is False and "CONSUME" in v.detail


def test_realtime_ingest_offset_advance_pass():
    calls = {"n": 0}

    async def end_offsets(cfg, topic):
        calls["n"] += 1
        return 5 if calls["n"] == 1 else 6  # before=5, after=6

    async def http_get(cfg, path):
        assert path == "/ingest"
        return 202

    cfg = _cfg(ctype="realtime-service", role="ingest", produce_topics=["sensor_raw"], timeout=2.0)
    v = _await(r.check_realtime_ingest(cfg, r.Deps(end_offsets=end_offsets, http_get=http_get)))
    assert v.passed is True and "5->6" in v.detail


def test_realtime_ingest_fail_when_no_advance():
    async def end_offsets(cfg, topic):
        return 7

    async def http_get(cfg, path):
        return 202

    cfg = _cfg(ctype="realtime-service", role="ingest", produce_topics=["sensor_raw"], timeout=2.0)
    v = _await(r.check_realtime_ingest(cfg, r.Deps(end_offsets=end_offsets, http_get=http_get)))
    assert v.passed is False


def test_realtime_processor_transform_pass():
    async def produce(cfg, topic, payload):
        return None

    async def consume_match(cfg, topic, marker_id):
        assert topic == "sensor_agg"
        return True

    cfg = _cfg(ctype="realtime-service", role="processor",
               consume_topics=["sensor_raw"], produce_topics=["sensor_agg"], timeout=2.0)
    v = _await(r.check_realtime_processor(cfg, r.Deps(kafka_produce=produce, kafka_consume_match=consume_match)))
    assert v.passed is True


def test_realtime_processor_fail_when_no_transformed_message():
    async def produce(cfg, topic, payload):
        return None

    async def consume_match(cfg, topic, marker_id):
        return False

    cfg = _cfg(ctype="realtime-service", role="processor",
               consume_topics=["sensor_raw"], produce_topics=["sensor_agg"], timeout=1.0)
    v = _await(r.check_realtime_processor(cfg, r.Deps(kafka_produce=produce, kafka_consume_match=consume_match)))
    assert v.passed is False


def test_run_wraps_client_errors_as_failed_verdict():
    async def http_get(cfg, path):
        raise RuntimeError("connection refused")

    cfg = _cfg(ctype="webservice", timeout=1.0)
    v = _await(r.run(cfg, r.Deps(http_get=http_get)))
    assert v.passed is False and "connection refused" in v.detail


def test_ws_url_apim_mode_adds_subscription_key():
    cfg = _cfg(ctype="realtime-service", role="gateway",
               apim_mode=True, ksvc_url="https://apim.example.com/svc/gw",
               apim_subscription_key="k123", ws_token="ct-probe")
    url = r._ws_url(cfg)
    assert url.startswith("wss://apim.example.com/svc/gw/ws?")
    assert "token=ct-probe" in url and "subscription-key=k123" in url


def test_ws_url_incluster_uses_ws_scheme_no_key():
    cfg = _cfg(ctype="realtime-service", role="gateway",
               ksvc_url="http://gw.default.svc.cluster.local")
    url = r._ws_url(cfg)
    assert url.startswith("ws://gw.default.svc.cluster.local/ws?")
    assert "subscription-key" not in url


# --- aggregate-topic fallback (live finding: per-topic vars live on the ksvc env,
# not in the -conn secret; the sensor passes gjson-extracted aggregates) ----------

def test_collect_topics_aggregate_json_array():
    env = {"CONSUME_TOPICS": '["sensor_agg","other"]'}
    assert r._collect_topics("CONSUME_", env) == ["other", "sensor_agg"]


def test_collect_topics_aggregate_comma():
    env = {"PRODUCE_TOPICS": "a, b"}
    assert r._collect_topics("PRODUCE_", env) == ["a", "b"]


def test_collect_topics_aggregate_not_treated_as_per_topic():
    # CONSUME_TOPICS itself starts with CONSUME_ — its raw value must not leak in.
    env = {"CONSUME_TOPICS": '["sensor_agg"]', "CONSUME_x": "x"}
    assert r._collect_topics("CONSUME_", env) == ["sensor_agg", "x"]


def test_infer_role_websocket_from_sensor_env():
    env = {"CONSUME_TOPICS": '["sensor_agg"]', "WEBSOCKET": '"true"'}
    assert r._infer_role(env) == "gateway"
