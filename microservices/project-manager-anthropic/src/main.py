"""
Project Manager Anthropic Microservice

Minimal main.py using shared factory pattern for Project Manager agent.
"""

from agent_common import create_agent_app
from project_manager import ProjectManagerAgent

# Define Project Manager specific endpoints
ENDPOINTS = [
    {
        "path": "/create-project-plan",
        "task_type": "create_project_plan",
        "description": "Create comprehensive project plan with phases and timeline"
    },
    {
        "path": "/create-work-packages", 
        "task_type": "create_work_packages",
        "description": "Create detailed work packages from requirements"
    },
    {
        "path": "/track-progress",
        "task_type": "track_progress", 
        "description": "Track project progress and provide analytics"
    },
    {
        "path": "/manage-risks",
        "task_type": "manage_risks",
        "description": "Manage project risks and mitigation strategies"
    },
    {
        "path": "/allocate-resources",
        "task_type": "allocate_resources",
        "description": "Allocate resources to work packages and timeline"
    }
]

app = create_agent_app(ProjectManagerAgent, "project-manager-anthropic", ENDPOINTS)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)