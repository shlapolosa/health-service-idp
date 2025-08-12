"""
Unit tests for OAM webhook domain services
"""

from unittest.mock import Mock, MagicMock, patch
import pytest

from src.domain.services import OAMWebhookService
from src.domain.models import (
    OAMApplication, OAMComponent, OAMWebhookRequest, OAMWebhookResponse
)


class TestOAMWebhookService:
    """Test OAMWebhookService domain service."""
    
    @patch('src.domain.strategies.orchestrator.PatternOrchestrator')
    def test_process_valid_webhook_request(self, mock_orchestrator_class):
        """Test processing a valid OAM webhook request with PatternOrchestrator."""
        # Setup
        service = OAMWebhookService()
        mock_argo_client = Mock()
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Mock successful processing results
        mock_results = [
            Mock(success=True, workflow_name="microservice-standard-contract", 
                 workflow_run_name="run-api", error=None),
            Mock(success=True, workflow_name="microservice-standard-contract",
                 workflow_run_name="run-worker", error=None)
        ]
        mock_orchestrator.handle_oam_application.return_value = mock_results
        
        # Mock processing summary
        mock_summary = {
            "total": 2,
            "successful": 2,
            "failed": 0,
            "by_pattern": {
                "pattern_3": {"successful": 0, "failed": 0},
                "pattern_2": {"successful": 0, "failed": 0},
                "pattern_1": {"successful": 2, "failed": 0}  # Both are Pattern 1 (webservice)
            },
            "workflows_triggered": [
                {"workflow": "microservice-standard-contract", "run": "run-api"},
                {"workflow": "microservice-standard-contract", "run": "run-worker"}
            ],
            "errors": []
        }
        mock_orchestrator.get_processing_summary.return_value = mock_summary
        
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
        assert "Pattern 1: 2" in response.message  # Both are Pattern 1 webservices
        assert len(response.triggered_workflows) == 2
        
        # Verify orchestrator was initialized with argo client
        mock_orchestrator_class.assert_called_once_with(mock_argo_client)
        
        # Verify orchestrator.handle_oam_application was called
        mock_orchestrator.handle_oam_application.assert_called_once()
        call_args = mock_orchestrator.handle_oam_application.call_args
        
        # Check OAM app structure was passed correctly
        oam_app_dict = call_args[1]["oam_application"]
        assert oam_app_dict["metadata"]["name"] == "test-app"
        assert len(oam_app_dict["spec"]["components"]) == 2
        assert call_args[1]["vcluster"] == "vcluster-1"
    
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
        
        # Argo client should not be called since we detect early that processing not needed
        mock_argo_client.assert_not_called()
    
    @patch('src.domain.strategies.orchestrator.PatternOrchestrator')
    def test_handle_workflow_trigger_failure(self, mock_orchestrator_class):
        """Test handling failures in workflow triggering."""
        service = OAMWebhookService()
        mock_argo_client = Mock()
        
        # Mock orchestrator with failure
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Mock failed processing results
        mock_results = [
            Mock(success=False, workflow_name=None, 
                 workflow_run_name=None, error="Connection failed")
        ]
        mock_orchestrator.handle_oam_application.return_value = mock_results
        
        # Mock processing summary with failure
        mock_summary = {
            "total": 1,
            "successful": 0,
            "failed": 1,
            "by_pattern": {
                "pattern_3": {"successful": 0, "failed": 0},
                "pattern_2": {"successful": 0, "failed": 0},
                "pattern_1": {"successful": 0, "failed": 1}
            },
            "workflows_triggered": [],
            "errors": ["Connection failed"]
        }
        mock_orchestrator.get_processing_summary.return_value = mock_summary
        
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
        assert "1 failed" in response.message
        assert len(response.triggered_workflows) == 0
    
    @patch('src.domain.strategies.orchestrator.PatternOrchestrator')
    def test_handle_workflow_trigger_exception(self, mock_orchestrator_class):
        """Test handling exceptions in workflow triggering."""
        service = OAMWebhookService()
        mock_argo_client = Mock()
        
        # Mock orchestrator that raises exception
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.handle_oam_application.side_effect = Exception("Unexpected error")
        
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
        
        # This should raise since we don't catch exceptions at this level
        with pytest.raises(Exception) as exc_info:
            response = service.process_oam_webhook(request, mock_argo_client)
        
        assert "Unexpected error" in str(exc_info.value)
    
    @patch('src.domain.strategies.orchestrator.PatternOrchestrator')
    def test_process_with_no_vcluster(self, mock_orchestrator_class):
        """Test processing when no vCluster is specified."""
        service = OAMWebhookService()
        mock_argo_client = Mock()
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Mock processing results
        mock_results = [
            Mock(success=True, workflow_name="microservice-standard-contract", 
                 workflow_run_name="run-456", error=None)
        ]
        mock_orchestrator.handle_oam_application.return_value = mock_results
        
        # Mock processing summary
        mock_summary = {
            "total": 1,
            "successful": 1,
            "failed": 0,
            "by_pattern": {
                "pattern_3": {"successful": 0, "failed": 0},
                "pattern_2": {"successful": 0, "failed": 0},
                "pattern_1": {"successful": 1, "failed": 0}
            },
            "workflows_triggered": [
                {"workflow": "microservice-standard-contract", "run": "run-456"}
            ],
            "errors": []
        }
        mock_orchestrator.get_processing_summary.return_value = mock_summary
        
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
        
        # Check vcluster parameter in orchestrator call
        call_args = mock_orchestrator.handle_oam_application.call_args
        # When no vcluster specified, it gets None (which becomes empty string later)
        assert call_args[1]["vcluster"] is None or call_args[1]["vcluster"] == ""
    
    @patch('src.domain.strategies.orchestrator.PatternOrchestrator')
    def test_mixed_component_types(self, mock_orchestrator_class):
        """Test processing application with mixed component types."""
        service = OAMWebhookService()
        mock_argo_client = Mock()
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Mock processing results - redis is Pattern 3, webservices are Pattern 1
        mock_results = [
            Mock(success=True, workflow_name="pattern3-infrastructure-workflow", 
                 workflow_run_name="run-redis", error=None),
            Mock(success=True, workflow_name="microservice-standard-contract", 
                 workflow_run_name="run-api", error=None),
            Mock(success=True, workflow_name="microservice-standard-contract",
                 workflow_run_name="run-worker", error=None),
            Mock(success=False, workflow_name=None,
                 workflow_run_name=None, error="Unknown type: database")
        ]
        mock_orchestrator.handle_oam_application.return_value = mock_results
        
        # Mock processing summary
        mock_summary = {
            "total": 4,
            "successful": 3,
            "failed": 1,
            "by_pattern": {
                "pattern_3": {"successful": 1, "failed": 0},  # redis
                "pattern_2": {"successful": 0, "failed": 0},
                "pattern_1": {"successful": 2, "failed": 1}  # webservices + unknown database
            },
            "workflows_triggered": [
                {"workflow": "pattern3-infrastructure-workflow", "run": "run-redis"},
                {"workflow": "microservice-standard-contract", "run": "run-api"},
                {"workflow": "microservice-standard-contract", "run": "run-worker"}
            ],
            "errors": ["Unknown type: database"]
        }
        mock_orchestrator.get_processing_summary.return_value = mock_summary
        
        app = OAMApplication(
            name="mixed-app",
            namespace="default",
            components=[
                OAMComponent(name="api", type="webservice", properties={}),
                OAMComponent(name="db", type="database", properties={}),  # Not webservice
                OAMComponent(name="worker", type="webservice", properties={}),
                OAMComponent(name="cache", type="redis", properties={})  # Pattern 3
            ],
            labels={"app-container": "monorepo"}
        )
        
        request = OAMWebhookRequest(
            uid="mixed-uid",
            operation="CREATE",
            oam_application=app
        )
        
        response = service.process_oam_webhook(request, mock_argo_client)
        
        # Should process all components with pattern-based handling
        assert response.allowed is True
        assert "Processed 4 components" in response.message
        assert "Pattern 3: 1" in response.message  # redis
        assert "Pattern 1: 2" in response.message  # webservices
        assert "1 failed" in response.message  # unknown database type
        assert len(response.triggered_workflows) == 3  # Only successful ones
    
    @patch('src.domain.strategies.orchestrator.PatternOrchestrator')
    def test_partial_success_handling(self, mock_orchestrator_class):
        """Test handling partial success in multiple component processing."""
        service = OAMWebhookService()
        mock_argo_client = Mock()
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # First succeeds, second fails, third succeeds
        mock_results = [
            Mock(success=True, workflow_name="microservice-standard-contract",
                 workflow_run_name="workflow-1", error=None),
            Mock(success=False, workflow_name=None,
                 workflow_run_name=None, error="Failed"),
            Mock(success=True, workflow_name="microservice-standard-contract",
                 workflow_run_name="workflow-3", error=None)
        ]
        mock_orchestrator.handle_oam_application.return_value = mock_results
        
        # Mock processing summary
        mock_summary = {
            "total": 3,
            "successful": 2,
            "failed": 1,
            "by_pattern": {
                "pattern_3": {"successful": 0, "failed": 0},
                "pattern_2": {"successful": 0, "failed": 0},
                "pattern_1": {"successful": 2, "failed": 1}
            },
            "workflows_triggered": [
                {"workflow": "microservice-standard-contract", "run": "workflow-1"},
                {"workflow": "microservice-standard-contract", "run": "workflow-3"}
            ],
            "errors": ["Failed"]
        }
        mock_orchestrator.get_processing_summary.return_value = mock_summary
        
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
        assert "Processed 3 components" in response.message
        assert "Pattern 1: 2" in response.message  # 2 successful
        assert "1 failed" in response.message
        assert len(response.triggered_workflows) == 2