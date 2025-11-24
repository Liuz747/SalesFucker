"""
报告生成服务

负责处理用户分析报告的生成逻辑，包括：
1. 获取对话记忆上下文
2. 组装分析 Prompt
3. 调用 LLM 生成报告
"""

from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from core.memory import StorageManager
from infra.runtimes import LLMClient, CompletionsRequest
from libs.types import Message
from utils import get_component_logger

logger = get_component_logger(__name__, "ReportService")

class ReportService:
    """
    报告生成服务类
    """
    
    @staticmethod
    async def generate_user_analysis(tenant_id: str, thread_id: UUID) -> str:
        """
        生成用户分析报告
        
        Args:
            tenant_id: 租户ID
            thread_id: 线程ID
            
        Returns:
            str: 生成的报告内容
        """
        try:
            # 1. 初始化记忆管理器
            memory_manager = StorageManager()

            # 2. 获取记忆 (Short-term + Long-term)
            short_term_messages, long_term_memories = await memory_manager.retrieve_context(
                tenant_id=tenant_id,
                thread_id=thread_id,
                query_text=None 
            )

            # 3. 构建 Prompt
            long_term_context = "\n".join([m.get('content', '') for m in long_term_memories]) if long_term_memories else "无长期记忆"
            
            system_prompt = f"""
            你是一个专业的用户分析专家。请根据以下的对话历史和长期记忆，生成一份详细的用户分析报告。
            
            [长期记忆]
            {long_term_context}
            
            [分析要求]
            1. 用户画像：基于对话风格和内容推断用户的性格、职业、年龄段等。
            2. 主要需求与痛点：用户在对话中表现出的核心需求和遇到的问题。
            3. 建议的沟通策略：针对该用户特点，建议后续采用的沟通方式（如：热情、专业、简洁等）。
            
            请直接输出报告内容，保持格式清晰。
            """
            
            # 4. 调用 LLM
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
            
            return response.content

        except Exception as e:
            logger.error(f"报告生成失败: {e}", exc_info=True)
            raise e
