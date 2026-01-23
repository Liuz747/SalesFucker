"""
Embedding生成服务

该模块提供统一的embedding生成接口，支持多种embedding模型。
包含Redis缓存机制，优化性能和成本。

核心功能:
- 文本embedding生成
- 批量embedding生成
- Redis缓存（7天TTL）
- 缓存命中率跟踪
- 自动重试机制
"""

import hashlib
import json
from typing import Optional, Sequence

import msgpack
from langfuse.decorators import observe
from openai import AsyncOpenAI
from redis.asyncio import Redis

from config import mas_config
from config.rag_config import rag_config
from libs.factory import infra_registry
from utils import get_component_logger

logger = get_component_logger(__name__, "EmbeddingService")


class EmbeddingService:
    """
    Embedding生成服务

    提供文本embedding生成和缓存管理功能。
    使用Redis缓存减少API调用，提高性能和降低成本。
    """

    def __init__(self):
        """初始化EmbeddingService"""
        self.model = rag_config.EMBEDDING_MODEL
        self.dimension = rag_config.EMBEDDING_DIMENSION
        self.cache_ttl = rag_config.EMBEDDING_CACHE_TTL
        self.batch_size = rag_config.EMBEDDING_BATCH_SIZE

        # 初始化OpenAI客户端
        self.client = AsyncOpenAI(api_key=mas_config.OPENAI_API_KEY)

        # 缓存统计
        self.cache_hits = 0
        self.cache_misses = 0

    @staticmethod
    def _generate_cache_key(text: str, model: str) -> str:
        """
        生成缓存键

        参数:
            text: 文本内容
            model: 模型名称

        返回:
            str: 缓存键
        """
        # 使用文本和模型的hash作为缓存键
        content = f"{model}:{text}"
        hash_key = hashlib.sha256(content.encode()).hexdigest()
        return f"embedding:{hash_key}"

    async def _get_cached_embedding(
        self,
        text: str,
        redis_client: Redis
    ) -> Optional[list[float]]:
        """
        从缓存获取embedding

        参数:
            text: 文本内容
            redis_client: Redis客户端

        返回:
            Optional[list[float]]: embedding向量，不存在则返回None
        """
        try:
            cache_key = self._generate_cache_key(text, self.model)
            cached_data = await redis_client.get(cache_key)

            if cached_data:
                self.cache_hits += 1
                embedding = msgpack.unpackb(cached_data, raw=False)
                logger.debug(f"缓存命中: {cache_key[:16]}...")
                return embedding

            self.cache_misses += 1
            return None

        except Exception as e:
            logger.error(f"获取缓存embedding失败: {e}")
            return None

    async def _cache_embedding(
        self,
        text: str,
        embedding: list[float],
        redis_client: Redis
    ):
        """
        缓存embedding

        参数:
            text: 文本内容
            embedding: embedding向量
            redis_client: Redis客户端
        """
        try:
            cache_key = self._generate_cache_key(text, self.model)
            packed_data = msgpack.packb(embedding)

            await redis_client.set(
                cache_key,
                packed_data,
                ex=self.cache_ttl
            )
            logger.debug(f"缓存embedding: {cache_key[:16]}...")

        except Exception as e:
            logger.error(f"缓存embedding失败: {e}")

    @observe(name="generate_embedding")
    async def generate_embedding(
        self,
        text: str,
        use_cache: bool = True
    ) -> list[float]:
        """
        生成单个文本的embedding

        参数:
            text: 文本内容
            use_cache: 是否使用缓存

        返回:
            list[float]: embedding向量
        """
        try:
            redis_client = infra_registry.get_cached_clients().redis

            # 尝试从缓存获取
            if use_cache:
                cached_embedding = await self._get_cached_embedding(text, redis_client)
                if cached_embedding:
                    return cached_embedding

            # 调用OpenAI API生成embedding
            logger.debug(f"生成embedding: {text[:50]}...")
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding

            # 缓存结果
            if use_cache:
                await self._cache_embedding(text, embedding, redis_client)

            logger.info(f"Embedding生成成功: 维度={len(embedding)}")
            return embedding

        except Exception as e:
            logger.error(f"生成embedding失败: {e}")
            raise

    @observe(name="generate_embeddings_batch")
    async def generate_embeddings_batch(
        self,
        texts: Sequence[str],
        use_cache: bool = True
    ) -> list[list[float]]:
        """
        批量生成embedding

        参数:
            texts: 文本列表
            use_cache: 是否使用缓存

        返回:
            list[list[float]]: embedding向量列表
        """
        try:
            if not texts:
                return []

            redis_client = infra_registry.get_cached_clients().redis
            embeddings = []
            texts_to_generate = []
            text_indices = []

            # 检查缓存
            if use_cache:
                for i, text in enumerate(texts):
                    cached_embedding = await self._get_cached_embedding(text, redis_client)
                    if cached_embedding:
                        embeddings.append((i, cached_embedding))
                    else:
                        texts_to_generate.append(text)
                        text_indices.append(i)
            else:
                texts_to_generate = list(texts)
                text_indices = list(range(len(texts)))

            # 批量生成未缓存的embedding
            if texts_to_generate:
                logger.info(f"批量生成embedding: {len(texts_to_generate)} 个文本")

                # 分批处理（避免超过API限制）
                batch_embeddings = []
                for i in range(0, len(texts_to_generate), self.batch_size):
                    batch = texts_to_generate[i:i + self.batch_size]

                    response = await self.client.embeddings.create(
                        model=self.model,
                        input=batch,
                        encoding_format="float"
                    )

                    batch_results = [item.embedding for item in response.data]
                    batch_embeddings.extend(batch_results)

                    logger.debug(f"批次完成: {len(batch)} 个embedding")

                # 缓存新生成的embedding
                if use_cache:
                    for text, embedding in zip(texts_to_generate, batch_embeddings):
                        await self._cache_embedding(text, embedding, redis_client)

                # 合并缓存和新生成的结果
                for idx, embedding in zip(text_indices, batch_embeddings):
                    embeddings.append((idx, embedding))

            # 按原始顺序排序
            embeddings.sort(key=lambda x: x[0])
            result = [emb for _, emb in embeddings]

            logger.info(f"批量embedding生成完成: {len(result)} 个向量")
            return result

        except Exception as e:
            logger.error(f"批量生成embedding失败: {e}")
            raise

    def get_cache_stats(self) -> dict:
        """
        获取缓存统计信息

        返回:
            dict: 缓存统计
        """
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total > 0 else 0

        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2)
        }

    def reset_cache_stats(self):
        """重置缓存统计"""
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("缓存统计已重置")


# 全局EmbeddingService实例
embedding_service = EmbeddingService()
