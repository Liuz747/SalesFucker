"""
画像生成服务

负责生成结构化用户画像逻辑。
"""

import json
from typing import Any
from uuid import UUID, uuid4

from core.memory import StorageManager
from infra.runtimes import LLMClient, CompletionsRequest
from libs.types import Message
from utils import get_component_logger, get_current_datetime, get_processing_time

logger = get_component_logger(__name__, "ProfileService")


class ProfileService:
    """
    画像生成服务类
    """
    
    @staticmethod
    async def generate_user_profile(tenant_id: str, thread_id: UUID) -> dict[str, Any]:
        """
        生成结构化用户画像
        
        Returns:
            dict[str, Any]: 结构化画像数据
        """
        try:
            start_time = get_current_datetime()
            logger.info(f"[{thread_id}] 开始生成画像")

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
            你是专业的用户画像分析专家。请基于上述聊天记录进行用户画像分析。
            
            [长期记忆]
            {long_term_context}
            
            **重要：你必须严格按照JSON格式返回分析结果，不要包含任何其他文本或格式标记。**

            **分析指导：通过用户的表达方式、语言习惯、关注点等信息，进行专业的用户画像分析。**

            分析要点：

            - 基本信息：从对话内容分析用户的基本特征

            - 性格特征：分析用户的表达方式和沟通风格

            - 消费行为：了解用户的消费偏好和能力

            - 业务需求：分析用户对业务的需求

            - 客户状态：评估用户的服务满意度和购买意向

            - 对话质量：评估本次对话信息的丰富程度

            请严格按照以下分析返回分析结果：

            "用户基本信息摘要（从对话时间、表达方式、关注点等推断年龄段、职业类型、地区等）",

            "性格特征摘要（从对话方式、情绪表达、语言风格等分析性格类型、价值观等）", 

            "消费行为摘要（从工作状态、对话时间、表达方式等推断消费能力、消费偏好等）",

            "业务需求摘要（从对话中的业务话题、关注点、询问方式等分析需求）",

            "客户状态摘要（从对话态度、服务满意度、互动方式等判断客户阶段、购买意向、流失风险等）",

            "综合以上分析，形成用户的整体画像描述"

            输出要求：

            1. 必须返回有效的JSON格式

            2. 基于对话内容进行专业分析

            3. 严格按照上述JSON格式输出
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

            # 4. 解析结果
            # 清理可能存在的 markdown 代码块标记
            content = content.replace("```json", "").replace("```", "").strip()
            profile_data = json.loads(content)
            
            # 提取画像结果
            profile_result = profile_data.get("综合以上分析，形成用户的整体画像描述")
            if not profile_result:
                # 如果没有找到对应的 key，尝试将整个 JSON 转为字符串
                 profile_result = json.dumps(profile_data, ensure_ascii=False)
            
            # 提取 token 使用情况
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            total_elapsed_ms = get_processing_time(start_time)
            logger.info(f"[{thread_id}] 画像生成完成, 总耗时: {total_elapsed_ms:.2f}ms, input_tokens: {input_tokens}, output_tokens: {output_tokens}")

            return {
                "profile_result": profile_result,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "error_message": None
            }

        except Exception as e:
            logger.error(f"画像生成失败: {e}", exc_info=True)
            return {
                "profile_result": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "error_message": str(e)
            }

