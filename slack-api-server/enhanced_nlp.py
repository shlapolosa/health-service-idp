#!/usr/bin/env python3
"""
Enhanced NLP option using spaCy for more sophisticated parsing
Optional upgrade from the basic regex approach
"""

import re
from datetime import datetime
from typing import Dict, List, Optional

# Try to import spaCy, fall back to basic parsing if not available
try:
    import spacy
    from spacy.matcher import Matcher
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

class EnhancedVClusterParser:
    """
    Enhanced NLP parser with spaCy support for more sophisticated command understanding.
    Falls back to regex patterns if spaCy is not available.
    """
    
    def __init__(self):
        self.nlp = None
        self.matcher = None
        self.spacy_available = SPACY_AVAILABLE
        
        if self.spacy_available:
            try:
                # Load spaCy model (requires: python -m spacy download en_core_web_sm)
                self.nlp = spacy.load("en_core_web_sm")
                self.matcher = Matcher(self.nlp.vocab)
                self._setup_patterns()
            except OSError:
                print("spaCy model not found. Run: python -m spacy download en_core_web_sm")
                self.spacy_available = False
    
    def _setup_patterns(self):
        """Set up spaCy patterns for entity extraction."""
        if not self.matcher:
            return
            
        # VCluster name patterns
        name_patterns = [
            [{"LOWER": {"IN": ["name", "called", "named"]}}, {"IS_ALPHA": True}],
            [{"LOWER": "vcluster"}, {"IS_ALPHA": True}]
        ]
        self.matcher.add("VCLUSTER_NAME", name_patterns)
        
        # Namespace patterns
        namespace_patterns = [
            [{"LOWER": {"IN": ["namespace", "ns"]}}, {"IS_ALPHA": True}],
            [{"LOWER": "in"}, {"LOWER": {"IN": ["namespace", "ns"]}}, {"IS_ALPHA": True}]
        ]
        self.matcher.add("NAMESPACE", namespace_patterns)
        
        # Size patterns
        size_patterns = [
            [{"LOWER": {"IN": ["small", "medium", "large", "xlarge"]}}],
            [{"IS_DIGIT": True}, {"LOWER": {"IN": ["cpu", "cores", "gb", "gi"]}}]
        ]
        self.matcher.add("SIZE", size_patterns)
        
        # Capability patterns
        capability_patterns = [
            [{"LOWER": "with"}, {"LOWER": {"IN": ["observability", "security", "monitoring", "gitops"]}}],
            [{"LOWER": "without"}, {"LOWER": {"IN": ["backup", "networking", "logging"]}}],
            [{"LOWER": "enable"}, {"LOWER": {"IN": ["observability", "security", "monitoring"]}}],
            [{"LOWER": "disable"}, {"LOWER": {"IN": ["backup", "networking", "logging"]}}]
        ]
        self.matcher.add("CAPABILITIES", capability_patterns)
    
    def parse_with_spacy(self, text: str) -> Dict:
        """Parse using spaCy NLP."""
        if not self.nlp or not self.matcher:
            return self._fallback_parse(text)
            
        doc = self.nlp(text)
        matches = self.matcher(doc)
        
        extracted = {
            "vcluster_name": None,
            "namespace": "default",
            "repository": "",
            "size": "medium",
            "capabilities": {},
            "enable_capabilities": [],
            "disable_capabilities": []
        }
        
        # Process matches
        for match_id, start, end in matches:
            label = self.nlp.vocab.strings[match_id]
            span = doc[start:end]
            
            if label == "VCLUSTER_NAME":
                if len(span) > 1:
                    extracted["vcluster_name"] = span[-1].text.lower()
                    
            elif label == "NAMESPACE":
                if len(span) > 1:
                    extracted["namespace"] = span[-1].text.lower()
                    
            elif label == "SIZE":
                if span[0].text.lower() in ["small", "medium", "large", "xlarge"]:
                    extracted["size"] = span[0].text.lower()
                    
            elif label == "CAPABILITIES":
                if span[0].text.lower() in ["with", "enable"]:
                    if len(span) > 1:
                        extracted["enable_capabilities"].append(span[-1].text.lower())
                elif span[0].text.lower() in ["without", "disable"]:
                    if len(span) > 1:
                        extracted["disable_capabilities"].append(span[-1].text.lower())
        
        # Use named entities for additional context
        for ent in doc.ents:
            if ent.label_ == "ORG" and not extracted["repository"]:
                extracted["repository"] = ent.text.lower()
        
        return extracted
    
    def _fallback_parse(self, text: str) -> Dict:
        """Fallback to regex parsing when spaCy is not available."""
        text = text.lower().strip()
        
        extracted = {
            "vcluster_name": None,
            "namespace": "default", 
            "repository": "",
            "size": "medium",
            "capabilities": {},
            "enable_capabilities": [],
            "disable_capabilities": []
        }
        
        # Extract name
        name_match = re.search(r'(?:name|called?)\s+([a-z0-9-]+)', text)
        if name_match:
            extracted["vcluster_name"] = name_match.group(1)
        
        # Extract namespace
        namespace_match = re.search(r'(?:namespace|ns)\s+([a-z0-9-]+)', text)
        if namespace_match:
            extracted["namespace"] = namespace_match.group(1)
        
        # Extract repository
        repo_match = re.search(r'(?:repository|repo|app)\s+([a-z0-9-]+)', text)
        if repo_match:
            extracted["repository"] = repo_match.group(1)
        
        # Extract size
        for size in ["xlarge", "large", "medium", "small"]:  # Check longer sizes first
            if size in text:
                extracted["size"] = size
                break
        
        # Extract capabilities
        capability_keywords = {
            'observability': ['observability', 'monitoring', 'metrics'],
            'security': ['security', 'rbac', 'policies'],
            'gitops': ['gitops', 'argocd', 'deployment'],
            'logging': ['logging', 'logs'],
            'networking': ['networking', 'service-mesh', 'istio'],
            'autoscaling': ['autoscaling', 'hpa', 'scaling'],
            'backup': ['backup', 'disaster-recovery']
        }
        
        for capability, keywords in capability_keywords.items():
            for keyword in keywords:
                if f"with {keyword}" in text or f"enable {keyword}" in text:
                    extracted["enable_capabilities"].append(capability)
                elif f"without {keyword}" in text or f"disable {keyword}" in text or f"no {keyword}" in text:
                    extracted["disable_capabilities"].append(capability)
        
        return extracted
    
    def parse_vcluster_request(self, text: str, user: str, channel: str) -> Dict:
        """Main parsing method that chooses between spaCy and regex."""
        # Use spaCy if available, otherwise fall back to regex
        if self.spacy_available and self.nlp:
            extracted = self.parse_with_spacy(text)
        else:
            extracted = self._fallback_parse(text)
        
        # Generate name if not provided
        if not extracted["vcluster_name"]:
            extracted["vcluster_name"] = f"vcluster-{int(datetime.now().timestamp())}"
        
        # Set up capabilities with defaults
        all_capabilities = ['observability', 'security', 'gitops', 'logging', 'networking', 'autoscaling', 'backup']
        capabilities = {}
        
        for cap in all_capabilities:
            if cap in extracted["enable_capabilities"]:
                capabilities[cap] = "true"
            elif cap in extracted["disable_capabilities"]:
                capabilities[cap] = "false"
            else:
                # Default to true for most capabilities, false for backup
                capabilities[cap] = "false" if cap == "backup" else "true"
        
        # Set up resources based on size
        resource_presets = {
            'small': {'cpu_limit': '1000m', 'memory_limit': '2Gi', 'storage_size': '10Gi', 'node_count': '1'},
            'medium': {'cpu_limit': '2000m', 'memory_limit': '4Gi', 'storage_size': '20Gi', 'node_count': '3'},
            'large': {'cpu_limit': '4000m', 'memory_limit': '8Gi', 'storage_size': '50Gi', 'node_count': '5'},
            'xlarge': {'cpu_limit': '8000m', 'memory_limit': '16Gi', 'storage_size': '100Gi', 'node_count': '10'}
        }
        
        resources = resource_presets[extracted["size"]]
        
        # Construct GitHub payload
        payload = {
            "event_type": "slack_create_vcluster",
            "client_payload": {
                "vcluster_name": extracted["vcluster_name"],
                "namespace": extracted["namespace"],
                "repository": extracted["repository"],
                "user": user,
                "slack_channel": channel,
                "slack_user_id": user,
                "capabilities": capabilities,
                "resources": resources,
                "original_request": text,
                "parsing_method": "spacy" if (self.spacy_available and self.nlp) else "regex"
            }
        }
        
        return payload

# Test the enhanced parser
def test_enhanced_parsing():
    """Test enhanced NLP parsing."""
    print("🧪 Testing Enhanced NLP Parsing")
    print("=" * 50)
    
    if SPACY_AVAILABLE:
        print("✅ spaCy available - using advanced NLP")
    else:
        print("⚠️ spaCy not available - using regex fallback")
    
    parser = EnhancedVClusterParser()
    
    test_cases = [
        "Create a large VCluster named prod-cluster with observability but without backup",
        "I need a small cluster for development with security enabled",
        "Make me a VCluster called test-env in namespace staging with monitoring and gitops",
        "Create vcluster artifacts repository with all capabilities except networking",
        "Build a medium cluster with security policies but disable backup features"
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_input}")
        
        result = parser.parse_vcluster_request(test_input, "test.user", "C1234567890")
        payload = result["client_payload"]
        
        print(f"   Name: {payload['vcluster_name']}")
        print(f"   Namespace: {payload['namespace']}")
        print(f"   Repository: {payload['repository']}")
        print(f"   Resources: {payload['resources']['cpu_limit']} CPU, {payload['resources']['memory_limit']} Memory")
        
        enabled_caps = [cap for cap, enabled in payload['capabilities'].items() if enabled == "true"]
        disabled_caps = [cap for cap, enabled in payload['capabilities'].items() if enabled == "false"]
        
        print(f"   Enabled: {', '.join(enabled_caps)}")
        if disabled_caps:
            print(f"   Disabled: {', '.join(disabled_caps)}")
        print(f"   Parsing: {payload['parsing_method']}")

if __name__ == "__main__":
    test_enhanced_parsing()
    
    print(f"\n🚀 Enhanced NLP Setup Instructions:")
    if not SPACY_AVAILABLE:
        print("To enable advanced NLP:")
        print("1. pip install spacy")
        print("2. python -m spacy download en_core_web_sm")
        print("3. Restart the application")
    else:
        print("✅ spaCy is ready for advanced natural language processing!")
        print("Features available:")
        print("• Named entity recognition")
        print("• Better intent understanding")
        print("• More flexible command patterns")
        print("• Typo tolerance (future)")