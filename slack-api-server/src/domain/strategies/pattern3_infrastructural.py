"""Pattern 3: Infrastructural components handler."""

from typing import Dict, Any, List
import json
import base64
import logging

from .base import PatternHandler, ComponentPattern, HandlerContext, HandlerResult

logger = logging.getLogger(__name__)


class Pattern3InfrastructuralHandler(PatternHandler):
    """Handler for Pattern 3: Infrastructural components (provider systems and infrastructure)."""
    
    # External service providers
    PROVIDER_TYPES = ["neon-postgres", "auth0-idp"]
    
    # Internal infrastructure
    INFRASTRUCTURE_TYPES = ["postgresql", "mongodb", "redis", "kafka", "clickhouse"]
    
    # Platform services (use existing workflows)
    PLATFORM_TYPES = ["realtime-platform", "camunda-orchestrator"]
    
    # Size configurations for infrastructure
    SIZE_CONFIGS = {
        "small": {"cpu": "500m", "memory": "1Gi", "storage": "10Gi"},
        "medium": {"cpu": "1", "memory": "2Gi", "storage": "50Gi"},
        "large": {"cpu": "2", "memory": "4Gi", "storage": "100Gi"},
        "xlarge": {"cpu": "4", "memory": "8Gi", "storage": "500Gi"}
    }
    
    def get_pattern(self) -> ComponentPattern:
        """Return Pattern 3: Infrastructural."""
        return ComponentPattern.INFRASTRUCTURAL
    
    def can_handle(self, component_type: str) -> bool:
        """Check if this handler can process the component type."""
        all_types = self.PROVIDER_TYPES + self.INFRASTRUCTURE_TYPES + self.PLATFORM_TYPES
        return component_type in all_types
    
    def get_workflow_name(self, component: Dict[str, Any]) -> str:
        """Get the appropriate workflow based on component type."""
        component_type = component.get("type")
        
        if component_type in self.PROVIDER_TYPES:
            return "pattern3-provider-workflow"
        elif component_type in self.INFRASTRUCTURE_TYPES:
            return "pattern3-infrastructure-workflow"
        elif component_type == "realtime-platform":
            return "realtime-platform-workflow"  # Existing workflow
        elif component_type == "camunda-orchestrator":
            return "orchestration-workflow"  # Existing workflow
        else:
            raise ValueError(f"Unknown infrastructural component type: {component_type}")
    
    def validate_prerequisites(self, component: Dict[str, Any], context: HandlerContext) -> HandlerResult:
        """Validate prerequisites for infrastructural components."""
        component_type = component.get("type")
        properties = component.get("properties", {})
        
        # Validate provider systems
        if component_type in self.PROVIDER_TYPES:
            credentials = properties.get("credentials", {})
            if not credentials:
                return HandlerResult(
                    success=False,
                    error=f"Provider {component_type} requires credentials",
                    workflow_name=None,
                    workflow_run_name=None,
                    metadata={"component_type": component_type},
                    pattern=self.get_pattern()
                )
            
            # Check provider-specific required fields
            if component_type == "neon-postgres":
                required = ["connection_string", "database_url"]
            elif component_type == "auth0-idp":
                required = ["domain", "client_id", "client_secret"]
            else:
                required = []
            
            missing = [field for field in required if field not in credentials]
            if missing:
                return HandlerResult(
                    success=False,
                    error=f"Missing required credentials: {', '.join(missing)}",
                    workflow_name=None,
                    workflow_run_name=None,
                    metadata={"missing_fields": missing},
                    pattern=self.get_pattern()
                )
        
        # Validate infrastructure components
        elif component_type in self.INFRASTRUCTURE_TYPES:
            size = properties.get("size", "small")
            if size not in self.SIZE_CONFIGS:
                return HandlerResult(
                    success=False,
                    error=f"Invalid size '{size}'. Must be one of: {', '.join(self.SIZE_CONFIGS.keys())}",
                    workflow_name=None,
                    workflow_run_name=None,
                    metadata={"valid_sizes": list(self.SIZE_CONFIGS.keys())},
                    pattern=self.get_pattern()
                )
            
            # Check for duplicate infrastructure
            if component_type in context.existing_components:
                logger.warning(f"Infrastructure {component_type} already exists, will create new instance")
        
        # Platform services have their own validation in their workflows
        
        return HandlerResult(
            success=True,
            error=None,
            workflow_name=None,
            workflow_run_name=None,
            metadata={},
            pattern=self.get_pattern()
        )
    
    def prepare_workflow_params(self, component: Dict[str, Any], context: HandlerContext) -> Dict[str, Any]:
        """Prepare parameters for infrastructural workflows."""
        component_type = component.get("type")
        component_name = component.get("name")
        properties = component.get("properties", {})
        
        # Provider systems parameters
        if component_type in self.PROVIDER_TYPES:
            credentials = properties.get("credentials", {})
            
            # Encode credentials for secure transmission
            encoded_credentials = {}
            for key, value in credentials.items():
                if isinstance(value, str):
                    encoded_credentials[key] = base64.b64encode(value.encode()).decode()
                else:
                    encoded_credentials[key] = base64.b64encode(json.dumps(value).encode()).decode()
            
            return {
                "provider_type": component_type,
                "secret_name": f"{component_name}-secret",
                "credentials": json.dumps(encoded_credentials),
                "namespace": context.namespace,
                "vcluster": context.vcluster,
                "service_binding": str(properties.get("service_binding", True)).lower(),
                "external_secrets_enabled": str(properties.get("use_external_secrets", False)).lower()
            }
        
        # Infrastructure components parameters
        elif component_type in self.INFRASTRUCTURE_TYPES:
            size = properties.get("size", "small")
            size_config = self.SIZE_CONFIGS[size]
            
            # Determine default version based on type
            default_versions = {
                "postgresql": "14",
                "mongodb": "6.0",
                "redis": "7",
                "kafka": "3.3",
                "clickhouse": "23.3"
            }
            
            return {
                "infrastructure_type": component_type,
                "claim_name": f"{component_name}-{component_type}",
                "size": size,
                "version": properties.get("version", default_versions.get(component_type, "latest")),
                "replicas": str(properties.get("replicas", 1)),
                "namespace": context.namespace,
                "vcluster": context.vcluster,
                "high_availability": str(properties.get("high_availability", False)).lower(),
                "backup_enabled": str(properties.get("backup_enabled", False)).lower(),
                "monitoring_enabled": str(properties.get("monitoring", True)).lower()
            }
        
        # Platform services parameters
        elif component_type == "realtime-platform":
            return {
                "name": component_name,
                "namespace": context.namespace,
                "vcluster": context.vcluster,
                "enable_kafka": str(properties.get("enableKafka", True)).lower(),
                "enable_mqtt": str(properties.get("enableMQTT", False)).lower(),
                "enable_websocket": str(properties.get("enableWebSocket", True)).lower()
            }
        
        elif component_type == "camunda-orchestrator":
            return {
                "orchestrator_name": component_name,
                "namespace": context.namespace,
                "vcluster": context.vcluster,
                "realtime_platform": properties.get("realtimePlatform", ""),
                "enable_ui": str(properties.get("enableUI", True)).lower(),
                "saga_patterns": json.dumps(properties.get("sagaPatterns", ["compensation", "timeout", "retry"]))
            }
        
        else:
            raise ValueError(f"Unknown infrastructural component type: {component_type}")