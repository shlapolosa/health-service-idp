"""
Application Layer - Use Cases and Application Services
Orchestrates domain objects and coordinates with infrastructure
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Tuple

from ..domain.models import (AppContainerRequest, InvalidAppContainerRequestError,
                             InvalidVClusterRequestError, SlackCommand,
                             VClusterRequest)
from ..domain.services import (CommandParserInterface,
                               SlackResponseBuilderService,
                               VClusterFactoryService,
                               VClusterValidationService)

logger = logging.getLogger(__name__)


class VClusterDispatcherInterface(ABC):
    """Interface for VCluster and AppContainer creation dispatch operations."""

    @abstractmethod
    def trigger_vcluster_creation(self, payload: Dict) -> Tuple[bool, str]:
        """Trigger VCluster creation via the dispatcher implementation."""
        pass

    @abstractmethod
    def trigger_appcontainer_creation(self, payload: Dict) -> Tuple[bool, str]:
        """Trigger AppContainer creation via the dispatcher implementation."""
        pass

    @abstractmethod
    def validate_configuration(self) -> Tuple[bool, str]:
        """Validate dispatcher configuration."""
        pass


# Keep for backward compatibility
class GitHubDispatcherInterface(VClusterDispatcherInterface):
    """Interface for GitHub repository dispatch operations (extends VClusterDispatcherInterface)."""
    pass


class SlackVerifierInterface(ABC):
    """Interface for Slack request verification."""

    @abstractmethod
    def verify_request(
        self, request_data: bytes, timestamp: str, signature: str
    ) -> bool:
        """Verify Slack request signature."""
        pass


class CreateVClusterUseCase:
    """Use case for creating a VCluster from Slack command."""

    def __init__(
        self,
        parser: CommandParserInterface,
        vcluster_dispatcher: VClusterDispatcherInterface,
        factory: VClusterFactoryService = None,
        validator: VClusterValidationService = None,
        response_builder: SlackResponseBuilderService = None,
    ):
        """Initialize use case with dependencies."""
        self.parser = parser
        self.vcluster_dispatcher = vcluster_dispatcher
        self.factory = factory or VClusterFactoryService()
        self.validator = validator or VClusterValidationService()
        self.response_builder = response_builder or SlackResponseBuilderService()

    def execute(self, command: SlackCommand) -> Dict:
        """Execute the create VCluster use case."""
        try:
            logger.info(
                f"Processing VCluster creation command from user {command.user_name}"
            )

            # Parse the command
            parsed_command = self.parser.parse_command(command)

            if parsed_command.action == "help":
                return self.response_builder.build_help_response()

            if parsed_command.action != "create":
                return self.response_builder.build_error_response(
                    f"Unknown action: {parsed_command.action}. Use '/vcluster help' for available commands."
                )

            # Create VCluster request
            request = self.factory.create_vcluster_request(
                parsed_command=parsed_command,
                user=command.user_name,
                channel=command.channel_id,
                original_text=command.text,
            )

            # Validate request
            is_valid, errors = self.validator.validate_request(request)
            if not is_valid:
                error_message = "Invalid request: " + "; ".join(errors)
                logger.warning(f"Validation failed: {error_message}")
                return self.response_builder.build_error_response(error_message)

            # Trigger VCluster creation via dispatcher
            payload = request.to_github_payload()  # This method can be kept/renamed to to_dispatch_payload()
            success, message = self.vcluster_dispatcher.trigger_vcluster_creation(payload)

            if not success:
                logger.error(f"VCluster dispatch failed: {message}")
                return self.response_builder.build_error_response(
                    f"Failed to trigger creation: {message}"
                )

            logger.info(f"Successfully triggered VCluster creation: {request.name}")
            return self.response_builder.build_success_response(request)

        except InvalidVClusterRequestError as e:
            logger.warning(f"Invalid VCluster request: {e}")
            return self.response_builder.build_error_response(str(e))

        except Exception as e:
            logger.error(
                f"Unexpected error in CreateVClusterUseCase: {e}", exc_info=True
            )
            return self.response_builder.build_error_response(
                "An unexpected error occurred. Please try again."
            )


class CreateAppContainerUseCase:
    """Use case for creating an AppContainer from Slack command."""

    def __init__(
        self,
        parser: CommandParserInterface,
        vcluster_dispatcher: VClusterDispatcherInterface,  # Reuse same dispatcher interface
        response_builder: SlackResponseBuilderService = None,
    ):
        """Initialize use case with dependencies."""
        self.parser = parser
        self.vcluster_dispatcher = vcluster_dispatcher  # Will dispatch to Argo workflows
        self.response_builder = response_builder or SlackResponseBuilderService()

    def execute(self, command: SlackCommand) -> Dict:
        """Execute the create AppContainer use case."""
        try:
            logger.info(
                f"Processing AppContainer creation command from user {command.user_name}"
            )

            # Parse the command
            parsed_command = self.parser.parse_command(command)

            if parsed_command.action == "help":
                return self.response_builder.build_appcontainer_help_response()

            if parsed_command.action != "create":
                return self.response_builder.build_error_response(
                    f"Unknown action: {parsed_command.action}. Use '/appcontainer help' for available commands."
                )

            # Create AppContainer request
            request = AppContainerRequest(
                name=parsed_command.appcontainer_name,
                namespace=parsed_command.namespace,
                user=command.user_name,
                slack_channel=command.channel_id,
                description=parsed_command.description,
                github_org=parsed_command.github_org,
                docker_registry=parsed_command.docker_registry,
                enable_observability=parsed_command.enable_observability,
                enable_security=parsed_command.enable_security,
                original_text=command.text,
            )

            # Basic validation
            if not request.name:
                return self.response_builder.build_error_response(
                    "AppContainer name is required"
                )

            # Trigger AppContainer creation via dispatcher (Argo workflows)
            payload = request.to_argo_payload()
            success, message = self.vcluster_dispatcher.trigger_appcontainer_creation(payload)

            if not success:
                logger.error(f"AppContainer dispatch failed: {message}")
                return self.response_builder.build_error_response(
                    f"Failed to trigger creation: {message}"
                )

            logger.info(f"Successfully triggered AppContainer creation: {request.name}")
            return self.response_builder.build_appcontainer_success_response(request)

        except InvalidAppContainerRequestError as e:
            logger.warning(f"Invalid AppContainer request: {e}")
            return self.response_builder.build_error_response(str(e))

        except Exception as e:
            logger.error(
                f"Unexpected error in CreateAppContainerUseCase: {e}", exc_info=True
            )
            return self.response_builder.build_error_response(
                "An unexpected error occurred. Please try again."
            )


class ProcessSlackCommandUseCase:
    """Use case for processing general Slack commands."""

    def __init__(
        self,
        create_vcluster_use_case: CreateVClusterUseCase,
        create_appcontainer_use_case: CreateAppContainerUseCase = None,
        response_builder: SlackResponseBuilderService = None,
    ):
        """Initialize use case with dependencies."""
        self.create_vcluster_use_case = create_vcluster_use_case
        self.create_appcontainer_use_case = create_appcontainer_use_case
        self.response_builder = response_builder or SlackResponseBuilderService()

    def execute(self, command: SlackCommand) -> Dict:
        """Execute the process Slack command use case."""
        try:
            logger.info(
                f"Processing Slack command: {command.command} from user {command.user_name}"
            )

            # Route to appropriate use case based on command type
            if command.command == "/vcluster":
                return self._handle_vcluster_command(command)
            elif command.command in ["/appcontainer", "/app-cont"]:
                return self._handle_appcontainer_command(command)
            else:
                return self.response_builder.build_error_response(
                    f"Unknown command: {command.command}"
                )

        except Exception as e:
            logger.error(
                f"Unexpected error in ProcessSlackCommandUseCase: {e}", exc_info=True
            )
            return self.response_builder.build_error_response(
                "An unexpected error occurred. Please try again."
            )

    def _handle_vcluster_command(self, command: SlackCommand) -> Dict:
        """Handle VCluster commands."""
        # Determine the action
        if not command.text or command.text.strip().startswith("help"):
            return self.response_builder.build_help_response()

        if command.text.strip().startswith("create"):
            return self.create_vcluster_use_case.execute(command)

        elif command.text.strip().startswith("list"):
            return self.response_builder.build_error_response(
                "List functionality coming soon..."
            )

        elif command.text.strip().startswith("delete"):
            return self.response_builder.build_error_response(
                "Delete functionality coming soon..."
            )

        elif command.text.strip().startswith("status"):
            return self.response_builder.build_error_response(
                "Status functionality coming soon..."
            )

        else:
            return self.response_builder.build_error_response(
                f"Unknown vcluster command: {command.text}\nUse '/vcluster help' for available commands."
            )

    def _handle_appcontainer_command(self, command: SlackCommand) -> Dict:
        """Handle AppContainer commands."""
        if not self.create_appcontainer_use_case:
            return self.response_builder.build_error_response(
                "AppContainer functionality is not enabled"
            )

        # Determine the action
        if not command.text or command.text.strip().startswith("help"):
            return self.response_builder.build_appcontainer_help_response()

        if command.text.strip().startswith("create"):
            return self.create_appcontainer_use_case.execute(command)

        elif command.text.strip().startswith("list"):
            return self.response_builder.build_error_response(
                "AppContainer list functionality coming soon..."
            )

        elif command.text.strip().startswith("delete"):
            return self.response_builder.build_error_response(
                "AppContainer delete functionality coming soon..."
            )

        elif command.text.strip().startswith("status"):
            return self.response_builder.build_error_response(
                "AppContainer status functionality coming soon..."
            )

        else:
            return self.response_builder.build_error_response(
                f"Unknown appcontainer command: {command.text}\nUse '/appcontainer help' for available commands."
            )


class VerifySlackRequestUseCase:
    """Use case for verifying Slack request authenticity."""

    def __init__(self, verifier: SlackVerifierInterface):
        """Initialize use case with dependencies."""
        self.verifier = verifier

    def execute(
        self, request_data: bytes, timestamp: str, signature: str
    ) -> Tuple[bool, str]:
        """Execute the verify Slack request use case."""
        try:
            logger.debug("Verifying Slack request signature")

            if not self.verifier.verify_request(request_data, timestamp, signature):
                logger.warning("Invalid Slack request signature")
                return False, "Invalid request signature"

            logger.debug("Slack request signature verified successfully")
            return True, "Request verified"

        except Exception as e:
            logger.error(f"Error verifying Slack request: {e}", exc_info=True)
            return False, "Verification failed"


class HealthCheckUseCase:
    """Use case for health check endpoint."""

    def execute(self) -> Dict:
        """Execute health check."""
        from datetime import datetime

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "slack-api-server",
        }
