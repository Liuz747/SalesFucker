"""
标签生成服务

负责生成用户标签逻辑。
"""

import json
from uuid import UUID, uuid4
from typing import List, Dict, Any

from core.memory import StorageManager
from infra.runtimes import LLMClient, CompletionsRequest
from libs.types import Message
from utils import get_component_logger

logger = get_component_logger(__name__, "LabelService")

class LabelService:
    """
    标签生成服务类
    """
    
    @staticmethod
    async def generate_user_labels(tenant_id: str, thread_id: UUID) -> Dict[str, Any]:
        """
        生成用户标签
        
        Returns:
            Dict[str, Any]: 包含标签结果、token使用情况和错误信息的字典
        """
        try:
            # 1. 获取记忆
            memory_manager = StorageManager()
            short_term_messages, long_term_memories = await memory_manager.retrieve_context(
                tenant_id=tenant_id,
                thread_id=thread_id,
                query_text=None 
            )
            
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
            llm_messages = [Message(role="system", content=system_prompt)]
            llm_messages.extend(short_term_messages)

            llm_client = LLMClient()
            request = CompletionsRequest(
                id=str(uuid4()),
                provider="openrouter", 
                model="openai/gpt-5-mini",
                messages=llm_messages,
                thread_id=thread_id,
                temperature=0.7
            )
            
            response = await llm_client.completions(request)
            content = response.content
            
            # 计算总token
            total_tokens = 0
            if response.usage:
                # 兼容 usage 是字典或对象的不同情况
                if isinstance(response.usage, dict):
                    total_tokens = response.usage.get("input_tokens", 0) + response.usage.get("output_tokens", 0)
                else:
                    # 尝试直接访问属性或转为字典
                    try:
                         total_tokens = getattr(response.usage, "total_tokens", 0)
                         if total_tokens == 0:
                             total_tokens = getattr(response.usage, "input_tokens", 0) + getattr(response.usage, "output_tokens", 0)
                    except AttributeError:
                        pass
            
            # 4. 解析结果
            # 清理可能存在的 markdown 代码块标记
            content = content.replace("```json", "").replace("```", "").strip()
            labels = []
            try:
                labels = json.loads(content)
            except json.JSONDecodeError:
                # 如果解析失败，尝试简单的文本分割作为兜底
                labels = [tag.strip() for tag in content.split(',') if tag.strip()]
            
            return {
                "label_result": labels,
                "label_tokens": total_tokens,
                "error_message": None
            }

        except Exception as e:
            logger.error(f"标签生成失败: {e}", exc_info=True)
            return {
                "label_result": [],
                "label_tokens": 0,
                "error_message": str(e)
            }
