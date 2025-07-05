"""
Pydantic models for Orchestration Service
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AgentRequestModel(BaseModel):
    """Standard agent request model"""
    query: str = Field(..., description="The query or task for the agent")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Additional parameters")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Context information")


class AgentResponseModel(BaseModel):
    """Standard agent response model"""
    result: Dict[str, Any] = Field(..., description="The result data")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Response metadata")


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentTaskStatus(str, Enum):
    """Agent task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentTask(BaseModel):
    """Agent task definition"""
    task_id: str
    agent_type: str
    task_type: str
    input_data: Dict[str, Any]
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dependencies: List[str] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3


class WorkflowStep(BaseModel):
    """Workflow step definition"""
    step_id: str
    name: str
    agent_type: str
    task_type: str
    input_mapping: Dict[str, str] = Field(default_factory=dict)
    output_mapping: Dict[str, str] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    condition: Optional[str] = None  # Optional condition for conditional execution
    retry_policy: Dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinition(BaseModel):
    """Workflow definition"""
    workflow_id: str
    name: str
    description: str
    version: str = "1.0.0"
    steps: List[WorkflowStep]
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 3600  # 1 hour default
    max_concurrent_steps: int = 5


class WorkflowExecution(BaseModel):
    """Workflow execution instance"""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    current_step: Optional[str] = None
    completed_steps: List[str] = Field(default_factory=list)
    failed_steps: List[str] = Field(default_factory=list)
    tasks: Dict[str, AgentTask] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class AgentInfo(BaseModel):
    """Agent information"""
    agent_type: str
    implementation: str  # anthropic, deterministic, etc.
    status: str = "available"
    capabilities: List[str] = Field(default_factory=list)
    endpoint_url: str
    health_check_url: str
    last_health_check: Optional[datetime] = None
    response_time_avg: float = 0.0
    success_rate: float = 1.0


class OrchestrationMetrics(BaseModel):
    """Orchestration metrics"""
    total_workflows: int = 0
    active_workflows: int = 0
    completed_workflows: int = 0
    failed_workflows: int = 0
    total_agent_tasks: int = 0
    active_agent_tasks: int = 0
    agent_health_status: Dict[str, str] = Field(default_factory=dict)
    average_workflow_duration: float = 0.0
    success_rate: float = 1.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class WorkflowEvent(BaseModel):
    """Workflow event for pub/sub"""
    event_type: str  # workflow_started, workflow_completed, task_started, task_completed, etc.
    execution_id: str
    workflow_id: str
    step_id: Optional[str] = None
    task_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RetryPolicy(BaseModel):
    """Retry policy configuration"""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True


class WorkflowConfiguration(BaseModel):
    """Workflow configuration"""
    max_concurrent_workflows: int = 10
    max_concurrent_tasks: int = 50
    default_timeout: int = 3600  # seconds
    health_check_interval: int = 30  # seconds
    metrics_collection_interval: int = 60  # seconds
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    agent_discovery_enabled: bool = True
    event_publishing_enabled: bool = True