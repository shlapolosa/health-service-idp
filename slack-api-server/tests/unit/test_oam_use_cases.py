"""
Unit tests for OAM webhook use cases
"""

import json
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.application.oam_use_cases import ProcessOAMWebhook
from src.domain.models import (
    OAMApplication, OAMComponent, OAMWebhookRequest, OAMWebhookResponse
)
from src.domain.strategies.base import HandlerResult, ComponentPattern


class TestProcessOAMWebhook:
    """Test ProcessOAMWebhook use case."""
    
    @patch('src.domain.strategies.orchestrator.PatternOrchestrator')
    def test_process_valid_create_request(self, mock_orchestrator_class):
        """Test processing a valid CREATE OAM webhook request."""
        # Setup mock argo client
        mock_argo_client = Mock()
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Mock successful processing results
        mock_results = [
            Mock(success=True, workflow_name="microservice-standard-contract", 
                 workflow_run_name="run-123", error=None, pattern=ComponentPattern.FOUNDATIONAL),
            Mock(success=True, workflow_name="microservice-standard-contract",
                 workflow_run_name="run-456", error=None, pattern=ComponentPattern.FOUNDATIONAL)
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
                "pattern_1": {"successful": 2, "failed": 0}
            },
            "workflows_triggered": [
                {"workflow": "microservice-standard-contract", "run": "run-123"},
                {"workflow": "microservice-standard-contract", "run": "run-456"}
            ],
            "errors": []
        }
        mock_orchestrator.get_processing_summary.return_value = mock_summary
        
        # Create use case
        use_case = ProcessOAMWebhook(argo_client=mock_argo_client)
        
        # Create admission request
        admission_request = {
            "request": {
                "uid": "test-uid-123",
                "operation": "CREATE",
                "object": {
                    "metadata": {
                        "name": "test-app",
                        "namespace": "default",
                        "labels": {
                            "app-container": "my-monorepo"
                        }
                    },
                    "spec": {
                        "components": [
                            {
                                "name": "api-service",
                                "type": "webservice",
                                "properties": {
                                    "language": "python",
                                    "framework": "fastapi"
                                }
                            },
                            {
                                "name": "worker-service",
                                "type": "webservice",
                                "properties": {
                                    "language": "java",
                                    "framework": "springboot"
                                }
                            }
                        ],
                        "policies": [
                            {
                                "type": "topology",
                                "properties": {
                                    "clusters": ["test-vcluster"]
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        # Execute
        response = use_case.execute(admission_request)
        
        # Verify response structure
        assert response["apiVersion"] == "admission.k8s.io/v1"
        assert response["kind"] == "AdmissionReview"
        assert response["response"]["uid"] == "test-uid-123"
        assert response["response"]["allowed"] is True
        
        # Verify orchestrator was initialized and called
        mock_orchestrator_class.assert_called_once_with(mock_argo_client)
        mock_orchestrator.handle_oam_application.assert_called_once()
        
        # Check orchestrator was called with correct parameters
        call_args = mock_orchestrator.handle_oam_application.call_args
        oam_app_dict = call_args[1]["oam_application"]
        assert oam_app_dict["metadata"]["name"] == "test-app"
        assert len(oam_app_dict["spec"]["components"]) == 2
        assert call_args[1]["vcluster"] == "test-vcluster"
        assert call_args[1]["namespace"] == "default"
    
    @patch('src.domain.strategies.orchestrator.PatternOrchestrator')
    def test_process_update_request(self, mock_orchestrator_class):
        """Test processing an UPDATE OAM webhook request."""
        mock_argo_client = Mock()
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Mock successful processing result
        mock_results = [
            Mock(success=True, workflow_name="microservice-standard-contract", 
                 workflow_run_name="run-789", error=None, pattern=ComponentPattern.FOUNDATIONAL)
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
                {"workflow": "microservice-standard-contract", "run": "run-789"}
            ],
            "errors": []
        }
        mock_orchestrator.get_processing_summary.return_value = mock_summary
        
        use_case = ProcessOAMWebhook(argo_client=mock_argo_client)
        
        admission_request = {
            "request": {
                "uid": "update-uid-456",
                "operation": "UPDATE",
                "object": {
                    "metadata": {
                        "name": "existing-app",
                        "namespace": "production",
                        "labels": {
                            "app-container": "prod-monorepo"
                        }
                    },
                    "spec": {
                        "components": [
                            {
                                "name": "updated-service",
                                "type": "webservice",
                                "properties": {
                                    "language": "python"
                                }
                            }
                        ],
                        "policies": []
                    }
                }
            }
        }
        
        response = use_case.execute(admission_request)
        
        assert response["response"]["allowed"] is True
        # Verify orchestrator was called
        mock_orchestrator.handle_oam_application.assert_called_once()
    
    def test_skip_delete_operation(self):
        """Test that DELETE operations are skipped."""
        mock_argo_client = Mock()
        
        use_case = ProcessOAMWebhook(argo_client=mock_argo_client)
        
        admission_request = {
            "request": {
                "uid": "delete-uid-789",
                "operation": "DELETE",
                "object": {
                    "metadata": {
                        "name": "app-to-delete",
                        "namespace": "default",
                        "labels": {
                            "app-container": "monorepo"
                        }
                    },
                    "spec": {
                        "components": [
                            {
                                "name": "service",
                                "type": "webservice",
                                "properties": {}
                            }
                        ]
                    }
                }
            }
        }
        
        response = use_case.execute(admission_request)
        
        assert response["response"]["allowed"] is True
        assert "does not require processing" in response["response"]["status"]["message"]
        # Argo client should not be called for DELETE
        mock_argo_client.assert_not_called()
    
    def test_skip_no_app_container_label(self):
        """Test that requests without app-container label are skipped."""
        mock_argo_client = Mock()
        
        use_case = ProcessOAMWebhook(argo_client=mock_argo_client)
        
        admission_request = {
            "request": {
                "uid": "no-label-uid",
                "operation": "CREATE",
                "object": {
                    "metadata": {
                        "name": "app-without-label",
                        "namespace": "default",
                        "labels": {}  # No app-container label
                    },
                    "spec": {
                        "components": [
                            {
                                "name": "service",
                                "type": "webservice",
                                "properties": {}
                            }
                        ]
                    }
                }
            }
        }
        
        response = use_case.execute(admission_request)
        
        assert response["response"]["allowed"] is True
        assert "does not require processing" in response["response"]["status"]["message"]
        mock_argo_client.assert_not_called()
    
    def test_skip_no_processable_components(self):
        """Test that requests with only unknown component types are skipped."""
        mock_argo_client = Mock()
        
        use_case = ProcessOAMWebhook(argo_client=mock_argo_client)
        
        admission_request = {
            "request": {
                "uid": "no-processable-uid",
                "operation": "CREATE",
                "object": {
                    "metadata": {
                        "name": "app-no-processable",
                        "namespace": "default",
                        "labels": {
                            "app-container": "monorepo"
                        }
                    },
                    "spec": {
                        "components": [
                            {
                                "name": "unknown1",
                                "type": "database",  # Unknown type
                                "properties": {}
                            },
                            {
                                "name": "unknown2",
                                "type": "custom-type",  # Unknown type
                                "properties": {}
                            }
                        ]
                    }
                }
            }
        }
        
        response = use_case.execute(admission_request)
        
        assert response["response"]["allowed"] is True
        assert "does not require processing" in response["response"]["status"]["message"]
        mock_argo_client.assert_not_called()
    
    def test_handle_argo_client_failure(self):
        """Test handling of Argo client failures."""
        mock_argo_client = Mock()
        mock_argo_client.trigger_microservice_from_oam.return_value = (False, "Connection failed")
        
        use_case = ProcessOAMWebhook(argo_client=mock_argo_client)
        
        admission_request = {
            "request": {
                "uid": "failure-uid",
                "operation": "CREATE",
                "object": {
                    "metadata": {
                        "name": "app-with-failure",
                        "namespace": "default",
                        "labels": {
                            "app-container": "monorepo"
                        }
                    },
                    "spec": {
                        "components": [
                            {
                                "name": "failing-service",
                                "type": "webservice",
                                "properties": {}
                            }
                        ]
                    }
                }
            }
        }
        
        response = use_case.execute(admission_request)
        
        # Should still allow (not block deployments)
        assert response["response"]["allowed"] is True
        assert response["response"]["uid"] == "failure-uid"
        # Message should indicate processing occurred
        assert "Processed" in response["response"]["status"]["message"]
    
    def test_handle_argo_client_exception(self):
        """Test handling of Argo client exceptions."""
        mock_argo_client = Mock()
        mock_argo_client.trigger_microservice_from_oam.side_effect = Exception("Unexpected error")
        
        use_case = ProcessOAMWebhook(argo_client=mock_argo_client)
        
        admission_request = {
            "request": {
                "uid": "exception-uid",
                "operation": "CREATE",
                "object": {
                    "metadata": {
                        "name": "app-with-exception",
                        "namespace": "default",
                        "labels": {
                            "app-container": "monorepo"
                        }
                    },
                    "spec": {
                        "components": [
                            {
                                "name": "error-service",
                                "type": "webservice",
                                "properties": {}
                            }
                        ]
                    }
                }
            }
        }
        
        response = use_case.execute(admission_request)
        
        # Should still allow (not block deployments)
        assert response["response"]["allowed"] is True
        assert response["response"]["uid"] == "exception-uid"
    
    def test_handle_invalid_json(self):
        """Test handling of invalid JSON in admission request."""
        mock_argo_client = Mock()
        
        use_case = ProcessOAMWebhook(argo_client=mock_argo_client)
        
        # Admission request with missing required fields
        admission_request = {
            "request": {
                "uid": "invalid-uid"
                # Missing operation and object
            }
        }
        
        response = use_case.execute(admission_request)
        
        # Should allow but not process (missing required fields)
        assert response["response"]["allowed"] is True
        # Since operation is missing, should_process will return False
        assert "does not require processing" in response["response"]["status"]["message"]
    
    @patch('src.domain.strategies.orchestrator.PatternOrchestrator')
    def test_dry_run_request(self, mock_orchestrator_class):
        """Test that dry-run requests are processed normally (stateless approach)."""
        mock_argo_client = Mock()
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Mock successful processing result
        mock_results = [
            Mock(success=True, workflow_name="microservice-standard-contract", 
                 workflow_run_name="workflow-dry", error=None, pattern=ComponentPattern.FOUNDATIONAL)
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
                {"workflow": "microservice-standard-contract", "run": "workflow-dry"}
            ],
            "errors": []
        }
        mock_orchestrator.get_processing_summary.return_value = mock_summary
        
        use_case = ProcessOAMWebhook(argo_client=mock_argo_client)
        
        admission_request = {
            "request": {
                "uid": "dry-run-uid",
                "operation": "CREATE",
                "dryRun": True,
                "object": {
                    "metadata": {
                        "name": "dry-run-app",
                        "namespace": "default",
                        "labels": {
                            "app-container": "monorepo"
                        }
                    },
                    "spec": {
                        "components": [
                            {
                                "name": "dry-service",
                                "type": "webservice",
                                "properties": {}
                            }
                        ]
                    }
                }
            }
        }
        
        response = use_case.execute(admission_request)
        
        assert response["response"]["allowed"] is True
        # In stateless approach, dry-run still triggers workflows
        # (ApplicationClaim will handle idempotency)
        mock_orchestrator.handle_oam_application.assert_called_once()
    
    @patch('src.domain.strategies.orchestrator.PatternOrchestrator')
    def test_multiple_components_partial_failure(self, mock_orchestrator_class):
        """Test processing multiple components with partial failures."""
        mock_argo_client = Mock()
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Mock partial success results - first succeeds, second fails, third succeeds
        mock_results = [
            Mock(success=True, workflow_name="microservice-standard-contract", 
                 workflow_run_name="workflow-1", error=None, pattern=ComponentPattern.FOUNDATIONAL),
            Mock(success=False, workflow_name=None,
                 workflow_run_name=None, error="Connection error", pattern=ComponentPattern.FOUNDATIONAL),
            Mock(success=True, workflow_name="microservice-standard-contract",
                 workflow_run_name="workflow-3", error=None, pattern=ComponentPattern.FOUNDATIONAL)
        ]
        mock_orchestrator.handle_oam_application.return_value = mock_results
        
        # Mock processing summary with partial failure
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
            "errors": ["Connection error"]
        }
        mock_orchestrator.get_processing_summary.return_value = mock_summary
        
        use_case = ProcessOAMWebhook(argo_client=mock_argo_client)
        
        admission_request = {
            "request": {
                "uid": "multi-uid",
                "operation": "CREATE",
                "object": {
                    "metadata": {
                        "name": "multi-app",
                        "namespace": "default",
                        "labels": {
                            "app-container": "monorepo"
                        }
                    },
                    "spec": {
                        "components": [
                            {
                                "name": "service-1",
                                "type": "webservice",
                                "properties": {}
                            },
                            {
                                "name": "service-2",
                                "type": "webservice",
                                "properties": {}
                            },
                            {
                                "name": "service-3",
                                "type": "webservice",
                                "properties": {}
                            }
                        ]
                    }
                }
            }
        }
        
        response = use_case.execute(admission_request)
        
        # Should still allow despite partial failure
        assert response["response"]["allowed"] is True
        # Verify orchestrator was called
        mock_orchestrator.handle_oam_application.assert_called_once()
        # Response should indicate some processing occurred
        assert "Processed" in response["response"]["status"]["message"]
        assert "3" in response["response"]["status"]["message"]  # 3 total processed
        assert "Pattern 1: 2" in response["response"]["status"]["message"]  # 2 successful
        assert "1 failed" in response["response"]["status"]["message"]  # 1 failed