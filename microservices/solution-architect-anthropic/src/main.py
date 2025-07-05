"""
Solution Architect Anthropic Microservice

Minimal main.py using shared factory pattern for Solution Architect agent.
"""

from agent_common import create_agent_app
from solution_architect import SolutionArchitectAgent

# Define Solution Architect specific endpoints
ENDPOINTS = [
    {
        "path": "/consolidate-architecture",
        "task_type": "consolidate_architecture",
        "description": "Consolidate architecture designs from all layers"
    },
    {
        "path": "/suggest-reference-architecture", 
        "task_type": "suggest_reference_architecture",
        "description": "Suggest reference architecture based on requirements"
    },
    {
        "path": "/analyze-technology-fit",
        "task_type": "analyze_technology_fit", 
        "description": "Analyze technology fit for requirements"
    },
    {
        "path": "/generate-implementation-plan",
        "task_type": "generate_implementation_plan",
        "description": "Generate detailed implementation plan with phases and resources"
    },
    {
        "path": "/validate-solution-design",
        "task_type": "validate_solution_design",
        "description": "Validate solution design against best practices and principles"
    }
]

app = create_agent_app(SolutionArchitectAgent, "solution-architect-anthropic", ENDPOINTS)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)