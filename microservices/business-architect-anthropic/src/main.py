"""
Business Architect Anthropic Microservice

FastAPI microservice implementing the Business Architect agent with Anthropic LLM integration.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import httpx

from .business_architect import BusinessArchitectAgent
from .models import AgentRequestModel, AgentResponseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global agent instance
agent: Optional[BusinessArchitectAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global agent
    
    # Startup
    logger.info("Starting Business Architect Anthropic service...")
    
    try:
        agent = BusinessArchitectAgent()
        await agent.initialize()
        logger.info("Business Architect agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Business Architect Anthropic service...")
    if agent:
        await agent.cleanup()


# Initialize FastAPI app
app = FastAPI(
    title="Business Architect Anthropic Service",
    description="Microservice for business architecture using Anthropic LLM",
    version="1.0.0",
    lifespan=lifespan
)


async def get_agent() -> BusinessArchitectAgent:
    """Dependency to get the agent instance"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "business-architect-anthropic"}


@app.post("/analyze-business-impact", response_model=AgentResponseModel)
async def analyze_business_impact(
    request: AgentRequestModel,
    agent_instance: BusinessArchitectAgent = Depends(get_agent)
) -> AgentResponseModel:
    """
    Analyze business impact of requirements
    """
    try:
        # Extract requirements and context from request
        requirements = request.parameters.get("requirements", []) if request.parameters else []
        context = request.parameters.get("context", {}) if request.parameters else {}
        
        if not requirements:
            # Try to parse from query if requirements not in parameters
            raise HTTPException(
                status_code=400,
                detail="requirements parameter is required"
            )
        
        # Create task for the agent
        task_payload = {
            "requirements": requirements,
            "context": context
        }
        
        # Process with agent
        from .business_architect import AgentTask
        task = AgentTask(
            task_id=f"impact-{hash(str(requirements))}",
            task_type="analyze_business_impact",
            payload=task_payload
        )
        
        response = await agent_instance.process_task(task)
        
        if response.success:
            return AgentResponseModel(
                result=response.result,
                metadata={
                    "agent_type": "business-architect",
                    "implementation": "anthropic",
                    "task_type": "analyze_business_impact",
                    "processing_time": response.metadata.get("processing_time", 0)
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Agent processing failed: {response.error}"
            )
    
    except Exception as e:
        logger.error(f"Error in analyze_business_impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-capability-map", response_model=AgentResponseModel)
async def generate_capability_map(
    request: AgentRequestModel,
    agent_instance: BusinessArchitectAgent = Depends(get_agent)
) -> AgentResponseModel:
    """
    Generate business capability map
    """
    try:
        industry = request.parameters.get("industry", "general") if request.parameters else "general"
        context = request.parameters.get("context", {}) if request.parameters else {}
        
        task_payload = {
            "industry": industry,
            "context": context
        }
        
        from .business_architect import AgentTask
        task = AgentTask(
            task_id=f"capability-{hash(industry)}",
            task_type="generate_capability_map",
            payload=task_payload
        )
        
        response = await agent_instance.process_task(task)
        
        if response.success:
            return AgentResponseModel(
                result=response.result,
                metadata={
                    "agent_type": "business-architect",
                    "implementation": "anthropic",
                    "task_type": "generate_capability_map"
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Agent processing failed: {response.error}"
            )
    
    except Exception as e:
        logger.error(f"Error in generate_capability_map: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/design-business-architecture", response_model=AgentResponseModel)
async def design_business_architecture(
    request: AgentRequestModel,
    agent_instance: BusinessArchitectAgent = Depends(get_agent)
) -> AgentResponseModel:
    """
    Design business architecture from requirements
    """
    try:
        if not request.parameters or "requirements" not in request.parameters:
            raise HTTPException(
                status_code=400,
                detail="requirements parameter is required"
            )
        
        requirements = request.parameters["requirements"]
        capabilities = request.parameters.get("capabilities", [])
        
        task_payload = {
            "requirements": requirements,
            "capabilities": capabilities
        }
        
        from .business_architect import AgentTask
        task = AgentTask(
            task_id=f"design-{hash(str(requirements))}",
            task_type="design_business_architecture",
            payload=task_payload
        )
        
        response = await agent_instance.process_task(task)
        
        if response.success:
            return AgentResponseModel(
                result=response.result,
                metadata={
                    "agent_type": "business-architect",
                    "implementation": "anthropic",
                    "task_type": "design_business_architecture"
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Agent processing failed: {response.error}"
            )
    
    except Exception as e:
        logger.error(f"Error in design_business_architecture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-archimate-model", response_model=AgentResponseModel)
async def generate_archimate_model(
    request: AgentRequestModel,
    agent_instance: BusinessArchitectAgent = Depends(get_agent)
) -> AgentResponseModel:
    """
    Generate ArchiMate model visualization
    """
    try:
        if not request.parameters or "elements" not in request.parameters:
            raise HTTPException(
                status_code=400,
                detail="elements parameter is required"
            )
        
        elements = request.parameters["elements"]
        relationships = request.parameters.get("relationships", [])
        
        task_payload = {
            "elements": elements,
            "relationships": relationships
        }
        
        from .business_architect import AgentTask
        task = AgentTask(
            task_id=f"archimate-{hash(str(elements))}",
            task_type="generate_archimate_model",
            payload=task_payload
        )
        
        response = await agent_instance.process_task(task)
        
        if response.success:
            return AgentResponseModel(
                result=response.result,
                metadata={
                    "agent_type": "business-architect",
                    "implementation": "anthropic",
                    "task_type": "generate_archimate_model"
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Agent processing failed: {response.error}"
            )
    
    except Exception as e:
        logger.error(f"Error in generate_archimate_model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Main entry point for development
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)