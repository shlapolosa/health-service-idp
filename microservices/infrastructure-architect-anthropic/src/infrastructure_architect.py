"""
Infrastructure Architect Agent for Microservice

Processes application requirements and designs infrastructure layer solutions including
infrastructure design, capacity planning, and deployment strategies.
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


class InfrastructureDesignEngine:
    """Designs infrastructure components and deployment strategies"""
    
    def __init__(self):
        self.cloud_providers = {
            "aws": {
                "compute": ["EC2", "ECS", "EKS", "Lambda", "Fargate"],
                "storage": ["S3", "EBS", "EFS", "FSx"],
                "database": ["RDS", "DynamoDB", "ElastiCache", "DocumentDB", "Neptune"],
                "networking": ["VPC", "ALB", "NLB", "CloudFront", "Route53"],
                "monitoring": ["CloudWatch", "X-Ray", "CloudTrail"],
                "security": ["IAM", "WAF", "Secrets Manager", "KMS", "Certificate Manager"]
            },
            "azure": {
                "compute": ["Virtual Machines", "AKS", "Container Instances", "Functions"],
                "storage": ["Blob Storage", "Disk Storage", "Files"],
                "database": ["SQL Database", "Cosmos DB", "Cache for Redis"],
                "networking": ["Virtual Network", "Load Balancer", "Application Gateway", "CDN"],
                "monitoring": ["Monitor", "Application Insights", "Log Analytics"],
                "security": ["Active Directory", "Key Vault", "Security Center"]
            },
            "gcp": {
                "compute": ["Compute Engine", "GKE", "Cloud Run", "Cloud Functions"],
                "storage": ["Cloud Storage", "Persistent Disk", "Filestore"],
                "database": ["Cloud SQL", "Firestore", "Cloud Bigtable", "Memorystore"],
                "networking": ["VPC", "Cloud Load Balancing", "Cloud CDN", "Cloud DNS"],
                "monitoring": ["Cloud Monitoring", "Cloud Logging", "Cloud Trace"],
                "security": ["Identity and Access Management", "Cloud KMS", "Security Command Center"]
            }
        }
        
        self.deployment_patterns = {
            "microservices": {
                "orchestration": ["Kubernetes", "Docker Swarm", "Nomad"],
                "service_mesh": ["Istio", "Linkerd", "Consul Connect"],
                "ingress": ["NGINX Ingress", "Traefik", "Ambassador", "Kong"],
                "monitoring": ["Prometheus", "Grafana", "Jaeger", "Zipkin"],
                "logging": ["ELK Stack", "Fluentd", "Loki"]
            },
            "serverless": {
                "functions": ["AWS Lambda", "Azure Functions", "Google Cloud Functions"],
                "orchestration": ["Step Functions", "Logic Apps", "Cloud Workflows"],
                "api_gateway": ["AWS API Gateway", "Azure API Management", "Cloud Endpoints"],
                "storage": ["S3", "Blob Storage", "Cloud Storage"],
                "monitoring": ["CloudWatch", "Application Insights", "Cloud Monitoring"]
            },
            "traditional": {
                "compute": ["Virtual Machines", "Bare Metal"],
                "load_balancing": ["HAProxy", "NGINX", "F5", "Citrix ADC"],
                "orchestration": ["Ansible", "Chef", "Puppet", "Terraform"],
                "monitoring": ["Nagios", "Zabbix", "New Relic", "DataDog"],
                "backup": ["Veeam", "Commvault", "Rubrik"]
            }
        }
    
    async def design_infrastructure(self, requirements: List[BusinessRequirement]) -> Dict[str, Any]:
        """Design infrastructure architecture from requirements"""
        
        # Analyze requirements to determine infrastructure needs
        infra_needs = self._analyze_infrastructure_needs(requirements)
        
        # Select cloud provider based on requirements
        cloud_provider = self._select_cloud_provider(infra_needs)
        
        # Choose deployment pattern
        deployment_pattern = self._select_deployment_pattern(infra_needs)
        
        # Design compute resources
        compute_design = self._design_compute_resources(infra_needs, cloud_provider, deployment_pattern)
        
        # Design storage resources
        storage_design = self._design_storage_resources(infra_needs, cloud_provider)
        
        # Design networking
        networking_design = self._design_networking(infra_needs, cloud_provider)
        
        # Design monitoring and logging
        monitoring_design = self._design_monitoring(infra_needs, cloud_provider, deployment_pattern)
        
        return {
            "infrastructure_needs": infra_needs,
            "cloud_provider": cloud_provider,
            "deployment_pattern": deployment_pattern,
            "compute": compute_design,
            "storage": storage_design,
            "networking": networking_design,
            "monitoring": monitoring_design,
            "estimated_cost": self._estimate_cost(compute_design, storage_design, networking_design)
        }
    
    def _analyze_infrastructure_needs(self, requirements: List[BusinessRequirement]) -> Dict[str, Any]:
        """Analyze requirements to determine infrastructure needs"""
        needs = {
            "scalability": "medium",
            "availability": "medium",
            "security": "medium",
            "performance": "medium",
            "cost_optimization": "medium",
            "compliance": [],
            "geographic_distribution": False,
            "data_volume": "medium"
        }
        
        for req in requirements:
            # Analyze for scalability needs
            if any(keyword in req.action.lower() for keyword in ["scale", "grow", "expand"]):
                needs["scalability"] = "high"
            
            # Analyze for availability needs
            if any(keyword in req.category.lower() for keyword in ["critical", "mission", "24/7", "uptime"]):
                needs["availability"] = "high"
            
            # Analyze for security needs
            if any(keyword in req.action.lower() for keyword in ["secure", "encrypt", "protect", "audit"]):
                needs["security"] = "high"
            
            # Analyze for performance needs
            if any(keyword in req.action.lower() for keyword in ["fast", "quick", "real-time", "performance"]):
                needs["performance"] = "high"
            
            # Analyze for compliance needs
            if any(keyword in req.category.lower() for keyword in ["compliance", "regulation", "gdpr", "hipaa", "sox"]):
                needs["compliance"].append(keyword.upper())
            
            # Analyze for geographic distribution
            if any(keyword in req.object.lower() for keyword in ["global", "worldwide", "multi-region"]):
                needs["geographic_distribution"] = True
            
            # Analyze data volume
            if any(keyword in req.object.lower() for keyword in ["big data", "large", "massive", "petabyte"]):
                needs["data_volume"] = "high"
        
        return needs
    
    def _select_cloud_provider(self, infra_needs: Dict[str, Any]) -> str:
        """Select appropriate cloud provider"""
        
        # Default selection logic (can be enhanced with more sophisticated scoring)
        if infra_needs.get("compliance") and "SOX" in infra_needs["compliance"]:
            return "aws"  # Strong compliance track record
        elif infra_needs.get("geographic_distribution"):
            return "azure"  # Strong global presence
        elif infra_needs.get("data_volume") == "high":
            return "gcp"  # Strong data analytics capabilities
        else:
            return "aws"  # Default choice for general use cases
    
    def _select_deployment_pattern(self, infra_needs: Dict[str, Any]) -> str:
        """Select deployment pattern based on needs"""
        
        if infra_needs.get("scalability") == "high":
            return "microservices"
        elif infra_needs.get("cost_optimization") == "high":
            return "serverless"
        else:
            return "traditional"
    
    def _design_compute_resources(self, infra_needs: Dict[str, Any], cloud_provider: str, deployment_pattern: str) -> Dict[str, Any]:
        """Design compute resources"""
        
        provider_services = self.cloud_providers[cloud_provider]
        pattern_services = self.deployment_patterns[deployment_pattern]
        
        compute_design = {
            "primary_service": provider_services["compute"][0],
            "orchestration": pattern_services.get("orchestration", [None])[0],
            "auto_scaling": infra_needs.get("scalability") == "high",
            "high_availability": infra_needs.get("availability") == "high"
        }
        
        # Add specific recommendations based on pattern
        if deployment_pattern == "microservices":
            compute_design.update({
                "container_platform": "Docker",
                "orchestrator": pattern_services["orchestration"][0],
                "service_mesh": pattern_services["service_mesh"][0] if infra_needs.get("security") == "high" else None
            })
        elif deployment_pattern == "serverless":
            compute_design.update({
                "function_service": pattern_services["functions"][0],
                "api_gateway": pattern_services["api_gateway"][0]
            })
        
        return compute_design
    
    def _design_storage_resources(self, infra_needs: Dict[str, Any], cloud_provider: str) -> Dict[str, Any]:
        """Design storage resources"""
        
        provider_services = self.cloud_providers[cloud_provider]
        
        storage_design = {
            "object_storage": provider_services["storage"][0],
            "database": provider_services["database"][0],
            "caching": provider_services["database"][2] if len(provider_services["database"]) > 2 else None,
            "backup_strategy": "automated" if infra_needs.get("availability") == "high" else "manual",
            "encryption": infra_needs.get("security") == "high"
        }
        
        # Add specific storage recommendations based on data volume
        if infra_needs.get("data_volume") == "high":
            storage_design.update({
                "data_warehouse": provider_services["database"][-1] if len(provider_services["database"]) > 3 else None,
                "archival_storage": "glacier_equivalent",
                "data_lifecycle_management": True
            })
        
        return storage_design
    
    def _design_networking(self, infra_needs: Dict[str, Any], cloud_provider: str) -> Dict[str, Any]:
        """Design networking infrastructure"""
        
        provider_services = self.cloud_providers[cloud_provider]
        
        networking_design = {
            "vpc": provider_services["networking"][0],
            "load_balancer": provider_services["networking"][1],
            "cdn": provider_services["networking"][3] if len(provider_services["networking"]) > 3 else None,
            "dns": provider_services["networking"][4] if len(provider_services["networking"]) > 4 else None,
            "ssl_termination": True,
            "ddos_protection": infra_needs.get("security") == "high"
        }
        
        # Add geographic distribution if needed
        if infra_needs.get("geographic_distribution"):
            networking_design.update({
                "multi_region": True,
                "global_load_balancing": True,
                "edge_locations": True
            })
        
        return networking_design
    
    def _design_monitoring(self, infra_needs: Dict[str, Any], cloud_provider: str, deployment_pattern: str) -> Dict[str, Any]:
        """Design monitoring and observability"""
        
        provider_services = self.cloud_providers[cloud_provider]
        pattern_services = self.deployment_patterns[deployment_pattern]
        
        monitoring_design = {
            "metrics": provider_services["monitoring"][0],
            "logging": provider_services["monitoring"][2] if len(provider_services["monitoring"]) > 2 else None,
            "alerting": True,
            "dashboards": True
        }
        
        # Add pattern-specific monitoring
        if deployment_pattern == "microservices":
            monitoring_design.update({
                "service_monitoring": pattern_services["monitoring"][0],
                "visualization": pattern_services["monitoring"][1],
                "distributed_tracing": pattern_services["monitoring"][2] if len(pattern_services["monitoring"]) > 2 else None
            })
        
        # Add enhanced monitoring for high availability needs
        if infra_needs.get("availability") == "high":
            monitoring_design.update({
                "uptime_monitoring": True,
                "synthetic_monitoring": True,
                "automated_recovery": True
            })
        
        return monitoring_design
    
    def _estimate_cost(self, compute_design: Dict[str, Any], storage_design: Dict[str, Any], networking_design: Dict[str, Any]) -> Dict[str, Any]:
        """Provide rough cost estimates"""
        
        # Simplified cost estimation (in practice, this would use actual pricing APIs)
        base_cost = 100  # Base monthly cost
        
        # Compute cost factors
        if compute_design.get("orchestration"):
            base_cost *= 1.5
        if compute_design.get("high_availability"):
            base_cost *= 2
        if compute_design.get("auto_scaling"):
            base_cost *= 1.3
        
        # Storage cost factors
        if storage_design.get("caching"):
            base_cost += 50
        if storage_design.get("encryption"):
            base_cost *= 1.1
        if storage_design.get("data_warehouse"):
            base_cost += 200
        
        # Networking cost factors
        if networking_design.get("cdn"):
            base_cost += 30
        if networking_design.get("multi_region"):
            base_cost *= 1.8
        if networking_design.get("ddos_protection"):
            base_cost += 100
        
        return {
            "estimated_monthly_cost_usd": round(base_cost, 2),
            "cost_factors": {
                "compute": "40%",
                "storage": "25%",
                "networking": "20%",
                "monitoring": "10%",
                "security": "5%"
            },
            "cost_optimization_recommendations": [
                "Use reserved instances for predictable workloads",
                "Implement auto-scaling to match demand",
                "Use spot instances for non-critical workloads",
                "Implement data lifecycle policies for storage"
            ]
        }


class CapacityPlanningEngine:
    """Plans infrastructure capacity based on expected load"""
    
    def __init__(self):
        self.load_patterns = {
            "steady": {"baseline": 100, "peak_multiplier": 1.2, "growth_rate": 0.1},
            "spiky": {"baseline": 50, "peak_multiplier": 5.0, "growth_rate": 0.2},
            "seasonal": {"baseline": 80, "peak_multiplier": 3.0, "growth_rate": 0.15},
            "viral": {"baseline": 20, "peak_multiplier": 50.0, "growth_rate": 1.0}
        }
    
    async def plan_capacity(self, requirements: List[BusinessRequirement]) -> Dict[str, Any]:
        """Plan infrastructure capacity"""
        
        # Analyze load patterns from requirements
        load_pattern = self._analyze_load_pattern(requirements)
        
        # Estimate resource requirements
        resource_requirements = self._estimate_resource_requirements(load_pattern, requirements)
        
        # Plan scaling strategy
        scaling_strategy = self._plan_scaling_strategy(load_pattern, resource_requirements)
        
        return {
            "load_pattern": load_pattern,
            "resource_requirements": resource_requirements,
            "scaling_strategy": scaling_strategy,
            "capacity_recommendations": self._generate_capacity_recommendations(load_pattern, scaling_strategy)
        }
    
    def _analyze_load_pattern(self, requirements: List[BusinessRequirement]) -> str:
        """Analyze expected load patterns from requirements"""
        
        # Look for keywords that indicate load patterns
        for req in requirements:
            if any(keyword in req.object.lower() for keyword in ["viral", "social", "trending"]):
                return "viral"
            elif any(keyword in req.object.lower() for keyword in ["seasonal", "holiday", "event"]):
                return "seasonal"
            elif any(keyword in req.action.lower() for keyword in ["burst", "spike", "peak"]):
                return "spiky"
        
        return "steady"  # Default pattern
    
    def _estimate_resource_requirements(self, load_pattern: str, requirements: List[BusinessRequirement]) -> Dict[str, Any]:
        """Estimate resource requirements"""
        
        pattern_info = self.load_patterns[load_pattern]
        
        # Base requirements (simplified)
        base_requirements = {
            "cpu_cores": 4,
            "memory_gb": 16,
            "storage_gb": 100,
            "network_bandwidth_mbps": 1000
        }
        
        # Adjust based on requirements complexity
        complexity_multiplier = len(requirements) * 0.1 + 1
        
        for key, value in base_requirements.items():
            base_requirements[key] = int(value * complexity_multiplier)
        
        # Add peak requirements
        peak_requirements = {}
        for key, value in base_requirements.items():
            peak_requirements[key] = int(value * pattern_info["peak_multiplier"])
        
        return {
            "baseline": base_requirements,
            "peak": peak_requirements,
            "growth_projection": {
                "monthly_growth_rate": pattern_info["growth_rate"],
                "yearly_projection": {
                    key: int(value * (1 + pattern_info["growth_rate"]) ** 12)
                    for key, value in base_requirements.items()
                }
            }
        }
    
    def _plan_scaling_strategy(self, load_pattern: str, resource_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Plan scaling strategy"""
        
        if load_pattern == "viral":
            return {
                "type": "aggressive_auto_scaling",
                "scale_out_trigger": "cpu > 50%",
                "scale_in_trigger": "cpu < 20%",
                "min_instances": 2,
                "max_instances": 100,
                "scale_out_cooldown": "1 minute",
                "scale_in_cooldown": "5 minutes"
            }
        elif load_pattern == "spiky":
            return {
                "type": "reactive_auto_scaling",
                "scale_out_trigger": "cpu > 70%",
                "scale_in_trigger": "cpu < 30%",
                "min_instances": 2,
                "max_instances": 20,
                "scale_out_cooldown": "2 minutes",
                "scale_in_cooldown": "10 minutes"
            }
        elif load_pattern == "seasonal":
            return {
                "type": "scheduled_scaling",
                "scale_out_trigger": "cpu > 80%",
                "scale_in_trigger": "cpu < 40%",
                "min_instances": 2,
                "max_instances": 15,
                "scheduled_events": [
                    {"name": "peak_season", "scale_to": 10, "schedule": "0 0 1 11 *"},
                    {"name": "off_season", "scale_to": 3, "schedule": "0 0 1 2 *"}
                ]
            }
        else:  # steady
            return {
                "type": "conservative_auto_scaling",
                "scale_out_trigger": "cpu > 80%",
                "scale_in_trigger": "cpu < 30%",
                "min_instances": 2,
                "max_instances": 10,
                "scale_out_cooldown": "5 minutes",
                "scale_in_cooldown": "15 minutes"
            }
    
    def _generate_capacity_recommendations(self, load_pattern: str, scaling_strategy: Dict[str, Any]) -> List[str]:
        """Generate capacity planning recommendations"""
        
        recommendations = [
            "Implement comprehensive monitoring and alerting",
            "Use auto-scaling to handle load variations",
            "Plan for 20% buffer capacity above expected peak",
            "Implement circuit breakers to prevent cascade failures"
        ]
        
        if load_pattern == "viral":
            recommendations.extend([
                "Use CDN to reduce origin server load",
                "Implement aggressive caching strategies",
                "Consider using serverless functions for burst capacity",
                "Plan for database read replicas"
            ])
        elif load_pattern == "spiky":
            recommendations.extend([
                "Implement queue-based processing for traffic spikes",
                "Use load balancers with health checks",
                "Consider using spot instances for additional capacity"
            ])
        elif load_pattern == "seasonal":
            recommendations.extend([
                "Pre-scale infrastructure before known peak periods",
                "Use reserved instances for baseline capacity",
                "Implement predictive scaling based on historical data"
            ])
        
        return recommendations


class InfrastructureArchitectAgent:
    """
    Infrastructure Architect Agent for Microservice
    
    Processes application requirements and designs infrastructure layer solutions including
    infrastructure design, capacity planning, and deployment strategies.
    """
    
    def __init__(self):
        self.agent_id = str(uuid.uuid4())
        self.name = "Infrastructure Architect"
        self.description = "Designs infrastructure architecture from application requirements"
        
        # Dependencies
        self.infra_design_engine = InfrastructureDesignEngine()
        self.capacity_planning_engine = CapacityPlanningEngine()
        
        logger.info(f"Infrastructure Architect Agent {self.agent_id} initialized")
    
    async def initialize(self):
        """Initialize agent and dependencies"""
        logger.info(f"Infrastructure Architect Agent {self.agent_id} fully initialized")
    
    async def cleanup(self):
        """Cleanup agent resources"""
        logger.info(f"Infrastructure Architect Agent {self.agent_id} cleanup completed")
    
    async def process_task(self, task: AgentTask) -> AgentResponse:
        """Process task specific to infrastructure architect"""
        try:
            task_type = task.task_type
            
            if task_type == "design_infrastructure":
                result = await self._design_infrastructure(task.payload)
            elif task_type == "plan_capacity":
                result = await self._plan_capacity(task.payload)
            elif task_type == "recommend_deployment":
                result = await self._recommend_deployment(task.payload)
            elif task_type == "estimate_costs":
                result = await self._estimate_costs(task.payload)
            elif task_type == "design_security":
                result = await self._design_security(task.payload)
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
    
    async def _design_infrastructure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Design infrastructure architecture from requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Design infrastructure using the infrastructure design engine
        infrastructure_design = await self.infra_design_engine.design_infrastructure(requirements)
        
        return infrastructure_design
    
    async def _plan_capacity(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Plan infrastructure capacity for requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Plan capacity using the capacity planning engine
        capacity_plan = await self.capacity_planning_engine.plan_capacity(requirements)
        
        return capacity_plan
    
    async def _recommend_deployment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend deployment strategy for requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Get infrastructure design to base deployment recommendations on
        infrastructure_design = await self.infra_design_engine.design_infrastructure(requirements)
        
        deployment_strategy = {
            "deployment_pattern": infrastructure_design["deployment_pattern"],
            "cloud_provider": infrastructure_design["cloud_provider"],
            "ci_cd_recommendations": self._get_cicd_recommendations(infrastructure_design),
            "deployment_environments": ["development", "staging", "production"],
            "rollout_strategy": self._get_rollout_strategy(infrastructure_design),
            "disaster_recovery": self._get_dr_strategy(infrastructure_design)
        }
        
        return deployment_strategy
    
    async def _estimate_costs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate infrastructure costs for requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Get infrastructure design for cost estimation
        infrastructure_design = await self.infra_design_engine.design_infrastructure(requirements)
        
        return {
            "cost_estimate": infrastructure_design["estimated_cost"],
            "cost_breakdown": infrastructure_design["estimated_cost"]["cost_factors"],
            "optimization_recommendations": infrastructure_design["estimated_cost"]["cost_optimization_recommendations"]
        }
    
    async def _design_security(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Design security architecture for requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Analyze security requirements
        security_needs = []
        for req in requirements:
            if "secure" in req.action.lower() or "security" in req.category.lower():
                security_needs.append(req.object)
        
        security_design = {
            "security_requirements": security_needs,
            "network_security": [
                "Web Application Firewall (WAF)",
                "DDoS protection",
                "SSL/TLS encryption",
                "VPC with private subnets"
            ],
            "identity_and_access": [
                "Multi-factor authentication",
                "Role-based access control (RBAC)",
                "API key management",
                "Service-to-service authentication"
            ],
            "data_protection": [
                "Encryption at rest",
                "Encryption in transit",
                "Key management service",
                "Regular security audits"
            ],
            "compliance_frameworks": self._identify_compliance_frameworks(requirements),
            "security_monitoring": [
                "Security information and event management (SIEM)",
                "Intrusion detection system (IDS)",
                "Vulnerability scanning",
                "Security incident response plan"
            ]
        }
        
        return security_design
    
    def _get_cicd_recommendations(self, infrastructure_design: Dict[str, Any]) -> List[str]:
        """Get CI/CD recommendations based on infrastructure"""
        
        recommendations = [
            "Implement infrastructure as code (IaC)",
            "Use container-based deployments",
            "Implement automated testing in pipeline",
            "Use blue-green or canary deployment strategies"
        ]
        
        cloud_provider = infrastructure_design.get("cloud_provider", "aws")
        
        if cloud_provider == "aws":
            recommendations.extend([
                "Use AWS CodePipeline for CI/CD",
                "Use AWS CodeBuild for build automation",
                "Use AWS CodeDeploy for deployment automation"
            ])
        elif cloud_provider == "azure":
            recommendations.extend([
                "Use Azure DevOps for CI/CD",
                "Use Azure Container Registry for container images",
                "Use Azure Resource Manager templates for IaC"
            ])
        elif cloud_provider == "gcp":
            recommendations.extend([
                "Use Cloud Build for CI/CD",
                "Use Google Container Registry for container images",
                "Use Cloud Deployment Manager for IaC"
            ])
        
        return recommendations
    
    def _get_rollout_strategy(self, infrastructure_design: Dict[str, Any]) -> Dict[str, str]:
        """Get deployment rollout strategy"""
        
        if infrastructure_design.get("deployment_pattern") == "microservices":
            return {
                "strategy": "canary_deployment",
                "rollout_percentage": "10% -> 50% -> 100%",
                "rollback_trigger": "error_rate > 1% or latency > 500ms",
                "monitoring_window": "15 minutes per stage"
            }
        elif infrastructure_design.get("deployment_pattern") == "serverless":
            return {
                "strategy": "blue_green_deployment",
                "switch_strategy": "traffic_shifting",
                "rollback_trigger": "error_rate > 0.5%",
                "monitoring_window": "5 minutes"
            }
        else:
            return {
                "strategy": "rolling_deployment",
                "batch_size": "25% of instances",
                "rollback_trigger": "health_check_failure",
                "monitoring_window": "10 minutes per batch"
            }
    
    def _get_dr_strategy(self, infrastructure_design: Dict[str, Any]) -> Dict[str, str]:
        """Get disaster recovery strategy"""
        
        return {
            "backup_strategy": "automated_daily_backups",
            "rto": "4 hours",  # Recovery Time Objective
            "rpo": "1 hour",   # Recovery Point Objective
            "multi_region": infrastructure_design.get("networking", {}).get("multi_region", False),
            "failover_strategy": "automatic" if infrastructure_design.get("networking", {}).get("multi_region") else "manual",
            "data_replication": "cross_region" if infrastructure_design.get("networking", {}).get("multi_region") else "local"
        }
    
    def _identify_compliance_frameworks(self, requirements: List[BusinessRequirement]) -> List[str]:
        """Identify relevant compliance frameworks"""
        
        frameworks = []
        
        for req in requirements:
            text = f"{req.action} {req.object} {req.category}".lower()
            
            if any(keyword in text for keyword in ["healthcare", "medical", "patient"]):
                frameworks.append("HIPAA")
            if any(keyword in text for keyword in ["financial", "payment", "banking"]):
                frameworks.append("PCI DSS")
            if any(keyword in text for keyword in ["gdpr", "privacy", "personal data"]):
                frameworks.append("GDPR")
            if any(keyword in text for keyword in ["sox", "sarbanes", "financial reporting"]):
                frameworks.append("SOX")
            if any(keyword in text for keyword in ["iso", "27001", "information security"]):
                frameworks.append("ISO 27001")
        
        return list(set(frameworks))