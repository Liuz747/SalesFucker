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
from utils import get_current_datetime


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
    ) -> str:
        """生成销售响应"""
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
            request = {
                "id": uuid4(),
                "provider": self.llm_provider,
                "model": self.llm_model,
                "temperature": 0.7,
                "messages": messages
            }

            llm_response = await self.invoke_llm(request)

            if llm_response and isinstance(llm_response.content, str):
                return llm_response.content.strip()
            elif llm_response:
                return str(llm_response.content).strip()
            else:
                return self._get_fallback_response(sales_prompt)

        except Exception as e:
            return self._get_fallback_response(sales_prompt)

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
            response = await self._generate_sales_response(
                processed_input,
                sales_prompt,
                sentiment_analysis
            )

            # 更新对话状态
            updated_state = self._update_state(state, response, sentiment_analysis)

            self.logger.info(f"销售响应生成完成: 长度={len(response)}字符")
            return updated_state

        except Exception as e:
            self.logger.error(f"Agent processing failed: {e}", exc_info=True)
            state["error_state"] = "sales_processing_error"
            return state
    
    # ===== 新增的便利方法 =====
    # 这些方法现在委托给response_adapter和templates模块

    async def get_greeting_message(self, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        获取个性化问候消息（委托给templates模块）

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
