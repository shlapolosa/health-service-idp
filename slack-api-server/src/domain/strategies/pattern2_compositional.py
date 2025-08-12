"""Pattern 2: Compositional components handler."""

from typing import Dict, Any
import json
import logging

from .base import PatternHandler, ComponentPattern, HandlerContext, HandlerResult

logger = logging.getLogger(__name__)


class Pattern2CompositionalHandler(PatternHandler):
    """Handler for Pattern 2: Compositional components (multi-service, orchestration needed)."""
    
    COMPOSITIONAL_TYPES = {
        "rasa-chatbot": {
            "workflow": "pattern2-compositional-workflow",  # Uses the new workflow
            "template": "chat-template",
            "build_strategy": "multi-image",
            "image_count": 3,
            "requires_monorepo": True
        },
        "graphql-gateway": {
            "workflow": "pattern2-compositional-workflow",
            "template": "graphql-federation-gateway-template",
            "build_strategy": "single-image",
            "image_count": 1,
            "requires_monorepo": True
        },
        "graphql-platform": {
            "workflow": "graphql-platform-workflow",  # Uses existing claim-based workflow
            "uses_claim": True,
            "build_strategy": "platform",
            "image_count": 1,
            "requires_monorepo": False
        },
        "identity-service": {
            "workflow": "identity-service-generator",  # Uses existing Argo workflow
            "template": "identity-service-template",
            "build_strategy": "java-maven",
            "image_count": 1,
            "requires_monorepo": False  # Can be standalone
        },
        "orchestration-platform": {
            "workflow": "orchestration-workflow",  # Uses orchestration workflow
            "template": "orchestration-platform-template",
            "build_strategy": "platform",
            "image_count": 1,
            "requires_monorepo": False  # Can be standalone
        }
    }
    
    def get_pattern(self) -> ComponentPattern:
        """Return Pattern 2: Compositional."""
        return ComponentPattern.COMPOSITIONAL
    
    def can_handle(self, component_type: str) -> bool:
        """Check if this handler can process the component type."""
        return component_type in self.COMPOSITIONAL_TYPES
    
    def get_workflow_name(self, component: Dict[str, Any]) -> str:
        """Get the appropriate workflow for the component type."""
        component_type = component.get("type")
        config = self.COMPOSITIONAL_TYPES.get(component_type, {})
        return config.get("workflow", "pattern2-compositional-workflow")
    
    def validate_prerequisites(self, component: Dict[str, Any], context: HandlerContext) -> HandlerResult:
        """Validate prerequisites for compositional components."""
        component_type = component.get("type")
        properties = component.get("properties", {})
        config = self.COMPOSITIONAL_TYPES.get(component_type, {})
        
        # Check if monorepo is required but missing
        if config.get("requires_monorepo") and not context.app_container:
            return HandlerResult(
                success=False,
                error=f"Component {component_type} requires an existing AppContainer (monorepo)",
                workflow_name=None,
                workflow_run_name=None,
                metadata={
                    "suggestion": "Add 'app-container' label to OAM Application",
                    "component_type": component_type
                },
                pattern=self.get_pattern()
            )
        
        # Type-specific validations
        if component_type == "identity-service":
            # Identity service requires domain specification
            domain = properties.get("domain")
            valid_domains = ["healthcare", "financial", "education"]
            
            if not domain:
                return HandlerResult(
                    success=False,
                    error="Identity service requires 'domain' property",
                    workflow_name=None,
                    workflow_run_name=None,
                    metadata={"valid_domains": valid_domains},
                    pattern=self.get_pattern()
                )
            
            if domain not in valid_domains:
                return HandlerResult(
                    success=False,
                    error=f"Invalid domain '{domain}'. Must be one of: {', '.join(valid_domains)}",
                    workflow_name=None,
                    workflow_run_name=None,
                    metadata={"valid_domains": valid_domains},
                    pattern=self.get_pattern()
                )
        
        elif component_type == "rasa-chatbot":
            # Set default NLU pipeline if not specified
            if "nlu_pipeline" not in properties:
                component["properties"]["nlu_pipeline"] = "pretrained_embeddings_spacy"
                logger.info("Set default NLU pipeline for RASA chatbot")
        
        elif component_type == "graphql-gateway":
            # Validate federation services if provided
            federation_services = properties.get("federation_services", [])
            if federation_services and not isinstance(federation_services, list):
                return HandlerResult(
                    success=False,
                    error="federation_services must be a list",
                    workflow_name=None,
                    workflow_run_name=None,
                    metadata={"provided": type(federation_services).__name__},
                    pattern=self.get_pattern()
                )
        
        return HandlerResult(
            success=True,
            error=None,
            workflow_name=None,
            workflow_run_name=None,
            metadata={},
            pattern=self.get_pattern()
        )
    
    def prepare_workflow_params(self, component: Dict[str, Any], context: HandlerContext) -> Dict[str, Any]:
        """Prepare parameters for compositional workflows."""
        component_type = component.get("type")
        component_name = component.get("name")
        properties = component.get("properties", {})
        config = self.COMPOSITIONAL_TYPES[component_type]
        
        # Base parameters for all compositional services
        base_params = {
            "component_type": component_type,
            "service_name": component_name,
            "namespace": context.namespace,
            "vcluster": context.vcluster,
            "github_owner": context.github_owner,
            "app_container": context.app_container or "new"
        }
        
        # Add template and build strategy info
        if "template" in config:
            base_params["template_repo"] = config["template"]
        if "build_strategy" in config:
            base_params["build_strategy"] = config["build_strategy"]
        if "image_count" in config:
            base_params["image_count"] = str(config["image_count"])
        
        # Type-specific parameters
        if component_type == "rasa-chatbot":
            base_params.update({
                "nlu_pipeline": properties.get("nlu_pipeline", "pretrained_embeddings_spacy"),
                "policies": properties.get("policies", "TEDPolicy,MemoizationPolicy,RulePolicy"),
                "language_model": properties.get("language_model", "en_core_web_md"),
                "training_data": properties.get("training_data", "default"),
                "build_base_image": "true",
                "build_rasa_image": "true",
                "build_actions_image": "true"
            })
        
        elif component_type == "graphql-gateway":
            base_params.update({
                "federation_services": json.dumps(properties.get("federation_services", [])),
                "introspection_enabled": str(properties.get("introspection", True)).lower(),
                "playground_enabled": str(properties.get("playground", False)).lower(),
                "auto_discovery": str(properties.get("auto_discovery", True)).lower(),
                "api_version": properties.get("api_version", "v1")
            })
        
        elif component_type == "graphql-platform":
            # GraphQL platform uses claims
            base_params.update({
                "enable_playground": str(properties.get("enablePlayground", True)).lower(),
                "enable_introspection": str(properties.get("enableIntrospection", False)).lower(),
                "federation_enabled": str(properties.get("federationEnabled", True)).lower(),
                "hasura_enabled": str(properties.get("hasuraEnabled", False)).lower()
            })
        
        elif component_type == "identity-service":
            # Identity service specific parameters
            base_params.update({
                "domain": properties.get("domain"),
                "database_type": properties.get("database", "postgresql"),
                "cache_type": properties.get("cache", "redis"),
                "auth_provider": properties.get("auth_provider", "auth0"),
                "compliance_level": properties.get("compliance_level", "standard"),
                "enable_mfa": str(properties.get("mfa", True)).lower(),
                "enable_audit": str(properties.get("audit", True)).lower(),
                "repository": properties.get("repository", f"{component_name}-identity-service")
            })
        
        elif component_type == "orchestration-platform":
            # Orchestration platform specific parameters
            base_params.update({
                "orchestration_type": component_type,  # Add this for compatibility
                "engine": properties.get("engine", "temporal"),
                "workers": str(properties.get("workers", 5)),
                "namespace": properties.get("namespace", context.namespace),
                "enable_ui": str(properties.get("enable_ui", True)).lower(),
                "persistence": properties.get("persistence", "postgresql"),
                "repository": properties.get("repository", f"{component_name}-orchestration")
            })
        
        return base_params