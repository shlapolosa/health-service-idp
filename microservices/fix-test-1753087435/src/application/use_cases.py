"""Application use cases following CLAUDE.md principles"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar('T')

class UseCase(ABC, Generic[T]):
    """Base use case following CLAUDE.md patterns"""
    
    @abstractmethod
    async def execute(self, request: T) -> dict:
        pass
