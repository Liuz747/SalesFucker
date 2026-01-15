"""
AssetsService 单元测试
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.assets_service import AssetsService


@pytest.fixture
def mock_redis():
    """Mock Redis客户端"""
    redis = AsyncMock()
    return redis


@pytest.fixture
def mock_external_client():
    """Mock ExternalClient"""
    client = AsyncMock()
    return client


@pytest.fixture
def assets_service(mock_external_client):
    """创建AssetsService实例"""
    with patch('services.assets_service.ExternalClient', return_value=mock_external_client):
        service = AssetsService(base_url="http://test.com")
        return service


@pytest.fixture
def sample_assets_data():
    """示例素材数据"""
    return {
        "assets": [
            {
                "id": 1,
                "name": "产品介绍视频",
                "content": "这是一个关于我们产品的介绍视频",
                "remark": "适合新客户"
            },
            {
                "id": 2,
                "name": "价格表",
                "content": "最新的产品价格表",
                "remark": "2024年版本"
            },
            {
                "id": 3,
                "name": "使用手册",
                "content": "详细的产品使用说明",
                "remark": "包含常见问题"
            }
        ],
        "total": 3,
        "from_cache": False
    }


class TestAssetsService:
    """AssetsService测试类"""

    def test_get_cache_key(self):
        """测试缓存键生成"""
        tenant_id = "test-tenant"
        cache_key = AssetsService._get_cache_key(tenant_id)
        assert cache_key == "assets:test-tenant"

    @pytest.mark.asyncio
    async def test_get_cached_assets_hit(self, assets_service, mock_redis, sample_assets_data):
        """测试缓存命中"""
        with patch('services.assets_service.infra_registry') as mock_registry:
            mock_registry.get_cached_clients().redis = mock_redis
            mock_redis.get.return_value = json.dumps(sample_assets_data)

            result = await assets_service.get_cached_assets("test-tenant")

            assert result is not None
            assert result["total"] == 3
            assert len(result["assets"]) == 3
            mock_redis.get.assert_called_once_with("assets:test-tenant")

    @pytest.mark.asyncio
    async def test_get_cached_assets_miss(self, assets_service, mock_redis):
        """测试缓存未命中"""
        with patch('services.assets_service.infra_registry') as mock_registry:
            mock_registry.get_cached_clients().redis = mock_redis
            mock_redis.get.return_value = None

            result = await assets_service.get_cached_assets("test-tenant")

            assert result is None
            mock_redis.get.assert_called_once_with("assets:test-tenant")

    @pytest.mark.asyncio
    async def test_set_cached_assets(self, assets_service, mock_redis, sample_assets_data):
        """测试设置缓存"""
        with patch('services.assets_service.infra_registry') as mock_registry:
            mock_registry.get_cached_clients().redis = mock_redis
            mock_redis.set.return_value = True

            result = await assets_service.set_cached_assets("test-tenant", sample_assets_data)

            assert result is True
            mock_redis.set.assert_called_once()
            args, kwargs = mock_redis.set.call_args
            assert args[0] == "assets:test-tenant"
            assert kwargs['ex'] == 86400  # 24小时

    @pytest.mark.asyncio
    async def test_query_assets_from_cache(self, assets_service, mock_redis, sample_assets_data):
        """测试从缓存查询素材"""
        with patch('services.assets_service.infra_registry') as mock_registry:
            mock_registry.get_cached_clients().redis = mock_redis
            mock_redis.get.return_value = json.dumps(sample_assets_data)

            result = await assets_service.query_assets(
                tenant_id="test-tenant",
                thread_id=uuid4(),
                assistant_id=uuid4(),
                workflow_id=uuid4(),
                use_cache=True
            )

            assert result["from_cache"] is True
            assert result["total"] == 3
            assert len(result["assets"]) == 3

    @pytest.mark.asyncio
    async def test_query_assets_from_api(self, assets_service, mock_redis):
        """测试从API查询素材"""
        with patch('services.assets_service.infra_registry') as mock_registry:
            mock_registry.get_cached_clients().redis = mock_redis
            mock_redis.get.return_value = None
            mock_redis.set.return_value = True

            # Mock API响应
            api_response = {
                "code": 200,
                "data": [
                    {
                        "id": 1,
                        "name": "测试素材",
                        "content": "测试内容",
                        "remark": "测试备注",
                        "extra_field": "should be ignored"
                    }
                ],
                "total": 1
            }

            assets_service.client.make_request = AsyncMock(return_value=api_response)

            result = await assets_service.query_assets(
                tenant_id="test-tenant",
                thread_id=uuid4(),
                assistant_id=uuid4(),
                workflow_id=uuid4(),
                use_cache=True
            )

            assert result["from_cache"] is False
            assert result["total"] == 1
            assert len(result["assets"]) == 1
            assert result["assets"][0]["name"] == "测试素材"
            assert "extra_field" not in result["assets"][0]  # 只保留关键字段

    @pytest.mark.asyncio
    async def test_query_assets_api_error(self, assets_service, mock_redis):
        """测试API错误处理"""
        with patch('services.assets_service.infra_registry') as mock_registry:
            mock_registry.get_cached_clients().redis = mock_redis
            mock_redis.get.return_value = None

            # Mock API错误响应
            api_response = {
                "code": 500,
                "msg": "Internal Server Error"
            }

            assets_service.client.make_request = AsyncMock(return_value=api_response)

            result = await assets_service.query_assets(
                tenant_id="test-tenant",
                thread_id=uuid4(),
                assistant_id=uuid4(),
                workflow_id=uuid4(),
                use_cache=False
            )

            assert result["total"] == 0
            assert len(result["assets"]) == 0
            assert "error" in result

    def test_extract_keywords(self):
        """测试关键词提取"""
        # 测试中文（简单分词按空格分割）
        text = "产品介绍 价格表 使用手册"
        keywords = AssetsService.extract_keywords(text)
        assert "产品介绍" in keywords
        assert "价格表" in keywords
        assert "使用手册" in keywords

        # 测试英文
        text = "product introduction and price list"
        keywords = AssetsService.extract_keywords(text)
        assert "product" in keywords
        assert "introduction" in keywords
        assert "price" in keywords
        assert "list" in keywords

        # 测试停用词过滤
        text = "的 了 是 产品"
        keywords = AssetsService.extract_keywords(text)
        assert "产品" in keywords
        assert "的" not in keywords
        assert "了" not in keywords

        # 测试空文本
        keywords = AssetsService.extract_keywords("")
        assert keywords == []

    def test_search_assets_with_keywords(self, sample_assets_data):
        """测试关键词搜索"""
        keywords = ["产品", "介绍"]

        results = AssetsService.search_assets(
            assets_data=sample_assets_data,
            keywords=keywords,
            top_k=10,
            score_threshold=0.0
        )

        # 应该返回包含"产品"和"介绍"的素材
        assert len(results) > 0
        assert results[0]["id"] == 1  # "产品介绍视频"应该排第一
        assert "search_score" in results[0]
        assert "matched_keywords" in results[0]
        assert results[0]["search_score"] > 0

    def test_search_assets_no_keywords(self, sample_assets_data):
        """测试无关键词搜索"""
        results = AssetsService.search_assets(
            assets_data=sample_assets_data,
            keywords=[],
            top_k=2
        )

        # 无关键词时返回前N个素材
        assert len(results) == 2

    def test_search_assets_no_match(self, sample_assets_data):
        """测试无匹配结果"""
        keywords = ["不存在的关键词", "xyz123"]

        results = AssetsService.search_assets(
            assets_data=sample_assets_data,
            keywords=keywords,
            top_k=10,
            score_threshold=0.0
        )

        # 应该返回空列表
        assert len(results) == 0

    def test_search_assets_scoring(self, sample_assets_data):
        """测试搜索评分机制"""
        # name中匹配应该得分最高
        keywords = ["产品介绍"]

        results = AssetsService.search_assets(
            assets_data=sample_assets_data,
            keywords=keywords,
            top_k=10
        )

        # "产品介绍视频"应该排第一（name匹配）
        assert results[0]["id"] == 1
        assert results[0]["search_score"] >= 5  # name匹配至少5分

    def test_search_assets_top_k(self, sample_assets_data):
        """测试top_k限制"""
        keywords = ["产品", "价格", "使用"]

        results = AssetsService.search_assets(
            assets_data=sample_assets_data,
            keywords=keywords,
            top_k=2
        )

        # 即使有3个匹配，也只返回2个
        assert len(results) == 2

    def test_search_assets_score_threshold(self, sample_assets_data):
        """测试分数阈值"""
        keywords = ["产品"]

        results = AssetsService.search_assets(
            assets_data=sample_assets_data,
            keywords=keywords,
            top_k=10,
            score_threshold=10.0  # 设置高阈值
        )

        # 高阈值可能过滤掉一些结果
        for result in results:
            assert result["search_score"] > 10.0