"""
Application Layer - Use Cases and Application Services
Orchestrates domain objects and coordinates with infrastructure
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Tuple

from ..domain.models import (InvalidVClusterRequestError, SlackCommand,
                             VClusterRequest)
from ..domain.services import (CommandParserInterface,
                               SlackResponseBuilderService,
                               VClusterFactoryService,
                               VClusterValidationService)

logger = logging.getLogger(__name__)


class VClusterDispatcherInterface(ABC):
    """Interface for VCluster creation dispatch operations."""

    @abstractmethod
    def trigger_vcluster_creation(self, payload: Dict) -> Tuple[bool, str]:
        """Trigger VCluster creation via the dispatcher implementation."""
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


class ProcessSlackCommandUseCase:
    """Use case for processing general Slack commands."""

    def __init__(
        self,
        create_vcluster_use_case: CreateVClusterUseCase,
        response_builder: SlackResponseBuilderService = None,
    ):
        """Initialize use case with dependencies."""
        self.create_vcluster_use_case = create_vcluster_use_case
        self.response_builder = response_builder or SlackResponseBuilderService()

    def execute(self, command: SlackCommand) -> Dict:
        """Execute the process Slack command use case."""
        try:
            logger.info(
                f"Processing Slack command: {command.command} from user {command.user_name}"
            )

            if command.command != "/vcluster":
                return self.response_builder.build_error_response(
                    f"Unknown command: {command.command}"
                )

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

        except Exception as e:
            logger.error(
                f"Unexpected error in ProcessSlackCommandUseCase: {e}", exc_info=True
            )
            return self.response_builder.build_error_response(
                "An unexpected error occurred. Please try again."
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
