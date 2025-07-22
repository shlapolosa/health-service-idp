"""Domain models following CLAUDE.md Onion Architecture"""
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel

class Entity(BaseModel):
    """Base domain entity"""
    id: Optional[str] = None

class DomainService(ABC):
    """Base domain service interface"""
    pass
