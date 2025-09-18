"""
Langfuse integration for workflow observation and tracing

This module provides comprehensive tracing capabilities for the MAS multi-agent system
using LangFuse Python SDK v3 with OpenTelemetry-based architecture.

Supports:
- Decorator-based tracing for automatic instrumentation
- Context manager approach for manual lifecycle management
- Workflow observation for complex multi-agent interactions
- Automatic context propagation for nested operations
"""

from typing import Dict, Any, Optional, Callable
from functools import wraps
import logging
from contextlib import contextmanager

from langfuse import observe, get_client
from config import mas_config

# 配置日志记录器
logger = logging.getLogger(__name__)

# 全局客户端实例，延迟初始化
_langfuse_client = None


def get_langfuse_client():
    """
    获取Langfuse客户端实例（单例模式）

    Returns:
        Langfuse客户端实例，如果配置无效则返回None
    """
    global _langfuse_client

    if _langfuse_client is None:
        try:
            # 检查必要的配置
            if not all([
                mas_config.LANGFUSE_SECRET_KEY,
                mas_config.LANGFUSE_PUBLIC_KEY,
                mas_config.LANGFUSE_HOST
            ]):
                logger.warning("LangFuse configuration incomplete, tracing disabled")
                return None

            _langfuse_client = get_client()
            logger.info("LangFuse client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize LangFuse client: {e}")
            _langfuse_client = None

    return _langfuse_client


def trace_workflow_step(
    name: Optional[str] = None,
    as_type: str = "span",
    capture_input: bool = True,
    capture_output: bool = True,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    装饰器：自动追踪工作流步骤

    Args:
        name: 自定义操作名称
        as_type: 观察类型 ("span", "generation", "event")
        capture_input: 是否捕获输入参数
        capture_output: 是否捕获输出结果
        metadata: 额外的元数据

    Returns:
        装饰器函数

    Example:
        @trace_workflow_step(name="sentiment-analysis", as_type="generation")
        def analyze_sentiment(message: str) -> Dict[str, Any]:
            return {"sentiment": "positive", "confidence": 0.95}
    """
    def decorator(func: Callable) -> Callable:
        if get_langfuse_client() is None:
            # 如果LangFuse未配置，返回原始函数
            return func

        @observe(
            name=name or func.__name__,
            as_type=as_type,
            capture_input=capture_input,
            capture_output=capture_output
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # 如果提供了元数据，可以通过langfuse_metadata参数传递
                if metadata:
                    kwargs['langfuse_metadata'] = {
                        **(kwargs.get('langfuse_metadata', {})),
                        **metadata
                    }
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in traced function {func.__name__}: {e}")
                raise

        return wrapper
    return decorator


def trace_agent_interaction(agent_name: str, tenant_id: Optional[str] = None):
    """
    智能体交互专用追踪装饰器

    Args:
        agent_name: 智能体名称
        tenant_id: 租户ID

    Returns:
        装饰器函数

    Example:
        @trace_agent_interaction("sentiment", tenant_id="tenant_123")
        def process_sentiment(message: str) -> Dict[str, Any]:
            return analyze_sentiment(message)
    """
    return trace_workflow_step(
        name=f"agent-{agent_name}" + (f"-{tenant_id}" if tenant_id else ""),
        as_type="generation",
        metadata={
            "agent_type": agent_name,
            "tenant_id": tenant_id,
            "component": "multi-agent-workflow"
        }
    )


@contextmanager
def trace_conversation_context(
    conversation_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    会话级别的上下文管理器追踪

    Args:
        conversation_id: 对话ID
        user_id: 用户ID
        session_id: 会话ID
        metadata: 额外元数据

    Yields:
        LangFuse span对象，用于嵌套操作

    Example:
        with trace_conversation_context("conv_123", user_id="user_456") as span:
            # 处理对话逻辑
            span.update(output={"status": "processed"})
    """
    client = get_langfuse_client()
    if client is None:
        # 如果客户端未配置，提供空上下文管理器
        from contextlib import nullcontext
        yield nullcontext()
        return

    trace_metadata = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "session_id": session_id,
        **(metadata or {})
    }

    try:
        with client.start_as_current_span(
            name=f"conversation-{conversation_id}",
            metadata=trace_metadata
        ) as span:
            yield span
    except Exception as e:
        logger.error(f"Error in conversation tracing: {e}")
        # 提供空上下文管理器作为fallback
        from contextlib import nullcontext
        yield nullcontext()
    finally:
        # 确保数据被发送
        try:
            client.flush()
        except Exception as e:
            logger.error(f"Failed to flush LangFuse data: {e}")


def trace_conversation(
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """
    传统的会话追踪函数（向后兼容）

    Args:
        input_data: 输入数据
        output_data: 输出数据
        metadata: 可选的元数据
        conversation_id: 对话ID
        user_id: 用户ID
    """
    client = get_langfuse_client()
    if client is None:
        logger.warning("LangFuse client not available, skipping trace")
        return

    try:
        span = client.start_span(name="conversation-legacy")

        # 更新span数据
        span.update(
            input=input_data,
            output=output_data,
            metadata={
                "conversation_id": conversation_id,
                "user_id": user_id,
                **(metadata or {})
            }
        )

        span.end()
        client.flush()

    except Exception as e:
        logger.error(f"LangFuse trace failed: {e}")


def trace_llm_generation(
    model: str,
    prompt: str,
    response: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    LLM生成专用追踪函数

    Args:
        model: 使用的模型名称
        prompt: 输入提示词
        response: 模型响应
        metadata: 额外元数据
    """
    client = get_langfuse_client()
    if client is None:
        return

    try:
        with client.start_as_current_generation(
            name="llm-generation",
            model=model
        ) as generation:
            generation.update(
                input=prompt,
                output=response,
                metadata=metadata or {}
            )

    except Exception as e:
        logger.error(f"LLM generation tracing failed: {e}")


def flush_traces():
    """
    强制发送所有待处理的追踪数据

    建议在应用程序关闭或长时间运行的任务结束时调用
    """
    client = get_langfuse_client()
    if client:
        try:
            client.flush()
            logger.info("LangFuse traces flushed successfully")
        except Exception as e:
            logger.error(f"Failed to flush LangFuse traces: {e}")