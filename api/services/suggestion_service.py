"""
回复建议生成服务层
"""

from typing import Any, Tuple, List
import json
from uuid import UUID

from core.memory.conversation_store import ConversationStore
from infra.runtimes import LLMClient, CompletionsRequest
from libs.types import Message
from utils import get_component_logger, get_current_datetime, get_processing_time_ms

logger = get_component_logger(__name__, "SuggestionService")

# TODO: 目前不是工作重心，之后需要修改整体逻辑
class SuggestionService:
    """
    提供回复建议生成的业务逻辑
    """

    @staticmethod
    async def generate_suggestions(
        input_content: Any,
        thread_id: UUID,
        tenant_id: str = None
    ) -> Tuple[List[dict], dict]:
        """
        生成回复建议
        
        参数:
            input_content: 标准化后的输入内容
            thread_id: 线程ID (用于日志和记忆检索)
            tenant_id: 租户ID (保留，暂未强制使用)
            
        返回:
            (multimodal_outputs, metrics): 建议输出列表和指标字典
        """
        try:
            # 初始化LLM客户端
            llm_client = LLMClient()

            # 明确指定使用 "openrouter" provider
            provider = llm_client.active_providers.get("openrouter")
            if not provider:
                raise ValueError("OpenRouter provider not available in active_providers")

            # 1. 获取最近的对话记忆
            store = ConversationStore()
            recent_messages = await store.get_recent(thread_id, limit=10)
            
            # 构建消息列表
            messages = []
            
            # 2. 添加系统预设提示词
            system_prompt = (
                "你是一个智能助手。请根据上下文回复用户，生成3条合适的建议回复。"
                "请务必以JSON数组格式返回，例如：[\"建议1\", \"建议2\", \"建议3\"]。"
            )
            messages.append(Message(role="system", content=system_prompt))
            
            # 3. 添加历史消息
            for msg in recent_messages:
                # 确保内容格式兼容
                # content = provider._format_message_content(msg.content)
                messages.append(Message(role=msg.role, content=msg.content))
                
            # 4. 添加当前用户输入
            # current_content = provider._format_message_content(input_content)
            messages.append(Message(role="user", content=input_content))
            
            # 调用OpenAI生成3条回复
            start_time = get_current_datetime()
            
            # 准备消息格式 (provider specific)
            formatted_messages = []
            for m in messages:
                content = provider._format_message_content(m.content)
                formatted_messages.append({"role": m.role, "content": content})

            # 使用 OpenRouter 模型名称
            model_name = "openai/gpt-oss-120b:exacto" 
            
            # 启用 require_parameters 确保 Provider 严格检查参数支持
            extra_body = {}
            if provider.provider.type == "openrouter":
                extra_body["provider"] = {"require_parameters": False} # 尝试关闭以允许部分兼容

            response = await provider.client.chat.completions.create(
                model=model_name,
                messages=formatted_messages,
                n=1,  # 改回 n=1，使用 JSON 数组获取多条建议
                temperature=0.7,
                # extra_body=extra_body
            )
            
            processing_time = round(get_processing_time_ms(start_time), 2)
            
            # 构造输出
            multimodal_outputs = []
            
            if response.choices:
                content = response.choices[0].message.content.strip()
                
                # 尝试清理 markdown 标记
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                try:
                    # 尝试解析JSON数组
                    suggestions = json.loads(content)
                    if isinstance(suggestions, list):
                         for suggestion in suggestions:
                            multimodal_outputs.append({
                                "type": "text",
                                "text": str(suggestion),
                                "metadata": {"text_type": "suggestion"}
                            })
                    else:
                        # 这是一个非列表的JSON对象或值
                         multimodal_outputs.append({
                            "type": "text",
                            "text": str(suggestions),
                            "metadata": {"text_type": "suggestion"}
                        })
                except json.JSONDecodeError:
                    # JSON解析失败，尝试按行分割作为兜底
                     logger.warning(f"建议生成 JSON解析失败: {content}")
                     lines = [line for line in content.split('\n') if line.strip()]
                     for line in lines:
                         # 简单清理序号如 "1. "
                         import re
                         cleaned_line = re.sub(r'^\d+[\.、]\s*', '', line.strip())
                         if cleaned_line:
                             multimodal_outputs.append({
                                "type": "text",
                                "text": cleaned_line,
                                "metadata": {"text_type": "suggestion"}
                             })
            else:
                logger.warning(f"LLM返回了空choices: {response}")
            
            # 统计Token
            metrics = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "processing_time": processing_time
            }
            
            return multimodal_outputs, metrics
            
        except Exception as e:
            logger.error(f"建议生成失败 - 线程: {thread_id}: {e}", exc_info=True)
            raise e

