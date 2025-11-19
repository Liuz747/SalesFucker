"""
Sales Agent - 简化版（使用智能匹配提示词 + 记忆系统）

基于 SentimentAgent 输出的 matched_prompt，结合记忆上下文生成个性化销售回复。
移除复杂的产品推荐逻辑，专注于核心对话生成。

核心职责:
- 接收 matched_prompt（情感驱动的提示词）
- 集成记忆上下文
- 生成个性化销售回复
- 记忆存储由工作流层级统一处理
"""

from typing import Dict, Any, Tuple
from uuid import uuid4

from ..base import BaseAgent
from libs.types import Message
from infra.runtimes.entities import CompletionsRequest
from utils import get_current_datetime
from config import mas_config


class SalesAgent(BaseAgent):
    """
    销售智能体 - 简化版

    设计理念：
    - 使用 SentimentAgent 匹配的提示词，而不是重新生成
    - 集成记忆系统提供上下文连贯性
    - 极简架构：接收→处理→生成，记忆存储由工作流统一处理
    """

    def __init__(self):
        super().__init__()

        # 移除独立的 StorageManager，记忆管理由工作流层级处理
        self.llm_provider = mas_config.DEFAULT_LLM_PROVIDER
        self.llm_model = "openai/gpt-5-mini"

    async def process_conversation(self, state: dict) -> dict:
        """
        处理对话状态（简化版：使用匹配提示词 + 记忆上下文）

        工作流程：
        1. 读取 SentimentAgent 输出的 matched_prompt 和 memory_context
        2. 构建增强的 LLM 提示词（包含历史记忆）
        3. 生成个性化销售回复
        4. 记忆存储由工作流层级统一处理

        参数:
            state: 包含 matched_prompt, memory_context, customer_input 等

        返回:
            dict: 更新后的对话状态，包含 sales_response
        """
        start_time = get_current_datetime()

        try:
            self.logger.info("=== Sales Agent 开始处理 ===")

            # 读取 SentimentAgent 传递的数据
            customer_input = state.get("customer_input", "")
            matched_prompt = state.get("matched_prompt", {})
            memory_context = state.get("memory_context", {})

            self.logger.info(f"接收数据 - 输入长度: {len(customer_input)}, 匹配提示词: {matched_prompt.get('matched_key', 'unknown')}")
            self.logger.info(f"记忆上下文 - 短期: {len(memory_context.get('short_term', []))} 条, 长期: {len(memory_context.get('long_term', []))} 条")

            # 生成个性化回复（基于匹配的提示词 + 记忆）
            sales_response, token_info = await self._generate_response_with_memory(
                customer_input, matched_prompt, memory_context
            )

            # 更新状态
            updated_state = self._update_state(state, sales_response, token_info)

            processing_time = (get_current_datetime() - start_time).total_seconds()
            self.logger.info(f"销售回复生成完成: 耗时{processing_time:.2f}s, 长度={len(sales_response)}, tokens={token_info.get('tokens_used', 0)}")
            self.logger.info("=== Sales Agent 处理完成（简化版） ===")

            return updated_state

        except Exception as e:
            self.logger.error(f"销售代理处理失败: {e}", exc_info=True)
            return self._create_error_state(state, str(e))

    async def _generate_response_with_memory(
        self, customer_input: str, matched_prompt: Dict[str, Any], memory_context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        🔥 新增：基于匹配提示词和记忆生成回复

        Args:
            customer_input: 客户输入
            matched_prompt: SentimentAgent 匹配的提示词
            memory_context: 记忆上下文

        Returns:
            tuple: (回复内容, token信息)
        """
        try:
            # 1. 构建基础 system prompt（来自匹配器）
            system_prompt = matched_prompt.get("system_prompt", "你是一个专业的美容顾问。")
            tone = matched_prompt.get("tone", "专业、友好")
            strategy = matched_prompt.get("strategy", "标准服务")

            # 2. 添加记忆上下文
            memory_text = self._format_memory_context(memory_context)

            # 3. 构建增强的系统提示
            enhanced_system_prompt = f"""
            {system_prompt}

            【语气要求】{tone}
            【策略要求】{strategy}

            {memory_text}

            【回复要求】
            - 用中文回复，语言自然流畅
            - 控制在150字以内
            - 体现个性化，避免模板化回复
            - 根据客户历史适度调整策略
            """

            # 4. 构建对话消息
            messages = [
                {"role": "system", "content": enhanced_system_prompt.strip()},
                {"role": "user", "content": customer_input}
            ]

            # 5. 调用 LLM
            request = CompletionsRequest(
                id=uuid4(),
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=0.7,  # 适度创造性
                messages=[Message(role=msg["role"], content=msg["content"]) for msg in messages]
            )

            llm_response = await self.invoke_llm(request)

            # 6. 提取 token 信息
            token_info = self._extract_token_info(llm_response)

            # 7. 返回响应
            if llm_response and llm_response.content:
                response_content = str(llm_response.content).strip()
                self.logger.debug(f"LLM 回复预览: {response_content[:100]}...")
                return response_content, token_info
            else:
                return self._get_fallback_response(matched_prompt), {}

        except Exception as e:
            self.logger.error(f"回复生成失败: {e}")
            return self._get_fallback_response(matched_prompt), {"tokens_used": 0, "error": str(e)}

    def _format_memory_context(self, memory_context: dict) -> str:
        """
        格式化记忆上下文为 LLM 可用的文本

        Args:
            memory_context: 记忆上下文字典

        Returns:
            str: 格式化后的记忆文本
        """
        parts = []

        # 长期记忆摘要
        long_term = memory_context.get("long_term", [])
        if long_term:
            summaries = []
            for memory in long_term[:3]:  # 最多 3 条摘要
                content = memory.get("content", "")
                if content:
                    summaries.append(f"- {content[:100]}")  # 限制长度

            if summaries:
                parts.append("【客户历史背景】\n" + "\n".join(summaries))

        # 短期对话历史
        short_term = memory_context.get("short_term", [])
        if short_term and len(short_term) > 2:  # 有足够的对话历史
            recent_exchanges = []
            for msg in short_term[-4:]:  # 最近 4 条消息
                role = msg.get("role", "")
                content = str(msg.get("content", ""))[:80]  # 限制长度
                if role == "user":
                    recent_exchanges.append(f"客户: {content}")
                elif role == "assistant":
                    recent_exchanges.append(f"我: {content}")

            if recent_exchanges:
                parts.append("【最近对话】\n" + "\n".join(recent_exchanges))

        # 如果没有记忆，添加首次对话提示
        if not parts:
            parts.append("【客户信息】这是与该客户的首次对话。")

        return "\n\n".join(parts)

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

        self.logger.info(f"状态更新完成 - 最终输出长度: {len(sales_response)}")
        return state


    def health_check(self) -> dict:
        """健康检查"""
        try:
            # 测试基本功能
            test_prompt = {
                "system_prompt": "你是测试顾问",
                "tone": "友好",
                "strategy": "测试"
            }
            test_memory = {"short_term": [], "long_term": []}

            # 模拟生成回复（通过 fallback）
            response = self._get_fallback_response(test_prompt)

            return {
                "status": "healthy",
                "llm_provider": self.llm_provider,
                "llm_model": self.llm_model,
                "memory_manager": "workflow_level",  # 更新为工作流级别
                "test_response_length": len(response)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
