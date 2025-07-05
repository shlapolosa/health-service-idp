"""
Business Architect Agent for Microservice

Simplified business architect agent adapted for microservice deployment.
Handles ArchiMate business layer management and capability mapping.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

try:
    from .models import ArchiMateElement, BusinessCapability, ArchitectureChange
except ImportError:
    from models import ArchiMateElement, BusinessCapability, ArchitectureChange

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


class BusinessArchitectureProcessor:
    """Business architecture processing engine"""
    
    def __init__(self):
        self.industry_capabilities = self._initialize_industry_capabilities()
        self.archimate_patterns = self._initialize_archimate_patterns()
        self.reference_architectures = self._initialize_reference_architectures()
    
    def _initialize_industry_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Initialize industry-standard business capability models"""
        return {
            "financial_services": {
                "l1_capabilities": [
                    "Customer Management", "Product Management", "Risk Management",
                    "Compliance & Regulatory", "Operations", "Technology & Data"
                ],
                "patterns": {
                    "customer_onboarding": {
                        "processes": ["Identity Verification", "Account Opening", "Document Collection"],
                        "actors": ["Customer", "Relationship Manager", "Compliance Officer"],
                        "systems": ["CRM", "KYC System", "Document Management"]
                    }
                }
            },
            "healthcare": {
                "l1_capabilities": [
                    "Patient Care", "Clinical Operations", "Revenue Cycle",
                    "Quality & Safety", "Regulatory Compliance", "Research & Development"
                ],
                "patterns": {
                    "patient_care": {
                        "processes": ["Registration", "Diagnosis", "Treatment", "Discharge"],
                        "actors": ["Patient", "Physician", "Nurse", "Administrator"],
                        "systems": ["EMR", "PACS", "Laboratory System", "Pharmacy System"]
                    }
                }
            },
            "general": {
                "l1_capabilities": [
                    "Customer Management", "Product & Service Management", "Operations Management",
                    "Financial Management", "Human Resources", "Technology Management"
                ],
                "patterns": {}
            }
        }
    
    def _initialize_archimate_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize ArchiMate modeling patterns"""
        return {
            "business_process_pattern": {
                "elements": [
                    {"type": "business_actor", "role": "process_owner"},
                    {"type": "business_process", "role": "main_process"},
                    {"type": "business_service", "role": "service_outcome"},
                    {"type": "business_object", "role": "process_input_output"}
                ],
                "relationships": [
                    {"type": "assignment", "from": "business_actor", "to": "business_process"},
                    {"type": "realization", "from": "business_process", "to": "business_service"},
                    {"type": "access", "from": "business_process", "to": "business_object"}
                ]
            },
            "capability_pattern": {
                "elements": [
                    {"type": "business_function", "role": "capability"},
                    {"type": "business_process", "role": "process_realization"},
                    {"type": "business_role", "role": "capability_owner"},
                    {"type": "business_service", "role": "service_delivery"}
                ],
                "relationships": [
                    {"type": "realization", "from": "business_process", "to": "business_function"},
                    {"type": "assignment", "from": "business_role", "to": "business_function"},
                    {"type": "serving", "from": "business_function", "to": "business_service"}
                ]
            }
        }
    
    def _initialize_reference_architectures(self) -> Dict[str, Dict[str, Any]]:
        """Initialize reference architecture patterns"""
        return {
            "digital_transformation": {
                "description": "Enterprise digital transformation reference architecture",
                "layers": {
                    "strategy": ["Digital Strategy", "Innovation Goals", "Market Positioning"],
                    "business": ["Customer Journey", "Digital Processes", "Business Capabilities"],
                    "application": ["Digital Platforms", "Integration Services", "Analytics"],
                    "technology": ["Cloud Infrastructure", "Data Architecture", "Security"]
                }
            },
            "customer_experience": {
                "description": "Customer-centric business architecture",
                "capabilities": [
                    "Customer Identity Management", "Journey Orchestration",
                    "Personalization", "Feedback Management", "Service Delivery"
                ]
            }
        }
    
    async def analyze_business_impact(self, requirements: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze business impact of requirements"""
        impact_analysis = []
        
        for req in requirements:
            impact = {
                "requirement_id": req.get("id", str(uuid.uuid4())),
                "requirement_summary": f"{req.get('subject', '')} {req.get('action', '')} {req.get('object', '')}",
                "impact_level": self._assess_impact_level(req),
                "affected_capabilities": self._identify_affected_capabilities(req),
                "stakeholder_impact": self._assess_stakeholder_impact(req),
                "timeline_estimate": self._estimate_timeline(req),
                "effort_estimate": self._estimate_effort(req)
            }
            impact_analysis.append(impact)
        
        return {
            "impact_analysis": impact_analysis,
            "overall_impact": self._calculate_overall_impact(impact_analysis),
            "recommendations": self._generate_recommendations(impact_analysis)
        }
    
    async def generate_capability_map(self, industry: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate business capability map"""
        industry_model = self.industry_capabilities.get(industry, self.industry_capabilities["general"])
        
        capabilities = []
        for i, cap_name in enumerate(industry_model["l1_capabilities"]):
            capability = BusinessCapability(
                id=f"cap_{i+1:03d}",
                name=cap_name,
                description=f"Level 1 capability: {cap_name}",
                level=1,
                maturity_level="developing",
                business_value="medium"
            )
            capabilities.append(capability.dict())
        
        return {
            "capability_map": {
                "l1_capabilities": capabilities,
                "industry": industry,
                "total_capabilities": len(capabilities)
            },
            "maturity_assessment": self._assess_capability_maturity(capabilities),
            "recommendations": self._generate_capability_recommendations(capabilities)
        }
    
    async def design_business_architecture(self, requirements: List[Dict[str, Any]], capabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Design business architecture"""
        elements = self._generate_business_elements(requirements, capabilities)
        relationships = self._generate_relationships(elements)
        
        return {
            "business_architecture": {
                "elements": [elem.dict() for elem in elements],
                "relationships": relationships,
                "patterns_applied": ["business_process_pattern", "capability_pattern"]
            },
            "archimate_model": self._generate_archimate_html(elements, relationships),
            "validation_results": self._validate_architecture(elements, relationships)
        }
    
    async def generate_archimate_model(self, elements: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate ArchiMate model visualization"""
        archimate_elements = []
        for elem_data in elements:
            element = ArchiMateElement(
                id=elem_data.get("id", ""),
                name=elem_data.get("name", ""),
                type=elem_data.get("type", "business_actor"),
                layer=elem_data.get("layer", "business"),
                description=elem_data.get("description", ""),
                color=elem_data.get("color", "#FFFF99")
            )
            archimate_elements.append(element)
        
        html_model = self._generate_archimate_html(archimate_elements, relationships)
        
        return {
            "archimate_model": {
                "html": html_model,
                "elements": [elem.dict() for elem in archimate_elements],
                "relationships": relationships
            },
            "model_statistics": {
                "total_elements": len(archimate_elements),
                "total_relationships": len(relationships)
            }
        }
    
    def _assess_impact_level(self, requirement: Dict[str, Any]) -> str:
        """Assess impact level of a requirement"""
        stakeholders = requirement.get("stakeholders", [])
        action = requirement.get("action", "").lower()
        
        if len(stakeholders) > 5 or "integration" in action or "transform" in action:
            return "high"
        elif len(stakeholders) > 2 or "update" in action or "modify" in action:
            return "medium"
        else:
            return "low"
    
    def _identify_affected_capabilities(self, requirement: Dict[str, Any]) -> List[str]:
        """Identify capabilities affected by requirement"""
        # Simple mapping based on keywords
        action = requirement.get("action", "").lower()
        obj = requirement.get("object", "").lower()
        
        capabilities = []
        if "customer" in obj or "user" in obj:
            capabilities.append("Customer Management")
        if "product" in obj or "service" in obj:
            capabilities.append("Product & Service Management")
        if "process" in obj or "workflow" in obj:
            capabilities.append("Operations Management")
        
        return capabilities or ["General Operations"]
    
    def _assess_stakeholder_impact(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Assess stakeholder impact"""
        stakeholders = requirement.get("stakeholders", [])
        return {
            "total_stakeholders": len(stakeholders),
            "impact_categories": {
                "high_impact": [s for s in stakeholders if "manager" in s.lower() or "admin" in s.lower()],
                "medium_impact": [s for s in stakeholders if "user" in s.lower()],
                "low_impact": []
            }
        }
    
    def _estimate_timeline(self, requirement: Dict[str, Any]) -> str:
        """Estimate implementation timeline"""
        impact_level = self._assess_impact_level(requirement)
        if impact_level == "high":
            return "12-24 weeks"
        elif impact_level == "medium":
            return "6-12 weeks"
        else:
            return "2-6 weeks"
    
    def _estimate_effort(self, requirement: Dict[str, Any]) -> str:
        """Estimate implementation effort"""
        impact_level = self._assess_impact_level(requirement)
        if impact_level == "high":
            return "Large (>100 person-days)"
        elif impact_level == "medium":
            return "Medium (20-100 person-days)"
        else:
            return "Small (<20 person-days)"
    
    def _calculate_overall_impact(self, impact_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall impact"""
        if not impact_analysis:
            return {"level": "low", "confidence": 1.0}
        
        impact_counts = {"high": 0, "medium": 0, "low": 0}
        for analysis in impact_analysis:
            impact_level = analysis.get("impact_level", "medium")
            impact_counts[impact_level] += 1
        
        total = len(impact_analysis)
        if impact_counts["high"] > 0:
            overall = "high"
        elif impact_counts["medium"] > total * 0.5:
            overall = "medium"
        else:
            overall = "low"
        
        return {
            "level": overall,
            "distribution": impact_counts,
            "confidence": 0.8
        }
    
    def _generate_recommendations(self, impact_analysis: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on impact analysis"""
        recommendations = []
        
        high_impact_count = sum(1 for a in impact_analysis if a.get("impact_level") == "high")
        if high_impact_count > 0:
            recommendations.append("Consider phased implementation approach for high-impact changes")
            recommendations.append("Establish strong change management and communication plan")
        
        total_stakeholders = sum(len(a.get("stakeholder_impact", {}).get("impact_categories", {}).get("high_impact", [])) 
                                for a in impact_analysis)
        if total_stakeholders > 10:
            recommendations.append("Implement comprehensive stakeholder engagement strategy")
        
        recommendations.append("Conduct detailed business impact assessment before implementation")
        recommendations.append("Establish success metrics and monitoring framework")
        
        return recommendations
    
    def _assess_capability_maturity(self, capabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess capability maturity"""
        maturity_levels = {"initial": 0, "developing": 0, "defined": 0, "managed": 0, "optimizing": 0}
        
        for cap in capabilities:
            level = cap.get("maturity_level", "developing")
            maturity_levels[level] += 1
        
        return {
            "maturity_distribution": maturity_levels,
            "average_maturity": "developing",  # Simplified
            "improvement_areas": ["Process standardization", "Performance measurement", "Continuous improvement"]
        }
    
    def _generate_capability_recommendations(self, capabilities: List[Dict[str, Any]]) -> List[str]:
        """Generate capability recommendations"""
        return [
            "Focus on developing core customer-facing capabilities first",
            "Establish capability ownership and governance",
            "Implement capability performance measurement",
            "Create capability roadmap aligned with business strategy",
            "Invest in technology enablers for key capabilities"
        ]
    
    def _generate_business_elements(self, requirements: List[Dict[str, Any]], capabilities: List[Dict[str, Any]]) -> List[ArchiMateElement]:
        """Generate business elements from requirements and capabilities"""
        elements = []
        element_id = 1
        
        # Generate actors from requirements
        actors = set()
        for req in requirements:
            subject = req.get("subject", "")
            stakeholders = req.get("stakeholders", [])
            if subject:
                actors.add(subject)
            actors.update(stakeholders)
        
        for actor_name in actors:
            if actor_name:
                element = ArchiMateElement(
                    id=f"actor_{element_id:03d}",
                    name=actor_name,
                    type="business_actor",
                    layer="business",
                    description=f"Business actor: {actor_name}",
                    color="#FFFF99"
                )
                elements.append(element)
                element_id += 1
        
        # Generate functions from capabilities
        for cap in capabilities:
            element = ArchiMateElement(
                id=f"func_{element_id:03d}",
                name=cap.get("name", "Unknown Function"),
                type="business_function",
                layer="business",
                description=cap.get("description", ""),
                color="#FFFF99"
            )
            elements.append(element)
            element_id += 1
        
        return elements
    
    def _generate_relationships(self, elements: List[ArchiMateElement]) -> List[Dict[str, Any]]:
        """Generate relationships between elements"""
        relationships = []
        actors = [e for e in elements if e.type == "business_actor"]
        functions = [e for e in elements if e.type == "business_function"]
        
        # Create assignment relationships (actor -> function)
        for i, actor in enumerate(actors):
            if i < len(functions):
                rel = {
                    "id": f"rel_{i+1:03d}",
                    "type": "assignment",
                    "source_id": actor.id,
                    "target_id": functions[i].id,
                    "description": f"{actor.name} assigned to {functions[i].name}"
                }
                relationships.append(rel)
        
        return relationships
    
    def _generate_archimate_html(self, elements: List[ArchiMateElement], relationships: List[Dict[str, Any]]) -> str:
        """Generate HTML representation of ArchiMate model"""
        elements_html = ""
        for i, element in enumerate(elements):
            x = (i % 4) * 200 + 50
            y = (i // 4) * 100 + 50
            
            elements_html += f"""
                <div class="archimate-element {element.type.replace('_', '-')}" 
                     style="left: {x}px; top: {y}px; background-color: {element.color};"
                     title="{element.description}">
                    {element.name}
                </div>
            """
        
        return f"""
        <div class="archimate-container" style="width: 100%; height: 600px; position: relative; border: 1px solid #ccc; background: #f9f9f9;">
            <style>
                .archimate-element {{
                    position: absolute;
                    border: 2px solid #333;
                    padding: 8px;
                    text-align: center;
                    font-family: Arial, sans-serif;
                    font-size: 12px;
                    border-radius: 4px;
                    box-shadow: 2px 2px 4px rgba(0,0,0,0.2);
                    cursor: pointer;
                }}
                .business-actor {{ border-radius: 50%; }}
                .business-function {{ border-radius: 8px; }}
                .business-object {{ border-radius: 0px; }}
            </style>
            {elements_html}
        </div>
        """
    
    def _validate_architecture(self, elements: List[ArchiMateElement], relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate architecture design"""
        issues = []
        
        if len(elements) == 0:
            issues.append("No elements defined in architecture")
        
        actors = [e for e in elements if e.type == "business_actor"]
        if len(actors) == 0:
            issues.append("No business actors defined")
        
        functions = [e for e in elements if e.type == "business_function"]
        if len(functions) == 0:
            issues.append("No business functions defined")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": [],
            "score": max(0, 100 - len(issues) * 20)
        }


class BusinessArchitectAgent:
    """
    Business Architect Agent for Microservice
    
    Handles ArchiMate business layer management, capability mapping,
    and business architecture design.
    """
    
    def __init__(self):
        self.agent_id = str(uuid.uuid4())
        self.name = "Business Architect"
        self.description = "ArchiMate business layer management and capability mapping"
        
        # Initialize processors
        self.architecture_processor = BusinessArchitectureProcessor()
        
        logger.info(f"Business Architect Agent {self.agent_id} initialized")
    
    async def initialize(self):
        """Initialize agent and dependencies"""
        logger.info(f"Business Architect Agent {self.agent_id} fully initialized")
    
    async def cleanup(self):
        """Cleanup agent resources"""
        logger.info(f"Business Architect Agent {self.agent_id} cleanup completed")
    
    async def process_task(self, task: AgentTask) -> AgentResponse:
        """Process task specific to business architect"""
        try:
            task_type = task.task_type
            
            if task_type == "analyze_business_impact":
                result = await self._analyze_business_impact(task.payload)
            elif task_type == "generate_capability_map":
                result = await self._generate_capability_map(task.payload)
            elif task_type == "design_business_architecture":
                result = await self._design_business_architecture(task.payload)
            elif task_type == "generate_archimate_model":
                result = await self._generate_archimate_model(task.payload)
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
    
    async def _analyze_business_impact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze business impact of requirements"""
        requirements = payload.get("requirements", [])
        context = payload.get("context", {})
        
        if not requirements:
            raise ValueError("requirements are required")
        
        return await self.architecture_processor.analyze_business_impact(requirements, context)
    
    async def _generate_capability_map(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate business capability map"""
        industry = payload.get("industry", "general")
        context = payload.get("context", {})
        
        return await self.architecture_processor.generate_capability_map(industry, context)
    
    async def _design_business_architecture(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Design business architecture"""
        requirements = payload.get("requirements", [])
        capabilities = payload.get("capabilities", [])
        
        if not requirements:
            raise ValueError("requirements are required")
        
        return await self.architecture_processor.design_business_architecture(requirements, capabilities)
    
    async def _generate_archimate_model(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ArchiMate model"""
        elements = payload.get("elements", [])
        relationships = payload.get("relationships", [])
        
        if not elements:
            raise ValueError("elements are required")
        
        return await self.architecture_processor.generate_archimate_model(elements, relationships)