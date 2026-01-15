"""
租户存储库测试

测试 TenantRepository 的数据库操作，特别是 update_tenant_field 方法中的 rowcount() 调用
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from repositories.tenant_repo import TenantRepository
from models import TenantOrm


@pytest.mark.asyncio
async def test_update_tenant_field_success():
    """测试成功更新租户字段，验证 rowcount 属性访问"""
    # 创建模拟的 AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # 创建模拟的 CursorResult
    mock_result = MagicMock()
    # 重要：rowcount 是一个 @memoized_property 装饰的属性，返回 int
    mock_result.rowcount = 1

    # 配置 session.execute 返回模拟结果
    mock_session.execute = AsyncMock(return_value=mock_result)

    # 调用被测试的方法
    tenant_id = "test-tenant-123"
    update_values = {"name": "Updated Name", "status": "active"}

    result = await TenantRepository.update_tenant_field(
        tenant_id=tenant_id,
        value=update_values,
        session=mock_session
    )

    # 验证结果
    assert result is True, "应该返回 True 当有行被更新时"

    # 验证 session.execute 被调用
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_tenant_field_no_rows_affected():
    """测试更新租户字段但没有行被影响（租户不存在）"""
    # 创建模拟的 AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # 创建模拟的 CursorResult，rowcount 返回 0
    mock_result = MagicMock()
    mock_result.rowcount = 0

    # 配置 session.execute 返回模拟结果
    mock_session.execute = AsyncMock(return_value=mock_result)

    # 调用被测试的方法
    tenant_id = "non-existent-tenant"
    update_values = {"name": "Updated Name"}

    result = await TenantRepository.update_tenant_field(
        tenant_id=tenant_id,
        value=update_values,
        session=mock_session
    )

    # 验证结果
    assert result is False, "应该返回 False 当没有行被更新时"


@pytest.mark.asyncio
async def test_update_tenant_field_preserves_input_dict():
    """测试 update_tenant_field 不会修改输入的 value 字典"""
    # 创建模拟的 AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # 创建模拟的 CursorResult
    mock_result = MagicMock()
    mock_result.rowcount = 1  # 属性，不是方法

    # 配置 session.execute 返回模拟结果
    mock_session.execute = AsyncMock(return_value=mock_result)

    # 创建输入字典
    original_values = {"name": "Test Name", "status": "active"}
    input_values = original_values.copy()

    # 调用被测试的方法
    await TenantRepository.update_tenant_field(
        tenant_id="test-tenant",
        value=input_values,
        session=mock_session
    )

    # 验证输入字典没有被修改（不应该包含 updated_at）
    assert input_values == original_values, "输入字典不应该被修改"
    assert "updated_at" not in input_values, "updated_at 不应该被添加到输入字典中"


@pytest.mark.asyncio
async def test_update_tenant_field_exception_handling():
    """测试更新租户字段时的异常处理"""
    # 创建模拟的 AsyncSession，抛出异常
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock(side_effect=Exception("Database error"))

    # 调用被测试的方法，应该抛出异常
    with pytest.raises(Exception) as exc_info:
        await TenantRepository.update_tenant_field(
            tenant_id="test-tenant",
            value={"name": "Test"},
            session=mock_session
        )

    assert "Database error" in str(exc_info.value)