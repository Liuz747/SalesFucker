"""
智能体消息系统模块

该模块定义了多智能体系统中的消息类型和通信架构。

核心功能:
- 智能体间消息格式标准化
- 对话状态管理
- 多租户上下文处理
- 消息优先级和路由
"""

from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from src.utils import MessageConstants, StatusConstants, WorkflowConstants, get_current_datetime


class AgentMessage(BaseModel):
    """
    智能体消息标准格式类
    
    定义智能体之间通信的标准消息格式，包含完整的上下文信息和元数据。
    支持多种消息类型和优先级管理。
    
    属性:
        message_id: 消息唯一标识符
        sender: 发送方智能体ID
        recipient: 接收方智能体ID
        message_type: 消息类型(查询/响应/通知/触发/建议)
        context: 消息上下文信息
        tenant_id: 多租户标识符
        customer_id: 客户标识符
        conversation_id: 对话标识符
        session_id: 会话标识符
        sentiment_score: 客户情感分数(-1到1)
        intent_classification: 客户意图分类
        compliance_status: 合规审查状态
        market_strategy: 选定的市场策略
        payload: 消息特定数据载荷
        timestamp: 消息时间戳
        priority: 消息优先级
        human_loop_required: 是否需要人工干预
    """
    
    # 消息基本信息
    message_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="消息唯一标识符，自动生成UUID"
    )
    sender: str = Field(description="发送方智能体的唯一标识符")
    recipient: str = Field(description="接收方智能体的唯一标识符")
    message_type: Literal["query", "response", "notification", "trigger", "suggestion"] = Field(
        description="消息类型：query=查询, response=响应, notification=通知, trigger=触发, suggestion=建议"
    )
    
    # 上下文信息
    context: Dict[str, Any] = Field(
        default_factory=dict, 
        description="消息上下文信息，包含处理消息所需的环境数据"
    )
    tenant_id: Optional[str] = Field(None, description="多租户标识符，用于区分不同的化妆品品牌")
    customer_id: Optional[str] = Field(None, description="客户唯一标识符")
    conversation_id: Optional[str] = Field(None, description="对话会话标识符")
    session_id: Optional[str] = Field(None, description="用户会话标识符")
    
    # 分析上下文
    sentiment_score: Optional[float] = Field(
        None, 
        description="客户情感分数，范围-1(负面)到1(正面)，0为中性"
    )
    intent_classification: Optional[str] = Field(None, description="客户意图分类结果")
    compliance_status: Literal["approved", "flagged", "blocked"] = Field(
        StatusConstants.APPROVED, 
        description="合规审查状态：approved=通过, flagged=标记, blocked=阻止"
    )
    market_strategy: Optional[Literal["premium", "budget", "youth", "mature"]] = Field(
        None, 
        description="选定的市场策略：premium=高端, budget=预算, youth=年轻, mature=成熟"
    )
    
    # 消息内容
    payload: Dict[str, Any] = Field(
        default_factory=dict, 
        description="消息特定数据载荷，包含具体的处理数据"
    )
    
    # 元数据
    timestamp: datetime = Field(
        default_factory=get_current_datetime,
        description="消息创建时间戳"
    )
    priority: Literal["low", "medium", "high", "urgent"] = Field(
        "medium", 
        description="消息优先级：low=低, medium=中, high=高, urgent=紧急"
    )
    human_loop_required: bool = Field(
        False, 
        description="是否需要人工干预标志"
    )


class ConversationState(BaseModel):
    """
    对话状态管理类
    
    管理整个对话过程中的状态信息，包含客户输入、智能体处理结果
    和最终响应。支持多智能体协同处理和状态同步。
    
    属性:
        conversation_id: 对话唯一标识符
        session_id: 会话标识符
        tenant_id: 租户标识符
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
        conversation_history: 对话历史记录
        final_response: 最终响应内容
        response_metadata: 响应元数据
        processing_complete: 处理完成标志
        error_state: 错误状态信息
        human_escalation: 人工升级标志
    """
    
    # 标识符
    conversation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="对话唯一标识符"
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="用户会话标识符"
    )
    tenant_id: str = Field(description="多租户标识符，区分不同化妆品品牌")
    customer_id: Optional[str] = Field(None, description="客户唯一标识符")
    
    # 客户输入
    customer_input: str = Field("", description="客户当前输入的消息内容")
    input_type: Literal["text", "voice", "image"] = Field(
        "text", 
        description="输入类型：text=文本, voice=语音, image=图片"
    )
    input_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="输入相关的元数据信息"
    )
    
    # 分析结果
    compliance_result: Dict[str, Any] = Field(
        default_factory=dict,
        description="合规审查处理结果，包含违规检测和处理建议"
    )
    sentiment_analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="情感分析结果，包含情感倾向和强度"
    )
    intent_analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="意图分析结果，包含客户意图分类和置信度"
    )
    
    # 智能体处理
    active_agents: List[str] = Field(
        default_factory=list,
        description="当前处理对话的活跃智能体ID列表"
    )
    agent_responses: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="各智能体的处理响应结果集合"
    )
    
    # 客户上下文
    customer_profile: Dict[str, Any] = Field(
        default_factory=dict,
        description="客户档案信息，包含偏好、历史和个人信息"
    )
    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="对话历史记录列表"
    )
    
    # 最终响应
    final_response: str = Field("", description="系统最终响应给客户的内容")
    response_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="响应相关的元数据信息"
    )
    
    # 系统状态
    processing_complete: bool = Field(False, description="对话处理完成标志")
    error_state: Optional[str] = Field(None, description="错误状态信息")
    human_escalation: bool = Field(False, description="是否需要人工升级处理")


# 验证函数：使用常量进行运行时验证
def validate_message_type(message_type: str) -> bool:
    """验证消息类型是否有效"""
    valid_types = [
        MessageConstants.QUERY,
        MessageConstants.RESPONSE,
        MessageConstants.NOTIFICATION,
        MessageConstants.TRIGGER,
        MessageConstants.SUGGESTION
    ]
    return message_type in valid_types


def validate_compliance_status(status: str) -> bool:
    """验证合规状态是否有效"""
    valid_statuses = [
        StatusConstants.APPROVED,
        StatusConstants.FLAGGED,
        StatusConstants.BLOCKED
    ]
    return status in valid_statuses


def validate_market_strategy(strategy: str) -> bool:
    """验证市场策略是否有效"""
    valid_strategies = [
        WorkflowConstants.PREMIUM_STRATEGY,
        WorkflowConstants.BUDGET_STRATEGY,
        WorkflowConstants.YOUTH_STRATEGY,
        WorkflowConstants.MATURE_STRATEGY
    ]
    return strategy in valid_strategies 