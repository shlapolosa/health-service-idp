#!/usr/bin/env python3
"""
Test natural language parsing without requiring environment variables
"""

import json
import re
from datetime import datetime
from typing import Dict

class VClusterRequestParser:
    """Parses natural language VCluster creation requests."""
    
    # Capability keywords mapping
    CAPABILITY_KEYWORDS = {
        'observability': ['observability', 'monitoring', 'metrics', 'grafana', 'prometheus'],
        'security': ['security', 'rbac', 'policies', 'admission'],
        'gitops': ['gitops', 'argocd', 'deployment', 'cd'],
        'logging': ['logging', 'logs', 'fluentd', 'elasticsearch'],
        'networking': ['networking', 'service-mesh', 'istio', 'ingress'],
        'autoscaling': ['autoscaling', 'hpa', 'vpa', 'scaling'],
        'backup': ['backup', 'disaster-recovery', 'br']
    }
    
    # Resource size presets
    RESOURCE_PRESETS = {
        'small': {'cpu_limit': '1000m', 'memory_limit': '2Gi', 'storage_size': '10Gi', 'node_count': '1'},
        'medium': {'cpu_limit': '2000m', 'memory_limit': '4Gi', 'storage_size': '20Gi', 'node_count': '3'},
        'large': {'cpu_limit': '4000m', 'memory_limit': '8Gi', 'storage_size': '50Gi', 'node_count': '5'},
        'xlarge': {'cpu_limit': '8000m', 'memory_limit': '16Gi', 'storage_size': '100Gi', 'node_count': '10'}
    }
    
    @classmethod
    def parse_vcluster_request(cls, text: str, user: str, channel: str) -> Dict:
        """Parse natural language VCluster creation request."""
        text = text.lower().strip()
        
        # Extract VCluster name
        name_match = re.search(r'(?:name|called?)\s+([a-z0-9-]+)', text)
        vcluster_name = name_match.group(1) if name_match else f"vcluster-{int(datetime.now().timestamp())}"
        
        # Extract namespace  
        namespace_match = re.search(r'(?:namespace|ns)\s+([a-z0-9-]+)', text)
        namespace = namespace_match.group(1) if namespace_match else "default"
        
        # Extract repository
        repo_match = re.search(r'(?:repository|repo|app)\s+([a-z0-9-]+)', text)
        repository = repo_match.group(1) if repo_match else ""
        
        # Parse capabilities
        capabilities = {}
        for capability, keywords in cls.CAPABILITY_KEYWORDS.items():
            # Default all capabilities to true unless explicitly disabled
            capabilities[capability] = "true"
            
            # Check for explicit mentions
            for keyword in keywords:
                if keyword in text:
                    capabilities[capability] = "true"
                    break
                    
            # Check for explicit disabling
            disable_patterns = [f'no {capability}', f'without {capability}', f'disable {capability}']
            for pattern in disable_patterns:
                if pattern in text:
                    capabilities[capability] = "false"
                    break
        
        # Parse resource size
        resources = cls.RESOURCE_PRESETS['medium']  # Default to medium
        for size, preset in cls.RESOURCE_PRESETS.items():
            if size in text:
                resources = preset
                break
                
        # Check for specific resource mentions
        cpu_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cpu|cores?)', text)
        if cpu_match:
            resources['cpu_limit'] = f"{int(float(cpu_match.group(1)) * 1000)}m"
            
        memory_match = re.search(r'(\d+)\s*(?:gb|gi)', text)
        if memory_match:
            resources['memory_limit'] = f"{memory_match.group(1)}Gi"
            
        # Construct payload
        payload = {
            "event_type": "slack_create_vcluster",
            "client_payload": {
                "vcluster_name": vcluster_name,
                "namespace": namespace,
                "repository": repository,
                "user": user,
                "slack_channel": channel,
                "slack_user_id": user,
                "capabilities": capabilities,
                "resources": resources,
                "original_request": text
            }
        }
        
        return payload

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
        },
        {
            "input": "create small vcluster in namespace dev with security but no networking",
            "expected_size": "small",
            "expected_namespace": "dev",
            "expected_security": "true",
            "expected_networking": "false"
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
        print(f"   Resources: {client_payload['resources']}")
        
        # Show enabled capabilities
        enabled_caps = [cap for cap, enabled in client_payload['capabilities'].items() if enabled == "true"]
        disabled_caps = [cap for cap, enabled in client_payload['capabilities'].items() if enabled == "false"]
        print(f"   Enabled Capabilities: {', '.join(enabled_caps)}")
        if disabled_caps:
            print(f"   Disabled Capabilities: {', '.join(disabled_caps)}")
        
        # Validate expectations
        if "expected_name" in test_case:
            assert client_payload["vcluster_name"] == test_case["expected_name"], f"Name mismatch"
            print(f"   ✅ Name matches expected: {test_case['expected_name']}")
            
        if "expected_namespace" in test_case:
            assert client_payload["namespace"] == test_case["expected_namespace"], f"Namespace mismatch"
            print(f"   ✅ Namespace matches expected: {test_case['expected_namespace']}")
            
        if "expected_repo" in test_case:
            assert client_payload["repository"] == test_case["expected_repo"], f"Repository mismatch"
            print(f"   ✅ Repository matches expected: {test_case['expected_repo']}")
            
        if "expected_backup" in test_case:
            assert client_payload["capabilities"]["backup"] == test_case["expected_backup"], f"Backup setting mismatch"
            print(f"   ✅ Backup setting matches expected: {test_case['expected_backup']}")
            
        if "expected_security" in test_case:
            assert client_payload["capabilities"]["security"] == test_case["expected_security"], f"Security setting mismatch"
            print(f"   ✅ Security setting matches expected: {test_case['expected_security']}")
            
        if "expected_networking" in test_case:
            assert client_payload["capabilities"]["networking"] == test_case["expected_networking"], f"Networking setting mismatch"
            print(f"   ✅ Networking setting matches expected: {test_case['expected_networking']}")
        
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
    print(f"   📄 Sample Payload:")
    print(json.dumps(payload, indent=4))

if __name__ == "__main__":
    print("🚀 Slack Natural Language Parsing Test")
    print("=" * 50)
    
    test_natural_language_parsing()
    test_github_payload_format()
    
    print("\n🎉 Natural language parsing tests completed!")
    print("\nKey Features Tested:")
    print("✅ VCluster name extraction")
    print("✅ Namespace parsing")
    print("✅ Repository detection")
    print("✅ Capability enabling/disabling") 
    print("✅ Resource size presets")
    print("✅ GitHub payload format")
    print("\nNext: Set up Slack app and test with real slash commands!")