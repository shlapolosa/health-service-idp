"""
Application Architect Anthropic Microservice

Minimal main.py using shared factory pattern for Application Architect agent.
"""

from agent_common import create_agent_app
from application_architect import ApplicationArchitectAgent

# Define Application Architect specific endpoints
ENDPOINTS = [
    {
        "path": "/design-api",
        "task_type": "design_api",
        "description": "Design API specification from business requirements"
    },
    {
        "path": "/select-technology-stack", 
        "task_type": "select_technology_stack",
        "description": "Select appropriate technology stack for requirements"
    },
    {
        "path": "/design-architecture",
        "task_type": "design_architecture", 
        "description": "Design high-level application architecture"
    },
    {
        "path": "/recommend-components",
        "task_type": "recommend_components",
        "description": "Recommend architectural components for requirements"
    },
    {
        "path": "/design-integration",
        "task_type": "design_integration",
        "description": "Design integration approach for requirements"
    }
]

app = create_agent_app(ApplicationArchitectAgent, "application-architect-anthropic", ENDPOINTS)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)