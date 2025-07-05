#!/usr/bin/env python3
"""
Local test script for business analyst microservice
"""

import os
import sys
import asyncio
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from business_analyst import BusinessAnalystAgent
from models import BusinessRequirement

async def test_business_analyst():
    """Test the business analyst agent locally"""
    
    print("🧪 Testing Business Analyst Agent...")
    
    # Create agent
    agent = BusinessAnalystAgent()
    await agent.initialize()
    
    print("✅ Agent initialized successfully")
    
    # Test requirements analysis
    test_requirements = "User should be able to create and manage their profile and update billing information"
    
    print(f"📝 Testing requirements analysis with: '{test_requirements}'")
    
    task_payload = {
        "requirements_text": test_requirements,
        "domain": "ecommerce"
    }
    
    from business_analyst import AgentTask
    task = AgentTask(
        task_type="analyze_requirements",
        payload=task_payload
    )
    
    response = await agent.process_task(task)
    
    if response.success:
        print("✅ Requirements analysis successful!")
        print(f"📊 Processing time: {response.processing_time:.2f}s")
        
        # Print results
        result = response.result
        print(f"📋 Found {len(result.get('requirements', []))} requirements")
        print(f"🏷️  Found {len(result.get('entities', []))} entities")
        print(f"🎯 Confidence: {result.get('confidence', 0):.2f}")
        
        # Show first requirement if any
        requirements = result.get('requirements', [])
        if requirements:
            req = requirements[0]
            print(f"📌 First requirement: {req.get('subject', '')} {req.get('action', '')} {req.get('object', '')}")
    else:
        print(f"❌ Requirements analysis failed: {response.error}")
    
    # Test entity extraction
    print(f"\n🏷️  Testing entity extraction...")
    
    entity_task = AgentTask(
        task_type="extract_entities",
        payload={"text": "The customer wants to update their billing address and payment method"}
    )
    
    entity_response = await agent.process_task(entity_task)
    
    if entity_response.success:
        entities = entity_response.result.get('entities', [])
        print(f"✅ Found {len(entities)} entities")
        for entity in entities[:3]:  # Show first 3
            print(f"   - {entity.get('text', '')} ({entity.get('label', '')})")
    else:
        print(f"❌ Entity extraction failed: {entity_response.error}")
    
    await agent.cleanup()
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    # Set environment variables
    os.environ["AGENT_TYPE"] = "business-analyst"
    os.environ["IMPLEMENTATION_TYPE"] = "anthropic"
    os.environ["LOG_LEVEL"] = "INFO"
    
    asyncio.run(test_business_analyst())