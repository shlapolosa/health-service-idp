"""Unit tests for Argo Workflows client."""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.infrastructure.argo_client import ArgoWorkflowsClient


class TestArgoWorkflowsClient:
    """Test Argo Workflows client implementation."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = ArgoWorkflowsClient(
            server_url="https://test-argo-server:2746",
            namespace="argo",
            token_file="/tmp/test-token"
        )
    
    def test_create_workflow_from_template_mock_mode(self, monkeypatch):
        """Test create_workflow_from_template in mock mode."""
        # Ensure mock mode is enabled
        monkeypatch.setenv("ARGO_USE_MOCK", "true")
        
        parameters = {
            "resource-name": "test-service",
            "resource-type": "microservice",
            "namespace": "default",
            "user": "test-user"
        }
        
        result = self.client.create_workflow_from_template(
            workflow_template_name="microservice-standard-contract",
            parameters=parameters,
            namespace="argo"
        )
        
        # Verify mock response structure
        assert "metadata" in result
        assert "name" in result["metadata"]
        assert result["metadata"]["name"].startswith("microservice-standard-contract-")
        assert result["metadata"]["namespace"] == "argo"
        assert "uid" in result["metadata"]
        
        assert "spec" in result
        assert result["spec"]["workflowTemplateRef"]["name"] == "microservice-standard-contract"
        
        assert "status" in result
        assert result["status"]["phase"] == "Running"
        
        # Verify parameters are included
        param_names = [p["name"] for p in result["spec"]["arguments"]["parameters"]]
        assert "resource-name" in param_names
        assert "resource-type" in param_names
    
    @patch('src.infrastructure.argo_client.requests.post')
    def test_create_workflow_from_template_real_mode_success(self, mock_post, monkeypatch):
        """Test create_workflow_from_template with successful API call."""
        # Disable mock mode
        monkeypatch.setenv("ARGO_USE_MOCK", "false")
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "metadata": {
                "name": "microservice-standard-contract-abc123",
                "namespace": "argo",
                "uid": "test-uid-123"
            },
            "spec": {
                "workflowTemplateRef": {
                    "name": "microservice-standard-contract"
                }
            },
            "status": {
                "phase": "Pending"
            }
        }
        mock_post.return_value = mock_response
        
        parameters = {
            "resource-name": "test-service",
            "resource-type": "microservice"
        }
        
        result = self.client.create_workflow_from_template(
            workflow_template_name="microservice-standard-contract",
            parameters=parameters
        )
        
        # Verify API was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL
        assert call_args[0][0] == "https://test-argo-server:2746/api/v1/workflows/argo"
        
        # Check request body
        request_body = call_args[1]["json"]
        assert request_body["namespace"] == "argo"
        assert request_body["workflow"]["spec"]["workflowTemplateRef"]["name"] == "microservice-standard-contract"
        
        # Check parameters were passed
        param_dict = {p["name"]: p["value"] for p in request_body["workflow"]["spec"]["arguments"]["parameters"]}
        assert param_dict["resource-name"] == "test-service"
        assert param_dict["resource-type"] == "microservice"
        
        # Verify response
        assert result["metadata"]["name"] == "microservice-standard-contract-abc123"
        assert result["status"]["phase"] == "Pending"
    
    @patch('src.infrastructure.argo_client.requests.post')
    def test_create_workflow_from_template_real_mode_failure(self, mock_post, monkeypatch):
        """Test create_workflow_from_template with API failure."""
        # Disable mock mode
        monkeypatch.setenv("ARGO_USE_MOCK", "false")
        
        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden: insufficient permissions"
        mock_post.return_value = mock_response
        
        parameters = {"resource-name": "test-service"}
        
        result = self.client.create_workflow_from_template(
            workflow_template_name="test-template",
            parameters=parameters
        )
        
        # Should return mock response with error info
        assert result["status"]["phase"] == "Failed"
        assert "Forbidden" in result["status"]["message"]
        assert "error" in result["metadata"]
    
    @patch('src.infrastructure.argo_client.requests.post')
    def test_create_workflow_from_template_connection_error(self, mock_post, monkeypatch):
        """Test create_workflow_from_template with connection error."""
        # Disable mock mode
        monkeypatch.setenv("ARGO_USE_MOCK", "false")
        
        # Mock connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        parameters = {"resource-name": "test-service"}
        
        result = self.client.create_workflow_from_template(
            workflow_template_name="test-template",
            parameters=parameters
        )
        
        # Should return mock response with error info
        assert result["status"]["phase"] == "Failed"
        assert "Connection refused" in result["status"]["message"]
        assert "error" in result["metadata"]
    
    def test_create_workflow_all_parameter_types(self, monkeypatch):
        """Test that all parameter types are correctly handled."""
        monkeypatch.setenv("ARGO_USE_MOCK", "true")
        
        parameters = {
            # Tier 1: Universal
            "resource-name": "test-service",
            "resource-type": "microservice",
            "namespace": "default",
            "user": "test-user",
            "description": "Test microservice",
            "github-org": "test-org",
            "docker-registry": "docker.io/test",
            "slack-channel": "#test",
            "slack-user-id": "U123",
            # Tier 2: Platform
            "security-enabled": "true",
            "observability-enabled": "true",
            "backup-enabled": "false",
            "environment-tier": "development",
            "auto-create-dependencies": "true",
            "resource-size": "medium",
            # Tier 3: Microservice-specific
            "microservice-language": "python",
            "microservice-framework": "fastapi",
            "microservice-database": "postgres",
            "microservice-cache": "redis",
            "microservice-expose-api": "true",
            "target-vcluster": "test-vcluster",
            "parent-appcontainer": "test-container",
            "repository-name": "test-repo"
        }
        
        result = self.client.create_workflow_from_template(
            workflow_template_name="microservice-standard-contract",
            parameters=parameters
        )
        
        # Verify all parameters are in the result
        param_dict = {p["name"]: p["value"] for p in result["spec"]["arguments"]["parameters"]}
        
        for key, value in parameters.items():
            assert key in param_dict
            assert param_dict[key] == value
    
    @patch('src.infrastructure.argo_client.requests.post')
    def test_trigger_microservice_creation(self, mock_post, monkeypatch):
        """Test trigger_microservice_creation method."""
        monkeypatch.setenv("ARGO_USE_MOCK", "false")
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "metadata": {"name": "microservice-workflow-123"},
            "status": {"phase": "Running"}
        }
        mock_post.return_value = mock_response
        
        payload = {
            "microservice-name": "test-service",
            "language": "python",
            "framework": "fastapi",
            "database": "postgres",
            "cache": "redis",
            "namespace": "default",
            "user": "test-user",
            "github-org": "test-org",
            "docker-registry": "docker.io/test",
            "slack-channel": "#test",
            "slack-user-id": "U123"
        }
        
        success, message = self.client.trigger_microservice_creation(payload)
        
        assert success is True
        assert "workflow started" in message.lower()
    
    def test_get_auth_headers_with_token(self, monkeypatch, tmp_path):
        """Test _get_auth_headers with token file."""
        # Create temporary token file
        token_file = tmp_path / "token"
        token_file.write_text("test-token-123")
        
        client = ArgoWorkflowsClient(
            server_url="https://test-server",
            namespace="argo",
            token_file=str(token_file)
        )
        
        headers = client._get_auth_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer test-token-123"
    
    def test_get_auth_headers_without_token(self):
        """Test _get_auth_headers without token file."""
        client = ArgoWorkflowsClient(
            server_url="https://test-server",
            namespace="argo",
            token_file="/nonexistent/token"
        )
        
        headers = client._get_auth_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers