"""
Configuration management for agent microservices
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from .models import AgentType, ImplementationType


@dataclass
class AgentConfig:
    """Configuration for agent microservices"""
    agent_type: AgentType
    implementation_type: ImplementationType
    service_name: str
    log_level: str = "INFO"
    port: int = 8080
    host: str = "0.0.0.0"
    
    # External service configurations
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    redis_host: Optional[str] = None
    redis_port: int = 6379
    
    # Performance configurations
    max_concurrent_tasks: int = 10
    task_timeout: int = 300  # seconds
    
    # Custom configurations
    custom_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Configure logging after initialization"""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )


def get_agent_config() -> AgentConfig:
    """Get agent configuration from environment variables"""
    
    # Required environment variables
    agent_type_str = os.getenv("AGENT_TYPE")
    if not agent_type_str:
        raise ValueError("AGENT_TYPE environment variable is required")
    
    implementation_type_str = os.getenv("IMPLEMENTATION_TYPE")
    if not implementation_type_str:
        raise ValueError("IMPLEMENTATION_TYPE environment variable is required")
    
    # Parse agent type
    try:
        agent_type = AgentType(agent_type_str)
    except ValueError:
        raise ValueError(f"Invalid AGENT_TYPE: {agent_type_str}")
    
    # Parse implementation type
    try:
        implementation_type = ImplementationType(implementation_type_str)
    except ValueError:
        raise ValueError(f"Invalid IMPLEMENTATION_TYPE: {implementation_type_str}")
    
    # Generate service name
    service_name = f"{agent_type.value}-{implementation_type.value}"
    
    return AgentConfig(
        agent_type=agent_type,
        implementation_type=implementation_type,
        service_name=service_name,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        port=int(os.getenv("PORT", "8080")),
        host=os.getenv("HOST", "0.0.0.0"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        redis_host=os.getenv("REDIS_HOST"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        max_concurrent_tasks=int(os.getenv("MAX_CONCURRENT_TASKS", "10")),
        task_timeout=int(os.getenv("TASK_TIMEOUT", "300"))
    )