"""
智能体消息系统模块

该模块定义了多智能体系统中的消息类型和通信架构。

核心功能:
- 智能体间消息格式标准化
- 对话状态管理
- 多租户上下文处理
- 消息优先级和路由
"""

import uuid
from typing import Any, Optional
from pydantic import BaseModel, Field

from libs.constants import MessageConstants
from libs.types import MessageType, InputType


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


class ThreadState(BaseModel):
    """
    对话状态管理类
    
    管理整个对话过程中的状态信息，包含客户输入、智能体处理结果
    和最终响应。支持多智能体协同处理和状态同步。
    
    属性:
        thread_id: 对话唯一标识符
        session_id: 会话标识符
        tenant_id: 租户标识符
        assistant_id: 销售助理标识符
        device_id: 设备标识符
        customer_id: 客户标识符
        customer_input: 客户输入内容
        input_type: 输入类型(文本/语音/图片)
        input_metadata: 输入元数据
        compliance_result: 合规审查结果
        sentiment_analysis: 情感分析结果
        intent_analysis: 意图分析结果
        active_agents: 活跃智能体列表
        agent_responses: 智能体响应集合
        customer_profile: 客户档案信息
        thread_history: 对话历史记录
        final_response: 最终响应内容
        response_metadata: 响应元数据
        processing_complete: 处理完成标志
        error_state: 错误状态信息
        human_escalation: 人工升级标志
    """
    
    # 标识符
    thread_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="对话唯一标识符"
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="用户会话标识符"
    )
    tenant_id: str = Field(description="多租户标识符")
    assistant_id: Optional[str] = Field(None, description="销售助理标识符，用于区分租户内不同的销售人员")
    device_id: Optional[str] = Field(None, description="设备标识符，用于区分销售助理使用的不同终端设备")
    customer_id: Optional[str] = Field(None, description="客户唯一标识符")
    
    # 客户输入
    customer_input: str = Field("", description="客户当前输入的消息内容")
    input_type: InputType = Field(
        MessageConstants.TEXT_INPUT, 
        description="输入类型：text=文本, voice=语音, image=图片"
    )
    input_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="输入相关的元数据信息"
    )
    
    # 分析结果
    compliance_result: dict[str, Any] = Field(
        default_factory=dict,
        description="合规审查处理结果，包含违规检测和处理建议"
    )
    sentiment_analysis: dict[str, Any] = Field(
        default_factory=dict,
        description="情感分析结果，包含情感倾向和强度"
    )
    intent_analysis: dict[str, Any] = Field(
        default_factory=dict,
        description="意图分析结果，包含客户意图分类和置信度"
    )
    
    # 智能体处理
    active_agents: list[str] = Field(
        default_factory=list,
        description="当前处理对话的活跃智能体ID列表"
    )
    agent_responses: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="各智能体的处理响应结果集合"
    )
    
    # 客户上下文
    customer_profile: dict[str, Any] = Field(
        default_factory=dict,
        description="客户档案信息，包含偏好、历史和个人信息"
    )
    thread_history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="对话历史记录列表"
    )
    conversation_history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="对话历史记录"
    )
    
    # 智能体特定状态
    strategy_hints: dict[str, Any] = Field(
        default_factory=dict,
        description="市场策略提示信息"
    )
    sales_response: str = Field("", description="销售智能体响应")
    
    # 最终响应
    final_response: str = Field("", description="系统最终响应给客户的内容")
    response_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="响应相关的元数据信息"
    )
    
    # 系统状态
    processing_complete: bool = Field(False, description="对话处理完成标志")
    error_state: Optional[str] = Field(None, description="错误状态信息")
    human_escalation: bool = Field(False, description="是否需要人工升级处理")
