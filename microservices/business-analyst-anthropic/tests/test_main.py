"""
Tests for Business Analyst Anthropic microservice
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "business-analyst-anthropic"


def test_analyze_requirements():
    """Test requirements analysis endpoint"""
    test_request = {
        "query": "User should be able to create and manage their profile",
        "parameters": {
            "domain": "ecommerce"
        }
    }
    
    response = client.post("/analyze-requirements", json=test_request)
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data
    assert "metadata" in data
    assert data["metadata"]["agent_type"] == "business-analyst"


def test_extract_entities():
    """Test entity extraction endpoint"""
    test_request = {
        "query": "The customer wants to update their billing address and payment method"
    }
    
    response = client.post("/extract-entities", json=test_request)
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data
    assert "entities" in data["result"]


def test_generate_user_stories():
    """Test user story generation endpoint"""
    test_requirements = [{
        "subject": "user",
        "action": "create",
        "object": "profile",
        "priority": "high",
        "category": "functional",
        "rationale": "to manage personal information",
        "acceptance_criteria": ["Profile form is accessible", "Data is validated"],
        "stakeholders": ["user", "admin"],
        "business_value": "improves user experience",
        "complexity": "medium",
        "entities": [],
        "confidence_score": 0.8
    }]
    
    test_request = {
        "query": "",
        "parameters": {
            "requirements": test_requirements
        }
    }
    
    response = client.post("/generate-user-stories", json=test_request)
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data
    assert "user_stories" in data["result"]


def test_invalid_request():
    """Test invalid request handling"""
    response = client.post("/analyze-requirements", json={})
    assert response.status_code == 422  # Validation error