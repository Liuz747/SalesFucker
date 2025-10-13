from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends

from utils import get_component_logger


logger = get_component_logger(__name__, "ConversationRouter")

# 创建路由器
router = APIRouter()


@router.post("")
async def create_thread(
    thread_create_request: ThreadCreateRequest,
    assistant_id: Annotated[UUID, Depends(get_assistant_id)],
):
    """
    创建新的对话线程
    
    使用高性能混合存储策略，针对云端PostgreSQL优化。
    性能目标: < 5ms 响应时间
    """
    thread_id = await ThreadService.create_thread(
        thread_id=thread_create_request.thread_id,
        status=ThreadStatus.ACTIVE,
        metadata=ThreadMetadata(
            assistant_id=assistant_id,
            tenant_id=tenant.tenant_id
        )
    )


@router.post("")
async def create_message(
    message_create_request: MessageCreateRequest,
    thread_id: Annotated[UUID, Depends(get_thread_id)],
):
    """
    创建新的对话消息
    """
    message_id = await MessageService.create_message(
        thread_id=thread_id,
        message_id=message_create_request.message_id,
        role=message_create_request.role,
    )


@router.post("")
async def wait_for_message(
    thread_id: Annotated[UUID, Depends(get_thread_id)],
    message_id: Annotated[UUID, Depends(get_message_id)],
):
    """
    等待消息完成
    """
    message = await MessageService.wait_for_message(
        thread_id=thread_id,
        message_id=message_id,
    )
    if message.status == MessageStatus.FAILED:
        raise HTTPException(status_code=500, detail=message.content)