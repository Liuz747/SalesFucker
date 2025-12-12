"""
标签生成服务

负责生成用户标签逻辑。
"""

import json
from typing import Any
from uuid import UUID, uuid4

from core.memory import StorageManager
from infra.runtimes import LLMClient, CompletionsRequest
from libs.types import Message
from utils import get_component_logger, get_current_datetime, get_processing_time

logger = get_component_logger(__name__, "LabelService")


class LabelService:
    """
    标签生成服务类
    """
    
    @staticmethod
    async def generate_user_labels(tenant_id: str, thread_id: UUID) -> dict[str, Any]:
        """
        生成用户标签
        
        Returns:
            dict[str, Any]: 包含标签结果、token使用情况和错误信息的字典
        """
        try:
            start_time = get_current_datetime()
            logger.info(f"[{thread_id}] 开始生成标签")

            # 1. 获取记忆
            memory_manager = StorageManager()
            short_term_messages, long_term_memories = await memory_manager.retrieve_context(
                tenant_id=tenant_id,
                thread_id=thread_id,
                query_text=None
            )
            logger.debug(f"获取记忆上下文, thread_id={thread_id}")
            
            long_term_context = "\n".join([m.get('content', '') for m in long_term_memories]) if long_term_memories else "无长期记忆"
            
            # 2. 构建 Prompt
            system_prompt = f"""
            你是一个用户画像标签生成器。请根据对话历史和长期记忆，提取出最能代表该用户的 3-5 个关键标签，每个标签5个字以内。
            标签应该简短、精准。你可以从以下维度中任意选择，核心是最能受益于销售进行分析的标签：
            MBTI性格分析
            个性情绪心理侧写
            身份推测
            互动密切程度
            犹豫点
            消费能力
            产品需求偏好
            决定话术收敛方式
            
            [长期记忆]
            {long_term_context}
            
            请仅返回一个 JSON 数组字符串，不要包含其他 markdown 格式。
            示例：["标签1", "标签2", "标签3"]
            """
            
            # 3. 调用 LLM
            logger.debug(f"构建 {thread_id} Prompt")
            llm_messages = [Message(role="system", content=system_prompt)]
            llm_messages.extend(short_term_messages)

            llm_client = LLMClient()
            request = CompletionsRequest(
                id=str(uuid4()),
                provider="openrouter",
                model="qwen/qwen3-coder-flash",
                messages=llm_messages,
                thread_id=thread_id,
                temperature=0.7
            )

            response = await llm_client.completions(request)
            content = response.content

            logger.debug(f"[LLM] {thread_id}，收到返回信息")

            # 提取 token 使用情况
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            # 4. 解析结果
            # 清理可能存在的 markdown 代码块标记
            content = content.replace("```json", "").replace("```", "").strip()
            labels = []
            try:
                labels = json.loads(content)
            except json.JSONDecodeError:
                # 如果解析失败，尝试简单的文本分割作为兜底
                labels = [tag.strip() for tag in content.split(',') if tag.strip()]
            
            total_elapsed_ms = get_processing_time(start_time)
            logger.info(f"[{thread_id}] 标签生成完成, 总耗时: {total_elapsed_ms:.2f}ms, input_tokens: {input_tokens}, output_tokens: {output_tokens}")

            return {
                "label_result": labels,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "error_message": None
            }

        except Exception as e:
            logger.error(f"标签生成失败: {e}", exc_info=True)
            return {
                "label_result": [],
                "input_tokens": 0,
                "output_tokens": 0,
                "error_message": str(e)
            }
