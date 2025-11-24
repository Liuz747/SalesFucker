"""
画像生成服务

负责生成结构化用户画像逻辑。
"""

import json
from uuid import UUID, uuid4
from typing import Dict, Any

from core.memory import StorageManager
from infra.runtimes import LLMClient, CompletionsRequest
from libs.types import Message
from utils import get_component_logger

logger = get_component_logger(__name__, "ProfileService")

class ProfileService:
    """
    画像生成服务类
    """
    
    @staticmethod
    async def generate_user_profile(tenant_id: str, thread_id: UUID) -> Dict[str, Any]:
        """
        生成结构化用户画像
        
        Returns:
            Dict[str, Any]: 结构化画像数据
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
            你是一个CRM数据录入专员。请根据对话历史和长期记忆，构建该用户的结构化画像信息。
            
            [长期记忆]
            {long_term_context}
            
            请提取以下字段，如果信息未知则填 null 或 "未知"：
            - name: 用户称呼
            - age_group: 预估年龄段
            - skin_type: 肤质（如果是美妆相关）
            - concerns: 主要关注点/困扰 (数组)
            - budget: 预算偏好 (高/中/低)
            - purchase_intent: 购买意向 (高/中/低)
            - preferences: 个人偏好描述
            
            请仅返回标准的 JSON 对象字符串，不要包含 markdown 格式。
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
            
            # 4. 解析结果
            # 清理可能存在的 markdown 代码块标记
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)

        except Exception as e:
            logger.error(f"画像生成失败: {e}", exc_info=True)
            raise e

