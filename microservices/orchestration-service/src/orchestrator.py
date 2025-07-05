"""
Workflow Orchestrator for Agent Coordination
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set

import httpx
import redis.asyncio as redis
from .models import (
    WorkflowDefinition, WorkflowExecution, WorkflowStatus, WorkflowStep,
    AgentTask, AgentTaskStatus, AgentInfo, OrchestrationMetrics, WorkflowEvent
)

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Main orchestrator for managing workflows and agent coordination
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # In-memory state
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.agent_registry: Dict[str, AgentInfo] = {}
        
        # Background tasks
        self._running_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        
        # Initialize standard workflow definitions
        self._initialize_standard_workflows()
    
    async def initialize(self):
        """Initialize the orchestrator"""
        logger.info("Initializing Workflow Orchestrator...")
        
        # Initialize Redis connection
        self.redis_client = redis.from_url(self.redis_url)
        await self.redis_client.ping()
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Discover available agents
        await self._discover_agents()
        
        # Start background tasks
        self._start_background_tasks()
        
        logger.info("Workflow Orchestrator initialized successfully")
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up Workflow Orchestrator...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel running tasks
        for task in self._running_tasks:
            task.cancel()
        
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
        
        # Close connections
        if self.http_client:
            await self.http_client.aclose()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Workflow Orchestrator cleanup completed")
    
    def _initialize_standard_workflows(self):
        """Initialize standard workflow definitions"""
        
        # Requirements Analysis Workflow
        requirements_analysis = WorkflowDefinition(
            workflow_id="requirements_analysis",
            name="Requirements Analysis Workflow",
            description="End-to-end requirements analysis and architecture design",
            steps=[
                WorkflowStep(
                    step_id="analyze_requirements",
                    name="Analyze Requirements",
                    agent_type="business-analyst",
                    task_type="analyze_requirements",
                    input_mapping={"requirements_text": "input.requirements"}
                ),
                WorkflowStep(
                    step_id="assess_business_impact",
                    name="Assess Business Impact",
                    agent_type="business-architect",
                    task_type="analyze_business_impact",
                    input_mapping={"requirements": "analyze_requirements.result.requirements"},
                    dependencies=["analyze_requirements"]
                ),
                WorkflowStep(
                    step_id="design_application_architecture",
                    name="Design Application Architecture",
                    agent_type="application-architect",
                    task_type="design_architecture",
                    input_mapping={"requirements": "analyze_requirements.result.requirements"},
                    dependencies=["assess_business_impact"]
                ),
                WorkflowStep(
                    step_id="design_infrastructure",
                    name="Design Infrastructure",
                    agent_type="infrastructure-architect",
                    task_type="design_infrastructure",
                    input_mapping={"application_design": "design_application_architecture.result"},
                    dependencies=["design_application_architecture"]
                ),
                WorkflowStep(
                    step_id="consolidate_solution",
                    name="Consolidate Solution",
                    agent_type="solution-architect",
                    task_type="consolidate_architecture",
                    input_mapping={
                        "business_analysis": "assess_business_impact.result",
                        "application_design": "design_application_architecture.result",
                        "infrastructure_design": "design_infrastructure.result"
                    },
                    dependencies=["design_infrastructure"]
                )
            ]
        )
        
        self.workflow_definitions["requirements_analysis"] = requirements_analysis
        
        # Simple Analysis Workflow
        simple_analysis = WorkflowDefinition(
            workflow_id="simple_analysis",
            name="Simple Requirements Analysis",
            description="Basic requirements analysis workflow",
            steps=[
                WorkflowStep(
                    step_id="analyze_requirements",
                    name="Analyze Requirements",
                    agent_type="business-analyst",
                    task_type="analyze_requirements",
                    input_mapping={"requirements_text": "input.requirements"}
                ),
                WorkflowStep(
                    step_id="generate_user_stories",
                    name="Generate User Stories",
                    agent_type="business-analyst",
                    task_type="generate_user_stories",
                    input_mapping={"requirements": "analyze_requirements.result.requirements"},
                    dependencies=["analyze_requirements"]
                )
            ]
        )
        
        self.workflow_definitions["simple_analysis"] = simple_analysis
    
    async def _discover_agents(self):
        """Discover available agent services"""
        logger.info("Discovering available agents...")
        
        # Define known agent services (in a real implementation, this could use service discovery)
        known_agents = [
            {"type": "business-analyst", "implementation": "anthropic", "port": 8081},
            {"type": "business-analyst", "implementation": "deterministic", "port": 8082},
            {"type": "business-architect", "implementation": "anthropic", "port": 8083},
            {"type": "business-architect", "implementation": "deterministic", "port": 8084},
            {"type": "application-architect", "implementation": "anthropic", "port": 8085},
            {"type": "application-architect", "implementation": "deterministic", "port": 8086},
            {"type": "infrastructure-architect", "implementation": "anthropic", "port": 8087},
            {"type": "infrastructure-architect", "implementation": "deterministic", "port": 8088},
            {"type": "solution-architect", "implementation": "anthropic", "port": 8089},
            {"type": "solution-architect", "implementation": "deterministic", "port": 8090},
            {"type": "developer", "implementation": "anthropic", "port": 8091},
            {"type": "developer", "implementation": "deterministic", "port": 8092},
            {"type": "project-manager", "implementation": "anthropic", "port": 8093},
            {"type": "project-manager", "implementation": "deterministic", "port": 8094},
            {"type": "accountant", "implementation": "anthropic", "port": 8095},
            {"type": "accountant", "implementation": "deterministic", "port": 8096},
        ]
        
        for agent_config in known_agents:
            agent_key = f"{agent_config['type']}-{agent_config['implementation']}"
            endpoint_url = f"http://localhost:{agent_config['port']}"
            health_url = f"{endpoint_url}/health"
            
            agent_info = AgentInfo(
                agent_type=agent_config["type"],
                implementation=agent_config["implementation"],
                endpoint_url=endpoint_url,
                health_check_url=health_url,
                capabilities=[
                    "analyze_requirements" if "analyst" in agent_config["type"] else "process_task",
                    "generate_reports",
                    "validate_input"
                ]
            )
            
            self.agent_registry[agent_key] = agent_info
        
        logger.info(f"Discovered {len(self.agent_registry)} agents")
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        
        # Health check task
        health_check_task = asyncio.create_task(self._health_check_loop())
        self._running_tasks.add(health_check_task)
        
        # Workflow execution monitor
        workflow_monitor_task = asyncio.create_task(self._workflow_monitor_loop())
        self._running_tasks.add(workflow_monitor_task)
        
        logger.info("Background tasks started")
    
    async def _health_check_loop(self):
        """Background task to check agent health"""
        while not self._shutdown_event.is_set():
            try:
                await self._check_agent_health()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)
    
    async def _workflow_monitor_loop(self):
        """Background task to monitor workflow executions"""
        while not self._shutdown_event.is_set():
            try:
                await self._monitor_active_workflows()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Workflow monitor loop error: {e}")
                await asyncio.sleep(5)
    
    async def _check_agent_health(self):
        """Check health of all registered agents"""
        if not self.http_client:
            return
        
        for agent_key, agent_info in self.agent_registry.items():
            try:
                start_time = datetime.utcnow()
                response = await self.http_client.get(agent_info.health_check_url, timeout=5.0)
                end_time = datetime.utcnow()
                
                if response.status_code == 200:
                    agent_info.status = "available"
                    agent_info.response_time_avg = (end_time - start_time).total_seconds()
                else:
                    agent_info.status = "unhealthy"
                
                agent_info.last_health_check = datetime.utcnow()
                
            except Exception as e:
                logger.warning(f"Health check failed for {agent_key}: {e}")
                agent_info.status = "unavailable"
                agent_info.last_health_check = datetime.utcnow()
    
    async def _monitor_active_workflows(self):
        """Monitor active workflow executions"""
        current_time = datetime.utcnow()
        
        for execution_id, execution in list(self.active_executions.items()):
            # Check for timeouts
            if execution.started_at:
                elapsed = (current_time - execution.started_at).total_seconds()
                if elapsed > 3600:  # 1 hour timeout
                    logger.warning(f"Workflow {execution_id} timed out")
                    execution.status = WorkflowStatus.FAILED
                    execution.error_message = "Workflow execution timed out"
                    execution.completed_at = current_time
                    
                    # Remove from active executions
                    del self.active_executions[execution_id]
    
    async def create_workflow_execution(
        self, 
        workflow_type: str, 
        input_data: Dict[str, Any]
    ) -> str:
        """Create a new workflow execution"""
        
        if workflow_type not in self.workflow_definitions:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        execution_id = str(uuid.uuid4())
        workflow_def = self.workflow_definitions[workflow_type]
        
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_type,
            input_data=input_data,
            created_at=datetime.utcnow()
        )
        
        # Create tasks for each step
        for step in workflow_def.steps:
            task = AgentTask(
                task_id=f"{execution_id}_{step.step_id}",
                agent_type=step.agent_type,
                task_type=step.task_type,
                input_data={},  # Will be populated during execution
                dependencies=step.dependencies
            )
            execution.tasks[step.step_id] = task
        
        self.active_executions[execution_id] = execution
        
        # Store in Redis for persistence
        if self.redis_client:
            await self.redis_client.setex(
                f"workflow:{execution_id}",
                3600,  # 1 hour TTL
                json.dumps(execution.dict(), default=str)
            )
        
        logger.info(f"Created workflow execution {execution_id} for type {workflow_type}")
        return execution_id
    
    async def execute_workflow(self, execution_id: str):
        """Execute a workflow"""
        if execution_id not in self.active_executions:
            logger.error(f"Workflow execution {execution_id} not found")
            return
        
        execution = self.active_executions[execution_id]
        workflow_def = self.workflow_definitions[execution.workflow_id]
        
        try:
            execution.status = WorkflowStatus.RUNNING
            execution.started_at = datetime.utcnow()
            
            logger.info(f"Starting workflow execution {execution_id}")
            
            # Execute steps in dependency order
            completed_steps = set()
            
            while len(completed_steps) < len(workflow_def.steps):
                # Find steps ready to execute (dependencies satisfied)
                ready_steps = []
                for step in workflow_def.steps:
                    if (step.step_id not in completed_steps and 
                        all(dep in completed_steps for dep in step.dependencies)):
                        ready_steps.append(step)
                
                if not ready_steps:
                    # Check if we're stuck
                    remaining_steps = [s for s in workflow_def.steps if s.step_id not in completed_steps]
                    logger.error(f"No ready steps found. Remaining: {[s.step_id for s in remaining_steps]}")
                    break
                
                # Execute ready steps (can be done in parallel)
                step_tasks = []
                for step in ready_steps:
                    task = asyncio.create_task(self._execute_step(execution, step))
                    step_tasks.append((step.step_id, task))
                
                # Wait for step completion
                for step_id, task in step_tasks:
                    try:
                        await task
                        completed_steps.add(step_id)
                        execution.completed_steps.append(step_id)
                        logger.info(f"Completed step {step_id} in workflow {execution_id}")
                    except Exception as e:
                        logger.error(f"Step {step_id} failed in workflow {execution_id}: {e}")
                        execution.failed_steps.append(step_id)
                        execution.tasks[step_id].status = AgentTaskStatus.FAILED
                        execution.tasks[step_id].error_message = str(e)
                        # For now, continue with other steps
            
            # Determine final status
            if execution.failed_steps:
                execution.status = WorkflowStatus.FAILED
                execution.error_message = f"Failed steps: {execution.failed_steps}"
            else:
                execution.status = WorkflowStatus.COMPLETED
                # Collect final output
                execution.output_data = self._collect_workflow_output(execution, workflow_def)
            
            execution.completed_at = datetime.utcnow()
            
            logger.info(f"Workflow execution {execution_id} completed with status {execution.status}")
            
        except Exception as e:
            logger.error(f"Workflow execution {execution_id} failed: {e}")
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
        
        finally:
            # Update Redis
            if self.redis_client:
                await self.redis_client.setex(
                    f"workflow:{execution_id}",
                    86400,  # 24 hour TTL for completed workflows
                    json.dumps(execution.dict(), default=str)
                )
    
    async def _execute_step(self, execution: WorkflowExecution, step: WorkflowStep):
        """Execute a single workflow step"""
        task = execution.tasks[step.step_id]
        
        try:
            task.status = AgentTaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            
            # Prepare input data using input mapping
            input_data = self._prepare_step_input(execution, step)
            task.input_data = input_data
            
            # Execute agent task
            result = await self.execute_agent_task(
                agent_type=step.agent_type,
                task_type=step.task_type,
                payload=input_data
            )
            
            task.result = result
            task.status = AgentTaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
        except Exception as e:
            task.status = AgentTaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            raise
    
    def _prepare_step_input(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict[str, Any]:
        """Prepare input data for a step using input mapping"""
        input_data = {}
        
        for output_key, input_path in step.input_mapping.items():
            try:
                if input_path.startswith("input."):
                    # Reference to workflow input
                    key = input_path[6:]  # Remove "input."
                    if key in execution.input_data:
                        input_data[output_key] = execution.input_data[key]
                else:
                    # Reference to previous step output
                    parts = input_path.split(".")
                    if len(parts) >= 2:
                        step_id = parts[0]
                        if step_id in execution.tasks and execution.tasks[step_id].result:
                            value = execution.tasks[step_id].result
                            # Navigate nested structure
                            for part in parts[1:]:
                                if isinstance(value, dict) and part in value:
                                    value = value[part]
                                else:
                                    value = None
                                    break
                            if value is not None:
                                input_data[output_key] = value
            except Exception as e:
                logger.warning(f"Failed to map input {input_path} to {output_key}: {e}")
        
        return input_data
    
    def _collect_workflow_output(self, execution: WorkflowExecution, workflow_def: WorkflowDefinition) -> Dict[str, Any]:
        """Collect final workflow output"""
        output = {}
        
        # Collect results from all completed tasks
        for step_id, task in execution.tasks.items():
            if task.status == AgentTaskStatus.COMPLETED and task.result:
                output[step_id] = task.result
        
        return output
    
    async def execute_agent_task(
        self, 
        agent_type: str, 
        task_type: str, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a task on a specific agent"""
        
        # Find available agent
        agent_key = None
        for key, agent_info in self.agent_registry.items():
            if (agent_info.agent_type == agent_type and 
                agent_info.status == "available"):
                agent_key = key
                break
        
        if not agent_key:
            raise RuntimeError(f"No available agent found for type {agent_type}")
        
        agent_info = self.agent_registry[agent_key]
        
        if not self.http_client:
            raise RuntimeError("HTTP client not initialized")
        
        # Prepare request
        endpoint_mapping = {
            "analyze_requirements": "/analyze-requirements",
            "extract_entities": "/extract-entities", 
            "generate_user_stories": "/generate-user-stories",
            "assess_complexity": "/assess-complexity",
            "validate_requirements": "/validate-requirements",
            "analyze_business_impact": "/analyze-business-impact",
            "generate_capability_map": "/generate-capability-map",
            "design_business_architecture": "/design-business-architecture",
            "generate_archimate_model": "/generate-archimate-model"
        }
        
        endpoint = endpoint_mapping.get(task_type, f"/{task_type}")
        url = f"{agent_info.endpoint_url}{endpoint}"
        
        request_data = {
            "query": payload.get("query", ""),
            "parameters": payload.get("parameters", {}),
            "context": payload.get("context", {})
        }
        
        # Make request
        response = await self.http_client.post(url, json=request_data, timeout=60.0)
        response.raise_for_status()
        
        result = response.json()
        return result.get("result", {})
    
    async def get_workflow_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow execution status"""
        # Check in-memory first
        if execution_id in self.active_executions:
            return self.active_executions[execution_id].dict()
        
        # Check Redis
        if self.redis_client:
            data = await self.redis_client.get(f"workflow:{execution_id}")
            if data:
                return json.loads(data)
        
        return None
    
    async def cancel_workflow_execution(self, execution_id: str) -> bool:
        """Cancel a workflow execution"""
        if execution_id not in self.active_executions:
            return False
        
        execution = self.active_executions[execution_id]
        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        
        # Cancel running tasks
        for task in execution.tasks.values():
            if task.status == AgentTaskStatus.RUNNING:
                task.status = AgentTaskStatus.CANCELLED
        
        # Remove from active executions
        del self.active_executions[execution_id]
        
        return True
    
    async def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get list of available agents"""
        return [
            {
                "agent_key": key,
                "agent_type": info.agent_type,
                "implementation": info.implementation,
                "status": info.status,
                "capabilities": info.capabilities,
                "endpoint_url": info.endpoint_url,
                "last_health_check": info.last_health_check.isoformat() if info.last_health_check else None,
                "response_time_avg": info.response_time_avg
            }
            for key, info in self.agent_registry.items()
        ]
    
    async def get_workflow_definitions(self) -> List[Dict[str, Any]]:
        """Get list of available workflow definitions"""
        return [
            {
                "workflow_id": def_id,
                "name": definition.name,
                "description": definition.description,
                "version": definition.version,
                "steps": len(definition.steps),
                "timeout_seconds": definition.timeout_seconds
            }
            for def_id, definition in self.workflow_definitions.items()
        ]
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get orchestration metrics"""
        active_count = len(self.active_executions)
        
        # Count by status (would be better to track in Redis)
        total_workflows = active_count  # Simplified
        completed_workflows = 0
        failed_workflows = 0
        
        agent_health = {
            key: info.status 
            for key, info in self.agent_registry.items()
        }
        
        return {
            "total_workflows": total_workflows,
            "active_workflows": active_count,
            "completed_workflows": completed_workflows,
            "failed_workflows": failed_workflows,
            "total_agents": len(self.agent_registry),
            "available_agents": sum(1 for info in self.agent_registry.values() if info.status == "available"),
            "agent_health_status": agent_health,
            "last_updated": datetime.utcnow().isoformat()
        }