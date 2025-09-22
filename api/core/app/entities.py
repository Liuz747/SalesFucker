from datetime import datetime
from uuid import UUID
from typing import Any, Optional

from pydantic import BaseModel, Field
from utils import get_current_datetime


class WorkflowExecutionModel(BaseModel):
    """工作流执行模型"""

    workflow_id: UUID = Field(description="工作流标识符")
    thread_id: UUID = Field(description="线程标识符")
    assistant_id: UUID = Field(description="助手标识符")
    tenant_id: str = Field(description="租户标识符")
    input: str = Field(description="输入内容")
    type: str = Field(default="text", description="输入类型")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    
    # LangGraph 状态字段（与工作流节点交互的状态）
    customer_input: str = Field(default="", description="客户原始输入内容")
    input_type: str = Field(default="text", description="输入类型（与状态兼容）")
    compliance_result: dict[str, Any] = Field(default_factory=dict, description="合规检查结果")
    sentiment_analysis: dict[str, Any] = Field(default_factory=dict, description="情感分析结果")
    intent_analysis: dict[str, Any] = Field(default_factory=dict, description="意图分析结果")
    market_strategy: dict[str, Any] = Field(default_factory=dict, description="市场策略结果")
    product_recommendations: dict[str, Any] = Field(default_factory=dict, description="产品推荐结果")
    memory_update: dict[str, Any] = Field(default_factory=dict, description="记忆更新结果")
    agent_responses: dict[str, Any] = Field(default_factory=dict, description="各智能体响应结果")
    final_response: str = Field(default="", description="最终响应内容")
    processing_complete: bool = Field(default=False, description="是否处理完成")
    error_state: Optional[str] = Field(default=None, description="错误状态标识（如存在）")
    blocked_by_compliance: bool = Field(default=False, description="是否被合规系统阻止")
    timestamp: Optional[datetime] = Field(default=None, description="可选的状态时间戳")