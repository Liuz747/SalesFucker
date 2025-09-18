"""
Simple product indexing with batch support
"""
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .embedding import EmbeddingGenerator
from .vector_db import MilvusDB


@dataclass
class IndexStats:
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0


class ProductIndexer:
    """Clean, fast product indexer"""
    
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self.embedding_gen = EmbeddingGenerator()
        self.vector_db = MilvusDB()
    
    async def index_products(
        self, 
        tenant_id: str, 
        products: List[Dict[str, Any]]
    ) -> IndexStats:
        """Index products in batches"""
        stats = IndexStats(total=len(products))
        
        # Process in batches
        for i in range(0, len(products), self.batch_size):
            batch = products[i:i + self.batch_size]
            batch_stats = await self._index_batch(tenant_id, batch)
            
            stats.success += batch_stats.success
            stats.failed += batch_stats.failed
            stats.skipped += batch_stats.skipped
        
        return stats
    
    async def index_single_product(
        self, 
        tenant_id: str, 
        product: Dict[str, Any]
    ) -> bool:
        """Index a single product"""
        try:
            # Generate embedding
            text = self.embedding_gen.create_product_text(product)
            embed_result = await self.embedding_gen.generate(text)
            
            # Insert to vector DB
            return await self.vector_db.insert_products(
                tenant_id=tenant_id,
                products=[product],
                embeddings=[embed_result.embedding]
            )
        except:
            return False
    
    async def _index_batch(
        self, 
        tenant_id: str, 
        products: List[Dict[str, Any]]
    ) -> IndexStats:
        """Index a batch of products"""
        stats = IndexStats(total=len(products))
        
        try:
            # Validate products
            valid_products = []
            for product in products:
                if not product.get("id"):
                    stats.skipped += 1
                    continue
                valid_products.append(product)
            
            if not valid_products:
                return stats
            
            # Generate embeddings in batch
            texts = [
                self.embedding_gen.create_product_text(p) 
                for p in valid_products
            ]
            
            embed_results = await self.embedding_gen.generate_batch(texts)
            embeddings = [r.embedding for r in embed_results]
            
            # Insert to vector database
            success = await self.vector_db.insert_products(
                tenant_id=tenant_id,
                products=valid_products,
                embeddings=embeddings
            )
            
            if success:
                stats.success = len(valid_products)
            else:
                stats.failed = len(valid_products)
                
        except Exception:
            stats.failed = len(products) - stats.skipped
        
        return stats
    
    async def delete_product(self, tenant_id: str, product_id: str) -> bool:
        """Delete a product from index"""
        return await self.vector_db.delete_product(tenant_id, product_id)
    
    async def get_index_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get indexing statistics"""
        return await self.vector_db.get_stats(tenant_id)