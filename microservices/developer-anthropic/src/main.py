"""
Developer Anthropic Microservice

Minimal main.py using shared factory pattern for Developer agent.
"""

from agent_common import create_agent_app
from developer import DeveloperAgent

# Define Developer specific endpoints
ENDPOINTS = [
    {
        "path": "/generate-code",
        "task_type": "generate_code",
        "description": "Generate code implementation from requirements"
    },
    {
        "path": "/create-tests", 
        "task_type": "create_tests",
        "description": "Create comprehensive test suite for code"
    },
    {
        "path": "/design-database",
        "task_type": "design_database", 
        "description": "Design database schema from requirements"
    },
    {
        "path": "/implement-features",
        "task_type": "implement_features",
        "description": "Implement specific features from user stories"
    },
    {
        "path": "/review-code",
        "task_type": "review_code",
        "description": "Review code for quality, security, and best practices"
    }
]

app = create_agent_app(DeveloperAgent, "developer-anthropic", ENDPOINTS)

# Main entry point for development
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)