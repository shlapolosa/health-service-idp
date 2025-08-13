"""Base pattern handler interface following Domain-Driven Design principles."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ComponentPattern(Enum):
    """Component pattern classification."""
    INFRASTRUCTURAL = 3  # Process first
    COMPOSITIONAL = 2    # Process second
    FOUNDATIONAL = 1     # Process last


@dataclass
class HandlerContext:
    """Context information for component processing."""
    app_container: Optional[str]
    namespace: str
    vcluster: str
    oam_application_name: str
    oam_application_namespace: str
    github_owner: str
    existing_components: List[str]
    processed_components: Dict[str, Any]  # For reference resolution


@dataclass
class HandlerResult:
    """Result from handler execution."""
    success: bool
    workflow_name: Optional[str]
    workflow_run_name: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    pattern: Optional[ComponentPattern] = None


class PatternHandler(ABC):
    """Abstract base class for pattern handlers."""
    
    @abstractmethod
    def get_pattern(self) -> ComponentPattern:
        """Return the pattern this handler implements."""
        pass
    
    @abstractmethod
    def can_handle(self, component_type: str) -> bool:
        """Check if this handler can process the component type."""
        pass
    
    @abstractmethod
    def get_workflow_name(self, component: Dict[str, Any]) -> str:
        """Get the Argo workflow name for this component."""
        pass
    
    @abstractmethod
    def validate_prerequisites(self, component: Dict[str, Any], context: HandlerContext) -> HandlerResult:
        """Validate all prerequisites before processing."""
        pass
    
    @abstractmethod
    def prepare_workflow_params(self, component: Dict[str, Any], context: HandlerContext) -> Dict[str, Any]:
        """Prepare parameters for the Argo workflow."""
        pass
    
    def resolve_references(self, component: Dict[str, Any], context: HandlerContext) -> Dict[str, Any]:
        """Resolve references to other components (mainly Pattern 3)."""
        properties = component.get("properties", {})
        
        # Check for database reference
        if "database" in properties:
            db_ref = properties["database"]
            if db_ref in context.processed_components:
                properties["database_url"] = self._get_connection_string(db_ref, context)
                logger.info(f"Resolved database reference: {db_ref}")
        
        # Check for cache reference
        if "cache" in properties:
            cache_ref = properties["cache"]
            if cache_ref in context.processed_components:
                properties["cache_url"] = self._get_connection_string(cache_ref, context)
                logger.info(f"Resolved cache reference: {cache_ref}")
        
        # Check for realtime reference (existing pattern)
        if "realtime" in properties:
            rt_ref = properties["realtime"]
            if rt_ref in context.processed_components:
                properties["realtime_endpoint"] = self._get_endpoint(rt_ref, context)
                logger.info(f"Resolved realtime reference: {rt_ref}")
        
        return component
    
    def handle(self, component: Dict[str, Any], context: HandlerContext, argo_client) -> HandlerResult:
        """Common handling logic for all patterns."""
        try:
            # Step 1: Validate prerequisites
            validation = self.validate_prerequisites(component, context)
            if not validation.success:
                return validation
            
            # Step 2: Resolve references
            component = self.resolve_references(component, context)
            
            # Step 3: Get workflow name
            workflow_name = self.get_workflow_name(component)
            
            # Step 4: Prepare parameters
            params = self.prepare_workflow_params(component, context)
            
            # Step 5: Trigger workflow
            logger.info(f"Triggering workflow {workflow_name} for {component.get('name')}")
            workflow_run = argo_client.create_workflow_from_template(
                workflow_template_name=workflow_name,
                parameters=params,
                namespace="argo"
            )
            
            # Step 6: Update processed components
            workflow_run_name = workflow_run.get("metadata", {}).get("name", "unknown") if isinstance(workflow_run, dict) else workflow_run.metadata.name
            context.processed_components[component.get("name")] = {
                "type": component.get("type"),
                "pattern": self.get_pattern().value,
                "workflow": workflow_name,
                "run": workflow_run_name
            }
            
            return HandlerResult(
                success=True,
                workflow_name=workflow_name,
                workflow_run_name=workflow_run_name,
                error=None,
                metadata={"parameters": params},
                pattern=self.get_pattern()
            )
            
        except Exception as e:
            logger.error(f"Failed to handle component {component.get('name')}: {str(e)}")
            return HandlerResult(
                success=False,
                workflow_name=None,
                workflow_run_name=None,
                error=str(e),
                metadata={"component": component},
                pattern=self.get_pattern()
            )
    
    def _get_connection_string(self, ref: str, context: HandlerContext) -> str:
        """Get connection string for a referenced component."""
        # This would typically query the actual secret
        return f"connection://{ref}"
    
    def _get_endpoint(self, ref: str, context: HandlerContext) -> str:
        """Get endpoint for a referenced component."""
        # This would typically query the actual service
        return f"http://{ref}.{context.namespace}.svc.cluster.local"
    
    def get_component_definition_metadata(self, component_type: str) -> Dict[str, Any]:
        """Fetch ComponentDefinition from K8s to check requires-source-code annotation."""
        import subprocess
        import json
        
        try:
            # Query Kubernetes for ComponentDefinition
            cmd = ["kubectl", "get", "componentdefinition", component_type, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                component_def = json.loads(result.stdout)
                annotations = component_def.get("metadata", {}).get("annotations", {})
                
                # Check for requires-source-code annotation
                requires_source = annotations.get("definition.oam.dev/requires-source-code", "false")
                
                return {
                    "requires_source_code": requires_source.lower() == "true",
                    "component_type": component_type,
                    "annotations": annotations,
                    "found": True
                }
            else:
                logger.warning(f"ComponentDefinition not found for {component_type}")
                # Default behavior based on known types
                default_requires_source = component_type in [
                    "webservice", "webservice-k8s", "orchestration-service",
                    "identity-service", "rasa-chatbot", "camunda-orchestrator"
                ]
                return {
                    "requires_source_code": default_requires_source,
                    "component_type": component_type,
                    "annotations": {},
                    "found": False
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout fetching ComponentDefinition for {component_type}")
        except Exception as e:
            logger.error(f"Error fetching ComponentDefinition for {component_type}: {e}")
        
        # Fallback to safe default
        return {
            "requires_source_code": False,
            "component_type": component_type,
            "annotations": {},
            "found": False
        }