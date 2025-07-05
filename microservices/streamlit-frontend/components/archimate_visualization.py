"""
ArchiMate Visualization Component

This component provides ArchiMate-compliant architecture visualization using 
modern web technologies (D3.js/Cytoscape.js) with interactive features.
"""
import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, List, Any, Optional, Tuple
import json
import uuid
from enum import Enum
from .archimate_performance import (
    get_performance_optimizer, 
    get_performance_monitor,
    PerformanceLevel,
    ViewportBounds
)


class ArchimateLayer(Enum):
    """ArchiMate 3.2 architectural layers and aspects"""
    STRATEGY = "strategy"
    BUSINESS = "business" 
    APPLICATION = "application"
    TECHNOLOGY = "technology"
    PHYSICAL = "physical"
    IMPLEMENTATION = "implementation"
    MOTIVATION = "motivation"


class ArchimateElementType(Enum):
    """ArchiMate 3.2 element types with their standard shapes and categories"""
    
    # Strategy layer (Purple #CC99FF) - Strategy elements
    RESOURCE = "resource"
    CAPABILITY = "capability"
    COURSE_OF_ACTION = "course_of_action"
    VALUE_STREAM = "value_stream"
    
    # Business layer (Yellow #FFFF99)
    # Active structure elements
    BUSINESS_ACTOR = "business_actor"
    BUSINESS_ROLE = "business_role"
    BUSINESS_COLLABORATION = "business_collaboration"
    BUSINESS_INTERFACE = "business_interface"
    
    # Behavior elements
    BUSINESS_PROCESS = "business_process"
    BUSINESS_FUNCTION = "business_function"
    BUSINESS_INTERACTION = "business_interaction"
    BUSINESS_EVENT = "business_event"
    BUSINESS_SERVICE = "business_service"
    
    # Passive structure elements
    BUSINESS_OBJECT = "business_object"
    CONTRACT = "contract"
    REPRESENTATION = "representation"
    PRODUCT = "product"
    
    # Application layer (Blue #99CCFF)
    # Active structure elements
    APPLICATION_COMPONENT = "application_component"
    APPLICATION_COLLABORATION = "application_collaboration"
    APPLICATION_INTERFACE = "application_interface"
    
    # Behavior elements
    APPLICATION_FUNCTION = "application_function"
    APPLICATION_INTERACTION = "application_interaction"
    APPLICATION_PROCESS = "application_process"
    APPLICATION_EVENT = "application_event"
    APPLICATION_SERVICE = "application_service"
    
    # Passive structure elements
    DATA_OBJECT = "data_object"
    
    # Technology layer (Orange #FFCC99)
    # Active structure elements
    NODE = "node"
    DEVICE = "device"
    SYSTEM_SOFTWARE = "system_software"
    TECHNOLOGY_COLLABORATION = "technology_collaboration"
    TECHNOLOGY_INTERFACE = "technology_interface"
    COMMUNICATION_NETWORK = "communication_network"
    PATH = "path"
    
    # Behavior elements
    TECHNOLOGY_FUNCTION = "technology_function"
    TECHNOLOGY_PROCESS = "technology_process"
    TECHNOLOGY_INTERACTION = "technology_interaction"
    TECHNOLOGY_EVENT = "technology_event"
    TECHNOLOGY_SERVICE = "technology_service"
    
    # Passive structure elements
    ARTIFACT = "artifact"
    
    # Physical layer (Light Green #C8E6C8)
    # Active structure elements
    EQUIPMENT = "equipment"
    FACILITY = "facility"
    DISTRIBUTION_NETWORK = "distribution_network"
    
    # Behavior elements
    PHYSICAL_PROCESS = "physical_process"
    PHYSICAL_FUNCTION = "physical_function"
    PHYSICAL_INTERACTION = "physical_interaction"
    PHYSICAL_EVENT = "physical_event"
    PHYSICAL_SERVICE = "physical_service"
    
    # Passive structure elements
    MATERIAL = "material"
    
    # Implementation & Migration layer (Light Brown #E6CC99)
    WORK_PACKAGE = "work_package"
    DELIVERABLE = "deliverable"
    IMPLEMENTATION_EVENT = "implementation_event"
    PLATEAU = "plateau"
    GAP = "gap"
    
    # Motivation elements (Light Pink #F0D0F0)
    STAKEHOLDER = "stakeholder"
    DRIVER = "driver"
    ASSESSMENT = "assessment"
    GOAL = "goal"
    OUTCOME = "outcome"
    PRINCIPLE = "principle"
    REQUIREMENT = "requirement"
    CONSTRAINT = "constraint"
    MEANING = "meaning"
    VALUE = "value"
    
    # Composite elements
    LOCATION = "location"
    GROUPING = "grouping"


class VisualizationEngine(Enum):
    """Available visualization engines"""
    D3JS = "d3js"
    CYTOSCAPE = "cytoscape"


class ArchimateElement:
    """Represents a single ArchiMate element"""
    
    def __init__(
        self,
        element_id: str,
        name: str,
        element_type: ArchimateElementType,
        layer: ArchimateLayer,
        description: str = "",
        properties: Optional[Dict[str, Any]] = None,
        position: Optional[Tuple[float, float]] = None,
        is_pending: bool = False
    ):
        self.element_id = element_id
        self.name = name
        self.element_type = element_type
        self.layer = layer
        self.description = description
        self.properties = properties or {}
        self.position = position or (0, 0)
        self.is_pending = is_pending
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert element to dictionary for JSON serialization"""
        return {
            "id": self.element_id,
            "name": self.name,
            "type": self.element_type.value,
            "layer": self.layer.value,
            "description": self.description,
            "properties": self.properties,
            "position": {"x": self.position[0], "y": self.position[1]},
            "is_pending": self.is_pending,
            "color": self._get_layer_color(),
            "shape": self._get_element_shape()
        }
    
    def _get_layer_color(self) -> str:
        """Get ArchiMate 3.2 standard color for the layer"""
        layer_colors = {
            ArchimateLayer.STRATEGY: "#CC99FF",       # Purple
            ArchimateLayer.BUSINESS: "#FFFF99",       # Yellow
            ArchimateLayer.APPLICATION: "#99CCFF",    # Blue
            ArchimateLayer.TECHNOLOGY: "#FFCC99",     # Orange
            ArchimateLayer.PHYSICAL: "#C8E6C8",       # Light Green
            ArchimateLayer.IMPLEMENTATION: "#E6CC99", # Light Brown
            ArchimateLayer.MOTIVATION: "#F0D0F0"      # Light Pink
        }
        return layer_colors.get(self.layer, "#FFFFFF")
    
    def _get_element_shape(self) -> str:
        """Get ArchiMate 3.2 standard shape for the element type"""
        
        # Strategy elements (purple) - diamonds for value, capability, resource
        if self.element_type in [ArchimateElementType.RESOURCE, ArchimateElementType.CAPABILITY, 
                                ArchimateElementType.VALUE_STREAM]:
            return "diamond"
        if self.element_type == ArchimateElementType.COURSE_OF_ACTION:
            return "hexagon"
        
        # Motivation elements (light pink) - rounded rectangles
        if self.layer == ArchimateLayer.MOTIVATION:
            if self.element_type in [ArchimateElementType.STAKEHOLDER]:
                return "ellipse"  # Actor-like elements
            elif self.element_type in [ArchimateElementType.DRIVER, ArchimateElementType.ASSESSMENT,
                                     ArchimateElementType.GOAL, ArchimateElementType.OUTCOME,
                                     ArchimateElementType.PRINCIPLE, ArchimateElementType.REQUIREMENT,
                                     ArchimateElementType.CONSTRAINT]:
                return "round-rectangle"
            elif self.element_type in [ArchimateElementType.MEANING, ArchimateElementType.VALUE]:
                return "ellipse"
            return "round-rectangle"
        
        # Active structure elements (rectangles with rounded corners)
        active_structure = [
            # Business active structure
            ArchimateElementType.BUSINESS_ACTOR, ArchimateElementType.BUSINESS_ROLE, 
            ArchimateElementType.BUSINESS_COLLABORATION, ArchimateElementType.BUSINESS_INTERFACE,
            # Application active structure
            ArchimateElementType.APPLICATION_COMPONENT, ArchimateElementType.APPLICATION_COLLABORATION,
            ArchimateElementType.APPLICATION_INTERFACE,
            # Technology active structure
            ArchimateElementType.NODE, ArchimateElementType.DEVICE, ArchimateElementType.SYSTEM_SOFTWARE,
            ArchimateElementType.TECHNOLOGY_COLLABORATION, ArchimateElementType.TECHNOLOGY_INTERFACE,
            ArchimateElementType.COMMUNICATION_NETWORK, ArchimateElementType.PATH,
            # Physical active structure
            ArchimateElementType.EQUIPMENT, ArchimateElementType.FACILITY, 
            ArchimateElementType.DISTRIBUTION_NETWORK
        ]
        if self.element_type in active_structure:
            return "round-rectangle"
        
        # Behavior elements (rounded rectangles with different styling)
        behavior_elements = [
            # Business behavior
            ArchimateElementType.BUSINESS_PROCESS, ArchimateElementType.BUSINESS_FUNCTION,
            ArchimateElementType.BUSINESS_INTERACTION, ArchimateElementType.BUSINESS_SERVICE,
            # Application behavior  
            ArchimateElementType.APPLICATION_FUNCTION, ArchimateElementType.APPLICATION_INTERACTION,
            ArchimateElementType.APPLICATION_PROCESS, ArchimateElementType.APPLICATION_SERVICE,
            # Technology behavior
            ArchimateElementType.TECHNOLOGY_FUNCTION, ArchimateElementType.TECHNOLOGY_PROCESS,
            ArchimateElementType.TECHNOLOGY_INTERACTION, ArchimateElementType.TECHNOLOGY_SERVICE,
            # Physical behavior
            ArchimateElementType.PHYSICAL_PROCESS, ArchimateElementType.PHYSICAL_FUNCTION,
            ArchimateElementType.PHYSICAL_INTERACTION, ArchimateElementType.PHYSICAL_SERVICE
        ]
        if self.element_type in behavior_elements:
            return "ellipse"
        
        # Event elements (pentagon-like)
        event_elements = [
            ArchimateElementType.BUSINESS_EVENT, ArchimateElementType.APPLICATION_EVENT,
            ArchimateElementType.TECHNOLOGY_EVENT, ArchimateElementType.PHYSICAL_EVENT,
            ArchimateElementType.IMPLEMENTATION_EVENT
        ]
        if self.element_type in event_elements:
            return "pentagon"
        
        # Passive structure elements (rectangles)
        passive_structure = [
            # Business passive structure
            ArchimateElementType.BUSINESS_OBJECT, ArchimateElementType.CONTRACT,
            ArchimateElementType.REPRESENTATION, ArchimateElementType.PRODUCT,
            # Application passive structure
            ArchimateElementType.DATA_OBJECT,
            # Technology passive structure
            ArchimateElementType.ARTIFACT,
            # Physical passive structure
            ArchimateElementType.MATERIAL
        ]
        if self.element_type in passive_structure:
            return "rectangle"
        
        # Implementation & Migration elements
        if self.layer == ArchimateLayer.IMPLEMENTATION:
            if self.element_type == ArchimateElementType.WORK_PACKAGE:
                return "round-rectangle"
            elif self.element_type == ArchimateElementType.DELIVERABLE:
                return "rectangle"
            elif self.element_type == ArchimateElementType.PLATEAU:
                return "round-rectangle"
            elif self.element_type == ArchimateElementType.GAP:
                return "rectangle"
        
        # Composite elements
        if self.element_type in [ArchimateElementType.LOCATION, ArchimateElementType.GROUPING]:
            return "round-rectangle"
        
        return "rectangle"  # default


class ArchimateRelationship:
    """Represents a relationship between ArchiMate elements"""
    
    def __init__(
        self,
        relationship_id: str,
        source_id: str,
        target_id: str,
        relationship_type: str,
        description: str = "",
        is_pending: bool = False
    ):
        self.relationship_id = relationship_id
        self.source_id = source_id
        self.target_id = target_id
        self.relationship_type = relationship_type
        self.description = description
        self.is_pending = is_pending
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary for JSON serialization"""
        return {
            "id": self.relationship_id,
            "source": self.source_id,
            "target": self.target_id,
            "type": self.relationship_type,
            "description": self.description,
            "is_pending": self.is_pending,
            "style": self._get_relationship_style()
        }
    
    def _get_relationship_style(self) -> Dict[str, Any]:
        """Get style properties for the ArchiMate 3.2 relationship"""
        styles = {
            # Structural relationships
            "composition": {"line_style": "solid", "arrow": "filled_diamond", "arrow_position": "source"},
            "aggregation": {"line_style": "solid", "arrow": "open_diamond", "arrow_position": "source"},
            "assignment": {"line_style": "solid", "arrow": "filled_circle", "arrow_position": "source"},
            "realization": {"line_style": "dashed", "arrow": "triangle", "arrow_position": "target"},
            
            # Dependency relationships
            "serving": {"line_style": "solid", "arrow": "triangle", "arrow_position": "target"},
            "access": {"line_style": "dotted", "arrow": "triangle", "arrow_position": "target"},
            "influence": {"line_style": "dashed", "arrow": "triangle", "arrow_position": "target"},
            
            # Dynamic relationships  
            "triggering": {"line_style": "solid", "arrow": "triangle", "arrow_position": "target"},
            "flow": {"line_style": "dashed", "arrow": "triangle", "arrow_position": "target"},
            
            # Other relationships
            "specialization": {"line_style": "solid", "arrow": "hollow_triangle", "arrow_position": "target"},
            "association": {"line_style": "solid", "arrow": "none", "arrow_position": "none"}
        }
        return styles.get(self.relationship_type, {"line_style": "solid", "arrow": "triangle", "arrow_position": "target"})


class ArchimateVisualization:
    """Main ArchiMate visualization component"""
    
    def __init__(self, engine: VisualizationEngine = VisualizationEngine.CYTOSCAPE):
        self.engine = engine
        self.elements: Dict[str, ArchimateElement] = {}
        self.relationships: Dict[str, ArchimateRelationship] = {}
        self.layout_settings = {
            "algorithm": "cose",  # For Cytoscape: cose, breadthfirst, circle, concentric, grid
            "animate": True,
            "fit": True,
            "padding": 50
        }
        self.view_settings = {
            "show_labels": True,
            "show_relationships": True,
            "layer_filter": list(ArchimateLayer),
            "zoom_level": 1.0,
            "enable_pan": True,
            "enable_zoom": True
        }
        self.performance_level = PerformanceLevel.MEDIUM
        self.enable_performance_optimization = True
    
    def add_element(self, element: ArchimateElement) -> None:
        """Add an element to the visualization"""
        self.elements[element.element_id] = element
    
    def add_relationship(self, relationship: ArchimateRelationship) -> None:
        """Add a relationship to the visualization"""
        self.relationships[relationship.relationship_id] = relationship
    
    def remove_element(self, element_id: str) -> None:
        """Remove an element and its relationships"""
        if element_id in self.elements:
            del self.elements[element_id]
        
        # Remove relationships involving this element
        to_remove = [
            rel_id for rel_id, rel in self.relationships.items()
            if rel.source_id == element_id or rel.target_id == element_id
        ]
        for rel_id in to_remove:
            del self.relationships[rel_id]
    
    def get_elements_by_layer(self, layer: ArchimateLayer) -> List[ArchimateElement]:
        """Get all elements in a specific layer"""
        return [elem for elem in self.elements.values() if elem.layer == layer]
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export visualization data to dictionary"""
        return {
            "elements": [elem.to_dict() for elem in self.elements.values()],
            "relationships": [rel.to_dict() for rel in self.relationships.values()],
            "layout": self.layout_settings,
            "view": self.view_settings,
            "engine": self.engine.value
        }
    
    def import_from_dict(self, data: Dict[str, Any]) -> None:
        """Import visualization data from dictionary"""
        self.elements.clear()
        self.relationships.clear()
        
        # Import elements
        for elem_data in data.get("elements", []):
            element = ArchimateElement(
                element_id=elem_data["id"],
                name=elem_data["name"],
                element_type=ArchimateElementType(elem_data["type"]),
                layer=ArchimateLayer(elem_data["layer"]),
                description=elem_data.get("description", ""),
                properties=elem_data.get("properties", {}),
                position=(elem_data["position"]["x"], elem_data["position"]["y"]),
                is_pending=elem_data.get("is_pending", False)
            )
            self.add_element(element)
        
        # Import relationships
        for rel_data in data.get("relationships", []):
            relationship = ArchimateRelationship(
                relationship_id=rel_data["id"],
                source_id=rel_data["source"],
                target_id=rel_data["target"],
                relationship_type=rel_data["type"],
                description=rel_data.get("description", ""),
                is_pending=rel_data.get("is_pending", False)
            )
            self.add_relationship(relationship)
        
        # Import settings
        self.layout_settings.update(data.get("layout", {}))
        self.view_settings.update(data.get("view", {}))
    
    def render_streamlit_component(
        self,
        width: int = 800,
        height: int = 600,
        key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Render the visualization as a Streamlit component"""
        
        # Generate unique key if not provided
        if key is None:
            key = f"archimate_viz_{uuid.uuid4().hex[:8]}"
        
        # Prepare data for visualization
        viz_data = self.export_to_dict()
        
        if self.engine == VisualizationEngine.CYTOSCAPE:
            return self._render_cytoscape_component(viz_data, width, height, key)
        elif self.engine == VisualizationEngine.D3JS:
            return self._render_d3_component(viz_data, width, height, key)
        else:
            st.error(f"Unsupported visualization engine: {self.engine}")
            return None
    
    def _render_cytoscape_component(
        self,
        viz_data: Dict[str, Any],
        width: int,
        height: int,
        key: str
    ) -> Optional[Dict[str, Any]]:
        """Render using Cytoscape.js with performance optimization"""
        
        # Apply performance optimization if enabled
        if self.enable_performance_optimization:
            optimizer = get_performance_optimizer(self.performance_level)
            monitor = get_performance_monitor()
            
            # Create viewport bounds (estimate based on width/height)
            viewport = ViewportBounds(0, 0, width, height, self.view_settings.get("zoom_level", 1.0))
            
            # Optimize visualization data
            optimized_elements, optimized_relationships, metrics = optimizer.optimize_visualization_data(
                viz_data["elements"],
                viz_data["relationships"],
                viewport
            )
            
            # Update viz_data with optimized elements
            viz_data["elements"] = optimized_elements
            viz_data["relationships"] = optimized_relationships
            
            # Record performance metrics
            monitor.record_metrics(metrics)
            
            # Use optimized HTML generation
            html_content = optimizer.generate_optimized_cytoscape_html(
                optimized_elements,
                optimized_relationships,
                width,
                height,
                enable_webgl=True
            )
        else:
            # Use standard HTML generation
            html_content = self._generate_cytoscape_html(viz_data, width, height)
        
        # Render as Streamlit component
        result = components.html(
            html_content,
            width=width,
            height=height,
            scrolling=False
        )
        
        return result
    
    def _render_d3_component(
        self,
        viz_data: Dict[str, Any],
        width: int,
        height: int,
        key: str
    ) -> Optional[Dict[str, Any]]:
        """Render using D3.js"""
        
        # Create HTML content with D3.js
        html_content = self._generate_d3_html(viz_data, width, height)
        
        # Render as Streamlit component
        result = components.html(
            html_content,
            width=width,
            height=height,
            scrolling=False
        )
        
        return result
    
    def _map_shape_to_cytoscape(self, archimate_shape: str) -> str:
        """Map ArchiMate shapes to Cytoscape.js supported shapes"""
        shape_mapping = {
            "rectangle": "rectangle",
            "round-rectangle": "round-rectangle", 
            "ellipse": "ellipse",
            "circle": "ellipse",
            "diamond": "diamond",
            "hexagon": "hexagon",
            "pentagon": "pentagon",
            "octagon": "octagon",
            "triangle": "triangle"
        }
        return shape_mapping.get(archimate_shape, "rectangle")
    
    def _get_element_width(self, shape: str) -> int:
        """Get appropriate width for element shape"""
        width_mapping = {
            "rectangle": 100,
            "round-rectangle": 120,
            "ellipse": 100,
            "diamond": 80,
            "hexagon": 90,
            "pentagon": 85,
            "octagon": 85,
            "triangle": 80
        }
        return width_mapping.get(shape, 100)
    
    def _get_element_height(self, shape: str) -> int:
        """Get appropriate height for element shape"""
        height_mapping = {
            "rectangle": 50,
            "round-rectangle": 50,
            "ellipse": 50,
            "diamond": 60,
            "hexagon": 55,
            "pentagon": 55,
            "octagon": 55,
            "triangle": 50
        }
        return height_mapping.get(shape, 50)
    
    def _map_arrow_to_cytoscape(self, archimate_arrow: str, position: str) -> str:
        """Map ArchiMate arrow types to Cytoscape.js arrow shapes"""
        arrow_mapping = {
            "triangle": "triangle",
            "filled_diamond": "diamond",
            "open_diamond": "diamond-tee",
            "filled_circle": "circle",
            "hollow_triangle": "triangle-tee",
            "none": "none"
        }
        
        # Only apply arrow if position matches
        return arrow_mapping.get(archimate_arrow, "triangle")
    
    def _generate_cytoscape_html(self, viz_data: Dict[str, Any], width: int, height: int) -> str:
        """Generate HTML content with Cytoscape.js visualization"""
        
        # Convert data to Cytoscape format
        elements = []
        
        # Add nodes
        for element in viz_data["elements"]:
            node = {
                "data": {
                    "id": element["id"],
                    "label": element["name"],
                    "type": element["type"],
                    "layer": element["layer"],
                    "description": element["description"],
                    "width": self._get_element_width(element["shape"]),
                    "height": self._get_element_height(element["shape"])
                },
                "position": element["position"],
                "classes": f"layer-{element['layer']} {'pending' if element['is_pending'] else ''}",
                "style": {
                    "background-color": element["color"] if not element["is_pending"] else "#CCCCCC",
                    "shape": self._map_shape_to_cytoscape(element["shape"]),
                    "label": element["name"],
                    "text-valign": "center",
                    "text-halign": "center",
                    "font-size": "10px",
                    "font-weight": "bold",
                    "text-wrap": "wrap",
                    "text-max-width": "80px",
                    "border-width": 2,
                    "border-color": "#333333" if not element["is_pending"] else "#999999",
                    "text-outline-width": 1,
                    "text-outline-color": "white"
                }
            }
            elements.append(node)
        
        # Add edges
        for relationship in viz_data["relationships"]:
            edge = {
                "data": {
                    "id": relationship["id"],
                    "source": relationship["source"],
                    "target": relationship["target"],
                    "type": relationship["type"],
                    "description": relationship["description"]
                },
                "classes": "relationship" + (" pending" if relationship["is_pending"] else ""),
                "style": {
                    "line-style": relationship["style"]["line_style"],
                    "target-arrow-shape": self._map_arrow_to_cytoscape(relationship["style"]["arrow"], "target"),
                    "source-arrow-shape": self._map_arrow_to_cytoscape(relationship["style"]["arrow"], "source") if relationship["style"]["arrow_position"] == "source" else "none",
                    "curve-style": "bezier",
                    "line-color": "#999999" if relationship["is_pending"] else "#333333",
                    "target-arrow-color": "#999999" if relationship["is_pending"] else "#333333",
                    "source-arrow-color": "#999999" if relationship["is_pending"] else "#333333",
                    "width": 2
                }
            }
            elements.append(edge)
        
        cytoscape_data = json.dumps(elements)
        layout_settings = json.dumps(viz_data["layout"])
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://unpkg.com/cytoscape@3.25.0/dist/cytoscape.min.js"></script>
            <script src="https://unpkg.com/cytoscape-cose-bilkent@4.1.0/cytoscape-cose-bilkent.js"></script>
            <style>
                #cy {{
                    width: {width}px;
                    height: {height}px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    background-color: #fafafa;
                    position: relative;
                }}
                .tooltip {{
                    position: absolute;
                    background: rgba(0,0,0,0.9);
                    color: white;
                    padding: 10px;
                    border-radius: 6px;
                    font-size: 12px;
                    pointer-events: none;
                    z-index: 1000;
                    max-width: 250px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
                    border: 1px solid rgba(255,255,255,0.2);
                }}
                .controls {{
                    position: absolute;
                    top: 10px;
                    left: 10px;
                    background: rgba(255,255,255,0.9);
                    padding: 8px;
                    border-radius: 4px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    z-index: 100;
                }}
                .layer-toggle {{
                    display: inline-block;
                    margin: 2px;
                    padding: 4px 8px;
                    background: #e0e0e0;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 10px;
                    user-select: none;
                }}
                .layer-toggle.active {{
                    background: #007bff;
                    color: white;
                }}
                .minimap {{
                    position: absolute;
                    bottom: 10px;
                    right: 10px;
                    width: 150px;
                    height: 100px;
                    border: 1px solid #ccc;
                    background: rgba(255,255,255,0.9);
                    z-index: 100;
                    pointer-events: auto;
                }}
                .status-bar {{
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    background: rgba(0,0,0,0.8);
                    color: white;
                    padding: 4px 8px;
                    font-size: 10px;
                    font-family: monospace;
                }}
            </style>
        </head>
        <body>
            <div id="cy">
                <div class="controls">
                    <div style="margin-bottom: 8px; font-weight: bold;">Layer Filters:</div>
                    <div class="layer-toggle active" data-layer="strategy">Strategy</div>
                    <div class="layer-toggle active" data-layer="motivation">Motivation</div>
                    <div class="layer-toggle active" data-layer="business">Business</div>
                    <div class="layer-toggle active" data-layer="application">Application</div>
                    <div class="layer-toggle active" data-layer="technology">Technology</div>
                    <div class="layer-toggle active" data-layer="physical">Physical</div>
                    <div class="layer-toggle active" data-layer="implementation">Implementation</div>
                    <hr style="margin: 8px 0;">
                    <button onclick="cy.fit()" style="margin: 2px; padding: 4px 8px; font-size: 10px;">Fit to View</button>
                    <button onclick="resetLayout()" style="margin: 2px; padding: 4px 8px; font-size: 10px;">Reset Layout</button>
                    <button onclick="exportView()" style="margin: 2px; padding: 4px 8px; font-size: 10px;">Export PNG</button>
                </div>
                <div class="minimap" id="minimap"></div>
                <div class="status-bar" id="status-bar">
                    Zoom: 1.00x | Elements: 0 | Selected: 0
                </div>
            </div>
            <div id="tooltip" class="tooltip" style="display: none;"></div>
            
            <script>
                var cy = cytoscape({{
                    container: document.getElementById('cy'),
                    elements: {cytoscape_data},
                    style: [
                        {{
                            selector: 'node',
                            style: {{
                                'width': 'data(width)',
                                'height': 'data(height)',
                                'text-wrap': 'wrap',
                                'text-max-width': '80px',
                                'font-family': 'Arial, sans-serif',
                                'text-outline-width': 1,
                                'text-outline-color': 'white',
                                'border-width': 2,
                                'border-opacity': 0.8
                            }}
                        }},
                        {{
                            selector: 'node:selected',
                            style: {{
                                'border-width': 4,
                                'border-color': '#ff6b6b',
                                'box-shadow': '0 0 10px rgba(255, 107, 107, 0.7)'
                            }}
                        }},
                        {{
                            selector: 'node.highlighted',
                            style: {{
                                'border-width': 3,
                                'border-color': '#4ecdc4',
                                'box-shadow': '0 0 8px rgba(78, 205, 196, 0.6)'
                            }}
                        }},
                        {{
                            selector: 'edge',
                            style: {{
                                'width': 2,
                                'font-size': '9px',
                                'text-rotation': 'autorotate',
                                'text-margin-y': -10,
                                'curve-style': 'bezier'
                            }}
                        }},
                        {{
                            selector: 'edge:selected',
                            style: {{
                                'width': 4,
                                'line-color': '#ff6b6b',
                                'target-arrow-color': '#ff6b6b'
                            }}
                        }},
                        {{
                            selector: '.pending',
                            style: {{
                                'opacity': 0.6,
                                'line-style': 'dashed'
                            }}
                        }},
                        {{
                            selector: '.filtered',
                            style: {{
                                'opacity': 0.1
                            }}
                        }}
                    ],
                    layout: {layout_settings},
                    zoomingEnabled: true,
                    userZoomingEnabled: true,
                    panningEnabled: true,
                    userPanningEnabled: true,
                    boxSelectionEnabled: true,
                    autoungrabify: false,
                    autounselectify: false,
                    minZoom: 0.1,
                    maxZoom: 5.0
                }});
                
                // Initialize variables
                var tooltip = document.getElementById('tooltip');
                var statusBar = document.getElementById('status-bar');
                var selectedElements = cy.collection();
                var visibleLayers = new Set(['strategy', 'motivation', 'business', 'application', 'technology', 'physical', 'implementation']);
                
                // Update status bar
                function updateStatusBar() {{
                    var zoom = Math.round(cy.zoom() * 100) / 100;
                    var elementCount = cy.nodes().filter(':visible').length;
                    var selectedCount = cy.$(':selected').length;
                    statusBar.innerHTML = 'Zoom: ' + zoom + 'x | Elements: ' + elementCount + ' | Selected: ' + selectedCount;
                }}
                
                // Enhanced tooltip functionality
                cy.on('mouseover', 'node', function(evt){{
                    var node = evt.target;
                    var content = '<div style="border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 6px; margin-bottom: 6px;">' +
                                 '<strong>' + node.data('label') + '</strong></div>' +
                                 '<div><strong>Type:</strong> ' + node.data('type').replace('_', ' ') + '</div>' +
                                 '<div><strong>Layer:</strong> ' + node.data('layer') + '</div>';
                    if (node.data('description')) {{
                        content += '<div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.2);">' +
                                  '<strong>Description:</strong><br>' + node.data('description') + '</div>';
                    }}
                    tooltip.innerHTML = content;
                    tooltip.style.display = 'block';
                    
                    // Highlight connected elements
                    var connected = node.neighborhood().add(node);
                    cy.elements().removeClass('highlighted');
                    connected.addClass('highlighted');
                }});
                
                cy.on('mouseout', 'node', function(evt){{
                    tooltip.style.display = 'none';
                    cy.elements().removeClass('highlighted');
                }});
                
                cy.on('mousemove', function(evt){{
                    if (tooltip.style.display === 'block') {{
                        tooltip.style.left = (evt.originalEvent.clientX + 15) + 'px';
                        tooltip.style.top = (evt.originalEvent.clientY + 15) + 'px';
                    }}
                }});
                
                // Enhanced interaction events
                cy.on('tap', 'node', function(evt){{
                    var node = evt.target;
                    console.log('Node selected:', node.data());
                    updateStatusBar();
                }});
                
                cy.on('tap', 'edge', function(evt){{
                    var edge = evt.target;
                    console.log('Edge selected:', edge.data());
                    updateStatusBar();
                }});
                
                cy.on('unselect', function(evt){{
                    updateStatusBar();
                }});
                
                // Viewport change tracking
                cy.on('viewport', function(){{
                    updateStatusBar();
                }});
                
                // Layer filtering functionality
                document.querySelectorAll('.layer-toggle').forEach(function(toggle) {{
                    toggle.addEventListener('click', function() {{
                        var layer = this.getAttribute('data-layer');
                        var isActive = this.classList.contains('active');
                        
                        if (isActive) {{
                            this.classList.remove('active');
                            visibleLayers.delete(layer);
                        }} else {{
                            this.classList.add('active');
                            visibleLayers.add(layer);
                        }}
                        
                        // Apply layer filtering
                        cy.nodes().forEach(function(node) {{
                            var nodeLayer = node.data('layer');
                            if (visibleLayers.has(nodeLayer)) {{
                                node.removeClass('filtered');
                                node.style('display', 'element');
                            }} else {{
                                node.addClass('filtered');
                                node.style('display', 'none');
                            }}
                        }});
                        
                        // Hide edges connected to filtered nodes
                        cy.edges().forEach(function(edge) {{
                            var sourceLayer = edge.source().data('layer');
                            var targetLayer = edge.target().data('layer');
                            if (visibleLayers.has(sourceLayer) && visibleLayers.has(targetLayer)) {{
                                edge.removeClass('filtered');
                                edge.style('display', 'element');
                            }} else {{
                                edge.addClass('filtered');
                                edge.style('display', 'none');
                            }}
                        }});
                        
                        updateStatusBar();
                    }});
                }});
                
                // Additional utility functions
                function resetLayout() {{
                    cy.layout({layout_settings}).run();
                }}
                
                function exportView() {{
                    var png64 = cy.png({{scale: 2, full: true}});
                    var link = document.createElement('a');
                    link.download = 'archimate-diagram.png';
                    link.href = png64;
                    link.click();
                }}
                
                // Keyboard shortcuts
                document.addEventListener('keydown', function(evt) {{
                    if (evt.ctrlKey || evt.metaKey) {{
                        switch(evt.key) {{
                            case 'a':
                                evt.preventDefault();
                                cy.nodes(':visible').select();
                                updateStatusBar();
                                break;
                            case 'f':
                                evt.preventDefault();
                                cy.fit();
                                break;
                            case 's':
                                evt.preventDefault();
                                exportView();
                                break;
                        }}
                    }}
                    if (evt.key === 'Escape') {{
                        cy.elements().unselect();
                        updateStatusBar();
                    }}
                }});
                
                // Initialize minimap (simplified version)
                function initMinimap() {{
                    var minimap = document.getElementById('minimap');
                    var minimapCy = cytoscape({{
                        container: minimap,
                        elements: cy.elements().jsons(),
                        style: [{{
                            selector: 'node',
                            style: {{
                                'width': 8,
                                'height': 6,
                                'background-color': '#666'
                            }}
                        }}, {{
                            selector: 'edge',
                            style: {{
                                'width': 1,
                                'line-color': '#999'
                            }}
                        }}],
                        layout: {{ name: 'preset' }},
                        zoomingEnabled: false,
                        userZoomingEnabled: false,
                        panningEnabled: false,
                        userPanningEnabled: false,
                        boxSelectionEnabled: false,
                        autoungrabify: true,
                        autounselectify: true
                    }});
                    
                    minimapCy.fit();
                    
                    // Sync minimap with main view
                    cy.on('viewport', function() {{
                        // Simple viewport indicator could be added here
                    }});
                }}
                
                // Initialize everything
                cy.ready(function() {{
                    cy.fit();
                    updateStatusBar();
                    initMinimap();
                }});
            </script>
        </body>
        </html>
        """
        
        return html_template
    
    def _generate_d3_html(self, viz_data: Dict[str, Any], width: int, height: int) -> str:
        """Generate HTML content with D3.js visualization"""
        
        # Convert data to D3 format
        nodes = viz_data["elements"]
        links = [
            {
                "source": rel["source"],
                "target": rel["target"],
                "type": rel["type"],
                "description": rel["description"],
                "is_pending": rel["is_pending"]
            }
            for rel in viz_data["relationships"]
        ]
        
        d3_data = json.dumps({"nodes": nodes, "links": links})
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                #d3-container {{
                    width: {width}px;
                    height: {height}px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    background-color: #fafafa;
                }}
                .node {{
                    stroke: #333;
                    stroke-width: 2px;
                    cursor: pointer;
                }}
                .link {{
                    stroke: #999;
                    stroke-width: 1.5px;
                }}
                .link.pending {{
                    stroke-dasharray: 5,5;
                    stroke: #ccc;
                }}
                .node.pending {{
                    opacity: 0.6;
                }}
                .tooltip {{
                    position: absolute;
                    background: rgba(0,0,0,0.8);
                    color: white;
                    padding: 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    pointer-events: none;
                    z-index: 1000;
                    max-width: 200px;
                }}
            </style>
        </head>
        <body>
            <div id="d3-container"></div>
            <div id="tooltip" class="tooltip" style="display: none;"></div>
            
            <script>
                const data = {d3_data};
                const width = {width};
                const height = {height};
                
                // Create SVG
                const svg = d3.select("#d3-container")
                    .append("svg")
                    .attr("width", width)
                    .attr("height", height);
                
                // Create force simulation
                const simulation = d3.forceSimulation(data.nodes)
                    .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
                    .force("charge", d3.forceManyBody().strength(-300))
                    .force("center", d3.forceCenter(width / 2, height / 2));
                
                // Create links
                const link = svg.append("g")
                    .selectAll("line")
                    .data(data.links)
                    .join("line")
                    .attr("class", d => "link" + (d.is_pending ? " pending" : ""));
                
                // Create nodes
                const node = svg.append("g")
                    .selectAll("circle")
                    .data(data.nodes)
                    .join("circle")
                    .attr("r", 20)
                    .attr("fill", d => d.color)
                    .attr("class", d => "node" + (d.is_pending ? " pending" : ""))
                    .call(d3.drag()
                        .on("start", dragstarted)
                        .on("drag", dragged)
                        .on("end", dragended));
                
                // Add labels
                const label = svg.append("g")
                    .selectAll("text")
                    .data(data.nodes)
                    .join("text")
                    .text(d => d.name)
                    .attr("font-family", "Arial, sans-serif")
                    .attr("font-size", "10px")
                    .attr("text-anchor", "middle")
                    .attr("dy", ".35em");
                
                // Tooltip
                const tooltip = d3.select("#tooltip");
                
                node.on("mouseover", function(event, d) {{
                    tooltip.html(`<strong>${{d.name}}</strong><br>Type: ${{d.type}}<br>Layer: ${{d.layer}}${{d.description ? '<br>Description: ' + d.description : ''}}`)
                        .style("display", "block")
                        .style("left", (event.pageX + 10) + "px")
                        .style("top", (event.pageY + 10) + "px");
                }})
                .on("mouseout", function() {{
                    tooltip.style("display", "none");
                }})
                .on("click", function(event, d) {{
                    console.log("Node clicked:", d);
                }});
                
                // Update positions
                simulation.on("tick", () => {{
                    link
                        .attr("x1", d => d.source.x)
                        .attr("y1", d => d.source.y)
                        .attr("x2", d => d.target.x)
                        .attr("y2", d => d.target.y);
                    
                    node
                        .attr("cx", d => d.x)
                        .attr("cy", d => d.y);
                    
                    label
                        .attr("x", d => d.x)
                        .attr("y", d => d.y);
                }});
                
                // Drag functions
                function dragstarted(event, d) {{
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                }}
                
                function dragged(event, d) {{
                    d.fx = event.x;
                    d.fy = event.y;
                }}
                
                function dragended(event, d) {{
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                }}
            </script>
        </body>
        </html>
        """
        
        return html_template


def create_sample_architecture() -> ArchimateVisualization:
    """Create a comprehensive ArchiMate 3.2 sample architecture for demonstration"""
    viz = ArchimateVisualization(engine=VisualizationEngine.CYTOSCAPE)
    
    # Strategy layer elements
    customer_satisfaction = ArchimateElement(
        "customer_satisfaction", "Customer Satisfaction", ArchimateElementType.VALUE_STREAM,
        ArchimateLayer.STRATEGY, "Primary value driver for digital transformation", position=(150, 50)
    )
    digital_capability = ArchimateElement(
        "digital_capability", "Digital Capability", ArchimateElementType.CAPABILITY,
        ArchimateLayer.STRATEGY, "Organization's digital transformation capability", position=(350, 50)
    )
    
    # Motivation layer elements
    customer_stakeholder = ArchimateElement(
        "customer_stakeholder", "Customer", ArchimateElementType.STAKEHOLDER,
        ArchimateLayer.MOTIVATION, "Primary business stakeholder", position=(50, 150)
    )
    efficiency_goal = ArchimateElement(
        "efficiency_goal", "Improve Efficiency", ArchimateElementType.GOAL,
        ArchimateLayer.MOTIVATION, "Increase operational efficiency by 25%", position=(250, 150)
    )
    
    # Business layer elements
    customer_actor = ArchimateElement(
        "customer_actor", "Customer", ArchimateElementType.BUSINESS_ACTOR, 
        ArchimateLayer.BUSINESS, "External customer actor", position=(100, 250)
    )
    order_process = ArchimateElement(
        "order_process", "Order Management Process", ArchimateElementType.BUSINESS_PROCESS,
        ArchimateLayer.BUSINESS, "End-to-end order processing", position=(300, 250)
    )
    customer_service = ArchimateElement(
        "customer_service", "Customer Service", ArchimateElementType.BUSINESS_SERVICE,
        ArchimateLayer.BUSINESS, "Customer support and interaction service", position=(500, 250)
    )
    order_object = ArchimateElement(
        "order_object", "Order", ArchimateElementType.BUSINESS_OBJECT,
        ArchimateLayer.BUSINESS, "Customer order information", position=(400, 350)
    )
    
    # Application layer elements
    crm_component = ArchimateElement(
        "crm_component", "CRM System", ArchimateElementType.APPLICATION_COMPONENT,
        ArchimateLayer.APPLICATION, "Customer relationship management system", position=(100, 450)
    )
    order_service = ArchimateElement(
        "order_service", "Order Service", ArchimateElementType.APPLICATION_SERVICE,
        ArchimateLayer.APPLICATION, "Digital order processing service", position=(300, 450)
    )
    order_data = ArchimateElement(
        "order_data", "Order Data", ArchimateElementType.DATA_OBJECT,
        ArchimateLayer.APPLICATION, "Structured order information", position=(500, 450)
    )
    
    # Technology layer elements  
    database_node = ArchimateElement(
        "database_node", "Database Server", ArchimateElementType.NODE,
        ArchimateLayer.TECHNOLOGY, "Primary database infrastructure", position=(200, 550)
    )
    web_server = ArchimateElement(
        "web_server", "Web Server", ArchimateElementType.DEVICE,
        ArchimateLayer.TECHNOLOGY, "Application hosting infrastructure", position=(400, 550)
    )
    
    # Physical layer elements
    data_center = ArchimateElement(
        "data_center", "Primary Data Center", ArchimateElementType.FACILITY,
        ArchimateLayer.PHYSICAL, "Main hosting facility", position=(300, 650)
    )
    
    # Implementation layer elements
    digital_transformation = ArchimateElement(
        "digital_transformation", "Digital Transformation", ArchimateElementType.WORK_PACKAGE,
        ArchimateLayer.IMPLEMENTATION, "Overall transformation initiative", position=(150, 750)
    )
    new_system_deliverable = ArchimateElement(
        "new_system", "New Order System", ArchimateElementType.DELIVERABLE,
        ArchimateLayer.IMPLEMENTATION, "Upgraded order management system", position=(400, 750)
    )
    
    # Add all elements
    elements = [
        customer_satisfaction, digital_capability, customer_stakeholder, efficiency_goal,
        customer_actor, order_process, customer_service, order_object,
        crm_component, order_service, order_data,
        database_node, web_server, data_center,
        digital_transformation, new_system_deliverable
    ]
    
    for element in elements:
        viz.add_element(element)
    
    # Add comprehensive relationships
    relationships = [
        # Strategy to motivation
        ArchimateRelationship("rel1", "customer_satisfaction", "efficiency_goal", "realization", "Value drives goal"),
        ArchimateRelationship("rel2", "digital_capability", "efficiency_goal", "realization", "Capability supports goal"),
        
        # Motivation to business
        ArchimateRelationship("rel3", "customer_stakeholder", "customer_actor", "association", "Stakeholder represented by actor"),
        ArchimateRelationship("rel4", "efficiency_goal", "order_process", "realization", "Goal drives process improvement"),
        
        # Business relationships
        ArchimateRelationship("rel5", "customer_actor", "order_process", "triggering", "Customer initiates order"),
        ArchimateRelationship("rel6", "order_process", "customer_service", "realization", "Process realizes service"),
        ArchimateRelationship("rel7", "order_process", "order_object", "access", "Process creates order"),
        
        # Business to application
        ArchimateRelationship("rel8", "order_process", "order_service", "realization", "Service realizes process"),
        ArchimateRelationship("rel9", "customer_service", "crm_component", "realization", "Component supports service"),
        ArchimateRelationship("rel10", "order_object", "order_data", "realization", "Data represents business object"),
        
        # Application to technology
        ArchimateRelationship("rel11", "crm_component", "web_server", "assignment", "Component deployed on server"),
        ArchimateRelationship("rel12", "order_service", "database_node", "assignment", "Service uses database"),
        ArchimateRelationship("rel13", "order_data", "database_node", "assignment", "Data stored in database"),
        
        # Technology to physical
        ArchimateRelationship("rel14", "database_node", "data_center", "assignment", "Server located in facility"),
        ArchimateRelationship("rel15", "web_server", "data_center", "assignment", "Server hosted in facility"),
        
        # Implementation relationships
        ArchimateRelationship("rel16", "digital_transformation", "new_system_deliverable", "aggregation", "Project delivers system"),
        ArchimateRelationship("rel17", "new_system_deliverable", "order_service", "realization", "Deliverable implements service")
    ]
    
    for relationship in relationships:
        viz.add_relationship(relationship)
    
    return viz


class ArchimateVisualizationManager:
    """Manager class for ArchiMate visualizations in Streamlit"""
    
    def __init__(self):
        self.current_visualization: Optional[ArchimateVisualization] = None
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize Streamlit session state for visualization"""
        if 'archimate_visualizations' not in st.session_state:
            st.session_state.archimate_visualizations = {}
        if 'current_viz_id' not in st.session_state:
            st.session_state.current_viz_id = None
    
    def create_visualization(
        self, 
        viz_id: str, 
        engine: VisualizationEngine = VisualizationEngine.CYTOSCAPE
    ) -> ArchimateVisualization:
        """Create a new visualization"""
        viz = ArchimateVisualization(engine=engine)
        st.session_state.archimate_visualizations[viz_id] = viz.export_to_dict()
        st.session_state.current_viz_id = viz_id
        self.current_visualization = viz
        return viz
    
    def load_visualization(self, viz_id: str) -> Optional[ArchimateVisualization]:
        """Load an existing visualization"""
        if viz_id in st.session_state.archimate_visualizations:
            viz_data = st.session_state.archimate_visualizations[viz_id]
            viz = ArchimateVisualization()
            viz.import_from_dict(viz_data)
            st.session_state.current_viz_id = viz_id
            self.current_visualization = viz
            return viz
        return None
    
    def save_current_visualization(self) -> bool:
        """Save the current visualization to session state"""
        if self.current_visualization and st.session_state.current_viz_id:
            viz_id = st.session_state.current_viz_id
            st.session_state.archimate_visualizations[viz_id] = self.current_visualization.export_to_dict()
            return True
        return False
    
    def render_visualization_controls(self) -> None:
        """Render controls for visualization management"""
        st.markdown("### 🎛️ Visualization Controls")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Layout", help="Refresh the visualization layout"):
                if self.current_visualization:
                    st.rerun()
        
        with col2:
            engine = st.selectbox(
                "Visualization Engine",
                [VisualizationEngine.CYTOSCAPE, VisualizationEngine.D3JS],
                format_func=lambda x: "Cytoscape.js" if x == VisualizationEngine.CYTOSCAPE else "D3.js"
            )
            if self.current_visualization and self.current_visualization.engine != engine:
                self.current_visualization.engine = engine
                st.rerun()
        
        with col3:
            if st.button("💾 Save Visualization", help="Save current visualization state"):
                if self.save_current_visualization():
                    st.success("Visualization saved!")
                else:
                    st.error("Failed to save visualization")
        
        # Performance controls
        with st.expander("⚡ Performance Settings"):
            if self.current_visualization:
                # Performance level selection
                current_perf = self.current_visualization.performance_level
                perf_level = st.selectbox(
                    "Performance Level",
                    list(PerformanceLevel),
                    index=list(PerformanceLevel).index(current_perf),
                    format_func=lambda x: f"{x.value.title()} - {self._get_performance_description(x)}",
                    help="Higher levels optimize for larger architectures"
                )
                
                if perf_level != current_perf:
                    self.current_visualization.performance_level = perf_level
                    st.rerun()
                
                # Performance optimization toggle
                enable_opt = st.checkbox(
                    "Enable Performance Optimization",
                    value=self.current_visualization.enable_performance_optimization,
                    help="Enable advanced performance optimizations for large visualizations"
                )
                self.current_visualization.enable_performance_optimization = enable_opt
                
                # Performance recommendations
                if self.current_visualization.elements:
                    element_count = len(self.current_visualization.elements)
                    optimizer = get_performance_optimizer(perf_level)
                    recommendations = optimizer.get_performance_recommendations(element_count)
                    
                    if recommendations["recommendations"]:
                        st.markdown("**📊 Performance Recommendations:**")
                        for rec in recommendations["recommendations"]:
                            st.markdown(f"• {rec}")
                
                # Performance monitoring
                monitor = get_performance_monitor()
                if monitor.metrics_history:
                    with st.expander("📈 Performance Metrics"):
                        monitor.render_performance_dashboard()
        
        # Layer filtering
        with st.expander("🔍 Layer Filters"):
            if self.current_visualization:
                available_layers = list(set(elem.layer for elem in self.current_visualization.elements.values()))
                selected_layers = st.multiselect(
                    "Show Layers",
                    available_layers,
                    default=available_layers,
                    format_func=lambda x: x.value.title()
                )
                self.current_visualization.view_settings["layer_filter"] = selected_layers
    
    def _get_performance_description(self, level: PerformanceLevel) -> str:
        """Get description for performance level"""
        descriptions = {
            PerformanceLevel.LOW: "Full detail, < 100 elements",
            PerformanceLevel.MEDIUM: "Viewport culling, < 500 elements", 
            PerformanceLevel.HIGH: "Level-of-detail, < 1000 elements",
            PerformanceLevel.ULTRA: "Clustering, 1000+ elements"
        }
        return descriptions.get(level, "Unknown")
    
    def render_element_inspector(self) -> None:
        """Render element inspector panel"""
        if not self.current_visualization:
            return
        
        st.markdown("### 🔍 Element Inspector")
        
        elements = list(self.current_visualization.elements.values())
        if not elements:
            st.info("No elements in visualization")
            return
        
        element_names = [f"{elem.name} ({elem.layer.value})" for elem in elements]
        selected_idx = st.selectbox("Select Element", range(len(elements)), format_func=lambda x: element_names[x])
        
        if selected_idx is not None:
            element = elements[selected_idx]
            
            # Display element details
            st.markdown(f"**Name:** {element.name}")
            st.markdown(f"**Type:** {element.element_type.value}")
            st.markdown(f"**Layer:** {element.layer.value}")
            st.markdown(f"**Description:** {element.description}")
            
            if element.properties:
                st.markdown("**Properties:**")
                for key, value in element.properties.items():
                    st.markdown(f"- {key}: {value}")
            
            # Edit controls
            if st.button(f"🗑️ Remove {element.name}", key=f"remove_{element.element_id}"):
                self.current_visualization.remove_element(element.element_id)
                st.rerun()


# Global visualization manager instance
_viz_manager: Optional[ArchimateVisualizationManager] = None


def get_visualization_manager() -> ArchimateVisualizationManager:
    """Get global visualization manager instance"""
    global _viz_manager
    if _viz_manager is None:
        _viz_manager = ArchimateVisualizationManager()
    return _viz_manager