"""
Accountant Anthropic Microservice

Minimal main.py using shared factory pattern for Accountant agent.
"""

from agent_common import create_agent_app
from accountant import AccountantAgent

# Define Accountant specific endpoints
ENDPOINTS = [
    {
        "path": "/analyze-costs",
        "task_type": "analyze_costs",
        "description": "Analyze infrastructure and development costs"
    },
    {
        "path": "/create-budget", 
        "task_type": "create_budget",
        "description": "Create comprehensive project budget with breakdown"
    },
    {
        "path": "/calculate-roi",
        "task_type": "calculate_roi", 
        "description": "Calculate return on investment and financial benefits"
    },
    {
        "path": "/optimize-costs",
        "task_type": "optimize_costs",
        "description": "Provide cost optimization recommendations and savings"
    },
    {
        "path": "/track-expenses",
        "task_type": "track_expenses",
        "description": "Track project expenses and analyze budget variances"
    }
]

app = create_agent_app(AccountantAgent, "accountant-anthropic", ENDPOINTS)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)