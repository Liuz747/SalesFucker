"""
对话处理相关数据模型

该模块定义了对话处理相关的请求和响应数据模型，支持多种输入类型
和完整的对话生命周期管理。

核心模型:
- ConversationRequest: 对话请求
- ConversationResponse: 对话响应
- ConversationHistoryRequest: 历史查询请求
- ConversationHistoryResponse: 历史查询响应
- ConversationStatusResponse: 对话状态响应
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .requests import BaseRequest
from .responses import PaginatedResponse, SuccessResponse


class InputType(str, Enum):
    """输入类型枚举"""

    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    MULTIMODAL = "multimodal"


class ConversationStatus(str, Enum):
    """对话状态枚举"""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"
    PAUSED = "paused"


class ComplianceStatus(str, Enum):
    """合规状态枚举"""

    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"
    REVIEW_REQUIRED = "review_required"


class ConversationRequest(BaseRequest):
    """
    对话处理请求模型
    
    注意: 由后端服务提供租户ID以确保数据隔离
    """

    tenant_id: str = Field(
        description="租户标识符", min_length=1, max_length=100
    )

    assistant_id: str = Field(
        description="销售助理标识符", min_length=1, max_length=100
    )

    device_id: str = Field(description="设备标识符", min_length=1, max_length=100)

    customer_id: Optional[str] = Field(
        None, description="客户标识符", min_length=1, max_length=100
    )

    message: str = Field(description="客户消息内容", min_length=1, max_length=4000)

    input_type: InputType = Field(default=InputType.TEXT, description="输入类型")

    thread_id: Optional[str] = Field(None, description="对话ID（继续现有对话时提供）")

    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="对话上下文信息"
    )

    # LLM配置
    preferred_provider: Optional[str] = Field(None, description="首选LLM供应商")

    model_name: Optional[str] = Field(None, description="指定模型名称")

    routing_strategy: Optional[str] = Field(
        None,
        description="路由策略",
        pattern="^(cost_optimized|performance_optimized|agent_optimized|round_robin)$",
    )

    # 处理选项
    enable_memory: bool = Field(True, description="是否启用记忆功能")

    enable_compliance_check: bool = Field(True, description="是否启用合规性检查")

    enable_sentiment_analysis: bool = Field(True, description="是否启用情感分析")

    # 多模态附件
    attachments: Optional[List[Dict[str, Any]]] = Field(
        None, description="附件信息（文件ID、类型等）"
    )

    @field_validator("message")
    def validate_message(cls, v):
        """验证消息内容"""
        if not v.strip():
            raise ValueError("消息内容不能为空")
        return v.strip()


class ConversationStartRequest(BaseRequest):
    """
    开始新对话请求模型
    
    注意: 由后端服务提供租户ID以确保数据隔离
    """
    tenant_id: str = Field(description="租户标识符", min_length=1, max_length=100)
    assistant_id: str = Field(description="销售助理ID")
    device_id: str = Field(description="设备ID")
    customer_id: Optional[str] = Field(None, description="客户ID")
    initial_message: Optional[str] = Field(None, description="初始消息")

    customer_profile: Optional[Dict[str, Any]] = Field(None, description="客户档案信息")

    conversation_type: str = Field(
        default="general",
        description="对话类型",
        pattern="^(general|consultation|support|sales)$",
    )


class ConversationHistoryRequest(BaseRequest):
    """
    对话历史查询请求模型
    
    注意: 由后端服务提供租户ID以确保数据隔离
    """
    tenant_id: str = Field(description="租户标识符", min_length=1, max_length=100)
    assistant_id: Optional[str] = Field(None, description="销售助理ID")
    device_id: Optional[str] = Field(None, description="设备ID")
    customer_id: Optional[str] = Field(None, description="客户ID")
    thread_id: Optional[str] = Field(None, description="对话ID")

    # 时间范围
    start_date: Optional[datetime] = Field(None, description="开始时间")
    end_date: Optional[datetime] = Field(None, description="结束时间")

    # 筛选条件
    status: Optional[ConversationStatus] = Field(None, description="对话状态")
    input_type: Optional[InputType] = Field(None, description="输入类型")

    # 分页参数继承自BaseRequest
    include_messages: bool = Field(True, description="是否包含消息内容")
    include_agent_responses: bool = Field(False, description="是否包含智能体详细响应")


class MessageAttachment(BaseModel):
    """消息附件模型"""

    attachment_id: str = Field(description="附件ID")
    attachment_type: str = Field(
        description="附件类型", pattern="^(image|audio|document)$"
    )
    file_name: str = Field(description="文件名")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    mime_type: str = Field(description="MIME类型")
    url: Optional[str] = Field(None, description="访问URL")


class ConversationMessage(BaseModel):
    """对话消息模型"""

    message_id: str = Field(description="消息ID")
    sender: str = Field(description="发送者", pattern="^(customer|agent|system)$")
    content: str = Field(description="消息内容")
    input_type: InputType = Field(description="输入类型")
    timestamp: datetime = Field(description="消息时间")

    # 处理信息
    processing_time_ms: Optional[float] = Field(None, description="处理时间（毫秒）")
    agent_responses: Optional[Dict[str, Any]] = Field(
        None, description="智能体响应详情"
    )

    # 分析结果
    sentiment: Optional[Dict[str, Any]] = Field(None, description="情感分析结果")
    intent: Optional[Dict[str, Any]] = Field(None, description="意图分析结果")
    compliance_result: Optional[Dict[str, Any]] = Field(
        None, description="合规检查结果"
    )

    # 附件
    attachments: Optional[List[MessageAttachment]] = Field(None, description="消息附件")


# 响应模型


class ConversationResponse(SuccessResponse[Dict[str, Any]]):
    """
    对话处理响应模型
    """

    thread_id: str = Field(description="对话ID")
    response: str = Field(description="回复内容")
    processing_complete: bool = Field(description="处理是否完成")

    # 状态信息
    conversation_status: ConversationStatus = Field(
        default=ConversationStatus.ACTIVE, description="对话状态"
    )

    compliance_status: ComplianceStatus = Field(
        default=ComplianceStatus.APPROVED, description="合规状态"
    )

    # 处理详情
    agent_responses: Dict[str, Any] = Field(
        default_factory=dict, description="智能体响应详情"
    )

    processing_stats: Optional[Dict[str, Any]] = Field(None, description="处理统计信息")

    # 错误和升级
    error_state: Optional[str] = Field(None, description="错误状态")
    human_escalation: bool = Field(default=False, description="是否需要人工升级")
    escalation_reason: Optional[str] = Field(None, description="升级原因")

    # LLM使用信息
    llm_provider_used: Optional[str] = Field(None, description="实际使用的LLM供应商")
    model_used: Optional[str] = Field(None, description="实际使用的模型")
    processing_cost: Optional[float] = Field(None, description="处理成本（美元）")
    token_usage: Optional[Dict[str, int]] = Field(None, description="Token使用统计")

    # 后续建议
    suggested_actions: Optional[List[str]] = Field(None, description="建议的后续操作")
    next_questions: Optional[List[str]] = Field(None, description="推荐的后续问题")


class ConversationStartResponse(SuccessResponse[Dict[str, Any]]):
    """
    开始对话响应模型
    """

    thread_id: str = Field(description="对话ID")
    welcome_message: Optional[str] = Field(None, description="欢迎消息")
    conversation_status: ConversationStatus = Field(description="对话状态")

    # 初始化结果
    agents_initialized: List[str] = Field(description="已初始化的智能体列表")
    memory_loaded: bool = Field(description="是否加载了客户记忆")

    customer_profile: Optional[Dict[str, Any]] = Field(None, description="客户档案摘要")


class ConversationStatusResponse(SuccessResponse[Dict[str, Any]]):
    """
    对话状态响应模型
    """

    thread_id: str = Field(description="对话ID")
    status: ConversationStatus = Field(description="当前状态")

    # 基本信息
    tenant_id: str = Field(description="租户ID")
    assistant_id: Optional[str] = Field(None, description="销售助理ID")
    device_id: Optional[str] = Field(None, description="设备ID")
    customer_id: Optional[str] = Field(None, description="客户ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")

    # 统计信息
    message_count: int = Field(description="消息数量")
    total_processing_time: float = Field(description="总处理时间（秒）")

    # 当前状态详情
    active_agents: List[str] = Field(description="活跃智能体列表")
    pending_actions: List[str] = Field(description="待处理操作")

    # 性能指标
    average_response_time: float = Field(description="平均响应时间（毫秒）")
    satisfaction_score: Optional[float] = Field(None, description="满意度分数")


class ConversationHistoryResponse(PaginatedResponse[List[Dict[str, Any]]]):
    """
    对话历史响应模型
    """

    conversations: List[Dict[str, Any]] = Field(description="对话列表")

    # 聚合统计
    total_conversations: int = Field(description="总对话数")
    active_conversations: int = Field(description="活跃对话数")

    # 时间范围统计
    date_range: Dict[str, datetime] = Field(description="查询时间范围")

    # 过滤统计
    filter_summary: Dict[str, int] = Field(description="过滤条件统计")


class ConversationAnalyticsResponse(SuccessResponse[Dict[str, Any]]):
    """
    对话分析响应模型
    """

    # 基础统计
    total_conversations: int = Field(description="总对话数")
    total_messages: int = Field(description="总消息数")

    # 时间分布
    conversation_distribution: Dict[str, int] = Field(description="对话时间分布")
    peak_hours: List[int] = Field(description="高峰时段")

    # 性能指标
    average_response_time: float = Field(description="平均响应时间")
    completion_rate: float = Field(description="对话完成率")
    satisfaction_scores: Dict[str, float] = Field(description="满意度统计")

    # 智能体表现
    agent_performance: Dict[str, Dict[str, Any]] = Field(description="智能体性能统计")

    # 成本分析
    cost_analysis: Dict[str, float] = Field(description="成本分析")

    # 趋势数据
    trends: Dict[str, List[float]] = Field(description="趋势数据")


class ConversationExportRequest(BaseRequest):
    """
    对话导出请求模型
    
    注意: 由后端服务提供租户ID以确保数据隔离
    """

    tenant_id: str = Field(description="租户标识符", min_length=1, max_length=100)
    
    # 导出范围
    thread_ids: Optional[List[str]] = Field(None, description="指定对话ID列表")
    assistant_id: Optional[str] = Field(None, description="指定销售助理ID")
    device_id: Optional[str] = Field(None, description="指定设备ID")
    customer_id: Optional[str] = Field(None, description="指定客户ID")

    # 时间范围
    start_date: Optional[datetime] = Field(None, description="开始时间")
    end_date: Optional[datetime] = Field(None, description="结束时间")

    # 导出选项
    export_format: str = Field(
        default="json", description="导出格式", pattern="^(json|csv|excel|pdf)$"
    )

    include_attachments: bool = Field(False, description="是否包含附件")
    include_agent_details: bool = Field(False, description="是否包含智能体详情")

    # 隐私选项
    anonymize_customer_data: bool = Field(False, description="是否匿名化客户数据")


class ConversationExportResponse(SuccessResponse[Dict[str, Any]]):
    """
    对话导出响应模型
    """

    export_id: str = Field(description="导出任务ID")
    download_url: Optional[str] = Field(None, description="下载链接")

    # 导出统计
    total_conversations: int = Field(description="导出对话数")
    total_messages: int = Field(description="导出消息数")
    file_size_mb: float = Field(description="文件大小（MB）")

    # 状态信息
    export_status: str = Field(description="导出状态")
    estimated_completion: Optional[datetime] = Field(None, description="预计完成时间")
    expires_at: Optional[datetime] = Field(None, description="下载链接过期时间")
