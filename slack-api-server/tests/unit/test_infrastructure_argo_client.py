"""
Unit tests for Argo Workflows client
"""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from src.infrastructure.argo_client import ArgoWorkflowsClient


class TestArgoWorkflowsClient:
    """Test ArgoWorkflowsClient infrastructure service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = ArgoWorkflowsClient(
            server_url="http://argo-server.argo:2746", 
            namespace="argo", 
            timeout=30,
            token_file=None  # No token file for tests
        )

    def test_initialization(self):
        """Test ArgoWorkflowsClient initialization."""
        assert self.client.server_url == "http://argo-server.argo:2746"
        assert self.client.namespace == "argo"
        assert self.client.timeout == 30
        assert self.client.base_url == "http://argo-server.argo:2746/api/v1"

    def test_initialization_with_trailing_slash(self):
        """Test ArgoWorkflowsClient initialization with trailing slash in URL."""
        client = ArgoWorkflowsClient(
            server_url="http://argo-server.argo:2746/", 
            namespace="argo",
            token_file=None
        )
        assert client.server_url == "http://argo-server.argo:2746"
        assert client.base_url == "http://argo-server.argo:2746/api/v1"

    @patch('src.infrastructure.argo_client.requests.post')
    def test_trigger_vcluster_creation_success(self, mock_post):
        """Test successful VCluster creation via Argo Workflows."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "metadata": {"name": "vcluster-creation-abc123"},
            "status": {"phase": "Pending"}
        }
        mock_post.return_value = mock_response

        payload = {
            "client_payload": {
                "vcluster_name": "test-cluster",
                "namespace": "default",
                "user": "testuser",
                "slack_channel": "C123",
                "slack_user_id": "U123",
                "capabilities": {"observability": "true", "security": "true"},
                "resources": {"cpu_limit": "2000m", "memory_limit": "4Gi", "node_count": "3"}
            }
        }

        success, message = self.client.trigger_vcluster_creation(payload)

        assert success is True
        assert "VCluster creation workflow started: vcluster-creation-abc123" in message

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://argo-server.argo:2746/api/v1/workflows/argo"
        
        # Verify workflow spec structure
        workflow_spec = call_args[1]["json"]
        assert workflow_spec["namespace"] == "argo"
        assert workflow_spec["workflow"]["spec"]["workflowTemplateRef"]["name"] == "vcluster-creation"
        
        # Verify parameters
        params = {p["name"]: p["value"] for p in workflow_spec["workflow"]["spec"]["arguments"]["parameters"]}
        assert params["vcluster-name"] == "test-cluster"
        assert params["namespace"] == "default"
        assert params["user"] == "testuser"
        assert params["slack-channel"] == "C123"
        assert params["slack-user-id"] == "U123"

    @patch('src.infrastructure.argo_client.requests.post')
    def test_trigger_appcontainer_creation_success(self, mock_post):
        """Test successful AppContainer creation via Argo Workflows."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "metadata": {"name": "appcontainer-creation-def456"},
            "status": {"phase": "Pending"}
        }
        mock_post.return_value = mock_response

        payload = {
            "appcontainer-name": "my-app",
            "namespace": "production",
            "description": "Test application container",
            "github-org": "testorg",
            "docker-registry": "registry.test.com/testorg",
            "observability": "true",
            "security": "false",
            "user": "alice",
            "slack-channel": "C456",
            "slack-user-id": "U456"
        }

        success, message = self.client.trigger_appcontainer_creation(payload)

        assert success is True
        assert "AppContainer creation workflow started: appcontainer-creation-def456" in message

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Verify workflow spec structure
        workflow_spec = call_args[1]["json"]
        assert workflow_spec["workflow"]["spec"]["workflowTemplateRef"]["name"] == "appcontainer-creation"
        
        # Verify parameters
        params = {p["name"]: p["value"] for p in workflow_spec["workflow"]["spec"]["arguments"]["parameters"]}
        assert params["appcontainer-name"] == "my-app"
        assert params["namespace"] == "production"
        assert params["description"] == "Test application container"
        assert params["github-org"] == "testorg"
        assert params["docker-registry"] == "registry.test.com/testorg"
        assert params["observability"] == "true"
        assert params["security"] == "false"

    @patch('src.infrastructure.argo_client.requests.post')
    def test_trigger_microservice_creation_success(self, mock_post):
        """Test successful Microservice creation via Argo Workflows."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "metadata": {"name": "microservice-creation-ghi789"},
            "status": {"phase": "Pending"}
        }
        mock_post.return_value = mock_response

        payload = {
            "microservice-name": "user-service",
            "namespace": "production",
            "language": "java",
            "database": "postgres",  # Note: should be postgres (mapped from postgresql)
            "cache": "redis",
            "description": "User management service",
            "github-org": "ecommerce",
            "docker-registry": "registry.ecommerce.com/services",
            "security": "true",
            "observability": "false",
            "target-vcluster": "prod-cluster",
            "auto-create-vcluster": "false",
            "user": "bob",
            "slack-channel": "C789",
            "slack-user-id": "U789"
        }

        success, message = self.client.trigger_microservice_creation(payload)

        assert success is True
        assert "Microservice creation workflow started: microservice-creation-ghi789" in message

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Verify workflow spec structure uses microservice-standard-contract template
        workflow_spec = call_args[1]["json"]
        assert workflow_spec["workflow"]["spec"]["workflowTemplateRef"]["name"] == "microservice-standard-contract"
        
        # Verify 4-tier standardized contract parameters
        params = {p["name"]: p["value"] for p in workflow_spec["workflow"]["spec"]["arguments"]["parameters"]}
        
        # TIER 1: Universal Parameters
        assert params["resource-name"] == "user-service"
        assert params["resource-type"] == "microservice"
        assert params["namespace"] == "production"
        assert params["user"] == "bob"
        assert params["description"] == "User management service"
        assert params["github-org"] == "ecommerce"
        assert params["docker-registry"] == "registry.ecommerce.com/services"
        assert params["slack-channel"] == "C789"
        assert params["slack-user-id"] == "U789"
        
        # TIER 2: Platform Parameters
        assert params["security-enabled"] == "true"
        assert params["observability-enabled"] == "false"
        assert params["backup-enabled"] == "false"
        assert params["environment-tier"] == "development"
        assert params["auto-create-dependencies"] == "false"
        assert params["resource-size"] == "medium"
        
        # TIER 3: Microservice-Specific Parameters
        assert params["microservice-language"] == "java"
        assert params["microservice-framework"] == "auto"
        assert params["microservice-database"] == "postgres"
        assert params["microservice-cache"] == "redis"
        assert params["microservice-expose-api"] == "false"
        assert params["target-vcluster"] == "prod-cluster"
        assert params["parent-appcontainer"] == ""

    @patch('src.infrastructure.argo_client.requests.post')
    def test_trigger_microservice_creation_database_mapping(self, mock_post):
        """Test that database values are properly mapped in microservice creation."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"metadata": {"name": "microservice-creation-test"}}
        mock_post.return_value = mock_response

        # Test with different database values
        test_cases = [
            {"input": "postgres", "expected": "postgres"},
            {"input": "none", "expected": "none"},
        ]

        for case in test_cases:
            payload = {
                "microservice-name": "test-service",
                "database": case["input"],
                "user": "testuser",
                "slack-channel": "C123",
                "slack-user-id": "U123"
            }

            self.client.trigger_microservice_creation(payload)
            
            # Get the last call arguments
            call_args = mock_post.call_args
            workflow_spec = call_args[1]["json"]
            params = {p["name"]: p["value"] for p in workflow_spec["workflow"]["spec"]["arguments"]["parameters"]}
            
            assert params["microservice-database"] == case["expected"]

    @patch('src.infrastructure.argo_client.requests.post')
    def test_trigger_creation_http_error(self, mock_post):
        """Test Argo Workflows HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        payload = {"client_payload": {"vcluster_name": "test-cluster"}}

        success, message = self.client.trigger_vcluster_creation(payload)

        assert success is False
        assert "Argo Workflows API error: 500 - Internal Server Error" in message

    @patch('src.infrastructure.argo_client.requests.post')
    def test_trigger_creation_timeout(self, mock_post):
        """Test Argo Workflows timeout handling."""
        mock_post.side_effect = requests.exceptions.Timeout()

        payload = {"client_payload": {"vcluster_name": "test-cluster"}}

        success, message = self.client.trigger_vcluster_creation(payload)

        assert success is False
        assert "Argo Workflows API request timed out after 30 seconds" in message

    @patch('src.infrastructure.argo_client.requests.post')
    def test_trigger_creation_connection_error(self, mock_post):
        """Test Argo Workflows connection error handling."""
        mock_post.side_effect = requests.exceptions.ConnectionError()

        payload = {"client_payload": {"vcluster_name": "test-cluster"}}

        success, message = self.client.trigger_vcluster_creation(payload)

        assert success is False
        assert "Failed to connect to Argo Workflows API" in message

    @patch('src.infrastructure.argo_client.requests.post')
    def test_trigger_creation_request_exception(self, mock_post):
        """Test Argo Workflows request exception handling."""
        mock_post.side_effect = requests.RequestException("Network error")

        payload = {"client_payload": {"vcluster_name": "test-cluster"}}

        success, message = self.client.trigger_vcluster_creation(payload)

        assert success is False
        assert "Argo Workflows API request failed: Network error" in message

    @patch('src.infrastructure.argo_client.requests.post')
    def test_trigger_creation_unexpected_error(self, mock_post):
        """Test Argo Workflows unexpected error handling."""
        mock_post.side_effect = Exception("Unexpected error")

        payload = {"client_payload": {"vcluster_name": "test-cluster"}}

        success, message = self.client.trigger_vcluster_creation(payload)

        assert success is False
        assert "Unexpected error calling Argo Workflows API: Unexpected error" in message

    @patch('src.infrastructure.argo_client.requests.get')
    def test_validate_configuration_success(self, mock_get):
        """Test successful Argo Workflows configuration validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        is_valid, message = self.client.validate_configuration()

        assert is_valid is True
        assert message == "Argo Workflows configuration valid"

        mock_get.assert_called_once_with(
            "http://argo-server.argo:2746/api/v1/info",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=30,
            verify=False
        )

    @patch('src.infrastructure.argo_client.requests.get')
    def test_validate_configuration_http_error(self, mock_get):
        """Test Argo Workflows configuration validation with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        is_valid, message = self.client.validate_configuration()

        assert is_valid is False
        assert "Argo Workflows API returned status 404" in message

    @patch('src.infrastructure.argo_client.requests.get')
    def test_validate_configuration_exception(self, mock_get):
        """Test Argo Workflows configuration validation with exception."""
        mock_get.side_effect = Exception("Connection failed")

        is_valid, message = self.client.validate_configuration()

        assert is_valid is False
        assert "Failed to validate Argo Workflows configuration: Connection failed" in message

    def test_validate_configuration_missing_server_url(self):
        """Test configuration validation with missing server URL."""
        client = ArgoWorkflowsClient(server_url="", namespace="argo", token_file=None)

        is_valid, message = client.validate_configuration()

        assert is_valid is False
        assert message == "Argo Workflows server URL not configured"

    def test_extract_size_from_resources(self):
        """Test size extraction from resource specifications."""
        test_cases = [
            {"cpu_limit": "1000m", "expected": "small"},
            {"cpu_limit": "2000m", "expected": "medium"},
            {"cpu_limit": "4000m", "expected": "large"},
            {"cpu_limit": "8000m", "expected": "xlarge"},
            {"cpu_limit": "3000m", "expected": "medium"},  # Default case
        ]

        for case in test_cases:
            client_payload = {
                "resources": {"cpu_limit": case["cpu_limit"]}
            }
            result = self.client._extract_size_from_resources(client_payload)
            assert result == case["expected"]

    def test_extract_size_from_resources_no_resources(self):
        """Test size extraction when no resources are provided."""
        client_payload = {}
        result = self.client._extract_size_from_resources(client_payload)
        assert result == "medium"  # Default

    @patch('src.infrastructure.argo_client.requests.get')
    def test_get_workflow_status_success(self, mock_get):
        """Test successful workflow status retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": {
                "phase": "Succeeded",
                "startedAt": "2023-01-01T12:00:00Z",
                "finishedAt": "2023-01-01T12:05:00Z"
            }
        }
        mock_get.return_value = mock_response

        success, status = self.client.get_workflow_status("test-workflow")

        assert success is True
        assert status["phase"] == "Succeeded"
        assert "startedAt" in status
        assert "finishedAt" in status

        mock_get.assert_called_once_with(
            "http://argo-server.argo:2746/api/v1/workflows/argo/test-workflow",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=30,
            verify=False
        )

    @patch('src.infrastructure.argo_client.requests.get')
    def test_get_workflow_status_not_found(self, mock_get):
        """Test workflow status retrieval for non-existent workflow."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        success, result = self.client.get_workflow_status("non-existent-workflow")

        assert success is False
        assert "Failed to get workflow status: 404" in result["error"]

    @patch('src.infrastructure.argo_client.requests.get')
    def test_get_workflow_status_exception(self, mock_get):
        """Test workflow status retrieval with exception."""
        mock_get.side_effect = Exception("Network error")

        success, result = self.client.get_workflow_status("test-workflow")

        assert success is False
        assert "Error getting workflow status: Network error" in result["error"]

    def test_get_auth_headers_no_token_file(self):
        """Test auth headers when no token file is configured."""
        client = ArgoWorkflowsClient(
            server_url="http://argo-server.argo:2746",
            namespace="argo",
            token_file=None
        )
        
        headers = client._get_auth_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "Authorization" not in headers

    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_get_auth_headers_with_token_file(self, mock_exists, mock_open):
        """Test auth headers when token file exists."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "test-token-123"
        
        client = ArgoWorkflowsClient(
            server_url="http://argo-server.argo:2746",
            namespace="argo",
            token_file="/var/run/secrets/argo/token"
        )
        
        headers = client._get_auth_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert headers["Authorization"] == "Bearer test-token-123"

    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_get_auth_headers_empty_token_file(self, mock_exists, mock_open):
        """Test auth headers when token file is empty."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "   "
        
        client = ArgoWorkflowsClient(
            server_url="http://argo-server.argo:2746",
            namespace="argo",
            token_file="/var/run/secrets/argo/token"
        )
        
        headers = client._get_auth_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "Authorization" not in headers

    @patch('os.path.exists')
    def test_get_auth_headers_missing_token_file(self, mock_exists):
        """Test auth headers when token file doesn't exist."""
        mock_exists.return_value = False
        
        client = ArgoWorkflowsClient(
            server_url="http://argo-server.argo:2746",
            namespace="argo",
            token_file="/var/run/secrets/argo/token"
        )
        
        headers = client._get_auth_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "Authorization" not in headers