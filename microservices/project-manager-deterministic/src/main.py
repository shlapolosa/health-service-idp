"""
Project Manager Anthropic Microservice

FastAPI microservice implementing the Project Manager agent with Anthropic LLM integration.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import httpx

from .project_manager import ProjectManagerAgent, AnalysisResult
from .models import AgentRequestModel, AgentResponseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global agent instance
agent: Optional[ProjectManagerAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global agent
    
    # Startup
    logger.info("Starting Project Manager Anthropic service...")
    
    try:
        agent = ProjectManagerAgent()
        await agent.initialize()
        logger.info("Project Manager agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Project Manager Anthropic service...")
    if agent:
        await agent.cleanup()


# Initialize FastAPI app
app = FastAPI(
    title="Project Manager Anthropic Service",
    description="Microservice for project manager using deterministic",
    version="1.0.0",
    lifespan=lifespan
)


async def get_agent() -> ProjectManagerAgent:
    """Dependency to get the agent instance"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "project-manager-deterministic"}


@app.post("/analyze-requirements", response_model=AgentResponseModel)
async def analyze_requirements(
    request: AgentRequestModel,
    agent_instance: ProjectManagerAgent = Depends(get_agent)
) -> AgentResponseModel:
    """
    Analyze natural language requirements and convert to structured format
    """
    try:
        # Extract requirements text and domain from request
        requirements_text = request.query
        domain = request.parameters.get("domain", "general") if request.parameters else "general"
        
        # Create task for the agent
        task_payload = {
            "requirements_text": requirements_text,
            "domain": domain
        }
        
        # Process with agent
        from .project_manager import AgentTask
        task = AgentTask(
            task_id=f"analyze-{hash(requirements_text)}",
            task_type="analyze_requirements",
            payload=task_payload
        )
        
        response = await agent_instance.process_task(task)
        
        if response.success:
            return AgentResponseModel(
                result=response.result,
                metadata={
                    "agent_type": "project-manager",
                    "implementation": "deterministic",
                    "task_type": "analyze_requirements",
                    "processing_time": response.metadata.get("processing_time", 0)
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Agent processing failed: {response.error}"
            )
    
    except Exception as e:
        logger.error(f"Error in analyze_requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-entities", response_model=AgentResponseModel)
async def extract_entities(
    request: AgentRequestModel,
    agent_instance: ProjectManagerAgent = Depends(get_agent)
) -> AgentResponseModel:
    """
    Extract entities from text
    """
    try:
        text = request.query
        
        task_payload = {"text": text}
        
        from .project_manager import AgentTask
        task = AgentTask(
            task_id=f"extract-{hash(text)}",
            task_type="extract_entities",
            payload=task_payload
        )
        
        response = await agent_instance.process_task(task)
        
        if response.success:
            return AgentResponseModel(
                result=response.result,
                metadata={
                    "agent_type": "project-manager",
                    "implementation": "deterministic",
                    "task_type": "extract_entities"
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Agent processing failed: {response.error}"
            )
    
    except Exception as e:
        logger.error(f"Error in extract_entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-user-stories", response_model=AgentResponseModel)
async def generate_user_stories(
    request: AgentRequestModel,
    agent_instance: ProjectManagerAgent = Depends(get_agent)
) -> AgentResponseModel:
    """
    Generate user stories from requirements
    """
    try:
        if not request.parameters or "requirements" not in request.parameters:
            raise HTTPException(
                status_code=400,
                detail="requirements parameter is required"
            )
        
        requirements = request.parameters["requirements"]
        task_payload = {"requirements": requirements}
        
        from .project_manager import AgentTask
        task = AgentTask(
            task_id=f"stories-{hash(str(requirements))}",
            task_type="generate_user_stories",
            payload=task_payload
        )
        
        response = await agent_instance.process_task(task)
        
        if response.success:
            return AgentResponseModel(
                result=response.result,
                metadata={
                    "agent_type": "project-manager",
                    "implementation": "deterministic",
                    "task_type": "generate_user_stories"
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Agent processing failed: {response.error}"
            )
    
    except Exception as e:
        logger.error(f"Error in generate_user_stories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/assess-complexity", response_model=AgentResponseModel)
async def assess_complexity(
    request: AgentRequestModel,
    agent_instance: ProjectManagerAgent = Depends(get_agent)
) -> AgentResponseModel:
    """
    Assess complexity of requirements
    """
    try:
        if not request.parameters or "requirements" not in request.parameters:
            raise HTTPException(
                status_code=400,
                detail="requirements parameter is required"
            )
        
        requirements = request.parameters["requirements"]
        task_payload = {"requirements": requirements}
        
        from .project_manager import AgentTask
        task = AgentTask(
            task_id=f"complexity-{hash(str(requirements))}",
            task_type="assess_complexity",
            payload=task_payload
        )
        
        response = await agent_instance.process_task(task)
        
        if response.success:
            return AgentResponseModel(
                result=response.result,
                metadata={
                    "agent_type": "project-manager",
                    "implementation": "deterministic",
                    "task_type": "assess_complexity"
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Agent processing failed: {response.error}"
            )
    
    except Exception as e:
        logger.error(f"Error in assess_complexity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate-requirements", response_model=AgentResponseModel)
async def validate_requirements(
    request: AgentRequestModel,
    agent_instance: ProjectManagerAgent = Depends(get_agent)
) -> AgentResponseModel:
    """
    Validate requirements for completeness and consistency
    """
    try:
        if not request.parameters or "requirements" not in request.parameters:
            raise HTTPException(
                status_code=400,
                detail="requirements parameter is required"
            )
        
        requirements = request.parameters["requirements"]
        task_payload = {"requirements": requirements}
        
        from .project_manager import AgentTask
        task = AgentTask(
            task_id=f"validate-{hash(str(requirements))}",
            task_type="validate_requirements",
            payload=task_payload
        )
        
        response = await agent_instance.process_task(task)
        
        if response.success:
            return AgentResponseModel(
                result=response.result,
                metadata={
                    "agent_type": "project-manager",
                    "implementation": "deterministic",
                    "task_type": "validate_requirements"
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Agent processing failed: {response.error}"
            )
    
    except Exception as e:
        logger.error(f"Error in validate_requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Main entry point for development
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)