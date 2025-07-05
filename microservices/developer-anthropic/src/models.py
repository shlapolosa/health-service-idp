"""
Pydantic models for Developer microservice
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from dataclasses import dataclass


class AgentRequestModel(BaseModel):
    """Standard agent request model"""
    query: str = Field(..., description="The query or task for the agent")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Additional parameters")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Context information")


class AgentResponseModel(BaseModel):
    """Standard agent response model"""
    result: Dict[str, Any] = Field(..., description="The result data")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Response metadata")


@dataclass
class CodeFile:
    """Generated code file"""
    filename: str
    content: str
    language: str = "Python"
    framework: str = ""
    
    def dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "content": self.content,
            "language": self.language,
            "framework": self.framework
        }


@dataclass
class TestFile:
    """Generated test file"""
    filename: str
    content: str
    test_framework: str = "pytest"
    coverage_target: str = "80%"
    
    def dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "content": self.content,
            "test_framework": self.test_framework,
            "coverage_target": self.coverage_target
        }


@dataclass
class DatabaseTable:
    """Database table definition"""
    name: str
    columns: List[Dict[str, Any]]
    indexes: List[str] = None
    relationships: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.indexes is None:
            self.indexes = []
        if self.relationships is None:
            self.relationships = []
    
    def dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "columns": self.columns,
            "indexes": self.indexes,
            "relationships": self.relationships
        }


@dataclass
class DeveloperResult:
    """Developer processing result"""
    success: bool
    data: Dict[str, Any]
    confidence: float = 0.8
    processing_time: float = 0.1
    
    def dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "confidence": self.confidence,
            "processing_time": self.processing_time
        }