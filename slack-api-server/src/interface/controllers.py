"""
Interface Layer - FastAPI Controllers
Handles HTTP requests and responses, coordinates with application layer
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from ..application.use_cases import (HealthCheckUseCase,
                                     ProcessSlackCommandUseCase,
                                     VerifySlackRequestUseCase)
from ..application.oam_use_cases import ProcessOAMWebhook
from ..domain.models import InvalidSlackCommandError, SlackCommand
from .dependencies import (get_process_slack_command_use_case,
                           get_verify_slack_request_use_case,
                           get_process_oam_webhook_use_case)

logger = logging.getLogger(__name__)


class SlackController:
    """Controller for Slack webhook endpoints."""

    def __init__(self):
        """Initialize controller."""
        self.health_check_use_case = HealthCheckUseCase()

    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return self.health_check_use_case.execute()

    async def slack_command(
        self,
        request: Request,
        process_use_case: ProcessSlackCommandUseCase = Depends(
            get_process_slack_command_use_case
        ),
        verify_use_case: VerifySlackRequestUseCase = Depends(
            get_verify_slack_request_use_case
        ),
    ) -> Dict[str, Any]:
        """Handle Slack slash command webhook."""
        try:
            # Get request data
            body = await request.body()
            headers = request.headers

            # Verify request if signing secret is configured
            timestamp = headers.get("X-Slack-Request-Timestamp")
            signature = headers.get("X-Slack-Signature")

            if timestamp and signature:
                is_valid, message = verify_use_case.execute(body, timestamp, signature)
                if not is_valid:
                    logger.warning(f"Invalid Slack request: {message}")
                    raise HTTPException(status_code=401, detail=message)

            # Parse form data
            form_data = await request.form()

            # Create SlackCommand domain object
            slack_command = SlackCommand(
                command=form_data.get("command", ""),
                text=form_data.get("text", ""),
                user_id=form_data.get("user_id", ""),
                user_name=form_data.get("user_name", ""),
                channel_id=form_data.get("channel_id", ""),
                channel_name=form_data.get("channel_name", ""),
                team_id=form_data.get("team_id", ""),
                team_domain=form_data.get("team_domain", ""),
            )

            # Process command
            response = process_use_case.execute(slack_command)

            logger.info(
                f"Processed Slack command: {slack_command.command} from {slack_command.user_name}"
            )
            return response

        except InvalidSlackCommandError as e:
            logger.warning(f"Invalid Slack command: {e}")
            return {"response_type": "ephemeral", "text": f"❌ {str(e)}"}

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Unexpected error in slack_command: {e}", exc_info=True)
            return {
                "response_type": "ephemeral",
                "text": "❌ An unexpected error occurred. Please try again.",
            }

    async def slack_events(
        self,
        request: Request,
        verify_use_case: VerifySlackRequestUseCase = Depends(
            get_verify_slack_request_use_case
        ),
    ) -> Dict[str, Any]:
        """Handle Slack events API webhook."""
        try:
            # Get request data
            body = await request.body()
            headers = request.headers

            # Verify request if signing secret is configured
            timestamp = headers.get("X-Slack-Request-Timestamp")
            signature = headers.get("X-Slack-Signature")

            if timestamp and signature:
                is_valid, message = verify_use_case.execute(body, timestamp, signature)
                if not is_valid:
                    logger.warning(f"Invalid Slack request: {message}")
                    raise HTTPException(status_code=401, detail=message)

            # Parse JSON data
            try:
                event_data = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON payload")

            # Handle URL verification challenge
            if event_data.get("type") == "url_verification":
                return {"challenge": event_data.get("challenge")}

            # Handle other events (placeholder for future implementation)
            logger.info(f"Received Slack event: {event_data.get('type')}")
            return {"status": "ok"}

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Unexpected error in slack_events: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")


class OAMWebhookController:
    """Controller for OAM webhook endpoints."""
    
    async def oam_webhook(
        self,
        request: Request,
        process_use_case: ProcessOAMWebhook = Depends(get_process_oam_webhook_use_case)
    ) -> Dict[str, Any]:
        """Handle OAM Application admission webhook.
        
        This endpoint receives admission review requests from Kubernetes
        when OAM Applications are created or updated, and triggers
        corresponding microservice creation workflows.
        """
        try:
            # Parse admission review request
            body = await request.body()
            try:
                data = json.loads(body.decode("utf-8"))
                # Log the exact request received from Argo Events
                logger.info(f"=== OAM Webhook Request Received ===")
                logger.info(f"Raw request keys: {list(data.keys())}")
                logger.info(f"Full request body: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError:
                logger.error("Invalid JSON in OAM webhook request")
                # Return admission response that allows but logs error
                return {
                    "apiVersion": "admission.k8s.io/v1",
                    "kind": "AdmissionReview",
                    "response": {
                        "uid": "unknown",
                        "allowed": True,
                        "status": {
                            "message": "Invalid JSON payload"
                        }
                    }
                }
            
            # Log the received data for debugging
            logger.debug(f"Received webhook data structure: {list(data.keys())}")
            
            # Handle both Argo Events format and standard admission review format
            # Check if this is from Argo Events (has 'body' field)
            if "body" in data and "operation" in data:
                # Argo Events format - body is a JSON string that needs parsing
                try:
                    # Parse the body string into an object
                    oam_object = json.loads(data["body"]) if isinstance(data["body"], str) else data["body"]
                    app_name = oam_object.get("metadata", {}).get("name", "unknown")
                    logger.info(f"Processing Argo Events webhook for OAM Application: {app_name}")
                    
                    # Wrap it in admission review format
                    admission_request = {
                        "apiVersion": "admission.k8s.io/v1",
                        "kind": "AdmissionReview",
                        "request": {
                            "uid": "argo-events-trigger",
                            "kind": {
                                "group": "core.oam.dev",
                                "version": "v1beta1", 
                                "kind": "Application"
                            },
                            "operation": data.get("operation", "CREATE"),
                            "object": oam_object
                        }
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Argo Events body field: {e}")
                    admission_request = data
            else:
                # Standard admission review format
                admission_request = data
            
            # Process the OAM webhook
            admission_response = process_use_case.execute(admission_request)
            
            logger.info(
                f"Processed OAM webhook for Application: "
                f"{admission_request.get('request', {}).get('object', {}).get('metadata', {}).get('name', 'unknown')}"
            )
            
            return admission_response
            
        except Exception as e:
            logger.error(f"Unexpected error in oam_webhook: {e}", exc_info=True)
            # Always allow to avoid blocking deployments
            return {
                "apiVersion": "admission.k8s.io/v1",
                "kind": "AdmissionReview",
                "response": {
                    "uid": admission_request.get("request", {}).get("uid", "unknown") if 'admission_request' in locals() else "unknown",
                    "allowed": True,
                    "status": {
                        "message": f"Error processing webhook: {str(e)}"
                    }
                }
            }


def create_slack_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Slack API Server",
        description="VCluster provisioning via Slack commands",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Initialize controllers
    slack_controller = SlackController()
    oam_controller = OAMWebhookController()

    # Register routes
    app.add_api_route(
        "/health", slack_controller.health_check, methods=["GET"], tags=["health"]
    )

    app.add_api_route(
        "/slack/command", slack_controller.slack_command, methods=["POST"], tags=["slack"]
    )

    app.add_api_route(
        "/slack/events", slack_controller.slack_events, methods=["POST"], tags=["slack"]
    )
    
    app.add_api_route(
        "/oam/webhook", oam_controller.oam_webhook, methods=["POST"], tags=["oam"]
    )

    # Add middleware for logging
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        start_time = datetime.now()
        response = await call_next(request)
        process_time = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )

        return response

    return app
