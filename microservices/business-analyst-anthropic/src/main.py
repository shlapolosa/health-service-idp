"""
Business Analyst Anthropic Microservice

Minimal main.py using shared factory pattern for Business Analyst agent.
"""

from agent_common import create_agent_app
from business_analyst import BusinessAnalystAgent

# Define Business Analyst specific endpoints
ENDPOINTS = [
    {
        "path": "/analyze-requirements",
        "task_type": "analyze_requirements",
        "description": "Analyze natural language requirements and convert to structured format"
    },
    {
        "path": "/extract-entities", 
        "task_type": "extract_entities",
        "description": "Extract entities from text"
    },
    {
        "path": "/generate-user-stories",
        "task_type": "generate_user_stories", 
        "description": "Generate user stories from requirements"
    },
    {
        "path": "/assess-complexity",
        "task_type": "assess_complexity",
        "description": "Assess complexity of requirements"
    },
    {
        "path": "/validate-requirements",
        "task_type": "validate_requirements",
        "description": "Validate requirements for completeness and consistency"
    }
]

app = create_agent_app(BusinessAnalystAgent, "business-analyst-anthropic", ENDPOINTS)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
