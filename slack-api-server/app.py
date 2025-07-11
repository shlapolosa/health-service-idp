#!/usr/bin/env python3
"""
Slack API Server for VCluster Management
Handles Slack slash commands and triggers GitHub Actions for VCluster provisioning.
"""

import os
import re
import json
import hmac
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration from environment variables
SLACK_SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'shlapolosa/health-service-idp')

# Validate required environment variables
required_vars = ['SLACK_SIGNING_SECRET', 'SLACK_BOT_TOKEN', 'GITHUB_TOKEN']
missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {missing_vars}")
    exit(1)

class SlackRequestVerifier:
    """Verifies Slack request signatures for security."""
    
    @staticmethod
    def verify_request(request_data: bytes, timestamp: str, signature: str) -> bool:
        """Verify Slack request signature."""
        if not SLACK_SIGNING_SECRET:
            logger.warning("SLACK_SIGNING_SECRET not set - skipping verification")
            return True
            
        # Check timestamp is recent (within 5 minutes)
        import time
        if abs(time.time() - int(timestamp)) > 60 * 5:
            logger.warning("Request timestamp too old")
            return False
            
        # Compute expected signature
        sig_basestring = f"v0:{timestamp}:{request_data.decode('utf-8')}"
        expected_signature = 'v0=' + hmac.new(
            SLACK_SIGNING_SECRET.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)

# Try to import spaCy for enhanced NLP
try:
    import spacy
    from spacy.matcher import Matcher
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

class VClusterRequestParser:
    """Enhanced NLP parser with spaCy support for sophisticated command understanding."""
    
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
    
    def __init__(self):
        """Initialize the parser with spaCy if available."""
        self.nlp = None
        self.matcher = None
        self.spacy_available = SPACY_AVAILABLE
        
        if self.spacy_available:
            try:
                # Load spaCy model
                self.nlp = spacy.load("en_core_web_sm")
                self.matcher = Matcher(self.nlp.vocab)
                self._setup_patterns()
                logger.info("✅ spaCy loaded successfully - enhanced NLP enabled")
            except OSError:
                logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
                self.spacy_available = False
        
        if not self.spacy_available:
            logger.info("Using regex-based parsing fallback")
    
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
            [{"LOWER": {"IN": ["small", "medium", "large", "xlarge"]}}]
        ]
        self.matcher.add("SIZE", size_patterns)
        
        # Capability patterns
        capability_patterns = [
            [{"LOWER": "with"}, {"LOWER": {"IN": ["observability", "security", "monitoring", "gitops"]}}],
            [{"LOWER": "without"}, {"LOWER": {"IN": ["backup", "networking", "logging"]}}]
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
            "enable_capabilities": [],
            "disable_capabilities": []
        }
        
        # Process matches
        for match_id, start, end in matches:
            label = self.nlp.vocab.strings[match_id]
            span = doc[start:end]
            
            if label == "VCLUSTER_NAME" and len(span) > 1:
                extracted["vcluster_name"] = span[-1].text.lower()
                    
            elif label == "NAMESPACE" and len(span) > 1:
                extracted["namespace"] = span[-1].text.lower()
                    
            elif label == "SIZE":
                if span[0].text.lower() in ["small", "medium", "large", "xlarge"]:
                    extracted["size"] = span[0].text.lower()
                    
            elif label == "CAPABILITIES":
                if span[0].text.lower() in ["with", "enable"] and len(span) > 1:
                    extracted["enable_capabilities"].append(span[-1].text.lower())
                elif span[0].text.lower() in ["without", "disable"] and len(span) > 1:
                    extracted["disable_capabilities"].append(span[-1].text.lower())
        
        # Use named entities for additional context
        for ent in doc.ents:
            if ent.label_ == "ORG" and not extracted["repository"]:
                extracted["repository"] = ent.text.lower()
        
        return extracted
    
    def _fallback_parse(self, text: str) -> Dict:
        """Fallback regex parsing when spaCy is not available."""
        text = text.lower().strip()
        
        extracted = {
            "vcluster_name": None,
            "namespace": "default", 
            "repository": "",
            "size": "medium",
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
        for size in ["xlarge", "large", "medium", "small"]:
            if size in text:
                extracted["size"] = size
                break
        
        # Extract capabilities
        for capability, keywords in self.CAPABILITY_KEYWORDS.items():
            for keyword in keywords:
                if f"with {keyword}" in text or f"enable {keyword}" in text:
                    extracted["enable_capabilities"].append(capability)
                elif f"without {keyword}" in text or f"disable {keyword}" in text or f"no {keyword}" in text:
                    extracted["disable_capabilities"].append(capability)
        
        return extracted
    
    def parse_vcluster_request(self, text: str, user: str, channel: str) -> Dict:
        """Parse natural language VCluster creation request using enhanced NLP."""
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
        
        # Get resources based on size
        resources = self.RESOURCE_PRESETS[extracted["size"]]
        
        # Check for specific resource mentions in original text
        text_lower = text.lower()
        cpu_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cpu|cores?)', text_lower)
        if cpu_match:
            resources['cpu_limit'] = f"{int(float(cpu_match.group(1)) * 1000)}m"
            
        memory_match = re.search(r'(\d+)\s*(?:gb|gi)', text_lower)
        if memory_match:
            resources['memory_limit'] = f"{memory_match.group(1)}Gi"
        
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

class GitHubDispatcher:
    """Handles GitHub repository dispatch events."""
    
    @staticmethod
    def trigger_vcluster_creation(payload: Dict) -> Tuple[bool, str]:
        """Trigger VCluster creation via GitHub repository dispatch."""
        url = f"https://api.github.com/repos/{GITHUB_REPO}/dispatches"
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 204:
                logger.info(f"Successfully triggered VCluster creation: {payload['client_payload']['vcluster_name']}")
                return True, "VCluster creation triggered successfully"
            else:
                error_msg = f"GitHub API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except requests.RequestException as e:
            error_msg = f"Failed to call GitHub API: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

class SlackResponder:
    """Handles Slack API responses and notifications."""
    
    @staticmethod
    def send_slack_message(channel: str, text: str, blocks: Optional[List] = None) -> bool:
        """Send message to Slack channel."""
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'channel': channel,
            'text': text
        }
        
        if blocks:
            payload['blocks'] = blocks
            
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
    
    @staticmethod
    def create_vcluster_response(vcluster_name: str, namespace: str, capabilities: Dict, resources: Dict) -> Dict:
        """Create formatted Slack response for VCluster creation."""
        # Format capabilities
        enabled_caps = [cap for cap, enabled in capabilities.items() if enabled == "true"]
        caps_text = ", ".join(enabled_caps) if enabled_caps else "none"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚀 VCluster Creation Started"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Name:*\n`{vcluster_name}`"
                    },
                    {
                        "type": "mrkdwn", 
                        "text": f"*Namespace:*\n`{namespace}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Capabilities:*\n{caps_text}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Resources:*\nCPU: {resources['cpu_limit']}, Memory: {resources['memory_limit']}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "⏳ *Status:* Provisioning started... You'll receive updates as the process progresses."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔍 View GitHub Action"
                        },
                        "url": f"https://github.com/{GITHUB_REPO}/actions"
                    }
                ]
            }
        ]
        
        return {
            "response_type": "in_channel",
            "text": f"🚀 VCluster `{vcluster_name}` creation started",
            "blocks": blocks
        }

# Flask Routes

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/slack/commands', methods=['POST'])
def handle_slack_command():
    """Handle Slack slash commands."""
    # Verify request signature
    signature = request.headers.get('X-Slack-Signature', '')
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    
    if not SlackRequestVerifier.verify_request(request.data, timestamp, signature):
        logger.warning("Invalid Slack request signature")
        return "Unauthorized", 401
    
    # Parse form data
    try:
        form_data = parse_qs(request.data.decode('utf-8'))
        command = form_data.get('command', [''])[0]
        text = form_data.get('text', [''])[0]
        user_id = form_data.get('user_id', [''])[0]
        channel_id = form_data.get('channel_id', [''])[0]
        user_name = form_data.get('user_name', [''])[0]
        
        logger.info(f"Received command: {command} from user: {user_name} in channel: {channel_id}")
        
    except Exception as e:
        logger.error(f"Failed to parse Slack request: {e}")
        return jsonify({"text": "❌ Failed to parse command"}), 400
    
    # Handle different commands
    if command == '/vcluster':
        return handle_vcluster_command(text, user_id, channel_id, user_name)
    else:
        return jsonify({"text": f"❌ Unknown command: {command}"}), 400

def handle_vcluster_command(text: str, user_id: str, channel_id: str, user_name: str) -> Dict:
    """Handle /vcluster slash command."""
    text = text.strip()
    
    if not text or text.startswith('help'):
        return jsonify({
            "response_type": "ephemeral",
            "text": "🤖 VCluster Management Commands",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available Commands:*\n• `/vcluster create [name] [options]` - Create new VCluster\n• `/vcluster list` - List existing VClusters\n• `/vcluster delete [name]` - Delete VCluster\n• `/vcluster status [name]` - Check VCluster status\n\n*Example:*\n`/vcluster create my-cluster with observability and security in namespace dev`"
                    }
                }
            ]
        })
    
    # Handle create command
    if text.startswith('create'):
        try:
            # Parse the creation request using enhanced NLP
            parser = VClusterRequestParser()
            payload = parser.parse_vcluster_request(text, user_name, channel_id)
            
            # Trigger GitHub Action
            success, message = GitHubDispatcher.trigger_vcluster_creation(payload)
            
            if success:
                # Return success response with details
                vcluster_name = payload['client_payload']['vcluster_name']
                namespace = payload['client_payload']['namespace']
                capabilities = payload['client_payload']['capabilities']
                resources = payload['client_payload']['resources']
                
                return jsonify(SlackResponder.create_vcluster_response(
                    vcluster_name, namespace, capabilities, resources
                ))
            else:
                return jsonify({
                    "response_type": "ephemeral", 
                    "text": f"❌ Failed to create VCluster: {message}"
                })
                
        except Exception as e:
            logger.error(f"Error handling vcluster create: {e}")
            return jsonify({
                "response_type": "ephemeral",
                "text": f"❌ Error processing request: {str(e)}"
            }), 500
    
    # Handle other commands (list, delete, status)
    elif text.startswith('list'):
        return jsonify({
            "response_type": "ephemeral",
            "text": "📋 VCluster list functionality coming soon..."
        })
    
    elif text.startswith('delete'):
        return jsonify({
            "response_type": "ephemeral",
            "text": "🗑️ VCluster delete functionality coming soon..."
        })
    
    elif text.startswith('status'):
        return jsonify({
            "response_type": "ephemeral",
            "text": "📊 VCluster status functionality coming soon..."
        })
    
    else:
        return jsonify({
            "response_type": "ephemeral",
            "text": f"❌ Unknown vcluster command: {text}\nUse `/vcluster help` for available commands."
        })

@app.route('/slack/events', methods=['POST'])
def handle_slack_events():
    """Handle Slack event subscriptions (for future use)."""
    # Verify request signature
    signature = request.headers.get('X-Slack-Signature', '')
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    
    if not SlackRequestVerifier.verify_request(request.data, timestamp, signature):
        return "Unauthorized", 401
    
    data = request.json
    
    # Handle URL verification challenge
    if data.get('type') == 'url_verification':
        return jsonify({"challenge": data.get('challenge')})
    
    # Handle other events
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Slack API server on port {port}")
    logger.info(f"GitHub repo: {GITHUB_REPO}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)