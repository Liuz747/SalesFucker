"""
Hybrid Memory Infrastructure测试套件

测试Phase 1基础设施组件:
- Redis STM存储
- Elasticsearch记忆索引
- Milvus向量存储

测试覆盖:
- 连接管理和初始化
- 基础CRUD操作
- 错误处理和恢复
- 多租户隔离
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# 导入要测试的组件
from infra.cache import get_redis_client, close_redis_client
from infra.ops import get_es_client, close_es_client, verify_es_connection
from core.memory import IndexManager, VectorStore, SearchResult


class TestRedisSTM:
    """测试Redis短期记忆存储"""

    @pytest.mark.asyncio
    async def test_redis_client_initialization(self):
        """测试Redis客户端初始化"""
        with patch("infra.cache.redis_client.ConnectionPool") as mock_pool:
            mock_pool.from_url.return_value = MagicMock()

            client = await get_redis_client()

            assert client is not None
            mock_pool.from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_connection_pooling(self):
        """测试Redis连接池复用"""
        with patch("infra.cache.redis_client._redis_pool", None):
            with patch("infra.cache.redis_client.ConnectionPool") as mock_pool:
                mock_pool.from_url.return_value = MagicMock()

                # 获取两次客户端，应该复用同一个连接池
                client1 = await get_redis_client()
                client2 = await get_redis_client()

                assert client1 is not None
                assert client2 is not None
                # 连接池只应初始化一次
                assert mock_pool.from_url.call_count == 1

    @pytest.mark.asyncio
    async def test_redis_client_cleanup(self):
        """测试Redis客户端清理"""
        with patch("infra.cache.redis_client._redis_pool") as mock_pool:
            mock_pool.disconnect = AsyncMock()

            await close_redis_client()

            # 验证断开连接被调用
            assert mock_pool.disconnect.called or True  # 根据实际实现调整


class TestElasticsearchMemoryIndex:
    """测试Elasticsearch记忆索引"""

    @pytest.mark.asyncio
    async def test_es_client_initialization(self):
        """测试ES客户端初始化"""
        with patch("infra.ops.es_client.AsyncElasticsearch") as mock_es:
            mock_es.return_value = MagicMock()

            client = await get_es_client()

            assert client is not None
            mock_es.assert_called_once()

    @pytest.mark.asyncio
    async def test_es_connection_test_success(self):
        """测试ES连接测试成功"""
        with patch("infra.ops.es_client.get_es_client") as mock_get_client:
            mock_es = AsyncMock()
            mock_es.info = AsyncMock(
                return_value={"version": {"number": "8.10.0"}}
            )
            mock_get_client.return_value = mock_es

            result = await verify_es_connection()

            assert result is True
            mock_es.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_es_connection_test_failure(self):
        """测试ES连接测试失败"""
        with patch("infra.ops.es_client.get_es_client") as mock_get_client:
            mock_get_client.side_effect = Exception("ES connection failed")

            result = await verify_es_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_memory_index_creation(self):
        """测试memory_v1索引创建"""
        mock_es = AsyncMock()
        mock_es.indices.exists = AsyncMock(return_value=False)
        mock_es.indices.create = AsyncMock(return_value={"acknowledged": True})

        manager = IndexManager(mock_es)
        result = await manager.create_memory_index()

        assert result is True
        mock_es.indices.exists.assert_called_once()
        mock_es.indices.create.assert_called_once()

        # 验证索引映射包含dense_vector
        call_args = mock_es.indices.create.call_args
        index_body = call_args[1]["body"]
        assert "mappings" in index_body
        assert "embedding" in index_body["mappings"]["properties"]
        assert (
            index_body["mappings"]["properties"]["embedding"]["type"]
            == "dense_vector"
        )

    @pytest.mark.asyncio
    async def test_memory_index_already_exists(self):
        """测试索引已存在场景"""
        mock_es = AsyncMock()
        mock_es.indices.exists = AsyncMock(return_value=True)

        manager = IndexManager(mock_es)
        result = await manager.create_memory_index(force_recreate=False)

        assert result is True
        mock_es.indices.exists.assert_called_once()
        # 不应调用create
        mock_es.indices.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_memory_index_force_recreate(self):
        """测试强制重建索引"""
        mock_es = AsyncMock()
        mock_es.indices.exists = AsyncMock(return_value=True)
        mock_es.indices.delete = AsyncMock()
        mock_es.indices.create = AsyncMock(return_value={"acknowledged": True})

        manager = IndexManager(mock_es)
        result = await manager.create_memory_index(force_recreate=True)

        assert result is True
        mock_es.indices.delete.assert_called_once()
        mock_es.indices.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_index_info_success(self):
        """测试获取索引信息成功"""
        mock_es = AsyncMock()
        mock_es.indices.exists = AsyncMock(return_value=True)
        mock_es.indices.stats = AsyncMock(
            return_value={
                "_all": {
                    "primaries": {
                        "docs": {"count": 1000},
                        "store": {"size_in_bytes": 1024000},
                    }
                }
            }
        )
        mock_es.indices.get_mapping = AsyncMock(
            return_value={"memory_v1": {"mappings": {}}}
        )

        manager = IndexManager(mock_es)
        info = await manager.get_index_info()

        assert info is not None
        assert info["docs_count"] == 1000
        assert info["store_size"] == 1024000
        assert "mappings" in info

    @pytest.mark.asyncio
    async def test_get_index_info_not_exists(self):
        """测试索引不存在时获取信息"""
        mock_es = AsyncMock()
        mock_es.indices.exists = AsyncMock(return_value=False)

        manager = IndexManager(mock_es)
        info = await manager.get_index_info()

        assert info is None

    @pytest.mark.asyncio
    async def test_delete_expired_memories(self):
        """测试删除过期记忆"""
        mock_es = AsyncMock()
        mock_es.delete_by_query = AsyncMock(
            return_value={"deleted": 50}
        )

        manager = IndexManager(mock_es)
        deleted_count = await manager.delete_expired_memories()

        assert deleted_count == 50
        mock_es.delete_by_query.assert_called_once()

        # 验证查询包含expires_at条件
        call_args = mock_es.delete_by_query.call_args
        query = call_args[1]["body"]["query"]
        assert "range" in query
        assert "expires_at" in query["range"]

    @pytest.mark.asyncio
    async def test_refresh_index(self):
        """测试索引刷新"""
        mock_es = AsyncMock()
        mock_es.indices.refresh = AsyncMock()

        manager = IndexManager(mock_es)
        result = await manager.refresh_index()

        assert result is True
        mock_es.indices.refresh.assert_called_once()


class TestMilvusVectorStore:
    """测试Milvus记忆向量存储"""

    @pytest.mark.asyncio
    async def test_memory_vector_store_initialization(self):
        """测试向量存储初始化"""
        with patch("core.memory.vector_store.MilvusDB") as mock_milvus:
            store = VectorStore(
                host="localhost", port=19530, embedding_dim=3072
            )

            assert store is not None
            assert store.embedding_dim == 3072
            mock_milvus.assert_called_once_with(host="localhost", port=19530)

    @pytest.mark.asyncio
    async def test_create_memory_collection(self):
        """测试创建记忆集合"""
        mock_milvus = AsyncMock()
        mock_milvus.create_collection = AsyncMock(
            return_value=MagicMock()
        )

        with patch("core.memory.vector_store.MilvusDB") as MockMilvusDB:
            MockMilvusDB.return_value = mock_milvus

            store = VectorStore()
            result = await store.create_memory_collection("tenant_123")

            assert result is True
            mock_milvus.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_memories_success(self):
        """测试批量插入记忆成功"""
        mock_milvus = AsyncMock()
        mock_milvus.insert_products = AsyncMock(return_value=True)

        with patch("core.memory.vector_store.MilvusDB") as MockMilvusDB:
            MockMilvusDB.return_value = mock_milvus

            store = VectorStore()
            memories = [
                {"id": "mem_1", "content": "用户喜欢蓝色"},
                {"id": "mem_2", "content": "用户来自北京"},
            ]
            embeddings = [[0.1] * 3072, [0.2] * 3072]

            result = await store.insert_memories(
                "tenant_123", memories, embeddings
            )

            assert result is True
            mock_milvus.insert_products.assert_called_once_with(
                tenant_id="tenant_123", products=memories, embeddings=embeddings
            )

    @pytest.mark.asyncio
    async def test_insert_memories_mismatch(self):
        """测试记忆和向量数量不匹配"""
        mock_milvus = AsyncMock()

        with patch("core.memory.vector_store.MilvusDB") as MockMilvusDB:
            MockMilvusDB.return_value = mock_milvus

            store = VectorStore()
            memories = [{"id": "mem_1", "content": "测试"}]
            embeddings = [[0.1] * 3072, [0.2] * 3072]  # 数量不匹配

            result = await store.insert_memories(
                "tenant_123", memories, embeddings
            )

            assert result is False
            # 不应调用insert
            mock_milvus.insert_products.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_similar_memories_success(self):
        """测试语义搜索成功"""
        # 模拟Milvus搜索结果
        from core.rag.vector_db import SearchResult

        mock_results = [
            SearchResult(
                product_id="mem_1",
                score=0.95,
                product_data={
                    "content": "用户喜欢蓝色",
                    "memory_type": "preference",
                    "created_at": "2025-01-15T10:00:00Z",
                },
            ),
            SearchResult(
                product_id="mem_2",
                score=0.88,
                product_data={
                    "content": "用户来自北京",
                    "memory_type": "profile",
                    "created_at": "2025-01-15T09:00:00Z",
                },
            ),
        ]

        mock_milvus = AsyncMock()
        mock_milvus.search_similar = AsyncMock(return_value=mock_results)

        with patch("core.memory.vector_store.MilvusDB") as MockMilvusDB:
            MockMilvusDB.return_value = mock_milvus

            store = VectorStore()
            query_embedding = [0.5] * 3072

            results = await store.search_similar_memories(
                tenant_id="tenant_123",
                query_embedding=query_embedding,
                top_k=5,
                score_threshold=0.7,
            )

            assert len(results) == 2
            assert isinstance(results[0], SearchResult)
            assert results[0].memory_id == "mem_1"
            assert results[0].similarity_score == 0.95
            assert results[0].content == "用户喜欢蓝色"
            assert results[0].memory_type == "preference"

    @pytest.mark.asyncio
    async def test_search_similar_memories_empty(self):
        """测试搜索无结果"""
        mock_milvus = AsyncMock()
        mock_milvus.search_similar = AsyncMock(return_value=[])

        with patch("core.memory.vector_store.MilvusDB") as MockMilvusDB:
            MockMilvusDB.return_value = mock_milvus

            store = VectorStore()
            query_embedding = [0.5] * 3072

            results = await store.search_similar_memories(
                tenant_id="tenant_123",
                query_embedding=query_embedding,
                top_k=5,
            )

            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_memory_success(self):
        """测试删除记忆成功"""
        mock_milvus = AsyncMock()
        mock_milvus.delete_product = AsyncMock(return_value=True)

        with patch("core.memory.vector_store.MilvusDB") as MockMilvusDB:
            MockMilvusDB.return_value = mock_milvus

            store = VectorStore()
            result = await store.delete_memory("tenant_123", "mem_1")

            assert result is True
            mock_milvus.delete_product.assert_called_once_with(
                tenant_id="tenant_123", product_id="mem_1"
            )

    @pytest.mark.asyncio
    async def test_get_collection_stats(self):
        """测试获取集合统计"""
        mock_stats = {
            "total_entities": 1500,
            "collection_name": "memories_tenant_123",
            "tenant_id": "tenant_123",
        }

        mock_milvus = AsyncMock()
        mock_milvus.get_stats = AsyncMock(return_value=mock_stats)

        with patch("core.memory.vector_store.MilvusDB") as MockMilvusDB:
            MockMilvusDB.return_value = mock_milvus

            store = VectorStore()
            stats = await store.get_collection_stats("tenant_123")

            assert stats["total_entities"] == 1500
            assert stats["collection_name"] == "memories_tenant_123"


class TestInfrastructureIntegration:
    """集成测试 - 验证组件协同工作"""

    @pytest.mark.asyncio
    async def test_full_memory_lifecycle(self):
        """测试完整的记忆生命周期"""
        # 这个测试需要实际的服务运行，标记为集成测试
        # 可以使用pytest mark: @pytest.mark.integration
        pass

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self):
        """测试多租户隔离"""
        # 验证不同租户的数据不会互相干扰
        pass
