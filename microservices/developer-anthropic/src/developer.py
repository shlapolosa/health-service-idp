"""
Developer Agent - Code generation and implementation
"""

from typing import Dict, List, Any
from agent_common.base_microservice_agent import BaseMicroserviceAgent, BaseProcessor


class DevelopmentProcessor(BaseProcessor):
    """Processor for Developer tasks"""
    
    def _initialize_knowledge_base(self) -> Dict[str, Any]:
        """Initialize development knowledge base"""
        return {
            "languages": ["Python", "JavaScript", "TypeScript", "Java", "Go", "Rust"],
            "frameworks": {
                "web": ["React", "Vue", "Angular", "Express", "FastAPI", "Django"],
                "mobile": ["React Native", "Flutter", "Swift", "Kotlin"],
                "desktop": ["Electron", "Qt", "Tkinter", "JavaFX"]
            },
            "patterns": ["MVC", "MVP", "MVVM", "Observer", "Factory", "Singleton"],
            "best_practices": [
                "Write clean, readable code",
                "Follow SOLID principles", 
                "Use meaningful variable names",
                "Write comprehensive tests",
                "Document complex logic"
            ]
        }
    
    def _initialize_templates(self) -> Dict[str, str]:
        """Initialize code templates"""
        return {
            "class": "class {name}:\n    def __init__(self):\n        pass",
            "function": "def {name}({params}):\n    \"\"\"{docstring}\"\"\"\n    pass",
            "api_endpoint": "@app.{method}('/{path}')\nasync def {name}({params}):\n    pass"
        }
    
    async def generate_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code based on requirements"""
        requirements = input_data.get("requirements", input_data.get("query", ""))
        language = input_data.get("language", "Python")
        
        code_files = []
        
        if "api" in requirements.lower() or "rest" in requirements.lower():
            code_files.append({
                "filename": "main.py",
                "content": '''from fastapi import FastAPI

app = FastAPI(title="Generated API")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
''',
                "language": language
            })
        
        if "database" in requirements.lower() or "model" in requirements.lower():
            code_files.append({
                "filename": "models.py", 
                "content": '''from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
''',
                "language": language
            })
        
        return {
            "generated_files": code_files,
            "language": language,
            "total_files": len(code_files),
            "recommendations": [
                "Review generated code for business logic",
                "Add proper error handling",
                "Implement authentication if needed", 
                "Add comprehensive tests"
            ]
        }
    
    async def create_tests(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create test cases for code"""
        code = input_data.get("code", input_data.get("query", ""))
        test_type = input_data.get("test_type", "unit")
        
        test_files = [{
            "filename": "test_main.py",
            "content": '''import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
''',
            "test_framework": "pytest"
        }]
        
        return {
            "test_files": test_files,
            "test_type": test_type,
            "coverage_target": "80%",
            "test_framework": "pytest"
        }
    
    async def design_database(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Design database schema"""
        requirements = input_data.get("requirements", input_data.get("query", ""))
        
        # Extract entities from requirements
        words = requirements.lower().split()
        potential_entities = [word for word in words if word in ["user", "product", "order", "customer", "item", "account", "profile"]]
        entities = list(set(potential_entities)) or ["entity"]
        
        tables = []
        for entity in entities:
            table = {
                "name": f"{entity}s",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "name", "type": "VARCHAR(255)", "nullable": False},
                    {"name": "created_at", "type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP"},
                    {"name": "updated_at", "type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP"}
                ],
                "indexes": ["idx_name"],
                "relationships": []
            }
            tables.append(table)
        
        return {
            "database_schema": {"tables": tables, "total_tables": len(tables)},
            "recommendations": [
                "Add proper foreign key constraints",
                "Consider indexing strategy for queries",
                "Plan for data migration scripts",
                "Consider backup and recovery strategy"
            ]
        }
    
    async def implement_features(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Implement specific features"""
        feature_name = input_data.get("feature_name", "New Feature")
        requirements = input_data.get("requirements", input_data.get("query", ""))
        
        implementation_plan = {
            "feature": feature_name,
            "components": [
                {"name": "API Layer", "status": "planned", "files": ["api.py"]},
                {"name": "Business Logic", "status": "planned", "files": ["service.py"]},
                {"name": "Data Layer", "status": "planned", "files": ["repository.py"]},
                {"name": "Tests", "status": "planned", "files": ["test_feature.py"]}
            ],
            "estimated_effort": "5-8 days",
            "dependencies": [],
            "risks": ["Integration complexity", "Performance impact", "Testing coverage"]
        }
        
        return {
            "implementation_plan": implementation_plan,
            "next_steps": [
                "Create detailed technical design",
                "Set up development environment", 
                "Implement core functionality",
                "Add comprehensive tests",
                "Conduct code review"
            ]
        }


class DeveloperAgent(BaseMicroserviceAgent):
    """Developer Agent for code generation and implementation"""
    
    def __init__(self):
        super().__init__(
            agent_type="developer",
            agent_name="Developer", 
            description="Code generation and implementation"
        )
    
    def _create_processor(self) -> BaseProcessor:
        return DevelopmentProcessor()
    
    def _get_supported_task_types(self) -> List[str]:
        return ["generate_code", "create_tests", "design_database", "implement_features"]
    
    async def _generate_code(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.processor.generate_code(payload)
    
    async def _create_tests(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.processor.create_tests(payload)
    
    async def _design_database(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.processor.design_database(payload)
    
    async def _implement_features(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.processor.implement_features(payload)