"""Functional tests for Slack command processing using JSON fixtures."""

import json
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.interface.controllers import create_slack_app


class TestSlackCommandFunctional:
    """Functional tests for Slack command processing with JSON fixtures."""
    
    @classmethod
    def setup_class(cls):
        """Load all test fixtures once for the test class."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "slack_commands"
        cls.fixtures = {}
        
        # Load JSON fixtures
        fixture_file = fixtures_dir / "pattern_commands.json"
        with open(fixture_file, 'r') as f:
            cls.fixtures['commands'] = json.load(f)
    
    def setup_method(self):
        """Set up test client for each test."""
        self.app = create_slack_app()
        self.client = TestClient(self.app)
    
    @patch('src.interface.dependencies.get_slack_verifier')
    @patch('src.interface.dependencies.get_vcluster_dispatcher')
    def test_microservice_commands(self, mock_get_dispatcher, mock_get_slack_verifier):
        """Test microservice creation via Slack commands."""
        # Mock dependencies
        mock_dispatcher = Mock()
        mock_get_dispatcher.return_value = mock_dispatcher
        mock_verifier = Mock()
        mock_verifier.verify_request.return_value = True
        mock_get_slack_verifier.return_value = mock_verifier
        
        # Test microservice commands
        microservice_tests = [
            "create_single_microservice",
            "create_java_microservice"
        ]
        
        for test_name in microservice_tests:
            test_case = next(tc for tc in self.fixtures['commands'] if tc['name'] == test_name)
            print(f"\nTesting: {test_case['name']}")
            
            # Reset mock
            mock_dispatcher.reset_mock()
            mock_dispatcher.trigger_microservice_creation.return_value = (True, "Workflow triggered successfully")
            
            # Send Slack command
            response = self.client.post("/slack/command", data=test_case['event'])
            
            # Verify response
            assert response.status_code == 200, f"Failed for {test_case['name']}"
            result = response.json()
            
            if test_case['expected']['success']:
                assert "started" in result.get('text', '').lower() or "triggered" in result.get('text', '').lower() or "success" in result.get('text', '').lower()
                
                # Verify dispatcher was called
                assert mock_dispatcher.trigger_microservice_creation.called
                call_args = mock_dispatcher.trigger_microservice_creation.call_args[0][0]
                
                # Verify key parameters - microservice uses different param names
                assert call_args.get("microservice-name") == test_case['expected']['parameters']['name'] or \
                       call_args.get("name") == test_case['expected']['parameters']['name']
                assert call_args.get("language") == test_case['expected']['parameters']['language']
    
    @patch('src.interface.dependencies.get_slack_verifier')
    @patch('src.interface.dependencies.get_vcluster_dispatcher')
    def test_vcluster_commands(self, mock_get_dispatcher, mock_get_slack_verifier):
        """Test VCluster creation via Slack commands."""
        # Mock dependencies
        mock_dispatcher = Mock()
        mock_get_dispatcher.return_value = mock_dispatcher
        mock_verifier = Mock()
        mock_verifier.verify_request.return_value = True
        mock_get_slack_verifier.return_value = mock_verifier
        
        # Test VCluster commands
        vcluster_tests = [
            "create_vcluster_infrastructure"
        ]
        
        for test_name in vcluster_tests:
            test_case = next(tc for tc in self.fixtures['commands'] if tc['name'] == test_name)
            print(f"\nTesting: {test_case['name']}")
            
            # Reset mock
            mock_dispatcher.reset_mock()
            mock_dispatcher.trigger_vcluster_creation.return_value = (True, "VCluster creation triggered")
            
            # Send Slack command
            response = self.client.post("/slack/command", data=test_case['event'])
            
            # Verify response
            assert response.status_code == 200, f"Failed for {test_case['name']}"
            result = response.json()
            
            if test_case['expected']['success']:
                # Check if response indicates success
                response_text = result.get('text', '').lower()
                assert "started" in response_text or "triggered" in response_text or "creating" in response_text
                
                # Verify dispatcher was called
                assert mock_dispatcher.trigger_vcluster_creation.called
                call_args = mock_dispatcher.trigger_vcluster_creation.call_args[0][0]
                
                # Verify VCluster was requested - just check the call was made with data
                assert call_args is not None
                assert len(call_args) > 0
    
    @patch('src.interface.dependencies.get_slack_verifier')
    @patch('src.interface.dependencies.get_vcluster_dispatcher')
    def test_appcontainer_commands(self, mock_get_dispatcher, mock_get_slack_verifier):
        """Test AppContainer creation via Slack commands."""
        # Mock dependencies
        mock_dispatcher = Mock()
        mock_get_dispatcher.return_value = mock_dispatcher
        mock_verifier = Mock()
        mock_verifier.verify_request.return_value = True
        mock_get_slack_verifier.return_value = mock_verifier
        
        # Test AppContainer commands
        appcontainer_tests = [
            "create_appcontainer"
        ]
        
        for test_name in appcontainer_tests:
            test_case = next(tc for tc in self.fixtures['commands'] if tc['name'] == test_name)
            print(f"\nTesting: {test_case['name']}")
            
            # Reset mock
            mock_dispatcher.reset_mock()
            mock_dispatcher.trigger_appcontainer_creation.return_value = (True, "AppContainer creation triggered")
            
            # Send Slack command
            response = self.client.post("/slack/command", data=test_case['event'])
            
            # Verify response
            assert response.status_code == 200, f"Failed for {test_case['name']}"
            result = response.json()
            
            if test_case['expected']['success']:
                # Check if response indicates success
                response_text = result.get('text', '').lower()
                assert "started" in response_text or "triggered" in response_text or "creating" in response_text
                
                # Verify dispatcher was called
                assert mock_dispatcher.trigger_appcontainer_creation.called
                call_args = mock_dispatcher.trigger_appcontainer_creation.call_args[0][0]
                
                # Verify AppContainer parameters
                assert "appcontainer-name" in call_args
                assert call_args["appcontainer-name"] == test_case['expected']['parameters']['appcontainer-name']
    
    @patch('src.interface.dependencies.get_slack_verifier')
    @patch('src.interface.dependencies.get_vcluster_dispatcher')
    def test_error_handling_commands(self, mock_get_dispatcher, mock_get_slack_verifier):
        """Test error handling for invalid Slack commands."""
        # Mock dependencies
        mock_dispatcher = Mock()
        mock_get_dispatcher.return_value = mock_dispatcher
        mock_verifier = Mock()
        mock_verifier.verify_request.return_value = True
        mock_get_slack_verifier.return_value = mock_verifier
        
        # Test error cases
        error_tests = [
            "invalid_command"
        ]
        
        for test_name in error_tests:
            test_case = next(tc for tc in self.fixtures['commands'] if tc['name'] == test_name)
            print(f"\nTesting: {test_case['name']}")
            
            # Reset mock
            mock_dispatcher.reset_mock()
            
            # Send Slack command
            response = self.client.post("/slack/command", data=test_case['event'])
            
            # Verify response
            assert response.status_code == 200, f"Failed for {test_case['name']}"
            result = response.json()
            
            # Should return error message
            assert test_case['expected']['error_contains'] in result.get('text', ''), \
                   f"Expected error message not found for {test_case['name']}"
    
    @patch('src.interface.dependencies.get_slack_verifier')
    @patch('src.interface.dependencies.get_vcluster_dispatcher')
    def test_help_commands(self, mock_get_dispatcher, mock_get_slack_verifier):
        """Test help commands return usage information."""
        # Mock dependencies
        mock_dispatcher = Mock()
        mock_get_dispatcher.return_value = mock_dispatcher
        mock_verifier = Mock()
        mock_verifier.verify_request.return_value = True
        mock_get_slack_verifier.return_value = mock_verifier
        
        # Test help commands
        help_tests = [
            "vcluster_help",
            "microservice_help",
            "missing_required_params"  # Empty text shows help
        ]
        
        for test_name in help_tests:
            test_case = next(tc for tc in self.fixtures['commands'] if tc['name'] == test_name)
            print(f"\nTesting: {test_case['name']}")
            
            # Send Slack command
            response = self.client.post("/slack/command", data=test_case['event'])
            
            # Verify response
            assert response.status_code == 200, f"Failed for {test_case['name']}"
            result = response.json()
            
            # Should return help text - check both lowercase and case-sensitive
            response_text = result.get('text', '')
            expected_text = test_case['expected'].get('response_contains', '')
            assert expected_text.lower() in response_text.lower() or expected_text in response_text, \
                   f"Expected help text '{expected_text}' not found in '{response_text}' for {test_case['name']}"
    
    
    @patch('src.interface.dependencies.get_slack_verifier')
    @patch('src.interface.dependencies.get_vcluster_dispatcher')
    def test_dispatcher_failure(self, mock_get_dispatcher, mock_get_slack_verifier):
        """Test handling of dispatcher failures."""
        # Mock dependencies
        mock_dispatcher = Mock()
        mock_get_dispatcher.return_value = mock_dispatcher
        mock_verifier = Mock()
        mock_verifier.verify_request.return_value = True
        mock_get_slack_verifier.return_value = mock_verifier
        
        # Mock dispatcher failure
        mock_dispatcher.trigger_microservice_creation.return_value = (False, "Connection to Argo failed")
        
        # Use a microservice test case
        test_case = next(tc for tc in self.fixtures['commands'] if tc['name'] == "create_single_microservice")
        
        # Send Slack command
        response = self.client.post("/slack/command", data=test_case['event'])
        
        # Should still return 200 but with error message
        assert response.status_code == 200
        result = response.json()
        assert "Failed" in result.get('text', '') or "Error" in result.get('text', '')
        assert "Connection to Argo failed" in result.get('text', '')
    
    @patch('src.interface.dependencies.get_slack_verifier')
    @patch('src.interface.dependencies.get_vcluster_dispatcher')
    def test_concurrent_command_processing(self, mock_get_dispatcher, mock_get_slack_verifier):
        """Test that multiple different commands can be processed."""
        # Mock dependencies
        mock_dispatcher = Mock()
        mock_get_dispatcher.return_value = mock_dispatcher
        mock_verifier = Mock()
        mock_verifier.verify_request.return_value = True
        mock_get_slack_verifier.return_value = mock_verifier
        
        # Setup different mock returns for different dispatchers
        mock_dispatcher.trigger_vcluster_creation.return_value = (True, "VCluster triggered")
        mock_dispatcher.trigger_appcontainer_creation.return_value = (True, "AppContainer triggered")
        mock_dispatcher.trigger_microservice_creation.return_value = (True, "Microservice triggered")
        
        call_counts = {
            "vcluster": 0,
            "appcontainer": 0,
            "microservice": 0
        }
        
        # Process commands in sequence
        command_sequence = [
            "create_vcluster_infrastructure",
            "create_appcontainer",
            "create_single_microservice"
        ]
        
        for test_name in command_sequence:
            test_case = next(tc for tc in self.fixtures['commands'] if tc['name'] == test_name)
            response = self.client.post("/slack/command", data=test_case['event'])
            assert response.status_code == 200
            
            # Track which dispatcher was called
            if "vcluster" in test_name:
                call_counts["vcluster"] = mock_dispatcher.trigger_vcluster_creation.call_count
            elif "appcontainer" in test_name:
                call_counts["appcontainer"] = mock_dispatcher.trigger_appcontainer_creation.call_count
            elif "microservice" in test_name:
                call_counts["microservice"] = mock_dispatcher.trigger_microservice_creation.call_count
        
        # Verify all dispatchers were called
        assert call_counts["vcluster"] >= 1
        assert call_counts["appcontainer"] >= 1
        assert call_counts["microservice"] >= 1