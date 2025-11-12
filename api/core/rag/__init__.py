"""
Clean RAG system with Milvus vector database

A lightweight, performance-focused RAG implementation for product search and recommendations.
All modules are under 250 lines and focused on core functionality.
"""

from .embedding import EmbeddingGenerator, EmbeddingResult
from .search import ProductSearch, SearchQuery, SearchResponse
from .recommender import ProductRecommender, RecommendationType, RecommendationRequest, Recommendation
from .indexer import ProductIndexer, IndexStats

__all__ = [
    # Core embedding
    "EmbeddingGenerator",
    "EmbeddingResult",
    
    # Search functionality
    "ProductSearch",
    "SearchQuery",
    "SearchResponse",
    
    # Recommendations
    "ProductRecommender",
    "RecommendationType",
    "RecommendationRequest", 
    "Recommendation",
    
    # Indexing
    "ProductIndexer",
    "IndexStats"
]