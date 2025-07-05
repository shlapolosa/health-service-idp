"""
Shared data models for agent microservices
"""

import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel, Field


class AgentType(Enum):
    """Types of agents in the system"""
    BUSINESS_ANALYST = "business-analyst"
    BUSINESS_ARCHITECT = "business-architect"
    APPLICATION_ARCHITECT = "application-architect"
    INFRASTRUCTURE_ARCHITECT = "infrastructure-architect"
    SOLUTION_ARCHITECT = "solution-architect"
    DEVELOPER = "developer"
    PROJECT_MANAGER = "project-manager"
    ACCOUNTANT = "accountant"
    ORCHESTRATOR = "orchestrator"


class AgentCapability(Enum):
    """Agent capabilities"""
    REQUIREMENT_ANALYSIS = "requirement-analysis"
    BUSINESS_ARCHITECTURE = "business-architecture"
    APPLICATION_ARCHITECTURE = "application-architecture"
    INFRASTRUCTURE_ARCHITECTURE = "infrastructure-architecture"
    SOLUTION_ARCHITECTURE = "solution-architecture"
    CODE_GENERATION = "code-generation"
    PROJECT_MANAGEMENT = "project-management"
    COST_ANALYSIS = "cost-analysis"
    DOCUMENTATION = "documentation"
    VALIDATION = "validation"
    ORCHESTRATION = "orchestration"


class ImplementationType(Enum):
    """Implementation types for agents"""
    DETERMINISTIC = "deterministic"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class AgentTask:
    """Task for agent processing"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    priority: int = 1  # 1=low, 2=medium, 3=high


@dataclass
class AgentResponse:
    """Response from agent processing"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    processing_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


class AgentRequestModel(BaseModel):
    """Base request model for agent operations"""
    query: str = Field(..., description="The query to process")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional parameters for the request"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context for the request"
    )
    task_type: Optional[str] = Field(
        default=None,
        description="Specific task type to execute"
    )
    priority: Optional[int] = Field(
        default=1,
        description="Task priority (1=low, 2=medium, 3=high)"
    )


class AgentResponseModel(BaseModel):
    """Base response model for agent operations"""
    result: Any = Field(..., description="The result of the operation")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata about the operation"
    )
    processing_time: Optional[float] = Field(
        default=None,
        description="Time taken to process the request in seconds"
    )


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    agent_type: str
    implementation: str
    timestamp: str
    capabilities: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    status_code: int
    timestamp: str