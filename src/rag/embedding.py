"""
Clean embedding generation with minimal dependencies
"""
import asyncio
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.infra.cache import get_redis_client
from src.llm import get_multi_llm_client


@dataclass
class EmbeddingResult:
    embedding: List[float]
    cache_hit: bool = False


class EmbeddingGenerator:
    """Simple, fast embedding generation with Redis caching"""
    
    def __init__(self, model: str = "text-embedding-3-large", cache_ttl: int = 3600):
        self.model = model
        self.cache_ttl = cache_ttl
        self.llm_client = get_multi_llm_client()
        self.redis_client = get_redis_client()
    
    async def generate(self, text: str) -> EmbeddingResult:
        """Generate embedding with caching"""
        cache_key = f"emb:{hashlib.md5(text.encode()).hexdigest()}"
        
        # Try cache first
        if cached := await self._get_cached(cache_key):
            return EmbeddingResult(embedding=cached, cache_hit=True)
        
        # Generate new embedding
        response = await self.llm_client.embeddings.create(
            input=text, model=self.model
        )
        embedding = response.data[0].embedding
        
        # Cache result
        await self._cache_embedding(cache_key, embedding)
        
        return EmbeddingResult(embedding=embedding, cache_hit=False)
    
    async def generate_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Generate embeddings in batch"""
        return await asyncio.gather(*[self.generate(text) for text in texts])
    
    def create_product_text(self, product: Dict[str, Any]) -> str:
        """Create optimized searchable text from product data"""
        parts = []
        
        # Core info
        for field in ["name", "chinese_name", "brand", "category"]:
            if value := product.get(field):
                parts.append(str(value))
        
        # Features
        for field in ["benefits", "key_ingredients", "skin_type_suitability"]:
            if value := product.get(field):
                parts.append(str(value))
        
        return " ".join(parts)
    
    async def _get_cached(self, key: str) -> Optional[List[float]]:
        """Get cached embedding"""
        try:
            data = await self.redis_client.get(key)
            return eval(data) if data else None
        except:
            return None
    
    async def _cache_embedding(self, key: str, embedding: List[float]):
        """Cache embedding"""
        try:
            await self.redis_client.setex(key, self.cache_ttl, str(embedding))
        except:
            pass  # Continue without caching