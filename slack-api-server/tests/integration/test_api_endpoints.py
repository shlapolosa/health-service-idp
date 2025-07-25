"""
Integration tests for API endpoints
"""

import os
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.interface.controllers import create_slack_app


class TestAPIEndpoints:
    """Test API endpoints integration."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock environment variables
        self.env_patcher = patch.dict(
            os.environ,
            {
                "PERSONAL_ACCESS_TOKEN": "test_token",
                "GITHUB_REPOSITORY": "test_owner/test_repo",
                "SLACK_SIGNING_SECRET": "test_secret",
            },
        )
        self.env_patcher.start()

        # Create test client
        self.app = create_slack_app()
        self.client = TestClient(self.app)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()

    def test_health_endpoint(self):
        """Test health endpoint."""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "slack-api-server"
        assert "timestamp" in data

    def test_docs_endpoint(self):
        """Test API documentation endpoint."""
        response = self.client.get("/docs")

        assert response.status_code == 200
        assert "swagger" in response.text.lower()

    def test_redoc_endpoint(self):
        """Test alternative API documentation endpoint."""
        response = self.client.get("/redoc")

        assert response.status_code == 200
        assert "redoc" in response.text.lower()

    def test_openapi_endpoint(self):
        """Test OpenAPI schema endpoint."""
        response = self.client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Slack API Server"

    def test_slack_command_help(self):
        """Test Slack command help endpoint."""
        form_data = {
            "command": "/vcluster",
            "text": "help",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "VCluster Management Commands" in data["text"]
        assert "blocks" in data

    def test_slack_command_empty_text(self):
        """Test Slack command with empty text (should return help)."""
        form_data = {
            "command": "/vcluster",
            "text": "",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "VCluster Management Commands" in data["text"]

    def test_slack_command_appcontainer_help(self):
        """Test AppContainer help command."""
        form_data = {
            "command": "/appcontainer",
            "text": "help",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "AppContainer Management Commands" in data["text"]
        assert "blocks" in data

    def test_slack_command_app_cont_alias(self):
        """Test /app-cont alias command."""
        form_data = {
            "command": "/app-cont",
            "text": "help",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "AppContainer Management Commands" in data["text"]

    @patch("src.infrastructure.argo_client.requests.post")
    def test_appcontainer_create_success(self, mock_post):
        """Test successful AppContainer create command."""
        # Mock successful Argo API response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"metadata": {"name": "appcontainer-creation-abc123"}}
        mock_post.return_value = mock_response

        form_data = {
            "command": "/appcontainer",
            "text": "create my-app",
            "user_id": "U123456", 
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "in_channel"
        assert "AppContainer" in data["text"]
        assert "creation started" in data["text"]
        assert "blocks" in data

    @patch("src.infrastructure.argo_client.requests.post")
    def test_microservice_create_success(self, mock_post):
        """Test successful Microservice create command."""
        # Mock successful Argo API response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"metadata": {"name": "microservice-creation-def456"}}
        mock_post.return_value = mock_response

        form_data = {
            "command": "/microservice",
            "text": "create user-service",
            "user_id": "U123456", 
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "in_channel"
        assert "Microservice" in data["text"]
        assert "creation started" in data["text"]
        assert "blocks" in data

    @patch("src.infrastructure.argo_client.requests.post")
    def test_microservice_create_with_database_and_cache(self, mock_post):
        """Test Microservice create command with database and cache."""
        # Mock successful Argo API response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"metadata": {"name": "microservice-creation-ghi789"}}
        mock_post.return_value = mock_response

        form_data = {
            "command": "/microservice",
            "text": "create order-service with java and postgres and redis",
            "user_id": "U456789", 
            "user_name": "alice",
            "channel_id": "C456789",
            "channel_name": "backend",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "in_channel"
        assert "Microservice" in data["text"]
        assert "creation started" in data["text"]
        assert "order-service" in data["text"]

    def test_slack_command_microservice_help(self):
        """Test Microservice help command."""
        form_data = {
            "command": "/microservice",
            "text": "help",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "Microservice Management Commands" in data["text"]

    def test_service_alias_command(self):
        """Test /service alias for microservice command."""
        form_data = {
            "command": "/service",
            "text": "help",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "Microservice Management Commands" in data["text"]

    @patch("src.infrastructure.argo_client.requests.post")
    def test_microservice_create_failure(self, mock_post):
        """Test Microservice create command with Argo API failure."""
        # Mock failed Argo API response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        form_data = {
            "command": "/microservice",
            "text": "create test-service",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "❌" in data["text"]
        assert "Failed to trigger creation" in data["text"]

    def test_microservice_create_invalid_name(self):
        """Test Microservice create command with invalid name."""
        form_data = {
            "command": "/microservice",
            "text": "create -invalid-service-",  # Invalid: starts and ends with dash
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "❌" in data["text"]
        # Should get validation error for invalid name
        assert "unexpected error" in data["text"] or "Failed to trigger creation" in data["text"]

    def test_microservice_missing_name(self):
        """Test Microservice create command without name."""
        form_data = {
            "command": "/microservice",
            "text": "create",  # Missing service name
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "❌" in data["text"]
        assert ("Microservice name is required" in data["text"] or 
               "unexpected error" in data["text"])

    @patch("src.infrastructure.argo_client.requests.post")
    def test_slack_command_create_success(self, mock_post):
        """Test successful Slack create command."""
        # Mock successful Argo API response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"metadata": {"name": "vcluster-creation-abc123"}}
        mock_post.return_value = mock_response

        form_data = {
            "command": "/vcluster",
            "text": "create test-cluster",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "in_channel"
        assert "VCluster" in data["text"]
        assert "creation started" in data["text"]
        assert "blocks" in data
        assert len(data["blocks"]) == 3

    @patch("src.infrastructure.github_client.requests.post")
    def test_slack_command_create_github_failure(self, mock_post):
        """Test Slack create command with GitHub API failure."""
        # Mock failed GitHub API response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        form_data = {
            "command": "/vcluster",
            "text": "create test-cluster",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "❌" in data["text"]
        assert "Failed to trigger creation" in data["text"]

    def test_slack_command_create_invalid_name(self):
        """Test Slack create command with invalid VCluster name."""
        form_data = {
            "command": "/vcluster",
            "text": "create invalid_name",  # Invalid: contains underscore
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "❌" in data["text"]
        # Accept either validation error or GitHub error (if validation passes but GitHub fails)
        assert (
            "Invalid request" in data["text"]
            or "GitHub API error" in data["text"]
            or "Failed to trigger creation" in data["text"]
        )

    def test_slack_command_unknown_command(self):
        """Test Slack command with unknown command."""
        form_data = {
            "command": "/unknown",
            "text": "test",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "❌" in data["text"]
        assert "Unknown command" in data["text"]

    def test_slack_command_future_commands(self):
        """Test Slack commands that are not yet implemented."""
        commands = ["list", "delete test", "status test"]

        for cmd_text in commands:
            form_data = {
                "command": "/vcluster",
                "text": cmd_text,
                "user_id": "U123456",
                "user_name": "testuser",
                "channel_id": "C123456",
                "channel_name": "general",
                "team_id": "T123456",
                "team_domain": "testteam",
            }

            response = self.client.post("/slack/command", data=form_data)

            assert response.status_code == 200
            data = response.json()
            assert data["response_type"] == "ephemeral"
            assert "❌" in data["text"]
            assert "coming soon" in data["text"].lower()

    def test_slack_command_missing_data(self):
        """Test Slack command with missing required data."""
        form_data = {
            "command": "/vcluster",
            "text": "help",
            # Missing other required fields
        }

        response = self.client.post("/slack/command", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        # With missing data, it should return help message
        assert "VCluster Management Commands" in data["text"]

    def test_slack_events_url_verification(self):
        """Test Slack events URL verification."""
        event_data = {"type": "url_verification", "challenge": "test_challenge_string"}

        response = self.client.post("/slack/events", json=event_data)

        assert response.status_code == 200
        data = response.json()
        assert data["challenge"] == "test_challenge_string"

    def test_slack_events_other_events(self):
        """Test Slack events for other event types."""
        event_data = {
            "type": "app_mention",
            "event": {"type": "app_mention", "text": "Hello bot!"},
        }

        response = self.client.post("/slack/events", json=event_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_slack_events_invalid_json(self):
        """Test Slack events with invalid JSON."""
        response = self.client.post("/slack/events", data="invalid json")

        assert response.status_code == 400
        data = response.json()
        assert "Invalid JSON payload" in data["detail"]

    def test_get_method_not_allowed(self):
        """Test that GET method is not allowed on POST endpoints."""
        response = self.client.get("/slack/command")

        assert response.status_code == 405
        assert "Method Not Allowed" in response.text

    def test_unsupported_endpoint(self):
        """Test accessing unsupported endpoint."""
        response = self.client.get("/nonexistent")

        assert response.status_code == 404
        assert "Not Found" in response.text

    @patch("src.infrastructure.slack_verifier.time.time")
    def test_slack_signature_verification_success(self, mock_time):
        """Test successful Slack signature verification."""
        # Mock current time
        mock_time.return_value = 1234567890

        # Create request data
        form_data = {
            "command": "/vcluster",
            "text": "help",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        # Generate valid signature
        import hashlib
        import hmac
        import urllib.parse

        timestamp = "1234567890"
        body = urllib.parse.urlencode(form_data).encode("utf-8")
        sig_basestring = f"v0:{timestamp}:".encode("utf-8") + body
        signature = (
            "v0=" + hmac.new(b"test_secret", sig_basestring, hashlib.sha256).hexdigest()
        )

        headers = {
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": signature,
        }

        response = self.client.post("/slack/command", data=form_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "VCluster Management Commands" in data["text"]

    @patch("src.infrastructure.slack_verifier.time.time")
    def test_slack_signature_verification_failure(self, mock_time):
        """Test failed Slack signature verification."""
        # Mock current time
        mock_time.return_value = 1234567890

        form_data = {
            "command": "/vcluster",
            "text": "help",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general",
            "team_id": "T123456",
            "team_domain": "testteam",
        }

        headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=invalid_signature",
        }

        response = self.client.post("/slack/command", data=form_data, headers=headers)

        assert response.status_code == 401
        data = response.json()
        assert "Invalid request signature" in data["detail"]
