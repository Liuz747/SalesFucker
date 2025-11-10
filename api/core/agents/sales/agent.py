"""
Sales Agent - 极简协调版

专注于接收 Sentiment Agent 的分析结果并生成个性化响应。
Agent 本身只负责协调，响应生成委托给专门的组件。

核心职责:
- 接收情感分析结果
- 基于情感提示词生成响应
- 状态管理和错误处理
- 与 Sentiment Agent 协同工作
"""

from typing import Dict, Any
from uuid import uuid4

from ..base import BaseAgent
from libs.types import Message
from infra.runtimes.entities import CompletionsRequest
from utils import get_current_datetime
from config import mas_config


class SalesResponseGenerator:
    """销售响应生成器"""

    def __init__(self, llm_provider: str, llm_model: str, invoke_llm_fn):
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.invoke_llm = invoke_llm_fn

    async def generate_response(
        self,
        customer_input: str,
        sales_prompt: str,
        sentiment_context: Dict[str, Any]
    ) -> tuple[str, dict]:
        """生成销售响应，返回响应内容和token使用信息"""
        try:
            # 构建基于情感提示的响应请求
            prompt = f"""作为专业的美妆销售顾问，请根据以下指导原则回应客户：

客户输入：{customer_input}

销售指导：{sales_prompt}

情感分析：
- 情感倾向：{sentiment_context.get('sentiment', 'neutral')}
- 情感强度：{sentiment_context.get('score', 0.0)}
- 紧急程度：{sentiment_context.get('urgency', 'medium')}

请提供：
1. 符合客户情感状态的专业回应
2. 相关的美妆建议或产品推荐
3. 后续的引导问题
4. 保持友好专业的语调

要求：用中文回复，语言自然流畅，控制在200字以内。"""

            messages = [
                Message(role="user", content=prompt)
            ]
            request = CompletionsRequest(
                id=uuid4(),
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=0.7,
                messages=messages
            )

            llm_response = await self.invoke_llm(request)

            # 提取token信息
            token_info = {}
            if llm_response and hasattr(llm_response, 'usage') and isinstance(llm_response.usage, dict):
                input_tokens = llm_response.usage.get('input_tokens', 0)
                output_tokens = llm_response.usage.get('output_tokens', 0)
                token_info['tokens_used'] = input_tokens + output_tokens
                token_info['input_tokens'] = input_tokens
                token_info['output_tokens'] = output_tokens
                self.logger.debug(f"Token统计: 输入={input_tokens}, 输出={output_tokens}, 总计={token_info['tokens_used']}")
            else:
                self.logger.warning("LLM响应缺少有效的usage信息")

            if llm_response and isinstance(llm_response.content, str):
                return llm_response.content.strip(), token_info
            elif llm_response:
                return str(llm_response.content).strip(), token_info
            else:
                return self._get_fallback_response(sales_prompt), {}

        except Exception as e:
            self.logger.error(f"生成销售响应时发生错误: {e}", exc_info=True)
            return self._get_fallback_response(sales_prompt), {"tokens_used": 0, "error": str(e)}

    def _get_fallback_response(self, sales_prompt: str) -> str:
        """获取降级响应"""
        if "紧急" in sales_prompt or "急" in sales_prompt:
            return "我理解您的需求很紧急，让我立即为您提供专业的建议和解决方案。"
        elif "积极" in sales_prompt:
            return "很高兴为您服务！基于您的需求，我很乐意为您推荐最合适的产品。"
        elif "负面" in sales_prompt or "安抚" in sales_prompt:
            return "我理解您的顾虑，让我为您提供专业的解决方案，确保您满意。"
        else:
            return "您好！作为您的美妆顾问，我很乐意为您提供专业的建议和推荐。"


class SalesAgent(BaseAgent):
    """
    销售智能体 - 极简协调版

    设计理念：
    - 接收 Sentiment Agent 的分析结果
    - 使用情感驱动的提示词生成响应
    - 保持极简的架构和职责
    - 专注于与 Sentiment Agent 的协同
    """

    def __init__(self):
        super().__init__()

        # LLM 配置
        self.llm_provider = mas_config.DEFAULT_LLM_PROVIDER

        # 根据provider选择合适的模型
        if self.llm_provider == "openrouter":
            self.llm_model = "google/gemini-2.5-flash-preview-09-2025"
        elif self.llm_provider == "zenmux":
            self.llm_model = "openai/gpt-5-chat"
        else:
            self.llm_model = "gpt-4o-mini"

        # 初始化响应生成器
        self.response_generator = SalesResponseGenerator(
            llm_provider=self.llm_provider,
            llm_model=self.llm_model,
            invoke_llm_fn=self.invoke_llm
        )

        self.logger.info(f"销售智能体初始化完成: {self.agent_id}, LLM: {self.llm_provider}/{self.llm_model}")

    async def process_conversation(self, state: dict) -> dict:
        """
        处理对话状态（LangGraph工作流节点）

        简化流程：
        1. 从 Sentiment Agent 获取分析结果
        2. 基于情感提示词生成响应
        3. 更新对话状态

        参数:
            state: 当前对话状态

        返回:
            dict: 更新后的对话状态
        """
        try:
            customer_input = state.get("customer_input", "")
            sentiment_analysis = state.get("sentiment_analysis", {})

            # 提取情感分析结果和销售提示词
            sales_prompt = sentiment_analysis.get("sales_prompt", "")
            processed_input = sentiment_analysis.get("processed_input", customer_input)

            # 生成销售响应
            response, token_info = await self._generate_sales_response(
                processed_input,
                sales_prompt,
                sentiment_analysis
            )

            # 更新对话状态
            updated_state = self._update_state(state, response, sentiment_analysis, token_info)

            self.logger.info(f"销售响应生成完成: 长度={len(response)}字符, tokens={token_info.get('tokens_used', 0)}")
            return updated_state

        except Exception as e:
            self.logger.error(f"Agent processing failed: {e}", exc_info=True)
            state["error_state"] = "sales_processing_error"
            return state
    
    # ===== 新增的便利方法 =====
    # 这些方法现在委托给response_adapter和templates模块

<<<<<<< HEAD
    async def get_greeting_message(self, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        获取个性化问候消息（委托给templates模块）
=======
    async def _generate_sales_response(
        self,
        customer_input: str,
        sales_prompt: str,
        sentiment_context: Dict[str, Any]
    ) -> tuple[str, dict]:
        """生成销售响应，返回响应内容和token信息"""
        if not sales_prompt:
            # 如果没有情感提示词，使用基础响应
            return "您好！我是您的美妆顾问，很高兴为您服务。请告诉我您的需求。", {}

        return await self.response_generator.generate_response(
            customer_input,
            sales_prompt,
            sentiment_context
        )

    def _update_state(self, state: dict, response: str, sentiment_analysis: Dict[str, Any], token_info: dict = None) -> dict:
        """更新对话状态"""
        # 设置销售响应 - 同时存储在两个位置以确保兼容性
        state["sales_response"] = response

        # 确保 values 和 agent_responses 结构存在并存储响应
        if state.get("values") is None:
            state["values"] = {}
        if state["values"].get("agent_responses") is None:
            state["values"]["agent_responses"] = {}

        agent_data = {
            "sales_response": response,
            "sentiment_analysis": sentiment_analysis,
            "timestamp": get_current_datetime()
        }

        # 添加token使用信息
        if token_info:
            agent_data.update(token_info)
            self.logger.info(f"添加token信息到agent_responses: {token_info}")

        state["values"]["agent_responses"][self.agent_id] = agent_data

        # 调试日志：跟踪响应存储
        self.logger.info(f"销售响应已存储: 长度={len(response)} 字符, agent_id={self.agent_id}")
        self.logger.info(f"values.agent_responses 结构已更新: {list(state.get('values', {}).get('agent_responses', {}).keys())}")
        self.logger.info(f"销售响应内容预览: {response[:50]}...")

        # 更新活跃智能体列表
        state.setdefault("active_agents", []).append(self.agent_id)

        # 更新对话历史
        customer_input = sentiment_analysis.get("processed_input", state.get("customer_input", ""))
        state.setdefault("conversation_history", []).extend([
            {"role": "user", "content": customer_input},
            {"role": "assistant", "content": response}
        ])

        return state

    def _create_error_state(self, state: dict, error_message: str) -> dict:
        """创建错误状态"""
        fallback_response = "感谢您的咨询！我是您的美妆顾问，很乐意为您服务。请告诉我您的具体需求。"

        # 设置销售响应 - 同时存储在两个位置以确保兼容性
        state["sales_response"] = fallback_response
        state["error_state"] = "sales_processing_error"

        # 确保 agent_responses 结构存在并存储错误状态响应
        state.setdefault("agent_responses", {})
        state["agent_responses"][self.agent_id] = {
            "sales_response": fallback_response,
            "error": error_message,
            "timestamp": get_current_datetime()
        }

        state.setdefault("active_agents", []).append(self.agent_id)

        return state

    def get_agent_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        return {
            "agent_id": self.agent_id,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "capabilities": [
                "sentiment_driven_response",
                "multimodal_input_support",
                "personalized_interaction"
            ],
            "dependencies": [
                "sentiment_analysis",
                "sales_prompt"
            ]
        }
>>>>>>> e292a6d (add: feedback handler)

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 简单的响应生成测试
            test_prompt = "客户情绪积极，可以友好交流。"
            test_response = self.response_generator.generate_response(
                "你好",
                test_prompt,
                {"sentiment": "positive", "score": 0.7, "urgency": "medium"}
            )

            return {
                "status": "healthy",
                "llm_provider": self.llm_provider,
                "llm_model": self.llm_model,
                "test_response_length": len(test_response) if test_response else 0
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
