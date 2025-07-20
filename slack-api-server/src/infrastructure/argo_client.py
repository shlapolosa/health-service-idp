"""
Infrastructure Layer - Argo Workflows Client Implementation
Handles Argo Workflows API communication for VCluster creation
"""

import json
import logging
from typing import Dict, Tuple

import requests

from ..application.use_cases import VClusterDispatcherInterface

logger = logging.getLogger(__name__)


class ArgoWorkflowsClient(VClusterDispatcherInterface):
    """Argo Workflows API client for VCluster creation operations."""

    def __init__(self, server_url: str, namespace: str = "argo", timeout: int = 30):
        """Initialize Argo Workflows client with configuration."""
        self.server_url = server_url.rstrip("/")
        self.namespace = namespace
        self.timeout = timeout
        self.base_url = f"{self.server_url}/api/v1"

    def trigger_vcluster_creation(self, payload: Dict) -> Tuple[bool, str]:
        """Trigger VCluster creation via Argo Workflows."""
        client_payload = payload.get("client_payload", {})
        vcluster_name = client_payload.get("vcluster_name", "unknown")
        
        # Create workflow submission
        workflow_spec = {
            "namespace": self.namespace,
            "serverDryRun": False,
            "workflow": {
                "metadata": {
                    "generateName": "vcluster-creation-",
                    "namespace": self.namespace,
                    "labels": {
                        "created-by": "slack-api",
                        "vcluster-name": vcluster_name,
                        "user": client_payload.get("user", "unknown")
                    }
                },
                "spec": {
                    "workflowTemplateRef": {
                        "name": "vcluster-creation"
                    },
                    "arguments": {
                        "parameters": [
                            {
                                "name": "vcluster-name",
                                "value": vcluster_name
                            },
                            {
                                "name": "namespace",
                                "value": client_payload.get("namespace", "default")
                            },
                            {
                                "name": "size",
                                "value": self._extract_size_from_resources(client_payload)
                            },
                            {
                                "name": "capabilities",
                                "value": json.dumps(client_payload.get("capabilities", {}))
                            },
                            {
                                "name": "user",
                                "value": client_payload.get("user", "unknown")
                            },
                            {
                                "name": "slack-channel",
                                "value": client_payload.get("slack_channel", "unknown")
                            },
                            {
                                "name": "slack-user-id",
                                "value": client_payload.get("slack_user_id", "unknown")
                            }
                        ]
                    }
                }
            }
        }

        url = f"{self.base_url}/workflows/{self.namespace}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            logger.info(
                f"Triggering Argo Workflow for VCluster: {vcluster_name}"
            )
            logger.debug(f"Workflow submission: {json.dumps(workflow_spec, indent=2)}")

            response = requests.post(
                url, 
                headers=headers, 
                json=workflow_spec, 
                timeout=self.timeout
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
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = requests.post(
                url, 
                headers=headers, 
                json=workflow_spec, 
                timeout=self.timeout
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
                            {"name": "microservice-expose-api", "value": "false"},
                            {"name": "target-vcluster", "value": payload.get("target-vcluster", "")},
                            {"name": "parent-appcontainer", "value": ""},
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
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = requests.post(
                url, 
                headers=headers, 
                json=workflow_spec, 
                timeout=self.timeout
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

    def validate_configuration(self) -> Tuple[bool, str]:
        """Validate Argo Workflows client configuration."""
        if not self.server_url:
            return False, "Argo Workflows server URL not configured"

        # Test API connectivity
        url = f"{self.base_url}/info"
        headers = {
            "Accept": "application/json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                return True, "Argo Workflows configuration valid"
            else:
                return False, f"Argo Workflows API returned status {response.status_code}"

        except Exception as e:
            return False, f"Failed to validate Argo Workflows configuration: {str(e)}"

    def get_workflow_status(self, workflow_name: str) -> Tuple[bool, Dict]:
        """Get status of a specific workflow."""
        url = f"{self.base_url}/workflows/{self.namespace}/{workflow_name}"
        headers = {
            "Accept": "application/json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                workflow_data = response.json()
                status = workflow_data.get("status", {})
                return True, status
            else:
                return False, {"error": f"Failed to get workflow status: {response.status_code}"}

        except Exception as e:
            return False, {"error": f"Error getting workflow status: {str(e)}"}