"""Functional tests for pattern-based OAM processing using JSON fixtures."""

import json
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.interface.controllers import create_slack_app
from src.domain.strategies.base import ComponentPattern


class TestPatternFunctional:
    """Functional tests for pattern-based OAM processing with JSON fixtures."""
    
    @classmethod
    def setup_class(cls):
        """Load all test fixtures once for the test class."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "argo_events"
        cls.fixtures = {}
        
        # Load all JSON fixtures
        for pattern_file in ["pattern3_infrastructure.json", "pattern2_compositional.json", 
                             "pattern1_foundational.json", "mixed_patterns.json"]:
            file_path = fixtures_dir / pattern_file
            with open(file_path, 'r') as f:
                cls.fixtures[pattern_file.replace('.json', '')] = json.load(f)
    
    def setup_method(self):
        """Set up test client for each test."""
        self.app = create_slack_app()
        self.client = TestClient(self.app)
    
    @patch('src.interface.dependencies.get_argo_client')
    def test_pattern3_infrastructure_fixtures(self, mock_get_argo_client):
        """Test Pattern 3 infrastructure components using JSON fixtures."""
        # Mock Argo client
        mock_argo = Mock()
        mock_get_argo_client.return_value = mock_argo
        
        # Test each Pattern 3 fixture
        for test_case in self.fixtures['pattern3_infrastructure']:
            print(f"\nTesting: {test_case['name']}")
            
            # Reset mock for each test case
            mock_argo.reset_mock()
            mock_argo.create_workflow_from_template.return_value = Mock(
                metadata=Mock(name=f"workflow-{test_case['name']}")
            )
            
            # Send Argo event to OAM webhook
            response = self.client.post("/oam/webhook", json=test_case['event'])
            
            # Verify response
            assert response.status_code == 200, f"Failed for {test_case['name']}"
            result = response.json()
            assert result["apiVersion"] == "admission.k8s.io/v1"
            assert result["kind"] == "AdmissionReview"
            assert result["response"]["allowed"] is test_case["expected"]["allowed"]
            
            # Debug: print response message
            print(f"Response message: {result['response']['status']['message']}")
            
            # Verify workflow was triggered
            if test_case["expected"]["pattern_counts"]["pattern_3"] > 0:
                # Check if the component requires processing
                if "does not require processing" not in result['response']['status']['message']:
                    assert mock_argo.create_workflow_from_template.called, f"Workflow not triggered for {test_case['name']}"
                
                # Check expected workflow template if workflow was called
                if mock_argo.create_workflow_from_template.called:
                    call_args = mock_argo.create_workflow_from_template.call_args_list[0]
                    assert call_args[1]["workflow_template_name"] == test_case["expected"]["workflow_template"]
                
                # Verify parameters if single component
                if "parameters" in test_case["expected"]:
                    params = call_args[1]["parameters"]
                    for key, expected_value in test_case["expected"]["parameters"].items():
                        assert params.get(key) == expected_value, f"Parameter {key} mismatch"
    
    @patch('src.interface.dependencies.get_argo_client')
    def test_pattern2_compositional_fixtures(self, mock_get_argo_client):
        """Test Pattern 2 compositional components using JSON fixtures."""
        mock_argo = Mock()
        mock_get_argo_client.return_value = mock_argo
        
        for test_case in self.fixtures['pattern2_compositional']:
            print(f"\nTesting: {test_case['name']}")
            
            mock_argo.reset_mock()
            mock_argo.create_workflow_from_template.return_value = Mock(
                metadata=Mock(name=f"workflow-{test_case['name']}")
            )
            
            response = self.client.post("/oam/webhook", json=test_case['event'])
            
            assert response.status_code == 200, f"Failed for {test_case['name']}"
            result = response.json()
            assert result["response"]["allowed"] is test_case["expected"]["allowed"]
            
            # Verify Pattern 2 workflow was triggered
            if test_case["expected"]["pattern_counts"]["pattern_2"] > 0:
                assert mock_argo.create_workflow_from_template.called
                call_args = mock_argo.create_workflow_from_template.call_args_list[0]
                assert call_args[1]["workflow_template_name"] == test_case["expected"]["workflow_template"]
                
                # Check parameters
                if "parameters" in test_case["expected"]:
                    params = call_args[1]["parameters"]
                    for key, expected_value in test_case["expected"]["parameters"].items():
                        assert params.get(key) == expected_value, f"Parameter {key} mismatch for {test_case['name']}"
    
    @patch('src.interface.dependencies.get_argo_client')
    def test_pattern1_foundational_fixtures(self, mock_get_argo_client):
        """Test Pattern 1 foundational components using JSON fixtures."""
        mock_argo = Mock()
        mock_get_argo_client.return_value = mock_argo
        
        for test_case in self.fixtures['pattern1_foundational']:
            print(f"\nTesting: {test_case['name']}")
            
            mock_argo.reset_mock()
            
            # Setup appropriate number of workflow returns for mixed patterns
            if "total_components" in test_case["expected"]:
                workflow_returns = []
                for i in range(test_case["expected"]["total_components"]):
                    workflow_returns.append(Mock(metadata=Mock(name=f"workflow-{i}")))
                mock_argo.create_workflow_from_template.side_effect = workflow_returns
            else:
                mock_argo.create_workflow_from_template.return_value = Mock(
                    metadata=Mock(name=f"workflow-{test_case['name']}")
                )
            
            response = self.client.post("/oam/webhook", json=test_case['event'])
            
            assert response.status_code == 200, f"Failed for {test_case['name']}"
            result = response.json()
            assert result["response"]["allowed"] is test_case["expected"]["allowed"]
            
            # Verify workflow calls
            if test_case["expected"]["pattern_counts"]["pattern_1"] > 0:
                assert mock_argo.create_workflow_from_template.called
                
                # For single webservice, check the workflow template
                if test_case["expected"]["pattern_counts"]["pattern_1"] == 1 and \
                   test_case["expected"]["pattern_counts"]["pattern_3"] == 0:
                    call_args = mock_argo.create_workflow_from_template.call_args_list[0]
                    assert call_args[1]["workflow_template_name"] == test_case["expected"]["workflow_template"]
                    
                    # Verify parameters
                    if "parameters" in test_case["expected"]:
                        params = call_args[1]["parameters"]
                        for key, expected_value in test_case["expected"]["parameters"].items():
                            assert params.get(key) == expected_value, f"Parameter {key} mismatch"
    
    @patch('src.interface.dependencies.get_argo_client')
    def test_mixed_patterns_fixtures(self, mock_get_argo_client):
        """Test mixed pattern processing order using JSON fixtures."""
        mock_argo = Mock()
        mock_get_argo_client.return_value = mock_argo
        
        for test_case in self.fixtures['mixed_patterns']:
            print(f"\nTesting: {test_case['name']}")
            
            mock_argo.reset_mock()
            
            # Track workflow calls
            workflow_calls = []
            
            def track_workflow(*args, **kwargs):
                workflow_name = kwargs["workflow_template_name"]
                workflow_calls.append(workflow_name)
                print(f"  Workflow triggered: {workflow_name}")
                return Mock(metadata=Mock(name=f"workflow-{len(workflow_calls)}"))
            
            mock_argo.create_workflow_from_template.side_effect = track_workflow
            
            response = self.client.post("/oam/webhook", json=test_case['event'])
            
            assert response.status_code == 200, f"Failed for {test_case['name']}"
            result = response.json()
            assert result["response"]["allowed"] is test_case["expected"]["allowed"]
            
            # Verify total components processed
            assert len(workflow_calls) == test_case["expected"]["total_components"]
            
            # Verify pattern counts in response message
            message = result["response"]["status"]["message"]
            
            # Check pattern counts
            for pattern_num in [3, 2, 1]:
                pattern_key = f"pattern_{pattern_num}"
                expected_count = test_case["expected"]["pattern_counts"][pattern_key]
                if expected_count > 0:
                    assert f"Pattern {pattern_num}: {expected_count}" in message, \
                           f"Pattern {pattern_num} count mismatch in message"
            
            # Verify processing order if specified
            if "processing_order" in test_case["expected"]:
                # Check that Pattern 3 workflows are called first
                pattern3_workflows = ["pattern3-infrastructure-workflow", "pattern3-provider-workflow", 
                                     "pattern3-platform-workflow", "realtime-platform-workflow"]
                pattern2_workflows = ["pattern2-compositional-workflow", "identity-service-generator", 
                                     "orchestration-workflow"]
                pattern1_workflows = ["microservice-standard-contract"]
                
                # Find indices of each pattern type
                pattern3_indices = [i for i, w in enumerate(workflow_calls) if w in pattern3_workflows]
                pattern2_indices = [i for i, w in enumerate(workflow_calls) if w in pattern2_workflows]
                pattern1_indices = [i for i, w in enumerate(workflow_calls) if w in pattern1_workflows]
                
                # Verify Pattern 3 comes before Pattern 2 if both exist
                if pattern3_indices and pattern2_indices:
                    assert max(pattern3_indices) < min(pattern2_indices), \
                           "Pattern 3 should be processed before Pattern 2"
                
                # Verify Pattern 2 comes before Pattern 1 if both exist
                if pattern2_indices and pattern1_indices:
                    assert max(pattern2_indices) < min(pattern1_indices), \
                           "Pattern 2 should be processed before Pattern 1"
                
                # Verify Pattern 3 comes before Pattern 1 if both exist
                if pattern3_indices and pattern1_indices:
                    assert max(pattern3_indices) < min(pattern1_indices), \
                           "Pattern 3 should be processed before Pattern 1"
    
    @patch('src.interface.dependencies.get_argo_client')
    def test_error_handling(self, mock_get_argo_client):
        """Test error handling for invalid components."""
        mock_argo = Mock()
        mock_get_argo_client.return_value = mock_argo
        
        # Create invalid event
        invalid_event = {
            "body": json.dumps({
                "apiVersion": "core.oam.dev/v1beta1",
                "kind": "Application",
                "metadata": {
                    "name": "invalid-app",
                    "namespace": "default",
                    "labels": {
                        "app-container": "invalid-monorepo"
                    }
                },
                "spec": {
                    "components": [
                        {
                            "name": "unknown-component",
                            "type": "unknown-type",
                            "properties": {}
                        }
                    ]
                }
            }),
            "operation": "CREATE"
        }
        
        response = self.client.post("/oam/webhook", json=invalid_event)
        
        # Should still allow but indicate the issue
        assert response.status_code == 200
        result = response.json()
        assert result["response"]["allowed"] is True
        
        # Message should indicate processing but potentially with failures
        message = result["response"]["status"]["message"]
        assert "Processed" in message or "does not require processing" in message
    
    @patch('src.interface.dependencies.get_argo_client')
    def test_vcluster_policy_handling(self, mock_get_argo_client):
        """Test that vCluster from topology policy is passed correctly."""
        mock_argo = Mock()
        mock_get_argo_client.return_value = mock_argo
        mock_argo.create_workflow_from_template.return_value = Mock(
            metadata=Mock(name="workflow-vcluster-test")
        )
        
        # Find a test case with vcluster policy
        for test_case in self.fixtures['pattern1_foundational']:
            if 'vcluster' in test_case.get('expected', {}):
                response = self.client.post("/oam/webhook", json=test_case['event'])
                
                assert response.status_code == 200
                result = response.json()
                assert result["response"]["allowed"] is True
                
                # Verify vcluster was passed in parameters
                if mock_argo.create_workflow_from_template.called:
                    call_args = mock_argo.create_workflow_from_template.call_args_list[0]
                    params = call_args[1]["parameters"]
                    assert params.get("vcluster") == test_case["expected"]["vcluster"] or \
                           params.get("target_vcluster") == test_case["expected"]["vcluster"] or \
                           params.get("target-vcluster") == test_case["expected"]["vcluster"], \
                           "vCluster parameter not passed correctly"
                break