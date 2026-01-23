"""
检索服务

该模块提供统一的检索接口，支持多种检索策略。
包括向量搜索（Milvus）、关键词搜索（Elasticsearch）和混合搜索。

核心功能:
- 向量搜索（语义相似度）
- 关键词搜索（全文检索）
- 混合搜索（加权组合）
- 结果去重和过滤
- 结果缓存（Redis）
"""

import hashlib
import json
from typing import Optional, Sequence

import msgpack
from elasticsearch import AsyncElasticsearch
from langfuse.decorators import observe
from pymilvus import MilvusClient
from redis.asyncio import Redis

from config.rag_config import rag_config
from core.rag.embedding_service import embedding_service
from infra.ops.milvus_client import get_milvus_connection
from libs.factory import infra_registry
from utils import get_component_logger

logger = get_component_logger(__name__, "RetrievalService")


class RetrievalResult:
    """检索结果"""

    def __init__(
        self,
        content: str,
        score: float,
        metadata: dict,
        source: str = "unknown"
    ):
        self.content = content
        self.score = score
        self.metadata = metadata
        self.source = source  # "vector", "keyword", "hybrid"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
            "source": self.source
        }


class RetrievalService:
    """
    检索服务

    提供多种检索策略的统一接口。
    支持向量搜索、关键词搜索和混合搜索。
    """

    def __init__(self):
        """初始化RetrievalService"""
        self.default_top_k = rag_config.DEFAULT_TOP_K
        self.min_similarity = rag_config.MIN_SIMILARITY_THRESHOLD
        self.cache_ttl = rag_config.RETRIEVAL_CACHE_TTL
        self.vector_weight = rag_config.VECTOR_SEARCH_WEIGHT
        self.keyword_weight = rag_config.KEYWORD_SEARCH_WEIGHT

        # 客户端将在使用时初始化
        self._milvus_client: Optional[MilvusClient] = None
        self._es_client: Optional[AsyncElasticsearch] = None
        self._redis_client: Optional[Redis] = None

    async def _get_milvus_client(self) -> MilvusClient:
        """获取Milvus客户端"""
        if self._milvus_client is None:
            self._milvus_client = await get_milvus_connection()
        return self._milvus_client

    def _get_es_client(self) -> AsyncElasticsearch:
        """获取Elasticsearch客户端"""
        if self._es_client is None:
            self._es_client = infra_registry.get_cached_clients().elasticsearch
        return self._es_client

    def _get_redis_client(self) -> Redis:
        """获取Redis客户端"""
        if self._redis_client is None:
            self._redis_client = infra_registry.get_cached_clients().redis
        return self._redis_client

    @staticmethod
    def _generate_cache_key(
        query: str,
        retrieval_type: str,
        tenant_id: str,
        top_k: int
    ) -> str:
        """
        生成缓存键

        参数:
            query: 查询文本
            retrieval_type: 检索类型
            tenant_id: 租户ID
            top_k: 返回数量

        返回:
            str: 缓存键
        """
        content = f"{retrieval_type}:{tenant_id}:{query}:{top_k}"
        hash_key = hashlib.sha256(content.encode()).hexdigest()
        return f"retrieval:{hash_key}"

    async def _get_cached_results(
        self,
        cache_key: str
    ) -> Optional[list[RetrievalResult]]:
        """
        从缓存获取检索结果

        参数:
            cache_key: 缓存键

        返回:
            Optional[list[RetrievalResult]]: 检索结果列表
        """
        try:
            redis_client = self._get_redis_client()
            cached_data = await redis_client.get(cache_key)

            if cached_data:
                results_data = msgpack.unpackb(cached_data, raw=False)
                results = [
                    RetrievalResult(
                        content=r["content"],
                        score=r["score"],
                        metadata=r["metadata"],
                        source=r["source"]
                    )
                    for r in results_data
                ]
                logger.debug(f"缓存命中: {cache_key[:16]}...")
                return results

            return None

        except Exception as e:
            logger.error(f"获取缓存结果失败: {e}")
            return None

    async def _cache_results(
        self,
        cache_key: str,
        results: list[RetrievalResult]
    ):
        """
        缓存检索结果

        参数:
            cache_key: 缓存键
            results: 检索结果列表
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
            logger.debug(f"缓存检索结果: {cache_key[:16]}...")

        except Exception as e:
            logger.error(f"缓存检索结果失败: {e}")

    @observe(name="vector_search")
    async def vector_search(
        self,
        tenant_id: str,
        query: str,
        collection_name: str = "documents",
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
        use_cache: bool = True
    ) -> list[RetrievalResult]:
        """
        向量搜索（语义相似度）

        参数:
            tenant_id: 租户ID
            query: 查询文本
            collection_name: Milvus集合名称
            top_k: 返回数量
            min_score: 最小相似度阈值
            use_cache: 是否使用缓存

        返回:
            list[RetrievalResult]: 检索结果列表
        """
        try:
            top_k = top_k or self.default_top_k
            min_score = min_score or self.min_similarity

            # 检查缓存
            if use_cache:
                cache_key = self._generate_cache_key(query, "vector", tenant_id, top_k)
                cached_results = await self._get_cached_results(cache_key)
                if cached_results:
                    return cached_results

            # 生成查询embedding
            logger.debug(f"向量搜索: {query[:50]}...")
            query_embedding = await embedding_service.generate_embedding(query)

            # Milvus搜索
            milvus_client = await self._get_milvus_client()

            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }

            search_results = milvus_client.search(
                collection_name=collection_name,
                data=[query_embedding],
                filter=f'tenant_id == "{tenant_id}"',
                limit=top_k,
                search_params=search_params,
                output_fields=["content", "metadata", "tenant_id"]
            )

            # 转换结果
            results = []
            for hits in search_results:
                for hit in hits:
                    if hit["distance"] >= min_score:
                        result = RetrievalResult(
                            content=hit["entity"].get("content", ""),
                            score=float(hit["distance"]),
                            metadata=hit["entity"].get("metadata", {}),
                            source="vector"
                        )
                        results.append(result)

            logger.info(f"向量搜索完成: {len(results)} 个结果")

            # 缓存结果
            if use_cache and results:
                await self._cache_results(cache_key, results)

            return results

        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []

    @observe(name="keyword_search")
    async def keyword_search(
        self,
        tenant_id: str,
        query: str,
        index_name: str = "documents",
        top_k: Optional[int] = None,
        use_cache: bool = True
    ) -> list[RetrievalResult]:
        """
        关键词搜索（全文检索）

        参数:
            tenant_id: 租户ID
            query: 查询文本
            index_name: Elasticsearch索引名称
            top_k: 返回数量
            use_cache: 是否使用缓存

        返回:
            list[RetrievalResult]: 检索结果列表
        """
        try:
            top_k = top_k or self.default_top_k

            # 检查缓存
            if use_cache:
                cache_key = self._generate_cache_key(query, "keyword", tenant_id, top_k)
                cached_results = await self._get_cached_results(cache_key)
                if cached_results:
                    return cached_results

            # Elasticsearch搜索
            logger.debug(f"关键词搜索: {query[:50]}...")
            es_client = self._get_es_client()

            search_query = {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["content^2", "metadata.title"],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"tenant_id": tenant_id}}
                    ]
                }
            }

            response = await es_client.search(
                index=index_name,
                query=search_query,
                size=top_k,
                _source=["content", "metadata", "tenant_id"]
            )

            # 转换结果
            results = []
            for hit in response["hits"]["hits"]:
                result = RetrievalResult(
                    content=hit["_source"].get("content", ""),
                    score=float(hit["_score"]),
                    metadata=hit["_source"].get("metadata", {}),
                    source="keyword"
                )
                results.append(result)

            logger.info(f"关键词搜索完成: {len(results)} 个结果")

            # 缓存结果
            if use_cache and results:
                await self._cache_results(cache_key, results)

            return results

        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            return []

    @observe(name="hybrid_search")
    async def hybrid_search(
        self,
        tenant_id: str,
        query: str,
        collection_name: str = "documents",
        index_name: str = "documents",
        top_k: Optional[int] = None,
        vector_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
        use_cache: bool = True
    ) -> list[RetrievalResult]:
        """
        混合搜索（向量 + 关键词）

        参数:
            tenant_id: 租户ID
            query: 查询文本
            collection_name: Milvus集合名称
            index_name: Elasticsearch索引名称
            top_k: 返回数量
            vector_weight: 向量搜索权重
            keyword_weight: 关键词搜索权重
            use_cache: 是否使用缓存

        返回:
            list[RetrievalResult]: 检索结果列表
        """
        try:
            top_k = top_k or self.default_top_k
            vector_weight = vector_weight or self.vector_weight
            keyword_weight = keyword_weight or self.keyword_weight

            # 检查缓存
            if use_cache:
                cache_key = self._generate_cache_key(query, "hybrid", tenant_id, top_k)
                cached_results = await self._get_cached_results(cache_key)
                if cached_results:
                    return cached_results

            logger.info(f"混合搜索: {query[:50]}...")

            # 并行执行向量搜索和关键词搜索
            import asyncio
            vector_results, keyword_results = await asyncio.gather(
                self.vector_search(tenant_id, query, collection_name, top_k * 2, use_cache=False),
                self.keyword_search(tenant_id, query, index_name, top_k * 2, use_cache=False)
            )

            # 合并和重排序结果
            results = self._merge_results(
                vector_results,
                keyword_results,
                vector_weight,
                keyword_weight
            )

            # 去重
            results = self._deduplicate_results(results)

            # 取top_k
            results = results[:top_k]

            logger.info(f"混合搜索完成: {len(results)} 个结果")

            # 缓存结果
            if use_cache and results:
                await self._cache_results(cache_key, results)

            return results

        except Exception as e:
            logger.error(f"混合搜索失败: {e}")
            return []

    def _merge_results(
        self,
        vector_results: list[RetrievalResult],
        keyword_results: list[RetrievalResult],
        vector_weight: float,
        keyword_weight: float
    ) -> list[RetrievalResult]:
        """
        合并向量和关键词搜索结果

        参数:
            vector_results: 向量搜索结果
            keyword_results: 关键词搜索结果
            vector_weight: 向量权重
            keyword_weight: 关键词权重

        返回:
            list[RetrievalResult]: 合并后的结果
        """
        # 归一化分数
        vector_scores = [r.score for r in vector_results] if vector_results else [0]
        keyword_scores = [r.score for r in keyword_results] if keyword_results else [0]

        max_vector_score = max(vector_scores) if vector_scores else 1
        max_keyword_score = max(keyword_scores) if keyword_scores else 1

        # 创建内容到结果的映射
        content_to_result = {}

        # 处理向量结果
        for result in vector_results:
            normalized_score = (result.score / max_vector_score) * vector_weight
            content_key = result.content[:100]  # 使用前100字符作为键

            if content_key not in content_to_result:
                content_to_result[content_key] = RetrievalResult(
                    content=result.content,
                    score=normalized_score,
                    metadata=result.metadata,
                    source="hybrid"
                )
            else:
                content_to_result[content_key].score += normalized_score

        # 处理关键词结果
        for result in keyword_results:
            normalized_score = (result.score / max_keyword_score) * keyword_weight
            content_key = result.content[:100]

            if content_key not in content_to_result:
                content_to_result[content_key] = RetrievalResult(
                    content=result.content,
                    score=normalized_score,
                    metadata=result.metadata,
                    source="hybrid"
                )
            else:
                content_to_result[content_key].score += normalized_score

        # 按分数排序
        merged_results = sorted(
            content_to_result.values(),
            key=lambda x: x.score,
            reverse=True
        )

        return merged_results

    def _deduplicate_results(
        self,
        results: list[RetrievalResult]
    ) -> list[RetrievalResult]:
        """
        去重检索结果

        参数:
            results: 检索结果列表

        返回:
            list[RetrievalResult]: 去重后的结果
        """
        seen_content = set()
        deduplicated = []

        for result in results:
            content_key = result.content[:100]
            if content_key not in seen_content:
                seen_content.add(content_key)
                deduplicated.append(result)

        logger.debug(f"去重: {len(results)} -> {len(deduplicated)}")
        return deduplicated

    @observe(name="conversation_aware_search")
    async def conversation_aware_search(
        self,
        tenant_id: str,
        query: str,
        conversation_history: Optional[Sequence] = None,
        collection_name: str = "documents",
        index_name: str = "documents",
        top_k: Optional[int] = None,
        use_cache: bool = True
    ) -> list[RetrievalResult]:
        """
        对话感知的检索

        使用对话历史上下文增强查询，提供更准确的检索结果。

        参数:
            tenant_id: 租户ID
            query: 查询文本
            conversation_history: 对话历史消息列表
            collection_name: Milvus集合名称
            index_name: Elasticsearch索引名称
            top_k: 返回数量
            use_cache: 是否使用缓存

        返回:
            list[RetrievalResult]: 检索结果列表
        """
        try:
            if top_k is None:
                top_k = self.default_top_k

            logger.info(f"对话感知检索: {query[:50]}...")

            # 如果没有对话历史，使用普通混合搜索
            if not conversation_history or len(conversation_history) == 0:
                logger.debug("无对话历史，使用普通混合搜索")
                return await self.hybrid_search(
                    tenant_id=tenant_id,
                    query=query,
                    collection_name=collection_name,
                    index_name=index_name,
                    top_k=top_k,
                    use_cache=use_cache
                )

            # 提取对话上下文
            from core.rag.context import conversation_context

            context = conversation_context.extract_context(
                conversation_history=conversation_history,
                current_query=query
            )

            # 使用上下文增强查询
            enhanced_query = conversation_context.enhance_query(query, context)

            logger.debug(f"查询增强: {query} -> {enhanced_query[:100]}...")

            # 执行混合搜索
            results = await self.hybrid_search(
                tenant_id=tenant_id,
                query=enhanced_query,
                collection_name=collection_name,
                index_name=index_name,
                top_k=top_k * 2,  # 获取更多结果用于过滤
                use_cache=use_cache
            )

            # 根据上下文过滤和重排结果
            filtered_results = self._filter_by_context(results, context)

            # 取top_k
            filtered_results = filtered_results[:top_k]

            logger.info(f"对话感知检索完成: {len(filtered_results)} 个结果")

            return filtered_results

        except Exception as e:
            logger.error(f"对话感知检索失败: {e}")
            # 降级到普通混合搜索
            return await self.hybrid_search(
                tenant_id=tenant_id,
                query=query,
                collection_name=collection_name,
                index_name=index_name,
                top_k=top_k,
                use_cache=use_cache
            )

    def _filter_by_context(
        self,
        results: list[RetrievalResult],
        context: dict
    ) -> list[RetrievalResult]:
        """
        根据对话上下文过滤和重排结果

        参数:
            results: 检索结果列表
            context: 对话上下文

        返回:
            list[RetrievalResult]: 过滤后的结果
        """
        try:
            # 提取上下文信息
            entities = context.get("entities", [])
            preferences = context.get("preferences", [])
            constraints = context.get("constraints", {})

            # 如果没有上下文信息，直接返回原结果
            if not entities and not preferences and not constraints:
                return results

            # 为每个结果计算上下文相关性分数
            scored_results = []
            for result in results:
                context_score = 0.0
                content_lower = result.content.lower()

                # 实体匹配加分
                for entity in entities:
                    entity_value = entity.get("value", "").lower()
                    if entity_value in content_lower:
                        context_score += 0.2

                # 正面偏好加分
                for preference in preferences:
                    if preference.startswith("positive:"):
                        pref_text = preference.split(":", 1)[1].lower()
                        # 提取偏好中的关键词
                        pref_keywords = [w for w in pref_text.split() if len(w) > 1]
                        for keyword in pref_keywords:
                            if keyword in content_lower:
                                context_score += 0.1

                # 负面偏好减分
                for preference in preferences:
                    if preference.startswith("negative:"):
                        pref_text = preference.split(":", 1)[1].lower()
                        pref_keywords = [w for w in pref_text.split() if len(w) > 1]
                        for keyword in pref_keywords:
                            if keyword in content_lower:
                                context_score -= 0.15

                # 价格敏感约束
                if constraints.get("price_sensitive"):
                    # 如果结果中提到价格相关信息，加分
                    price_keywords = ["价格", "优惠", "折扣", "便宜", "实惠"]
                    for keyword in price_keywords:
                        if keyword in content_lower:
                            context_score += 0.1
                            break

                # 时间敏感约束
                if constraints.get("time_sensitive"):
                    # 如果结果中提到时效相关信息，加分
                    time_keywords = ["快速", "立即", "马上", "现货", "当天"]
                    for keyword in time_keywords:
                        if keyword in content_lower:
                            context_score += 0.1
                            break

                # 组合原始分数和上下文分数
                # 原始分数权重70%，上下文分数权重30%
                combined_score = result.score * 0.7 + context_score * 0.3

                scored_results.append((combined_score, result))

            # 按组合分数排序
            scored_results.sort(key=lambda x: x[0], reverse=True)

            # 提取结果
            filtered_results = [result for _, result in scored_results]

            logger.debug(f"上下文过滤: {len(results)} -> {len(filtered_results)}")

            return filtered_results

        except Exception as e:
            logger.error(f"上下文过滤失败: {e}")
            return results


# 全局RetrievalService实例
retrieval_service = RetrievalService()
