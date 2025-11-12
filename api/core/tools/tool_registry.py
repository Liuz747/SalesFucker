from collections.abc import Callable

from .entities import ToolArgument, ToolDefinition
from .rag_retrieve import rag_retrieve
from .search_context import search_context
from .trigger_workflow import trigger_workflow


long_term_memory_tool = ToolDefinition(
    name="long_term_memory_retrieve",
    description="Retrieve semantically similar documents or memories from vector database.",
    arguments=[
        ToolArgument("tenant_id", "string", "Tenant identifier for isolation."),
        ToolArgument("query", "string", "The user query or embedding text."),
        ToolArgument("top_k", "integer", "Number of top similar memories to return."),
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
    "rag_retrieve_context": rag_retrieve,
    "trigger_temporal_workflow": trigger_workflow,
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
        raise ValueError(f"Unknown tool: {tool_name}")

    return TOOL_HANDLERS[tool_name]