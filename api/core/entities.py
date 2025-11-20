"""
工作流运行业务模型模块

支持LangGraph并发状态更新和并行节点执行。
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Any, Optional
from uuid import UUID
from typing_extensions import TypedDict
import operator

from pydantic import BaseModel, Field

from libs.types import InputContentParams, OutputContentParams, OutputType
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


# ==============================
# LangGraph 状态类型定义
# ==============================

class WorkflowState(TypedDict):
    """
    LangGraph工作流状态类型定义

    使用Annotated类型和Reducer函数支持并发状态更新。
    """
    # 基础字段
    workflow_id: str
    thread_id: str
    tenant_id: str
    input: Any

    # 并行节点专用字段 - 使用Reducer避免并发冲突
    sentiment_analysis: Annotated[Optional[dict], safe_merge_dict]
    appointment_intent: Annotated[Optional[dict], safe_merge_dict]
    material_intent: Annotated[Optional[dict], safe_merge_dict]

    # 统一的状态收集器 - 使用专门的Reducer
    values: Annotated[Optional[dict], merge_agent_results]

    # 全局状态字段
    journey_stage: Optional[str]
    matched_prompt: Optional[dict]

    # 元数据字段
    total_tokens: Optional[int]
    error_message: Optional[str]
    exception_count: int
    started_at: str
    finished_at: Optional[str]

    # 并行执行控制
    parallel_execution: Optional[dict]
    active_agents: Annotated[Optional[list], merge_list]


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

    input: InputContentParams = Field(description="输入内容")
    output: Optional[str] = Field(default=None, description="文本输出内容")
    values: Optional[Mapping[str, Any]] = Field(default=None, description="工作流节点交互的状态")

    # 多模态输出 - 支持音频、图像、视频等
    multimodal_outputs: Optional[OutputContentParams] = Field(
        default=None,
        description="多模态输出列表（音频、图像、视频等）"
    )
    actions: Optional[list[OutputType]] = Field(
        default=None,
        description="输出类型列表，例如：['output_audio', 'output_image']"
    )

    total_tokens: Optional[int] = Field(default=None, description="总Token数")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    exception_count: int = Field(default=0, description="异常次数")

    started_at: datetime = Field(default_factory=get_current_datetime, description="开始时间")
    finished_at: Optional[datetime] = Field(default=None, description="结束时间")

    def to_workflow_state(self) -> dict:
        """
        转换为LangGraph状态类型（字典）

        确保在LangGraph中能正确处理并发状态更新，解决Pydantic模型与LangGraph不匹配的问题。
        """
        return {
            # 基础字段
            "workflow_id": str(self.workflow_id),
            "thread_id": str(self.thread_id),
            "tenant_id": self.tenant_id,
            "input": self.input,

            # 并行节点专用字段 - 使用Reducer避免并发冲突
            "sentiment_analysis": self.sentiment_analysis,
            "appointment_intent": self.appointment_intent,
            "material_intent": self.material_intent,

            # 统一的状态收集器
            "values": dict(self.values) if self.values else None,

            # 全局状态字段
            "journey_stage": self.journey_stage,
            "matched_prompt": self.matched_prompt,

            # 元数据字段
            "total_tokens": self.total_tokens,
            "error_message": self.error_message,
            "exception_count": self.exception_count,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,

            # 并行执行控制
            "parallel_execution": self.parallel_execution,
            "active_agents": self.active_agents or []
        }

    @classmethod
    def from_workflow_state(cls, state: dict) -> "WorkflowExecutionModel":
        """
        从LangGraph状态创建执行模型实例

        支持从并发更新的状态中恢复数据，将字典状态转换回Pydantic模型。
        """
        # 处理基本字段
        basic_fields = {
            "workflow_id": state.get("workflow_id"),
            "thread_id": state.get("thread_id"),
            "tenant_id": state.get("tenant_id"),
            "input": state.get("input"),
            "total_tokens": state.get("total_tokens"),
            "error_message": state.get("error_message"),
            "exception_count": state.get("exception_count", 0),
            "parallel_execution": state.get("parallel_execution"),
            "active_agents": state.get("active_agents")
        }

        # 处理时间字段
        if state.get("started_at"):
            basic_fields["started_at"] = datetime.fromisoformat(state["started_at"])
        if state.get("finished_at"):
            basic_fields["finished_at"] = datetime.fromisoformat(state["finished_at"])

        # 处理并行节点字段 - 这些字段已经通过Reducer合并
        parallel_fields = {
            "sentiment_analysis": state.get("sentiment_analysis"),
            "appointment_intent": state.get("appointment_intent"),
            "material_intent": state.get("material_intent"),
            "journey_stage": state.get("journey_stage"),
            "matched_prompt": state.get("matched_prompt"),
            "values": state.get("values")
        }

        # 合并所有字段
        all_fields = {**basic_fields, **parallel_fields}

        # 过滤None值并转换UUID字符串为UUID对象
        filtered_fields = {}
        for k, v in all_fields.items():
            if v is not None:
                if k in ["workflow_id", "thread_id", "assistant_id"] and isinstance(v, str):
                    # 转换字符串UUID为UUID对象
                    try:
                        from uuid import UUID
                        filtered_fields[k] = UUID(v)
                    except ValueError:
                        # 如果转换失败，保持原值
                        filtered_fields[k] = v
                else:
                    filtered_fields[k] = v

        return cls(**filtered_fields)
