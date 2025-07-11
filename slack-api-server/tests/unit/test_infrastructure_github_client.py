"""
Unit tests for infrastructure GitHub client
"""

import pytest
from unittest.mock import Mock, patch
import requests
from src.infrastructure.github_client import GitHubApiClient


class TestGitHubApiClient:
    """Test GitHubApiClient infrastructure service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = GitHubApiClient(
            token="test_token",
            repository="test_owner/test_repo",
            timeout=10
        )
    
    def test_initialization(self):
        """Test client initialization."""
        assert self.client.token == "test_token"
        assert self.client.repository == "test_owner/test_repo"
        assert self.client.timeout == 10
        assert self.client.base_url == "https://api.github.com"
    
    @patch('src.infrastructure.github_client.requests.post')
    def test_trigger_vcluster_creation_success(self, mock_post):
        """Test successful VCluster creation trigger."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        payload = {
            "event_type": "slack_create_vcluster",
            "client_payload": {
                "vcluster_name": "test-cluster",
                "namespace": "default",
                "user": "testuser"
            }
        }
        
        success, message = self.client.trigger_vcluster_creation(payload)
        
        assert success is True
        assert message == "VCluster creation triggered successfully"
        
        mock_post.assert_called_once_with(
            "https://api.github.com/repos/test_owner/test_repo/dispatches",
            headers={
                'Authorization': 'token test_token',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=10
        )
    
    @patch('src.infrastructure.github_client.requests.post')
    def test_trigger_vcluster_creation_http_error(self, mock_post):
        """Test VCluster creation trigger with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        payload = {"event_type": "slack_create_vcluster"}
        
        success, message = self.client.trigger_vcluster_creation(payload)
        
        assert success is False
        assert "GitHub API error: 401 - Unauthorized" in message
    
    @patch('src.infrastructure.github_client.requests.post')
    def test_trigger_vcluster_creation_timeout(self, mock_post):
        """Test VCluster creation trigger with timeout."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        payload = {"event_type": "slack_create_vcluster"}
        
        success, message = self.client.trigger_vcluster_creation(payload)
        
        assert success is False
        assert "GitHub API request timed out after 10 seconds" in message
    
    @patch('src.infrastructure.github_client.requests.post')
    def test_trigger_vcluster_creation_connection_error(self, mock_post):
        """Test VCluster creation trigger with connection error."""
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        payload = {"event_type": "slack_create_vcluster"}
        
        success, message = self.client.trigger_vcluster_creation(payload)
        
        assert success is False
        assert "Failed to connect to GitHub API" in message
    
    @patch('src.infrastructure.github_client.requests.post')
    def test_trigger_vcluster_creation_request_exception(self, mock_post):
        """Test VCluster creation trigger with request exception."""
        mock_post.side_effect = requests.RequestException("Test error")
        
        payload = {"event_type": "slack_create_vcluster"}
        
        success, message = self.client.trigger_vcluster_creation(payload)
        
        assert success is False
        assert "GitHub API request failed: Test error" in message
    
    @patch('src.infrastructure.github_client.requests.post')
    def test_trigger_vcluster_creation_unexpected_error(self, mock_post):
        """Test VCluster creation trigger with unexpected error."""
        mock_post.side_effect = Exception("Unexpected error")
        
        payload = {"event_type": "slack_create_vcluster"}
        
        success, message = self.client.trigger_vcluster_creation(payload)
        
        assert success is False
        assert "Unexpected error calling GitHub API: Unexpected error" in message
    
    @patch('src.infrastructure.github_client.requests.get')
    def test_validate_configuration_success(self, mock_get):
        """Test successful configuration validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        is_valid, message = self.client.validate_configuration()
        
        assert is_valid is True
        assert message == "GitHub configuration valid"
        
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/test_owner/test_repo",
            headers={
                'Authorization': 'token test_token',
                'Accept': 'application/vnd.github.v3+json'
            },
            timeout=10
        )
    
    def test_validate_configuration_missing_token(self):
        """Test configuration validation with missing token."""
        client = GitHubApiClient(
            token="",
            repository="test_owner/test_repo"
        )
        
        is_valid, message = client.validate_configuration()
        
        assert is_valid is False
        assert message == "GitHub token not configured"
    
    def test_validate_configuration_invalid_repository(self):
        """Test configuration validation with invalid repository."""
        client = GitHubApiClient(
            token="test_token",
            repository="invalid_repo"
        )
        
        is_valid, message = client.validate_configuration()
        
        assert is_valid is False
        assert message == "Invalid repository format (should be owner/repo)"
    
    @patch('src.infrastructure.github_client.requests.get')
    def test_validate_configuration_unauthorized(self, mock_get):
        """Test configuration validation with unauthorized token."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        is_valid, message = self.client.validate_configuration()
        
        assert is_valid is False
        assert message == "Invalid GitHub token"
    
    @patch('src.infrastructure.github_client.requests.get')
    def test_validate_configuration_not_found(self, mock_get):
        """Test configuration validation with repository not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        is_valid, message = self.client.validate_configuration()
        
        assert is_valid is False
        assert message == "Repository test_owner/test_repo not found or not accessible"
    
    @patch('src.infrastructure.github_client.requests.get')
    def test_validate_configuration_other_http_error(self, mock_get):
        """Test configuration validation with other HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        is_valid, message = self.client.validate_configuration()
        
        assert is_valid is False
        assert message == "GitHub API returned status 500"
    
    @patch('src.infrastructure.github_client.requests.get')
    def test_validate_configuration_exception(self, mock_get):
        """Test configuration validation with exception."""
        mock_get.side_effect = Exception("Test error")
        
        is_valid, message = self.client.validate_configuration()
        
        assert is_valid is False
        assert "Failed to validate GitHub configuration: Test error" in message
    
    @patch('src.infrastructure.github_client.logger')
    @patch('src.infrastructure.github_client.requests.post')
    def test_logging_during_success(self, mock_post, mock_logger):
        """Test logging during successful operation."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        payload = {
            "client_payload": {
                "vcluster_name": "test-cluster"
            }
        }
        
        self.client.trigger_vcluster_creation(payload)
        
        mock_logger.info.assert_called()
        # Check that the success message was logged
        success_call = [call for call in mock_logger.info.call_args_list if "✅" in str(call)]
        assert len(success_call) > 0
    
    @patch('src.infrastructure.github_client.logger')
    @patch('src.infrastructure.github_client.requests.post')
    def test_logging_during_error(self, mock_post, mock_logger):
        """Test logging during error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        payload = {"event_type": "slack_create_vcluster"}
        
        self.client.trigger_vcluster_creation(payload)
        
        mock_logger.error.assert_called()
        # Check that the error message was logged
        error_call = [call for call in mock_logger.error.call_args_list if "❌" in str(call)]
        assert len(error_call) > 0