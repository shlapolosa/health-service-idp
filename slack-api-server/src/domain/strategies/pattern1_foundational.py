"""Pattern 1: Foundational components handler."""

from typing import Dict, Any
import logging

from .base import PatternHandler, ComponentPattern, HandlerContext, HandlerResult

logger = logging.getLogger(__name__)


class Pattern1FoundationalHandler(PatternHandler):
    """Handler for Pattern 1: Foundational components (single service, needs repository)."""
    
    SUPPORTED_TYPES = {
        "webservice": {
            "workflow": "microservice-standard-contract",  # Existing comprehensive workflow
            "supports_languages": ["python", "nodejs", "java", "go"],
            "supports_frameworks": ["fastapi", "flask", "express", "nestjs", "spring", "gin", "fiber"]
        },
        "webservice-k8s": {
            "workflow": "microservice-standard-contract",  # Same workflow, different deployment
            "deployment_type": "kubernetes",
            "supports_languages": ["python", "nodejs", "java", "go"]
        },
        "vcluster": {
            "workflow": "vcluster-workflow",  # Existing vCluster creation workflow
            "infrastructure_only": True
        }
    }
    
    # Template mapping based on language/framework combinations
    TEMPLATE_MAP = {
        ("python", "fastapi"): "onion-architecture-template",
        ("python", "flask"): "python-flask-template",
        ("nodejs", "express"): "nodejs-express-template", 
        ("nodejs", "nestjs"): "nodejs-nestjs-template",
        ("java", "spring"): "spring-boot-template",
        ("go", "gin"): "go-gin-template",
        ("go", "fiber"): "go-fiber-template"
    }
    
    def get_pattern(self) -> ComponentPattern:
        """Return Pattern 1: Foundational."""
        return ComponentPattern.FOUNDATIONAL
    
    def can_handle(self, component_type: str) -> bool:
        """Check if this handler can process the component type."""
        return component_type in self.SUPPORTED_TYPES
    
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
            properties = component.get("properties", {})
            
            # Map OAM properties to workflow parameters (reuse Slack command parameters)
            params = {
                # Tier 1: Universal Parameters
                "resource-name": component_name,
                "resource-type": "microservice",
                "namespace": context.namespace or "default",
                "user": "oam-webhook",
                "description": f"OAM-driven service from {context.oam_application_name}",
                "github-org": context.github_owner or "shlapolosa",
                "docker-registry": "docker.io/socrates12345",
                "slack-channel": "#oam-deployments",
                "slack-user-id": "OAM",
                
                # Tier 2: Platform Parameters
                "security-enabled": "true",
                "observability-enabled": "true",
                "backup-enabled": "false",
                "environment-tier": "development",
                "auto-create-dependencies": "false",  # vCluster should already exist
                "resource-size": "medium",
                
                # Tier 3: Microservice-specific
                "microservice-language": properties.get("language", "python"),
                "microservice-framework": properties.get("framework", "fastapi"),
                "microservice-database": properties.get("database", "none"),
                "microservice-cache": properties.get("cache", "none"),
                "microservice-expose-api": str(properties.get("exposeApi", False)).lower(),
                "target-vcluster": context.vcluster or "",
                "parent-appcontainer": context.app_container or "",
                "repository-name": context.app_container or ""  # Use existing repo
            }
            
            # Always use microservice-standard-contract for ApplicationClaim
            workflow_name = "microservice-standard-contract"
            
            logger.info(f"Triggering ApplicationClaim workflow for {component_name}")
            workflow_run = argo_client.create_workflow_from_template(
                workflow_template_name=workflow_name,
                parameters=params,
                namespace="argo"
            )
            
            # Update processed components
            workflow_run_name = workflow_run.get("metadata", {}).get("name", "unknown") if isinstance(workflow_run, dict) else workflow_run.metadata.name
            context.processed_components[component_name] = {
                "type": component.get("type"),
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
                    "requires_source_code": True
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
        config = self.SUPPORTED_TYPES.get(component_type, {})
        return config.get("workflow", "microservice-standard-contract")
    
    def validate_prerequisites(self, component: Dict[str, Any], context: HandlerContext) -> HandlerResult:
        """Validate prerequisites for foundational components."""
        component_type = component.get("type")
        component_name = component.get("name")
        properties = component.get("properties", {})
        config = self.SUPPORTED_TYPES.get(component_type, {})
        
        # Validate component name
        if not component_name:
            return HandlerResult(
                success=False,
                error="Component name is required",
                workflow_name=None,
                workflow_run_name=None,
                metadata={"component_type": component_type},
                pattern=self.get_pattern()
            )
        
        # vCluster has minimal requirements
        if component_type == "vcluster":
            return HandlerResult(
                success=True,
                error=None,
                workflow_name=None,
                workflow_run_name=None,
                metadata={},
                pattern=self.get_pattern()
            )
        
        # Validate language for webservice types
        language = properties.get("language")
        if not language:
            return HandlerResult(
                success=False,
                error="Language property is required for webservice",
                workflow_name=None,
                workflow_run_name=None,
                metadata={
                    "component": component_name,
                    "supported_languages": config.get("supports_languages", [])
                },
                pattern=self.get_pattern()
            )
        
        # Validate language is supported
        supported_languages = config.get("supports_languages", [])
        if language not in supported_languages:
            return HandlerResult(
                success=False,
                error=f"Language '{language}' not supported. Must be one of: {', '.join(supported_languages)}",
                workflow_name=None,
                workflow_run_name=None,
                metadata={"supported_languages": supported_languages},
                pattern=self.get_pattern()
            )
        
        # Validate framework if specified
        framework = properties.get("framework")
        if framework:
            supported_frameworks = config.get("supports_frameworks", [])
            if framework not in supported_frameworks:
                logger.warning(f"Framework '{framework}' not in standard list, will use default template")
        
        return HandlerResult(
            success=True,
            error=None,
            workflow_name=None,
            workflow_run_name=None,
            metadata={},
            pattern=self.get_pattern()
        )
    
    def prepare_workflow_params(self, component: Dict[str, Any], context: HandlerContext) -> Dict[str, Any]:
        """Prepare parameters for foundational workflows."""
        component_type = component.get("type")
        component_name = component.get("name")
        properties = component.get("properties", {})
        
        # vCluster parameters
        if component_type == "vcluster":
            return {
                "vcluster_name": component_name,
                "namespace": context.namespace,
                "values": properties.get("values", "{}"),
                "expose": str(properties.get("expose", True)).lower(),
                "storage_size": properties.get("storage_size", "10Gi")
            }
        
        # Webservice parameters (both webservice and webservice-k8s)
        language = properties.get("language", "python")
        framework = properties.get("framework", self._get_default_framework(language))
        
        # Determine template repository
        template_key = (language, framework)
        template_repo = self.TEMPLATE_MAP.get(template_key, "onion-architecture-template")
        
        # Determine platform (Knative vs K8s deployment)
        if component_type == "webservice-k8s":
            platform = "kubernetes"
        else:
            platform = properties.get("platform", "knative")
        
        params = {
            # Core service parameters
            "service_name": component_name,
            "language": language,
            "framework": framework,
            "platform": platform,
            
            # Repository and template
            "template_repo": template_repo,
            "app_container": context.app_container or "new",
            "github_owner": context.github_owner,
            "repository": properties.get("repository", component_name),
            
            # Deployment context
            "namespace": context.namespace,
            "vcluster": context.vcluster,
            "target_environment": properties.get("targetEnvironment", context.vcluster),
            
            # OAM context
            "oam_application": context.oam_application_name,
            "oam_namespace": context.oam_application_namespace,
            
            # Service configuration
            "enable_tracing": str(properties.get("tracing", True)).lower(),
            "enable_metrics": str(properties.get("metrics", True)).lower(),
            "enable_health_check": str(properties.get("health_check", True)).lower(),
            "enable_graphql_federation": str(properties.get("enableGraphQLFederation", False)).lower(),
            
            # Scaling configuration
            "min_scale": str(properties.get("minScale", 0)),
            "max_scale": str(properties.get("maxScale", 10)),
            
            # Resource limits
            "cpu_request": properties.get("cpu", "100m"),
            "memory_request": properties.get("memory", "128Mi"),
            "cpu_limit": properties.get("cpuLimit", "500m"),
            "memory_limit": properties.get("memoryLimit", "512Mi"),
            
            # Additional metadata
            "source": properties.get("source", "api-driven"),
            "api_version": properties.get("apiVersion", "v1"),
            "open_api_path": properties.get("openApiPath", "/openapi.json")
        }
        
        # Add realtime integration if specified
        if "realtime" in properties:
            params["realtime_platform"] = properties["realtime"]
            params["enable_websocket"] = "true"
            params["enable_event_streaming"] = "true"
        
        # Add database/cache references if resolved
        if "database_url" in properties:
            params["database_url"] = properties["database_url"]
        if "cache_url" in properties:
            params["cache_url"] = properties["cache_url"]
        
        # Add language-specific parameters
        if language == "java":
            params["jdk_version"] = properties.get("jdk_version", "11")
            params["build_tool"] = properties.get("build_tool", "maven")
            if framework == "springboot":
                params["spring_boot_version"] = properties.get("spring_boot_version", "2.7.0")
        elif language == "python":
            params["python_version"] = properties.get("python_version", "3.9")
        elif language == "nodejs":
            params["node_version"] = properties.get("node_version", "16")
        elif language == "go":
            params["go_version"] = properties.get("go_version", "1.19")
        
        return params
    
    def _get_default_framework(self, language: str) -> str:
        """Get default framework for a language."""
        defaults = {
            "python": "fastapi",
            "nodejs": "express",
            "java": "spring",
            "go": "gin"
        }
        return defaults.get(language, "unknown")