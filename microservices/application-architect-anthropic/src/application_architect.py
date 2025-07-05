"""
Application Architect Agent for Microservice

Processes business requirements and designs application layer solutions including
API design, technology stack selection, and component architecture.
"""

import asyncio
import logging
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

try:
    from .models import RequirementEntity, BusinessRequirement, AnalysisResult
except ImportError:
    from models import RequirementEntity, BusinessRequirement, AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    """Simple task representation"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Simple response representation"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class APIDesignEngine:
    """Designs REST APIs and data models from business requirements"""
    
    def __init__(self):
        self.api_patterns = {
            "crud": {
                "endpoints": ["GET /{resource}", "POST /{resource}", "PUT /{resource}/{id}", "DELETE /{resource}/{id}"],
                "methods": ["create", "read", "update", "delete"]
            },
            "workflow": {
                "endpoints": ["POST /{resource}/start", "PUT /{resource}/{id}/transition", "GET /{resource}/{id}/status"],
                "methods": ["start", "transition", "complete", "cancel"]
            },
            "integration": {
                "endpoints": ["POST /webhook/{service}", "GET /sync/{resource}", "POST /import", "GET /export"],
                "methods": ["sync", "import", "export", "notify"]
            }
        }
        
        self.data_types = {
            "string": {"validation": ["required", "maxLength", "pattern"], "example": "example text"},
            "integer": {"validation": ["required", "minimum", "maximum"], "example": 42},
            "boolean": {"validation": ["required"], "example": True},
            "datetime": {"validation": ["required", "format"], "example": "2024-01-01T12:00:00Z"},
            "array": {"validation": ["required", "minItems", "maxItems"], "example": ["item1", "item2"]},
            "object": {"validation": ["required", "properties"], "example": {"key": "value"}}
        }
    
    async def design_api(self, requirements: List[BusinessRequirement]) -> Dict[str, Any]:
        """Design API specification from requirements"""
        api_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Generated API", "version": "1.0.0"},
            "paths": {},
            "components": {"schemas": {}}
        }
        
        for req in requirements:
            # Determine API pattern
            pattern = self._identify_api_pattern(req)
            
            # Generate endpoints
            endpoints = self._generate_endpoints(req, pattern)
            api_spec["paths"].update(endpoints)
            
            # Generate data models
            schemas = self._generate_schemas(req)
            api_spec["components"]["schemas"].update(schemas)
        
        return api_spec
    
    def _identify_api_pattern(self, requirement: BusinessRequirement) -> str:
        """Identify the appropriate API pattern for requirement"""
        action = requirement.action.lower()
        
        if action in ["create", "read", "update", "delete", "manage"]:
            return "crud"
        elif action in ["approve", "review", "submit", "process", "start", "complete"]:
            return "workflow"
        elif action in ["sync", "import", "export", "integrate"]:
            return "integration"
        else:
            return "crud"  # Default pattern
    
    def _generate_endpoints(self, requirement: BusinessRequirement, pattern: str) -> Dict[str, Any]:
        """Generate API endpoints for requirement"""
        resource = requirement.object.lower().replace(" ", "_")
        endpoints = {}
        
        pattern_info = self.api_patterns[pattern]
        
        for endpoint_template in pattern_info["endpoints"]:
            endpoint = endpoint_template.format(resource=resource, id="{id}")
            method = endpoint.split()[0].lower()
            path = endpoint.split()[1]
            
            if path not in endpoints:
                endpoints[path] = {}
            
            endpoints[path][method] = {
                "summary": f"{method.upper()} {resource}",
                "description": f"Generated from requirement: {requirement.subject} {requirement.action} {requirement.object}",
                "responses": {
                    "200": {"description": "Success"},
                    "400": {"description": "Bad Request"},
                    "404": {"description": "Not Found"},
                    "500": {"description": "Internal Server Error"}
                }
            }
            
            # Add request body for POST/PUT
            if method in ["post", "put"]:
                endpoints[path][method]["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{resource.title()}"}
                        }
                    }
                }
        
        return endpoints
    
    def _generate_schemas(self, requirement: BusinessRequirement) -> Dict[str, Any]:
        """Generate data schemas for requirement"""
        resource = requirement.object.replace(" ", "_").title()
        
        # Extract properties from entities
        properties = {}
        for entity in requirement.entities:
            prop_name = entity.text.lower().replace(" ", "_")
            prop_type = self._infer_data_type(entity.text, entity.label)
            properties[prop_name] = {
                "type": prop_type,
                "description": f"Property extracted from: {entity.text}",
                **self.data_types.get(prop_type, {})
            }
        
        # Add common properties
        properties.update({
            "id": {"type": "string", "description": "Unique identifier"},
            "created_at": {"type": "string", "format": "date-time", "description": "Creation timestamp"},
            "updated_at": {"type": "string", "format": "date-time", "description": "Last update timestamp"}
        })
        
        return {
            resource: {
                "type": "object",
                "required": ["id"],
                "properties": properties,
                "description": f"Schema for {resource} generated from business requirement"
            }
        }
    
    def _infer_data_type(self, text: str, label: str) -> str:
        """Infer data type from entity text and label"""
        text_lower = text.lower()
        
        if label in ["DATE", "TIME"]:
            return "datetime"
        elif label in ["CARDINAL", "QUANTITY"]:
            return "integer"
        elif "email" in text_lower:
            return "string"
        elif "phone" in text_lower:
            return "string"
        elif "address" in text_lower:
            return "string"
        elif "status" in text_lower or "state" in text_lower:
            return "string"
        elif "list" in text_lower or "array" in text_lower:
            return "array"
        else:
            return "string"


class TechnologyStackSelector:
    """Selects appropriate technology stacks based on requirements"""
    
    def __init__(self):
        self.tech_stacks = {
            "web_application": {
                "frontend": ["React", "Vue.js", "Angular", "Svelte"],
                "backend": ["Node.js", "Python FastAPI", "Java Spring Boot", "Go Gin"],
                "database": ["PostgreSQL", "MongoDB", "MySQL"],
                "cache": ["Redis", "Memcached"],
                "deployment": ["Docker", "Kubernetes", "AWS ECS"]
            },
            "api_service": {
                "framework": ["FastAPI", "Express.js", "Spring Boot", "Flask", "Gin"],
                "database": ["PostgreSQL", "MongoDB", "DynamoDB"],
                "messaging": ["RabbitMQ", "Apache Kafka", "AWS SQS"],
                "monitoring": ["Prometheus", "Grafana", "DataDog"],
                "deployment": ["Docker", "Kubernetes", "Serverless"]
            },
            "data_processing": {
                "processing": ["Apache Spark", "Apache Flink", "Pandas", "Dask"],
                "storage": ["HDFS", "AWS S3", "Google Cloud Storage"],
                "database": ["BigQuery", "Snowflake", "ClickHouse"],
                "orchestration": ["Apache Airflow", "Prefect", "Dagster"],
                "deployment": ["Kubernetes", "AWS EMR", "Google Dataflow"]
            },
            "microservice": {
                "framework": ["FastAPI", "Spring Boot", "Go Gin", "Express.js"],
                "database": ["PostgreSQL", "MongoDB", "CockroachDB"],
                "service_mesh": ["Istio", "Linkerd", "Consul Connect"],
                "messaging": ["NATS", "Apache Kafka", "RabbitMQ"],
                "deployment": ["Kubernetes", "Docker Swarm", "Nomad"]
            }
        }
        
        self.selection_criteria = {
            "performance": {"Go", "Rust", "C++", "Java"},
            "scalability": {"Kubernetes", "AWS Lambda", "Go", "Node.js"},
            "security": {"Java Spring Security", "OAuth 2.0", "JWT", "HashiCorp Vault"},
            "real_time": {"WebSocket", "Server-Sent Events", "Apache Kafka", "Redis Streams"},
            "integration": {"REST APIs", "GraphQL", "Apache Kafka", "RabbitMQ"},
            "cost_efficiency": {"Python", "Go", "Serverless", "MongoDB"}
        }
    
    async def select_stack(self, requirements: List[BusinessRequirement]) -> Dict[str, Any]:
        """Select technology stack based on requirements"""
        
        # Analyze requirements to determine application type
        app_type = self._determine_application_type(requirements)
        
        # Get base technology stack
        base_stack = self.tech_stacks.get(app_type, self.tech_stacks["api_service"])
        
        # Apply requirement-specific optimizations
        optimized_stack = self._optimize_stack(base_stack, requirements)
        
        # Generate architecture recommendations
        architecture = self._design_architecture(optimized_stack, requirements)
        
        return {
            "application_type": app_type,
            "technology_stack": optimized_stack,
            "architecture": architecture,
            "deployment_strategy": self._recommend_deployment(requirements),
            "scalability_considerations": self._analyze_scalability_needs(requirements),
            "security_requirements": self._analyze_security_needs(requirements)
        }
    
    def _determine_application_type(self, requirements: List[BusinessRequirement]) -> str:
        """Determine the type of application from requirements"""
        actions = [req.action.lower() for req in requirements]
        objects = [req.object.lower() for req in requirements]
        
        # Check for data processing patterns
        if any(action in ["process", "analyze", "transform", "aggregate"] for action in actions):
            return "data_processing"
        
        # Check for user interface patterns
        if any(action in ["view", "display", "navigate", "interact"] for action in actions):
            return "web_application"
        
        # Check for microservice patterns
        if any("service" in obj or "component" in obj for obj in objects):
            return "microservice"
        
        # Default to API service
        return "api_service"
    
    def _optimize_stack(self, base_stack: Dict[str, List[str]], requirements: List[BusinessRequirement]) -> Dict[str, str]:
        """Optimize technology stack based on specific requirements"""
        optimized = {}
        
        # Analyze requirements for specific needs
        needs = set()
        for req in requirements:
            if "performance" in req.category.lower() or "fast" in req.action.lower():
                needs.add("performance")
            if "scale" in req.action.lower() or "many" in req.object.lower():
                needs.add("scalability")
            if "secure" in req.category.lower() or "auth" in req.action.lower():
                needs.add("security")
            if "real" in req.category.lower() or "live" in req.action.lower():
                needs.add("real_time")
            if "integrate" in req.action.lower() or "connect" in req.action.lower():
                needs.add("integration")
        
        # Select technologies based on needs
        for category, options in base_stack.items():
            best_option = options[0]  # Default to first option
            
            # Find best match for identified needs
            for need in needs:
                criteria_techs = self.selection_criteria.get(need, set())
                for option in options:
                    if any(tech.lower() in option.lower() for tech in criteria_techs):
                        best_option = option
                        break
                if best_option != options[0]:
                    break
            
            optimized[category] = best_option
        
        return optimized
    
    def _design_architecture(self, stack: Dict[str, str], requirements: List[BusinessRequirement]) -> Dict[str, Any]:
        """Design high-level architecture"""
        
        # Identify architectural patterns
        patterns = []
        for req in requirements:
            if "layer" in req.category.lower():
                patterns.append("layered")
            if "event" in req.action.lower():
                patterns.append("event_driven")
            if "service" in req.object.lower():
                patterns.append("microservices")
            if "pipe" in req.action.lower() or "flow" in req.action.lower():
                patterns.append("pipes_and_filters")
        
        if not patterns:
            patterns = ["layered"]  # Default pattern
        
        # Generate component structure
        components = self._generate_components(requirements)
        
        return {
            "patterns": list(set(patterns)),
            "components": components,
            "data_flow": self._design_data_flow(components),
            "integration_points": self._identify_integration_points(requirements)
        }
    
    def _generate_components(self, requirements: List[BusinessRequirement]) -> List[Dict[str, Any]]:
        """Generate architectural components from requirements"""
        components = []
        
        # Standard components
        components.extend([
            {"name": "API Gateway", "type": "gateway", "responsibility": "Request routing and authentication"},
            {"name": "Business Logic", "type": "service", "responsibility": "Core business rules and processing"},
            {"name": "Data Access", "type": "repository", "responsibility": "Data persistence and retrieval"}
        ])
        
        # Add requirement-specific components
        for req in requirements:
            if "auth" in req.action.lower():
                components.append({
                    "name": "Authentication Service",
                    "type": "service",
                    "responsibility": f"Handle {req.action} for {req.object}"
                })
            elif "notify" in req.action.lower():
                components.append({
                    "name": "Notification Service",
                    "type": "service",
                    "responsibility": f"Handle {req.action} for {req.object}"
                })
            elif "process" in req.action.lower():
                components.append({
                    "name": f"{req.object.title()} Processor",
                    "type": "processor",
                    "responsibility": f"Process {req.object} as requested"
                })
        
        return components
    
    def _design_data_flow(self, components: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Design data flow between components"""
        flows = []
        
        # Simple linear flow for now
        for i in range(len(components) - 1):
            flows.append({
                "from": components[i]["name"],
                "to": components[i + 1]["name"],
                "type": "synchronous",
                "protocol": "HTTP/REST"
            })
        
        return flows
    
    def _identify_integration_points(self, requirements: List[BusinessRequirement]) -> List[Dict[str, Any]]:
        """Identify external integration points"""
        integrations = []
        
        for req in requirements:
            if "integrate" in req.action.lower() or "external" in req.object.lower():
                integrations.append({
                    "name": f"{req.object.title()} Integration",
                    "type": "external_api",
                    "purpose": f"Integration for {req.action} {req.object}",
                    "protocol": "REST API"
                })
        
        return integrations
    
    def _recommend_deployment(self, requirements: List[BusinessRequirement]) -> Dict[str, Any]:
        """Recommend deployment strategy"""
        
        # Analyze scale and availability requirements
        high_availability = any("available" in req.category.lower() for req in requirements)
        high_scale = any("scale" in req.action.lower() for req in requirements)
        
        if high_availability or high_scale:
            return {
                "strategy": "kubernetes",
                "replicas": 3 if high_availability else 2,
                "auto_scaling": high_scale,
                "load_balancer": True,
                "health_checks": True
            }
        else:
            return {
                "strategy": "docker",
                "replicas": 1,
                "auto_scaling": False,
                "load_balancer": False,
                "health_checks": True
            }
    
    def _analyze_scalability_needs(self, requirements: List[BusinessRequirement]) -> Dict[str, Any]:
        """Analyze scalability requirements"""
        return {
            "horizontal_scaling": any("scale" in req.action.lower() for req in requirements),
            "caching_needed": any("fast" in req.action.lower() for req in requirements),
            "load_balancing": any("many" in req.object.lower() for req in requirements),
            "database_sharding": any("large" in req.object.lower() for req in requirements)
        }
    
    def _analyze_security_needs(self, requirements: List[BusinessRequirement]) -> List[str]:
        """Analyze security requirements"""
        security_needs = []
        
        for req in requirements:
            if "auth" in req.action.lower():
                security_needs.append("authentication")
            if "admin" in req.subject.lower():
                security_needs.append("authorization")
            if "secure" in req.category.lower():
                security_needs.append("encryption")
            if "audit" in req.action.lower():
                security_needs.append("audit_logging")
        
        return list(set(security_needs))


class ComponentArchitectureLibrary:
    """Library of architectural components and patterns"""
    
    def __init__(self):
        self.component_templates = {
            "api_gateway": {
                "responsibilities": ["routing", "authentication", "rate_limiting", "request_validation"],
                "technologies": ["Kong", "Ambassador", "AWS API Gateway", "Nginx"],
                "patterns": ["gateway_aggregation", "gateway_offloading"]
            },
            "authentication_service": {
                "responsibilities": ["user_authentication", "token_management", "session_handling"],
                "technologies": ["OAuth 2.0", "JWT", "SAML", "Auth0", "Keycloak"],
                "patterns": ["token_based_auth", "session_based_auth", "federated_identity"]
            },
            "data_access_layer": {
                "responsibilities": ["data_persistence", "query_optimization", "transaction_management"],
                "technologies": ["Repository Pattern", "Active Record", "Data Mapper", "ORM"],
                "patterns": ["repository", "unit_of_work", "data_mapper"]
            },
            "business_logic_service": {
                "responsibilities": ["business_rules", "domain_logic", "workflow_orchestration"],
                "technologies": ["Domain Services", "Use Cases", "Command Handlers"],
                "patterns": ["domain_driven_design", "clean_architecture", "hexagonal_architecture"]
            },
            "notification_service": {
                "responsibilities": ["message_delivery", "template_management", "delivery_tracking"],
                "technologies": ["SendGrid", "AWS SES", "Twilio", "Firebase", "WebSocket"],
                "patterns": ["observer", "publish_subscribe", "message_queue"]
            }
        }
        
        self.architectural_patterns = {
            "layered": {
                "description": "Organizes system into horizontal layers",
                "layers": ["presentation", "business", "persistence", "database"],
                "benefits": ["separation_of_concerns", "maintainability", "testability"],
                "drawbacks": ["performance_overhead", "tight_coupling_between_layers"]
            },
            "microservices": {
                "description": "Decomposes application into small, independent services",
                "components": ["service_registry", "api_gateway", "load_balancer", "monitoring"],
                "benefits": ["scalability", "technology_diversity", "fault_isolation"],
                "drawbacks": ["complexity", "network_latency", "data_consistency"]
            },
            "event_driven": {
                "description": "Components communicate through events",
                "components": ["event_producer", "event_consumer", "event_store", "message_broker"],
                "benefits": ["loose_coupling", "scalability", "responsiveness"],
                "drawbacks": ["eventual_consistency", "debugging_complexity"]
            },
            "hexagonal": {
                "description": "Isolates core logic from external concerns",
                "components": ["core_domain", "ports", "adapters", "external_systems"],
                "benefits": ["testability", "flexibility", "independence"],
                "drawbacks": ["initial_complexity", "abstraction_overhead"]
            }
        }
        
        self.integration_patterns = {
            "synchronous": {
                "protocols": ["HTTP/REST", "GraphQL", "gRPC", "SOAP"],
                "use_cases": ["real_time_requests", "immediate_responses", "simple_operations"],
                "considerations": ["timeout_handling", "circuit_breakers", "retry_logic"]
            },
            "asynchronous": {
                "protocols": ["Message Queues", "Event Streams", "Webhooks", "WebSockets"],
                "use_cases": ["batch_processing", "event_notifications", "long_running_operations"],
                "considerations": ["message_ordering", "duplicate_handling", "dead_letter_queues"]
            }
        }
    
    async def get_component_template(self, component_type: str) -> Dict[str, Any]:
        """Get template for specific component type"""
        return self.component_templates.get(component_type, {
            "responsibilities": [],
            "technologies": [],
            "patterns": []
        })
    
    async def get_architectural_pattern(self, pattern_name: str) -> Dict[str, Any]:
        """Get details for architectural pattern"""
        return self.architectural_patterns.get(pattern_name, {})
    
    async def recommend_integration_approach(self, requirements: List[BusinessRequirement]) -> Dict[str, Any]:
        """Recommend integration approach based on requirements"""
        
        # Analyze requirements for integration characteristics
        real_time_needed = any("immediate" in req.action.lower() or "real" in req.category.lower() for req in requirements)
        high_volume = any("many" in req.object.lower() or "bulk" in req.action.lower() for req in requirements)
        
        if real_time_needed and not high_volume:
            return {
                "approach": "synchronous",
                "recommended_protocols": ["HTTP/REST", "GraphQL"],
                "patterns": ["request_response", "circuit_breaker"]
            }
        elif high_volume or any("process" in req.action.lower() for req in requirements):
            return {
                "approach": "asynchronous", 
                "recommended_protocols": ["Message Queues", "Event Streams"],
                "patterns": ["publish_subscribe", "message_queue"]
            }
        else:
            return {
                "approach": "hybrid",
                "recommended_protocols": ["HTTP/REST", "Message Queues"],
                "patterns": ["request_response", "event_driven"]
            }


class ApplicationArchitectAgent:
    """
    Application Architect Agent for Microservice
    
    Processes business requirements and designs application layer solutions including
    API design, technology stack selection, and component architecture.
    """
    
    def __init__(self):
        self.agent_id = str(uuid.uuid4())
        self.name = "Application Architect"
        self.description = "Designs application architecture from business requirements"
        
        # Dependencies
        self.api_design_engine = APIDesignEngine()
        self.tech_stack_selector = TechnologyStackSelector()
        self.component_library = ComponentArchitectureLibrary()
        
        logger.info(f"Application Architect Agent {self.agent_id} initialized")
    
    async def initialize(self):
        """Initialize agent and dependencies"""
        logger.info(f"Application Architect Agent {self.agent_id} fully initialized")
    
    async def cleanup(self):
        """Cleanup agent resources"""
        logger.info(f"Application Architect Agent {self.agent_id} cleanup completed")
    
    async def process_task(self, task: AgentTask) -> AgentResponse:
        """Process task specific to application architect"""
        try:
            task_type = task.task_type
            
            if task_type == "design_api":
                result = await self._design_api(task.payload)
            elif task_type == "select_technology_stack":
                result = await self._select_technology_stack(task.payload)
            elif task_type == "design_architecture":
                result = await self._design_architecture(task.payload)
            elif task_type == "recommend_components":
                result = await self._recommend_components(task.payload)
            elif task_type == "design_integration":
                result = await self._design_integration(task.payload)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            return AgentResponse(
                success=True,
                result=result,
                metadata={"task_id": task.task_id, "processing_time": 0.1}
            )
        
        except Exception as e:
            logger.error(f"Error processing task {task.task_id}: {e}")
            return AgentResponse(
                success=False,
                error=str(e),
                metadata={"task_id": task.task_id}
            )
    
    async def _design_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Design API specification from business requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Design API using the API design engine
        api_spec = await self.api_design_engine.design_api(requirements)
        
        return {
            "api_specification": api_spec,
            "endpoint_count": len(api_spec.get("paths", {})),
            "schema_count": len(api_spec.get("components", {}).get("schemas", {})),
            "requirements_processed": len(requirements)
        }
    
    async def _select_technology_stack(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate technology stack for requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Select technology stack
        stack_recommendation = await self.tech_stack_selector.select_stack(requirements)
        
        return stack_recommendation
    
    async def _design_architecture(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Design high-level architecture for requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Design architecture using tech stack selector's architecture method
        stack_recommendation = await self.tech_stack_selector.select_stack(requirements)
        architecture = stack_recommendation.get("architecture", {})
        
        return {
            "architecture": architecture,
            "patterns": architecture.get("patterns", []),
            "components": architecture.get("components", []),
            "integration_points": architecture.get("integration_points", [])
        }
    
    async def _recommend_components(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend architectural components for requirements"""
        requirements_data = payload.get("requirements", [])
        component_type = payload.get("component_type", "api_gateway")
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Get component template
        component_template = await self.component_library.get_component_template(component_type)
        
        # Analyze requirements for component recommendations
        recommendations = []
        for req_data in requirements_data:
            requirement = BusinessRequirement(**req_data)
            
            # Determine recommended components based on requirement
            if "auth" in requirement.action.lower():
                recommendations.append("authentication_service")
            elif "notify" in requirement.action.lower():
                recommendations.append("notification_service")
            elif "data" in requirement.object.lower():
                recommendations.append("data_access_layer")
            else:
                recommendations.append("business_logic_service")
        
        return {
            "component_template": component_template,
            "recommended_components": list(set(recommendations)),
            "requirements_analyzed": len(requirements_data)
        }
    
    async def _design_integration(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Design integration approach for requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Get integration recommendations
        integration_approach = await self.component_library.recommend_integration_approach(requirements)
        
        return {
            "integration_approach": integration_approach,
            "recommended_protocols": integration_approach.get("recommended_protocols", []),
            "patterns": integration_approach.get("patterns", []),
            "requirements_analyzed": len(requirements)
        }