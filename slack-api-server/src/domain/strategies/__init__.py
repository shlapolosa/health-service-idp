"""Pattern-based component handling strategies."""

from .base import PatternHandler, HandlerContext, HandlerResult
from .pattern1_foundational import Pattern1FoundationalHandler
from .pattern2_compositional import Pattern2CompositionalHandler
from .pattern3_infrastructural import Pattern3InfrastructuralHandler
from .orchestrator import PatternOrchestrator

__all__ = [
    "PatternHandler",
    "HandlerContext", 
    "HandlerResult",
    "Pattern1FoundationalHandler",
    "Pattern2CompositionalHandler",
    "Pattern3InfrastructuralHandler",
    "PatternOrchestrator"
]