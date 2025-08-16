"""
Infrastructure Layer - Argo Workflows Client Implementation
Handles Argo Workflows API communication for VCluster creation
"""

import json
import logging
import os
from typing import Dict, Tuple

import requests

from ..application.use_cases import VClusterDispatcherInterface

logger = logging.getLogger(__name__)


class ArgoWorkflowsClient(VClusterDispatcherInterface):
    """Argo Workflows API client for VCluster creation operations."""

    def __init__(self, server_url: str, namespace: str = "argo", timeout: int = 30, token_file: str = None):
        """Initialize Argo Workflows client with configuration."""
        self.server_url = server_url.rstrip("/")
        self.namespace = namespace
        self.timeout = timeout
        self.base_url = f"{self.server_url}/api/v1"
        self.token_file = token_file or os.getenv("ARGO_TOKEN_FILE")
        self._token = None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers with Bearer token."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if self.token_file and os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    token = f.read().strip()
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                        logger.debug("Successfully loaded Argo authentication token")
                    else:
                        logger.warning("Argo token file is empty")
            except Exception as e:
                logger.error(f"Failed to read Argo token file {self.token_file}: {e}")
        else:
            logger.warning(f"Argo token file not found: {self.token_file}")
        
        return headers

    def trigger_vcluster_creation(self, payload: Dict) -> Tuple[bool, str]:
        """Trigger VCluster creation via Argo Workflows using standardized parameter contract."""
        client_payload = payload.get("client_payload", {})
        vcluster_name = client_payload.get("vcluster_name", "unknown")
        
        # Create workflow submission using vcluster-standard-contract template
        workflow_spec = {
            "namespace": self.namespace,
            "serverDryRun": False,
            "workflow": {
                "metadata": {
                    "generateName": "vcluster-standard-",
                    "namespace": self.namespace,
                    "labels": {
                        "created-by": "slack-api",
                        "vcluster-name": vcluster_name,
                        "user": client_payload.get("user", "unknown"),
                        "template-version": "v1.0"
                    }
                },
                "spec": {
                    "workflowTemplateRef": {
                        "name": "vcluster-standard-contract"
                    },
                    "arguments": {
                        "parameters": [
                            # === TIER 1: UNIVERSAL PARAMETERS (Required) ===
                            {
                                "name": "resource-name",
                                "value": vcluster_name
                            },
                            {
                                "name": "resource-type",
                                "value": "vcluster"
                            },
                            {
                                "name": "namespace",
                                "value": client_payload.get("namespace", "default")
                            },
                            {
                                "name": "user",
                                "value": client_payload.get("user", "unknown")
                            },
                            {
                                "name": "description",
                                "value": f"VCluster {vcluster_name} created via Slack API"
                            },
                            {
                                "name": "github-org",
                                "value": "shlapolosa"
                            },
                            {
                                "name": "docker-registry",
                                "value": "docker.io/socrates12345"
                            },
                            {
                                "name": "slack-channel",
                                "value": client_payload.get("slack_channel", "#all-internal-developer-platform")
                            },
                            {
                                "name": "slack-user-id",
                                "value": client_payload.get("slack_user_id", "UNKNOWN")
                            },
                            
                            # === TIER 2: PLATFORM PARAMETERS (Common) ===
                            {
                                "name": "security-enabled",
                                "value": "true"
                            },
                            {
                                "name": "observability-enabled",
                                "value": "true"
                            },
                            {
                                "name": "backup-enabled",
                                "value": "false"
                            },
                            {
                                "name": "environment-tier",
                                "value": "development"
                            },
                            {
                                "name": "auto-create-dependencies",
                                "value": "true"
                            },
                            {
                                "name": "resource-size",
                                "value": self._extract_size_from_resources(client_payload)
                            },
                            
                            # === TIER 3: VCLUSTER-SPECIFIC PARAMETERS ===
                            {
                                "name": "vcluster-size",
                                "value": self._extract_size_from_resources(client_payload)
                            },
                            {
                                "name": "vcluster-capabilities",
                                "value": json.dumps(self._build_capabilities_with_defaults(client_payload.get("capabilities", {})))
                            }
                        ]
                    }
                }
            }
        }

        url = f"{self.base_url}/workflows/{self.namespace}"
        headers = self._get_auth_headers()

        try:
            logger.info(
                f"Triggering Argo Workflow for VCluster: {vcluster_name}"
            )
            logger.debug(f"Workflow submission: {json.dumps(workflow_spec, indent=2)}")

            response = requests.post(
                url, 
                headers=headers, 
                json=workflow_spec, 
                timeout=self.timeout,
                verify=False  # Skip SSL verification for internal cluster communication
            )

            if response.status_code in [200, 201]:
                workflow_data = response.json()
                workflow_name = workflow_data.get("metadata", {}).get("name", "unknown")
                success_msg = f"VCluster creation workflow started: {workflow_name}"
                logger.info(f"✅ {success_msg}")
                return True, success_msg
            else:
                error_msg = (
                    f"Argo Workflows API error: {response.status_code} - {response.text}"
                )
                logger.error(f"❌ {error_msg}")
                return False, error_msg

        except requests.exceptions.Timeout:
            error_msg = f"Argo Workflows API request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            return False, error_msg

        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Argo Workflows API"
            logger.error(error_msg)
            return False, error_msg

        except requests.RequestException as e:
            error_msg = f"Argo Workflows API request failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error calling Argo Workflows API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def trigger_appcontainer_creation(self, payload: Dict) -> Tuple[bool, str]:
        """Trigger AppContainer creation via Argo Workflows."""
        appcontainer_name = payload.get("appcontainer-name", "unknown")
        
        # Create workflow submission for AppContainer
        workflow_spec = {
            "namespace": self.namespace,
            "serverDryRun": False,
            "workflow": {
                "metadata": {
                    "generateName": "appcontainer-creation-",
                    "namespace": self.namespace,
                    "labels": {
                        "created-by": "slack-api",
                        "appcontainer-name": appcontainer_name,
                        "user": payload.get("user", "unknown")
                    }
                },
                "spec": {
                    "workflowTemplateRef": {
                        "name": "appcontainer-creation"
                    },
                    "arguments": {
                        "parameters": [
                            {"name": "appcontainer-name", "value": payload.get("appcontainer-name", "")},
                            {"name": "namespace", "value": payload.get("namespace", "default")},
                            {"name": "description", "value": payload.get("description", "CLAUDE.md-compliant application container")},
                            {"name": "github-org", "value": payload.get("github-org", "shlapolosa")},
                            {"name": "docker-registry", "value": payload.get("docker-registry", "docker.io/socrates12345")},
                            {"name": "observability", "value": payload.get("observability", "true")},
                            {"name": "security", "value": payload.get("security", "true")},
                            {"name": "user", "value": payload.get("user", "unknown")},
                            {"name": "slack-channel", "value": payload.get("slack-channel", "unknown")},
                            {"name": "slack-user-id", "value": payload.get("slack-user-id", "unknown")},
                        ]
                    }
                }
            }
        }

        logger.info(f"🚀 Triggering AppContainer creation workflow for: {appcontainer_name}")
        logger.debug(f"Workflow spec: {json.dumps(workflow_spec, indent=2)}")

        # Submit workflow to Argo
        url = f"{self.base_url}/workflows/{self.namespace}"
        headers = self._get_auth_headers()

        try:
            response = requests.post(
                url, 
                headers=headers, 
                json=workflow_spec, 
                timeout=self.timeout,
                verify=False  # Skip SSL verification for internal cluster communication
            )

            if response.status_code in [200, 201]:
                workflow_data = response.json()
                workflow_name = workflow_data.get("metadata", {}).get("name", "unknown")
                success_msg = f"AppContainer creation workflow started: {workflow_name}"
                logger.info(f"✅ {success_msg}")
                return True, success_msg
            else:
                error_msg = (
                    f"Argo Workflows API error: {response.status_code} - {response.text}"
                )
                logger.error(f"❌ {error_msg}")
                return False, error_msg

        except requests.exceptions.Timeout:
            error_msg = f"Argo Workflows API request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            return False, error_msg

        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Argo Workflows API"
            logger.error(error_msg)
            return False, error_msg

        except requests.RequestException as e:
            error_msg = f"Argo Workflows API request failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error calling Argo Workflows API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def trigger_microservice_creation(self, payload: Dict) -> Tuple[bool, str]:
        """Trigger Microservice creation via Argo Workflows."""
        microservice_name = payload.get("microservice-name", "unknown")
        
        # Create workflow submission for Microservice
        workflow_spec = {
            "namespace": self.namespace,
            "serverDryRun": False,
            "workflow": {
                "metadata": {
                    "generateName": "microservice-creation-",
                    "namespace": self.namespace,
                    "labels": {
                        "created-by": "slack-api",
                        "microservice-name": microservice_name,
                        "user": payload.get("user", "unknown"),
                        "language": payload.get("language", "python"),
                        "database": payload.get("database", "none"),
                        "cache": payload.get("cache", "none")
                    }
                },
                "spec": {
                    "workflowTemplateRef": {
                        "name": "microservice-standard-contract"
                    },
                    "arguments": {
                        "parameters": [
                            # TIER 1: Universal Parameters
                            {"name": "resource-name", "value": payload.get("microservice-name", "")},
                            {"name": "resource-type", "value": "microservice"},
                            {"name": "namespace", "value": payload.get("namespace", "default")},
                            {"name": "user", "value": payload.get("user", "unknown")},
                            {"name": "description", "value": payload.get("description", "CLAUDE.md-compliant microservice")},
                            {"name": "github-org", "value": payload.get("github-org", "shlapolosa")},
                            {"name": "docker-registry", "value": payload.get("docker-registry", "docker.io/socrates12345")},
                            {"name": "slack-channel", "value": payload.get("slack-channel", "unknown")},
                            {"name": "slack-user-id", "value": payload.get("slack-user-id", "unknown")},
                            
                            # TIER 2: Platform Parameters
                            {"name": "bootstrap-source", "value": "api-driven"},
                            {"name": "security-enabled", "value": payload.get("security", "true")},
                            {"name": "observability-enabled", "value": payload.get("observability", "true")},
                            {"name": "backup-enabled", "value": "false"},
                            {"name": "environment-tier", "value": "development"},
                            {"name": "auto-create-dependencies", "value": payload.get("auto-create-vcluster", "true")},
                            {"name": "resource-size", "value": "medium"},
                            
                            # TIER 3: Microservice-Specific Parameters
                            {"name": "microservice-language", "value": payload.get("language", "python")},
                            {"name": "microservice-framework", "value": "auto"},
                            {"name": "microservice-database", "value": payload.get("database", "none")},
                            {"name": "microservice-cache", "value": payload.get("cache", "none")},
                            {"name": "microservice-realtime", "value": payload.get("realtime", "")},
                            {"name": "microservice-expose-api", "value": "false"},
                            {"name": "target-vcluster", "value": payload.get("target-vcluster", "")},
                            {"name": "parent-appcontainer", "value": payload.get("parent-appcontainer", "")},
                            {"name": "repository-name", "value": payload.get("repository-name", "")},
                        ]
                    }
                }
            }
        }

        logger.info(f"🚀 Triggering Microservice creation workflow for: {microservice_name}")
        logger.debug(f"Workflow spec: {json.dumps(workflow_spec, indent=2)}")

        # Submit workflow to Argo
        url = f"{self.base_url}/workflows/{self.namespace}"
        headers = self._get_auth_headers()

        try:
            response = requests.post(
                url, 
                headers=headers, 
                json=workflow_spec, 
                timeout=self.timeout,
                verify=False  # Skip SSL verification for internal cluster communication
            )

            if response.status_code in [200, 201]:
                workflow_data = response.json()
                workflow_name = workflow_data.get("metadata", {}).get("name", "unknown")
                success_msg = f"Microservice creation workflow started: {workflow_name}"
                logger.info(f"✅ {success_msg}")
                return True, success_msg
            else:
                error_msg = (
                    f"Argo Workflows API error: {response.status_code} - {response.text}"
                )
                logger.error(f"❌ {error_msg}")
                return False, error_msg

        except requests.exceptions.Timeout:
            error_msg = f"Argo Workflows API request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            return False, error_msg

        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Argo Workflows API"
            logger.error(error_msg)
            return False, error_msg

        except requests.RequestException as e:
            error_msg = f"Argo Workflows API request failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error calling Argo Workflows API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _extract_size_from_resources(self, client_payload: Dict) -> str:
        """Extract size preset from resource specifications."""
        resources = client_payload.get("resources", {})
        cpu_limit = resources.get("cpu_limit", "2000m")
        
        # Map CPU limits back to size presets
        if cpu_limit == "1000m":
            return "small"
        elif cpu_limit == "4000m":
            return "large"
        elif cpu_limit == "8000m":
            return "xlarge"
        else:
            return "medium"

    def _build_capabilities_with_defaults(self, capabilities: Dict) -> Dict[str, str]:
        """Build capabilities with defaults, converting boolean values to strings."""
        # Default capabilities (strings as expected by the workflow template)
        default_capabilities = {
            "observability": "true",
            "security": "true", 
            "gitops": "true",
            "logging": "true",
            "networking": "true",
            "autoscaling": "true",
            "backup": "false"
        }
        
        # Override with provided capabilities, ensuring string values
        for key, value in capabilities.items():
            if isinstance(value, bool):
                default_capabilities[key] = "true" if value else "false"
            elif isinstance(value, str):
                default_capabilities[key] = value.lower()
            
        return default_capabilities

    def validate_configuration(self) -> Tuple[bool, str]:
        """Validate Argo Workflows client configuration."""
        if not self.server_url:
            return False, "Argo Workflows server URL not configured"

        # Test API connectivity
        url = f"{self.base_url}/info"
        headers = self._get_auth_headers()

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout, verify=False)

            if response.status_code == 200:
                return True, "Argo Workflows configuration valid"
            else:
                return False, f"Argo Workflows API returned status {response.status_code}"

        except Exception as e:
            return False, f"Failed to validate Argo Workflows configuration: {str(e)}"

    def get_workflow_status(self, workflow_name: str) -> Tuple[bool, Dict]:
        """Get status of a specific workflow."""
        url = f"{self.base_url}/workflows/{self.namespace}/{workflow_name}"
        headers = self._get_auth_headers()

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
            
            if response.status_code == 200:
                workflow_data = response.json()
                status = workflow_data.get("status", {})
                return True, status
            else:
                return False, {"error": f"Failed to get workflow status: {response.status_code}"}

        except Exception as e:
            return False, {"error": f"Error getting workflow status: {str(e)}"}
    
    def trigger_microservice_from_oam(self, component: Dict, app_container: str, vcluster: str) -> Tuple[bool, str]:
        """Trigger service creation from OAM component.
        
        This method handles different component types (webservice, identity-service, etc)
        and routes them to appropriate workflow triggers.
        """
        
        component_type = component.get("type", "")
        component_name = component.get("name", "unknown")
        
        # Handle identity-service components
        if component_type == "identity-service":
            return self.trigger_identity_service_from_oam(component, app_container)
        
        # Default to webservice handling
        # Extract properties directly from OAM component
        props = component.get("properties", {})
        
        # Build payload matching what trigger_microservice_creation expects
        payload = {
            "microservice-name": component_name,
            "language": props.get("language", "python"),
            "framework": props.get("framework", "fastapi"),
            "database": props.get("database", "none"),
            "cache": props.get("cache", "none"),
            "target-vcluster": vcluster if vcluster else "",
            "parent-appcontainer": app_container,  # Key: Always set for monorepo
            "repository-name": app_container,       # Use monorepo pattern
            "namespace": "default",
            "user": "oam-webhook",
            "slack-channel": "#platform-automation",
            "slack-user-id": "OAM-System",
            "github-org": "shlapolosa",
            "docker-registry": "docker.io/socrates12345",
            "auto-create-vcluster": "false",  # vCluster should already exist
            "description": f"Service {component_name} auto-created from OAM Application",
            "security": "true",
            "observability": "true",
            "realtime": props.get("realtime", "")
        }
        
        logger.info(f"🎯 OAM-triggered microservice creation for: {component_name} in {app_container}")
        
        # Use existing trigger_microservice_creation with our constructed payload
        return self.trigger_microservice_creation(payload)
    
    def trigger_identity_service_from_oam(self, component: Dict, app_container: str) -> Tuple[bool, str]:
        """Trigger identity service creation from OAM component.
        
        Identity services use a different workflow template and parameters.
        """
        props = component.get("properties", {})
        component_name = component.get("name", "unknown")
        domain = props.get("domain", "healthcare")  # Default to healthcare
        
        logger.info(f"🔐 Triggering identity service creation: {component_name} with domain {domain}")
        
        # Identity services use the identity-service-generator WorkflowTemplate
        workflow_payload = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {
                "generateName": f"{component_name}-identity-gen-",
                "namespace": "default",
                "labels": {
                    "app.kubernetes.io/name": component_name,
                    "app.kubernetes.io/component": "identity-service",
                    "app-container": app_container
                }
            },
            "spec": {
                "serviceAccountName": "argo-workflows-client",
                "workflowTemplateRef": {
                    "name": "identity-service-generator"
                },
                "arguments": {
                    "parameters": [
                        {"name": "domain", "value": domain},
                        {"name": "repo-name", "value": f"{component_name}-identity-service"},
                        {"name": "app-name", "value": app_container},
                        {"name": "github-owner", "value": "shlapolosa"}
                    ]
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.argo_server_url}/api/v1/workflows/default",
                json=workflow_payload,
                headers={"Authorization": f"Bearer {self.argo_token}"},
                verify=False
            )
            
            if response.status_code in [200, 201]:
                workflow_data = response.json()
                workflow_name = workflow_data.get("metadata", {}).get("name", "unknown")
                logger.info(f"✅ Identity service workflow created: {workflow_name}")
                return True, workflow_name
            else:
                error_msg = f"Failed to create identity service workflow: {response.status_code}"
                logger.error(f"{error_msg} - {response.text}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error triggering identity service: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def create_workflow_from_template(self, workflow_template_name: str, parameters: Dict, namespace: str = "argo") -> Dict:
        """Create a workflow from a template with parameters.
        
        This is a generic method to trigger any workflow template with given parameters.
        Used by the pattern-based handlers.
        
        Args:
            workflow_template_name: Name of the workflow template
            parameters: Dictionary of parameters to pass to the workflow
            namespace: Namespace to create the workflow in
            
        Returns:
            Workflow object with metadata including name
        """
        import uuid
        import logging
        import os
        
        logger = logging.getLogger(__name__)
        
        # Check if we're in test mode
        use_mock = os.getenv("ARGO_USE_MOCK", "false").lower() == "true"
        
        # Generate a unique workflow name
        workflow_name = f"{workflow_template_name}-{str(uuid.uuid4())[:8]}"
        
        # Log the workflow trigger
        logger.info(f"Creating workflow {workflow_name} from template {workflow_template_name}")
        logger.debug(f"Parameters: {parameters}")
        logger.debug(f"Using mock client: {use_mock}")
        
        if use_mock:
            # Return mock response for testing
            return {
                "metadata": {
                    "name": workflow_name,
                    "namespace": namespace,
                    "uid": str(uuid.uuid4())
                },
                "spec": {
                    "workflowTemplateRef": {
                        "name": workflow_template_name
                    },
                    "arguments": {
                        "parameters": [{"name": k, "value": str(v)} for k, v in parameters.items()]
                    }
                },
                "status": {
                    "phase": "Running"
                }
            }
        
        # Real Argo API call
        workflow_spec = {
            "namespace": namespace,
            "serverDryRun": False,
            "workflow": {
                "metadata": {
                    "generateName": f"{workflow_template_name}-",
                    "namespace": namespace,
                    "labels": {
                        "created-by": "oam-webhook",
                        "template": workflow_template_name,
                        "pattern-handler": "true"
                    }
                },
                "spec": {
                    "workflowTemplateRef": {
                        "name": workflow_template_name
                    },
                    "arguments": {
                        "parameters": [
                            {"name": k, "value": str(v)} 
                            for k, v in parameters.items()
                        ]
                    }
                }
            }
        }
        
        url = f"{self.base_url}/workflows/{namespace}"
        headers = self._get_auth_headers()
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=workflow_spec,
                timeout=self.timeout,
                verify=False  # Skip SSL verification for internal cluster communication
            )
            
            if response.status_code in [200, 201]:
                workflow_data = response.json()
                logger.info(f"✅ Successfully created workflow: {workflow_data.get('metadata', {}).get('name')}")
                return workflow_data
            else:
                error_msg = f"Argo API error: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                # Return mock response on error to prevent workflow failures
                logger.warning("Falling back to mock response due to API error")
                return {
                    "metadata": {
                        "name": workflow_name,
                        "namespace": namespace,
                        "uid": str(uuid.uuid4()),
                        "error": error_msg
                    },
                    "spec": {
                        "workflowTemplateRef": {
                            "name": workflow_template_name
                        },
                        "arguments": {
                            "parameters": [{"name": k, "value": str(v)} for k, v in parameters.items()]
                        }
                    },
                    "status": {
                        "phase": "Failed",
                        "message": error_msg
                    }
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Argo API request failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Return mock response on error to prevent workflow failures
            logger.warning("Falling back to mock response due to connection error")
            return {
                "metadata": {
                    "name": workflow_name,
                    "namespace": namespace,
                    "uid": str(uuid.uuid4()),
                    "error": error_msg
                },
                "spec": {
                    "workflowTemplateRef": {
                        "name": workflow_template_name
                    },
                    "arguments": {
                        "parameters": [{"name": k, "value": str(v)} for k, v in parameters.items()]
                    }
                },
                "status": {
                    "phase": "Failed",
                    "message": error_msg
                }
            }