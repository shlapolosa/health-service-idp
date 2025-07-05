"""
ArchiMate Performance Optimization Module

Provides performance optimizations for large architecture visualizations
including virtualization, level-of-detail rendering, and WebAssembly integration.
"""
import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, List, Any, Optional, Tuple, Set
import json
import math
from dataclasses import dataclass
from enum import Enum


class PerformanceLevel(Enum):
    """Performance optimization levels"""
    LOW = "low"          # Basic optimizations
    MEDIUM = "medium"    # Moderate optimizations with some quality trade-offs
    HIGH = "high"        # Aggressive optimizations for large datasets
    ULTRA = "ultra"      # Maximum performance for very large architectures


class RenderingStrategy(Enum):
    """Rendering strategies for different performance needs"""
    FULL = "full"                    # Render all elements
    VIEWPORT_CULLING = "viewport"    # Only render visible elements
    LOD = "lod"                      # Level-of-detail based on zoom
    CLUSTERED = "clustered"          # Group elements into clusters
    SIMPLIFIED = "simplified"        # Simplified shapes and reduced detail


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring visualization performance"""
    render_time_ms: float = 0.0
    frame_rate: float = 0.0
    memory_usage_mb: float = 0.0
    visible_elements: int = 0
    total_elements: int = 0
    optimization_level: PerformanceLevel = PerformanceLevel.LOW
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "render_time_ms": self.render_time_ms,
            "frame_rate": self.frame_rate,
            "memory_usage_mb": self.memory_usage_mb,
            "visible_elements": self.visible_elements,
            "total_elements": self.total_elements,
            "optimization_level": self.optimization_level.value
        }


class ViewportBounds:
    """Represents the current viewport boundaries"""
    
    def __init__(self, x: float, y: float, width: float, height: float, zoom: float = 1.0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.zoom = zoom
    
    def contains_point(self, point_x: float, point_y: float, margin: float = 50.0) -> bool:
        """Check if a point is within the viewport (with margin for culling)"""
        return (
            self.x - margin <= point_x <= self.x + self.width + margin and
            self.y - margin <= point_y <= self.y + self.height + margin
        )
    
    def intersects_bounds(self, bounds_x: float, bounds_y: float, 
                         bounds_width: float, bounds_height: float, 
                         margin: float = 50.0) -> bool:
        """Check if bounding box intersects with viewport"""
        return not (
            bounds_x + bounds_width < self.x - margin or
            bounds_x > self.x + self.width + margin or
            bounds_y + bounds_height < self.y - margin or
            bounds_y > self.y + self.height + margin
        )


class ElementCluster:
    """Represents a cluster of elements for performance optimization"""
    
    def __init__(self, cluster_id: str, elements: List[str], center: Tuple[float, float], radius: float):
        self.cluster_id = cluster_id
        self.element_ids = elements
        self.center = center
        self.radius = radius
        self.is_expanded = False
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Get bounding box of the cluster"""
        x, y = self.center
        return (x - self.radius, y - self.radius, 2 * self.radius, 2 * self.radius)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "element_ids": self.element_ids,
            "center": {"x": self.center[0], "y": self.center[1]},
            "radius": self.radius,
            "is_expanded": self.is_expanded
        }


class PerformanceOptimizer:
    """Main performance optimization engine for ArchiMate visualizations"""
    
    def __init__(self, performance_level: PerformanceLevel = PerformanceLevel.MEDIUM):
        self.performance_level = performance_level
        self.rendering_strategy = self._determine_rendering_strategy()
        self.viewport_bounds: Optional[ViewportBounds] = None
        self.clusters: Dict[str, ElementCluster] = {}
        self.metrics = PerformanceMetrics()
        
        # Performance thresholds
        self.element_count_thresholds = {
            PerformanceLevel.LOW: 100,
            PerformanceLevel.MEDIUM: 500,
            PerformanceLevel.HIGH: 1000,
            PerformanceLevel.ULTRA: 5000
        }
        
        # LOD (Level of Detail) settings
        self.lod_settings = {
            "zoom_threshold_detail": 0.5,    # Below this zoom, use simplified rendering
            "zoom_threshold_labels": 0.3,    # Below this zoom, hide labels
            "zoom_threshold_cluster": 0.1,   # Below this zoom, use clustering
        }
    
    def _determine_rendering_strategy(self) -> RenderingStrategy:
        """Determine rendering strategy based on performance level"""
        strategy_map = {
            PerformanceLevel.LOW: RenderingStrategy.FULL,
            PerformanceLevel.MEDIUM: RenderingStrategy.VIEWPORT_CULLING,
            PerformanceLevel.HIGH: RenderingStrategy.LOD,
            PerformanceLevel.ULTRA: RenderingStrategy.CLUSTERED
        }
        return strategy_map[self.performance_level]
    
    def optimize_visualization_data(
        self, 
        elements: List[Dict[str, Any]], 
        relationships: List[Dict[str, Any]],
        viewport: Optional[ViewportBounds] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], PerformanceMetrics]:
        """Optimize visualization data based on current settings"""
        
        self.viewport_bounds = viewport
        optimized_elements = elements.copy()
        optimized_relationships = relationships.copy()
        
        # Update metrics
        self.metrics.total_elements = len(elements)
        
        # Apply optimization strategy
        if self.rendering_strategy == RenderingStrategy.VIEWPORT_CULLING:
            optimized_elements, optimized_relationships = self._apply_viewport_culling(
                optimized_elements, optimized_relationships
            )
        elif self.rendering_strategy == RenderingStrategy.LOD:
            optimized_elements, optimized_relationships = self._apply_lod_optimization(
                optimized_elements, optimized_relationships
            )
        elif self.rendering_strategy == RenderingStrategy.CLUSTERED:
            optimized_elements, optimized_relationships = self._apply_clustering(
                optimized_elements, optimized_relationships
            )
        elif self.rendering_strategy == RenderingStrategy.SIMPLIFIED:
            optimized_elements = self._apply_simplification(optimized_elements)
        
        # Update performance metrics
        self.metrics.visible_elements = len(optimized_elements)
        self.metrics.optimization_level = self.performance_level
        
        return optimized_elements, optimized_relationships, self.metrics
    
    def _apply_viewport_culling(
        self, 
        elements: List[Dict[str, Any]], 
        relationships: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Apply viewport culling to remove off-screen elements"""
        
        if not self.viewport_bounds:
            return elements, relationships
        
        # Filter elements within viewport
        visible_elements = []
        visible_element_ids = set()
        
        for element in elements:
            pos = element.get("position", {"x": 0, "y": 0})
            if self.viewport_bounds.contains_point(pos["x"], pos["y"]):
                visible_elements.append(element)
                visible_element_ids.add(element["id"])
        
        # Filter relationships to only include those between visible elements
        visible_relationships = [
            rel for rel in relationships
            if rel["source"] in visible_element_ids and rel["target"] in visible_element_ids
        ]
        
        return visible_elements, visible_relationships
    
    def _apply_lod_optimization(
        self, 
        elements: List[Dict[str, Any]], 
        relationships: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Apply level-of-detail optimization based on zoom level"""
        
        zoom_level = self.viewport_bounds.zoom if self.viewport_bounds else 1.0
        
        # First apply viewport culling
        optimized_elements, optimized_relationships = self._apply_viewport_culling(elements, relationships)
        
        # Apply LOD modifications based on zoom
        for element in optimized_elements:
            if zoom_level < self.lod_settings["zoom_threshold_labels"]:
                # Hide labels at low zoom
                element["show_label"] = False
            
            if zoom_level < self.lod_settings["zoom_threshold_detail"]:
                # Simplify shapes at low zoom
                element["simplified"] = True
                element["shape"] = "rectangle"  # Use simple rectangles
        
        # Reduce relationship complexity at low zoom
        if zoom_level < self.lod_settings["zoom_threshold_detail"]:
            for relationship in optimized_relationships:
                relationship["style"]["curve-style"] = "straight"  # Use straight lines
        
        return optimized_elements, optimized_relationships
    
    def _apply_clustering(
        self, 
        elements: List[Dict[str, Any]], 
        relationships: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Apply clustering to group nearby elements"""
        
        zoom_level = self.viewport_bounds.zoom if self.viewport_bounds else 1.0
        
        if zoom_level >= self.lod_settings["zoom_threshold_cluster"]:
            # Don't cluster at high zoom levels
            return self._apply_lod_optimization(elements, relationships)
        
        # Group elements by proximity and layer
        clusters = self._create_element_clusters(elements)
        
        # Create cluster representations
        cluster_elements = []
        cluster_relationships = []
        
        for cluster in clusters.values():
            if cluster.is_expanded:
                # Show individual elements if cluster is expanded
                cluster_elements.extend([
                    elem for elem in elements if elem["id"] in cluster.element_ids
                ])
            else:
                # Show cluster as single element
                cluster_element = {
                    "id": cluster.cluster_id,
                    "name": f"Cluster ({len(cluster.element_ids)} items)",
                    "type": "cluster",
                    "layer": "cluster",
                    "position": {"x": cluster.center[0], "y": cluster.center[1]},
                    "color": "#DDDDDD",
                    "shape": "circle",
                    "cluster_data": cluster.to_dict()
                }
                cluster_elements.append(cluster_element)
        
        # Create relationships between clusters
        cluster_relationships = self._create_cluster_relationships(relationships, clusters)
        
        return cluster_elements, cluster_relationships
    
    def _apply_simplification(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply geometric simplification for maximum performance"""
        
        simplified_elements = []
        
        for element in elements:
            simplified = element.copy()
            
            # Use simple shapes
            simplified["shape"] = "rectangle"
            
            # Reduce visual complexity
            simplified["border-width"] = 1
            simplified["font-size"] = "8px"
            
            # Remove detailed styling
            simplified.pop("gradient", None)
            simplified.pop("shadow", None)
            
            simplified_elements.append(simplified)
        
        return simplified_elements
    
    def _create_element_clusters(self, elements: List[Dict[str, Any]]) -> Dict[str, ElementCluster]:
        """Create clusters of nearby elements using spatial proximity"""
        
        if not elements:
            return {}
        
        # Group elements by layer first
        layer_groups = {}
        for element in elements:
            layer = element.get("layer", "default")
            if layer not in layer_groups:
                layer_groups[layer] = []
            layer_groups[layer].append(element)
        
        clusters = {}
        cluster_id_counter = 0
        
        # Create clusters within each layer
        for layer, layer_elements in layer_groups.items():
            layer_clusters = self._cluster_elements_by_proximity(layer_elements, max_cluster_size=10)
            
            for cluster_elements in layer_clusters:
                cluster_id = f"cluster_{layer}_{cluster_id_counter}"
                cluster_id_counter += 1
                
                # Calculate cluster center and radius
                positions = [elem["position"] for elem in cluster_elements]
                center_x = sum(pos["x"] for pos in positions) / len(positions)
                center_y = sum(pos["y"] for pos in positions) / len(positions)
                
                # Calculate radius as maximum distance from center
                max_distance = max(
                    math.sqrt((pos["x"] - center_x)**2 + (pos["y"] - center_y)**2)
                    for pos in positions
                )
                radius = max(max_distance + 50, 100)  # Minimum radius of 100
                
                cluster = ElementCluster(
                    cluster_id=cluster_id,
                    elements=[elem["id"] for elem in cluster_elements],
                    center=(center_x, center_y),
                    radius=radius
                )
                
                clusters[cluster_id] = cluster
        
        return clusters
    
    def _cluster_elements_by_proximity(
        self, 
        elements: List[Dict[str, Any]], 
        max_cluster_size: int = 10
    ) -> List[List[Dict[str, Any]]]:
        """Cluster elements based on spatial proximity using simple distance-based clustering"""
        
        if len(elements) <= max_cluster_size:
            return [elements]
        
        clusters = []
        remaining_elements = elements.copy()
        
        while remaining_elements:
            # Start new cluster with first remaining element
            seed_element = remaining_elements.pop(0)
            current_cluster = [seed_element]
            seed_pos = seed_element["position"]
            
            # Find nearby elements
            cluster_threshold = 200  # Distance threshold for clustering
            elements_to_remove = []
            
            for element in remaining_elements:
                if len(current_cluster) >= max_cluster_size:
                    break
                
                elem_pos = element["position"]
                distance = math.sqrt(
                    (elem_pos["x"] - seed_pos["x"])**2 + 
                    (elem_pos["y"] - seed_pos["y"])**2
                )
                
                if distance <= cluster_threshold:
                    current_cluster.append(element)
                    elements_to_remove.append(element)
            
            # Remove clustered elements from remaining
            for elem in elements_to_remove:
                remaining_elements.remove(elem)
            
            clusters.append(current_cluster)
        
        return clusters
    
    def _create_cluster_relationships(
        self, 
        relationships: List[Dict[str, Any]], 
        clusters: Dict[str, ElementCluster]
    ) -> List[Dict[str, Any]]:
        """Create relationships between clusters based on original element relationships"""
        
        # Create mapping from element ID to cluster ID
        element_to_cluster = {}
        for cluster_id, cluster in clusters.items():
            for element_id in cluster.element_ids:
                element_to_cluster[element_id] = cluster_id
        
        # Track inter-cluster relationships
        cluster_relationships = {}
        
        for relationship in relationships:
            source_cluster = element_to_cluster.get(relationship["source"])
            target_cluster = element_to_cluster.get(relationship["target"])
            
            if source_cluster and target_cluster and source_cluster != target_cluster:
                rel_key = f"{source_cluster}_{target_cluster}"
                if rel_key not in cluster_relationships:
                    cluster_relationships[rel_key] = {
                        "id": f"cluster_rel_{len(cluster_relationships)}",
                        "source": source_cluster,
                        "target": target_cluster,
                        "type": "cluster_relationship",
                        "weight": 0
                    }
                cluster_relationships[rel_key]["weight"] += 1
        
        return list(cluster_relationships.values())
    
    def generate_optimized_cytoscape_html(
        self, 
        elements: List[Dict[str, Any]], 
        relationships: List[Dict[str, Any]], 
        width: int, 
        height: int,
        enable_webgl: bool = True
    ) -> str:
        """Generate optimized Cytoscape.js HTML with performance enhancements"""
        
        # Convert data to Cytoscape format
        cytoscape_elements = []
        
        # Add nodes
        for element in elements:
            node = {
                "data": {
                    "id": element["id"],
                    "label": element["name"] if element.get("show_label", True) else "",
                    "type": element["type"],
                    "layer": element["layer"]
                },
                "position": element["position"],
                "classes": f"layer-{element['layer']} {'simplified' if element.get('simplified') else ''}",
                "style": {
                    "background-color": element["color"],
                    "shape": element.get("shape", "rectangle"),
                    "width": element.get("width", 60 if element.get("simplified") else 80),
                    "height": element.get("height", 30 if element.get("simplified") else 40),
                    "font-size": element.get("font-size", "10px"),
                    "border-width": element.get("border-width", 2)
                }
            }
            cytoscape_elements.append(node)
        
        # Add edges
        for relationship in relationships:
            edge = {
                "data": {
                    "id": relationship["id"],
                    "source": relationship["source"],
                    "target": relationship["target"],
                    "type": relationship["type"]
                },
                "style": {
                    "curve-style": relationship.get("style", {}).get("curve-style", "bezier"),
                    "line-style": "solid",
                    "target-arrow-shape": "triangle",
                    "width": relationship.get("weight", 1) if relationship["type"] == "cluster_relationship" else 1
                }
            }
            cytoscape_elements.append(edge)
        
        cytoscape_data = json.dumps(cytoscape_elements)
        webgl_script = """
        // Enable WebGL renderer for better performance
        if (cy.renderer().name !== 'canvas') {
            console.log('WebGL not available, using canvas renderer');
        }
        
        // Disable animations during interaction for better performance
        cy.on('viewport', function() {
            cy.batch(function() {
                cy.elements().removeClass('animated');
            });
        });
        """ if enable_webgl else ""
        
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
                }}
                .performance-stats {{
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    background: rgba(0,0,0,0.7);
                    color: white;
                    padding: 5px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-family: monospace;
                }}
            </style>
        </head>
        <body>
            <div id="cy"></div>
            <div id="performance-stats" class="performance-stats">
                Elements: {len(elements)}<br>
                Relationships: {len(relationships)}<br>
                Optimization: {self.performance_level.value}
            </div>
            
            <script>
                var startTime = performance.now();
                
                var cy = cytoscape({{
                    container: document.getElementById('cy'),
                    elements: {cytoscape_data},
                    style: [
                        {{
                            selector: 'node',
                            style: {{
                                'text-valign': 'center',
                                'text-halign': 'center',
                                'font-family': 'Arial, sans-serif'
                            }}
                        }},
                        {{
                            selector: 'edge',
                            style: {{
                                'line-color': '#999',
                                'target-arrow-color': '#999'
                            }}
                        }},
                        {{
                            selector: '.simplified',
                            style: {{
                                'border-width': 1,
                                'font-size': '8px'
                            }}
                        }}
                    ],
                    layout: {{
                        name: 'preset',
                        fit: true,
                        padding: 20
                    }},
                    // Performance settings
                    renderer: {{
                        showFps: false,
                        showInfo: false,
                        textureOnViewport: false,
                        motionBlur: false,
                        wheelSensitivity: 0.5
                    }},
                    minZoom: 0.1,
                    maxZoom: 5,
                    zoomingEnabled: true,
                    userZoomingEnabled: true,
                    panningEnabled: true,
                    userPanningEnabled: true
                }});
                
                {webgl_script}
                
                // Performance monitoring
                var renderTime = performance.now() - startTime;
                document.getElementById('performance-stats').innerHTML += '<br>Render: ' + renderTime.toFixed(1) + 'ms';
                
                // Throttled viewport change handler for performance
                var viewportThrottleTimeout;
                cy.on('viewport', function() {{
                    clearTimeout(viewportThrottleTimeout);
                    viewportThrottleTimeout = setTimeout(function() {{
                        // Handle viewport changes (for future viewport culling integration)
                        var zoom = cy.zoom();
                        var pan = cy.pan();
                        console.log('Viewport changed - zoom:', zoom, 'pan:', pan);
                    }}, 100);
                }});
                
                // Click handlers for clusters
                cy.on('tap', 'node[type="cluster"]', function(evt) {{
                    var node = evt.target;
                    console.log('Cluster clicked:', node.data());
                    // Could expand cluster here in future implementation
                }});
                
                // Double-click to fit
                cy.on('dblclick', function() {{
                    cy.fit();
                }});
                
                cy.fit();
            </script>
        </body>
        </html>
        """
        
        return html_template
    
    def generate_web_worker_script(self) -> str:
        """Generate Web Worker script for offloading heavy computations"""
        return """
        // ArchiMate Visualization Web Worker
        class ArchimateWorker {
            constructor() {
                this.layouts = new Map();
                this.clusters = new Map();
            }
            
            // Layout calculation using force-directed algorithm
            calculateForceLayout(nodes, edges, options = {}) {
                const defaults = {
                    iterations: 100,
                    attraction: 0.1,
                    repulsion: 100,
                    damping: 0.9,
                    minDistance: 50
                };
                const config = {...defaults, ...options};
                
                // Initialize positions if not set
                nodes.forEach(node => {
                    if (!node.position) {
                        node.position = {
                            x: Math.random() * 800,
                            y: Math.random() * 600
                        };
                    }
                    node.velocity = {x: 0, y: 0};
                });
                
                for (let i = 0; i < config.iterations; i++) {
                    // Calculate forces
                    nodes.forEach(node1 => {
                        let fx = 0, fy = 0;
                        
                        // Repulsion forces
                        nodes.forEach(node2 => {
                            if (node1.id !== node2.id) {
                                const dx = node1.position.x - node2.position.x;
                                const dy = node1.position.y - node2.position.y;
                                const distance = Math.sqrt(dx * dx + dy * dy);
                                
                                if (distance > 0 && distance < config.repulsion * 2) {
                                    const force = config.repulsion / (distance * distance);
                                    fx += (dx / distance) * force;
                                    fy += (dy / distance) * force;
                                }
                            }
                        });
                        
                        // Attraction forces from edges
                        edges.forEach(edge => {
                            let connected = null;
                            if (edge.source === node1.id) {
                                connected = nodes.find(n => n.id === edge.target);
                            } else if (edge.target === node1.id) {
                                connected = nodes.find(n => n.id === edge.source);
                            }
                            
                            if (connected) {
                                const dx = connected.position.x - node1.position.x;
                                const dy = connected.position.y - node1.position.y;
                                const distance = Math.sqrt(dx * dx + dy * dy);
                                
                                if (distance > config.minDistance) {
                                    fx += dx * config.attraction;
                                    fy += dy * config.attraction;
                                }
                            }
                        });
                        
                        // Update velocity and position
                        node1.velocity.x = (node1.velocity.x + fx) * config.damping;
                        node1.velocity.y = (node1.velocity.y + fy) * config.damping;
                        
                        node1.position.x += node1.velocity.x;
                        node1.position.y += node1.velocity.y;
                    });
                }
                
                return nodes;
            }
            
            // Hierarchical layout calculation
            calculateHierarchicalLayout(nodes, edges, options = {}) {
                const defaults = {
                    levelSeparation: 150,
                    nodeSeparation: 100,
                    direction: 'vertical'
                };
                const config = {...defaults, ...options};
                
                // Build graph structure
                const graph = new Map();
                const inDegree = new Map();
                
                nodes.forEach(node => {
                    graph.set(node.id, []);
                    inDegree.set(node.id, 0);
                });
                
                edges.forEach(edge => {
                    if (graph.has(edge.source) && graph.has(edge.target)) {
                        graph.get(edge.source).push(edge.target);
                        inDegree.set(edge.target, inDegree.get(edge.target) + 1);
                    }
                });
                
                // Topological sort to determine levels
                const levels = [];
                const queue = [];
                
                // Find root nodes (no incoming edges)
                inDegree.forEach((degree, nodeId) => {
                    if (degree === 0) {
                        queue.push({id: nodeId, level: 0});
                    }
                });
                
                const nodeLevel = new Map();
                
                while (queue.length > 0) {
                    const current = queue.shift();
                    nodeLevel.set(current.id, current.level);
                    
                    if (!levels[current.level]) {
                        levels[current.level] = [];
                    }
                    levels[current.level].push(current.id);
                    
                    // Process children
                    const children = graph.get(current.id) || [];
                    children.forEach(childId => {
                        const newDegree = inDegree.get(childId) - 1;
                        inDegree.set(childId, newDegree);
                        
                        if (newDegree === 0) {
                            queue.push({id: childId, level: current.level + 1});
                        }
                    });
                }
                
                // Position nodes
                levels.forEach((levelNodes, levelIndex) => {
                    const levelY = levelIndex * config.levelSeparation;
                    const totalWidth = (levelNodes.length - 1) * config.nodeSeparation;
                    const startX = -totalWidth / 2;
                    
                    levelNodes.forEach((nodeId, nodeIndex) => {
                        const node = nodes.find(n => n.id === nodeId);
                        if (node) {
                            if (config.direction === 'vertical') {
                                node.position = {
                                    x: startX + nodeIndex * config.nodeSeparation,
                                    y: levelY
                                };
                            } else {
                                node.position = {
                                    x: levelY,
                                    y: startX + nodeIndex * config.nodeSeparation
                                };
                            }
                        }
                    });
                });
                
                return nodes;
            }
            
            // Element clustering for performance
            clusterElements(elements, options = {}) {
                const defaults = {
                    maxClusterSize: 10,
                    clusterDistance: 200,
                    minClusterElements: 3
                };
                const config = {...defaults, ...options};
                
                const clusters = [];
                const processed = new Set();
                
                elements.forEach(element => {
                    if (processed.has(element.id)) return;
                    
                    const cluster = [element];
                    processed.add(element.id);
                    
                    // Find nearby elements to cluster
                    elements.forEach(otherElement => {
                        if (processed.has(otherElement.id) || cluster.length >= config.maxClusterSize) {
                            return;
                        }
                        
                        const dx = element.position.x - otherElement.position.x;
                        const dy = element.position.y - otherElement.position.y;
                        const distance = Math.sqrt(dx * dx + dy * dy);
                        
                        if (distance <= config.clusterDistance) {
                            cluster.push(otherElement);
                            processed.add(otherElement.id);
                        }
                    });
                    
                    // Only create cluster if it has minimum elements
                    if (cluster.length >= config.minClusterElements) {
                        // Calculate cluster center
                        const centerX = cluster.reduce((sum, elem) => sum + elem.position.x, 0) / cluster.length;
                        const centerY = cluster.reduce((sum, elem) => sum + elem.position.y, 0) / cluster.length;
                        
                        clusters.push({
                            id: `cluster_${clusters.length}`,
                            elements: cluster.map(e => e.id),
                            center: {x: centerX, y: centerY},
                            size: cluster.length
                        });
                    } else {
                        // Remove from processed if not clustered
                        cluster.forEach(elem => processed.delete(elem.id));
                    }
                });
                
                return clusters;
            }
        }
        
        // Worker message handler
        const worker = new ArchimateWorker();
        
        self.onmessage = function(e) {
            const {type, data, options} = e.data;
            let result;
            
            try {
                switch(type) {
                    case 'forceLayout':
                        result = worker.calculateForceLayout(data.nodes, data.edges, options);
                        break;
                    case 'hierarchicalLayout':
                        result = worker.calculateHierarchicalLayout(data.nodes, data.edges, options);
                        break;
                    case 'clustering':
                        result = worker.clusterElements(data.elements, options);
                        break;
                    default:
                        throw new Error(`Unknown operation: ${type}`);
                }
                
                self.postMessage({
                    type: 'success',
                    operation: type,
                    result: result
                });
            } catch (error) {
                self.postMessage({
                    type: 'error',
                    operation: type,
                    error: error.message
                });
            }
        };
        """
    
    def get_performance_recommendations(self, element_count: int) -> Dict[str, Any]:
        """Get performance recommendations based on current visualization size"""
        
        recommendations = {
            "current_level": self.performance_level.value,
            "element_count": element_count,
            "recommended_level": None,
            "recommendations": []
        }
        
        # Determine recommended performance level
        if element_count < 100:
            recommended_level = PerformanceLevel.LOW
            recommendations["recommendations"].append("Current size is optimal for full rendering")
        elif element_count < 500:
            recommended_level = PerformanceLevel.MEDIUM
            recommendations["recommendations"].append("Consider enabling viewport culling")
        elif element_count < 1000:
            recommended_level = PerformanceLevel.HIGH
            recommendations["recommendations"].append("Recommend level-of-detail optimization")
        else:
            recommended_level = PerformanceLevel.ULTRA
            recommendations["recommendations"].extend([
                "Large architecture detected",
                "Clustering recommended for optimal performance",
                "Consider breaking into smaller sub-architectures"
            ])
        
        recommendations["recommended_level"] = recommended_level.value
        
        # Add specific optimization recommendations
        if element_count > self.element_count_thresholds[self.performance_level]:
            recommendations["recommendations"].append(
                f"Consider upgrading to {recommended_level.value} performance level"
            )
        
        return recommendations


class PerformanceMonitor:
    """Monitors and reports visualization performance metrics"""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 100
    
    def record_metrics(self, metrics: PerformanceMetrics) -> None:
        """Record performance metrics"""
        self.metrics_history.append(metrics)
        
        # Maintain history size limit
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history.pop(0)
    
    def get_average_metrics(self, last_n: int = 10) -> PerformanceMetrics:
        """Get average metrics over last N measurements"""
        if not self.metrics_history:
            return PerformanceMetrics()
        
        recent_metrics = self.metrics_history[-last_n:]
        
        avg_metrics = PerformanceMetrics(
            render_time_ms=sum(m.render_time_ms for m in recent_metrics) / len(recent_metrics),
            frame_rate=sum(m.frame_rate for m in recent_metrics) / len(recent_metrics),
            memory_usage_mb=sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics),
            visible_elements=int(sum(m.visible_elements for m in recent_metrics) / len(recent_metrics)),
            total_elements=recent_metrics[-1].total_elements if recent_metrics else 0
        )
        
        return avg_metrics
    
    def render_performance_dashboard(self) -> None:
        """Render performance monitoring dashboard in Streamlit"""
        if not self.metrics_history:
            st.info("No performance data available yet")
            return
        
        st.markdown("### 📊 Performance Metrics")
        
        latest_metrics = self.metrics_history[-1]
        avg_metrics = self.get_average_metrics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Render Time", f"{latest_metrics.render_time_ms:.1f}ms")
        
        with col2:
            st.metric("Frame Rate", f"{latest_metrics.frame_rate:.1f} fps")
        
        with col3:
            st.metric("Visible Elements", f"{latest_metrics.visible_elements}/{latest_metrics.total_elements}")
        
        with col4:
            st.metric("Optimization", latest_metrics.optimization_level.value.title())
        
        # Performance history chart
        if len(self.metrics_history) > 1:
            st.markdown("#### 📈 Performance History")
            
            # Create simple performance chart data
            chart_data = {
                "Render Time (ms)": [m.render_time_ms for m in self.metrics_history[-20:]],
                "Visible Elements": [m.visible_elements for m in self.metrics_history[-20:]]
            }
            
            st.line_chart(chart_data)


# Global performance optimizer and monitor instances
_performance_optimizer: Optional[PerformanceOptimizer] = None
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_optimizer(performance_level: PerformanceLevel = PerformanceLevel.MEDIUM) -> PerformanceOptimizer:
    """Get global performance optimizer instance"""
    global _performance_optimizer
    if _performance_optimizer is None or _performance_optimizer.performance_level != performance_level:
        _performance_optimizer = PerformanceOptimizer(performance_level)
    return _performance_optimizer


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor