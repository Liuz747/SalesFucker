"""
记忆管理路由器

该模块提供记忆插入和管理相关的API端点，支持批量记忆插入。
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from libs.exceptions import (
    BaseHTTPException,
    MemoryInsertionException,
    MemoryInsertFailureException,
    MemoryDeletionException,
    ThreadNotFoundException,
    ThreadAccessDeniedException
)
from models import TenantModel
from schemas import (
    BaseResponse,
    MemoryInsertRequest,
    MemoryInsertResponse,
    MemoryDeleteRequest
)
from services import MemoryService, ThreadService
from utils import get_component_logger
from ..wraps import validate_and_get_tenant

logger = get_component_logger(__name__, "MemoryRouter")

# 创建路由器
router = APIRouter()


@router.post("/insert", response_model=MemoryInsertResponse)
async def insert_memory(
    request: MemoryInsertRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    手动插入记忆列表

    支持批量插入，返回每条记忆的插入结果。

    可选择性添加标签。
    """
    try:
        # 验证线程存在且租户有权访问
        thread = await ThreadService.get_thread(request.thread_id)

        if not thread:
            raise ThreadNotFoundException(request.thread_id)

        if thread.tenant_id != tenant.tenant_id:
            raise ThreadAccessDeniedException(request.thread_id, tenant.tenant_id)

        # 插入记忆
        results, summary = await MemoryService.insert_memory(
            tenant_id=tenant.tenant_id,
            thread_id=request.thread_id,
            memories=request.memories,
            tags=request.tags
        )

        if not summary.succeed:
            raise MemoryInsertFailureException()

        return MemoryInsertResponse(
            message=f"手动插入记忆成功：{summary.succeed}/{summary.total}",
            results=results,
            metadata=summary.model_dump()
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"记忆插入失败: {e}", exc_info=True)
        raise MemoryInsertionException(reason=str(e))


@router.post("/delete", response_model=BaseResponse)
async def delete_inserted_memory(
    request: MemoryDeleteRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    删除指定的记忆

    验证线程存在且租户有权访问后删除记忆。
    """
    try:
        # 验证线程存在且租户有权访问
        thread = await ThreadService.get_thread(request.thread_id)

        if not thread:
            raise ThreadNotFoundException(request.thread_id)

        if thread.tenant_id != tenant.tenant_id:
            raise ThreadAccessDeniedException(request.thread_id, tenant.tenant_id)

        # 删除记忆
        await MemoryService.delete_memory(
            tenant_id=tenant.tenant_id,
            thread_id=request.thread_id,
            memory_id=request.memory_id
        )

        return BaseResponse(message="记忆删除成功")

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"记忆删除失败: {e}", exc_info=True)
        raise MemoryDeletionException(reason=str(e))
