"""
Data models for Accountant Anthropic microservice

Pydantic models for request/response handling.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class AgentRequestModel(BaseModel):
    """Base request model for agent operations"""
    query: str = Field(..., description="The query to process")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional parameters for the request"
    )


class AgentResponseModel(BaseModel):
    """Base response model for agent operations"""
    result: Any = Field(..., description="The result of the operation")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata about the operation"
    )


class RequirementEntity(BaseModel):
    """Extracted entity from requirement text"""
    text: str
    label: str
    start: int
    end: int
    confidence: float = 0.0
    attributes: Dict[str, Any] = Field(default_factory=dict)


class BusinessRequirement(BaseModel):
    """Structured business requirement in Subject-Action-Object format"""
    subject: str
    action: str
    object: str
    priority: str = "medium"
    category: str = "functional"
    rationale: str = ""
    acceptance_criteria: List[str] = Field(default_factory=list)
    stakeholders: List[str] = Field(default_factory=list)
    business_value: str = ""
    complexity: str = "medium"
    entities: List[RequirementEntity] = Field(default_factory=list)
    confidence_score: float = 0.0


class AnalysisResult(BaseModel):
    """Result of business analysis operation"""
    requirements: List[BusinessRequirement] = Field(default_factory=list)
    entities: List[RequirementEntity] = Field(default_factory=list)
    user_stories: List[str] = Field(default_factory=list)
    complexity_assessment: str = "medium"
    business_value_score: float = 0.0
    confidence: float = 0.0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    timestamp: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    status_code: int