"""
Unit tests for controller endpoints, especially OAM webhook with Argo Events support
"""

import json
from unittest.mock import Mock, patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from fastapi import Request

from src.interface.controllers import OAMWebhookController
from src.application.oam_use_cases import ProcessOAMWebhook


class TestOAMWebhookController:
    """Test OAM webhook controller with both admission review and Argo Events formats."""
    
    @pytest.mark.asyncio
    async def test_standard_admission_review_format(self):
        """Test processing standard Kubernetes admission review format."""
        controller = OAMWebhookController()
        
        # Mock the process use case
        mock_use_case = Mock(spec=ProcessOAMWebhook)
        mock_use_case.execute.return_value = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": "test-uid",
                "allowed": True,
                "status": {"message": "Processed"}
            }
        }
        
        # Create mock request with standard admission review
        admission_data = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "request": {
                "uid": "test-uid",
                "operation": "CREATE",
                "object": {
                    "metadata": {"name": "test-app"},
                    "spec": {"components": []}
                }
            }
        }
        
        mock_request = AsyncMock(spec=Request)
        mock_request.body = AsyncMock(return_value=json.dumps(admission_data).encode())
        
        # Test the controller
        with patch('src.interface.controllers.get_process_oam_webhook_use_case', return_value=mock_use_case):
            result = await controller.oam_webhook(mock_request, mock_use_case)
        
        # Verify
        assert result["response"]["allowed"] == True
        mock_use_case.execute.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_argo_events_format(self):
        """Test processing Argo Events format (body field with OAM Application)."""
        controller = OAMWebhookController()
        
        # Mock the process use case
        mock_use_case = Mock(spec=ProcessOAMWebhook)
        mock_use_case.execute.return_value = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": "argo-events-trigger",
                "allowed": True,
                "status": {"message": "Processed from Argo Events"}
            }
        }
        
        # Create OAM Application object
        oam_app = {
            "apiVersion": "core.oam.dev/v1beta1",
            "kind": "Application",
            "metadata": {
                "name": "argo-test-app",
                "namespace": "default"
            },
            "spec": {
                "components": [{
                    "name": "test-service",
                    "type": "webservice",
                    "properties": {}
                }]
            }
        }
        
        # Create mock request with Argo Events format (body as JSON string)
        argo_data = {
            "body": json.dumps(oam_app),  # Body is a JSON string
            "operation": "CREATE"
        }
        
        mock_request = AsyncMock(spec=Request)
        mock_request.body = AsyncMock(return_value=json.dumps(argo_data).encode())
        
        # Test the controller
        with patch('src.interface.controllers.get_process_oam_webhook_use_case', return_value=mock_use_case):
            result = await controller.oam_webhook(mock_request, mock_use_case)
        
        # Verify the admission request was properly constructed
        assert result["response"]["allowed"] == True
        mock_use_case.execute.assert_called_once()
        
        # Check that the OAM object was properly wrapped
        call_args = mock_use_case.execute.call_args[0][0]
        assert call_args["request"]["object"]["metadata"]["name"] == "argo-test-app"
        
    @pytest.mark.asyncio
    async def test_argo_events_format_with_object_body(self):
        """Test processing Argo Events format when body is already an object."""
        controller = OAMWebhookController()
        
        # Mock the process use case
        mock_use_case = Mock(spec=ProcessOAMWebhook)
        mock_use_case.execute.return_value = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": "argo-events-trigger",
                "allowed": True,
                "status": {"message": "Processed from Argo Events"}
            }
        }
        
        # Create mock request with Argo Events format (body as object)
        argo_data = {
            "body": {  # Body is already an object
                "apiVersion": "core.oam.dev/v1beta1",
                "kind": "Application",
                "metadata": {
                    "name": "argo-object-app",
                    "namespace": "default"
                },
                "spec": {
                    "components": [{
                        "name": "test-service",
                        "type": "webservice",
                        "properties": {}
                    }]
                }
            },
            "operation": "UPDATE"
        }
        
        mock_request = AsyncMock(spec=Request)
        mock_request.body = AsyncMock(return_value=json.dumps(argo_data).encode())
        
        # Test the controller
        with patch('src.interface.controllers.get_process_oam_webhook_use_case', return_value=mock_use_case):
            result = await controller.oam_webhook(mock_request, mock_use_case)
        
        # Verify
        assert result["response"]["allowed"] == True
        mock_use_case.execute.assert_called_once()
        
        # Check that the OAM object was properly wrapped
        call_args = mock_use_case.execute.call_args[0][0]
        assert call_args["request"]["object"]["metadata"]["name"] == "argo-object-app"
        assert call_args["request"]["operation"] == "UPDATE"
    
    @pytest.mark.asyncio
    async def test_argo_events_with_partial_request_fields(self):
        """Test Argo Events format with some request fields already present."""
        controller = OAMWebhookController()
        
        # Mock the process use case
        mock_use_case = Mock(spec=ProcessOAMWebhook)
        mock_use_case.execute.return_value = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": "custom-uid",
                "allowed": True,
                "status": {"message": "Processed"}
            }
        }
        
        # Create mock request with mixed format
        mixed_data = {
            "body": {
                "metadata": {"name": "mixed-app"},
                "spec": {"components": []}
            },
            "request": {
                "uid": "custom-uid",
                "operation": "UPDATE"
            }
        }
        
        mock_request = AsyncMock(spec=Request)
        mock_request.body = AsyncMock(return_value=json.dumps(mixed_data).encode())
        
        # Test the controller
        with patch('src.interface.controllers.get_process_oam_webhook_use_case', return_value=mock_use_case):
            result = await controller.oam_webhook(mock_request, mock_use_case)
        
        # Verify
        assert result["response"]["allowed"] == True
        call_args = mock_use_case.execute.call_args[0][0]
        assert call_args["request"]["uid"] == "custom-uid"
        assert call_args["request"]["operation"] == "UPDATE"
        
    @pytest.mark.asyncio
    async def test_invalid_json(self):
        """Test handling of invalid JSON in request."""
        controller = OAMWebhookController()
        
        mock_use_case = Mock(spec=ProcessOAMWebhook)
        mock_request = AsyncMock(spec=Request)
        mock_request.body = AsyncMock(return_value=b"invalid json {")
        
        # Test the controller
        result = await controller.oam_webhook(mock_request, mock_use_case)
        
        # Should return allowed=True but with error message
        assert result["response"]["allowed"] == True
        assert "Invalid JSON" in result["response"]["status"]["message"]
        
    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test exception handling in webhook processing."""
        controller = OAMWebhookController()
        
        # Mock use case that raises exception
        mock_use_case = Mock(spec=ProcessOAMWebhook)
        mock_use_case.execute.side_effect = Exception("Test error")
        
        # Create valid request
        admission_data = {
            "request": {
                "uid": "test-uid",
                "object": {"metadata": {"name": "test"}}
            }
        }
        
        mock_request = AsyncMock(spec=Request)
        mock_request.body = AsyncMock(return_value=json.dumps(admission_data).encode())
        
        # Test the controller
        with patch('src.interface.controllers.get_process_oam_webhook_use_case', return_value=mock_use_case):
            result = await controller.oam_webhook(mock_request, mock_use_case)
        
        # Should still allow but with error message
        assert result["response"]["allowed"] == True
        assert "Error processing webhook" in result["response"]["status"]["message"]