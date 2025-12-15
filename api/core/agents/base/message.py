"""
智能体消息系统模块

该模块定义了多智能体系统中的消息类型和通信架构。

核心功能:
- 智能体间消息格式标准化
- 对话状态管理
- 多租户上下文处理
- 消息优先级和路由
"""

from typing import Any
from pydantic import BaseModel, Field

from libs.types import MessageType


class AgentMessage(BaseModel):
    """
    智能体消息标准格式类
    
    定义智能体之间通信的标准消息格式，包含完整的上下文信息和元数据。
    支持多种消息类型和优先级管理。
    
    属性:
        sender: 发送方智能体ID
        message_type: 消息类型(查询/响应/通知/触发/建议)
        context: 消息上下文信息
        payload: 消息特定数据载荷
    """
    
    # 消息基本信息
    sender: str = Field(description="发送方智能体的唯一标识符")
    message_type: MessageType = Field(
        description="消息类型：query=查询, response=响应, notification=通知, trigger=触发, suggestion=建议"
    )
    
    # 上下文信息
    context: dict[str, Any] = Field(
        default_factory=dict, 
        description="消息上下文信息，包含处理消息所需的环境数据"
    )
    # 消息内容
    payload: dict[str, Any] = Field(
        default_factory=dict, 
        description="消息特定数据载荷，包含具体的处理数据"
    )
