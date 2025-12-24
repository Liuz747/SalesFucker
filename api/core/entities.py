"""
工作流运行业务模型模块

支持LangGraph并发状态更新和并行节点执行。
"""

from collections.abc import Mapping
from datetime import datetime
import operator
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from libs.types import MessageParams, OutputContentParams, OutputType
from utils import get_current_datetime


# ==============================
# LangGraph Reducer 函数定义
# ==============================

def safe_merge_dict(left: Optional[dict], right: Optional[dict]) -> Optional[dict]:
    """
    安全的字典合并Reducer函数

    用于处理多个agents同时更新字典类型字段的冲突。
    采用后写入优先策略，并确保不修改原始对象。
    """
    if left is None and right is None:
        return None
    if left is None:
        return right
    if right is None:
        return left

    # 创建新的合并结果，避免修改原对象
    result = left.copy()
    result.update(right)
    return result


def merge_agent_results(left: Optional[dict], right: Optional[dict]) -> Optional[dict]:
    """
    专门的agent结果合并Reducer函数

    特殊处理agent_responses字段，确保所有agents的输出都被正确收集。
    """
    if left is None:
        return right
    if right is None:
        return left

    result = left.copy()

    # 特殊处理agent_responses字段
    if isinstance(right, dict) and "agent_responses" in right:
        if not isinstance(result, dict):
            result = {}
        if "agent_responses" not in result:
            result["agent_responses"] = {}
        elif result["agent_responses"] is None:
            result["agent_responses"] = {}

        # 合并agent_responses，确保所有agents的输出都被保存
        if isinstance(right["agent_responses"], dict):
            result["agent_responses"].update(right["agent_responses"])
            # 从right中移除已处理的agent_responses，避免重复
            right_copy = right.copy()
            del right_copy["agent_responses"]
            result.update(right_copy)
        else:
            result.update(right)
    else:
        result.update(right)

    return result


def merge_list(left: Optional[list], right: Optional[list]) -> Optional[list]:
    """
    列表合并Reducer函数 - 使用operator.add
    """
    if left is None:
        return right
    if right is None:
        return left
    return left + right



class WorkflowExecutionModel(BaseModel):
    """
    支持并行执行的工作流执行模型

    兼容现有API的同时支持LangGraph的并发状态管理。
    使用Reducer机制处理多agents同时更新状态的问题。
    """

    workflow_id: UUID = Field(description="工作流标识符")
    thread_id: UUID = Field(description="线程标识符")
    assistant_id: UUID = Field(description="助手标识符")
    tenant_id: str = Field(description="租户标识符")

    input: MessageParams | None = Field(description="输入消息列表")
    output: Optional[str] = Field(default=None, description="文本输出内容")

    # 多模态输出 - 支持音频、图像、视频等
    multimodal_outputs: Optional[OutputContentParams] = Field(
        default=None,
        description="多模态输出列表（音频、图像、视频等）"
    )
    actions: Optional[list[OutputType]] = Field(
        default=None,
        description="输出类型列表，例如：['output_audio', 'output_image']"
    )

    # Token 统计字段
    input_tokens: Annotated[int, operator.add] = Field(default=0, description="输入Token数")
    output_tokens: Annotated[int, operator.add] = Field(default=0, description="输出Token数")
    total_tokens: Optional[int] = Field(default=None, description="总Token数")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    exception_count: int = Field(default=0, description="异常次数")

    started_at: datetime = Field(default_factory=get_current_datetime, description="开始时间")
    finished_at: Optional[datetime] = Field(default=None, description="结束时间")

    sentiment_analysis: Annotated[Optional[dict], safe_merge_dict] = Field(default=None)
    appointment_intent: Annotated[Optional[dict], safe_merge_dict] = Field(default=None)
    material_intent: Annotated[Optional[dict], safe_merge_dict] = Field(default=None)

    values: Annotated[Optional[dict], merge_agent_results] = Field(default=None, description="工作流节点交互的状态")
    
    # 传递业务输出
    business_outputs: Optional[dict] = Field(default=None, description="结构化业务输出")

    active_agents: Annotated[Optional[list], merge_list] = Field(default=None)

    # 工作流状态字段
    journey_stage: Optional[str] = Field(default=None, description="客户旅程阶段")
    matched_prompt: Optional[dict] = Field(default=None, description="匹配的提示词信息")

    # 触发事件元数据
    trigger_metadata: Mapping | None = Field(default=None, description="触发事件元数据：event_type, services等")

    model_config = {
        "arbitrary_types_allowed": True
    }
