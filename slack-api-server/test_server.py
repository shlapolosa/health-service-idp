#!/usr/bin/env python3
"""
Test script for Slack API Server
Tests natural language parsing and GitHub integration
"""

import json
import requests
from app import VClusterRequestParser, GitHubDispatcher

def test_natural_language_parsing():
    """Test the natural language parsing functionality."""
    print("🧪 Testing Natural Language Parsing...")
    
    test_cases = [
        {
            "input": "create vcluster called my-app with observability and security in namespace production",
            "expected_name": "my-app",
            "expected_namespace": "production",
            "expected_capabilities": ["observability", "security"]
        },
        {
            "input": "create large vcluster with monitoring and without backup",
            "expected_size": "large",
            "expected_backup": "false"
        },
        {
            "input": "create vcluster repo artifacts with gitops and autoscaling",
            "expected_repo": "artifacts",
            "expected_capabilities": ["gitops", "autoscaling"]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['input']}")
        
        payload = VClusterRequestParser.parse_vcluster_request(
            test_case["input"], "test.user", "C1234567890"
        )
        
        client_payload = payload["client_payload"]
        print(f"   VCluster Name: {client_payload['vcluster_name']}")
        print(f"   Namespace: {client_payload['namespace']}")
        print(f"   Repository: {client_payload['repository']}")
        print(f"   Capabilities: {client_payload['capabilities']}")
        print(f"   Resources: {client_payload['resources']}")
        
        # Validate expectations
        if "expected_name" in test_case:
            assert client_payload["vcluster_name"] == test_case["expected_name"], f"Name mismatch"
        if "expected_namespace" in test_case:
            assert client_payload["namespace"] == test_case["expected_namespace"], f"Namespace mismatch"
        if "expected_repo" in test_case:
            assert client_payload["repository"] == test_case["expected_repo"], f"Repository mismatch"
        if "expected_backup" in test_case:
            assert client_payload["capabilities"]["backup"] == test_case["expected_backup"], f"Backup setting mismatch"
        
        print("   ✅ Test passed")
    
    print("\n✅ All natural language parsing tests passed!")

def test_github_payload_format():
    """Test GitHub payload format."""
    print("\n🧪 Testing GitHub Payload Format...")
    
    payload = VClusterRequestParser.parse_vcluster_request(
        "create vcluster test-validation with all capabilities", 
        "test.user", 
        "C1234567890"
    )
    
    # Validate payload structure
    assert "event_type" in payload
    assert payload["event_type"] == "slack_create_vcluster"
    assert "client_payload" in payload
    
    client_payload = payload["client_payload"]
    required_fields = [
        "vcluster_name", "namespace", "repository", "user", 
        "slack_channel", "capabilities", "resources"
    ]
    
    for field in required_fields:
        assert field in client_payload, f"Missing required field: {field}"
    
    print("   ✅ Payload structure valid")
    print(f"   📄 Payload: {json.dumps(payload, indent=2)}")

def test_server_endpoints():
    """Test server endpoints (requires running server)."""
    print("\n🧪 Testing Server Endpoints...")
    
    base_url = "http://localhost:5000"
    
    try:
        # Test health endpoint
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Health endpoint working")
        else:
            print(f"   ❌ Health endpoint failed: {response.status_code}")
    except requests.RequestException as e:
        print(f"   ⚠️ Server not running or not accessible: {e}")
        print("   To start server: python app.py")

if __name__ == "__main__":
    print("🚀 Slack API Server Test Suite")
    print("=" * 50)
    
    test_natural_language_parsing()
    test_github_payload_format() 
    test_server_endpoints()
    
    print("\n🎉 Test suite completed!")
    print("\nNext steps:")
    print("1. Set up Slack app and bot")
    print("2. Configure environment variables") 
    print("3. Start the server: python app.py")
    print("4. Test with Slack slash commands")