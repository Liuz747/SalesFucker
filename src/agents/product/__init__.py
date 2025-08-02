"""
Product Expert Agent Module

Provides AI-powered product recommendations and beauty expertise.
Uses modular architecture with RAG integration and fallback systems.

Architecture Components:
- ProductExpertAgent: Main orchestrating agent
- RecommendationCoordinator: Strategy coordination
- CustomerNeedsAnalyzer: Enhanced needs analysis
- ProductKnowledgeManager: Product knowledge management
- RAGRecommendationEngine: RAG-powered recommendations
- FallbackRecommendationSystem: Rule-based fallback
- RecommendationFormatter: Result formatting
"""

from .agent import ProductExpertAgent
from .recommendation_coordinator import RecommendationCoordinator
from .needs_analyzer import CustomerNeedsAnalyzer
from .product_knowledge import ProductKnowledgeManager
from .recommendation_engine import RAGRecommendationEngine
from .fallback_system import FallbackRecommendationSystem
from .recommendation_formatter import RecommendationFormatter

__all__ = [
    "ProductExpertAgent",
    "RecommendationCoordinator", 
    "CustomerNeedsAnalyzer",
    "ProductKnowledgeManager",
    "RAGRecommendationEngine",
    "FallbackRecommendationSystem",
    "RecommendationFormatter"
]