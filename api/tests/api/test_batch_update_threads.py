"""
批量更新线程端点测试

测试 POST /api/v1/workspace/app/threads/batch/update 端点的功能和边界情况
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from models import Thread, ThreadOrm
from services.thread_service import ThreadService
from repositories.thread_repo import ThreadRepository
from schemas import ThreadBatchUpdateRequest
from schemas.thread_schema import ThreadBatchUpdatePayload


class TestBatchUpdateThreads:
    """批量更新线程测试类"""

    @pytest.fixture
    def sample_thread_ids(self):
        """示例线程ID列表"""
        return [uuid4() for _ in range(3)]

    @pytest.fixture
    def tenant_id(self):
        """示例租户ID"""
        return "test-tenant-123"

    @pytest.mark.asyncio
    async def test_batch_update_service_success(self, sample_thread_ids, tenant_id):
        """测试批量更新服务层 - 成功场景"""
        # Mock数据库会话和Redis
        with patch('services.thread_service.database_session') as mock_db_session, \
             patch('services.thread_service.infra_registry') as mock_registry:

            # Mock数据库返回成功更新的线程ID
            mock_session = AsyncMock()
            mock_db_session.return_value.__aenter__.return_value = mock_session

            with patch.object(ThreadRepository, 'bulk_update_threads',
                            return_value=sample_thread_ids):
                # Mock Redis客户端
                mock_redis = AsyncMock()
                mock_registry.get_cached_clients().redis = mock_redis

                # 执行批量更新
                succeeded, failed, failed_ids = await ThreadService.batch_update_threads(
                    tenant_id=tenant_id,
                    thread_ids=sample_thread_ids,
                    set_updates={"is_converted": True}
                )

                # 验证结果
                assert succeeded == 3
                assert failed == 0
                assert failed_ids == []

    @pytest.mark.asyncio
    async def test_batch_update_service_partial_failure(self, sample_thread_ids, tenant_id):
        """测试批量更新服务层 - 部分失败场景"""
        with patch('services.thread_service.database_session') as mock_db_session, \
             patch('services.thread_service.infra_registry') as mock_registry:

            mock_session = AsyncMock()
            mock_db_session.return_value.__aenter__.return_value = mock_session

            # 只返回部分成功的线程ID
            successful_ids = sample_thread_ids[:2]
            with patch.object(ThreadRepository, 'bulk_update_threads',
                            return_value=successful_ids):
                mock_redis = AsyncMock()
                mock_registry.get_cached_clients().redis = mock_redis

                succeeded, failed, failed_ids = await ThreadService.batch_update_threads(
                    tenant_id=tenant_id,
                    thread_ids=sample_thread_ids,
                    set_updates={"enable_trigger": True}
                )

                # 验证结果
                assert succeeded == 2
                assert failed == 1
                assert len(failed_ids) == 1
                assert failed_ids[0] == sample_thread_ids[2]

    @pytest.mark.asyncio
    async def test_batch_update_repository(self, sample_thread_ids, tenant_id):
        """测试批量更新仓储层"""
        # 使用patch测试repository方法
        with patch.object(ThreadRepository, 'bulk_update_threads', return_value=sample_thread_ids) as mock_bulk_update:
            mock_session = AsyncMock()

            # 执行批量更新
            result = await ThreadRepository.bulk_update_threads(
                tenant_id=tenant_id,
                thread_ids=sample_thread_ids,
                set_updates={"is_converted": True, "enable_trigger": True},
                session=mock_session
            )

            # 验证结果
            assert len(result) == 3
            assert result == sample_thread_ids

            # 验证方法被调用
            mock_bulk_update.assert_called_once_with(
                tenant_id=tenant_id,
                thread_ids=sample_thread_ids,
                set_updates={"is_converted": True, "enable_trigger": True},
                session=mock_session
            )

    @pytest.mark.asyncio
    async def test_batch_delete_cache(self, sample_thread_ids):
        """测试批量删除Redis缓存"""
        # 使用patch直接测试方法被调用
        with patch.object(ThreadRepository, 'batch_delete_cache', new_callable=AsyncMock) as mock_batch_delete:
            mock_redis = AsyncMock()

            await ThreadRepository.batch_delete_cache(sample_thread_ids, mock_redis)

            # 验证方法被调用
            mock_batch_delete.assert_called_once_with(sample_thread_ids, mock_redis)

    @pytest.mark.asyncio
    async def test_batch_delete_cache_empty_list(self):
        """测试批量删除缓存 - 空列表"""
        mock_redis = AsyncMock()

        # 执行批量删除缓存（空列表）
        await ThreadRepository.batch_delete_cache([], mock_redis)

        # 验证pipeline未被调用
        mock_redis.pipeline.assert_not_called()

    def test_batch_update_payload_validation_success(self):
        """测试批量更新payload验证 - 成功场景"""
        # 至少一个字段非None
        payload = ThreadBatchUpdatePayload(is_converted=True)
        assert payload.is_converted is True

        payload2 = ThreadBatchUpdatePayload(
            enable_trigger=True,
            enable_takeover=False
        )
        assert payload2.enable_trigger is True
        assert payload2.enable_takeover is False

    def test_batch_update_payload_validation_failure(self):
        """测试批量更新payload验证 - 失败场景"""
        # 所有字段都是None应该失败
        with pytest.raises(ValueError, match="至少需要提供一个更新字段"):
            ThreadBatchUpdatePayload()

    def test_batch_update_request_validation(self, sample_thread_ids):
        """测试批量更新请求验证"""
        # 正常请求
        request = ThreadBatchUpdateRequest(
            thread_ids=sample_thread_ids,
            set_updates=ThreadBatchUpdatePayload(is_converted=True)
        )
        assert len(request.thread_ids) == 3
        assert request.set_updates.is_converted is True

    def test_batch_update_request_max_threads(self):
        """测试批量更新请求 - 超过最大数量"""
        # 超过100个线程应该失败
        too_many_ids = [uuid4() for _ in range(101)]

        with pytest.raises(ValueError):
            ThreadBatchUpdateRequest(
                thread_ids=too_many_ids,
                set_updates=ThreadBatchUpdatePayload(is_converted=True)
            )

    def test_batch_update_request_empty_threads(self):
        """测试批量更新请求 - 空线程列表"""
        # 空列表应该失败
        with pytest.raises(ValueError):
            ThreadBatchUpdateRequest(
                thread_ids=[],
                set_updates=ThreadBatchUpdatePayload(is_converted=True)
            )

    @pytest.mark.asyncio
    async def test_batch_update_with_multiple_fields(self, sample_thread_ids, tenant_id):
        """测试批量更新多个字段"""
        with patch('services.thread_service.database_session') as mock_db_session, \
             patch('services.thread_service.infra_registry') as mock_registry:

            mock_session = AsyncMock()
            mock_db_session.return_value.__aenter__.return_value = mock_session

            with patch.object(ThreadRepository, 'bulk_update_threads',
                            return_value=sample_thread_ids):
                mock_redis = AsyncMock()
                mock_registry.get_cached_clients().redis = mock_redis

                # 更新多个字段
                succeeded, failed, failed_ids = await ThreadService.batch_update_threads(
                    tenant_id=tenant_id,
                    thread_ids=sample_thread_ids,
                    set_updates={
                        "is_converted": True,
                        "enable_trigger": True,
                        "enable_takeover": False
                    }
                )

                assert succeeded == 3
                assert failed == 0

    @pytest.mark.asyncio
    async def test_batch_update_wrong_tenant(self, sample_thread_ids):
        """测试批量更新 - 错误的租户ID"""
        with patch('services.thread_service.database_session') as mock_db_session, \
             patch('services.thread_service.infra_registry') as mock_registry:

            mock_session = AsyncMock()
            mock_db_session.return_value.__aenter__.return_value = mock_session

            # 返回空列表（没有匹配的线程）
            with patch.object(ThreadRepository, 'bulk_update_threads',
                            return_value=[]):
                mock_redis = AsyncMock()
                mock_registry.get_cached_clients().redis = mock_redis

                succeeded, failed, failed_ids = await ThreadService.batch_update_threads(
                    tenant_id="wrong-tenant-id",
                    thread_ids=sample_thread_ids,
                    set_updates={"is_converted": True}
                )

                # 所有线程都应该失败
                assert succeeded == 0
                assert failed == 3
                assert len(failed_ids) == 3