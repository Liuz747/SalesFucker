"""
Milvus vector database operations
"""
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from pymilvus import (
    connections, Collection, CollectionSchema, FieldSchema, DataType,
    utility, MilvusException
)


@dataclass
class SearchResult:
    product_id: str
    score: float
    product_data: Dict[str, Any]


class MilvusDB:
    """Clean Milvus vector database interface"""
    
    def __init__(self, host: str = "localhost", port: int = 19530):
        self.host = host
        self.port = port
        self.connected = False
        
    async def connect(self):
        """Connect to Milvus"""
        if self.connected:
            return
            
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            self.connected = True
        except MilvusException as e:
            raise ConnectionError(f"Failed to connect to Milvus: {e}")
    
    def get_collection_name(self, tenant_id: str) -> str:
        """Generate tenant-specific collection name"""
        return f"products_{tenant_id}"
    
    async def create_collection(self, tenant_id: str, dim: int = 3072) -> Collection:
        """Create collection for tenant"""
        await self.connect()
        
        collection_name = self.get_collection_name(tenant_id)
        
        # Check if collection exists
        if utility.has_collection(collection_name):
            return Collection(collection_name)
        
        # Define schema
        fields = [
            FieldSchema("id", DataType.VARCHAR, max_length=100, is_primary=True),
            FieldSchema("product_id", DataType.VARCHAR, max_length=100),
            FieldSchema("tenant_id", DataType.VARCHAR, max_length=50),
            FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema("product_data", DataType.JSON),
        ]
        
        schema = CollectionSchema(fields, f"Products for tenant {tenant_id}")
        collection = Collection(collection_name, schema)
        
        # Create index
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        collection.create_index("embedding", index_params)
        
        return collection
    
    async def insert_products(
        self, 
        tenant_id: str, 
        products: List[Dict[str, Any]], 
        embeddings: List[List[float]]
    ) -> bool:
        """Insert products with embeddings"""
        collection = await self.create_collection(tenant_id)
        
        # Prepare data
        data = [
            [f"{tenant_id}_{p['id']}" for p in products],  # id
            [p["id"] for p in products],  # product_id
            [tenant_id] * len(products),  # tenant_id
            embeddings,  # embedding
            products,  # product_data
        ]
        
        try:
            collection.insert(data)
            collection.flush()
            return True
        except MilvusException:
            return False
    
    async def search_similar(
        self,
        tenant_id: str,
        query_embedding: List[float],
        top_k: int = 10,
        score_threshold: float = 0.7
    ) -> List[SearchResult]:
        """Search for similar products"""
        await self.connect()
        
        collection_name = self.get_collection_name(tenant_id)
        if not utility.has_collection(collection_name):
            return []
        
        collection = Collection(collection_name)
        collection.load()
        
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        
        try:
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=f'tenant_id == "{tenant_id}"',
                output_fields=["product_id", "product_data"]
            )
            
            search_results = []
            for hits in results:
                for hit in hits:
                    if hit.score >= score_threshold:
                        search_results.append(SearchResult(
                            product_id=hit.entity.get("product_id"),
                            score=hit.score,
                            product_data=hit.entity.get("product_data")
                        ))
            
            return search_results
            
        except MilvusException:
            return []
    
    async def delete_product(self, tenant_id: str, product_id: str) -> bool:
        """Delete a product"""
        await self.connect()
        
        collection_name = self.get_collection_name(tenant_id)
        if not utility.has_collection(collection_name):
            return False
        
        collection = Collection(collection_name)
        
        try:
            collection.delete(f'id == "{tenant_id}_{product_id}"')
            return True
        except MilvusException:
            return False
    
    async def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get collection statistics"""
        await self.connect()
        
        collection_name = self.get_collection_name(tenant_id)
        if not utility.has_collection(collection_name):
            return {}
        
        collection = Collection(collection_name)
        
        try:
            return {
                "total_entities": collection.num_entities,
                "collection_name": collection_name,
                "tenant_id": tenant_id
            }
        except MilvusException:
            return {}