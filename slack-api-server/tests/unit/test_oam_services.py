"""
Unit tests for OAM webhook domain services
"""

from unittest.mock import Mock, MagicMock
import pytest

from src.domain.services import OAMWebhookService
from src.domain.models import (
    OAMApplication, OAMComponent, OAMWebhookRequest, OAMWebhookResponse
)


class TestOAMWebhookService:
    """Test OAMWebhookService domain service."""
    
    def test_process_valid_webhook_request(self):
        """Test processing a valid OAM webhook request."""
        # Setup
        service = OAMWebhookService()
        mock_argo_client = Mock()
        mock_argo_client.trigger_microservice_from_oam.return_value = (True, "workflow-123")
        
        # Create OAM application
        app = OAMApplication(
            name="test-app",
            namespace="default",
            components=[
                OAMComponent(
                    name="api",
                    type="webservice",
                    properties={"language": "python"}
                ),
                OAMComponent(
                    name="worker",
                    type="webservice",
                    properties={"language": "java"}
                )
            ],
            labels={"app-container": "my-monorepo"},
            policies=[
                {"type": "topology", "properties": {"clusters": ["vcluster-1"]}}
            ]
        )
        
        request = OAMWebhookRequest(
            uid="test-uid",
            operation="CREATE",
            oam_application=app
        )
        
        # Execute
        response = service.process_oam_webhook(request, mock_argo_client)
        
        # Verify
        assert isinstance(response, OAMWebhookResponse)
        assert response.uid == "test-uid"
        assert response.allowed is True
        assert "Processed 2 components" in response.message
        assert len(response.triggered_workflows) == 2
        
        # Verify argo client was called correctly
        assert mock_argo_client.trigger_microservice_from_oam.call_count == 2
        
        # Check first call
        first_call = mock_argo_client.trigger_microservice_from_oam.call_args_list[0]
        assert first_call[1]["component"]["name"] == "api"
        assert first_call[1]["app_container"] == "my-monorepo"
        assert first_call[1]["vcluster"] == "vcluster-1"
        
        # Check second call
        second_call = mock_argo_client.trigger_microservice_from_oam.call_args_list[1]
        assert second_call[1]["component"]["name"] == "worker"
        assert second_call[1]["app_container"] == "my-monorepo"
        assert second_call[1]["vcluster"] == "vcluster-1"
    
    def test_skip_non_processable_request(self):
        """Test skipping requests that shouldn't be processed."""
        service = OAMWebhookService()
        mock_argo_client = Mock()
        
        # Create app without app-container label
        app = OAMApplication(
            name="test-app",
            namespace="default",
            components=[
                OAMComponent(name="api", type="webservice", properties={})
            ],
            labels={}  # No app-container
        )
        
        request = OAMWebhookRequest(
            uid="skip-uid",
            operation="CREATE",
            oam_application=app
        )
        
        response = service.process_oam_webhook(request, mock_argo_client)
        
        assert response.uid == "skip-uid"
        assert response.allowed is True
        assert "does not require processing" in response.message
        assert len(response.triggered_workflows) == 0
        
        # Argo client should not be called
        mock_argo_client.trigger_microservice_from_oam.assert_not_called()
    
    def test_handle_workflow_trigger_failure(self):
        """Test handling failures in workflow triggering."""
        service = OAMWebhookService()
        mock_argo_client = Mock()
        mock_argo_client.trigger_microservice_from_oam.return_value = (False, "Connection failed")
        
        app = OAMApplication(
            name="test-app",
            namespace="default",
            components=[
                OAMComponent(name="failing-service", type="webservice", properties={})
            ],
            labels={"app-container": "monorepo"}
        )
        
        request = OAMWebhookRequest(
            uid="fail-uid",
            operation="CREATE",
            oam_application=app
        )
        
        response = service.process_oam_webhook(request, mock_argo_client)
        
        # Should still return success (resilient approach)
        assert response.allowed is True
        assert "Processed 0 components" in response.message
        assert len(response.triggered_workflows) == 0
    
    def test_handle_workflow_trigger_exception(self):
        """Test handling exceptions in workflow triggering."""
        service = OAMWebhookService()
        mock_argo_client = Mock()
        mock_argo_client.trigger_microservice_from_oam.side_effect = Exception("Unexpected error")
        
        app = OAMApplication(
            name="test-app",
            namespace="default",
            components=[
                OAMComponent(name="error-service", type="webservice", properties={})
            ],
            labels={"app-container": "monorepo"}
        )
        
        request = OAMWebhookRequest(
            uid="error-uid",
            operation="CREATE",
            oam_application=app
        )
        
        response = service.process_oam_webhook(request, mock_argo_client)
        
        # Should still return success (resilient approach)
        assert response.allowed is True
        assert "Processed 0 components" in response.message
        assert len(response.triggered_workflows) == 0
    
    def test_process_with_no_vcluster(self):
        """Test processing when no vCluster is specified."""
        service = OAMWebhookService()
        mock_argo_client = Mock()
        mock_argo_client.trigger_microservice_from_oam.return_value = (True, "workflow-456")
        
        app = OAMApplication(
            name="test-app",
            namespace="default",
            components=[
                OAMComponent(name="api", type="webservice", properties={})
            ],
            labels={"app-container": "monorepo"},
            policies=[]  # No topology policy
        )
        
        request = OAMWebhookRequest(
            uid="no-vcluster-uid",
            operation="CREATE",
            oam_application=app
        )
        
        response = service.process_oam_webhook(request, mock_argo_client)
        
        assert response.allowed is True
        assert mock_argo_client.trigger_microservice_from_oam.call_count == 1
        
        # Check vcluster parameter is empty string
        call_args = mock_argo_client.trigger_microservice_from_oam.call_args_list[0]
        assert call_args[1]["vcluster"] == ""
    
    def test_mixed_component_types(self):
        """Test processing application with mixed component types."""
        service = OAMWebhookService()
        mock_argo_client = Mock()
        mock_argo_client.trigger_microservice_from_oam.return_value = (True, "workflow-789")
        
        app = OAMApplication(
            name="mixed-app",
            namespace="default",
            components=[
                OAMComponent(name="api", type="webservice", properties={}),
                OAMComponent(name="db", type="database", properties={}),  # Not webservice
                OAMComponent(name="worker", type="webservice", properties={}),
                OAMComponent(name="cache", type="redis", properties={})  # Not webservice
            ],
            labels={"app-container": "monorepo"}
        )
        
        request = OAMWebhookRequest(
            uid="mixed-uid",
            operation="CREATE",
            oam_application=app
        )
        
        response = service.process_oam_webhook(request, mock_argo_client)
        
        # Should only process webservice components
        assert response.allowed is True
        assert "Processed 2 components" in response.message
        assert mock_argo_client.trigger_microservice_from_oam.call_count == 2
        
        # Verify only webservices were processed
        call_names = [
            call[1]["component"]["name"] 
            for call in mock_argo_client.trigger_microservice_from_oam.call_args_list
        ]
        assert "api" in call_names
        assert "worker" in call_names
        assert "db" not in call_names
        assert "cache" not in call_names
    
    def test_partial_success_handling(self):
        """Test handling partial success in multiple component processing."""
        service = OAMWebhookService()
        mock_argo_client = Mock()
        
        # First succeeds, second fails, third succeeds
        mock_argo_client.trigger_microservice_from_oam.side_effect = [
            (True, "workflow-1"),
            (False, "Failed"),
            (True, "workflow-3")
        ]
        
        app = OAMApplication(
            name="partial-app",
            namespace="default",
            components=[
                OAMComponent(name="service-1", type="webservice", properties={}),
                OAMComponent(name="service-2", type="webservice", properties={}),
                OAMComponent(name="service-3", type="webservice", properties={})
            ],
            labels={"app-container": "monorepo"}
        )
        
        request = OAMWebhookRequest(
            uid="partial-uid",
            operation="CREATE",
            oam_application=app
        )
        
        response = service.process_oam_webhook(request, mock_argo_client)
        
        assert response.allowed is True
        assert "Processed 2 components" in response.message  # 2 successful
        assert len(response.triggered_workflows) == 2
        assert mock_argo_client.trigger_microservice_from_oam.call_count == 3