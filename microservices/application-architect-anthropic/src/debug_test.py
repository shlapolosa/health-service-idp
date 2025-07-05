#!/usr/bin/env python3
"""Debug test to find the exact location of the 'id' error"""

import traceback
import asyncio
from application_architect import ApplicationArchitectAgent, AgentTask

async def debug_application_architect():
    """Debug the exact error location"""
    print("🔍 Debugging Application Architect Agent...")
    
    agent = ApplicationArchitectAgent()
    await agent.initialize()
    
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
        task_id="debug-test",
        task_type="design_api",
        payload={
            "requirements": requirements,
            "query": "Debug test"
        }
    )
    
    try:
        print("📝 Processing task...")
        response = await agent.process_task(task)
        print(f"✅ Success: {response.result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("🔍 Full traceback:")
        traceback.print_exc()
    
    await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(debug_application_architect())