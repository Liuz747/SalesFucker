"""
产品搜索和推荐模块

该模块提供产品搜索和推荐功能。
"""

from .product_recommender import (
    ProductRecommender,
    RecommendationStrategy,
    product_recommender
)
from .product_search import ProductResult, ProductSearch, product_search

__all__ = [
    "ProductRecommender",
    "ProductResult",
    "ProductSearch",
    "RecommendationStrategy",
    "product_recommender",
    "product_search"
]
