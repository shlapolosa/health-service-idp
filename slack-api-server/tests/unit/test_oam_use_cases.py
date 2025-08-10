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


class TestProcessOAMWebhook:
    """Test ProcessOAMWebhook use case."""
    
    def test_process_valid_create_request(self):
        """Test processing a valid CREATE OAM webhook request."""
        # Setup mock argo client
        mock_argo_client = Mock()
        mock_argo_client.trigger_microservice_from_oam.return_value = (True, "workflow-123")
        
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
        
        # Verify argo client was called for both webservices
        assert mock_argo_client.trigger_microservice_from_oam.call_count == 2
        
        # Check first call (api-service)
        first_call = mock_argo_client.trigger_microservice_from_oam.call_args_list[0]
        assert first_call[1]["component"]["name"] == "api-service"
        assert first_call[1]["app_container"] == "my-monorepo"
        assert first_call[1]["vcluster"] == "test-vcluster"
        
        # Check second call (worker-service)
        second_call = mock_argo_client.trigger_microservice_from_oam.call_args_list[1]
        assert second_call[1]["component"]["name"] == "worker-service"
        assert second_call[1]["app_container"] == "my-monorepo"
        assert second_call[1]["vcluster"] == "test-vcluster"
    
    def test_process_update_request(self):
        """Test processing an UPDATE OAM webhook request."""
        mock_argo_client = Mock()
        mock_argo_client.trigger_microservice_from_oam.return_value = (True, "workflow-456")
        
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
        assert mock_argo_client.trigger_microservice_from_oam.call_count == 1
    
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
        mock_argo_client.trigger_microservice_from_oam.assert_not_called()
    
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
        mock_argo_client.trigger_microservice_from_oam.assert_not_called()
    
    def test_skip_no_webservice_components(self):
        """Test that requests without webservice components are skipped."""
        mock_argo_client = Mock()
        
        use_case = ProcessOAMWebhook(argo_client=mock_argo_client)
        
        admission_request = {
            "request": {
                "uid": "no-webservice-uid",
                "operation": "CREATE",
                "object": {
                    "metadata": {
                        "name": "app-no-webservice",
                        "namespace": "default",
                        "labels": {
                            "app-container": "monorepo"
                        }
                    },
                    "spec": {
                        "components": [
                            {
                                "name": "database",
                                "type": "database",
                                "properties": {}
                            },
                            {
                                "name": "cache",
                                "type": "redis",
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
        mock_argo_client.trigger_microservice_from_oam.assert_not_called()
    
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
    
    def test_dry_run_request(self):
        """Test that dry-run requests are processed normally (stateless approach)."""
        mock_argo_client = Mock()
        mock_argo_client.trigger_microservice_from_oam.return_value = (True, "workflow-dry")
        
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
        assert mock_argo_client.trigger_microservice_from_oam.call_count == 1
    
    def test_multiple_components_partial_failure(self):
        """Test processing multiple components with partial failures."""
        mock_argo_client = Mock()
        # First call succeeds, second fails, third succeeds
        mock_argo_client.trigger_microservice_from_oam.side_effect = [
            (True, "workflow-1"),
            (False, "Connection error"),
            (True, "workflow-3")
        ]
        
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
        assert mock_argo_client.trigger_microservice_from_oam.call_count == 3
        # Response should indicate some processing occurred
        assert "Processed" in response["response"]["status"]["message"]
        assert "2" in response["response"]["status"]["message"]  # 2 successful