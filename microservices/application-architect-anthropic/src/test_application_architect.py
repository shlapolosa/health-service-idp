#!/usr/bin/env python3
"""
Test cases for Application Architect Agent

Tests API design, technology stack selection, and component architecture functionality.
Validates all agent endpoints work correctly with business requirements.
"""

import asyncio
import pytest
from typing import Dict, Any, List

from application_architect import ApplicationArchitectAgent, AgentTask, BusinessRequirement

class TestApplicationArchitectAgent:
    """Test suite for Application Architect Agent functionality"""

    @pytest.fixture
    def agent(self):
        """Create Application Architect Agent instance"""
        return ApplicationArchitectAgent()

    @pytest.fixture
    def sample_requirements(self):
        """Sample business requirements for testing"""
        return [
            BusinessRequirement(
                subject="User",
                action="register",
                object="account",
                priority="high",
                category="functional"
            ),
            BusinessRequirement(
                subject="User",
                action="authenticate", 
                object="credentials",
                priority="high",
                category="functional"
            ),
            BusinessRequirement(
                subject="System",
                action="validate",
                object="input",
                priority="medium",
                category="non-functional"
            )
        ]

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        await agent.initialize()
        assert agent.agent_id is not None
        assert agent.name == "Application Architect"
        assert agent.api_design_engine is not None
        assert agent.tech_stack_selector is not None
        assert agent.component_library is not None

    @pytest.mark.asyncio
    async def test_design_api_task(self, agent, sample_requirements):
        """Test API design functionality"""
        await agent.initialize()
        
        # Convert BusinessRequirement objects to dict format
        requirements_data = [req.dict() for req in sample_requirements]
        
        task = AgentTask(
            task_id="test-api-design",
            task_type="design_api",
            payload={
                "requirements": requirements_data,
                "query": "Design an API for user management"
            }
        )
        
        response = await agent.process_task(task)
        
        assert response.success is True
        assert "api_specification" in response.result
        assert "endpoint_count" in response.result
        assert "schema_count" in response.result
        assert response.result["requirements_processed"] == len(sample_requirements)

    @pytest.mark.asyncio
    async def test_select_technology_stack_task(self, agent, sample_requirements):
        """Test technology stack selection functionality"""
        await agent.initialize()
        
        requirements_data = [req.dict() for req in sample_requirements]
        
        task = AgentTask(
            task_id="test-tech-stack",
            task_type="select_technology_stack",
            payload={
                "requirements": requirements_data,
                "query": "Select technology stack for user management service"
            }
        )
        
        response = await agent.process_task(task)
        
        assert response.success is True
        assert "recommended_stack" in response.result
        assert "justification" in response.result
        assert "requirements_processed" in response.result

    @pytest.mark.asyncio
    async def test_design_architecture_task(self, agent, sample_requirements):
        """Test component architecture design functionality"""
        await agent.initialize()
        
        requirements_data = [req.dict() for req in sample_requirements]
        
        task = AgentTask(
            task_id="test-architecture",
            task_type="design_architecture",
            payload={
                "requirements": requirements_data,
                "query": "Design component architecture"
            }
        )
        
        response = await agent.process_task(task)
        
        assert response.success is True
        assert "components" in response.result
        assert "data_flows" in response.result
        assert "integration_points" in response.result
        assert "deployment_recommendation" in response.result

    @pytest.mark.asyncio
    async def test_invalid_task_type(self, agent):
        """Test handling of invalid task types"""
        await agent.initialize()
        
        task = AgentTask(
            task_id="test-invalid",
            task_type="invalid_task",
            payload={"query": "This should fail"}
        )
        
        response = await agent.process_task(task)
        
        assert response.success is False
        assert "Unknown task type" in response.error

    @pytest.mark.asyncio 
    async def test_missing_requirements(self, agent):
        """Test handling of missing requirements"""
        await agent.initialize()
        
        task = AgentTask(
            task_id="test-no-requirements",
            task_type="design_api",
            payload={"query": "Design API without requirements"}
        )
        
        response = await agent.process_task(task)
        
        assert response.success is False
        assert "requirements are required" in response.error

if __name__ == "__main__":
    import asyncio
    
    async def run_basic_test():
        """Run a basic test to verify functionality"""
        print("🧪 Running basic Application Architect Agent test...")
        
        agent = ApplicationArchitectAgent()
        await agent.initialize()
        
        # Test requirements
        requirements = [
            {
                "subject": "User",
                "action": "register", 
                "object": "account",
                "priority": "high",
                "category": "functional"
            }
        ]
        
        task = AgentTask(
            task_id="basic-test",
            task_type="design_api",
            payload={
                "requirements": requirements,
                "query": "Design basic user registration API"
            }
        )
        
        response = await agent.process_task(task)
        
        if response.success:
            print("✅ Basic API design test passed")
            print(f"   - API endpoints: {response.result.get('endpoint_count', 0)}")
            print(f"   - Data schemas: {response.result.get('schema_count', 0)}")
        else:
            print(f"❌ Basic test failed: {response.error}")
        
        await agent.cleanup()
    
    # Run the test
    asyncio.run(run_basic_test())