"""
情景记忆存储工具

存储情景记忆（事实、个人偏好或用户特定事件）到长期记忆。
"""

from typing import Any
from uuid import UUID

from core.memory import StorageManager
from utils import get_component_logger

logger = get_component_logger(__name__)


async def store_episodic(
    tenant_id: str,
    thread_id: UUID,
    content: str,
    tags: list[str] = None,
    metadata: dict[str, Any] = None
) -> dict[str, Any]:
    """
    存储情景记忆到长期记忆系统

    用于存储重要的用户偏好、事实信息或特定事件，以便后续检索使用。

    Args:
        tenant_id: 租户标识符，用于数据隔离
        thread_id: 线程ID，用于关联对话上下文
        content: 要存储的记忆内容
        tags: 可选的标签列表，用于分类和检索
        metadata: 可选的元数据字典，存储额外信息

    Returns:
        dict: 包含存储结果的响应字典
            - success: bool, 是否成功
            - doc_id: str, 存储的文档ID
            - message: str, 操作结果描述
    """
    try:
        logger.info(f"开始存储情景记忆 - 租户: {tenant_id}, 线程: {thread_id}")

        # 初始化存储管理器
        storage_manager = StorageManager()

        # 执行存储
        doc_id = await storage_manager.add_episodic_memory(
            tenant_id=tenant_id,
            thread_id=thread_id,
            content=content,
            tags=tags,
            metadata=metadata
        )

        response = {
            "success": True,
            "doc_id": doc_id,
            "message": f"情景记忆已成功存储，文档ID: {doc_id}"
        }

        logger.info(f"情景记忆存储完成 - 文档ID: {doc_id}")
        return response

    except Exception as e:
        logger.error(f"情景记忆存储失败: {e}")
        return {
            "success": False,
            "doc_id": None,
            "message": f"存储失败: {str(e)}",
            "error": str(e)
        }