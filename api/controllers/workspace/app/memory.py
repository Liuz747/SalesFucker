"""
记忆管理路由器

该模块提供记忆插入和管理相关的API端点，支持批量记忆插入。
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from libs.exceptions import (
    BaseHTTPException,
    MemoryException,
    MemoryInsertFailureException,
    ThreadNotFoundException,
    ThreadAccessDeniedException,
    ThreadBusyException
)
from libs.types import ThreadStatus
from models import TenantModel
from schemas import (
    BaseResponse,
    MemoryInsertRequest,
    MemoryInsertResponse,
    MemoryDeleteRequest,
    MemoryAppendRequest
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
            raise ThreadAccessDeniedException(tenant.tenant_id)

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
        raise MemoryException(detail=f"记忆插入失败: {str(e)}")


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
            raise ThreadAccessDeniedException(tenant.tenant_id)

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
        raise MemoryException(detail=f"记忆删除失败: {str(e)}")


@router.post("/{thread_id}/append", response_model=BaseResponse)
async def append_messages(
    thread_id: UUID,
    request: MemoryAppendRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    追加消息到线程记忆

    允许外部调用者批量追加消息到指定线程的记忆末尾。
    消息将按顺序追加到现有记忆的最后，并在达到阈值时自动触发摘要生成。

    注意：
    - 消息将直接追加，不进行去重检查
    - 调用方需确保消息的幂等性
    - 最多支持一次追加100条消息
    - 如果线程正在处理工作流，将等待最多5秒，超时后返回409错误
    """
    try:
        # 验证线程存在且属于该租户
        thread = await ThreadService.get_thread(thread_id)
        if not thread:
            raise ThreadNotFoundException(thread_id)

        if thread.tenant_id != tenant.tenant_id:
            raise ThreadAccessDeniedException(tenant.tenant_id)

        # 检查线程状态，如果正在处理工作流则等待
        if thread.status == ThreadStatus.BUSY:
            logger.info(f"线程正在处理工作流，等待可用 - thread: {thread_id}")

            # 等待最多5秒让工作流完成
            is_available = await ThreadService.wait_for_thread_available(
                thread_id=thread_id,
                timeout=5.0
            )

            if not is_available:
                raise ThreadBusyException(thread_id, timeout=5.0)

            logger.info(f"线程已可用，继续追加消息 - thread: {thread_id}")

        # 调用服务层处理消息追加
        await MemoryService.append_messages(
            tenant_id=tenant.tenant_id,
            thread_id=thread_id,
            messages=request.messages
        )

        logger.info(f"消息追加成功 - thread: {thread_id}")

        return BaseResponse(message="消息追加成功")

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"消息追加失败 - thread: {thread_id}, 错误: {e}", exc_info=True)
        raise MemoryException(detail=f"消息追加失败: {str(e)}")
