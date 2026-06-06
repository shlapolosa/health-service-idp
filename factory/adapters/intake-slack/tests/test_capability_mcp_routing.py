"""Unit tests for declarative-spine W6: /microservice routed via capability-mcp app.submit."""

import os
from unittest.mock import Mock, patch

import yaml

from src.infrastructure.argo_client import ArgoWorkflowsClient


def _client():
    return ArgoWorkflowsClient(server_url="https://test-argo:2746", namespace="argo",
                               token_file="/tmp/none")


PAYLOAD = {
    "microservice-name": "order-svc",
    "user": "socrates",
    "language": "java",
    "database": "postgres",
    "cache": "none",
    "namespace": "default",
    "target-vcluster": "team-a-vc",
}


class TestBuildOAM:
    def test_minimal_oam_shape(self):
        oam = yaml.safe_load(ArgoWorkflowsClient._build_oam_from_payload(PAYLOAD))
        assert oam["kind"] == "Application"
        assert oam["metadata"]["name"] == "order-svc"
        comp = oam["spec"]["components"][0]
        assert comp["type"] == "webservice"
        assert comp["properties"]["language"] == "java"
        assert comp["properties"]["database"] == "postgres"
        assert "cache" not in comp["properties"]  # 'none' filtered out
        assert comp["properties"]["targetEnvironment"] == "team-a-vc"
        assert oam["metadata"]["annotations"]["intake.cafe.io/source"] == "slack"

    def test_no_framework_emitted(self):
        # framework derivation is app.submit's job (single source of truth)
        oam = yaml.safe_load(ArgoWorkflowsClient._build_oam_from_payload(PAYLOAD))
        assert "framework" not in oam["spec"]["components"][0]["properties"]


class TestRouting:
    @patch.dict(os.environ, {"CAPABILITY_MCP_URL": "http://capability-mcp-mfg-tc.default.svc.cluster.local"})
    @patch("src.infrastructure.argo_client.requests.post")
    def test_routes_to_mcp_when_env_set(self, mock_post):
        mock_post.return_value = Mock(status_code=200, content=b"{}",
                                      json=lambda: {"ok": True, "workflow_name": "order-svc",
                                                    "message": "submitted"})
        ok, msg = _client().trigger_microservice_creation(PAYLOAD)
        assert ok
        assert "workflow started" in msg
        url = mock_post.call_args[0][0]
        assert url.endswith("/api/submit")
        body = mock_post.call_args.kwargs["json"]
        assert "oam_yaml" in body and "order-svc" in body["oam_yaml"]

    @patch.dict(os.environ, {"CAPABILITY_MCP_URL": "http://capability-mcp-mfg-tc.default.svc.cluster.local"})
    @patch("src.infrastructure.argo_client.requests.post")
    def test_mcp_error_surfaces_not_masked(self, mock_post):
        mock_post.return_value = Mock(status_code=422, content=b"{}",
                                      json=lambda: {"ok": False, "message": "validation failed: bad enum"})
        ok, msg = _client().trigger_microservice_creation(PAYLOAD)
        assert not ok
        assert "validation failed" in msg

    @patch.dict(os.environ, {}, clear=False)
    @patch("src.infrastructure.argo_client.requests.post")
    def test_legacy_wft_when_env_unset(self, mock_post):
        os.environ.pop("CAPABILITY_MCP_URL", None)
        mock_post.return_value = Mock(status_code=200,
                                      json=lambda: {"metadata": {"name": "microservice-creation-x"}})
        ok, msg = _client().trigger_microservice_creation(PAYLOAD)
        assert ok
        url = mock_post.call_args[0][0]
        assert "/workflows/argo" in url  # legacy Argo REST path
