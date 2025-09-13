"""
对话消息数据模型
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class MessageType(Enum):
    """消息类型枚举"""
    USER_TEXT = "user_text"
    USER_VOICE = "user_voice"  
    USER_IMAGE = "user_image"
    LLM_RESPONSE = "llm_response"
    SYSTEM_EVENT = "system_event"
    AGENT_INTERNAL = "agent_internal"


class MessageStatus(Enum):
    """消息状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ConversationMessage:
    """标准化对话消息结构"""
    message_id: str
    thread_id: str
    tenant_id: str
    assistant_id: str
    device_id: str
    customer_id: str
    message_type: MessageType
    content: Union[str, Dict[str, Any]]
    metadata: Dict[str, Any]
    timestamp: datetime
    status: MessageStatus = MessageStatus.COMPLETED
    
    # LLM响应特有字段
    model_name: Optional[str] = None
    tokens_used: Optional[int] = None
    processing_time_ms: Optional[float] = None
    
    # 多模态内容
    attachments: Optional[List[Dict[str, Any]]] = None
    
    # 情感和意图分析结果
    sentiment_score: Optional[float] = None
    intent_categories: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式用于存储"""
        data = asdict(self)
        data['message_type'] = self.message_type.value
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """从字典创建消息对象"""
        data['message_type'] = MessageType(data['message_type'])
        data['status'] = MessageStatus(data['status'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)