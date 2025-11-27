from collections.abc import Callable

from .entities import ToolArgument, ToolDefinition
# from .rag_retrieve import rag_retrieve
from .search_context import search_context
from .store_episodic import store_episodic
# from .trigger_workflow import trigger_workflow


long_term_memory_tool = ToolDefinition(
    name="long_term_memory_retrieve",
    description="在长期记忆（Elasticsearch）中按关键字搜索摘要。",
    arguments=[
        ToolArgument("tenant_id", "string", "租户ID，用于隔离存储和检索数据"),
        ToolArgument("thread_id", "UUID", "线程ID，用于限定搜索范围"),
        ToolArgument("query", "string", "查询内容"),
        ToolArgument("limit", "integer", "最多返回条数，默认5（可选）")
    ],
)


store_episodic_memory_tool = ToolDefinition(
    name="store_episodic_memory",
    description="存储情景记忆（事实、个人偏好或用户特定事件）到长期记忆系统。",
    arguments=[
        ToolArgument("tenant_id", "string", "租户ID，用于数据隔离"),
        ToolArgument("thread_id", "UUID", "线程ID，用于关联对话上下文"),
        ToolArgument("content", "string", "要存储的记忆内容"),
        ToolArgument("tags", "array", "标签列表，用于分类和检索（可选）"),
        ToolArgument("metadata", "object", "元数据字典，存储额外信息（可选）")
    ],
)


rag_retrieve_tool = ToolDefinition(
    name="rag_retrieve_context",
    description="Retrieve relevant context for answering questions using hybrid search (vector + keyword).",
    arguments=[
        ToolArgument("tenant_id", "string", "Tenant identifier."),
        ToolArgument("query", "string", "Natural language question to search for."),
        ToolArgument("top_k", "integer", "Number of context documents to return."),
    ],
)


trigger_workflow_tool = ToolDefinition(
    name="trigger_temporal_workflow",
    description="Trigger an asynchronous Temporal workflow for background task execution.",
    arguments=[
        ToolArgument("tenant_id", "string", "Tenant identifier."),
        ToolArgument("workflow_name", "string", "Name of the Temporal workflow."),
        ToolArgument("payload", "object", "JSON payload to pass to the workflow."),
    ],
)


# Dictionary mapping tool names to their handler functions
TOOL_HANDLERS: dict[str, Callable] = {
    "long_term_memory_retrieve": search_context,
    "store_episodic_memory": store_episodic,
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