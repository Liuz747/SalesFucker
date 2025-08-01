"""
Core search functionality with caching
"""
import asyncio
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .embedding import EmbeddingGenerator, EmbeddingResult
from .vector_db import MilvusDB, SearchResult
from src.utils.redis_client import get_redis_client


@dataclass
class SearchQuery:
    text: str
    tenant_id: str
    filters: Dict[str, Any] = None
    top_k: int = 10
    min_score: float = 0.7


@dataclass
class SearchResponse:
    results: List[SearchResult]
    query_embedding: List[float]
    cache_hit: bool = False


class ProductSearch:
    """Fast product search with intelligent caching"""
    
    def __init__(self, cache_ttl: int = 300):
        self.embedding_gen = EmbeddingGenerator()
        self.vector_db = MilvusDB()
        self.redis_client = get_redis_client()
        self.cache_ttl = cache_ttl
    
    async def search(self, query: SearchQuery) -> SearchResponse:
        """Main search interface"""
        # Check result cache
        cache_key = self._get_cache_key(query)
        if cached := await self._get_cached_results(cache_key):
            return SearchResponse(
                results=cached["results"],
                query_embedding=cached["embedding"],
                cache_hit=True
            )
        
        # Generate embedding
        embed_result = await self.embedding_gen.generate(query.text)
        
        # Search vector database
        results = await self.vector_db.search_similar(
            tenant_id=query.tenant_id,
            query_embedding=embed_result.embedding,
            top_k=query.top_k,
            score_threshold=query.min_score
        )
        
        # Apply additional filters
        if query.filters:
            results = self._apply_filters(results, query.filters)
        
        # Cache results
        await self._cache_results(cache_key, results, embed_result.embedding)
        
        return SearchResponse(
            results=results,
            query_embedding=embed_result.embedding,
            cache_hit=False
        )
    
    async def search_by_product(
        self, 
        tenant_id: str, 
        product_data: Dict[str, Any], 
        top_k: int = 10
    ) -> List[SearchResult]:
        """Find products similar to given product"""
        # Create searchable text
        text = self.embedding_gen.create_product_text(product_data)
        
        query = SearchQuery(
            text=text,
            tenant_id=tenant_id,
            top_k=top_k + 1  # +1 to exclude self
        )
        
        response = await self.search(query)
        
        # Filter out the same product
        product_id = product_data.get("id")
        return [r for r in response.results if r.product_id != product_id]
    
    def _apply_filters(
        self, 
        results: List[SearchResult], 
        filters: Dict[str, Any]
    ) -> List[SearchResult]:
        """Apply post-search filters"""
        filtered = []
        
        for result in results:
            product = result.product_data
            keep = True
            
            for field, value in filters.items():
                if field not in product:
                    continue
                    
                product_value = product[field]
                
                if isinstance(value, list):
                    if product_value not in value:
                        keep = False
                        break
                elif isinstance(value, dict):
                    # Range filter
                    if "min" in value and product_value < value["min"]:
                        keep = False
                        break
                    if "max" in value and product_value > value["max"]:
                        keep = False
                        break
                else:
                    if product_value != value:
                        keep = False
                        break
            
            if keep:
                filtered.append(result)
        
        return filtered
    
    def _get_cache_key(self, query: SearchQuery) -> str:
        """Generate cache key for query"""
        key_parts = [
            query.text,
            query.tenant_id,
            str(query.top_k),
            str(query.min_score),
            str(sorted(query.filters.items()) if query.filters else "")
        ]
        key_str = "|".join(key_parts)
        return f"search:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    async def _get_cached_results(self, cache_key: str) -> Optional[Dict]:
        """Get cached search results"""
        try:
            data = await self.redis_client.get(cache_key)
            return eval(data) if data else None
        except:
            return None
    
    async def _cache_results(
        self, 
        cache_key: str, 
        results: List[SearchResult], 
        embedding: List[float]
    ):
        """Cache search results"""
        try:
            cache_data = {
                "results": [
                    {
                        "product_id": r.product_id,
                        "score": r.score,
                        "product_data": r.product_data
                    }
                    for r in results
                ],
                "embedding": embedding
            }
            await self.redis_client.setex(
                cache_key, self.cache_ttl, str(cache_data)
            )
        except:
            pass  # Continue without caching