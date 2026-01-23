"""
产品搜索服务

该模块提供产品搜索功能，支持基于查询和基于产品的相似搜索。
包含Redis缓存机制以优化性能。

核心功能:
- 查询驱动的产品搜索
- 基于产品的相似搜索
- 过滤器支持（类别、价格、可用性）
- Redis缓存（1小时TTL）
- 多租户隔离
"""

import hashlib
from typing import Optional, Sequence

import msgpack
from redis.asyncio import Redis

from core.rag import retrieval_service
from libs.factory import infra_registry
from utils import get_component_logger

logger = get_component_logger(__name__, "ProductSearch")


class ProductResult:
    """产品搜索结果"""

    def __init__(
        self,
        product_id: str,
        name: str,
        description: str,
        price: float,
        category: str,
        score: float,
        metadata: dict
    ):
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = price
        self.category = category
        self.score = score
        self.metadata = metadata

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "category": self.category,
            "score": self.score,
            "metadata": self.metadata
        }


class ProductSearch:
    """
    产品搜索服务

    提供产品搜索和推荐功能，支持多种搜索策略。
    """

    def __init__(self):
        """初始化ProductSearch"""
        self.cache_ttl = 3600  # 1小时
        self._redis_client: Optional[Redis] = None

    def _get_redis_client(self) -> Redis:
        """获取Redis客户端"""
        if self._redis_client is None:
            self._redis_client = infra_registry.get_cached_clients().redis
        return self._redis_client

    @staticmethod
    def _generate_cache_key(
        search_type: str,
        tenant_id: str,
        query: str,
        filters: Optional[dict] = None
    ) -> str:
        """
        生成缓存键

        参数:
            search_type: 搜索类型
            tenant_id: 租户ID
            query: 查询内容
            filters: 过滤条件

        返回:
            str: 缓存键
        """
        filter_str = str(sorted(filters.items())) if filters else ""
        content = f"{search_type}:{tenant_id}:{query}:{filter_str}"
        hash_key = hashlib.sha256(content.encode()).hexdigest()
        return f"product_search:{hash_key}"

    async def _get_cached_results(
        self,
        cache_key: str
    ) -> Optional[list[ProductResult]]:
        """
        从缓存获取搜索结果

        参数:
            cache_key: 缓存键

        返回:
            Optional[list[ProductResult]]: 产品结果列表
        """
        try:
            redis_client = self._get_redis_client()
            cached_data = await redis_client.get(cache_key)

            if cached_data:
                results_data = msgpack.unpackb(cached_data, raw=False)
                results = [
                    ProductResult(
                        product_id=r["product_id"],
                        name=r["name"],
                        description=r["description"],
                        price=r["price"],
                        category=r["category"],
                        score=r["score"],
                        metadata=r["metadata"]
                    )
                    for r in results_data
                ]
                logger.debug(f"产品搜索缓存命中: {cache_key[:16]}...")
                return results

            return None

        except Exception as e:
            logger.error(f"获取缓存产品结果失败: {e}")
            return None

    async def _cache_results(
        self,
        cache_key: str,
        results: list[ProductResult]
    ):
        """
        缓存搜索结果

        参数:
            cache_key: 缓存键
            results: 产品结果列表
        """
        try:
            redis_client = self._get_redis_client()
            results_data = [r.to_dict() for r in results]
            packed_data = msgpack.packb(results_data)

            await redis_client.set(
                cache_key,
                packed_data,
                ex=self.cache_ttl
            )
            logger.debug(f"缓存产品搜索结果: {cache_key[:16]}...")

        except Exception as e:
            logger.error(f"缓存产品搜索结果失败: {e}")

    async def search_by_query(
        self,
        tenant_id: str,
        query: str,
        top_k: int = 10,
        filters: Optional[dict] = None,
        use_cache: bool = True
    ) -> list[ProductResult]:
        """
        基于查询搜索产品

        参数:
            tenant_id: 租户ID
            query: 搜索查询
            top_k: 返回数量
            filters: 过滤条件（category, min_price, max_price, availability）
            use_cache: 是否使用缓存

        返回:
            list[ProductResult]: 产品结果列表
        """
        try:
            logger.info(f"产品搜索: {query[:50]}...")

            # 检查缓存
            if use_cache:
                cache_key = self._generate_cache_key("query", tenant_id, query, filters)
                cached_results = await self._get_cached_results(cache_key)
                if cached_results:
                    return cached_results

            # 使用混合搜索检索产品
            retrieval_results = await retrieval_service.hybrid_search(
                tenant_id=tenant_id,
                query=query,
                collection_name="products",
                index_name="products",
                top_k=top_k * 2  # 获取更多结果用于过滤
            )

            # 转换为产品结果
            products = []
            for result in retrieval_results:
                # 应用过滤器
                if filters and not self._apply_filters(result.metadata, filters):
                    continue

                product = ProductResult(
                    product_id=result.metadata.get("product_id", ""),
                    name=result.metadata.get("name", ""),
                    description=result.content,
                    price=result.metadata.get("price", 0.0),
                    category=result.metadata.get("category", ""),
                    score=result.score,
                    metadata=result.metadata
                )
                products.append(product)

                if len(products) >= top_k:
                    break

            logger.info(f"产品搜索完成: {len(products)} 个结果")

            # 缓存结果
            if use_cache and products:
                await self._cache_results(cache_key, products)

            return products

        except Exception as e:
            logger.error(f"产品搜索失败: {e}")
            return []

    async def search_similar_products(
        self,
        tenant_id: str,
        product_id: str,
        top_k: int = 10,
        use_cache: bool = True
    ) -> list[ProductResult]:
        """
        搜索相似产品

        参数:
            tenant_id: 租户ID
            product_id: 产品ID
            top_k: 返回数量
            use_cache: 是否使用缓存

        返回:
            list[ProductResult]: 相似产品列表
        """
        try:
            logger.info(f"搜索相似产品: {product_id}")

            # 检查缓存
            if use_cache:
                cache_key = self._generate_cache_key("similar", tenant_id, product_id)
                cached_results = await self._get_cached_results(cache_key)
                if cached_results:
                    return cached_results

            # 首先获取目标产品信息
            # 这里假设产品信息存储在向量数据库中
            # 实际实现中可能需要从产品服务API获取

            # 使用产品描述进行相似搜索
            # 这是一个简化实现，实际可能需要更复杂的逻辑
            query = f"product_id:{product_id}"

            retrieval_results = await retrieval_service.vector_search(
                tenant_id=tenant_id,
                query=query,
                collection_name="products",
                top_k=top_k + 1  # +1 因为会包含自己
            )

            # 转换为产品结果（排除自己）
            products = []
            for result in retrieval_results:
                result_product_id = result.metadata.get("product_id", "")

                # 跳过自己
                if result_product_id == product_id:
                    continue

                product = ProductResult(
                    product_id=result_product_id,
                    name=result.metadata.get("name", ""),
                    description=result.content,
                    price=result.metadata.get("price", 0.0),
                    category=result.metadata.get("category", ""),
                    score=result.score,
                    metadata=result.metadata
                )
                products.append(product)

                if len(products) >= top_k:
                    break

            logger.info(f"相似产品搜索完成: {len(products)} 个结果")

            # 缓存结果
            if use_cache and products:
                await self._cache_results(cache_key, products)

            return products

        except Exception as e:
            logger.error(f"相似产品搜索失败: {e}")
            return []

    def _apply_filters(
        self,
        metadata: dict,
        filters: dict
    ) -> bool:
        """
        应用过滤条件

        参数:
            metadata: 产品元数据
            filters: 过滤条件

        返回:
            bool: 是否通过过滤
        """
        # 类别过滤
        if "category" in filters:
            if metadata.get("category") != filters["category"]:
                return False

        # 价格范围过滤
        if "min_price" in filters:
            if metadata.get("price", 0) < filters["min_price"]:
                return False

        if "max_price" in filters:
            if metadata.get("price", float('inf')) > filters["max_price"]:
                return False

        # 可用性过滤
        if "availability" in filters:
            if metadata.get("availability") != filters["availability"]:
                return False

        return True

    async def search_by_category(
        self,
        tenant_id: str,
        category: str,
        top_k: int = 20,
        use_cache: bool = True
    ) -> list[ProductResult]:
        """
        按类别搜索产品

        参数:
            tenant_id: 租户ID
            category: 产品类别
            top_k: 返回数量
            use_cache: 是否使用缓存

        返回:
            list[ProductResult]: 产品结果列表
        """
        filters = {"category": category}
        return await self.search_by_query(
            tenant_id=tenant_id,
            query=category,
            top_k=top_k,
            filters=filters,
            use_cache=use_cache
        )


# 全局ProductSearch实例
product_search = ProductSearch()
