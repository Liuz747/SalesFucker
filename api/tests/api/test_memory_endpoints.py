"""
记忆管理API端点单元测试

该测试模块专注于记忆管理API端点的业务逻辑测试:
- 记忆删除逻辑
- 权限验证
- 错误处理

注意: 这些是单元测试，不包含JWT认证层的集成测试
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4, UUID

from controllers.workspace.app.memory import delete_inserted_memory
from models import TenantModel, Thread
from schemas import MemoryDeleteRequest, BaseResponse
from libs.exceptions import (
    ThreadNotFoundException,
    ThreadAccessDeniedException,
    MemoryNotFoundException,
    MemoryDeletionException
)


class TestMemoryDeleteEndpoint:
    """测试记忆删除端点业务逻辑"""

    @pytest.fixture
    def mock_tenant(self):
        """模拟租户fixture"""
        tenant = Mock(spec=TenantModel)
        tenant.tenant_id = "test_tenant_123"
        return tenant

    @pytest.fixture
    def mock_thread(self):
        """模拟线程fixture"""
        thread = Mock(spec=Thread)
        thread.thread_id = uuid4()
        thread.tenant_id = "test_tenant_123"
        return thread

    @pytest.fixture
    def valid_delete_request(self, mock_thread):
        """有效的删除请求"""
        return MemoryDeleteRequest(
            thread_id=mock_thread.thread_id,
            memory_id="test_memory_id_123"
        )

    @pytest.mark.asyncio
    @patch("controllers.workspace.app.memory.ThreadService.get_thread")
    @patch("controllers.workspace.app.memory.MemoryService.delete_memory")
    async def test_delete_memory_success(
        self,
        mock_delete_memory,
        mock_get_thread,
        mock_tenant,
        mock_thread,
        valid_delete_request
    ):
        """测试成功删除记忆"""
        # 设置mock返回值
        mock_get_thread.return_value = mock_thread
        mock_delete_memory.return_value = None

        # 调用端点函数
        response = await delete_inserted_memory(valid_delete_request, mock_tenant)

        # 验证响应
        assert isinstance(response, BaseResponse)
        assert response.message == "记忆删除成功"

        # 验证调用
        mock_get_thread.assert_called_once_with(valid_delete_request.thread_id)
        mock_delete_memory.assert_called_once_with(
            tenant_id=mock_tenant.tenant_id,
            thread_id=mock_thread.thread_id,
            memory_id=valid_delete_request.memory_id
        )

    @pytest.mark.asyncio
    @patch("controllers.workspace.app.memory.ThreadService.get_thread")
    async def test_delete_memory_thread_not_found(
        self,
        mock_get_thread,
        mock_tenant,
        valid_delete_request
    ):
        """测试删除记忆时线程不存在"""
        # 设置mock返回值 - 线程不存在
        mock_get_thread.return_value = None

        # 验证抛出异常
        with pytest.raises(ThreadNotFoundException) as exc_info:
            await delete_inserted_memory(valid_delete_request, mock_tenant)

        assert str(valid_delete_request.thread_id) in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("controllers.workspace.app.memory.ThreadService.get_thread")
    async def test_delete_memory_access_denied(
        self,
        mock_get_thread,
        mock_tenant,
        mock_thread,
        valid_delete_request
    ):
        """测试删除记忆时访问被拒绝"""
        # 设置mock返回值 - 线程属于不同租户
        mock_thread.tenant_id = "different_tenant_456"
        mock_get_thread.return_value = mock_thread

        # 验证抛出异常
        with pytest.raises(ThreadAccessDeniedException) as exc_info:
            await delete_inserted_memory(valid_delete_request, mock_tenant)

        assert str(valid_delete_request.thread_id) in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("controllers.workspace.app.memory.ThreadService.get_thread")
    @patch("controllers.workspace.app.memory.MemoryService.delete_memory")
    async def test_delete_memory_not_found(
        self,
        mock_delete_memory,
        mock_get_thread,
        mock_tenant,
        mock_thread,
        valid_delete_request
    ):
        """测试删除不存在的记忆"""
        # 设置mock返回值
        mock_get_thread.return_value = mock_thread
        mock_delete_memory.side_effect = MemoryNotFoundException("test_memory_id_123")

        # 验证抛出异常
        with pytest.raises(MemoryNotFoundException) as exc_info:
            await delete_inserted_memory(valid_delete_request, mock_tenant)

        assert "test_memory_id_123" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("controllers.workspace.app.memory.ThreadService.get_thread")
    @patch("controllers.workspace.app.memory.MemoryService.delete_memory")
    async def test_delete_memory_service_error(
        self,
        mock_delete_memory,
        mock_get_thread,
        mock_tenant,
        mock_thread,
        valid_delete_request
    ):
        """测试删除记忆时服务层错误"""
        # 设置mock返回值
        mock_get_thread.return_value = mock_thread
        mock_delete_memory.side_effect = Exception("Database connection failed")

        # 验证抛出MemoryDeletionException
        with pytest.raises(MemoryDeletionException) as exc_info:
            await delete_inserted_memory(valid_delete_request, mock_tenant)

        assert "Database connection failed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_request_validation(self):
        """测试删除请求参数验证"""
        # 测试有效的UUID
        valid_request = MemoryDeleteRequest(
            thread_id=uuid4(),
            memory_id="test_memory_id"
        )
        assert isinstance(valid_request.thread_id, UUID)
        assert valid_request.memory_id == "test_memory_id"

        # 测试无效的UUID
        with pytest.raises(ValueError):
            MemoryDeleteRequest(
                thread_id="not-a-valid-uuid",
                memory_id="test_memory_id"
            )