"""
Langfuse 链路追踪工具模块

为 MAS 多智能体系统提供 Langfuse 集成功能。

核心功能:
- 提供 flush_traces 工具函数
- 简化的追踪数据刷新机制
- 标准化的错误处理

使用方式:
    from langfuse import observe
    from utils.tracer_client import flush_traces

    @observe()
    def my_function():
        return "Hello, world!"

    @observe(as_type="generation")
    def llm_call():
        return "LLM response"
"""

import logging
from langfuse import get_client

# 配置日志记录器
logger = logging.getLogger(__name__)


def flush_traces():
    """
    强制发送所有待处理的追踪数据

    建议在应用程序关闭或长时间运行的任务结束时调用
    """
    client = get_client()
    try:
        client.flush()
        logger.info("Langfuse 成功发送所有追踪数据")
    except Exception as e:
        logger.error(f"Langfuse 发送追踪数据失败: {e}")