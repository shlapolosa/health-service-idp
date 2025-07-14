"""
Unit tests for application use cases
"""

from unittest.mock import Mock, patch

import pytest

from src.application.use_cases import (CreateAppContainerUseCase,
                                       CreateMicroserviceUseCase,
                                       CreateVClusterUseCase,
                                       HealthCheckUseCase,
                                       ProcessSlackCommandUseCase,
                                       VerifySlackRequestUseCase)
from src.domain.models import (AppContainerRequest, Capability, CapabilitySet,
                               InvalidVClusterRequestError, 
                               MicroserviceRequest, MicroserviceLanguage, 
                               MicroserviceDatabase, MicroserviceCache,
                               ParsedCommand,
                               ResourceSpec, SlackCommand, VClusterRequest,
                               VClusterSize)


class TestCreateVClusterUseCase:
    """Test CreateVClusterUseCase application service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_parser = Mock()
        self.mock_vcluster_dispatcher = Mock()
        self.mock_factory = Mock()
        self.mock_validator = Mock()
        self.mock_response_builder = Mock()

        self.use_case = CreateVClusterUseCase(
            parser=self.mock_parser,
            vcluster_dispatcher=self.mock_vcluster_dispatcher,
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
        self.mock_vcluster_dispatcher.trigger_vcluster_creation.assert_not_called()

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
        self.mock_vcluster_dispatcher.trigger_vcluster_creation.assert_not_called()

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
        self.mock_vcluster_dispatcher.trigger_vcluster_creation.return_value = (
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
        self.mock_vcluster_dispatcher.trigger_vcluster_creation.assert_called_once()
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
        self.mock_vcluster_dispatcher.trigger_vcluster_creation.assert_not_called()
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
        self.mock_vcluster_dispatcher.trigger_vcluster_creation.return_value = (
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
        self.mock_create_appcontainer_use_case = Mock()
        self.mock_create_microservice_use_case = Mock()
        self.mock_response_builder = Mock()

        self.use_case = ProcessSlackCommandUseCase(
            create_vcluster_use_case=self.mock_create_use_case,
            create_appcontainer_use_case=self.mock_create_appcontainer_use_case,
            create_microservice_use_case=self.mock_create_microservice_use_case,
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

    def test_execute_appcontainer_command(self):
        """Test executing AppContainer command."""
        command = SlackCommand(
            command="/appcontainer",
            text="create my-app",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        appcontainer_response = {"response_type": "in_channel", "text": "Creating AppContainer..."}
        self.mock_create_appcontainer_use_case.execute.return_value = appcontainer_response

        result = self.use_case.execute(command)

        assert result == appcontainer_response
        self.mock_create_appcontainer_use_case.execute.assert_called_once_with(command)
        self.mock_create_use_case.execute.assert_not_called()

    def test_execute_app_cont_alias_command(self):
        """Test executing /app-cont alias command."""
        command = SlackCommand(
            command="/app-cont",
            text="create test-service",
            user_id="U456",
            user_name="alice",
            channel_id="C456",
            channel_name="backend",
            team_id="T123",
            team_domain="testteam",
        )

        appcontainer_response = {"response_type": "in_channel", "text": "Creating AppContainer..."}
        self.mock_create_appcontainer_use_case.execute.return_value = appcontainer_response

        result = self.use_case.execute(command)

        assert result == appcontainer_response
        self.mock_create_appcontainer_use_case.execute.assert_called_once_with(command)
        self.mock_create_use_case.execute.assert_not_called()

    def test_execute_microservice_command(self):
        """Test executing Microservice command."""
        command = SlackCommand(
            command="/microservice",
            text="create user-service",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        microservice_response = {"response_type": "in_channel", "text": "Creating Microservice..."}
        self.mock_create_microservice_use_case.execute.return_value = microservice_response

        result = self.use_case.execute(command)

        assert result == microservice_response
        self.mock_create_microservice_use_case.execute.assert_called_once_with(command)
        self.mock_create_use_case.execute.assert_not_called()
        self.mock_create_appcontainer_use_case.execute.assert_not_called()

    def test_execute_service_alias_command(self):
        """Test executing /service alias command."""
        command = SlackCommand(
            command="/service",
            text="create api-service",
            user_id="U456",
            user_name="alice",
            channel_id="C456",
            channel_name="backend",
            team_id="T123",
            team_domain="testteam",
        )

        microservice_response = {"response_type": "in_channel", "text": "Creating Microservice..."}
        self.mock_create_microservice_use_case.execute.return_value = microservice_response

        result = self.use_case.execute(command)

        assert result == microservice_response
        self.mock_create_microservice_use_case.execute.assert_called_once_with(command)
        self.mock_create_use_case.execute.assert_not_called()
        self.mock_create_appcontainer_use_case.execute.assert_not_called()

    def test_execute_microservice_without_use_case(self):
        """Test executing microservice command when use case is not enabled."""
        # Create use case without microservice use case
        use_case_without_microservice = ProcessSlackCommandUseCase(
            create_vcluster_use_case=self.mock_create_use_case,
            create_appcontainer_use_case=self.mock_create_appcontainer_use_case,
            create_microservice_use_case=None,  # Not provided
            response_builder=self.mock_response_builder,
        )

        command = SlackCommand(
            command="/microservice",
            text="create test-service",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        error_response = {"response_type": "ephemeral", "text": "Microservice functionality is not enabled"}
        self.mock_response_builder.build_error_response.return_value = error_response

        result = use_case_without_microservice.execute(command)

        assert result == error_response
        self.mock_response_builder.build_error_response.assert_called_once()


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


class TestCreateAppContainerUseCase:
    """Test CreateAppContainerUseCase application service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_parser = Mock()
        self.mock_vcluster_dispatcher = Mock()
        self.mock_response_builder = Mock()
        
        self.use_case = CreateAppContainerUseCase(
            parser=self.mock_parser,
            vcluster_dispatcher=self.mock_vcluster_dispatcher,
        )
        # Inject the mock response builder
        self.use_case.response_builder = self.mock_response_builder

    def test_execute_success(self):
        """Test successful AppContainer creation."""
        command = SlackCommand(
            command="/appcontainer",
            text="create my-app",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(
            action="create",
            command_type="appcontainer",
            appcontainer_name="my-app",
            namespace="default",
            description="CLAUDE.md-compliant application container",
            github_org="socrates12345",
            enable_observability=True,
            enable_security=True,
        )

        success_response = {"response_type": "in_channel", "text": "AppContainer created"}
        
        self.mock_parser.parse_command.return_value = parsed
        self.mock_vcluster_dispatcher.trigger_appcontainer_creation.return_value = (
            True,
            "AppContainer creation workflow started: appcontainer-creation-abc123",
        )
        self.mock_response_builder.build_appcontainer_success_response.return_value = success_response

        result = self.use_case.execute(command)

        assert result == success_response
        
        self.mock_parser.parse_command.assert_called_once_with(command)
        self.mock_vcluster_dispatcher.trigger_appcontainer_creation.assert_called_once()
        self.mock_response_builder.build_appcontainer_success_response.assert_called_once()

        # Verify payload structure
        call_args = self.mock_vcluster_dispatcher.trigger_appcontainer_creation.call_args[0][0]
        assert call_args["appcontainer-name"] == "my-app"
        assert call_args["namespace"] == "default"
        assert call_args["user"] == "testuser"
        assert call_args["slack-channel"] == "C123"

    def test_execute_with_custom_parameters(self):
        """Test AppContainer creation with custom parameters."""
        command = SlackCommand(
            command="/appcontainer",
            text='create my-api description "REST API for user management" github-org mycompany',
            user_id="U456",
            user_name="alice",
            channel_id="C456",
            channel_name="backend",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(
            action="create",
            command_type="appcontainer",
            appcontainer_name="my-api",
            namespace="production",
            description="REST API for user management",
            github_org="mycompany",
            docker_registry="docker.io/mycompany",
            enable_observability=False,
            enable_security=True,
        )

        success_response = {"response_type": "in_channel", "text": "AppContainer created"}
        
        self.mock_parser.parse_command.return_value = parsed
        self.mock_vcluster_dispatcher.trigger_appcontainer_creation.return_value = (
            True,
            "AppContainer creation workflow started: appcontainer-creation-def456",
        )
        self.mock_response_builder.build_appcontainer_success_response.return_value = success_response

        result = self.use_case.execute(command)

        assert result == success_response
        
        # Verify payload with custom parameters
        call_args = self.mock_vcluster_dispatcher.trigger_appcontainer_creation.call_args[0][0]
        assert call_args["appcontainer-name"] == "my-api"
        assert call_args["namespace"] == "production"
        assert call_args["description"] == "REST API for user management"
        assert call_args["github-org"] == "mycompany"
        assert call_args["docker-registry"] == "docker.io/mycompany"
        assert call_args["observability"] == "false"
        assert call_args["security"] == "true"

    def test_execute_workflow_failure(self):
        """Test AppContainer creation with workflow failure."""
        command = SlackCommand(
            command="/appcontainer",
            text="create test-app",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(
            action="create",
            command_type="appcontainer",
            appcontainer_name="test-app",
        )

        error_response = {"response_type": "ephemeral", "text": "Failed to trigger creation"}
        
        self.mock_parser.parse_command.return_value = parsed
        self.mock_vcluster_dispatcher.trigger_appcontainer_creation.return_value = (
            False,
            "Argo Workflows API error: 500 - Internal Server Error",
        )
        self.mock_response_builder.build_error_response.return_value = error_response

        result = self.use_case.execute(command)

        assert result == error_response
        self.mock_response_builder.build_error_response.assert_called_once()

    def test_execute_invalid_request(self):
        """Test AppContainer creation with invalid request data."""
        command = SlackCommand(
            command="/appcontainer",
            text="create -invalid-name-",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(
            action="create",
            command_type="appcontainer",
            appcontainer_name="-invalid-name-",
        )

        error_response = {"response_type": "ephemeral", "text": "An unexpected error occurred"}
        
        self.mock_parser.parse_command.return_value = parsed
        self.mock_response_builder.build_error_response.return_value = error_response

        # AppContainerRequest validation should fail
        result = self.use_case.execute(command)

        assert result == error_response
        self.mock_response_builder.build_error_response.assert_called_once()
        
        # Should not call the dispatcher
        self.mock_vcluster_dispatcher.trigger_appcontainer_creation.assert_not_called()


class TestCreateMicroserviceUseCase:
    """Test CreateMicroserviceUseCase application service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_parser = Mock()
        self.mock_vcluster_dispatcher = Mock()
        self.mock_response_builder = Mock()
        
        self.use_case = CreateMicroserviceUseCase(
            parser=self.mock_parser,
            vcluster_dispatcher=self.mock_vcluster_dispatcher,
        )
        # Inject the mock response builder
        self.use_case.response_builder = self.mock_response_builder

    def test_execute_success(self):
        """Test successful Microservice creation."""
        command = SlackCommand(
            command="/microservice",
            text="create user-service",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(
            action="create",
            command_type="microservice",
            microservice_name="user-service",
            namespace="default",
            description="CLAUDE.md-compliant microservice",
            github_org="socrates12345",
            enable_observability=True,
            enable_security=True,
            microservice_language=MicroserviceLanguage.PYTHON,
            microservice_database=MicroserviceDatabase.NONE,
            microservice_cache=MicroserviceCache.NONE,
        )

        success_response = {"response_type": "in_channel", "text": "Microservice created"}
        
        self.mock_parser.parse_command.return_value = parsed
        self.mock_vcluster_dispatcher.trigger_microservice_creation.return_value = (
            True,
            "Microservice creation workflow started: microservice-creation-abc123",
        )
        self.mock_response_builder.build_microservice_success_response.return_value = success_response

        result = self.use_case.execute(command)

        assert result == success_response
        
        self.mock_parser.parse_command.assert_called_once_with(command)
        self.mock_vcluster_dispatcher.trigger_microservice_creation.assert_called_once()
        self.mock_response_builder.build_microservice_success_response.assert_called_once()

        # Verify payload structure matches 4-tier standardized contract
        call_args = self.mock_vcluster_dispatcher.trigger_microservice_creation.call_args[0][0]
        assert call_args["microservice-name"] == "user-service"
        assert call_args["namespace"] == "default"
        assert call_args["language"] == "python"
        assert call_args["database"] == "none"
        assert call_args["cache"] == "none"
        assert call_args["user"] == "testuser"
        assert call_args["slack-channel"] == "C123"

    def test_execute_with_database_and_cache(self):
        """Test Microservice creation with PostgreSQL database and Redis cache."""
        command = SlackCommand(
            command="/microservice",
            text='create order-service with java and postgres and redis',
            user_id="U456",
            user_name="alice",
            channel_id="C456",
            channel_name="backend",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(
            action="create",
            command_type="microservice",
            microservice_name="order-service",
            namespace="production",
            description="Order processing microservice",
            github_org="ecommerce",
            docker_registry="docker.io/ecommerce",
            enable_observability=True,
            enable_security=True,
            microservice_language=MicroserviceLanguage.JAVA,
            microservice_database=MicroserviceDatabase.POSTGRESQL,
            microservice_cache=MicroserviceCache.REDIS,
            target_vcluster="prod-cluster",
            auto_create_vcluster=False,
        )

        success_response = {"response_type": "in_channel", "text": "Microservice created"}
        
        self.mock_parser.parse_command.return_value = parsed
        self.mock_vcluster_dispatcher.trigger_microservice_creation.return_value = (
            True,
            "Microservice creation workflow started: microservice-creation-def456",
        )
        self.mock_response_builder.build_microservice_success_response.return_value = success_response

        result = self.use_case.execute(command)

        assert result == success_response
        
        # Verify payload with custom parameters and database mapping
        call_args = self.mock_vcluster_dispatcher.trigger_microservice_creation.call_args[0][0]
        assert call_args["microservice-name"] == "order-service"
        assert call_args["namespace"] == "production"
        assert call_args["language"] == "java"
        assert call_args["database"] == "postgres"  # postgresql -> postgres mapping
        assert call_args["cache"] == "redis"
        assert call_args["description"] == "Order processing microservice"
        assert call_args["github-org"] == "ecommerce"
        assert call_args["docker-registry"] == "docker.io/ecommerce"
        assert call_args["target-vcluster"] == "prod-cluster"
        assert call_args["auto-create-vcluster"] == "false"

    def test_execute_help_command(self):
        """Test Microservice help command."""
        command = SlackCommand(
            command="/microservice",
            text="help",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(action="help")
        help_response = {"response_type": "ephemeral", "text": "Microservice help"}

        self.mock_parser.parse_command.return_value = parsed
        self.mock_response_builder.build_microservice_help_response.return_value = help_response

        result = self.use_case.execute(command)

        assert result == help_response
        self.mock_parser.parse_command.assert_called_once_with(command)
        self.mock_response_builder.build_microservice_help_response.assert_called_once()
        self.mock_vcluster_dispatcher.trigger_microservice_creation.assert_not_called()

    def test_execute_missing_microservice_name(self):
        """Test Microservice creation without microservice name."""
        command = SlackCommand(
            command="/microservice",
            text="create",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(
            action="create",
            command_type="microservice",
            microservice_name=None,  # Missing name
        )

        error_response = {"response_type": "ephemeral", "text": "Microservice name is required"}
        
        self.mock_parser.parse_command.return_value = parsed
        self.mock_response_builder.build_error_response.return_value = error_response

        result = self.use_case.execute(command)

        assert result == error_response
        self.mock_response_builder.build_error_response.assert_called_once()
        
        # Should not call the dispatcher
        self.mock_vcluster_dispatcher.trigger_microservice_creation.assert_not_called()

    def test_execute_parsing_exception(self):
        """Test AppContainer creation with parsing exception."""
        command = SlackCommand(
            command="/appcontainer",
            text="create test-app",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        error_response = {"response_type": "ephemeral", "text": "An unexpected error occurred"}
        
        self.mock_parser.parse_command.side_effect = Exception("Parsing failed")
        self.mock_response_builder.build_error_response.return_value = error_response

        result = self.use_case.execute(command)

        assert result == error_response
        self.mock_response_builder.build_error_response.assert_called_once()

    def test_execute_missing_appcontainer_name(self):
        """Test AppContainer creation without appcontainer name."""
        command = SlackCommand(
            command="/appcontainer",
            text="create",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(
            action="create",
            command_type="appcontainer",
            appcontainer_name=None,  # Missing name
        )

        error_response = {"response_type": "ephemeral", "text": "An unexpected error occurred"}
        
        self.mock_parser.parse_command.return_value = parsed
        self.mock_response_builder.build_error_response.return_value = error_response

        result = self.use_case.execute(command)

        assert result == error_response
        self.mock_response_builder.build_error_response.assert_called_once()
        
        # Should not call the dispatcher
        self.mock_vcluster_dispatcher.trigger_appcontainer_creation.assert_not_called()


class TestCreateMicroserviceUseCase:
    """Test CreateMicroserviceUseCase application service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_parser = Mock()
        self.mock_vcluster_dispatcher = Mock()
        self.mock_response_builder = Mock()
        
        self.use_case = CreateMicroserviceUseCase(
            parser=self.mock_parser,
            vcluster_dispatcher=self.mock_vcluster_dispatcher,
        )
        # Inject the mock response builder
        self.use_case.response_builder = self.mock_response_builder

    def test_execute_success(self):
        """Test successful Microservice creation."""
        command = SlackCommand(
            command="/microservice",
            text="create user-service",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(
            action="create",
            command_type="microservice",
            microservice_name="user-service",
            namespace="default",
            description="CLAUDE.md-compliant microservice",
            github_org="socrates12345",
            enable_observability=True,
            enable_security=True,
            microservice_language=MicroserviceLanguage.PYTHON,
            microservice_database=MicroserviceDatabase.NONE,
            microservice_cache=MicroserviceCache.NONE,
        )

        success_response = {"response_type": "in_channel", "text": "Microservice created"}
        
        self.mock_parser.parse_command.return_value = parsed
        self.mock_vcluster_dispatcher.trigger_microservice_creation.return_value = (
            True,
            "Microservice creation workflow started: microservice-creation-abc123",
        )
        self.mock_response_builder.build_microservice_success_response.return_value = success_response

        result = self.use_case.execute(command)

        assert result == success_response
        
        self.mock_parser.parse_command.assert_called_once_with(command)
        self.mock_vcluster_dispatcher.trigger_microservice_creation.assert_called_once()
        self.mock_response_builder.build_microservice_success_response.assert_called_once()

        # Verify payload structure matches 4-tier standardized contract
        call_args = self.mock_vcluster_dispatcher.trigger_microservice_creation.call_args[0][0]
        assert call_args["microservice-name"] == "user-service"
        assert call_args["namespace"] == "default"
        assert call_args["language"] == "python"
        assert call_args["database"] == "none"
        assert call_args["cache"] == "none"
        assert call_args["user"] == "testuser"
        assert call_args["slack-channel"] == "C123"

    def test_execute_with_database_and_cache(self):
        """Test Microservice creation with PostgreSQL database and Redis cache."""
        command = SlackCommand(
            command="/microservice",
            text='create order-service with java and postgres and redis',
            user_id="U456",
            user_name="alice",
            channel_id="C456",
            channel_name="backend",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(
            action="create",
            command_type="microservice",
            microservice_name="order-service",
            namespace="production",
            description="Order processing microservice",
            github_org="ecommerce",
            docker_registry="docker.io/ecommerce",
            enable_observability=True,
            enable_security=True,
            microservice_language=MicroserviceLanguage.JAVA,
            microservice_database=MicroserviceDatabase.POSTGRESQL,
            microservice_cache=MicroserviceCache.REDIS,
            target_vcluster="prod-cluster",
            auto_create_vcluster=False,
        )

        success_response = {"response_type": "in_channel", "text": "Microservice created"}
        
        self.mock_parser.parse_command.return_value = parsed
        self.mock_vcluster_dispatcher.trigger_microservice_creation.return_value = (
            True,
            "Microservice creation workflow started: microservice-creation-def456",
        )
        self.mock_response_builder.build_microservice_success_response.return_value = success_response

        result = self.use_case.execute(command)

        assert result == success_response
        
        # Verify payload with custom parameters and database mapping
        call_args = self.mock_vcluster_dispatcher.trigger_microservice_creation.call_args[0][0]
        assert call_args["microservice-name"] == "order-service"
        assert call_args["namespace"] == "production"
        assert call_args["language"] == "java"
        assert call_args["database"] == "postgres"  # postgresql -> postgres mapping
        assert call_args["cache"] == "redis"
        assert call_args["description"] == "Order processing microservice"
        assert call_args["github-org"] == "ecommerce"
        assert call_args["docker-registry"] == "docker.io/ecommerce"
        assert call_args["target-vcluster"] == "prod-cluster"
        assert call_args["auto-create-vcluster"] == "false"

    def test_execute_help_command(self):
        """Test Microservice help command."""
        command = SlackCommand(
            command="/microservice",
            text="help",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(action="help")
        help_response = {"response_type": "ephemeral", "text": "Microservice help"}

        self.mock_parser.parse_command.return_value = parsed
        self.mock_response_builder.build_microservice_help_response.return_value = help_response

        result = self.use_case.execute(command)

        assert result == help_response
        self.mock_parser.parse_command.assert_called_once_with(command)
        self.mock_response_builder.build_microservice_help_response.assert_called_once()
        self.mock_vcluster_dispatcher.trigger_microservice_creation.assert_not_called()

    def test_execute_missing_microservice_name(self):
        """Test Microservice creation without microservice name."""
        command = SlackCommand(
            command="/microservice",
            text="create",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        parsed = ParsedCommand(
            action="create",
            command_type="microservice",
            microservice_name=None,  # Missing name
        )

        error_response = {"response_type": "ephemeral", "text": "Microservice name is required"}
        
        self.mock_parser.parse_command.return_value = parsed
        self.mock_response_builder.build_error_response.return_value = error_response

        result = self.use_case.execute(command)

        assert result == error_response
        self.mock_response_builder.build_error_response.assert_called_once()
        
        # Should not call the dispatcher
        self.mock_vcluster_dispatcher.trigger_microservice_creation.assert_not_called()
