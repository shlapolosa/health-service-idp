"""
Tests for Business Analyst Deterministic microservice
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def sample_requirements():
    """Sample requirements data"""
    return {
        "query": "User should be able to create and manage their profile",
        "parameters": {"domain": "general"}
    }


@pytest.fixture
def sample_entities_request():
    """Sample entities request"""
    return {
        "query": "The customer wants to purchase products from the online store"
    }


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "business-analyst-deterministic"


@patch('main.agent')
def test_analyze_requirements_success(mock_agent, client, sample_requirements):
    """Test successful requirements analysis"""
    # Mock agent response
    mock_response = type('Response', (), {
        'success': True,
        'result': {
            'requirements': [
                {
                    'subject': 'User',
                    'action': 'create',
                    'object': 'profile',
                    'confidence_score': 0.9
                }
            ],
            'confidence': 0.9,
            'method': 'deterministic'
        },
        'error': None,
        'metadata': {'processing_time': 0.1}
    })()
    
    mock_agent.process_task = AsyncMock(return_value=mock_response)
    
    response = client.post("/analyze-requirements", json=sample_requirements)
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data
    assert data["metadata"]["implementation"] == "deterministic"


@patch('main.agent')
def test_analyze_requirements_failure(mock_agent, client, sample_requirements):
    """Test failed requirements analysis"""
    # Mock agent failure
    mock_response = type('Response', (), {
        'success': False,
        'result': None,
        'error': 'Analysis failed',
        'metadata': {}
    })()
    
    mock_agent.process_task = AsyncMock(return_value=mock_response)
    
    response = client.post("/analyze-requirements", json=sample_requirements)
    assert response.status_code == 500


@patch('main.agent')
def test_extract_entities_success(mock_agent, client, sample_entities_request):
    """Test successful entity extraction"""
    # Mock agent response
    mock_response = type('Response', (), {
        'success': True,
        'result': {
            'entities': [
                {
                    'text': 'customer',
                    'label': 'ACTOR',
                    'confidence': 0.9
                },
                {
                    'text': 'products',
                    'label': 'OBJECT',
                    'confidence': 0.8
                }
            ],
            'entity_count': 2,
            'method': 'deterministic'
        },
        'error': None,
        'metadata': {}
    })()
    
    mock_agent.process_task = AsyncMock(return_value=mock_response)
    
    response = client.post("/extract-entities", json=sample_entities_request)
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data
    assert data["result"]["entity_count"] == 2


def test_analyze_requirements_missing_query(client):
    """Test analyze requirements with missing query"""
    response = client.post("/analyze-requirements", json={})
    assert response.status_code == 422  # Validation error


@patch('main.agent')
def test_generate_user_stories_success(mock_agent, client):
    """Test successful user story generation"""
    # Mock agent response
    mock_response = type('Response', (), {
        'success': True,
        'result': {
            'user_stories': [
                'As a User, I want to create profile so that achieve business objectives'
            ],
            'story_count': 1,
            'method': 'deterministic'
        },
        'error': None,
        'metadata': {}
    })()
    
    mock_agent.process_task = AsyncMock(return_value=mock_response)
    
    request_data = {
        "query": "Generate stories",
        "parameters": {
            "requirements": [
                {
                    "subject": "User",
                    "action": "create",
                    "object": "profile"
                }
            ]
        }
    }
    
    response = client.post("/generate-user-stories", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data
    assert data["result"]["story_count"] == 1


def test_generate_user_stories_missing_requirements(client):
    """Test user story generation with missing requirements"""
    request_data = {
        "query": "Generate stories",
        "parameters": {}
    }
    
    response = client.post("/generate-user-stories", json=request_data)
    assert response.status_code == 400


@patch('main.agent')
def test_assess_complexity_success(mock_agent, client):
    """Test successful complexity assessment"""
    # Mock agent response
    mock_response = type('Response', (), {
        'success': True,
        'result': {
            'complexity_assessments': [
                {
                    'requirement_id': 'User_create_profile',
                    'complexity': 'low',
                    'score': 1,
                    'factors': []
                }
            ],
            'overall_complexity': 'low',
            'method': 'deterministic'
        },
        'error': None,
        'metadata': {}
    })()
    
    mock_agent.process_task = AsyncMock(return_value=mock_response)
    
    request_data = {
        "query": "Assess complexity",
        "parameters": {
            "requirements": [
                {
                    "subject": "User",
                    "action": "create",
                    "object": "profile"
                }
            ]
        }
    }
    
    response = client.post("/assess-complexity", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data
    assert data["result"]["overall_complexity"] == "low"


@patch('main.agent')
def test_validate_requirements_success(mock_agent, client):
    """Test successful requirements validation"""
    # Mock agent response
    mock_response = type('Response', (), {
        'success': True,
        'result': {
            'validation_results': [
                {
                    'requirement_id': 'User_create_profile',
                    'is_valid': True,
                    'issues': [],
                    'completeness_score': 0.8,
                    'quality_score': 0.7
                }
            ],
            'valid_count': 1,
            'total_count': 1,
            'overall_valid': True,
            'method': 'deterministic'
        },
        'error': None,
        'metadata': {}
    })()
    
    mock_agent.process_task = AsyncMock(return_value=mock_response)
    
    request_data = {
        "query": "Validate requirements",
        "parameters": {
            "requirements": [
                {
                    "subject": "User",
                    "action": "create",
                    "object": "profile"
                }
            ]
        }
    }
    
    response = client.post("/validate-requirements", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data
    assert data["result"]["overall_valid"] is True


if __name__ == "__main__":
    pytest.main([__file__])