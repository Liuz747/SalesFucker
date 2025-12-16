"""
工具注册表

管理所有可用工具的定义和处理函数映射。
"""

from collections.abc import Callable
from typing import Any

from utils import get_component_logger

from .entities import ToolArgument, ToolDefinition
from .search_context import search_conversation_context
from .store_episodic import store_episodic_memory

logger = get_component_logger(__name__)


# =============================================================================
# 工具定义
# =============================================================================

long_term_memory_tool = ToolDefinition(
    name="long_term_memory_retrieve",
    description="在长期记忆中按关键字搜索用户的历史对话摘要和偏好。当用户询问过去的交互或存储的偏好时使用。",
    arguments=[
        ToolArgument("tenant_id", "string", "租户ID，用于隔离存储和检索数据"),
        ToolArgument("thread_id", "string", "线程ID，用于限定搜索范围"),
        ToolArgument("query", "string", "搜索查询内容"),
        ToolArgument("limit", "integer", "最多返回条数，默认5", required=False)
    ],
)


store_episodic_memory_tool = ToolDefinition(
    name="store_episodic_memory",
    description="保存重要的用户信息供将来参考。当用户分享偏好、个人信息或重要事实时使用。",
    arguments=[
        ToolArgument("tenant_id", "string", "租户ID，用于隔离存储和检索数据"),
        ToolArgument("thread_id", "string", "线程ID，用于关联对话上下文"),
        ToolArgument("content", "string", "要存储的记忆内容"),
        ToolArgument("importance_score", "number", "记忆的相对重要程度，范围0-1", required=False),
        ToolArgument("tags", "array", "标签列表，用于分类和检索", required=False),
        ToolArgument("metadata", "object", "元数据字典，存储额外信息", required=False)
    ],
)


rag_retrieve_tool = ToolDefinition(
    name="rag_retrieve_context",
    description="Retrieve relevant context for answering questions using hybrid search (vector + keyword).",
    arguments=[
        ToolArgument("query", "string", "Natural language question to search for."),
        ToolArgument("top_k", "integer", "Number of context documents to return.", required=False),
    ],
)


trigger_workflow_tool = ToolDefinition(
    name="trigger_temporal_workflow",
    description="Trigger an asynchronous Temporal workflow for background task execution.",
    arguments=[
        ToolArgument("workflow_name", "string", "Name of the Temporal workflow."),
        ToolArgument("payload", "object", "JSON payload to pass to the workflow."),
    ],
)


# =============================================================================
# 工具处理函数注册表
# =============================================================================

TOOL_HANDLERS: dict[str, Callable] = {
    "long_term_memory_retrieve": search_conversation_context,
    "store_episodic_memory": store_episodic_memory,
    # "rag_retrieve_context": rag_retrieve,
    # "trigger_temporal_workflow": trigger_workflow,
}


def get_handler(tool_name: str) -> Callable:
    """获取指定工具名称的处理函数。

    Args:
        tool_name: 要获取处理函数的工具名称。

    Returns:
        指定工具的处理函数。

    Raises:
        ValueError: 如果工具名称在注册表中未找到。
    """
    if tool_name not in TOOL_HANDLERS:
        raise ValueError(f"未知工具: {tool_name}")

    return TOOL_HANDLERS[tool_name]


def get_tools_schema(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    """将工具定义列表转换为 OpenAI API 格式的 schema。

    Args:
        tools: 工具定义列表

    Returns:
        OpenAI tools 格式的列表
    """
    return [tool.to_openai_tool() for tool in tools]
