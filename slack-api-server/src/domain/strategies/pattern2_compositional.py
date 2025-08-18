"""Pattern 2: Compositional components handler."""

from typing import Dict, Any
import json
import logging
import os

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
    
    def handle(self, component: Dict[str, Any], context: HandlerContext, argo_client) -> HandlerResult:
        """Handle component with source code check."""
        component_type = component.get("type")
        
        # Check if this component requires source code
        component_metadata = self.get_component_definition_metadata(component_type)
        
        if component_metadata["requires_source_code"]:
            # Route to ApplicationClaim creation path
            logger.info(f"Component {component.get('name')} requires source code, using ApplicationClaim path")
            return self.handle_via_application_claim(component, context, argo_client)
        else:
            # Use existing direct deployment path
            logger.info(f"Component {component.get('name')} uses external image, using direct deployment")
            return super().handle(component, context, argo_client)
    
    def handle_via_application_claim(self, component: Dict[str, Any], context: HandlerContext, argo_client) -> HandlerResult:
        """Handle component through ApplicationClaim for source code creation."""
        try:
            component_name = component.get("name")
            component_type = component.get("type")
            properties = component.get("properties", {})
            
            # Special handling for different compositional types
            if component_type == "rasa-chatbot":
                language = "rasa"
                framework = "chatbot"
            elif component_type == "identity-service":
                language = "java"
                framework = "springboot"
            elif component_type == "orchestration-platform":
                language = properties.get("language", "java")
                framework = "orchestration"
            else:
                language = properties.get("language", "python")
                framework = properties.get("framework", "fastapi")
            
            # Get registry configuration from environment or use defaults
            registry_type = os.getenv("REGISTRY_TYPE", "dockerhub").lower()
            if registry_type == "acr":
                docker_registry = "healthidpuaeacr.azurecr.io"
            else:
                # Default to Docker Hub
                docker_registry = "docker.io/socrates12345"
            
            # Map OAM properties to workflow parameters
            params = {
                # Tier 1: Universal Parameters
                "resource-name": component_name,
                "resource-type": "microservice",
                "namespace": context.namespace or "default",
                "user": "oam-webhook",
                "description": f"OAM-driven {component_type} from {context.oam_application_name}",
                "github-org": context.github_owner or "shlapolosa",
                "docker-registry": docker_registry,
                "slack-channel": "#oam-deployments",
                "slack-user-id": "OAM",
                
                # Tier 2: Platform Parameters
                "bootstrap-source": "OAM-driven",  # Pattern2 is OAM-driven
                "security-enabled": "true",
                "observability-enabled": "true",
                "backup-enabled": "false",
                "environment-tier": "development",
                "auto-create-dependencies": "false",
                "resource-size": "medium",
                
                # Tier 3: Microservice-specific
                "microservice-language": language,
                "microservice-framework": framework,
                "microservice-database": properties.get("database", "none"),
                "microservice-cache": properties.get("cache", "none"),
                "microservice-realtime": properties.get("realtime", ""),
                "microservice-expose-api": str(properties.get("exposeApi", False)).lower(),
                "target-vcluster": context.vcluster or "",
                "parent-appcontainer": context.app_container or "",
                "repository-name": context.app_container or ""
            }
            
            # Use microservice-standard-contract for ApplicationClaim
            workflow_name = "microservice-standard-contract"
            
            logger.info(f"Triggering ApplicationClaim workflow for {component_type}: {component_name}")
            workflow_run = argo_client.create_workflow_from_template(
                workflow_template_name=workflow_name,
                parameters=params,
                namespace="argo"
            )
            
            # Update processed components
            workflow_run_name = workflow_run.get("metadata", {}).get("name", "unknown") if isinstance(workflow_run, dict) else workflow_run.metadata.name
            context.processed_components[component_name] = {
                "type": component_type,
                "pattern": self.get_pattern().value,
                "workflow": workflow_name,
                "run": workflow_run_name,
                "via": "ApplicationClaim"
            }
            
            return HandlerResult(
                success=True,
                workflow_name=workflow_name,
                workflow_run_name=workflow_run_name,
                error=None,
                metadata={
                    "parameters": params,
                    "route": "ApplicationClaim",
                    "requires_source_code": True,
                    "compositional_type": component_type
                },
                pattern=self.get_pattern()
            )
            
        except Exception as e:
            logger.error(f"Failed to handle component {component.get('name')} via ApplicationClaim: {str(e)}")
            return HandlerResult(
                success=False,
                workflow_name=None,
                workflow_run_name=None,
                error=str(e),
                metadata={"component": component},
                pattern=self.get_pattern()
            )
    
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
        
        # Determine if this is OAM-driven
        is_oam_driven = bool(context.app_container)
        
        # Get registry configuration
        registry_type = os.getenv("REGISTRY_TYPE", "dockerhub").lower()
        if registry_type == "acr":
            docker_registry = "healthidpuaeacr.azurecr.io"
        else:
            docker_registry = "docker.io/socrates12345"
        
        # Base parameters for all compositional services - using workflow template expected names
        base_params = {
            # Core parameters matching workflow template
            "resource-name": component_name,  # Changed from service_name
            "resource-type": "microservice",
            "namespace": context.namespace,
            "user": "oam-webhook" if is_oam_driven else "api-user",
            "description": f"{'OAM-driven' if is_oam_driven else 'API-driven'} {component_type} service",
            
            # GitHub and repository parameters
            "github-org": context.github_owner or "shlapolosa",
            "docker-registry": docker_registry,
            "repository-name": context.app_container if is_oam_driven else component_name,
            
            # Bootstrap source
            "bootstrap-source": "oam-driven" if is_oam_driven else "api-driven",
            
            # Environment
            "environment-tier": "development",
            "target-vcluster": context.vcluster or "",
            
            # Backward compatibility parameters
            "component_type": component_type,
            "service_name": component_name,  # Keep for compatibility
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