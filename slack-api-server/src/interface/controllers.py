"""
Interface Layer - FastAPI Controllers
Handles HTTP requests and responses, coordinates with application layer
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
import json
from datetime import datetime

from ..domain.models import SlackCommand, InvalidSlackCommandError
from ..application.use_cases import (
    ProcessSlackCommandUseCase, 
    VerifySlackRequestUseCase,
    HealthCheckUseCase
)
from .dependencies import get_process_slack_command_use_case, get_verify_slack_request_use_case

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
        process_use_case: ProcessSlackCommandUseCase = Depends(get_process_slack_command_use_case),
        verify_use_case: VerifySlackRequestUseCase = Depends(get_verify_slack_request_use_case)
    ) -> Dict[str, Any]:
        """Handle Slack slash command webhook."""
        try:
            # Get request data
            body = await request.body()
            headers = request.headers
            
            # Verify request if signing secret is configured
            timestamp = headers.get('X-Slack-Request-Timestamp')
            signature = headers.get('X-Slack-Signature')
            
            if timestamp and signature:
                is_valid, message = verify_use_case.execute(body, timestamp, signature)
                if not is_valid:
                    logger.warning(f"Invalid Slack request: {message}")
                    raise HTTPException(status_code=401, detail=message)
            
            # Parse form data
            form_data = await request.form()
            
            # Create SlackCommand domain object
            slack_command = SlackCommand(
                command=form_data.get('command', ''),
                text=form_data.get('text', ''),
                user_id=form_data.get('user_id', ''),
                user_name=form_data.get('user_name', ''),
                channel_id=form_data.get('channel_id', ''),
                channel_name=form_data.get('channel_name', ''),
                team_id=form_data.get('team_id', ''),
                team_domain=form_data.get('team_domain', '')
            )
            
            # Process command
            response = process_use_case.execute(slack_command)
            
            logger.info(f"Processed Slack command: {slack_command.command} from {slack_command.user_name}")
            return response
            
        except InvalidSlackCommandError as e:
            logger.warning(f"Invalid Slack command: {e}")
            return {
                "response_type": "ephemeral",
                "text": f"❌ {str(e)}"
            }
        
        except HTTPException:
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error in slack_command: {e}", exc_info=True)
            return {
                "response_type": "ephemeral",
                "text": "❌ An unexpected error occurred. Please try again."
            }
    
    async def slack_events(
        self,
        request: Request,
        verify_use_case: VerifySlackRequestUseCase = Depends(get_verify_slack_request_use_case)
    ) -> Dict[str, Any]:
        """Handle Slack events API webhook."""
        try:
            # Get request data
            body = await request.body()
            headers = request.headers
            
            # Verify request if signing secret is configured
            timestamp = headers.get('X-Slack-Request-Timestamp')
            signature = headers.get('X-Slack-Signature')
            
            if timestamp and signature:
                is_valid, message = verify_use_case.execute(body, timestamp, signature)
                if not is_valid:
                    logger.warning(f"Invalid Slack request: {message}")
                    raise HTTPException(status_code=401, detail=message)
            
            # Parse JSON data
            try:
                event_data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON payload")
            
            # Handle URL verification challenge
            if event_data.get('type') == 'url_verification':
                return {"challenge": event_data.get('challenge')}
            
            # Handle other events (placeholder for future implementation)
            logger.info(f"Received Slack event: {event_data.get('type')}")
            return {"status": "ok"}
            
        except HTTPException:
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error in slack_events: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")


def create_slack_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Slack API Server",
        description="VCluster provisioning via Slack commands",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Initialize controller
    controller = SlackController()
    
    # Register routes
    app.add_api_route(
        "/health",
        controller.health_check,
        methods=["GET"],
        tags=["health"]
    )
    
    app.add_api_route(
        "/slack/command",
        controller.slack_command,
        methods=["POST"],
        tags=["slack"]
    )
    
    app.add_api_route(
        "/slack/events",
        controller.slack_events,
        methods=["POST"],
        tags=["slack"]
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
