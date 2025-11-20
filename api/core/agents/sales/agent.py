"""
Sales Agent - 仅仅负责输出最终回复

基于 SentimentAgent 输出的 matched_prompt，结合记忆上下文生成个性化回复。

核心职责:
- 接收 matched_prompt（情感驱动的提示词）
- 集成记忆上下文
- 生成个性化销售回复
- 智能体自主管理记忆存储
"""

from typing import Tuple
from uuid import uuid4

from ..base import BaseAgent
from libs.types import Message
from infra.runtimes.entities import CompletionsRequest
from utils import get_current_datetime
from config import mas_config
from core.memory import StorageManager


class SalesAgent(BaseAgent):
    """
    销售智能体 - 简化版

    设计理念：
    - 使用 SentimentAgent 匹配的提示词，而不是重新生成
    - 集成记忆系统提供上下文连贯性
    - 极简架构：接收→处理→生成，自主管理记忆存储
    """

    def __init__(self):
        super().__init__()

        # 记忆管理
        self.memory_manager = StorageManager()
        self.llm_provider = mas_config.DEFAULT_LLM_PROVIDER
        self.llm_model = "openai/gpt-5-mini"
        
        self.logger.info(f"最终回复llm: {self.llm_provider}/{self.llm_model}")


    async def process_conversation(self, state: dict) -> dict:
        """
        工作流程：
        1. 读取 SentimentAgent 输出的 matched_prompt
        2. 主动检索记忆上下文（长期记忆 + 短期记忆）
        3. 构建增强的 LLM 提示词（包含历史记忆）
        4. 生成个性化销售回复
        5. 存储助手回复到记忆

        参数:
            state: 包含 matched_prompt, customer_input, tenant_id, thread_id 等

        返回:
            dict: 更新后的对话状态，包含 sales_response
        """
        start_time = get_current_datetime()

        try:
            self.logger.info("=== Sales Agent 开始处理 ===")

            # 读取 SentimentAgent 传递的数据
            customer_input = state.get("customer_input", "")
            matched_prompt = state.get("matched_prompt", {})

            tenant_id = state.get("tenant_id")
            thread_id = state.get("thread_id")

            self.logger.info(f"sales agent 匹配提示词: {matched_prompt.get('matched_key', 'unknown')}")

            # 直接检索记忆上下文
            user_text = self._input_to_text(customer_input)
            short_term_messages, long_term_memories = await self.memory_manager.retrieve_context(
                tenant_id=tenant_id,
                thread_id=thread_id,
                query_text=user_text,
            )
            self.logger.info(f"记忆检索完成 - 短期: {len(short_term_messages)} 条, 长期: {len(long_term_memories)} 条")

            # 生成个性化回复（基于匹配的提示词 + 记忆）
            sales_response, token_info = await self.__generate_final_response(
                customer_input, matched_prompt, short_term_messages, long_term_memories
            )

            # 存储助手回复到记忆
            if sales_response and tenant_id and thread_id:
                try:
                    await self.memory_manager.save_assistant_message(
                        tenant_id=tenant_id,
                        thread_id=thread_id,
                        message=sales_response,
                    )
                    self.logger.debug("助手回复已保存到记忆")
                except Exception as e:
                    self.logger.error(f"保存助手回复失败: {e}")

            # 更新状态
            updated_state = self._update_state(state, sales_response, token_info)

            processing_time = (get_current_datetime() - start_time).total_seconds()
            self.logger.info(f"最终回复生成完成: 耗时{processing_time:.2f}s, 长度={len(sales_response)}, tokens={token_info.get('tokens_used', 0)}")
            self.logger.info("=== Sales Agent 处理完成 ===")

            return updated_state

        except Exception as e:
            self.logger.error(f"销售代理处理失败: {e}", exc_info=True)
            return self._create_error_state(state, str(e))

    def _input_to_text(self, content) -> str:
        """将输入转换为文本（参照 Chat Agent）"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for node in content:
                value = getattr(node, "content", None)
                parts.append(value if isinstance(value, str) else str(node))
            return "\n".join(parts)
        return str(content)

    async def __generate_final_response(
        self, customer_input: str, matched_prompt: dict, short_term_messages: list, long_term_memories: list
    ) -> Tuple[str, dict]:
        """
        基于匹配提示词和记忆生成回复

        Args:
            customer_input: 客户输入
            matched_prompt: SentimentAgent 匹配的提示词
            short_term_messages: 短期记忆消息列表
            long_term_memories: 长期记忆摘要列表

        Returns:
            tuple: (回复内容, token信息)
        """
        try:
            # 1. 构建基础系统提示（来自匹配器）
            base_system_prompt = matched_prompt.get("system_prompt", "你是一个专业的美容顾问。")
            tone = matched_prompt.get("tone", "专业、友好")
            strategy = matched_prompt.get("strategy", "标准服务")

            # 2. 整合长期记忆到系统提示（参照 Chat Agent）
            enhanced_system_prompt = self._build_system_prompt_with_memory(
                base_system_prompt, tone, strategy, long_term_memories
            )

            # 3. 构建消息列表（直接使用记忆消息）
            llm_messages = [Message(role="system", content=enhanced_system_prompt)]
            llm_messages.extend(short_term_messages)  # 直接添加短期记忆消息
            llm_messages.append(Message(role="user", content=customer_input))

            # 4. 调用 LLM
            request = CompletionsRequest(
                id=uuid4(),
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=0.7,  # 适度创造性
                messages=llm_messages
            )

            llm_response = await self.invoke_llm(request)

            # 5. 提取 token 信息
            token_info = self._extract_token_info(llm_response)

            # 6. 返回响应
            if llm_response and llm_response.content:
                response_content = str(llm_response.content).strip()
                self.logger.debug(f"LLM 回复预览: {response_content[:100]}...")
                return response_content, token_info
            else:
                return self._get_fallback_response(matched_prompt), {}

        except Exception as e:
            self.logger.error(f"回复生成失败: {e}")
            return self._get_fallback_response(matched_prompt), {"tokens_used": 0, "error": str(e)}

    def _build_system_prompt_with_memory(
        self, base_prompt: str, tone: str, strategy: str, summaries: list
    ) -> str:
        """
        构建增强的系统提示词

        Args:
            base_prompt: 基础系统提示词
            tone: 语气要求
            strategy: 策略要求
            summaries: 长期记忆摘要列表

        Returns:
            str: 增强后的系统提示词
        """
        # 构建基础提示
        enhanced_prompt = f"""
{base_prompt}

【语气要求】{tone}
【策略要求】{strategy}

【回复要求】
- 用中文回复，语言自然流畅
- 控制在150字以内
- 体现个性化，避免模板化回复
- 根据客户历史适度调整策略
        """.strip()

        # 添加长期记忆（如果有）
        if summaries:
            memory_lines = []
            for idx, summary in enumerate(summaries[:3], 1):  # 最多3条摘要
                content = summary.get("content") or ""
                tags = summary.get("tags") or []
                tag_display = (
                    f" (标签: {', '.join(str(tag) for tag in tags)})"
                    if tags
                    else ""
                )
                memory_lines.append(f"{idx}. {content[:100]}{tag_display}")  # 限制长度

            enhanced_prompt += f"\n\n【客户历史背景】\n" + "\n".join(memory_lines)

        return enhanced_prompt

    def _extract_token_info(self, llm_response) -> dict:
        """提取 token 使用信息"""
        try:
            if llm_response and hasattr(llm_response, 'usage') and isinstance(llm_response.usage, dict):
                usage = llm_response.usage
                return {
                    "tokens_used": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0)
                }
        except Exception as e:
            self.logger.warning(f"Token 信息提取失败: {e}")

        return {"tokens_used": 0}

    def _get_fallback_response(self, matched_prompt: dict) -> str:
        """获取兜底回复"""
        tone = matched_prompt.get("tone", "专业、友好")

        if "温和" in tone or "关怀" in tone:
            return "我理解您的感受，作为您的美容顾问，我会耐心为您提供专业建议。请告诉我您遇到的具体问题。"
        elif "积极" in tone or "热情" in tone:
            return "太好了！我是您的专业美容顾问，很高兴为您服务！请告诉我您的美容需求，我会为您提供最适合的建议。"
        else:
            return "感谢您的咨询。我是您的专业美容顾问，很乐意为您提供个性化的产品建议和美容方案。"

    def _update_state(self, state: dict, sales_response: str, token_info: dict) -> dict:
        """更新对话状态"""
        # 主要状态（LangGraph 传递）
        state["sales_response"] = sales_response
        state["output"] = sales_response  # 作为最终输出

        # 备份到 values 结构
        if state.get("values") is None:
            state["values"] = {}
        if state["values"].get("agent_responses") is None:
            state["values"]["agent_responses"] = {}

        state["values"]["agent_responses"][self.agent_id] = {
            "sales_response": sales_response,
            "tokens_used": token_info.get("tokens_used", 0),
            "timestamp": get_current_datetime(),
            "response_length": len(sales_response)
        }

        # 更新活跃代理列表
        state.setdefault("active_agents", []).append(self.agent_id)

        self.logger.info(f"状态更新完成 - 最终输出内容: {sales_response[:100]}...")
        return state
