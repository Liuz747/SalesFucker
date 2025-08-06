"""
消息构建助手模块
"""

import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from .models import ConversationMessage, MessageType


class MessageBuilder:
    """消息构建助手类"""
    
    @staticmethod
    def create_user_message(
        thread_id: str,
        tenant_id: str,
        customer_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """创建用户文本消息"""
        return ConversationMessage(
            message_id=str(uuid.uuid4()),
            thread_id=thread_id,
            tenant_id=tenant_id,
            customer_id=customer_id,
            message_type=MessageType.USER_TEXT,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.utcnow()
        )
    
    @staticmethod
    def create_llm_response(
        thread_id: str,
        tenant_id: str,
        customer_id: str,
        content: str,
        model_name: str,
        tokens_used: int,
        processing_time_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """创建LLM响应消息"""
        return ConversationMessage(
            message_id=str(uuid.uuid4()),
            thread_id=thread_id,
            tenant_id=tenant_id,
            customer_id=customer_id,
            message_type=MessageType.LLM_RESPONSE,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.utcnow(),
            model_name=model_name,
            tokens_used=tokens_used,
            processing_time_ms=processing_time_ms
        )
    
    @staticmethod
    def create_multimodal_message(
        thread_id: str,
        tenant_id: str,
        customer_id: str,
        content: Union[str, Dict[str, Any]],
        message_type: MessageType,
        attachments: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """创建多模态消息"""
        return ConversationMessage(
            message_id=str(uuid.uuid4()),
            thread_id=thread_id,
            tenant_id=tenant_id,
            customer_id=customer_id,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.utcnow(),
            attachments=attachments
        )


# 工厂函数
async def create_conversation_store(tenant_id: str, elasticsearch_url: str):
    """创建并初始化对话存储实例"""
    from .conversation_store import ConversationStore
    
    store = ConversationStore(tenant_id)
    await store.initialize(elasticsearch_url)
    return store