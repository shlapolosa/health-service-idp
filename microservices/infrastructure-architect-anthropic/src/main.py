"""
Infrastructure Architect Anthropic Microservice

Minimal main.py using shared factory pattern for Infrastructure Architect agent.
"""

from agent_common import create_agent_app
from infrastructure_architect import InfrastructureArchitectAgent

# Define Infrastructure Architect specific endpoints
ENDPOINTS = [
    {
        "path": "/design-infrastructure",
        "task_type": "design_infrastructure",
        "description": "Design infrastructure architecture from application requirements"
    },
    {
        "path": "/plan-capacity", 
        "task_type": "plan_capacity",
        "description": "Plan infrastructure capacity based on expected load"
    },
    {
        "path": "/recommend-deployment",
        "task_type": "recommend_deployment", 
        "description": "Recommend deployment strategy and CI/CD approach"
    },
    {
        "path": "/estimate-costs",
        "task_type": "estimate_costs",
        "description": "Estimate infrastructure costs for requirements"
    },
    {
        "path": "/design-security",
        "task_type": "design_security",
        "description": "Design security architecture and compliance framework"
    }
]

app = create_agent_app(InfrastructureArchitectAgent, "infrastructure-architect-anthropic", ENDPOINTS)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)