"""
通用分析服务

负责处理各类LLM分析任务的通用逻辑，包括：
1. 获取对话记忆上下文
2. 组装分析 Prompt
3. 调用 LLM 生成结果
4. 解析和返回结果
"""

import json
from pathlib import Path
import re
from typing import Any
from uuid import UUID

from core.memory import StorageManager
from infra.runtimes import LLMClient, CompletionsRequest
from libs.types import Message
from utils import get_component_logger, load_yaml_file

logger = get_component_logger(__name__, "AnalysisService")


async def generate_analysis(
    run_id: UUID,
    tenant_id: str,
    thread_id: UUID,
    analysis_type: str,
    provider: str,
    model: str,
    temperature: float = 0.7
) -> dict[str, Any]:
    """
    生成分析结果的通用方法

    Args:
        run_id: 运行ID
        tenant_id: 租户ID
        thread_id: 线程ID
        analysis_type: 分析类型（用于日志）
        provider: LLM提供商
        model: 使用的模型名称
        temperature: 温度参数

    Returns:
        dict[str, Any]: 包含分析结果、token使用情况和错误信息的字典
            - result: 解析后的分析结果
            - input_tokens: 输入token数
            - output_tokens: 输出token数
            - error_message: 错误信息（成功时为None）
    """
    try:
        logger.info(f"[{thread_id}] 开始生成{analysis_type}")

        # 1. 获取记忆
        memory_manager = StorageManager()
        short_term_messages, long_term_memories = await memory_manager.retrieve_context(
            tenant_id=tenant_id,
            thread_id=thread_id,
            query_text=None
        )
        logger.debug(f"获取记忆上下文, thread_id={thread_id}")

        # 临时处理：过滤掉多模态输入
        # TODO: 后续支持多模态
        for msg in short_term_messages:
            if isinstance(msg.content, list):
                msg.content = [item for item in msg.content if item.type == "text"]

        # 2. 格式化长期记忆
        long_term_context = "\n".join(
            [m.get('content', '') for m in long_term_memories]
        ) if long_term_memories else "无长期记忆"

        # 3. 格式化短期对话历史为文本
        conversation_text = ""
        for msg in short_term_messages:
            role_label = "【客户】" if msg.role == "user" else "【员工】"
            # 处理多模态内容
            if isinstance(msg.content, list):
                text_parts = [item.content for item in msg.content]
                content = " ".join(text_parts)
            else:
                content = msg.content
            conversation_text += f"{role_label}: {content}\n"

        # 4. 构建 Prompt
        template_path = Path(__file__).parent.parent / "data" / "analysis_prompts.yaml"

        # 加载YAML配置
        config = load_yaml_file(template_path)

        # 获取指定模板配置
        template_config = config.get(analysis_type)

        if not template_config:
            return {
                "result": None,
                "input_tokens": 0,
                "output_tokens": 0,
                "error_message": "提示词模板配置不存在"
            }

        logger.debug(f"构建 {thread_id} Prompt")

        system_prompt = template_config.get("prompt").format(memory_content=long_term_context)

        # 5. 准备 LLM 消息
        llm_messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=f"请根据以下对话内容，按照相应要求做出分析：\n\n{conversation_text}")
        ]

        # 5. 调用 LLM
        llm_client = LLMClient()
        request = CompletionsRequest(
            id=run_id,
            provider=provider,
            model=model,
            messages=llm_messages,
            thread_id=thread_id,
            temperature=temperature
        )

        response = await llm_client.completions(request)
        content = re.sub(r'^```(?:json)?\s*|\s*```$', '', response.content)
        logger.debug(f"[LLM] {thread_id}，收到{analysis_type}返回信息")

        result = {
            "result": content,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        try:
            result["result"] = json.loads(content)
        except json.JSONDecodeError:
            # 降级处理：如果无法解析，返回原始内容
            logger.warning(f"Failed to parse {analysis_type} JSON response")

        return result

    except Exception as e:
        logger.error(f"{analysis_type}生成失败: {e}", exc_info=True)
        return {
            "result": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "error_message": str(e)
        }
