"""
Pydantic models for Business Architect microservice
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from dataclasses import dataclass


class AgentRequestModel(BaseModel):
    """Standard agent request model"""
    query: str = Field(..., description="The query or task for the agent")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Additional parameters")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Context information")


class AgentResponseModel(BaseModel):
    """Standard agent response model"""
    result: Dict[str, Any] = Field(..., description="The result data")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Response metadata")


@dataclass
class ArchiMateElement:
    """ArchiMate element representation"""
    id: str
    name: str
    type: str
    layer: str
    description: str = ""
    properties: Dict[str, Any] = None
    relationships: List[str] = None
    color: str = "#FFFF99"  # Yellow for business layer
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.relationships is None:
            self.relationships = []
    
    def dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "layer": self.layer,
            "description": self.description,
            "properties": self.properties,
            "relationships": self.relationships,
            "color": self.color
        }


@dataclass
class BusinessCapability:
    """Business capability definition"""
    id: str
    name: str
    description: str
    level: int = 1
    parent_id: Optional[str] = None
    children: List[str] = None
    maturity_level: str = "developing"
    business_value: str = "medium"
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "parent_id": self.parent_id,
            "children": self.children,
            "maturity_level": self.maturity_level,
            "business_value": self.business_value
        }


@dataclass
class ArchitectureChange:
    """Architecture change representation"""
    change_id: str
    change_type: str
    element_type: str
    element_id: str
    current_state: Optional[Dict[str, Any]] = None
    target_state: Optional[Dict[str, Any]] = None
    rationale: str = ""
    impact_level: str = "medium"
    affected_elements: List[str] = None
    
    def __post_init__(self):
        if self.affected_elements is None:
            self.affected_elements = []
    
    def dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type,
            "element_type": self.element_type,
            "element_id": self.element_id,
            "current_state": self.current_state,
            "target_state": self.target_state,
            "rationale": self.rationale,
            "impact_level": self.impact_level,
            "affected_elements": self.affected_elements
        }