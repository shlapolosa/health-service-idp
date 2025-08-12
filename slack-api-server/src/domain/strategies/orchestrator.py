"""Pattern orchestrator for handling OAM applications with 3-2-1 processing order."""

from typing import Dict, Any, List, Optional
import logging
from collections import defaultdict

from .base import PatternHandler, ComponentPattern, HandlerContext, HandlerResult
from .pattern1_foundational import Pattern1FoundationalHandler
from .pattern2_compositional import Pattern2CompositionalHandler
from .pattern3_infrastructural import Pattern3InfrastructuralHandler

logger = logging.getLogger(__name__)


class PatternOrchestrator:
    """Orchestrates component processing in Pattern 3 → 2 → 1 order."""
    
    def __init__(self, argo_client=None):
        """Initialize with pattern handlers and optional Argo client."""
        self.handlers = {
            ComponentPattern.INFRASTRUCTURAL: Pattern3InfrastructuralHandler(),
            ComponentPattern.COMPOSITIONAL: Pattern2CompositionalHandler(),
            ComponentPattern.FOUNDATIONAL: Pattern1FoundationalHandler()
        }
        self.argo_client = argo_client
        self.processed_components = {}
    
    def classify_component(self, component: Dict[str, Any]) -> Optional[ComponentPattern]:
        """Classify a component into its pattern category."""
        component_type = component.get("type")
        
        # Try each handler to see which can handle this component
        for pattern, handler in self.handlers.items():
            if handler.can_handle(component_type):
                return pattern
        
        logger.warning(f"Unknown component type: {component_type}")
        return None
    
    def sort_components_by_pattern(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort components by pattern priority: 3 → 2 → 1."""
        pattern_groups = defaultdict(list)
        
        for component in components:
            pattern = self.classify_component(component)
            if pattern:
                pattern_groups[pattern].append(component)
            else:
                # Unknown components go last
                pattern_groups[ComponentPattern.FOUNDATIONAL].append(component)
        
        # Process in order: Pattern 3 (Infrastructural) → Pattern 2 (Compositional) → Pattern 1 (Foundational)
        sorted_components = []
        sorted_components.extend(pattern_groups[ComponentPattern.INFRASTRUCTURAL])
        sorted_components.extend(pattern_groups[ComponentPattern.COMPOSITIONAL])
        sorted_components.extend(pattern_groups[ComponentPattern.FOUNDATIONAL])
        
        logger.info(f"Component processing order: "
                   f"Pattern 3: {len(pattern_groups[ComponentPattern.INFRASTRUCTURAL])}, "
                   f"Pattern 2: {len(pattern_groups[ComponentPattern.COMPOSITIONAL])}, "
                   f"Pattern 1: {len(pattern_groups[ComponentPattern.FOUNDATIONAL])}")
        
        return sorted_components
    
    def handle_oam_application(
        self,
        oam_application: Dict[str, Any],
        namespace: str = "default",
        vcluster: str = "",
        github_owner: str = ""
    ) -> List[HandlerResult]:
        """Process an OAM application with all its components in pattern order."""
        results = []
        
        # Extract application metadata
        app_metadata = oam_application.get("metadata", {})
        app_spec = oam_application.get("spec", {})
        app_name = app_metadata.get("name", "unknown")
        app_namespace = app_metadata.get("namespace", namespace)
        
        # Check for AppContainer label (monorepo indicator)
        app_labels = app_metadata.get("labels", {})
        app_container = app_labels.get("app-container")
        
        # Get components
        components = app_spec.get("components", [])
        if not components:
            logger.warning(f"No components found in OAM application {app_name}")
            return results
        
        # Create handler context
        context = HandlerContext(
            app_container=app_container,
            namespace=namespace,
            vcluster=vcluster or app_name,  # Default vcluster to app name
            oam_application_name=app_name,
            oam_application_namespace=app_namespace,
            github_owner=github_owner or "default-owner",
            existing_components=list(self.processed_components.keys()),
            processed_components=self.processed_components
        )
        
        # Sort components by pattern
        sorted_components = self.sort_components_by_pattern(components)
        
        # Process each component in order
        for component in sorted_components:
            component_name = component.get("name", "unknown")
            component_type = component.get("type", "unknown")
            pattern = self.classify_component(component)
            
            if not pattern:
                logger.error(f"Cannot classify component {component_name} of type {component_type}")
                results.append(HandlerResult(
                    success=False,
                    workflow_name=None,
                    workflow_run_name=None,
                    error=f"Unknown component type: {component_type}",
                    metadata={"component": component_name},
                    pattern=None
                ))
                continue
            
            handler = self.handlers[pattern]
            logger.info(f"Processing Pattern {pattern.value} component: {component_name} (type: {component_type})")
            
            try:
                # Handle the component
                if self.argo_client:
                    result = handler.handle(component, context, self.argo_client)
                else:
                    # Dry run mode - just validate and prepare
                    validation = handler.validate_prerequisites(component, context)
                    if not validation.success:
                        result = validation
                    else:
                        # Resolve references
                        component = handler.resolve_references(component, context)
                        workflow_name = handler.get_workflow_name(component)
                        params = handler.prepare_workflow_params(component, context)
                        
                        result = HandlerResult(
                            success=True,
                            workflow_name=workflow_name,
                            workflow_run_name="dry-run",
                            error=None,
                            metadata={"parameters": params, "dry_run": True},
                            pattern=pattern
                        )
                
                results.append(result)
                
                # Track processed component for reference resolution
                if result.success:
                    self.processed_components[component_name] = {
                        "type": component_type,
                        "pattern": pattern.value,
                        "workflow": result.workflow_name,
                        "run": result.workflow_run_name
                    }
                    # Update context with new processed component
                    context.existing_components.append(component_name)
                
            except Exception as e:
                logger.error(f"Failed to process component {component_name}: {str(e)}", exc_info=True)
                results.append(HandlerResult(
                    success=False,
                    workflow_name=None,
                    workflow_run_name=None,
                    error=str(e),
                    metadata={"component": component_name, "type": component_type},
                    pattern=pattern
                ))
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        logger.info(f"OAM Application {app_name} processing complete: "
                   f"{successful} successful, {failed} failed")
        
        return results
    
    def get_processing_summary(self, results: List[HandlerResult]) -> Dict[str, Any]:
        """Generate a summary of processing results."""
        summary = {
            "total": len(results),
            "successful": 0,
            "failed": 0,
            "by_pattern": {
                "pattern_3": {"total": 0, "successful": 0, "failed": 0},
                "pattern_2": {"total": 0, "successful": 0, "failed": 0},
                "pattern_1": {"total": 0, "successful": 0, "failed": 0}
            },
            "workflows_triggered": [],
            "errors": []
        }
        
        for result in results:
            if result.success:
                summary["successful"] += 1
                if result.workflow_name:
                    summary["workflows_triggered"].append({
                        "workflow": result.workflow_name,
                        "run": result.workflow_run_name
                    })
            else:
                summary["failed"] += 1
                if result.error:
                    summary["errors"].append(result.error)
            
            # Track by pattern
            if result.pattern:
                pattern_key = f"pattern_{result.pattern.value}"
                summary["by_pattern"][pattern_key]["total"] += 1
                if result.success:
                    summary["by_pattern"][pattern_key]["successful"] += 1
                else:
                    summary["by_pattern"][pattern_key]["failed"] += 1
        
        return summary
    
    def reset(self):
        """Reset the orchestrator state for a new application."""
        self.processed_components = {}
        logger.info("Orchestrator state reset")