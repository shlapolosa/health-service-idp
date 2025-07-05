"""
Orchestration Service Microservice

FastAPI microservice for agent orchestration and workflow management.
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import httpx
import redis.asyncio as redis

from .models import AgentRequestModel, AgentResponseModel, WorkflowDefinition, WorkflowExecution
from .orchestrator import WorkflowOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator: Optional[WorkflowOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global orchestrator
    
    # Startup
    logger.info("Starting Orchestration Service...")
    
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        orchestrator = WorkflowOrchestrator(redis_url)
        await orchestrator.initialize()
        logger.info("Orchestration Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize orchestration service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Orchestration Service...")
    if orchestrator:
        await orchestrator.cleanup()


# Initialize FastAPI app
app = FastAPI(
    title="Orchestration Service",
    description="Microservice for agent orchestration and workflow management",
    version="1.0.0",
    lifespan=lifespan
)


async def get_orchestrator() -> WorkflowOrchestrator:
    """Dependency to get the orchestrator instance"""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return orchestrator


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "orchestration-service"}


@app.post("/workflows", response_model=AgentResponseModel)
async def create_workflow(
    request: AgentRequestModel,
    background_tasks: BackgroundTasks,
    orchestrator_instance: WorkflowOrchestrator = Depends(get_orchestrator)
) -> AgentResponseModel:
    """
    Create and execute a new workflow
    """
    try:
        workflow_type = request.parameters.get("workflow_type", "requirements_analysis") if request.parameters else "requirements_analysis"
        requirements = request.query
        context = request.context or {}
        
        # Create workflow execution
        execution_id = await orchestrator_instance.create_workflow_execution(
            workflow_type=workflow_type,
            input_data={
                "requirements": requirements,
                "context": context
            }
        )
        
        # Start workflow execution in background
        background_tasks.add_task(
            orchestrator_instance.execute_workflow,
            execution_id
        )
        
        return AgentResponseModel(
            result={
                "execution_id": execution_id,
                "status": "started",
                "workflow_type": workflow_type
            },
            metadata={
                "service": "orchestration",
                "action": "create_workflow"
            }
        )
    
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows/{execution_id}", response_model=AgentResponseModel)
async def get_workflow_status(
    execution_id: str,
    orchestrator_instance: WorkflowOrchestrator = Depends(get_orchestrator)
) -> AgentResponseModel:
    """
    Get workflow execution status
    """
    try:
        execution = await orchestrator_instance.get_workflow_execution(execution_id)
        
        if not execution:
            raise HTTPException(status_code=404, detail="Workflow execution not found")
        
        return AgentResponseModel(
            result=execution,
            metadata={
                "service": "orchestration",
                "action": "get_workflow_status"
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workflows/{execution_id}/cancel", response_model=AgentResponseModel)
async def cancel_workflow(
    execution_id: str,
    orchestrator_instance: WorkflowOrchestrator = Depends(get_orchestrator)
) -> AgentResponseModel:
    """
    Cancel a workflow execution
    """
    try:
        success = await orchestrator_instance.cancel_workflow_execution(execution_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Workflow execution not found or cannot be cancelled")
        
        return AgentResponseModel(
            result={
                "execution_id": execution_id,
                "status": "cancelled"
            },
            metadata={
                "service": "orchestration",
                "action": "cancel_workflow"
            }
        )
    
    except Exception as e:
        logger.error(f"Error cancelling workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents", response_model=AgentResponseModel)
async def list_agents(
    orchestrator_instance: WorkflowOrchestrator = Depends(get_orchestrator)
) -> AgentResponseModel:
    """
    List available agents
    """
    try:
        agents = await orchestrator_instance.get_available_agents()
        
        return AgentResponseModel(
            result={
                "agents": agents,
                "total_count": len(agents)
            },
            metadata={
                "service": "orchestration",
                "action": "list_agents"
            }
        )
    
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/{agent_type}/execute", response_model=AgentResponseModel)
async def execute_agent_task(
    agent_type: str,
    request: AgentRequestModel,
    orchestrator_instance: WorkflowOrchestrator = Depends(get_orchestrator)
) -> AgentResponseModel:
    """
    Execute a specific agent task
    """
    try:
        task_type = request.parameters.get("task_type") if request.parameters else None
        if not task_type:
            raise HTTPException(status_code=400, detail="task_type parameter is required")
        
        result = await orchestrator_instance.execute_agent_task(
            agent_type=agent_type,
            task_type=task_type,
            payload={
                "query": request.query,
                "parameters": request.parameters,
                "context": request.context
            }
        )
        
        return AgentResponseModel(
            result=result,
            metadata={
                "service": "orchestration",
                "action": "execute_agent_task",
                "agent_type": agent_type,
                "task_type": task_type
            }
        )
    
    except Exception as e:
        logger.error(f"Error executing agent task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows/definitions", response_model=AgentResponseModel)
async def list_workflow_definitions(
    orchestrator_instance: WorkflowOrchestrator = Depends(get_orchestrator)
) -> AgentResponseModel:
    """
    List available workflow definitions
    """
    try:
        definitions = await orchestrator_instance.get_workflow_definitions()
        
        return AgentResponseModel(
            result={
                "workflow_definitions": definitions,
                "total_count": len(definitions)
            },
            metadata={
                "service": "orchestration",
                "action": "list_workflow_definitions"
            }
        )
    
    except Exception as e:
        logger.error(f"Error listing workflow definitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics", response_model=AgentResponseModel)
async def get_metrics(
    orchestrator_instance: WorkflowOrchestrator = Depends(get_orchestrator)
) -> AgentResponseModel:
    """
    Get orchestration metrics
    """
    try:
        metrics = await orchestrator_instance.get_metrics()
        
        return AgentResponseModel(
            result=metrics,
            metadata={
                "service": "orchestration",
                "action": "get_metrics"
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Main entry point for development
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)