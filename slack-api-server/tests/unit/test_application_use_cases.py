"""
Unit tests for application use cases
"""

from unittest.mock import Mock, patch

import pytest

from src.application.use_cases import (CreateVClusterUseCase,
                                       HealthCheckUseCase,
                                       ProcessSlackCommandUseCase,
                                       VerifySlackRequestUseCase)
from src.domain.models import (Capability, CapabilitySet,
                               InvalidVClusterRequestError, ParsedCommand,
                               ResourceSpec, SlackCommand, VClusterRequest,
                               VClusterSize)


class TestCreateVClusterUseCase:
    """Test CreateVClusterUseCase application service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_parser = Mock()
        self.mock_github_dispatcher = Mock()
        self.mock_factory = Mock()
        self.mock_validator = Mock()
        self.mock_response_builder = Mock()

        self.use_case = CreateVClusterUseCase(
            parser=self.mock_parser,
            github_dispatcher=self.mock_github_dispatcher,
            factory=self.mock_factory,
            validator=self.mock_validator,
            response_builder=self.mock_response_builder,
        )

    def test_execute_help_command(self):
        """Test executing help command."""
        command = SlackCommand(
            command="/vcluster",
            text="help",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(action="help")
        help_response = {"response_type": "ephemeral", "text": "Help message"}

        self.mock_parser.parse_command.return_value = parsed
        self.mock_response_builder.build_help_response.return_value = help_response

        result = self.use_case.execute(command)

        assert result == help_response
        self.mock_parser.parse_command.assert_called_once_with(command)
        self.mock_response_builder.build_help_response.assert_called_once()
        self.mock_github_dispatcher.trigger_vcluster_creation.assert_not_called()

    def test_execute_unknown_action(self):
        """Test executing unknown action."""
        command = SlackCommand(
            command="/vcluster",
            text="unknown",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(action="unknown")
        error_response = {"response_type": "ephemeral", "text": "Error message"}

        self.mock_parser.parse_command.return_value = parsed
        self.mock_response_builder.build_error_response.return_value = error_response

        result = self.use_case.execute(command)

        assert result == error_response
        self.mock_response_builder.build_error_response.assert_called_once()
        self.mock_github_dispatcher.trigger_vcluster_creation.assert_not_called()

    def test_execute_create_success(self):
        """Test executing successful create command."""
        command = SlackCommand(
            command="/vcluster",
            text="create test-cluster",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(action="create", vcluster_name="test-cluster")
        capabilities = CapabilitySet()
        resources = ResourceSpec("2000m", "4Gi", "20Gi", 3)

        request = VClusterRequest(
            name="test-cluster",
            namespace="default",
            user="testuser",
            slack_channel="C123",
            capabilities=capabilities,
            resources=resources,
        )

        success_response = {"response_type": "in_channel", "text": "Success"}

        self.mock_parser.parse_command.return_value = parsed
        self.mock_factory.create_vcluster_request.return_value = request
        self.mock_validator.validate_request.return_value = (True, [])
        self.mock_github_dispatcher.trigger_vcluster_creation.return_value = (
            True,
            "Success",
        )
        self.mock_response_builder.build_success_response.return_value = (
            success_response
        )

        result = self.use_case.execute(command)

        assert result == success_response
        self.mock_parser.parse_command.assert_called_once_with(command)
        self.mock_factory.create_vcluster_request.assert_called_once()
        self.mock_validator.validate_request.assert_called_once_with(request)
        self.mock_github_dispatcher.trigger_vcluster_creation.assert_called_once()
        self.mock_response_builder.build_success_response.assert_called_once_with(
            request
        )

    def test_execute_create_validation_failure(self):
        """Test executing create command with validation failure."""
        command = SlackCommand(
            command="/vcluster",
            text="create invalid_name",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(action="create", vcluster_name="invalid_name")
        request = Mock()
        error_response = {"response_type": "ephemeral", "text": "Validation error"}

        self.mock_parser.parse_command.return_value = parsed
        self.mock_factory.create_vcluster_request.return_value = request
        self.mock_validator.validate_request.return_value = (False, ["Invalid name"])
        self.mock_response_builder.build_error_response.return_value = error_response

        result = self.use_case.execute(command)

        assert result == error_response
        self.mock_github_dispatcher.trigger_vcluster_creation.assert_not_called()
        self.mock_response_builder.build_error_response.assert_called_once()

    def test_execute_create_github_failure(self):
        """Test executing create command with GitHub API failure."""
        command = SlackCommand(
            command="/vcluster",
            text="create test-cluster",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(action="create", vcluster_name="test-cluster")
        request = Mock()
        error_response = {"response_type": "ephemeral", "text": "GitHub error"}

        self.mock_parser.parse_command.return_value = parsed
        self.mock_factory.create_vcluster_request.return_value = request
        self.mock_validator.validate_request.return_value = (True, [])
        self.mock_github_dispatcher.trigger_vcluster_creation.return_value = (
            False,
            "API Error",
        )
        self.mock_response_builder.build_error_response.return_value = error_response

        result = self.use_case.execute(command)

        assert result == error_response
        self.mock_response_builder.build_error_response.assert_called_once()

    def test_execute_exception_handling(self):
        """Test exception handling in execute method."""
        command = SlackCommand(
            command="/vcluster",
            text="create test-cluster",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        error_response = {"response_type": "ephemeral", "text": "Unexpected error"}

        self.mock_parser.parse_command.side_effect = Exception("Test error")
        self.mock_response_builder.build_error_response.return_value = error_response

        result = self.use_case.execute(command)

        assert result == error_response
        self.mock_response_builder.build_error_response.assert_called_once()


class TestProcessSlackCommandUseCase:
    """Test ProcessSlackCommandUseCase application service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_create_use_case = Mock()
        self.mock_response_builder = Mock()

        self.use_case = ProcessSlackCommandUseCase(
            create_vcluster_use_case=self.mock_create_use_case,
            response_builder=self.mock_response_builder,
        )

    def test_execute_unknown_command(self):
        """Test executing unknown command."""
        command = SlackCommand(
            command="/unknown",
            text="test",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        error_response = {"response_type": "ephemeral", "text": "Unknown command"}
        self.mock_response_builder.build_error_response.return_value = error_response

        result = self.use_case.execute(command)

        assert result == error_response
        self.mock_response_builder.build_error_response.assert_called_once()

    def test_execute_help_command(self):
        """Test executing help command."""
        command = SlackCommand(
            command="/vcluster",
            text="help",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        help_response = {"response_type": "ephemeral", "text": "Help"}
        self.mock_response_builder.build_help_response.return_value = help_response

        result = self.use_case.execute(command)

        assert result == help_response
        self.mock_response_builder.build_help_response.assert_called_once()

    def test_execute_create_command(self):
        """Test executing create command."""
        command = SlackCommand(
            command="/vcluster",
            text="create test-cluster",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        create_response = {"response_type": "in_channel", "text": "Creating..."}
        self.mock_create_use_case.execute.return_value = create_response

        result = self.use_case.execute(command)

        assert result == create_response
        self.mock_create_use_case.execute.assert_called_once_with(command)

    def test_execute_future_commands(self):
        """Test executing future commands (list, delete, status)."""
        commands = ["list", "delete test", "status test"]

        for cmd_text in commands:
            command = SlackCommand(
                command="/vcluster",
                text=cmd_text,
                user_id="U123",
                user_name="testuser",
                channel_id="C123",
                channel_name="general",
                team_id="T123",
                team_domain="testteam",
            )

            error_response = {"response_type": "ephemeral", "text": "Coming soon"}
            self.mock_response_builder.build_error_response.return_value = (
                error_response
            )

            result = self.use_case.execute(command)

            assert result == error_response
            assert (
                "coming soon"
                in self.mock_response_builder.build_error_response.call_args[0][
                    0
                ].lower()
            )


class TestVerifySlackRequestUseCase:
    """Test VerifySlackRequestUseCase application service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_verifier = Mock()
        self.use_case = VerifySlackRequestUseCase(verifier=self.mock_verifier)

    def test_execute_valid_request(self):
        """Test executing with valid request."""
        self.mock_verifier.verify_request.return_value = True

        is_valid, message = self.use_case.execute(
            request_data=b"test_data",
            timestamp="1234567890",
            signature="v0=test_signature",
        )

        assert is_valid is True
        assert message == "Request verified"
        self.mock_verifier.verify_request.assert_called_once_with(
            b"test_data", "1234567890", "v0=test_signature"
        )

    def test_execute_invalid_request(self):
        """Test executing with invalid request."""
        self.mock_verifier.verify_request.return_value = False

        is_valid, message = self.use_case.execute(
            request_data=b"test_data",
            timestamp="1234567890",
            signature="v0=invalid_signature",
        )

        assert is_valid is False
        assert message == "Invalid request signature"

    def test_execute_exception_handling(self):
        """Test exception handling in execute method."""
        self.mock_verifier.verify_request.side_effect = Exception("Test error")

        is_valid, message = self.use_case.execute(
            request_data=b"test_data",
            timestamp="1234567890",
            signature="v0=test_signature",
        )

        assert is_valid is False
        assert message == "Verification failed"


class TestHealthCheckUseCase:
    """Test HealthCheckUseCase application service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.use_case = HealthCheckUseCase()

    def test_execute(self):
        """Test executing health check."""
        with patch("src.application.use_cases.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = (
                "2023-01-01T12:00:00"
            )

            result = self.use_case.execute()

            assert result["status"] == "healthy"
            assert result["service"] == "slack-api-server"
            # Just check that timestamp is a string, not the exact value
            assert isinstance(result["timestamp"], str)
            assert len(result["timestamp"]) > 0
