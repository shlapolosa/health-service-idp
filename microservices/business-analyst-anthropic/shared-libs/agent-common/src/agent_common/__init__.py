"""
Agent Common Library

Shared base classes and utilities for all agent microservices.
"""

from .base_agent import BaseAgent, AgentType, AgentCapability
from .models import AgentTask, AgentResponse, AgentRequestModel, AgentResponseModel
from .config import AgentConfig, get_agent_config
from .shared_agent_factory import create_agent_app

__version__ = "1.0.0"
__all__ = [
    "BaseAgent",
    "AgentType", 
    "AgentCapability",
    "AgentTask",
    "AgentResponse", 
    "AgentRequestModel",
    "AgentResponseModel",
    "AgentConfig",
    "get_agent_config",
    "create_agent_app"
]